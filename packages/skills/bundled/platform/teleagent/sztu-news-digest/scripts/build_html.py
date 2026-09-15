#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
深技大热点新闻 HTML 渲染脚本
读取 fetch_sztu_news.py 输出的 JSON，渲染为单文件响应式 HTML 网页。

用法:
    python build_html.py [--input sztu_news.json] [--output sztu_news.html]

网页特性:
    - 深技大主题色（深蓝 + 活力橙渐变），视觉升级：渐变 Hero + 动效卡片
    - 三栏主布局：左(关注事项 sticky) / 中(新闻主列表) / 右(数据速览)
    - 新闻列表支持 全部/校园/媒体/科研 四栏目筛选（纯前端 JS）
    - 科研动态横条（消费抓取的「科学研究」栏目）
    - 校园日历时间线板块
    - 数据可视化：行业占比环形图(conic-gradient)、栏目分布统计条
    - 快捷入口导航条
    - 下部三栏：热门行业 / 竞赛 / 在线热点
    - 成长规划全宽板块
    - 明暗主题切换 + 移动端响应式
"""

import argparse
import html
import json
from datetime import datetime

# 每日鸡汤列表
SOUPS = [
    "你今天的努力，是幸运的伏笔。",
    "不必仰望别人，自己亦是风景。",
    "与其临渊羡鱼，不如退而结网。",
    "星光不问赶路人，时光不负有心人。",
    "你只管努力，剩下的交给时间。",
    "每一个不曾起舞的日子，都是对生命的辜负。",
    "所谓万丈深渊，走下去，也是前程万里。",
    "生活明朗，万物可爱，人间值得，未来可期。",
    "愿你历尽千帆，归来仍是少年。",
    "乾坤未定，你我皆是黑马。",
    "世上无难事，只要肯放弃——开玩笑的，再坚持一下！",
    "你的气质里，藏着你走过的路和读过的书。",
    "别让平凡的生活耗尽你所有的向往。",
    "所有的不甘，都是因为还心存梦想。",
    "人生没有白走的路，每一步都算数。",
]

# 栏目颜色映射：用于卡片徽章和数据速览
COLUMN_META = {
    "campus":   {"label": "校园新闻", "cls": "tag-campus",   "rgb": "0,229,255"},
    "media":    {"label": "媒体聚焦", "cls": "tag-media",    "rgb": "255,145,0"},
    "research": {"label": "科学研究", "cls": "tag-research", "rgb": "124,77,255"},
}

# 快捷入口
QUICK_LINKS = [
    {"icon": "🏠", "name": "学校概况", "url": "https://www.sztu.edu.cn/xxgk/xxjj.htm"},
    {"icon": "🎓", "name": "本科招生", "url": "https://zs.sztu.edu.cn/"},
    {"icon": "📚", "name": "研究生院", "url": "https://gra.sztu.edu.cn/"},
    {"icon": "🧭", "name": "就业指导", "url": "https://jyzd.sztu.edu.cn/"},
    {"icon": "📖", "name": "图书馆", "url": "https://lib.sztu.edu.cn/"},
    {"icon": "🗓", "name": "学校校历", "url": "https://www.sztu.edu.cn/xxgk/xxxl/a2026___2027xnd.htm"},
    {"icon": "🌐", "name": "国际交流", "url": "https://www.sztu.edu.cn/dwjl/gjjl.htm"},
    {"icon": "🎪", "name": "活力技大", "url": "https://www.sztu.edu.cn/hljd.htm"},
]

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>深技大热点新闻 | @@date_label@@</title>
<style>
  :root {
    --rgb-cyan: 0,119,255; --rgb-blue: 0,102,255; --rgb-orange: 255,138,0;
    --rgb-pink: 255,77,104; --rgb-neon: 0,168,107; --rgb-purple: 124,77,255;
    --bg: #eef3fb; --panel: rgba(255,255,255,.85); --tint: rgba(15,45,85,.035);
    --line-soft: rgba(20,40,80,.07); --grid: rgba(0,80,255,.025);
    --cyan: #0080ff; --blue: #0066ff; --neon: #00a86b; --purple: #7c4dff;
    --orange: #ff8a00; --pink: #ff4d68;
    --text: #2c3a5e; --text-bright: #0d1b3e; --muted: #5c6b92;
    --border: rgba(var(--rgb-cyan),.14); --border-bright: rgba(var(--rgb-cyan),.38);
    --glow: 0 0 20px rgba(var(--rgb-cyan),.08); --glow-strong: 0 0 30px rgba(var(--rgb-cyan),.18);
    --hero-bg: linear-gradient(135deg, #e9f2ff 0%, #d3e5ff 50%, #e9f2ff 100%);
    --title-grad: linear-gradient(135deg, #0b5fd9 0%, #0d1b3e 55%, #0080ff 100%);
  }
  [data-theme="dark"] {
    --rgb-256: 0,229,255; --rgb-orange: 255,145,0; --rgb-pink: 255,64,129;
    --rgb-neon: 0,255,157; --rgb-purple: 124,77,255; --rgb-blue: 0,128,255;
    --bg: #060a18; --panel: rgba(15,25,50,.65); --tint: rgba(255,255,255,.02);
    --line-soft: rgba(255,255,255,.06); --grid: rgba(0,229,255,.025);
    --cyan: #00e5ff; --blue: #0080ff; --neon: #00ff9d; --purple: #7c4dff;
    --orange: #ff9100; --pink: #ff4081;
    --text: #d0e0ff; --text-bright: #ffffff; --muted: #6882a8;
    --border: rgba(var(--rgb-256),.15); --border-bright: rgba(var(--rgb-256),.35);
    --glow: 0 0 20px rgba(var(--rgb-256),.15); --glow-strong: 0 0 30px rgba(var(--rgb-256),.25);
    --hero-bg: linear-gradient(135deg, #0a1024 0%, #0d1530 50%, #0a1024 100%);
    --title-grad: linear-gradient(135deg, #00e5ff 0%, #ffffff 50%, #0080ff 100%);
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family:"PingFang SC","Microsoft YaHei","Helvetica Neue",Arial,sans-serif;
    background:var(--bg); color:var(--text); line-height:1.6; overflow-x:hidden;
    transition:background .3s,color .3s;
  }
  body::before {
    content:""; position:fixed; inset:0; z-index:0; pointer-events:none;
    background-image:
      linear-gradient(var(--grid) 1px, transparent 1px),
      linear-gradient(90deg, var(--grid) 1px, transparent 1px);
    background-size:50px 50px;
  }
  body::after {
    content:""; position:fixed; top:-20%; left:-10%; width:600px; height:600px;
    background:radial-gradient(circle, rgba(var(--rgb-blue),.06) 0%, transparent 70%);
    z-index:0; pointer-events:none; animation:drift 20s ease-in-out infinite alternate;
  }
  @keyframes drift { 0%{transform:translate(0,0);} 100%{transform:translate(100px,80px);} }

  /* ===== Hero ===== */
  header.hero {
    background:var(--hero-bg); border-bottom:1px solid var(--border-bright);
    padding:40px 24px 32px; text-align:center; position:relative; overflow:hidden; z-index:1;
  }
  header.hero::before {
    content:""; position:absolute; top:0; left:0; width:100%; height:2px;
    background:linear-gradient(90deg, transparent 0%, var(--cyan) 50%, transparent 100%);
    animation:scanline 3s ease-in-out infinite;
  }
  @keyframes scanline { 0%,100%{opacity:.3;} 50%{opacity:1;} }
  header.hero::after {
    content:""; position:absolute; bottom:-50%; right:-10%; width:400px; height:400px;
    border-radius:50%; background:radial-gradient(circle, rgba(var(--rgb-purple),.07) 0%, transparent 70%);
  }
  .hero h1 {
    font-size:clamp(24px,4.5vw,38px); font-weight:800; letter-spacing:3px;
    background:var(--title-grad); -webkit-background-clip:text; background-clip:text;
    -webkit-text-fill-color:transparent; position:relative; z-index:1;
  }
  .hero h1::after {
    content:attr(data-text); position:absolute; left:0; top:0; width:100%;
    background:linear-gradient(90deg, transparent 0%, transparent 30%, rgba(255,255,255,.5) 50%, transparent 70%, transparent 100%);
    -webkit-background-clip:text; background-clip:text; -webkit-text-fill-color:transparent;
    background-size:200% 100%; animation:titleShine 4s ease-in-out infinite;
  }
  @keyframes titleShine {
    0%   { background-position:200% 0; }
    100% { background-position:-200% 0; }
  }
  .hero .sub {
    margin-top:8px; font-size:12px; color:var(--muted);
    font-family:"SF Mono","Consolas",monospace; letter-spacing:1px; position:relative; z-index:1;
    display:flex; align-items:center; justify-content:center; gap:6px;
  }
  .hero .live-dot {
    display:inline-block; width:8px; height:8px; border-radius:50%; background:var(--neon);
    box-shadow:0 0 8px var(--neon); animation:liveBreathe 1.5s ease-in-out infinite;
    flex-shrink:0;
  }
  @keyframes liveBreathe {
    0%,100% { opacity:1; box-shadow:0 0 6px var(--neon); transform:scale(1); }
    50%      { opacity:.5; box-shadow:0 0 14px var(--neon), 0 0 24px var(--neon); transform:scale(1.3); }
  }
  .hero .stats {
    display:flex; justify-content:center; gap:clamp(16px,4vw,48px);
    margin-top:18px; position:relative; z-index:1; flex-wrap:wrap;
  }
  .hero .stat { text-align:center; position:relative; padding:6px 14px; border-radius:12px;
    background:rgba(255,255,255,.35); backdrop-filter:blur(6px); border:1px solid var(--border);
    transition:all .3s; cursor:default;
  }
  .hero .stat:hover {
    transform:translateY(-3px); border-color:var(--border-bright);
    box-shadow:0 6px 20px rgba(0,229,255,.15);
  }
  .hero .stat:hover b { transform:scale(1.15); text-shadow:0 0 20px rgba(0,229,255,.6), 0 0 40px rgba(0,229,255,.3); }
  .hero .stat b {
    display:block; font-size:26px; font-family:"SF Mono",Consolas,monospace;
    color:var(--cyan); text-shadow:0 0 12px rgba(var(--rgb-256),.4); font-weight:700;
    transition:transform .3s, text-shadow .3s;
  }
  .hero .stat span { font-size:11px; color:var(--muted); letter-spacing:1px; }

  /* ===== 主题切换 ===== */
  .theme-toggle {
    position:fixed; top:16px; right:16px; z-index:999; display:flex; align-items:center; gap:6px;
    background:var(--panel); border:1px solid var(--border-bright); border-radius:999px;
    padding:7px 14px; cursor:pointer; font-size:12px; font-weight:600; color:var(--text);
    font-family:inherit; backdrop-filter:blur(10px); box-shadow:var(--glow); transition:all .25s;
  }
  .theme-toggle:hover { transform:translateY(-1px); box-shadow:var(--glow-strong); }
  .theme-toggle .tt-icon { font-size:14px; }

  /* ===== 每日鸡汤 ===== */
  .soup-bar {
    background:linear-gradient(90deg, transparent 0%, rgba(255,145,0,.06) 30%, rgba(255,145,0,.1) 50%, rgba(255,145,0,.06) 70%, transparent 100%);
    border-bottom:1px solid rgba(255,145,0,.12); padding:11px 20px; text-align:center;
    font-size:13px; color:var(--orange); font-weight:600; letter-spacing:1px; position:relative; z-index:1;
  }
  .soup-bar .soup-inner { position:relative; display:inline-flex; align-items:center; gap:8px; }
  .soup-bar .soup-icon-wrap { position:relative; display:inline-block; }
  .soup-bar .soup-icon-wrap .soup-steam {
    position:absolute; top:-14px; left:50%; transform:translateX(-50%);
    width:20px; height:14px; pointer-events:none;
  }
  .soup-bar .soup-steam span {
    position:absolute; bottom:0; width:3px; height:3px; border-radius:50%;
    background:rgba(255,255,255,.5); opacity:0;
  }
  .soup-bar .soup-steam span:nth-child(1) { left:4px; animation:steam 2.5s ease-out infinite; }
  .soup-bar .soup-steam span:nth-child(2) { left:10px; animation:steam 2.5s ease-out infinite .8s; }
  .soup-bar .soup-steam span:nth-child(3) { left:14px; animation:steam 2.5s ease-out infinite 1.6s; }
  @keyframes steam {
    0%   { transform:translateY(0) scale(.5); opacity:0; }
    20%  { opacity:.6; }
    100% { transform:translateY(-18px) scale(1.5); opacity:0; }
  }
  .soup-bar .soup-text {
    background:linear-gradient(90deg, var(--orange) 0%, #ffc266 50%, var(--orange) 100%);
    background-size:200% 100%; -webkit-background-clip:text; background-clip:text;
    -webkit-text-fill-color:transparent; animation:soupShine 4s linear infinite;
  }
  @keyframes soupShine { 0%{background-position:0% 0;} 100%{background-position:200% 0;} }
  .soup-bar .soup-fade { transition:opacity .5s ease; }

  /* ===== 快捷入口 ===== */
  .quick-nav {
    max-width:1280px; margin:16px auto 0; padding:0 16px; position:relative; z-index:1;
  }
  .quick-grid {
    display:grid; grid-template-columns:repeat(8,1fr); gap:10px;
  }
  .quick-item {
    display:flex; flex-direction:column; align-items:center; gap:6px; padding:14px 8px;
    background:var(--panel); border:1px solid var(--border); border-radius:12px;
    text-decoration:none; color:var(--text); box-shadow:var(--glow); transition:all .25s;
    backdrop-filter:blur(12px);
  }
  .quick-item:hover {
    transform:translateY(-3px); border-color:var(--border-bright); box-shadow:var(--glow-strong);
  }
  .quick-item .q-icon {
    font-size:20px; width:40px; height:40px; border-radius:10px; display:flex;
    align-items:center; justify-content:center;
    background:linear-gradient(135deg, rgba(var(--rgb-256),.1), rgba(var(--rgb-purple),.06));
    background-size:200% 200%; animation:iconGrad 4s ease-in-out infinite;
  }
  @keyframes iconGrad {
    0%,100% { background-position:0% 0%; }
    50%      { background-position:100% 100%; }
  }
  .quick-item:hover .q-icon { animation-play-state:paused; }
  .quick-grid { position:relative; }
  .quick-grid::before {
    content:""; position:absolute; width:120px; height:120px; border-radius:50%;
    background:radial-gradient(circle, rgba(0,229,255,.08) 0%, transparent 70%);
    pointer-events:none; opacity:0; transition:opacity .2s; z-index:0;
    transform:translate(-50%,-50%); left:var(--mx,50%); top:var(--my,50%);
  }
  .quick-grid:hover::before { opacity:1; }
  .quick-item .q-title { font-size:11px; font-weight:600; color:var(--text-bright); }
  @media (max-width:900px) { .quick-grid { grid-template-columns:repeat(4,1fr); } }
  @media (max-width:480px) { .quick-grid { grid-template-columns:repeat(2,1fr); } }

  /* ===== 通用卡片 ===== */
  .container { max-width:1280px; margin:0 auto; padding:16px 16px 40px; position:relative; z-index:1; }
  .section-card {
    background:var(--panel); backdrop-filter:blur(12px); border:1px solid var(--border);
    border-radius:14px; box-shadow:var(--glow); overflow:hidden; position:relative;
    transition:border-color .3s,box-shadow .3s,background .3s;
  }
  .section-card::before {
    content:""; position:absolute; top:0; left:0; width:40px; height:2px;
    background:linear-gradient(90deg, var(--cyan), transparent);
  }
  .section-card:hover { border-color:var(--border-bright); box-shadow:var(--glow-strong); }
  .section-head { display:flex; align-items:center; gap:8px; padding:16px 18px 0; }
  .section-head h2 {
    font-size:15px; font-weight:800; color:var(--text-bright); position:relative; padding-left:14px;
  }
  .section-head h2::before {
    content:""; position:absolute; left:0; top:50%; transform:translateY(-50%);
    width:3px; height:16px; background:var(--cyan); border-radius:2px;
    box-shadow:0 0 8px rgba(0,229,255,.5);
  }
  .section-sub {
    font-size:10px; color:var(--muted); padding:0 18px 12px;
    font-family:"SF Mono",Consolas,monospace; letter-spacing:.5px;
  }
  .section-body { padding:0 18px 18px; }

  /* ===== 上部三栏 ===== */
  .main-layout { display:grid; grid-template-columns:230px 1fr 290px; gap:16px; align-items:start; }
  @media (max-width:1100px) { .main-layout { grid-template-columns:1fr; } }

  /* 左：关注事项 sticky */
  .focus-panel {
    background:var(--panel); backdrop-filter:blur(12px); border:1px solid var(--border);
    border-radius:14px; padding:18px 16px; box-shadow:var(--glow); position:sticky; top:16px;
    transition:border-color .3s;
  }
  .focus-panel:hover { border-color:var(--border-bright); }
  .focus-panel::before {
    content:""; position:absolute; top:0; left:0; width:40px; height:2px;
    background:linear-gradient(90deg, var(--orange), transparent);
  }
  .focus-panel .panel-head { display:flex; align-items:center; gap:8px; margin-bottom:2px; }
  .focus-panel .panel-head h2 {
    font-size:15px; font-weight:800; color:var(--text-bright); position:relative; padding-left:14px;
  }
  .focus-panel .panel-head h2::before {
    content:""; position:absolute; left:0; top:50%; transform:translateY(-50%);
    width:3px; height:16px; background:var(--orange); border-radius:2px;
    box-shadow:0 0 8px rgba(255,145,0,.5);
  }
  .focus-panel .panel-sub {
    font-size:10px; color:var(--muted); margin-bottom:12px;
    font-family:"SF Mono",Consolas,monospace; letter-spacing:.5px;
  }
  /* 折叠开关 */
  .focus-toggle {
    margin-left:auto; display:flex; align-items:center; gap:4px;
    background:rgba(255,145,0,.08); border:1px solid rgba(255,145,0,.15);
    color:var(--orange); font-size:10px; font-weight:600; cursor:pointer;
    padding:3px 8px; border-radius:6px; transition:all .2s; font-family:inherit;
  }
  .focus-toggle:hover { background:rgba(255,145,0,.16); border-color:rgba(255,145,0,.3); }
  .focus-toggle .ft-arrow { display:inline-block; transition:transform .25s; }
  .focus-panel.collapsed .focus-toggle .ft-arrow { transform:rotate(90deg); }
  .focus-collapsible { transition:max-height .3s ease, opacity .3s ease, margin .3s ease; overflow:hidden; }
  .focus-panel.collapsed .focus-collapse { max-height:0; opacity:0; margin:0; }
  .focus-group { margin-bottom:14px; }
  .focus-group-title {
    font-size:11px; font-weight:700; color:var(--cyan); letter-spacing:1.5px;
    margin-bottom:8px; padding-bottom:6px; border-bottom:1px solid rgba(0,229,255,.1);
    display:flex; align-items:center; gap:6px; text-transform:uppercase;
  }
  .focus-item {
    display:flex; gap:8px; padding:7px 0; border-bottom:1px solid var(--line-soft);
    align-items:flex-start; transition:padding-left .2s;
  }
  .focus-item:hover { padding-left:4px; }
  .focus-item:last-child { border-bottom:none; }
  .focus-dot {
    flex:0 0 auto; width:6px; height:6px; border-radius:50%;
    background:var(--cyan); margin-top:7px; box-shadow:0 0 6px rgba(0,229,255,.4);
  }
  .focus-item.hot .focus-dot { background:var(--orange); box-shadow:0 0 8px rgba(255,145,0,.5); }
  .focus-item .f-body { flex:1; min-width:0; }
  .focus-item .f-title { font-size:13px; font-weight:600; color:var(--text-bright); }
  .focus-item .f-desc { font-size:11px; color:var(--muted); margin-top:1px; line-height:1.4; }
  .focus-item .f-date {
    display:inline-block; margin-top:4px; font-size:9px; font-weight:700;
    color:var(--pink); background:rgba(255,64,129,.1); padding:2px 8px;
    border-radius:4px; border:1px solid rgba(255,64,129,.2); font-family:"SF Mono",Consolas,monospace;
  }
  .focus-tip {
    margin-top:12px; background:rgba(255,145,0,.06); border:1px solid rgba(255,145,0,.15);
    border-radius:8px; padding:10px 12px; font-size:11px; color:var(--orange);
    line-height:1.6; backdrop-filter:blur(6px);
  }
  .focus-item.expired { opacity:.45; filter:grayscale(.6); }
  .focus-item.expired .f-title { text-decoration:line-through; text-decoration-color:var(--muted); }
  .focus-item.expired .f-date {
    color:var(--muted); background:rgba(92,107,146,.08); border-color:rgba(92,107,146,.15);
  }
  .focus-item.expired::after {
    content:"已过期"; font-size:9px; font-weight:700; color:var(--muted);
    margin-left:6px; padding:1px 6px; border-radius:3px;
    background:rgba(92,107,146,.1); border:1px solid rgba(92,107,146,.15);
  }

  /* 中：新闻主列表 */
  .news-panel { background:var(--panel); backdrop-filter:blur(12px); border:1px solid var(--border);
    border-radius:14px; padding:16px 14px; box-shadow:var(--glow); position:relative; }
  .news-panel::before {
    content:""; position:absolute; top:0; left:0; width:40px; height:2px;
    background:linear-gradient(90deg, var(--cyan), transparent);
  }
  .news-panel .panel-head { display:flex; align-items:center; gap:8px; margin-bottom:2px; }
  .news-panel .panel-head h2 {
    font-size:15px; font-weight:800; color:var(--text-bright); position:relative; padding-left:14px;
  }
  .news-panel .panel-head h2::before {
    content:""; position:absolute; left:0; top:50%; transform:translateY(-50%);
    width:3px; height:16px; background:var(--cyan); border-radius:2px;
    box-shadow:0 0 8px rgba(0,229,255,.5);
  }
  .news-panel .panel-sub {
    font-size:10px; color:var(--muted); margin-bottom:10px;
    font-family:"SF Mono",Consolas,monospace; letter-spacing:.5px;
  }
  .filters { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:12px; }
  .filter-btn {
    border:1px solid var(--border); background:rgba(0,229,255,.04); color:var(--muted);
    padding:4px 12px; border-radius:4px; font-size:11px; cursor:pointer; transition:all .2s; font-family:inherit;
  }
  .filter-btn.active {
    background:rgba(0,229,255,.15); border-color:var(--cyan); color:var(--cyan);
    box-shadow:0 0 10px rgba(0,229,255,.2);
  }
  .filter-btn:hover { border-color:var(--cyan); color:var(--cyan); }
  .news-list { display:flex; flex-direction:column; gap:6px; }
  .news-card {
    display:flex; gap:10px; background:var(--tint); border-radius:8px; padding:10px 12px;
    border:1px solid var(--line-soft); text-decoration:none; color:inherit; transition:all .2s;
    align-items:stretch;
  }
  .news-card:hover {
    transform:translateY(-2px); border-color:var(--border-bright);
    background:rgba(0,229,255,.04); box-shadow:0 4px 16px rgba(0,229,255,.08);
  }
  .news-date {
    flex:0 0 auto; width:38px; text-align:center; padding-top:2px;
    border-right:1px solid rgba(0,229,255,.1); margin-right:4px;
  }
  .news-date .d {
    display:block; font-size:16px; font-weight:800; color:var(--cyan);
    line-height:1.1; font-family:"SF Mono",Consolas,monospace; text-shadow:0 0 6px rgba(0,229,255,.3);
  }
  .news-date .m {
    display:block; font-size:9px; color:var(--muted); font-family:"SF Mono",Consolas,monospace;
  }
  .news-body { flex:1; min-width:0; display:flex; flex-direction:column; }
  .news-meta { display:flex; gap:5px; align-items:center; flex-wrap:wrap; margin-bottom:3px; }
  .tag { font-size:9px; padding:2px 7px; border-radius:4px; font-weight:600; letter-spacing:.5px; }
  .tag-campus { background:rgba(0,229,255,.1); color:var(--cyan); border:1px solid rgba(0,229,255,.15); }
  .tag-media { background:rgba(255,145,0,.1); color:var(--orange); border:1px solid rgba(255,145,0,.15); }
  .tag-research { background:rgba(124,77,255,.12); color:var(--purple); border:1px solid rgba(124,77,255,.2); }
  .media-src {
    font-size:9px; color:var(--orange); background:rgba(255,145,0,.08);
    padding:1px 6px; border-radius:3px; border:1px solid rgba(255,145,0,.12);
  }
  .news-title { font-size:13px; font-weight:700; margin:2px 0 3px; color:var(--text-bright); }
  .news-summary {
    font-size:11px; color:var(--muted); display:-webkit-box;
    -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; line-height:1.5;
  }
  .news-link { font-size:10px; color:var(--cyan); margin-top:auto; padding-top:6px; display:inline-flex; align-items:center; gap:3px; }
  .empty { text-align:center; padding:30px 16px; color:var(--muted); }
  .empty b { font-size:14px; display:block; margin-bottom:4px; color:var(--text-bright); }

  /* 右：数据速览 */
  .stats-panel {
    background:var(--panel); backdrop-filter:blur(12px); border:1px solid var(--border);
    border-radius:14px; padding:16px 14px; box-shadow:var(--glow); position:relative;
    display:flex; flex-direction:column; gap:16px;
  }
  .stats-panel::before {
    content:""; position:absolute; top:0; left:0; width:40px; height:2px;
    background:linear-gradient(90deg, var(--purple), transparent);
  }
  .sp-title {
    font-size:12px; font-weight:800; color:var(--text-bright);
    display:flex; align-items:center; gap:6px;
  }
  .sp-title::before {
    content:""; width:3px; height:14px; background:var(--purple); border-radius:2px;
    box-shadow:0 0 8px rgba(124,77,255,.5);
  }
  .sp-sub { font-size:10px; color:var(--muted); margin-top:2px; font-family:"SF Mono",Consolas,monospace; }
  .donut-wrap { display:flex; align-items:center; gap:14px; }
  .donut {
    width:96px; height:96px; border-radius:50%; position:relative; flex:0 0 auto;
  }
  .donut::after {
    content:""; position:absolute; inset:18px; border-radius:50%;
    background:var(--panel);
  }
  .donut-center {
    position:absolute; inset:0; display:flex; flex-direction:column;
    align-items:center; justify-content:center; z-index:2;
  }
  .donut-center b { font-size:20px; color:var(--text-bright); font-family:"SF Mono",Consolas,monospace; }
  .donut-center span { font-size:9px; color:var(--muted); }
  .donut-legend { flex:1; display:flex; flex-direction:column; gap:6px; }
  .legend-item { display:flex; align-items:center; gap:6px; font-size:11px; color:var(--text); }
  .legend-dot { width:10px; height:10px; border-radius:3px; flex:0 0 auto; }
  .legend-item .l-val { margin-left:auto; font-weight:700; color:var(--text-bright); font-family:"SF Mono",Consolas,monospace; }
  .colbar { display:flex; flex-direction:column; gap:8px; }
  .colbar-row { display:flex; flex-direction:column; gap:3px; }
  .colbar-top { display:flex; justify-content:space-between; font-size:10px; color:var(--muted); }
  .colbar-top b { color:var(--text-bright); }
  .colbar-track { height:6px; background:var(--tint); border-radius:3px; overflow:hidden; }
  .colbar-fill { height:100%; border-radius:3px; }
  .quick-tip {
    padding:10px 12px; background:rgba(124,77,255,.06); border:1px solid rgba(124,77,255,.15);
    border-radius:8px; font-size:11px; color:var(--purple); line-height:1.6;
  }

  /* ===== 科研动态横条 ===== */
  .research-strip {
    margin-top:16px; display:grid; grid-template-columns:1fr 1fr 1fr; gap:12px;
  }
  .research-strip:empty { display:none; }
  @media (max-width:900px) { .research-strip { grid-template-columns:1fr 1fr; } }
  @media (max-width:600px) { .research-strip { grid-template-columns:1fr; } }
  .research-item {
    display:block; text-decoration:none; color:inherit; padding:14px;
    background:linear-gradient(135deg, rgba(124,77,255,.05), rgba(0,229,255,.03));
    border:1px solid rgba(124,77,255,.12); border-radius:10px; transition:all .25s;
  }
  .research-item:hover {
    transform:translateY(-2px); border-color:rgba(124,77,255,.3);
    box-shadow:0 6px 18px rgba(124,77,255,.1);
  }
  .research-item .r-tag {
    display:inline-block; font-size:9px; font-weight:700; color:var(--purple);
    background:rgba(124,77,255,.1); padding:2px 8px; border-radius:4px;
    border:1px solid rgba(124,77,255,.15); letter-spacing:.5px; margin-bottom:6px;
  }
  .research-item .r-title { font-size:12px; font-weight:700; color:var(--text-bright); line-height:1.5; }
  .research-item .r-date { font-size:10px; color:var(--muted); margin-top:6px; font-family:"SF Mono",Consolas,monospace; }

  /* ===== 校园日历时间线（卡片式） ===== */
  .timeline { position:relative; display:flex; gap:12px; padding:24px 0 14px; overflow-x:auto; }
  .timeline::-webkit-scrollbar { height:6px; }
  .timeline::-webkit-scrollbar-track { background:rgba(0,229,255,.04); border-radius:3px; }
  .timeline::-webkit-scrollbar-thumb { background:rgba(0,229,255,.2); border-radius:3px; }
  .timeline::before {
    content:""; position:absolute; left:12px; right:12px; top:36px; height:2px;
    background:linear-gradient(90deg, var(--cyan), var(--purple), var(--cyan));
    opacity:.4; z-index:0;
  }
  .tl-item {
    position:relative; flex:1; min-width:130px; padding:0 6px; text-align:center;
    display:flex; flex-direction:column; align-items:center; z-index:1;
  }
  .tl-item::before {
    content:""; position:absolute; left:50%; top:30px; transform:translateX(-50%);
    width:14px; height:14px; border-radius:50%; background:var(--cyan);
    border:3px solid var(--panel); box-shadow:0 0 10px rgba(0,229,255,.5); z-index:2;
  }
  .tl-item:nth-child(2n)::before { background:var(--purple); box-shadow:0 0 10px rgba(124,77,255,.5); }
  .tl-item .tl-date {
    font-size:13px; font-weight:800; color:#fff; margin-bottom:18px; padding:3px 12px;
    border-radius:999px; background:linear-gradient(135deg, var(--cyan), var(--blue));
    box-shadow:0 2px 8px rgba(0,128,255,.3); font-family:"SF Mono",Consolas,monospace;
    letter-spacing:.5px; white-space:nowrap;
  }
  .tl-item:nth-child(2n) .tl-date { background:linear-gradient(135deg, var(--purple), #a78bff); box-shadow:0 2px 8px rgba(124,77,255,.3); }
  .tl-item .tl-card {
    background:var(--tint); border:1px solid var(--border); border-radius:10px;
    padding:10px 8px; width:100%; transition:all .25s; margin-top:4px;
  }
  .tl-item:hover .tl-card {
    transform:translateY(-3px); border-color:var(--border-bright);
    background:rgba(0,229,255,.06); box-shadow:0 6px 20px rgba(0,229,255,.1);
  }
  .tl-item:nth-child(2n):hover .tl-card { background:rgba(124,77,255,.06); box-shadow:0 6px 20px rgba(124,77,255,.1); }
  .tl-item .tl-title { font-size:13px; font-weight:700; color:var(--text-bright); margin-top:0; }
  .tl-item .tl-desc { font-size:11px; color:var(--muted); line-height:1.4; margin-top:4px; }
  @media (max-width:760px) { .tl-item { min-width:110px; } }

  /* ===== 下部三栏 ===== */
  .bottom-layout { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-top:16px; align-items:stretch; }
  .bottom-layout .section-card { display:flex; flex-direction:column; }
  .bottom-layout .section-body { flex:1; }
  @media (max-width:900px) { .bottom-layout { grid-template-columns:1fr 1fr; } }
  @media (max-width:600px) { .bottom-layout { grid-template-columns:1fr; } }

  .industry-grid { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  .industry-item {
    background:linear-gradient(135deg, rgba(0,229,255,.04) 0%, rgba(0,128,255,.02) 100%);
    border:1px solid rgba(0,229,255,.1); border-radius:8px; padding:11px 12px;
    position:relative; overflow:hidden; transition:all .2s;
  }
  .industry-item:hover {
    border-color:rgba(0,229,255,.3); background:rgba(0,229,255,.06);
    box-shadow:0 0 12px rgba(0,229,255,.1);
  }
  .industry-item .rank {
    position:absolute; top:4px; right:10px; font-size:24px; font-weight:800;
    color:rgba(0,229,255,.08); line-height:1; font-family:"SF Mono",Consolas,monospace;
  }
  .industry-item .name { font-size:12px; font-weight:700; color:var(--text-bright); }
  .industry-item .desc { font-size:10px; color:var(--muted); margin-top:2px; line-height:1.4; }
  .industry-item .trend {
    display:inline-block; margin-top:6px; font-size:9px; font-weight:600;
    color:var(--neon); background:rgba(0,255,157,.08); padding:2px 8px;
    border-radius:4px; border:1px solid rgba(0,255,157,.15);
  }
  .industry-note { font-size:10px; color:var(--muted); margin-top:12px; line-height:1.5; }
  .industry-note a { color:var(--cyan); text-decoration:none; }

  .contest-list { display:flex; flex-direction:column; gap:8px; }
  .contest-item {
    border:1px solid rgba(var(--rgb-256),.1); border-radius:8px; padding:11px 14px;
    background:var(--tint); transition:all .2s; cursor:pointer;
    display:block; text-decoration:none; color:inherit;
  }
  .contest-item:hover {
    transform:translateY(-2px); border-color:var(--border-bright);
    background:rgba(0,229,255,.04); box-shadow:0 4px 16px rgba(0,229,255,.08);
  }
  .contest-item .c-link { font-size:10px; color:var(--cyan); margin-top:5px; display:inline-flex; align-items:center; gap:3px; }
  .contest-item .c-head { display:flex; align-items:center; gap:6px; margin-bottom:4px; }
  .contest-item .c-level { display:inline-block; font-size:9px; font-weight:700; letter-spacing:1px; padding:2px 8px; border-radius:4px; }
  .c-level-a { background:rgba(255,64,129,.12); color:var(--pink); border:1px solid rgba(255,64,129,.2); }
  .c-level-b { background:rgba(255,145,0,.12); color:var(--orange); border:1px solid rgba(255,145,0,.2); }
  .c-level-c { background:rgba(0,229,255,.12); color:var(--cyan); border:1px solid rgba(0,229,255,.2); }
  .contest-item .c-name { font-size:13px; font-weight:700; color:var(--text-bright); margin-bottom:2px; }
  .contest-item .c-organizer { font-size:10px; color:var(--muted); margin-bottom:6px; }
  .contest-item .c-deadline {
    display:inline-block; font-size:10px; font-weight:600; color:var(--pink);
    background:rgba(255,64,129,.08); padding:2px 8px; border-radius:4px;
    border:1px solid rgba(255,64,129,.15);
  }
  .contest-item .c-tag {
    display:inline-block; font-size:9px; font-weight:600;
    color:var(--neon); background:rgba(0,255,157,.08); padding:2px 8px;
    border-radius:4px; border:1px solid rgba(0,255,157,.15); margin-left:4px;
  }
  .contest-note { font-size:10px; color:var(--muted); margin-top:12px; line-height:1.5; }
  .contest-note a { color:var(--cyan); text-decoration:none; }
  .contest-more {
    display:flex; align-items:center; justify-content:center; gap:6px;
    width:100%; margin-top:10px; padding:8px 12px;
    background:var(--tint); border:1px solid var(--border); border-radius:8px;
    color:var(--cyan); font-size:12px; font-weight:600; cursor:pointer;
    font-family:inherit; transition:all .2s;
  }
  .contest-more:hover { border-color:var(--border-bright); background:rgba(var(--rgb-256),.06); box-shadow:0 0 10px rgba(var(--rgb-256),.1); }
  .contest-item.extra { display:none; }
  .contest-list.open .contest-item.extra { display:block; }
  .contest-item.expired { opacity:.5; filter:grayscale(.5); }
  .contest-item.expired .c-deadline {
    color:var(--muted); background:rgba(92,107,146,.08); border-color:rgba(92,107,146,.12);
  }
  .contest-item.expired .c-deadline::after { content:" · 已截止"; }

  .dxs-list { display:flex; flex-direction:column; gap:8px; }
  .dxs-item {
    display:flex; gap:10px; padding:10px 12px;
    background:rgba(0,229,255,.03); border:1px solid rgba(0,229,255,.08);
    border-radius:8px; text-decoration:none; color:inherit; transition:all .2s;
  }
  .dxs-item:hover { transform:translateX(4px); border-color:var(--border-bright); background:rgba(0,229,255,.06); box-shadow:0 0 12px rgba(0,229,255,.08); }
  .dxs-item .d-icon {
    flex:0 0 auto; width:26px; height:26px; border-radius:50%;
    background:linear-gradient(135deg, var(--cyan), var(--blue)); color:#fff;
    display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:700; box-shadow:0 0 10px rgba(0,229,255,.3);
  }
  .dxs-item .d-body { flex:1; min-width:0; }
  .dxs-item .d-title { font-size:12px; font-weight:600; color:var(--text-bright); }
  .dxs-item .d-desc { font-size:10px; color:var(--muted); margin-top:2px; line-height:1.4; }
  .dxs-item .d-date { font-size:9px; color:var(--muted); margin-top:3px; font-family:"SF Mono",Consolas,monospace; }
  .dxs-note { font-size:10px; color:var(--muted); margin-top:12px; }

  /* ===== 成长规划 ===== */
  .growth-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
  .growth-item {
    display:flex; flex-direction:column; gap:5px; padding:16px 18px;
    background:linear-gradient(135deg, rgba(0,229,255,.04) 0%, rgba(124,77,255,.03) 100%);
    border:1px solid rgba(0,229,255,.1); border-radius:10px; transition:all .25s; position:relative; overflow:hidden;
  }
  .growth-item::after {
    content:""; position:absolute; bottom:0; left:0; width:100%; height:1px;
    background:linear-gradient(90deg, transparent, var(--cyan), transparent); opacity:0; transition:opacity .3s;
  }
  .growth-item:hover { transform:translateY(-3px); border-color:var(--border-bright); box-shadow:0 8px 24px rgba(0,229,255,.1); }
  .growth-item:hover::after { opacity:1; }
  .growth-item .g-icon {
    width:34px; height:34px; border-radius:8px;
    background:linear-gradient(135deg, var(--cyan), var(--blue)); color:#fff;
    display:flex; align-items:center; justify-content:center;
    font-size:15px; font-weight:700; margin-bottom:6px; box-shadow:0 0 12px rgba(0,229,255,.25);
  }
  .growth-item .g-title { font-size:13px; font-weight:700; color:var(--text-bright); }
  .growth-item .g-desc { font-size:11px; color:var(--muted); line-height:1.5; }
  @media (max-width:760px) { .growth-grid { grid-template-columns:repeat(2,1fr); } }
  @media (max-width:480px) { .growth-grid { grid-template-columns:1fr; } }

  /* ===== 新生报到指南 ===== */
  .guide-grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  @media (max-width:760px) { .guide-grid { grid-template-columns:1fr; } }
  .guide-card {
    background:linear-gradient(135deg, rgba(0,229,255,.05) 0%, rgba(124,77,255,.03) 100%);
    border:1px solid rgba(0,229,255,.12); border-radius:12px; padding:14px 16px;
    position:relative; overflow:hidden; transition:all .25s;
  }
  .guide-card:hover { transform:translateY(-2px); border-color:var(--border-bright); box-shadow:0 6px 20px rgba(0,229,255,.1); }
  .guide-card .gc-head { display:flex; align-items:center; gap:8px; margin-bottom:10px; }
  .guide-card .gc-icon {
    width:30px; height:30px; border-radius:8px; display:flex; align-items:center; justify-content:center;
    font-size:15px; color:#fff; flex-shrink:0;
  }
  .guide-card .gc-icon.cyan { background:linear-gradient(135deg, var(--cyan), var(--blue)); box-shadow:0 0 10px rgba(0,229,255,.3); }
  .guide-card .gc-icon.orange { background:linear-gradient(135deg, var(--orange), #ffb347); box-shadow:0 0 10px rgba(255,145,0,.3); }
  .guide-card .gc-icon.purple { background:linear-gradient(135deg, var(--purple), #a78bff); box-shadow:0 0 10px rgba(124,77,255,.3); }
  .guide-card .gc-icon.pink { background:linear-gradient(135deg, var(--pink), #ff7a9c); box-shadow:0 0 10px rgba(255,77,104,.3); }
  .guide-card .gc-title { font-size:13px; font-weight:800; color:var(--text-bright); }
  .guide-card .gc-badge {
    font-size:9px; font-weight:700; padding:2px 8px; border-radius:4px; margin-left:auto;
    color:var(--pink); background:rgba(255,77,104,.1); border:1px solid rgba(255,77,104,.15); white-space:nowrap;
  }
  .guide-card .gc-badge.done { color:var(--neon); background:rgba(0,168,107,.1); border-color:rgba(0,168,107,.15); }
  .guide-card .gc-list { list-style:none; padding:0; margin:0; }
  .guide-card .gc-list li {
    font-size:11px; color:var(--text); line-height:1.6; padding:4px 0 4px 16px;
    position:relative; border-bottom:1px solid rgba(0,229,255,.06);
  }
  .guide-card .gc-list li:last-child { border-bottom:none; }
  .guide-card .gc-list li::before {
    content:""; position:absolute; left:4px; top:12px; width:4px; height:4px;
    border-radius:50%; background:var(--cyan); opacity:.6;
  }
  .guide-card .gc-list li b { color:var(--text-bright); font-weight:700; }
  .guide-card .gc-link {
    display:inline-block; margin-top:8px; font-size:10px; font-weight:600;
    color:var(--cyan); text-decoration:none; padding:3px 10px; border-radius:4px;
    background:rgba(0,229,255,.06); border:1px solid rgba(0,229,255,.12);
  }
  .guide-card .gc-link:hover { background:rgba(0,229,255,.12); }
  .guide-card .gc-note {
    font-size:10px; color:var(--pink); margin-top:8px; padding:6px 10px;
    background:rgba(255,77,104,.06); border-radius:6px; border:1px solid rgba(255,77,104,.1);
    line-height:1.5;
  }
  .guide-steps { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:12px; }
  .guide-step {
    flex:1; min-width:80px; text-align:center; padding:8px 6px;
    background:rgba(0,229,255,.04); border:1px solid rgba(0,229,255,.1); border-radius:8px;
    position:relative; transition:all .2s;
  }
  .guide-step:hover { background:rgba(0,229,255,.08); border-color:var(--border-bright); }
  .guide-step .gs-num {
    font-size:18px; font-weight:800; color:var(--cyan); font-family:"SF Mono",Consolas,monospace;
  }
  .guide-step .gs-label { font-size:10px; color:var(--text); margin-top:2px; }
  .faq-list { display:flex; flex-direction:column; gap:8px; }
  .faq-item {
    background:rgba(0,229,255,.03); border:1px solid rgba(0,229,255,.08); border-radius:8px;
    padding:10px 12px; transition:all .2s;
  }
  .faq-item:hover { border-color:var(--border-bright); background:rgba(0,229,255,.06); }
  .faq-item .faq-q { font-size:12px; font-weight:700; color:var(--text-bright); margin-bottom:4px; display:flex; align-items:center; gap:6px; }
  .faq-item .faq-q::before { content:"Q"; font-size:9px; font-weight:800; color:#fff; background:var(--cyan); border-radius:3px; padding:1px 5px; flex-shrink:0; }
  .faq-item .faq-a { font-size:11px; color:var(--muted); line-height:1.6; padding-left:22px; }
  .contact-bar {
    display:flex; gap:10px; flex-wrap:wrap; margin-top:14px; padding:12px 14px;
    background:rgba(124,77,255,.04); border:1px solid rgba(124,77,255,.1); border-radius:10px;
  }
  .contact-item { display:flex; align-items:center; gap:6px; font-size:11px; color:var(--text); }
  .contact-item b { color:var(--text-bright); font-weight:700; }
  .contact-item .c-tel {
    font-family:"SF Mono",Consolas,monospace; font-weight:700; color:var(--purple);
    background:rgba(124,77,255,.08); padding:1px 8px; border-radius:4px; border:1px solid rgba(124,77,255,.12);
  }

  footer { text-align:center; font-size:11px; color:var(--muted); padding:20px; border-top:1px solid var(--border); margin-top:20px; position:relative; z-index:1; font-family:"SF Mono",Consolas,monospace; letter-spacing:.5px; }

  /* 页面渐入动画 */
  .fade-in { opacity:0; transform:translateY(14px); animation:fadeUp .5s ease forwards; }
  @keyframes fadeUp { to { opacity:1; transform:translateY(0); } }

  /* ===== Hero 粒子动效（彩虹色 30 粒子） ===== */
  .particles { position:absolute; inset:0; overflow:hidden; pointer-events:none; z-index:0; }
  .particle {
    position:absolute; bottom:0; border-radius:50%; opacity:0; animation:floatUp linear infinite;
    box-shadow:0 0 6px currentColor;
  }
  /* 彩虹七色循环：红橙黄绿青蓝紫 */
  .particle:nth-child(7n+1) { background:#ff4d68; color:#ff4d68; }
  .particle:nth-child(7n+2) { background:#ff8a00; color:#ff8a00; }
  .particle:nth-child(7n+3) { background:#ffd700; color:#ffd700; }
  .particle:nth-child(7n+4) { background:#00a86b; color:#00a86b; }
  .particle:nth-child(7n+5) { background:#0080ff; color:#0080ff; }
  .particle:nth-child(7n+6) { background:#00d4ff; color:#00d4ff; }
  .particle:nth-child(7n+7) { background:#7c4dff; color:#7c4dff; }
  /* 30 个粒子：位置/大小/速度/延迟各不同 */
  .particle:nth-child(1)  { left:3%;  width:3px; height:3px; animation-duration:8s;  animation-delay:0s;   }
  .particle:nth-child(2)  { left:7%;  width:5px; height:5px; animation-duration:12s; animation-delay:1s;   }
  .particle:nth-child(3)  { left:11%; width:2px; height:2px; animation-duration:10s; animation-delay:2s;   }
  .particle:nth-child(4)  { left:15%; width:4px; height:4px; animation-duration:14s; animation-delay:.5s;  }
  .particle:nth-child(5)  { left:19%; width:3px; height:3px; animation-duration:9s;  animation-delay:3s;   }
  .particle:nth-child(6)  { left:23%; width:5px; height:5px; animation-duration:11s; animation-delay:1.5s; }
  .particle:nth-child(7)  { left:27%; width:2px; height:2px; animation-duration:13s; animation-delay:.8s;  }
  .particle:nth-child(8)  { left:31%; width:4px; height:4px; animation-duration:10s; animation-delay:2.5s; }
  .particle:nth-child(9)  { left:35%; width:3px; height:3px; animation-duration:15s; animation-delay:1.2s; }
  .particle:nth-child(10) { left:39%; width:5px; height:5px; animation-duration:9s;  animation-delay:3.5s; }
  .particle:nth-child(11) { left:43%; width:2px; height:2px; animation-duration:11s; animation-delay:.3s;  }
  .particle:nth-child(12) { left:47%; width:4px; height:4px; animation-duration:13s; animation-delay:2.2s; }
  .particle:nth-child(13) { left:51%; width:3px; height:3px; animation-duration:8s;  animation-delay:1.8s; }
  .particle:nth-child(14) { left:55%; width:5px; height:5px; animation-duration:14s; animation-delay:.6s;  }
  .particle:nth-child(15) { left:59%; width:2px; height:2px; animation-duration:10s; animation-delay:3.2s; }
  .particle:nth-child(16) { left:63%; width:4px; height:4px; animation-duration:12s; animation-delay:1.1s; }
  .particle:nth-child(17) { left:67%; width:3px; height:3px; animation-duration:9s;  animation-delay:2.8s; }
  .particle:nth-child(18) { left:71%; width:5px; height:5px; animation-duration:11s; animation-delay:.4s;  }
  .particle:nth-child(19) { left:75%; width:2px; height:2px; animation-duration:15s; animation-delay:1.7s; }
  .particle:nth-child(20) { left:79%; width:4px; height:4px; animation-duration:10s; animation-delay:3.8s; }
  .particle:nth-child(21) { left:83%; width:3px; height:3px; animation-duration:13s; animation-delay:.9s;  }
  .particle:nth-child(22) { left:87%; width:5px; height:5px; animation-duration:9s;  animation-delay:2.5s;  }
  .particle:nth-child(23) { left:91%; width:2px; height:2px; animation-duration:11s; animation-delay:1.3s; }
  .particle:nth-child(24) { left:95%; width:4px; height:4px; animation-duration:14s; animation-delay:3.6s; }
  .particle:nth-child(25) { left:6%;  width:3px; height:3px; animation-duration:10s; animation-delay:4.2s; }
  .particle:nth-child(26) { left:42%; width:5px; height:5px; animation-duration:12s; animation-delay:4.5s; }
  .particle:nth-child(27) { left:62%; width:2px; height:2px; animation-duration:8s;  animation-delay:4.8s;  }
  .particle:nth-child(28) { left:78%; width:4px; height:4px; animation-duration:15s; animation-delay:5.1s; }
  .particle:nth-child(29) { left:18%; width:3px; height:3px; animation-duration:11s; animation-delay:5.4s; }
  .particle:nth-child(30) { left:88%; width:5px; height:5px; animation-duration:13s; animation-delay:5.7s; }
  @keyframes floatUp {
    0%   { transform:translateY(0) scale(1); opacity:0; }
    8%   { opacity:.7; }
    85%  { opacity:.4; }
    100% { transform:translateY(-200px) scale(.3); opacity:0; }
  }

  /* ===== 新闻日期块 hover 脉冲 ===== */
  .news-card:hover .news-date .d { animation:pulseGlow .6s ease infinite alternate; }
  @keyframes pulseGlow {
    from { text-shadow:0 0 6px rgba(0,229,255,.3); }
    to   { text-shadow:0 0 16px rgba(0,229,255,.6), 0 0 24px rgba(0,229,255,.3); }
  }

  /* ===== 环形图旋转入场 ===== */
  .donut { animation:donutSpin .8s cubic-bezier(.4,.2,.2,1) forwards; }
  @keyframes donutSpin {
    from { transform:rotate(-90deg) scale(.6); opacity:0; }
    to   { transform:rotate(0) scale(1); opacity:1; }
  }

  /* ===== 快捷入口 hover 图标弹跳 ===== */
  .quick-item:hover .q-icon { animation:iconBounce .5s ease; }
  @keyframes iconBounce {
    0%   { transform:scale(1); }
    30%  { transform:scale(1.25) rotate(-8deg); }
    50%  { transform:scale(.95) rotate(4deg); }
    70%  { transform:scale(1.1) rotate(-2deg); }
    100% { transform:scale(1) rotate(0); }
  }

  /* ===== 成长规划错落入场 ===== */
  .growth-item { opacity:0; transform:translateY(20px); animation:growIn .5s ease forwards; }
  .growth-item:nth-child(1) { animation-delay:.1s; }
  .growth-item:nth-child(2) { animation-delay:.2s; }
  .growth-item:nth-child(3) { animation-delay:.3s; }
  .growth-item:nth-child(4) { animation-delay:.4s; }
  @keyframes growIn { to { opacity:1; transform:translateY(0); } }

  /* ===== 返回顶部按钮 ===== */
  .back-top {
    position:fixed; bottom:24px; right:24px; z-index:999;
    width:40px; height:40px; border-radius:50%; border:1px solid var(--border-bright);
    background:var(--panel); backdrop-filter:blur(10px); box-shadow:var(--glow);
    color:var(--cyan); font-size:18px; cursor:pointer; display:flex;
    align-items:center; justify-content:center; transition:all .25s;
    opacity:0; pointer-events:none; transform:translateY(10px);
  }
  .back-top.show { opacity:1; pointer-events:auto; transform:translateY(0); }
  .back-top:hover { box-shadow:var(--glow-strong); transform:translateY(-3px); }

  /* ===== 动效1：顶部加载进度条 ===== */
  .load-bar {
    position:fixed; top:0; left:0; height:3px; width:0%; z-index:9999;
    background:linear-gradient(90deg, var(--cyan), var(--purple), var(--cyan));
    background-size:200% 100%; box-shadow:0 0 10px rgba(0,229,255,.6);
    animation:loadFill 1.2s ease-out forwards, loadShimmer 1s linear infinite;
  }
  @keyframes loadFill { 0%{width:0%;} 60%{width:80%;} 80%{width:92%;} 100%{width:100%;} }
  @keyframes loadShimmer { 0%{background-position:0% 0;} 100%{background-position:200% 0;} }
  .load-bar.done { opacity:0; transition:opacity .4s; }

  /* ===== 动效2：背景数字雨 ===== */
  .digital-rain {
    position:fixed; inset:0; z-index:0; pointer-events:none; overflow:hidden; opacity:.25;
  }
  .rain-col {
    position:absolute; top:-100%; font-family:"SF Mono",Consolas,monospace;
    font-size:11px; line-height:1.3; color:var(--cyan);
    writing-mode:vertical-rl; text-orientation:upright;
    white-space:nowrap; animation:rainFall linear infinite;
  }
  @keyframes rainFall { 0%{transform:translateY(0);} 100%{transform:translateY(200vh);} }

  /* ===== 动效3：标题竖线生长 ===== */
  .section-head h2::before, .focus-panel .panel-head h2::before, .news-panel .panel-head h2::before, .stats-panel .sp-title::before {
    animation:barGrow .6s ease forwards;
  }
  @keyframes barGrow { 0%{height:0; opacity:0;} 100%{opacity:1;} }

  /* ===== 动效4：卡片光边扫描 ===== */
  .section-card, .news-card, .contest-item, .dxs-item, .industry-item, .growth-item, .research-item, .quick-item {
    position:relative; overflow:hidden;
  }
  .section-card::after, .news-card::after, .contest-item::after, .dxs-item::after, .industry-item::after, .growth-item::after, .research-item::after, .quick-item::after {
    content:""; position:absolute; top:0; left:-60%; width:60%; height:100%;
    background:linear-gradient(120deg, transparent 0%, rgba(0,229,255,.08) 45%, rgba(0,229,255,.15) 50%, rgba(0,229,255,.08) 55%, transparent 100%);
    pointer-events:none; opacity:0; transition:none;
  }
  .section-card:hover::after, .news-card:hover::after, .contest-item:hover::after, .dxs-item:hover::after, .industry-item:hover::after, .growth-item:hover::after, .research-item:hover::after, .quick-item:hover::after {
    animation:cardScan .7s ease;
  }
  @keyframes cardScan {
    0%   { left:-60%; opacity:0; }
    20%  { opacity:1; }
    100% { left:120%; opacity:0; }
  }

  /* ===== 动效5：新闻卡片滚动入场 ===== */
  .news-card {
    opacity:0; transform:translateY(20px);
    transition:opacity .5s ease, transform .5s ease, border-color .2s, background .2s, box-shadow .2s;
  }
  .news-card.visible { opacity:1; transform:translateY(0); }

  /* ===== 动效6：时间线节点脉冲 ===== */
  .tl-item::before {
    animation:tlPulse 2s ease-in-out infinite;
  }
  .tl-item:nth-child(2n)::before { animation-delay:.5s; }
  .tl-item:nth-child(3n)::before { animation-delay:1s; }
  .tl-item:nth-child(4n)::before { animation-delay:1.5s; }
  .tl-item:nth-child(5n)::before { animation-delay:.3s; }
  @keyframes tlPulse {
    0%,100% { box-shadow:0 0 4px rgba(0,229,255,.3); transform:translateX(-50%) scale(1); }
    50%      { box-shadow:0 0 14px rgba(0,229,255,.7), 0 0 24px rgba(0,229,255,.3); transform:translateX(-50%) scale(1.3); }
  }

  /* ===== 动效7：打字机光标 ===== */
  .hero .sub .cursor {
    display:inline-block; width:2px; height:14px; background:var(--cyan);
    margin-left:2px; vertical-align:middle; animation:cursorBlink .8s steps(2) infinite;
  }
  @keyframes cursorBlink { 0%,100%{opacity:1;} 50%{opacity:0;} }
</style>
</head>
<body>
<div class="load-bar" id="loadBar"></div>
<div class="digital-rain" id="digitalRain"></div>
<button class="theme-toggle" id="themeToggle" aria-label="切换明暗主题">
  <span class="tt-icon">🌙</span>
  <span class="tt-label" id="themeLabel">暗黑模式</span>
</button>
<header class="hero">
  <div class="particles">
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
    <span class="particle"></span><span class="particle"></span><span class="particle"></span>
  </div>
  <h1 data-text="深圳技术大学 · 校园资讯中枢">深圳技术大学 · 校园资讯中枢</h1>
  <div class="sub" id="heroSub" data-text="数据来源：官网「技大焦点」+「科研实训」栏目 · @@date_label@@"><span class="live-dot"></span></div>
  <div class="stats">
    <div class="stat"><b class="count" data-target="@@total@@">0</b><span>条新闻</span></div>
    <div class="stat"><b class="count" data-target="@@window@@">0</b><span>天时间窗口</span></div>
    <div class="stat"><b class="count" data-target="@@campus@@">0</b><span>校园新闻</span></div>
    <div class="stat"><b class="count" data-target="@@media@@">0</b><span>媒体聚焦</span></div>
    <div class="stat"><b class="count" data-target="@@research@@">0</b><span>科学研究</span></div>
  </div>
</header>
<div class="soup-bar">
  <div class="soup-inner">
    <span class="soup-icon-wrap">&#9749;<span class="soup-steam"><span></span><span></span><span></span></span></span>
    <span>每日鸡汤：</span><span class="soup-text soup-fade" id="soupText">@@soup_text@@</span>
  </div>
</div>

<!-- 快捷入口 -->
<div class="quick-nav">
  <div class="quick-grid">
    @@quick_links@@
  </div>
</div>

<div class="container">

  <!-- ========== 校园日历时间线 ========== -->
  <div class="section-card fade-in" style="animation-delay:.05s">
    <div class="section-head"><h2>校园日历 · 关键节点</h2></div>
    <div class="section-sub">开学季重要时间线 · 供提前规划</div>
    <div class="section-body">
      <div class="timeline">
        <div class="tl-item"><div class="tl-date">8/21-8/28</div><div class="tl-card"><div class="tl-title">学宿费缴纳</div><div class="tl-desc">逾期注册失效</div></div></div>
        <div class="tl-item"><div class="tl-date">8/29</div><div class="tl-card"><div class="tl-title">老生报到注册</div><div class="tl-desc">未注册取消选课</div></div></div>
        <div class="tl-item"><div class="tl-date">8/30</div><div class="tl-card"><div class="tl-title">新生报到</div><div class="tl-desc">D2 体育馆二楼</div></div></div>
        <div class="tl-item"><div class="tl-date">8/31</div><div class="tl-card"><div class="tl-title">第二轮选课确认</div><div class="tl-desc">先到先得</div></div></div>
        <div class="tl-item"><div class="tl-date">9/4-9/13</div><div class="tl-card"><div class="tl-title">重修与第三轮补选</div><div class="tl-desc">重修4-7日，补选8-13日</div></div></div>
      </div>
    </div>
  </div>

  <!-- ========== 上部三栏 ========== -->
  <div class="main-layout">

    <!-- 左：关注事项 -->
    <div class="focus-panel fade-in" style="animation-delay:.05s">
      <div class="panel-head"><h2>关注事项</h2><button class="focus-toggle" id="focusToggle" aria-expanded="true" title="折叠/展开"><span class="ft-arrow">◀</span><span class="ft-text">收起</span></button></div>
      <div class="panel-sub">近期校园关键安排</div>
      <div class="focus-collapsible focus-collapse">
      <div class="focus-group">
        <div class="focus-group-title">开学季 · 近期安排</div>
        <div class="focus-item hot" data-deadline="2026-08-28">
          <span class="focus-dot"></span>
          <div class="f-body">
            <div class="f-title">学宿费缴纳</div>
            <div class="f-desc">逾期未缴注册失效</div>
            <span class="f-date">8/21-8/28</span>
          </div>
        </div>
        <div class="focus-item hot" data-deadline="2026-08-29">
          <span class="focus-dot"></span>
          <div class="f-body">
            <div class="f-title">老生返校报到注册</div>
            <div class="f-desc">未注册取消选课资格</div>
            <span class="f-date">8/29</span>
          </div>
        </div>
        <div class="focus-item hot" data-deadline="2026-08-30">
          <span class="focus-dot"></span>
          <div class="f-body">
            <div class="f-title">新生报到</div>
            <div class="f-desc">D2 体育馆二楼</div>
            <span class="f-date">8/30</span>
          </div>
        </div>
        <div class="focus-item hot" data-deadline="2026-08-31">
          <span class="focus-dot"></span>
          <div class="f-body">
            <div class="f-title">第二轮选课确认（抢选）</div>
            <div class="f-desc">先到先得</div>
            <span class="f-date">8/31 13:00</span>
          </div>
        </div>
        <div class="focus-item" data-deadline="2026-09-13">
          <span class="focus-dot"></span>
          <div class="f-body">
            <div class="f-title">重修选课 / 第三轮补选</div>
            <div class="f-desc">重修 9/4-9/7，补选 9/8-9/13</div>
            <span class="f-date">9月上旬</span>
          </div>
        </div>
      </div>
      <div class="focus-tip">
        &#128161; 以上以学校官方通知为准。<br>教材费 8/27 截止、学费 8/28 截止！
      </div>
      </div><!-- /.focus-collapsible -->
    </div>

    <!-- 中：新闻主列表 -->
    <div class="news-panel fade-in" style="animation-delay:.1s">
      <div class="panel-head"><h2>深技大新闻</h2></div>
      <div class="panel-sub">官网「技大焦点」+「科研实训」栏目 · 点击卡片跳转原文</div>
      <div class="filters">
        <button class="filter-btn active" data-filter="all">全部</button>
        <button class="filter-btn" data-filter="campus">校园</button>
        <button class="filter-btn" data-filter="media">媒体</button>
        <button class="filter-btn" data-filter="research">科研</button>
      </div>
      <div class="news-list" id="newsList">
        @@cards@@
      </div>
    </div>

    <!-- 右：数据速览 -->
    <div class="stats-panel fade-in" style="animation-delay:.15s">
      <div>
        <div class="sp-title">新闻栏目分布</div>
        <div class="sp-sub">数据实时统计</div>
        <div class="donut-wrap" style="margin-top:14px">
          <div class="donut" style="background:conic-gradient(@@donut_bg@@)">
            <div class="donut-center"><b>@@total@@</b><span>条</span></div>
          </div>
          <div class="donut-legend">
            <div class="legend-item"><span class="legend-dot" style="background:var(--cyan)"></span>校园新闻<span class="l-val">@@campus@@</span></div>
            <div class="legend-item"><span class="legend-dot" style="background:var(--orange)"></span>媒体聚焦<span class="l-val">@@media@@</span></div>
            <div class="legend-item"><span class="legend-dot" style="background:var(--purple)"></span>科学研究<span class="l-val">@@research@@</span></div>
          </div>
        </div>
      </div>
      <div>
        <div class="sp-title">栏目占比</div>
        <div class="colbar" style="margin-top:10px">
          <div class="colbar-row">
            <div class="colbar-top"><span>校园新闻</span><b>@@campus_pct@@%</b></div>
            <div class="colbar-track"><div class="colbar-fill" style="width:@@campus_pct@@%;background:var(--cyan)"></div></div>
          </div>
          <div class="colbar-row">
            <div class="colbar-top"><span>媒体聚焦</span><b>@@media_pct@@%</b></div>
            <div class="colbar-track"><div class="colbar-fill" style="width:@@media_pct@@%;background:var(--orange)"></div></div>
          </div>
          <div class="colbar-row">
            <div class="colbar-top"><span>科学研究</span><b>@@research_pct@@%</b></div>
            <div class="colbar-track"><div class="colbar-fill" style="width:@@research_pct@@%;background:var(--purple)"></div></div>
          </div>
        </div>
      </div>
      <div class="quick-tip">
        💡 热门方向 · 人工智能/大数据、智能制造、半导体、新能源，对接深圳「20+8」产业，均为深技大优势学科方向。
      </div>
    </div>

  </div><!-- /.main-layout -->

  <!-- ========== 科研动态横条 ========== -->
  <div class="research-strip">
    @@research_cards@@
  </div>

  <!-- ========== 下部三栏 ========== -->
  <div class="bottom-layout">

    <!-- 热门行业 -->
    <div class="section-card">
      <div class="section-head"><h2>近三年毕业生热门行业</h2></div>
      <div class="section-sub">2023-2025 届主要就业方向 · 公开信息整理</div>
      <div class="section-body">
        <div class="industry-grid">
          <div class="industry-item"><span class="rank">01</span><div class="name">信息技术 / 软件服务</div><div class="desc">华为/腾讯等龙头录用</div><span class="trend">长期热门</span></div>
          <div class="industry-item"><span class="rank">02</span><div class="name">智能制造 / 先进制造</div><div class="desc">对接深圳「20+8」产业</div><span class="trend">持续升温</span></div>
          <div class="industry-item"><span class="rank">03</span><div class="name">半导体 / 集成电路</div><div class="desc">国产替代赛道</div><span class="trend">高速增长</span></div>
          <div class="industry-item"><span class="rank">04</span><div class="name">新能源 / 智能汽车</div><div class="desc">比亚迪等龙头</div><span class="trend">高速增长</span></div>
          <div class="industry-item"><span class="rank">05</span><div class="name">人工智能 / 大数据</div><div class="desc">AI 精英班产教融合</div><span class="trend">高速增长</span></div>
          <div class="industry-item"><span class="rank">06</span><div class="name">生物医药 / 医疗器械</div><div class="desc">医工交叉方向</div><span class="trend">新兴热门</span></div>
        </div>
        <div class="industry-note">
          * 来源：学校就业公开报道（去向落实率 92%→97%，留深率约 80%），具体以就业质量报告为准。<br>最后更新：@@update_date@@
        </div>
      </div>
    </div>

    <!-- 竞赛 -->
    <div class="section-card">
      <div class="section-head"><h2>大学生高含金量竞赛</h2></div>
      <div class="section-sub">2026 年重点竞赛 · 我爱竞赛网榜单整理</div>
      <div class="section-body">
        <div class="contest-list">
          <a class="contest-item" href="https://cy.ncss.cn/" target="_blank" rel="noopener" data-deadline="2026-09-25">
            <div class="c-head"><span class="c-level c-level-a">A 级</span></div>
            <div class="c-name">中国国际大学生创新大赛</div>
            <div class="c-organizer">教育部 · 原"互联网+"大赛</div>
            <span class="c-deadline">报名截止 9/25</span>
            <span class="c-tag">含金量极高</span>
            <div class="c-link">官网报名 →</div>
          </a>
          <a class="contest-item" href="https://www.mcm.edu.cn/" target="_blank" rel="noopener" data-deadline="2026-11-30">
            <div class="c-head"><span class="c-level c-level-a">A 级</span></div>
            <div class="c-name">高教社杯数学建模竞赛</div>
            <div class="c-organizer">中国工业与应用数学学会</div>
            <span class="c-deadline">报名截止 11月</span>
            <span class="c-tag">保研加分</span>
            <div class="c-link">官网报名 →</div>
          </a>
          <a class="contest-item" href="http://jsjds.blcu.edu.cn/" target="_blank" rel="noopener">
            <div class="c-head"><span class="c-level c-level-a">A 级</span></div>
            <div class="c-name">中国大学生计算机设计大赛</div>
            <div class="c-organizer">教育部计算机类教指委</div>
            <span class="c-tag">保研加分</span>
            <div class="c-link">官网报名 →</div>
          </a>
          <a class="contest-item" href="https://www.52jingsai.com/" target="_blank" rel="noopener" data-deadline="2026-09-18">
            <div class="c-head"><span class="c-level c-level-b">B 级</span></div>
            <div class="c-name">外文奖英语词汇大赛</div>
            <div class="c-organizer">中国外文局</div>
            <span class="c-deadline">报名截止 9/18</span>
            <div class="c-link">官网报名 →</div>
          </a>
          <a class="contest-item extra" href="https://www.cecmath.com/" target="_blank" rel="noopener">
            <div class="c-head"><span class="c-level c-level-b">B 级</span></div>
            <div class="c-name">华教杯全国大学生数学竞赛</div>
            <div class="c-organizer">华教杯组委会</div>
            <div class="c-link">官网报名 →</div>
          </a>
          <a class="contest-item extra" href="http://nciecc.com/" target="_blank" rel="noopener">
            <div class="c-head"><span class="c-level c-level-c">C 级</span></div>
            <div class="c-name">全国高校英语挑战赛</div>
            <div class="c-organizer">全国高等教育英语教研中心</div>
            <div class="c-link">官网报名 →</div>
          </a>
        </div>
        <button class="contest-more" id="contestMore" aria-expanded="false">
          <span class="cm-text">展开全部竞赛</span>
          <span class="cm-arrow">▾</span>
        </button>
        <div class="contest-note">
          * 来源：我爱竞赛网（52jingsai.com）2026 榜单。截止日期以各竞赛官网为准。<br>最后更新：@@update_date@@
        </div>
      </div>
    </div>

    <!-- 在线热点 -->
    <div class="section-card">
      <div class="section-head"><h2>大学生在线 · 热点</h2></div>
      <div class="section-sub">教育部主管平台 dxs.moe.gov.cn</div>
      <div class="section-body">
        <div class="dxs-list">
          <a class="dxs-item" href="https://dxs.moe.gov.cn/zx/hd/" target="_blank" rel="noopener">
            <div class="d-icon">热</div>
            <div class="d-body"><div class="d-title">2026 高教社杯数学建模竞赛第一次通知</div><div class="d-desc">竞赛时间、AI 工具使用规定等已发布</div><div class="d-date">2026-08-07</div></div>
          </a>
          <a class="dxs-item" href="https://dxs.moe.gov.cn/zx/hd/" target="_blank" rel="noopener">
            <div class="d-icon">新</div>
            <div class="d-body"><div class="d-title">数学建模 AI 工具使用规定（2026 试行版）</div><div class="d-desc">首次允许大模型辅助建模，规范使用条件</div><div class="d-date">2026-08</div></div>
          </a>
          <a class="dxs-item" href="https://dxs.moe.gov.cn/zx/hd/" target="_blank" rel="noopener">
            <div class="d-icon">活</div>
            <div class="d-body"><div class="d-title">「小我融入大我」大学生暑期社会实践</div><div class="d-desc">全国范围开展，深入基层服务社会</div><div class="d-date">2026-07</div></div>
          </a>
          <a class="dxs-item" href="https://dxs.moe.gov.cn/zx/hd/" target="_blank" rel="noopener">
            <div class="d-icon">展</div>
            <div class="d-body"><div class="d-title">全国大学生讲解员展示活动</div><div class="d-desc">面向全国高校选拔优秀大学生讲解员</div><div class="d-date">2026-07</div></div>
          </a>
          <a class="dxs-item" href="https://dxs.moe.gov.cn/zx/hd/" target="_blank" rel="noopener">
            <div class="d-icon">答</div>
            <div class="d-body"><div class="d-title">全国大学生国家安全知识答题活动</div><div class="d-desc">线上答题形式，增强国家安全意识</div><div class="d-date">2026-08</div></div>
          </a>
        </div>
        <div class="dxs-note">* 来源：中国大学生在线（dxs.moe.gov.cn），以官方网站为准。<br>最后更新：@@update_date@@</div>
      </div>
    </div>

  </div><!-- /.bottom-layout -->

  <!-- ========== 成长规划（全宽） ========== -->
  <div class="section-card" style="margin-top:16px">
    <div class="section-head"><h2>成长 · 学业与规划</h2></div>
    <div class="section-sub">通用成长指南 · 助力大学四年稳步前行</div>
    <div class="section-body">
      <div class="growth-grid">
        <div class="growth-item"><div class="g-icon">考</div><div class="g-title">四六级 / 证书考试</div><div class="g-desc">9月关注 CET 报名，提前规划备考节奏</div></div>
        <div class="growth-item"><div class="g-icon">奖</div><div class="g-title">奖学金 / 评优评先</div><div class="g-desc">开学后留意学院通知，学业+综测两手抓</div></div>
        <div class="growth-item"><div class="g-icon">习</div><div class="g-title">实习 / 校招提前批</div><div class="g-desc">大三大四关注双选会，打磨简历作品集</div></div>
        <div class="growth-item"><div class="g-icon">研</div><div class="g-title">考研 / 升学规划</div><div class="g-desc">大三启动目标院校与专业课复习</div></div>
      </div>
    </div>
  </div>

  <!-- ========== 新生报到指南 ========== -->
  <div class="section-card fade-in" style="margin-top:16px; animation-delay:.05s">
    <div class="section-head"><h2>新生报到指南 · 2026 级</h2></div>
    <div class="section-sub">来源：深圳技术大学公众号 · 2026 级新生报到指南</div>
    <div class="section-body">

      <!-- 报到流程 5 步 -->
      <div class="guide-steps">
        <div class="guide-step"><div class="gs-num">01</div><div class="gs-label">学院注册</div></div>
        <div class="guide-step"><div class="gs-num">02</div><div class="gs-label">绿色通道</div></div>
        <div class="guide-step"><div class="gs-num">03</div><div class="gs-label">学生部窗口</div></div>
        <div class="guide-step"><div class="gs-num">04</div><div class="gs-label">咨询区</div></div>
        <div class="guide-step"><div class="gs-num">05</div><div class="gs-label">入住宿舍</div></div>
      </div>

      <!-- 双栏内容 -->
      <div class="guide-grid">

        <!-- 线上注册 -->
        <div class="guide-card">
          <div class="gc-head">
            <div class="gc-icon cyan">🖥</div>
            <div class="gc-title">线上注册（开学前必做）</div>
            <span class="gc-badge" data-deadline="2026-08-30">截止 8/30</span>
          </div>
          <ul class="gc-list">
            <li>登录<b>迎新服务网</b>，用户名为身份证号，密码为 <b>sztu@身份证后六位</b>（X 结尾大写）</li>
            <li><b>新生入学问卷调查</b> — 涵盖学校认知、职业规划、学习态度等维度</li>
            <li><b>学习手册在线答题</b> — 50 题，可无限次作答，90 分以上合格</li>
            <li><b>安全教育在线答题</b> — 50 题，可无限次作答，90 分以上合格</li>
          </ul>
          <div class="gc-note">⚠ 以上 3 项均为报到注册必要环节，未完成无法报到</div>
          <a class="gc-link" href="https://stu.sztu.edu.cn/yxwz" target="_blank" rel="noopener">迎新服务网 →</a>
        </div>

        <!-- 线下报到 -->
        <div class="guide-card">
          <div class="gc-head">
            <div class="gc-icon orange">🏫</div>
            <div class="gc-title">线下报到</div>
            <span class="gc-badge" data-deadline="2026-08-30">8/30 周日</span>
          </div>
          <ul class="gc-list">
            <li><b>时间：</b>2026 年 8 月 30 日（周日）8:00-18:00</li>
            <li><b>地点：</b>D-2 体育馆二楼 · 羽毛球馆</li>
            <li><b>需携带：</b>身份证、录取通知书、高中档案（学籍+团员）、助学贷款材料（如有）、户口迁移材料</li>
            <li><b>北区迎新点：</b>E2 栋二楼（男生后勤办公室门口 / 女生团学办公室门口）</li>
            <li><b>南区迎新点：</b>A1 栋（男生南区中庭 / 女生公交站东侧外围）</li>
          </ul>
        </div>

        <!-- 校园卡 -->
        <div class="guide-card">
          <div class="gc-head">
            <div class="gc-icon purple">💳</div>
            <div class="gc-title">校园卡使用</div>
          </div>
          <ul class="gc-list">
            <li>报到当天在学院窗口领取校园卡，关注<b>「深圳技术大学信息中心」</b>公众号开通虚拟卡</li>
            <li>默认密码为<b>身份证后 6 位</b>（X 结尾取前六位数字），首次登录须修改</li>
            <li>密码要求：大小写字母+数字+符号至少 2 种，长度 8-16 位</li>
            <li>支持微信充值，仅限主账户；热水补助需到圈存机领取</li>
          </ul>
          <div class="gc-note">📞 校园卡问题：0755-23256326 / C-5 教学楼 2 楼 248 室</div>
        </div>

        <!-- 宿舍入住 -->
        <div class="guide-card">
          <div class="gc-head">
            <div class="gc-icon pink">🛏</div>
            <div class="gc-title">宿舍入住</div>
          </div>
          <ul class="gc-list">
            <li><b>拎包入住</b>，只需准备生活用品和洗漱用品</li>
            <li>床垫需自备，建议尺寸 <b>1.9m × 0.85m</b>（小卖部当天有售）</li>
            <li><b>热水充值：</b>报到后到圈存机充值，避免晚间拥堵</li>
            <li>北区圈存机：北区宿舍 1 楼 / C-5 教学楼 2 楼 248 室</li>
            <li>南区圈存机：南区宿舍 2 楼 / C-5 教学楼 2 楼 248 室</li>
          </ul>
        </div>

        <!-- 宿舍宽带 -->
        <div class="guide-card">
          <div class="gc-head">
            <div class="gc-icon cyan">📡</div>
            <div class="gc-title">南区宿舍宽带</div>
            <span class="gc-badge done">免费体验至 9/30</span>
          </div>
          <ul class="gc-list">
            <li>连接 <b>SZTU-student</b>（不是 SZTU），自动弹出认证页，或访问 <b>172.17.40.8:8800</b></li>
            <li>账号为 <b>12 位学号</b>，密码为 <b>SZtu@身份证后 6 位</b>（X 结尾也取后 6 位含 X）</li>
            <li><b>50M</b>：30 元/月 | <b>100M</b>：40 元/月</li>
            <li>预存 5 个月送 1 个月 | 预存 10 个月送 2 个月（更优惠）</li>
            <li>缴费方式：先给一卡通充值，再在自助服务→套餐→缴费</li>
            <li>上下行对等，1 个账号可登 3-5 台设备，仅限南区宿舍使用</li>
          </ul>
          <div class="gc-note">⚠ 注意：校园一卡通密码（6 位数字）和宽带认证密码（SZtu@身份证后 6 位）不同，别搞混</div>
        </div>

        <!-- 校园手机卡 -->
        <div class="guide-card">
          <div class="gc-head">
            <div class="gc-icon orange">📱</div>
            <div class="gc-title">校园星卡（电信）</div>
            <span class="gc-badge done">8-9 月月租 0 元</span>
          </div>
          <ul class="gc-list">
            <li><b>月租 39 元</b>：含 135G 全国流量 + 30G 定向流量 + 100 分钟通话</li>
            <li>定向流量覆盖：爱奇艺、腾讯视频、抖音、快手、网易云等</li>
            <li><b>预存 100 元</b>话费立即到账，办理需身份证 + 录取通知书</li>
            <li>有效期 <b>48 个月</b>，仅限 18-28 岁在校生，报到现场办理</li>
            <li>融合套餐：<b>69 元/月</b> = 100M 宽带 + 185G 流量 + 100 分钟通话</li>
            <li>支持微信自动扣费，流量不结转，合约期内不可过户</li>
          </ul>
          <div class="gc-note">⚠ 新卡需二次实人认证（收到短信后按指引操作，需关闭 WiFi 用 4G/5G 认证）</div>
        </div>

      </div><!-- /.guide-grid -->

      <!-- 高频 FAQ -->
      <div style="margin-top:14px">
        <div class="gc-head" style="margin-bottom:8px">
          <div class="gc-icon cyan">💬</div>
          <div class="gc-title">高频问答</div>
        </div>
        <div class="faq-list">
          <div class="faq-item">
            <div class="faq-q">行李、快递寄哪里？</div>
            <div class="faq-a">广东省深圳市坪山区石井街道田头社区兰田路 3002 号 深圳技术大学<b>北区宿舍</b></div>
          </div>
          <div class="faq-item">
            <div class="faq-q">去哪里吃饭？</div>
            <div class="faq-a">北区 E-0 食堂 2 楼 11:00-14:00，3 楼部分档口全天供餐；南区 A-0 食堂 11:00-14:00，部分档口全天供餐。西餐厅因装修暂不供餐。</div>
          </div>
          <div class="faq-item">
            <div class="faq-q">买生活用品去哪里？</div>
            <div class="faq-a">E3 宿舍楼下超市 / 北区 E-0 食堂二楼小超市 / 南区食堂一楼超市</div>
          </div>
          <div class="faq-item">
            <div class="faq-q">家人来住哪最方便？</div>
            <div class="faq-a">校内：深技大国际学术交流中心 1034 酒店。校外地铁站附近：麦途酒店、希尔达智略酒店、雅美途酒店等。</div>
          </div>
          <div class="faq-item">
            <div class="faq-q">宽带免费体验到什么时候？</div>
            <div class="faq-a">新生报到可<b>免费体验到 9 月 30 日</b>，之后需自费购买套餐。当月充值当月生效，1 号和 28 号充值都算 1 个月。</div>
          </div>
          <div class="faq-item">
            <div class="faq-q">宽带套餐没到期不想用了能退费吗？</div>
            <div class="faq-a">不能退费。可以更换速率套餐，但原预付费用需核实后退费，流程较麻烦。</div>
          </div>
          <div class="faq-item">
            <div class="faq-q">校园星卡超出套餐怎么收费？</div>
            <div class="faq-a">超出通话 0.1 元/分钟，超出流量 5 元/GB（不足 1G 按 1G 计），600 元断网。短彩信 0.1 元/条。流量不结转。</div>
          </div>
          <div class="faq-item">
            <div class="faq-q">新办的手机卡注册了微信/支付宝怎么办？</div>
            <div class="faq-a">运营商无法取消第三方账号。关注公众号<b>「中国信通院 CAICT」</b>→「一证通查」→「互联网账号」核查并登录对应 APP 注销。</div>
          </div>
        </div>
      </div>

      <!-- 联系电话 -->
      <div class="contact-bar">
        <div class="contact-item"><b>学生部</b><span class="c-tel">0755-23256153</span></div>
        <div class="contact-item"><b>招生办</b><span class="c-tel">0755-23256666</span></div>
        <div class="contact-item"><b>保卫处</b><span class="c-tel">0755-23256110</span></div>
        <div class="contact-item"><b>校医院</b><span class="c-tel">0755-23256120</span></div>
        <div class="contact-item"><b>校园卡</b><span class="c-tel">0755-23256326</span></div>
      </div>

      <div style="margin-top:10px; font-size:10px; color:var(--muted); line-height:1.5">
        * 来源：深圳技术大学公众号《@2026 级新同学，你的报到指南请查收》。<br>报到当天天气提醒：8 月 30 日大雨转雷阵雨，请携带雨具。
      </div>

    </div>
  </div>

</div><!-- /.container -->
<button class="back-top" id="backTop" aria-label="返回顶部">↑</button>
<footer>由 TeleAgent 深技大资讯中枢技能生成 · 数据实时抓取自 www.sztu.edu.cn</footer>
<script>
  // 主题切换
  const toggleBtn = document.getElementById('themeToggle');
  const themeLabel = document.getElementById('themeLabel');
  const savedTheme = localStorage.getItem('sztu-theme');
  if (savedTheme) { document.documentElement.setAttribute('data-theme', savedTheme); updateLabel(savedTheme); }
  function updateLabel(theme) {
    const dark = theme === 'dark';
    themeLabel.textContent = dark ? '明亮模式' : '暗黑模式';
    toggleBtn.querySelector('.tt-icon').textContent = dark ? '☀️' : '🌙';
  }
  function updateTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('sztu-theme', theme);
    updateLabel(theme);
  }
  toggleBtn.addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme') || 'light';
    updateTheme(cur === 'dark' ? 'light' : 'dark');
  });

  /* 关注事项折叠 */
  const focusToggle = document.getElementById('focusToggle');
  const focusPanel = focusToggle.closest('.focus-panel');
  focusToggle.addEventListener('click', () => {
    const collapsed = focusPanel.classList.toggle('collapsed');
    focusToggle.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    focusToggle.querySelector('.ft-text').textContent = collapsed ? '展开' : '收起';
  });

  /* 新闻筛选 */
  const btns = document.querySelectorAll('.filter-btn');
  const cards = document.querySelectorAll('.news-card');
  btns.forEach(b => b.addEventListener('click', () => {
    btns.forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    const f = b.dataset.filter;
    cards.forEach(c => { c.style.display = (f === 'all' || c.dataset.column === f) ? '' : 'none'; });
  }));

  /* 过期条目检测 */
  const today = new Date(); today.setHours(0,0,0,0);
  document.querySelectorAll('[data-deadline]').forEach(el => {
    const dl = el.dataset.deadline;
    if (!dl) return;
    const dlDate = new Date(dl); dlDate.setHours(23,59,59,999);
    if (dlDate < today) el.classList.add('expired');
  });

  /* 竞赛展开/折叠 */
  const moreBtn = document.getElementById('contestMore');
  const contestList = moreBtn.parentElement.querySelector('.contest-list');
  moreBtn.addEventListener('click', () => {
    const open = contestList.classList.toggle('open');
    moreBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
    moreBtn.querySelector('.cm-text').textContent = open ? '收起竞赛' : '展开全部竞赛';
    moreBtn.querySelector('.cm-arrow').textContent = open ? '▴' : '▾';
  });

  /* 返回顶部 */
  const backTop = document.getElementById('backTop');
  window.addEventListener('scroll', () => {
    if (window.scrollY > 400) { backTop.classList.add('show'); }
    else { backTop.classList.remove('show'); }
  });
  backTop.addEventListener('click', () => { window.scrollTo({top:0, behavior:'smooth'}); });

  /* 动效1：顶部加载进度条完成 */
  window.addEventListener('load', () => {
    const lb = document.getElementById('loadBar');
    if (lb) { lb.classList.add('done'); setTimeout(() => lb.remove(), 600); }
  });

  /* 动效2：数字滚动计数器 */
  function animateCount(el) {
    const target = parseInt(el.dataset.target || '0', 10);
    if (target <= 0) { el.textContent = '0'; return; }
    const dur = 1200;
    const start = performance.now();
    function tick(now) {
      const p = Math.min((now - start) / dur, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased);
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = target;
    }
    requestAnimationFrame(tick);
  }
  document.querySelectorAll('.count').forEach(el => animateCount(el));

  /* 动效3：打字机效果 */
  (function() {
    const subEl = document.getElementById('heroSub');
    if (!subEl) return;
    const fullText = subEl.dataset.text || '';
    subEl.textContent = '';
    const liveDot = document.createElement('span');
    liveDot.className = 'live-dot';
    subEl.appendChild(liveDot);
    let idx = 0;
    function typeNext() {
      if (idx < fullText.length) {
        liveDot.remove();
        subEl.textContent = fullText.substring(0, idx + 1);
        subEl.appendChild(liveDot);
        idx++;
        setTimeout(typeNext, 35);
      } else {
        const cursor = document.createElement('span');
        cursor.className = 'cursor';
        subEl.appendChild(cursor);
      }
    }
    setTimeout(typeNext, 300);
  })();

  /* 动效4：新闻卡片滚动入场（IntersectionObserver） */
  (function() {
    const nc = document.querySelectorAll('.news-card');
    if (!('IntersectionObserver' in window)) {
      nc.forEach(c => c.classList.add('visible'));
      return;
    }
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry, i) => {
        if (entry.isIntersecting) {
          const card = entry.target;
          const delay = Array.from(nc).indexOf(card) * 80;
          setTimeout(() => card.classList.add('visible'), delay);
          io.unobserve(card);
        }
      });
    }, { threshold: 0.1, rootMargin: '0px 0px -40px 0px' });
    nc.forEach(c => io.observe(c));
  })();

  /* 动效5：背景数字雨 */
  (function() {
    const rain = document.getElementById('digitalRain');
    if (!rain) return;
    const colCount = Math.min(Math.floor(window.innerWidth / 50), 24);
    for (let i = 0; i < colCount; i++) {
      const col = document.createElement('div');
      col.className = 'rain-col';
      col.style.left = (i * (100 / colCount)) + '%';
      const dur = 6 + Math.random() * 8;
      col.style.animationDuration = dur + 's';
      col.style.animationDelay = (Math.random() * 6) + 's';
      let chars = '';
      const len = 12 + Math.floor(Math.random() * 12);
      for (let j = 0; j < len; j++) chars += (Math.random() > 0.5 ? '1' : '0') + ' ';
      col.textContent = chars;
      rain.appendChild(col);
    }
  })();

  /* 动效6：鸡汤轮播 + 鼠标跟随光晕 */
  (function() {
    var soups = [
      "你今天的努力，是幸运的伏笔。",
      "不必仰望别人，自己亦是风景。",
      "与其临渊羡鱼，不如退而结网。",
      "星光不问赶路人，时光不负有心人。",
      "你只管努力，剩下的交给时间。",
      "每一个不曾起舞的日子，都是对生命的辜负。",
      "所谓万丈深渊，走下去，也是前程万里。",
      "生活明朗，万物可爱，人间值得，未来可期。",
      "愿你历尽千帆，归来仍是少年。",
      "乾坤未定，你我皆是黑马。",
      "世上无难事，只要肯放弃——开玩笑的，再坚持一下！",
      "你的气质里，藏着你走过的路和读过的书。",
      "别让平凡的生活耗尽你所有的向往。",
      "所有的不甘，都是因为还心存梦想。",
      "人生没有白走的路，每一步都算数。"
    ];
    varidx = 0;
    var soupEl = document.getElementById('soupText');
    if (soupEl) {
      var current = soupEl.textContent.trim();
      var startIdx = soups.indexOf(current);
      if (startIdx >= 0) idx = startIdx;
      setInterval(function() {
        idx = (idx + 1) % soups.length;
        soupEl.style.opacity = '0';
        setTimeout(function() {
          soupEl.textContent = soups[idx];
          soupEl.style.opacity = '1';
        }, 500);
      }, 6000);
    }

    /* 鼠标跟随光晕 */
    var grid = document.querySelector('.quick-grid');
    if (grid) {
      grid.addEventListener('mousemove', function(e) {
        var rect = grid.getBoundingClientRect();
        var x = ((e.clientX - rect.left) / rect.width * 100).toFixed(1);
        var y = ((e.clientY - rect.top) / rect.height * 100).toFixed(1);
        grid.style.setProperty('--mx', x + '%');
        grid.style.setProperty('--my', y + '%');
      });
    }
  })();
</script>
</body>
</html>
"""


def render_date(d):
    """日期字符串 'YYYY-MM-DD' -> (日, 月/年)"""
    parts = d.split("-")
    if len(parts) == 3:
        return parts[2].lstrip("0"), f"{parts[1]}/{parts[0][2:]}"
    return d, ""


def build_card(item):
    d, m = render_date(item["date"]) if item["date"] else ("--", "")
    if item["column"] == "校园新闻":
        col, meta = "campus", COLUMN_META["campus"]
    elif item["column"] == "媒体聚焦":
        col, meta = "media", COLUMN_META["media"]
    else:
        col, meta = "research", COLUMN_META["research"]
    badge = f'<span class="tag {meta["cls"]}">{html.escape(meta["label"])}</span>'
    media_badge = f'<span class="media-src">{html.escape(item["media"])}</span>' if item.get("media") else ""
    summary = html.escape(item.get("summary") or "")
    summary_html = f'<div class="news-summary">{summary}</div>' if summary else ""
    title = html.escape(item["title"])
    url = item["url"]
    return f'''<a class="news-card" data-column="{col}" href="{html.escape(url)}" target="_blank" rel="noopener">
  <div class="news-date"><span class="d">{html.escape(d)}</span><span class="m">{html.escape(m)}</span></div>
  <div class="news-body">
    <div class="news-meta">{badge}{media_badge}</div>
    <div class="news-title">{title}</div>
    {summary_html}
    <div class="news-link">阅读原文 →</div>
  </div>
</a>'''


def build_research_cards(items):
    """构建科研动态横条卡片，最多取 3 条科学新闻。"""
    research = [it for it in items if it["column"] == "科学研究"]
    if not research:
        return ""
    out = []
    for it in research[:3]:
        d = it["date"]
        m = ""
        if len(d.split("-")) == 3:
            m = d.split("-")[1] + "-" + d.split("-")[2]
        out.append(f'''<a class="research-item" href="{html.escape(it['url'])}" target="_blank" rel="noopener">
  <span class="r-tag">🔬 科学研究</span>
  <div class="r-title">{html.escape(it["title"])}</div>
  <div class="r-date">{html.escape(m)}</div>
</a>''')
    return "\n".join(out)


def build_quick_links():
    out = []
    for link in QUICK_LINKS:
        out.append(f'''<a class="quick-item" href="{link["url"]}" target="_blank" rel="noopener">
  <div class="q-icon">{link["icon"]}</div>
  <div class="q-title">{html.escape(link["name"])}</div>
</a>''')
    return "\n".join(out)


def pick_soup(date_str):
    """根据日期确定性地选一条鸡汤，同一天打开看到同一条"""
    seed = 0
    for ch in date_str:
        seed = (seed * 31 + ord(ch)) % 100000
    return SOUPS[seed % len(SOUPS)]


def main():
    ap = argparse.ArgumentParser(description="渲染深技大热点新闻 HTML")
    ap.add_argument("--input", default="sztu_news.json")
    ap.add_argument("--output", default="sztu_news.html")
    args = ap.parse_args()

    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)

    items = data.get("items", [])
    cards = "\n".join(build_card(it) for it in items)
    campus = sum(1 for it in items if it["column"] == "校园新闻")
    media = sum(1 for it in items if it["column"] == "媒体聚焦")
    research = sum(1 for it in items if it["column"] == "科学研究")
    total = len(items) or 1
    campus_pct = round(campus / total * 100)
    media_pct = round(media / total * 100)
    research_pct = 100 - campus_pct - media_pct
    # 动态环形图：按真实占比生成 conic-gradient 分段（保留最小显示宽度，0 值跳过）
    segs = []
    start = 0
    for name, pct, var in (("校园新闻", campus_pct, "var(--cyan)"),
                           ("媒体聚焦", media_pct, "var(--orange)"),
                           ("科学研究", research_pct, "var(--purple)")):
        if pct <= 0:
            continue
        end = start + pct
        segs.append(f"{var} {start}deg {end}deg")
        start = end
    donut_bg = ", ".join(segs)
    if not donut_bg:
        donut_bg = "var(--cyan) 0deg 360deg"
    research_cards = build_research_cards(items)
    quick_links = build_quick_links()

    date_label = data.get("generated_at", "")
    soup_text = pick_soup(date_label)
    update_date = date_label.split(" ")[0] if date_label else ""

    html_out = TEMPLATE \
        .replace("@@date_label@@", date_label) \
        .replace("@@total@@", str(len(items))) \
        .replace("@@window@@", str(data.get("effective_window_days", "?"))) \
        .replace("@@campus@@", str(campus)) \
        .replace("@@media@@", str(media)) \
        .replace("@@research@@", str(research)) \
        .replace("@@campus_pct@@", str(campus_pct)) \
        .replace("@@media_pct@@", str(media_pct)) \
        .replace("@@research_pct@@", str(research_pct)) \
        .replace("@@donut_bg@@", donut_bg) \
        .replace("@@cards@@", cards) \
        .replace("@@soup_text@@", soup_text) \
        .replace("@@update_date@@", update_date) \
        .replace("@@research_cards@@", research_cards) \
        .replace("@@quick_links@@", quick_links)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html_out)
    print(f"[ok] 已生成 {args.output}（{len(items)} 条新闻）")


if __name__ == "__main__":
    main()