# -*- coding: utf-8 -*-
"""
知学云（zhixueyun.com）网大课程自动化学习工具
支持 GUI 模式和 CLI 命令行模式

用法:
  GUI模式:     python zhixueyun_auto_study.py --mode gui
  CLI模式:     python zhixueyun_auto_study.py --mode cli --url "URL" [--speed 1.5] [--headless] [--infinite]
"""
import os
import sys
import json
import random
import asyncio
import subprocess
import threading
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Callable, Set

from playwright.async_api import async_playwright, Page, BrowserContext

# ========================= 配置常量 =========================
DEFAULT_CONFIG = {
    "user_data_dir": "./网大浏览器数据",
    "subject_urls": [
        "https://kc.zhixueyun.com/#/branch-list-v/fbeb2cf4-6801-4575-a090-81603dce1404"
    ],
    "max_rounds_per_url": 10,
    "video_speed": 1.5,
    "headless": False,
    "browser_channel": "chrome",
    "browser_executable_path": "",
    "doc_wait_seconds": 10,
    "random_delay": (2, 5)
}

CONFIG_FILE = Path("./网大课程_config.json")

# ========================= 浏览器路径检测 =========================
def get_chrome_path_from_registry() -> Optional[str]:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
        path, _ = winreg.QueryValueEx(key, None)
        winreg.CloseKey(key)
        return path if os.path.exists(path) else None
    except Exception:
        return None

def query_chrome_path_via_cmd() -> Optional[str]:
    try:
        result = subprocess.run(
            ['reg', 'query', r'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe',
             '/ve'],
            capture_output=True, text=True, encoding='gbk', errors='ignore')
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if 'REG_SZ' in line:
                    parts = line.split('REG_SZ')
                    if len(parts) > 1:
                        path = parts[1].strip()
                        if os.path.exists(path):
                            return path
    except Exception:
        pass
    return None

def get_edge_path_from_registry() -> Optional[str]:
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                             r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe")
        path, _ = winreg.QueryValueEx(key, None)
        winreg.CloseKey(key)
        return path if os.path.exists(path) else None
    except Exception:
        return None

def detect_browser_path(browser_channel: str) -> Optional[str]:
    if browser_channel == "chrome":
        path = get_chrome_path_from_registry()
        if not path:
            path = query_chrome_path_via_cmd()
        return path
    elif browser_channel == "msedge":
        return get_edge_path_from_registry()
    return None

# ========================= 考试/测试关键词 =========================
EXAM_KEYWORDS = ["考试", "测试", "测验", "考题", "试题", "试卷", "quiz", "exam", "test"]

def is_exam_name(name: str) -> bool:
    name_lower = name.lower()
    return any(kw in name_lower for kw in EXAM_KEYWORDS)

# ========================= 核心学习引擎 =========================
class SubjectLearner:
    def __init__(self, user_data_dir, subject_url, max_rounds, video_speed=1.5,
                 headless=False, browser_channel="chrome", browser_executable_path="",
                 doc_wait_seconds=10, random_delay=(2, 5),
                 log_callback=None, progress_callback=None, finish_callback=None):
        self.user_data_dir = Path(user_data_dir)
        self.subject_url = subject_url
        self.max_rounds = max_rounds
        self.video_speed = video_speed
        self.headless = headless
        self.browser_channel = browser_channel
        self.browser_executable_path = browser_executable_path
        self.doc_wait_seconds = doc_wait_seconds
        self.random_delay = random_delay
        self.log_callback = log_callback or (lambda x: None)
        self.progress_callback = progress_callback or (lambda cur, total: None)
        self.finish_callback = finish_callback
        self.playwright = None
        self.context = None
        self.page = None
        self.completed_courses = set()
        self.completed_topics = set()
        self.stop_requested = False
        self.is_branch_list_mode = "branch-list-v" in subject_url

    def log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_callback(f"[{timestamp}] {msg}")

    def stop(self):
        self.stop_requested = True
        self.log("正在请求停止任务...")

    async def init_browser(self):
        self.log("正在启动浏览器...")
        self.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.playwright = await async_playwright().start()
        launch_options = {
            "user_data_dir": str(self.user_data_dir),
            "headless": self.headless,
            "viewport": {"width": 1280, "height": 720},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "args": ["--no-proxy-server", "--disable-extensions-except=", "--disable-blink-features=AutomationControlled"]
        }
        if self.browser_executable_path and os.path.exists(self.browser_executable_path):
            launch_options["executable_path"] = self.browser_executable_path
            launch_options["channel"] = None
        elif self.browser_channel == "chrome":
            launch_options["channel"] = "chrome"
        elif self.browser_channel == "msedge":
            launch_options["channel"] = "msedge"
        else:
            launch_options["channel"] = "chrome"
        self.context = await self.playwright.chromium.launch_persistent_context(**launch_options)
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.log("浏览器启动完成")

    async def login_if_needed(self):
        max_retries, retry_count, last_error = 3, 0, None
        while retry_count < max_retries:
            try:
                self.log(f"正在访问: {self.subject_url} (尝试 {retry_count + 1}/{max_retries})")
                await self.page.goto(self.subject_url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)
                current_url = self.page.url
                if "login" in current_url.lower() or "authorize" in current_url.lower():
                    self.log("=" * 50)
                    self.log("请手动扫码或账号密码登录，登录完成后脚本将自动继续...")
                    self.log("=" * 50)
                    try:
                        await self.page.wait_for_function(
                            "url => !url.includes('login') && !url.includes('authorize')",
                            arg=current_url, timeout=300000)
                        self.log("登录成功，等待8秒确保页面稳定...")
                        await asyncio.sleep(8)
                        await self.page.goto(self.subject_url, wait_until="domcontentloaded", timeout=30000)
                        await asyncio.sleep(3)
                    except Exception as e:
                        self.log(f"等待登录超时: {e}")
                        raise
                else:
                    self.log("已检测到登录状态")
                if self.is_branch_list_mode:
                    try:
                        await self.page.wait_for_selector(
                            ".branch-item,.course-card,.topic-item,.card-item,.list-item,.subject-card,.train-card,.branch-list .item,.ant-card,.el-card,a[href*='subject'],a[href*='study'],.item-link,.course-item",
                            timeout=15000)
                        self.log("专题列表页加载完成")
                    except:
                        self.log("警告：专题列表项未找到，尝试等待通用元素...")
                        await asyncio.sleep(5)
                else:
                    try:
                        await self.page.wait_for_selector(".item.current-hover", timeout=15000)
                        self.log("课程目录加载完成")
                    except:
                        self.log("警告：课程项未找到，刷新重试")
                        await self.page.reload()
                        await asyncio.sleep(5)
                        try:
                            await self.page.wait_for_selector(".item.current-hover", timeout=10000)
                        except:
                            self.log("仍无法找到课程项，可能页面结构变化，将尝试继续")
                return
            except Exception as e:
                last_error = e
                self.log(f"访问页面失败: {e}")
                if "ERR_NAME_NOT_RESOLVED" in str(e):
                    self.log("错误：无法解析域名，请检查网络连接")
                retry_count += 1
                if retry_count < max_retries:
                    self.log("将在 5 秒后重试...")
                    await asyncio.sleep(5)
        self.log(f"经过 {max_retries} 次尝试后仍然失败。")
        raise last_error

    async def get_topic_items(self):
        topics = []
        try:
            slides = await self.page.evaluate("""() => {
                const results = [];
                const slides = document.querySelectorAll('.swiper-slide:not(.swiper-slide-duplicate)');
                for (const s of slides) {
                    const title = s.getAttribute('title') || '';
                    const typeEl = s.querySelector('.type');
                    const type = typeEl ? typeEl.innerText.trim() : '';
                    const btn = s.querySelector('.learn-btn');
                    const btnText = btn ? btn.innerText.trim() : '';
                    const index = s.getAttribute('data-index') || '';
                    results.push({ title, type, btnText, index });
                }
                return results;
            }""")
            for i, s in enumerate(slides):
                if not s['title']: continue
                topic_id = f"topic_{s['index']}_{s['title'][:20]}"
                topics.append({"name": s['title'], "type": s['type'], "btn_text": s['btnText'],
                               "topic_id": topic_id, "index": int(s['index']) if s['index'].isdigit() else i,
                               "is_completed": False})
                status = "考试/测试[跳过]" if is_exam_name(s['title']) else "待学习"
                self.log(f"发现专题: {s['title']} [{s['type']}] [{status}]")
        except Exception as e:
            self.log(f"获取专题列表失败: {e}")
        return topics

    async def enter_topic(self, topic):
        try:
            idx = topic["index"]
            slide = self.page.locator(f".swiper-slide[data-index='{idx}']:not(.swiper-slide-duplicate)")
            if await slide.count() == 0:
                slide = self.page.locator(".swiper-slide:not(.swiper-slide-duplicate)").nth(idx)
            await slide.first.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            btn = slide.locator(".learn-btn")
            self.log(f"点击进入专题: {topic['name']}")
            try:
                async with self.context.expect_page(timeout=15000) as new_page_info:
                    await btn.first.click(timeout=10000)
                    await asyncio.sleep(3)
                new_page = await new_page_info.value
                if new_page:
                    self.log("专题在新标签页打开")
                    await new_page.wait_for_load_state("domcontentloaded")
                    await asyncio.sleep(3)
                    return new_page
            except Exception as e:
                self.log(f"等待新标签页超时: {e}")
            return None
        except Exception as e:
            self.log(f"点击专题失败: {e}")
            return None

    async def go_back_to_branch_list(self, topic_page):
        try:
            await topic_page.close()
            self.log("已关闭专题标签页")
            self.page = self.context.pages[0] if self.context.pages else self.page
            await asyncio.sleep(2)
        except Exception as e:
            self.log(f"关闭专题标签页失败: {e}")

    async def click_next_page(self):
        next_selectors = [
            ".ant-pagination-next:not(.ant-pagination-disabled)",
            ".el-pagination .btn-next:not([disabled])",
            "button:has-text('下一页'):not([disabled])",
            "a:has-text('下一页')", ".pagination .next:not(.disabled)",
            "li.next a", ".ant-pagination-next .ant-pagination-item-link"]
        for sel in next_selectors:
            try:
                locator = self.page.locator(sel)
                if await locator.count() > 0 and await locator.first.is_visible():
                    self.log(f"点击下一页 (选择器: {sel})")
                    await locator.first.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await locator.first.click()
                    await asyncio.sleep(3)
                    return True
            except:
                continue
        try:
            found = await self.page.evaluate("""() => {
                const candidates = document.querySelectorAll('button, a, li, span, div');
                for (const el of candidates) {
                    const text = el.innerText?.trim();
                    if (text === '下一页' || text === 'Next' || text === '>') {
                        if (!el.disabled && !el.classList.contains('disabled')) { el.click(); return true; }
                    }
                }
                return false;
            }""")
            if found:
                self.log("通过JS点击到下一页")
                await asyncio.sleep(3)
                return True
        except:
            pass
        self.log("未找到下一页按钮，已是最后一页")
        return False

    async def expand_all_chapters(self):
        try:
            arrows = await self.page.query_selector_all(".catalog-state .arrow-icon i, .catalog-state i[class*='arrow']")
            for arrow in arrows:
                class_name = await arrow.get_attribute("class")
                if class_name and ("arrow-down" in class_name or "arrow-right" in class_name):
                    try:
                        await arrow.click()
                        await asyncio.sleep(0.3)
                    except:
                        pass
            self.log("已展开所有章节")
        except Exception as e:
            self.log(f"展开章节时出错（可忽略）: {e}")

    async def get_pending_courses(self):
        courses = []
        try:
            await self.page.wait_for_selector(".item.current-hover", timeout=10000)
            items = await self.page.query_selector_all(".item.current-hover")
            for item in items:
                section_type = await item.get_attribute("data-section-type")
                if section_type and section_type not in ["10", "3"]: continue
                name_el = await item.query_selector(".name-des")
                name = (await name_el.inner_text()).strip() if name_el else "未知课程"
                if is_exam_name(name):
                    self.log(f"跳过考试/测试课程: {name}")
                    continue
                btn_el = await item.query_selector(".operation .small")
                if not btn_el: continue
                btn_text = (await btn_el.inner_text()).strip()
                if "继续学习" in btn_text or "开始学习" in btn_text:
                    resource_id = await item.get_attribute("data-resource-id")
                    courses.append({"name": name, "btn_text": btn_text, "resource_id": resource_id})
                    self.log(f"发现待学课程: {name} -> {btn_text}")
        except Exception as e:
            self.log(f"获取课程列表失败: {e}")
        return courses

    async def click_course(self, resource_id):
        try:
            item = self.page.locator(f"[data-resource-id='{resource_id}']")
            if await item.count() == 0: return None
            await item.first.scroll_into_view_if_needed()
            await asyncio.sleep(0.5)
            btn = item.locator(".operation .small")
            if await btn.count() == 0: return None
            async with self.context.expect_page(timeout=5000) as new_page_info:
                try:
                    await btn.first.click(timeout=5000)
                except:
                    await btn.first.click(force=True)
                await asyncio.sleep(2)
            try:
                new_page = await new_page_info.value
                if new_page:
                    self.log("课程在新标签页打开")
                    try:
                        await new_page.wait_for_selector("video, .player-content, .document-viewer", timeout=10000)
                    except:
                        await new_page.wait_for_load_state("domcontentloaded")
                    return new_page
            except:
                pass
            return self.page
        except Exception as e:
            self.log(f"点击课程失败: {e}")
            return None

    async def handle_common_popups(self, page):
        handled = False
        like_path = page.locator("svg path[d*='M908.1 353.1']")
        if await like_path.count() > 0:
            self.log("检测到点赞弹窗，正在点赞...")
            await like_path.first.click()
            await asyncio.sleep(1)
            confirm_btn = page.locator("button.ant-btn-primary:has-text('确定')")
            if await confirm_btn.count() > 0:
                try:
                    await confirm_btn.first.wait_for(state="visible", timeout=5000)
                    await confirm_btn.first.click()
                    self.log("已点击确定按钮")
                    handled = True
                    await asyncio.sleep(1)
                except Exception as e:
                    self.log(f"点击确定按钮失败: {e}")
        i_know_btn = page.locator("#D345btn-ok, .btn-ok:has-text('我知道了')")
        if await i_know_btn.count() > 0:
            self.log("检测到「我知道了」弹窗，正在关闭...")
            await i_know_btn.first.click()
            handled = True
            await asyncio.sleep(1)
        return handled

    async def handle_popup(self, page):
        try:
            like = page.locator("text=点赞")
            submit = page.locator("button:has-text('提交')")
            if await like.count() > 0 and await submit.count() > 0:
                self.log("检测到课程质量评价弹窗，正在处理...")
                await like.first.click()
                await asyncio.sleep(0.5)
                await submit.first.click()
                await asyncio.sleep(2)
                self.log("已点赞并提交")
                continue_btn = page.locator("text=继续学习")
                if await continue_btn.count() > 0:
                    await continue_btn.first.click()
                    await asyncio.sleep(1)
                    self.log("已点击继续学习")
                return True
        except Exception as e:
            self.log(f"处理课程评价弹窗失败: {e}")
        return await self.handle_common_popups(page)

    async def wait_video_complete(self, page, check_interval=2, timeout=3600):
        start_time = datetime.now()
        last_progress = -1
        while (datetime.now() - start_time).total_seconds() < timeout:
            if self.stop_requested:
                self.log("收到停止信号，中断视频播放")
                return False
            await self.handle_popup(page)
            state = await page.evaluate("""() => {
                const v = document.querySelector('video');
                if(!v) return { ended: false, currentTime: 0, duration: 0 };
                return { ended: v.ended, currentTime: v.currentTime, duration: v.duration };
            }""")
            if state["ended"]:
                await self.handle_popup(page)
                return True
            if state["duration"] > 0:
                progress = state["currentTime"] / state["duration"]
                if progress >= 0.98:
                    await self.handle_popup(page)
                    return True
                if int(progress * 10) > last_progress:
                    last_progress = int(progress * 10)
                    self.log(f"视频进度: {progress * 100:.1f}%")
            await asyncio.sleep(check_interval)
        return False

    async def play_single_video(self, page):
        video = await page.query_selector("video")
        if not video:
            self.log("未找到视频元素")
            return False
        await video.scroll_into_view_if_needed()
        await page.evaluate(f"""() => {{
            const v = document.querySelector('video');
            if(v) v.playbackRate = {self.video_speed};
            if(v) v.play();
        }}""")
        completed = await self.wait_video_complete(page)
        if not completed:
            self.log("视频播放未完成")
            return False
        self.log("视频播放完成")
        return True

    async def handle_document(self, page):
        try:
            pdf_iframe = page.locator("iframe.pdf-iframe")
            if await pdf_iframe.count() > 0:
                self.log("检测到PDF iframe，模拟滚动...")
                box = await pdf_iframe.first.bounding_box()
                if box:
                    cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                    await page.mouse.move(cx, cy)
                    await asyncio.sleep(0.3)
                    await page.mouse.click(cx, cy)
                    await asyncio.sleep(0.5)
                    self.log("开始高频滚动10秒...")
                    start_time = datetime.now()
                    while (datetime.now() - start_time).total_seconds() < 10 and not self.stop_requested:
                        dy = random.choice([-1, 1]) * random.randint(300, 500)
                        await page.mouse.wheel(0, dy)
                        await asyncio.sleep(random.uniform(0.1, 0.3))
                    self.log("PDF滚动完成")
                    return True
            text_layer = page.locator("div.textLayer")
            if await text_layer.count() > 0:
                self.log("检测到textLayer区域，移动鼠标滚动...")
                await page.mouse.move(680, 466)
                await asyncio.sleep(0.3)
                await page.mouse.click(680, 466)
                await asyncio.sleep(0.5)
                start_time = datetime.now()
                while (datetime.now() - start_time).total_seconds() < 10 and not self.stop_requested:
                    dy = random.choice([-1, 1]) * random.randint(250, 450)
                    await page.mouse.wheel(0, dy)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                self.log("textLayer滚动完成")
                return True
            doc = page.locator(".player-content, .document-viewer")
            if await doc.count() > 0:
                self.log("检测到文档容器，等待内容加载...")
                await doc.first.wait_for(state="visible", timeout=60000)
                await asyncio.sleep(5)
                self.log("开始模拟阅读...")
                start_time = datetime.now()
                while (datetime.now() - start_time).total_seconds() < 10 and not self.stop_requested:
                    await page.evaluate("() => { const d = document.querySelector('.player-content, .document-viewer'); if(d) d.scrollTop += 400; }")
                    await asyncio.sleep(random.uniform(0.1, 0.2))
                await page.evaluate("() => { const d = document.querySelector('.player-content, .document-viewer'); if(d) d.scrollTop = d.scrollHeight; }")
                await asyncio.sleep(2)
                self.log("文档阅读完成")
                return True
            self.log(f"未检测到文档容器，等待{self.doc_wait_seconds}秒")
            for _ in range(self.doc_wait_seconds):
                if self.stop_requested: return False
                await asyncio.sleep(1)
            return True
        except Exception as e:
            self.log(f"文档处理失败: {e}")
            return False

    async def learn_chapter_section(self, course_page, section_idx, total_sections=0):
        try:
            all_sections = await course_page.query_selector_all("dl[data-sectiontype='1'], dl[data-sectiontype='6']")
            if section_idx > len(all_sections):
                self.log(f"第 {section_idx} 个小节超出范围，跳过")
                return False
            section_element = all_sections[section_idx - 1]
            try:
                section_name_el = await section_element.query_selector(".name-des, .name, dt, .title")
                if section_name_el:
                    section_name = (await section_name_el.inner_text()).strip()
                    if is_exam_name(section_name):
                        self.log(f"跳过考试/测试小节: {section_name}")
                        return True
            except:
                pass
        except Exception as e:
            self.log(f"无法定位第 {section_idx} 个小节: {e}")
            return False
        play_btn = None
        icon = await section_element.query_selector(".icon-com-play")
        if icon:
            play_btn = icon
        else:
            pointer = await section_element.query_selector(".item.pointer")
            if pointer: play_btn = pointer
        if not play_btn:
            self.log(f"第 {section_idx} 个小节未找到播放按钮，跳过")
            return False
        try:
            await play_btn.click(timeout=10000)
        except Exception as e:
            self.log(f"点击第 {section_idx} 个小节播放按钮失败: {e}")
            return False
        await asyncio.sleep(2)
        try:
            await course_page.wait_for_selector("video, .player-content, .document-viewer", timeout=15000)
        except:
            self.log("小节内容加载超时或没有可学习内容")
            return True
        video = await course_page.query_selector("video")
        success = await self.play_single_video(course_page) if video else await self.handle_document(course_page)
        await self.handle_popup(course_page)
        return success

    async def learn_course_with_sections(self, course_page):
        try:
            await course_page.wait_for_selector("dl[data-sectiontype='1'], dl[data-sectiontype='6']", timeout=10000)
        except:
            self.log("未找到小节列表，可能是单一内容课程")
            return False
        sections = await course_page.query_selector_all("dl[data-sectiontype='1'], dl[data-sectiontype='6']")
        total = len(sections)
        if total == 0: return False
        exam_count = 0
        for s in sections:
            try:
                name_el = await s.query_selector(".name-des, .name, dt, .title")
                if name_el:
                    name = (await name_el.inner_text()).strip()
                    if is_exam_name(name): exam_count += 1
            except:
                pass
        if exam_count > 0:
            self.log(f"其中 {exam_count} 个小节为考试/测试，将跳过")
        for idx in range(1, total + 1):
            if self.stop_requested: break
            self.log(f"学习第 {idx}/{total} 个小节")
            success = await self.learn_chapter_section(course_page, idx, total)
            if not success:
                self.log(f"第 {idx} 个小节学习失败，继续下一个")
            await asyncio.sleep(random.uniform(1, 3))
        self.log("所有小节学习完成（考试已跳过）")
        await self.handle_popup(course_page)
        return True

    async def learn_course(self, course):
        name, resource_id = course["name"], course["resource_id"]
        if is_exam_name(name):
            self.log(f"跳过考试/测试课程: {name}")
            return True
        if resource_id in self.completed_courses:
            self.log(f"跳过已完成记录: {name}")
            return True
        self.log(f"开始学习: {name} ({course['btn_text']})")
        course_page = await self.click_course(resource_id)
        if not course_page:
            self.log(f"无法点击课程: {name}")
            return False
        original_page = self.page
        self.page = course_page
        try:
            has_sections = await self.learn_course_with_sections(self.page)
            if has_sections:
                success = True
            else:
                video_present = await self.page.locator("video").count() > 0
                success = await self.play_single_video(self.page) if video_present else await self.handle_document(self.page)
            if success and not self.stop_requested:
                self.completed_courses.add(resource_id)
                self.log(f"成功完成课程: {name}")
            else:
                self.log(f"课程未完成: {name}")
        finally:
            if course_page != original_page:
                await course_page.close()
            else:
                if "subject/detail" not in self.page.url:
                    await self.page.go_back()
            await asyncio.sleep(2)
            self.page = original_page
        return success

    async def learn_topic_courses(self, topic_page):
        try:
            await asyncio.sleep(5)
            iframe_frame = None
            for f in topic_page.frames:
                if 'paas-designer' in f.url:
                    iframe_frame = f
                    break
            if not iframe_frame:
                self.log("未找到专题详情iframe，尝试等待...")
                await asyncio.sleep(5)
                for f in topic_page.frames:
                    if 'paas-designer' in f.url:
                        iframe_frame = f
                        break
            if not iframe_frame:
                self.log("仍未找到iframe，跳过该专题")
                return False
            self.log("已进入专题详情iframe")
            any_learned, page_num = False, 1
            while not self.stop_requested:
                self.log(f"专题内课程第 {page_num} 页")
                await asyncio.sleep(3)
                courses = await self._get_iframe_courses(iframe_frame)
                if not courses:
                    self.log("当前页未找到待学习课程")
                    if await self._click_iframe_next_page(iframe_frame):
                        page_num += 1
                        continue
                    else:
                        break
                pending = [c for c in courses if not is_exam_name(c['name'])]
                exam_skipped = len(courses) - len(pending)
                if exam_skipped > 0:
                    self.log(f"跳过 {exam_skipped} 门考试/测试课程")
                if not pending:
                    self.log("当前页所有课程为考试或已完成")
                    if await self._click_iframe_next_page(iframe_frame):
                        page_num += 1
                        continue
                    else:
                        break
                self.log(f"发现 {len(pending)} 门待学习课程")
                self.progress_callback(0, len(pending))
                for idx, course in enumerate(pending, 1):
                    if self.stop_requested: return any_learned
                    self.progress_callback(idx, len(pending))
                    learned = await self._learn_iframe_course(iframe_frame, topic_page, course)
                    if learned: any_learned = True
                    await asyncio.sleep(random.uniform(*self.random_delay))
                if await self._click_iframe_next_page(iframe_frame):
                    page_num += 1
                else:
                    break
            return any_learned
        except Exception as e:
            self.log(f"专题内学习异常: {e}")
            return False

    async def _get_iframe_courses(self, iframe_frame):
        courses = []
        try:
            items = await iframe_frame.evaluate("""() => {
                const results = [];
                const operations = document.querySelectorAll('.operation');
                for (const op of operations) {
                    const container = op.closest('.activeContent') || op.parentElement;
                    const lineEl = container?.querySelector('.line');
                    const name = lineEl?.innerText?.trim() || '';
                    const statusEl = op.querySelector('.status');
                    const status = statusEl?.innerText?.trim() || '';
                    const allText = op.innerText?.trim() || '';
                    let btnText = '';
                    if (allText.includes('开始学习')) btnText = '开始学习';
                    else if (allText.includes('继续学习')) btnText = '继续学习';
                    else if (allText.includes('重新学习')) btnText = '已完成';
                    if (name && btnText !== '已完成') {
                        results.push({ name: name.substring(0, 100), status, btnText });
                    }
                }
                return results;
            }""")
            for item in items:
                courses.append({"name": item['name'], "status": item['status'], "btn_text": item['btnText']})
                self.log(f"  待学课程: {item['name'][:50]} [{item['btnText']}]")
        except Exception as e:
            self.log(f"获取iframe课程列表失败: {e}")
        return courses

    async def _learn_iframe_course(self, iframe_frame, topic_page, course):
        name, btn_text = course['name'], course['btn_text']
        self.log(f"开始学习: {name[:50]} ({btn_text})")
        try:
            iframe_fl = topic_page.frame_locator("iframe.paasIframe")
            btn_locator = iframe_fl.locator(f"span:has-text('{btn_text}')").first
            pages_before = len(self.context.pages)
            try:
                async with self.context.expect_page(timeout=15000) as new_page_info:
                    await btn_locator.click(timeout=10000)
                    await asyncio.sleep(3)
                course_page = await new_page_info.value
            except:
                await btn_locator.click(timeout=10000)
                await asyncio.sleep(5)
                course_page = self.context.pages[-1] if len(self.context.pages) > pages_before else None
            if not course_page:
                self.log(f"点击课程未打开新页面: {name[:50]}")
                return False
            self.log(f"课程在新标签页打开: {course_page.url[:80]}")
            await course_page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            try:
                has_sections = await self._learn_course_page(course_page)
                if has_sections and not self.stop_requested:
                    self.log(f"课程学习完成: {name[:50]}")
                else:
                    self.log(f"课程未完成: {name[:50]}")
            finally:
                try:
                    await course_page.close()
                    self.log("已关闭课程标签页")
                except:
                    pass
                await asyncio.sleep(2)
            return True
        except Exception as e:
            self.log(f"学习课程失败: {name[:50]} - {e}")
            return False

    async def _learn_course_page(self, course_page):
        try:
            await asyncio.sleep(3)
            try:
                arrows = await course_page.query_selector_all(".catalog-state .arrow-icon i, .catalog-state i[class*='arrow']")
                for arrow in arrows:
                    class_name = await arrow.get_attribute("class")
                    if class_name and ("arrow-down" in class_name or "arrow-right" in class_name):
                        try:
                            await arrow.click()
                            await asyncio.sleep(0.3)
                        except:
                            pass
                self.log("已展开所有章节")
            except:
                pass
            has_sections = await self.learn_course_with_sections(course_page)
            if has_sections: return True
            video_present = await course_page.locator("video").count() > 0
            return await self.play_single_video(course_page) if video_present else await self.handle_document(course_page)
        except Exception as e:
            self.log(f"课程页面学习失败: {e}")
            return False

    async def _click_iframe_next_page(self, iframe_frame):
        try:
            next_btn = iframe_frame.locator(".ant-pagination-next:not(.ant-pagination-disabled)")
            if await next_btn.count() > 0:
                self.log("点击iframe内下一页")
                await next_btn.first.click()
                await asyncio.sleep(3)
                return True
            found = await iframe_frame.evaluate("""() => {
                const next = document.querySelector('.ant-pagination-next:not(.ant-pagination-disabled)');
                if (next) { next.click(); return true; }
                return false;
            }""")
            if found:
                self.log("通过JS点击iframe内下一页")
                await asyncio.sleep(3)
                return True
        except Exception as e:
            self.log(f"iframe内翻页失败: {e}")
        return False

    async def run(self):
        try:
            await self.init_browser()
            await self.login_if_needed()
            if self.is_branch_list_mode:
                await self._run_branch_list_mode()
            else:
                await self._run_single_url_mode()
        except Exception as e:
            self.log(f"发生异常: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            if self.context: await self.context.close()
            if self.playwright: await self.playwright.stop()
            if self.finish_callback: self.finish_callback()

    async def _run_single_url_mode(self):
        await self.expand_all_chapters()
        round_count = 0
        while not self.stop_requested and round_count < self.max_rounds:
            round_count += 1
            self.log(f"开始第 {round_count} 轮扫描（最大 {self.max_rounds} 轮）")
            self.completed_courses.clear()
            pending = await self.get_pending_courses()
            if not pending:
                self.log("当前URL下所有课程已完成！")
                break
            total = len(pending)
            self.progress_callback(0, total)
            self.log(f"发现 {total} 门待学课程")
            for idx, course in enumerate(pending, 1):
                if self.stop_requested:
                    self.log("用户停止操作")
                    return
                self.progress_callback(idx, total)
                await self.learn_course(course)
                await asyncio.sleep(random.uniform(*self.random_delay))
            self.log(f"第 {round_count} 轮完成，重新扫描...")
            await asyncio.sleep(3)
        if round_count >= self.max_rounds and not self.stop_requested:
            self.log(f"已达到最大扫描轮数 {self.max_rounds}，停止当前URL学习。")

    async def _run_branch_list_mode(self):
        page_num, total_topics_learned = 1, 0
        while not self.stop_requested:
            self.log(f"\n{'='*60}\n专题列表第 {page_num} 页\n{'='*60}")
            topics = await self.get_topic_items()
            if not topics:
                self.log("当前页未找到专题卡片，等待重试...")
                await asyncio.sleep(5)
                topics = await self.get_topic_items()
                if not topics:
                    self.log("仍未找到专题，结束")
                    break
            pending_topics = []
            for topic in topics:
                if topic["topic_id"] in self.completed_topics:
                    self.log(f"跳过已完成专题: {topic['name']}")
                    continue
                if is_exam_name(topic["name"]):
                    self.log(f"跳过考试/测试专题: {topic['name']}")
                    continue
                pending_topics.append(topic)
            if not pending_topics:
                self.log(f"第 {page_num} 页所有专题已完成或为考试，尝试翻页...")
                if await self.click_next_page():
                    page_num += 1
                    continue
                else:
                    self.log("所有页面已完成，学习流程结束！")
                    break
            self.log(f"第 {page_num} 页有 {len(pending_topics)} 个待学习专题")
            for idx, topic in enumerate(pending_topics, 1):
                if self.stop_requested:
                    self.log("用户停止操作")
                    return
                self.log(f"\n--- [{idx}/{len(pending_topics)}] 进入专题: {topic['name']} ---")
                self.progress_callback(idx, len(pending_topics))
                topic_page = await self.enter_topic(topic)
                if not topic_page:
                    self.log(f"无法进入专题: {topic['name']}，跳过")
                    continue
                learned = await self.learn_topic_courses(topic_page)
                if learned and not self.stop_requested:
                    self.completed_topics.add(topic["topic_id"])
                    total_topics_learned += 1
                    self.log(f"专题学习完成: {topic['name']} (累计完成 {total_topics_learned} 个专题)")
                else:
                    self.log(f"专题未完成或被跳过: {topic['name']}")
                try:
                    await self.go_back_to_branch_list(topic_page)
                except:
                    pass
                delay = random.uniform(3, 8)
                self.log(f"专题间休息 {delay:.1f} 秒...")
                await asyncio.sleep(delay)
            self.log(f"第 {page_num} 页所有专题处理完毕")
            if await self.click_next_page():
                page_num += 1
                self.log(f"翻到第 {page_num} 页")
                await asyncio.sleep(3)
            else:
                self.log("已是最后一页，所有专题学习完成！")
                break
        self.log(f"\n学习流程结束！共完成 {total_topics_learned} 个专题，翻越 {page_num} 页")


# ========================= CLI 模式入口 =========================
def run_cli(args):
    urls = args.url
    if not urls:
        print("错误：cli 模式需要至少指定一个 --url 参数")
        sys.exit(1)
    browser_path = args.browser_path
    if not browser_path:
        detected = detect_browser_path(args.browser)
        if detected:
            browser_path = detected
            print(f"自动检测到浏览器: {detected}")
        else:
            print(f"未检测到 {args.browser}，将使用 Playwright 默认浏览器")

    async def cli_runner():
        for idx, url in enumerate(urls, 1):
            print(f"\n========== 处理第 {idx}/{len(urls)} 个URL ==========")
            print(f"URL: {url}")
            print(f"倍速: {args.speed}x | 无头: {args.headless} | 最大轮数: {args.max_rounds}")
            learner = SubjectLearner(
                user_data_dir=args.user_data_dir, subject_url=url,
                max_rounds=args.max_rounds, video_speed=args.speed,
                headless=args.headless, browser_channel=args.browser,
                browser_executable_path=browser_path or "",
                log_callback=lambda msg: print(msg),
                progress_callback=lambda cur, total: None, finish_callback=None)
            await learner.run()

    loop_count = 0
    while True:
        loop_count += 1
        if args.infinite:
            print(f"\n{'#'*60}\n第 {loop_count} 轮循环开始\n{'#'*60}")
        asyncio.run(cli_runner())
        if not args.infinite: break
        print("\n所有URL处理完成，等待5秒后重新开始循环...")
        import time; time.sleep(5)


# ========================= GUI 模式入口 =========================
def run_gui():
    import tkinter as tk
    from tkinter import filedialog, simpledialog
    import ttkbootstrap as ttk
    import ttkbootstrap.constants as ttk_constants
    from ttkbootstrap.dialogs import Messagebox
    try:
        from ttkbootstrap.widgets import ScrolledText
    except ImportError:
        try:
            from ttkbootstrap.scrolled import ScrolledText
        except ImportError:
            from tkinter.scrolledtext import ScrolledText

    class UrlManager:
        def __init__(self, parent_frame, urls_changed_callback):
            self.parent = parent_frame
            self.urls_changed_callback = urls_changed_callback
            self.listbox = None
            self.entry = None
            self.history = []
            self.history_index = -1
            self._create_widgets()
            self._save_history_snapshot()

        def _create_widgets(self):
            main_frame = ttk.Frame(self.parent)
            main_frame.pack(fill=tk.BOTH, expand=True, pady=5)
            left_frame = ttk.Frame(main_frame)
            left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            ttk.Label(left_frame, text="课程URL列表（每行一个，按顺序处理）", font=("微软雅黑", 9)).pack(anchor=tk.W, pady=(0, 5))
            list_frame = ttk.Frame(left_frame)
            list_frame.pack(fill=tk.BOTH, expand=True)
            self.listbox = tk.Listbox(list_frame, height=8, selectmode=tk.SINGLE, font=("Consolas", 9))
            scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.listbox.yview)
            self.listbox.configure(yscrollcommand=scrollbar.set)
            self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            add_frame = ttk.Frame(left_frame)
            add_frame.pack(fill=tk.X, pady=5)
            ttk.Label(add_frame, text="新URL:").pack(side=tk.LEFT, padx=2)
            self.entry = ttk.Entry(add_frame, width=50)
            self.entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            ttk.Button(add_frame, text="添加", bootstyle="success", command=self._add_url).pack(side=tk.LEFT, padx=2)
            right_frame = ttk.Frame(main_frame)
            right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
            for text, style, cmd in [("编辑选中", "primary", self._edit_selected), ("删除选中", "danger", self._delete_selected),
                                     ("上移", "info", self._move_up), ("下移", "info", self._move_down),
                                     ("撤销 Ctrl+Z", "secondary", self._undo), ("重做 Ctrl+Y", "secondary", self._redo)]:
                ttk.Button(right_frame, text=text, bootstyle=style, command=cmd, width=10).pack(pady=2)
            self.parent.bind_all("<Control-z>", lambda e: self._undo())
            self.parent.bind_all("<Control-y>", lambda e: self._redo())
            self.parent.bind_all("<Control-Z>", lambda e: self._redo())

        def _save_history_snapshot(self):
            self.history = self.history[:self.history_index + 1]
            snapshot = list(self.listbox.get(0, tk.END))
            self.history.append(snapshot)
            self.history_index = len(self.history) - 1
            if len(self.history) > 50:
                self.history.pop(0); self.history_index -= 1

        def _restore_history_snapshot(self, snapshot):
            self.listbox.delete(0, tk.END)
            for item in snapshot: self.listbox.insert(tk.END, item)
            self._notify_change()

        def _undo(self):
            if self.history_index > 0:
                self.history_index -= 1
                self._restore_history_snapshot(self.history[self.history_index])

        def _redo(self):
            if self.history_index < len(self.history) - 1:
                self.history_index += 1
                self._restore_history_snapshot(self.history[self.history_index])

        def _add_url(self):
            url = self.entry.get().strip()
            if url:
                self.listbox.insert(tk.END, url)
                self.entry.delete(0, tk.END)
                self._save_history_snapshot(); self._notify_change()

        def _edit_selected(self):
            selection = self.listbox.curselection()
            if not selection:
                Messagebox.show_warning("请先选中要编辑的URL", "提示"); return
            idx = selection[0]
            old_url = self.listbox.get(idx)
            new_url = simpledialog.askstring("编辑URL", "请输入新的URL：", initialvalue=old_url, parent=self.parent)
            if new_url and new_url.strip():
                self.listbox.delete(idx); self.listbox.insert(idx, new_url.strip())
                self.listbox.selection_set(idx)
                self._save_history_snapshot(); self._notify_change()

        def _delete_selected(self):
            selection = self.listbox.curselection()
            if selection:
                self.listbox.delete(selection[0])
                self._save_history_snapshot(); self._notify_change()
            else:
                Messagebox.show_warning("请先选中要删除的URL", "提示")

        def _move_up(self):
            selection = self.listbox.curselection()
            if selection and selection[0] > 0:
                idx = selection[0]; item = self.listbox.get(idx)
                self.listbox.delete(idx); self.listbox.insert(idx-1, item)
                self.listbox.selection_set(idx-1)
                self._save_history_snapshot(); self._notify_change()

        def _move_down(self):
            selection = self.listbox.curselection()
            if selection and selection[0] < self.listbox.size() - 1:
                idx = selection[0]; item = self.listbox.get(idx)
                self.listbox.delete(idx); self.listbox.insert(idx+1, item)
                self.listbox.selection_set(idx+1)
                self._save_history_snapshot(); self._notify_change()

        def _notify_change(self):
            if self.urls_changed_callback: self.urls_changed_callback(self.get_urls())

        def get_urls(self):
            return list(self.listbox.get(0, tk.END))

        def set_urls(self, urls):
            self.listbox.delete(0, tk.END)
            for url in urls: self.listbox.insert(tk.END, url)
            self.history = []; self.history_index = -1
            self._save_history_snapshot(); self._notify_change()

    class NetCourseApp:
        def __init__(self):
            self.root = ttk.Window(title="网大课程自动化学习工具（多URL版）", themename="superhero", size=(1100, 850))
            self.root.minsize(900, 700); self.root.resizable(True, True)
            self.config = self.load_config()
            self.user_data_dir = tk.StringVar(value=self.config["user_data_dir"])
            self.video_speed = tk.StringVar(value=str(self.config["video_speed"]))
            self.headless = tk.BooleanVar(value=self.config["headless"])
            self.browser_channel = tk.StringVar(value=self.config["browser_channel"])
            self.browser_executable_path = tk.StringVar(value=self.config["browser_executable_path"])
            self.max_rounds = tk.IntVar(value=self.config["max_rounds_per_url"])
            self.url_manager = None; self.learner = None; self.thread = None
            self.stop_flag = False; self.infinite_loop = tk.BooleanVar(value=False)
            self._create_widgets(); self._auto_detect_browser()

        def load_config(self):
            if CONFIG_FILE.exists():
                try:
                    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                        saved = json.load(f)
                        config = DEFAULT_CONFIG.copy(); config.update(saved); return config
                except: pass
            return DEFAULT_CONFIG.copy()

        def save_config(self):
            config = {"user_data_dir": self.user_data_dir.get(), "subject_urls": self.url_manager.get_urls(),
                      "max_rounds_per_url": self.max_rounds.get(), "video_speed": float(self.video_speed.get()),
                      "headless": self.headless.get(), "browser_channel": self.browser_channel.get(),
                      "browser_executable_path": self.browser_executable_path.get()}
            try:
                with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except: pass

        def _create_widgets(self):
            main_frame = ttk.Frame(self.root, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)
            header = ttk.Frame(main_frame); header.pack(fill=tk.X, pady=(0, 10))
            ttk.Label(header, text="网大课程自动化学习系统（多URL版）", font=("微软雅黑", 16, "bold")).pack(side=tk.LEFT)
            ttk.Label(header, text="支持多课程URL自动切换", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=10)
            basic_frame = ttk.Labelframe(main_frame, text="基本设置", padding=10, bootstyle="primary")
            basic_frame.pack(fill=tk.X, pady=(0, 10))
            row_combined = ttk.Frame(basic_frame); row_combined.pack(fill=tk.X, pady=5)
            left_row = ttk.Frame(row_combined); left_row.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
            ttk.Label(left_row, text="用户数据目录:", width=14).pack(side=tk.LEFT)
            ttk.Entry(left_row, textvariable=self.user_data_dir, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            ttk.Button(left_row, text="浏览", command=self._browse_user_data, bootstyle="secondary").pack(side=tk.LEFT, padx=2)
            ttk.Button(left_row, text="打开目录", command=self._open_user_data, bootstyle="info").pack(side=tk.LEFT, padx=2)
            right_row = ttk.Frame(row_combined); right_row.pack(side=tk.RIGHT, fill=tk.X)
            ttk.Label(right_row, text="每个URL最大扫描轮数:", width=18).pack(side=tk.LEFT)
            ttk.Spinbox(right_row, from_=1, to=99, textvariable=self.max_rounds, width=10).pack(side=tk.LEFT, padx=5)
            ttk.Label(right_row, text="轮（达到后自动切换）").pack(side=tk.LEFT)
            url_frame = ttk.Labelframe(main_frame, text="课程URL列表管理", padding=10, bootstyle="primary")
            url_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
            self.url_manager = UrlManager(url_frame, self._on_urls_changed)
            self.url_manager.set_urls(self.config["subject_urls"])
            browser_frame = ttk.Labelframe(main_frame, text="浏览器设置", padding=10, bootstyle="primary")
            browser_frame.pack(fill=tk.X, pady=(0, 10))
            browser_row = ttk.Frame(browser_frame); browser_row.pack(fill=tk.X, pady=5)
            type_frame = ttk.Frame(browser_row); type_frame.pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(type_frame, text="浏览器类型:", width=14).pack(side=tk.LEFT)
            ttk.Radiobutton(type_frame, text="Chrome", variable=self.browser_channel, value="chrome", command=self._on_browser_changed, bootstyle="info").pack(side=tk.LEFT, padx=5)
            ttk.Radiobutton(type_frame, text="Edge", variable=self.browser_channel, value="msedge", command=self._on_browser_changed, bootstyle="info").pack(side=tk.LEFT, padx=5)
            ttk.Button(type_frame, text="自动检测", command=self._auto_detect_browser, bootstyle="secondary").pack(side=tk.LEFT, padx=10)
            speed_frame = ttk.Frame(browser_row); speed_frame.pack(side=tk.LEFT, padx=(0, 20))
            ttk.Label(speed_frame, text="视频播放倍速:", width=14).pack(side=tk.LEFT)
            ttk.Combobox(speed_frame, textvariable=self.video_speed, values=["0.75", "1.0", "1.25", "1.5"], width=8, state="readonly").pack(side=tk.LEFT, padx=5)
            headless_frame = ttk.Frame(browser_row); headless_frame.pack(side=tk.LEFT)
            ttk.Checkbutton(headless_frame, text="无头模式（不显示浏览器）", variable=self.headless, bootstyle="info").pack(side=tk.LEFT)
            row4 = ttk.Frame(browser_frame); row4.pack(fill=tk.X, pady=5)
            ttk.Label(row4, text="浏览器可执行文件路径:", width=14).pack(side=tk.LEFT)
            ttk.Entry(row4, textvariable=self.browser_executable_path, width=60).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
            ttk.Button(row4, text="浏览", command=self._browse_browser_exe, bootstyle="secondary").pack(side=tk.LEFT)
            control_frame = ttk.Frame(main_frame); control_frame.pack(fill=tk.X, pady=10)
            self.start_btn = ttk.Button(control_frame, text="▶ 开始学习", command=self._start_learning, bootstyle="success", width=15)
            self.start_btn.pack(side=tk.LEFT, padx=5)
            self.stop_btn = ttk.Button(control_frame, text="⏹ 停止", command=self._stop_learning, bootstyle="danger", width=15, state=tk.DISABLED)
            self.stop_btn.pack(side=tk.LEFT, padx=5)
            self.save_btn = ttk.Button(control_frame, text="💾 保存配置", command=self.save_config, bootstyle="info", width=15)
            self.save_btn.pack(side=tk.LEFT, padx=5)
            self.infinite_loop = tk.BooleanVar(value=False)
            ttk.Checkbutton(control_frame, text="无限循环模式", variable=self.infinite_loop, bootstyle="info").pack(side=tk.LEFT, padx=10)
            self.progress_bar = ttk.Progressbar(control_frame, bootstyle="success-striped", mode='determinate', length=400)
            self.progress_bar.pack(side=tk.LEFT, padx=20, fill=tk.X, expand=True)
            self.progress_label = ttk.Label(control_frame, text="未开始", width=12); self.progress_label.pack(side=tk.LEFT)
            log_frame = ttk.Labelframe(main_frame, text="运行日志", padding=5, bootstyle="primary")
            log_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
            self.log_text = ScrolledText(log_frame, height=20, wrap=tk.WORD, font=("Consolas", 9), bootstyle="dark")
            self.log_text.pack(fill=tk.BOTH, expand=True)
            footer = ttk.Frame(main_frame); footer.pack(fill=tk.X, pady=(5, 0))
            ttk.Label(footer, text="提示：程序会依次处理列表中的每个URL，每个URL最大扫描轮数达到后自动切换。支持手动停止。", font=("微软雅黑", 8), foreground="gray").pack()

        def _on_urls_changed(self, urls): self.save_config()
        def _log(self, msg):
            self.log_text.insert(tk.END, msg + "\n"); self.log_text.see(tk.END); self.root.update_idletasks()
        def _update_progress(self, current, total):
            if total > 0:
                self.progress_bar['maximum'] = total; self.progress_bar['value'] = current
                self.progress_label.config(text=f"{current}/{total}")
            else:
                self.progress_bar['value'] = 0; self.progress_label.config(text="无课程")
        def _on_finish(self):
            self.start_btn.config(state=tk.NORMAL); self.stop_btn.config(state=tk.DISABLED)
            self.save_btn.config(state=tk.NORMAL); self.progress_label.config(text="完成")
            self._log("自动化流程结束"); self.learner = None; self.thread = None
        def _browse_user_data(self):
            dir_path = filedialog.askdirectory(title="选择用户数据目录")
            if dir_path: self.user_data_dir.set(dir_path)
        def _open_user_data(self):
            path = Path(self.user_data_dir.get())
            if path.exists(): os.startfile(str(path))
            else: Messagebox.show_warning("目录不存在，将自动创建", "提示")
        def _browse_browser_exe(self):
            path = filedialog.askopenfilename(title="选择浏览器可执行文件", filetypes=[("exe文件", "*.exe")])
            if path: self.browser_executable_path.set(path)
        def _on_browser_changed(self): self._auto_detect_browser()
        def _auto_detect_browser(self):
            browser_type = self.browser_channel.get()
            self._log(f"正在自动检测 {browser_type.upper()} 浏览器路径...")
            path = detect_browser_path(browser_type)
            if path:
                self.browser_executable_path.set(path)
                self._log(f"检测到 {browser_type.upper()} 路径: {path}")
            else:
                self._log(f"未检测到 {browser_type.upper()}，请手动选择可执行文件")
                if browser_type == "chrome": Messagebox.show_warning("未自动检测到Chrome，请手动选择chrome.exe", "提示")
                else: Messagebox.show_warning("未自动检测到Edge，请手动选择msedge.exe", "提示")

        def _start_learning(self):
            self.save_config()
            user_dir = self.user_data_dir.get().strip()
            if not user_dir: Messagebox.show_error("请设置用户数据目录", "错误"); return
            Path(user_dir).mkdir(parents=True, exist_ok=True)
            urls = self.url_manager.get_urls()
            if not urls: Messagebox.show_error("请至少添加一个课程URL", "错误"); return
            try:
                import playwright
            except ImportError:
                Messagebox.show_error("未安装Playwright，请执行：pip install playwright && playwright install", "缺少依赖"); return
            self.start_btn.config(state=tk.DISABLED); self.stop_btn.config(state=tk.NORMAL)
            self.save_btn.config(state=tk.DISABLED)
            self.progress_bar['value'] = 0; self.progress_label.config(text="准备中...")
            self.log_text.delete(1.0, tk.END)
            self.stop_flag = False; infinite = self.infinite_loop.get()
            def run_multi_url():
                async def multi_url_runner():
                    try:
                        while not self.stop_flag:
                            for idx, url in enumerate(urls, 1):
                                if self.stop_flag: break
                                self._log(f"\n========== 开始处理第 {idx}/{len(urls)} 个URL ==========")
                                self._log(f"URL: {url}\n最大扫描轮数: {self.max_rounds.get()} 轮")
                                learner = SubjectLearner(
                                    user_data_dir=user_dir, subject_url=url, max_rounds=self.max_rounds.get(),
                                    video_speed=float(self.video_speed.get()), headless=self.headless.get(),
                                    browser_channel=self.browser_channel.get(),
                                    browser_executable_path=self.browser_executable_path.get(),
                                    log_callback=self._log, progress_callback=self._update_progress, finish_callback=None)
                                self.learner = learner; await learner.run(); self.learner = None
                                if self.stop_flag: break
                            if not infinite: break
                            self._log("所有URL处理完成，等待5秒后重新开始循环...")
                            await asyncio.sleep(5)
                    except Exception as e:
                        self._log(f"多URL循环异常: {e}")
                    finally:
                        self._on_finish()
                asyncio.run(multi_url_runner())
            self.thread = threading.Thread(target=run_multi_url, daemon=True); self.thread.start()

        def _stop_learning(self):
            self.stop_flag = True
            if self.learner: self.learner.stop()
            self._log("已发送停止信号，请稍等...")

        def run(self):
            self.root.mainloop()

    app = NetCourseApp()
    app.run()


# ========================= 程序入口 =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="知学云（zhixueyun.com）网大课程自动化学习工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  GUI模式（默认）:     python zhixueyun_auto_study.py
  CLI模式:            python zhixueyun_auto_study.py --mode cli --url "https://kc.zhixueyun.com/#/branch-list-v/xxx"
  CLI多URL:           python zhixueyun_auto_study.py --mode cli --url "URL1" --url "URL2" --speed 1.5
  CLI无头+无限循环:    python zhixueyun_auto_study.py --mode cli --url "URL" --headless --infinite
        """)
    parser.add_argument("--mode", choices=["gui", "cli"], default="gui", help="运行模式: gui=图形界面(默认), cli=命令行")
    parser.add_argument("--url", action="append", dest="url", help="目标课程URL（cli模式必需，可多次指定）")
    parser.add_argument("--speed", type=float, default=1.5, help="视频播放倍速（默认1.5）")
    parser.add_argument("--headless", action="store_true", help="无头模式，不显示浏览器窗口")
    parser.add_argument("--max-rounds", type=int, default=10, help="每个URL最大扫描轮数（默认10）")
    parser.add_argument("--browser", choices=["chrome", "msedge"], default="chrome", help="浏览器类型（默认chrome）")
    parser.add_argument("--browser-path", default="", help="浏览器可执行文件路径（留空自动检测）")
    parser.add_argument("--user-data-dir", default="./网大浏览器数据", help="浏览器用户数据目录")
    parser.add_argument("--infinite", action="store_true", help="无限循环模式")
    args = parser.parse_args()
    if args.mode == "gui":
        run_gui()
    else:
        run_cli(args)
