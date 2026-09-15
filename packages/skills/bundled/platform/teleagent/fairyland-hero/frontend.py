import streamlit as st
import streamlit.components.v1 as components
import requests
import json
import base64
import hashlib
import os
import re
import math
import html as html_escape
from urllib.parse import quote, urlparse
from datetime import datetime, timedelta
from typing import Any, Dict, List, MutableMapping, Optional, Tuple
import warnings
import logging
import sys
import asyncio

def _dq_equipment_quality_colors(meta: Optional[Dict[str, Any]]) -> Tuple[str, str, str]:
    """
    装备稀有度配色：背景色、文字色、边框色。
    与 dq_rpg QUALITY_* 一致：normal / fine / epic / legend / supreme。
    """
    q = str((meta or {}).get("quality", "normal") or "normal")
    table: Dict[str, Tuple[str, str, str]] = {
        "normal": ("#ffffff", "#0f172a", "#e2e8f0"),
        "fine": ("#dbeafe", "#1e3a8a", "#60a5fa"),
        # 史诗：饱和浅紫底 + 深紫字 + 正紫边（与精良浅蓝底 / 亮蓝边区分）
        "epic": ("#e9d5ff", "#6b21a8", "#9333ea"),
        "legend": ("#ffedd5", "#9a3412", "#fb923c"),
        "supreme": ("#fecaca", "#991b1b", "#ef4444"),
    }
    return table.get(q, table["normal"])


def _dq_inv_category_badge(label: str, variant: str = "pot") -> None:
    """背包「药水 / 材料 / 功能道具」列标题：胶囊标签（替代灰字 caption）。"""
    presets = {
        "pot": ("#eff6ff", "#1d4ed8", "#93c5fd"),
        "mat": ("#f0fdf4", "#15803d", "#86efac"),
        "util": ("#fffbeb", "#c2410c", "#fcd34d"),
    }
    bg, fg, bd = presets.get(variant, presets["pot"])
    safe = html_escape.escape(label)
    st.markdown(
        f'<div style="margin-bottom:12px;">'
        f'<span style="display:inline-block;font-size:0.78rem;font-weight:600;letter-spacing:0.08em;'
        f'color:{fg};background:{bg};border:1px solid {bd};border-radius:999px;padding:5px 14px;'
        f'box-shadow:0 1px 2px rgba(15,23,42,0.06);">{safe}</span></div>',
        unsafe_allow_html=True,
    )


def _dq_inv_empty_hint(message: str) -> None:
    """暂无药水 / 材料 / 功能道具时的轻提示块。"""
    safe = html_escape.escape(message)
    st.markdown(
        f'<div style="font-size:0.82rem;color:#64748b;line-height:1.55;text-align:center;'
        f'background:linear-gradient(180deg,#f8fafc 0%,#f1f5f9 100%);border:1px dashed #cbd5e1;'
        f'border-radius:10px;padding:12px 14px;margin-top:2px;">{safe}</div>',
        unsafe_allow_html=True,
    )


def _dq_equip_card_title_name(raw: str) -> str:
    """背包装备卡片标题：去掉「【战士专属】」类后缀（与下方职业署名区分）。"""
    s = str(raw or "").strip()
    if not s:
        return "装备"
    s = re.sub(r"【[^】]*专属】", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s or "装备"


def _dq_backpack_equip_card_details(it: Dict[str, Any], dq: Any) -> None:
    """
    背包装备卡片属性区：
    第一行：主属性 | 副属性 | 物攻+1% 等（副属性右侧为百分比类词条，多条以 · 分隔）；
    第二行：职业署名（无 req_roles 为「全职业」）；饰品特效【名称】（悬停见详细介绍）。
    """
    meta = (it.get("meta") or {}) if isinstance(it, dict) else {}
    attr_keys = getattr(dq, "ATTR_KEYS", ("str", "int", "dex", "agi", "luk", "vit"))
    role_cn = getattr(dq, "ROLE_CN", {}) or {}

    row1_parts: List[str] = []
    mk = str(meta.get("main_attr", "") or "")
    mv = int(meta.get("main_val", 0) or 0)
    if mk in attr_keys and mv:
        row1_parts.append(
            f'<span style="font-weight:600;color:#0f172a;">主属性 {html_escape.escape(mk.upper())} +{mv}</span>'
        )
    sk = str(meta.get("sub_attr", "") or "")
    sv = int(meta.get("sub_val", 0) or 0)
    if sk in attr_keys and sv:
        row1_parts.append(
            f'<span style="font-weight:600;color:#0f172a;">副属性 {html_escape.escape(sk.upper())} +{sv}</span>'
        )

    # 第一排右侧：物攻/法伤/治疗与各加成百分比（与 dq 词条一致）
    effect_chunks: List[str] = []
    for k, lab in (("atk_bonus", "物攻"), ("spell_bonus", "法伤"), ("heal_bonus", "治疗")):
        pv = float(meta.get(k, 0.0) or 0.0)
        if pv > 0:
            effect_chunks.append(
                f'<span style="color:#0369a1;font-weight:500;">{html_escape.escape(lab)}'
                f'+{int(round(pv * 100))}%</span>'
            )
    for k, lab in (
        ("atk_pct", "攻击加成"),
        ("eva_bonus", "闪避加成"),
        ("mit_bonus", "免伤加成"),
        ("crit_bonus", "暴击加成"),
        ("hit_bonus", "命中加成"),
    ):
        pv = float(meta.get(k, 0.0) or 0.0)
        if pv > 0:
            effect_chunks.append(
                f'<span style="color:#0369a1;font-weight:500;">{html_escape.escape(lab)}'
                f'+{int(round(pv * 100))}%</span>'
            )
    if effect_chunks:
        _fx_sep = '<span style="color:#94a3b8;margin:0 4px;">·</span>'
        row1_parts.append(_fx_sep.join(effect_chunks))

    row2_segments: List[str] = []

    req_roles = meta.get("req_roles")
    if isinstance(req_roles, list) and len(req_roles) > 0:
        req_cn = "、".join([str(role_cn.get(str(r), r)) for r in req_roles])
        row2_segments.append(
            '<span style="font-weight:700;">职业署名</span> '
            f'<span style="color:#0f172a;">{html_escape.escape(req_cn)}</span>'
        )
    else:
        row2_segments.append(
            '<span style="font-weight:700;">职业署名</span> '
            '<span style="color:#0f172a;">全职业</span>'
        )

    acc_spec = getattr(dq, "ACCESSORY_SPECIALS", {}) or {}
    sids = meta.get("special_ids")
    acc_lines: List[str] = []
    if isinstance(sids, list) and sids:
        for _sid in sids:
            sp = acc_spec.get(str(_sid))
            if isinstance(sp, dict) and sp.get("name"):
                nm = html_escape.escape(str(sp.get("name", "")))
                desc_raw = str(sp.get("desc", "") or "")
                title_esc = html_escape.escape(desc_raw, quote=True)
                acc_lines.append(
                    '<span style="font-weight:700;">饰品特效</span> '
                    f'<span style="cursor:help;" title="{title_esc}">【{nm}】</span>'
                )
    else:
        sid_one = meta.get("special_id")
        if sid_one:
            sp = acc_spec.get(str(sid_one))
            if isinstance(sp, dict) and sp.get("name"):
                nm = html_escape.escape(str(sp.get("name", "")))
                desc_raw = str(sp.get("desc", "") or "")
                title_esc = html_escape.escape(desc_raw, quote=True)
                acc_lines.append(
                    '<span style="font-weight:700;">饰品特效</span> '
                    f'<span style="cursor:help;" title="{title_esc}">【{nm}】</span>'
                )

    if acc_lines:
        row2_segments.append(" ".join(acc_lines))

    div_sep = '<span style="color:#cbd5e1;margin:0 8px;">|</span>'
    if row1_parts:
        st.markdown(
            f'<div style="font-size:0.82rem;line-height:1.45;margin-top:6px;margin-bottom:8px;">'
            f"{div_sep.join(row1_parts)}</div>",
            unsafe_allow_html=True,
        )

    if row2_segments:
        st.markdown(
            f'<div style="font-size:0.78rem;line-height:1.55;color:#475569;">'
            f'{" · ".join(row2_segments)}</div>',
            unsafe_allow_html=True,
        )


# 过滤 tornado WebSocket 关闭错误（Streamlit 内部错误，不影响功能）
# 这个错误通常发生在页面刷新或重定向时，是 Streamlit 内部的正常行为
# 设置 tornado 日志级别，减少不必要的错误输出
logging.getLogger('tornado.access').setLevel(logging.ERROR)
logging.getLogger('tornado.application').setLevel(logging.ERROR)
logging.getLogger('tornado.general').setLevel(logging.ERROR)
logging.getLogger('tornado.websocket').setLevel(logging.ERROR)

# 抑制未捕获的任务异常（WebSocket 关闭时经常出现）
# Task exception was never retrieved / WebSocketClosedError：用户刷新或关闭页时 Streamlit/Tornado 仍写 WebSocket，属正常现象
import asyncio

def _ws_safe_exception_handler(loop, context):
    """过滤 WebSocket 关闭相关异常，避免刷屏"""
    exception = context.get('exception')
    message = context.get('message', '')
    if exception:
        name = type(exception).__name__
        if name in ('WebSocketClosedError', 'StreamClosedError', 'ConnectionResetError'):
            return
        if 'Stream is closed' in (str(exception) or '') or 'WebSocket' in (str(exception) or ''):
            return
    if message and ('Stream is closed' in str(message) or 'WebSocket' in str(message)):
        return
    try:
        loop.default_exception_handler(context)
    except Exception:
        pass

try:
    _orig_new = asyncio.new_event_loop
except AttributeError:
    _orig_new = None
if _orig_new:
    def _new_event_loop():
        loop = _orig_new()
        try:
            loop.set_exception_handler(_ws_safe_exception_handler)
        except Exception:
            pass
        return loop
    asyncio.new_event_loop = _new_event_loop
try:
    loop = asyncio.get_event_loop()
    if loop is not None:
        try:
            loop.set_exception_handler(_ws_safe_exception_handler)
        except Exception:
            pass
except (RuntimeError, AttributeError):
    pass


st.set_page_config(
    page_title="仙境Hero",
    page_icon="🧙",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsed"],
    [data-testid="stExpandSidebarButton"] {
        display: none !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

if os.environ.get("ENVIRONMENT") == "production" and not os.environ.get("BACKEND_URL"):
    BACKEND_URL = ""
else:
    BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8083")

def _dq_url_host_is_loopback(url: str) -> bool:
    try:
        h = (urlparse(url).hostname or "").lower()
        return h in ("localhost", "127.0.0.1", "::1")
    except Exception:
        return False


def _dq_streamlit_browser_origin() -> Optional[str]:
    """当前用户在浏览器里访问 Streamlit 的站点根（scheme://host[:port]），用于修正 localhost API 地址。"""
    try:
        ctx = getattr(st, "context", None)
        if ctx is None:
            return None
        u = getattr(ctx, "url", None)
        if u:
            p = urlparse(str(u))
            if p.scheme and p.netloc:
                return f"{p.scheme}://{p.netloc}".rstrip("/")
        hdrs = getattr(ctx, "headers", None)
        if hdrs is not None:
            host = hdrs.get("Host") or hdrs.get("host")
            if host:
                xf = hdrs.get("X-Forwarded-Proto") or hdrs.get("x-forwarded-proto") or "https"
                proto = str(xf).split(",")[0].strip().lower()
                if proto not in ("http", "https"):
                    proto = "https"
                return f"{proto}://{host}".rstrip("/")
    except Exception:
        pass
    return None


def _dq_browser_api_base() -> str:
    """
    浏览器内嵌媒体（<video>/<audio>）请求的 API 根地址，无尾斜杠。
    - 空字符串：使用相对路径 /api/...（与当前页同协议、主机、端口，需反代把 /api 转到 Flask）。
    - 勿把服务端 BACKEND_URL=localhost 直接写进 HTML：远程用户浏览器会连到自己电脑的 8083，导致 ERR_CONNECTION_REFUSED。

    可显式设置环境变量：PUBLIC_API_BASE 或 BROWSER_API_BASE（例如 https://你的域名 或 http://服务器IP:8083）。

    优先级：显式 PUBLIC → 非 localhost 的 BACKEND_URL → 当前页面 origin（非 localhost 时，用于远程访问修正）
    → 仍保留 localhost 的 BACKEND_URL（本机双端口开发直连 Flask）→ 相对路径。
    """
    pub = (os.environ.get("PUBLIC_API_BASE") or os.environ.get("BROWSER_API_BASE") or "").strip().rstrip("/")
    if pub:
        return pub
    back = (BACKEND_URL or "").strip().rstrip("/")
    if back and not _dq_url_host_is_loopback(back):
        return back
    origin = _dq_streamlit_browser_origin()
    if origin and not _dq_url_host_is_loopback(origin):
        return origin
    if back:
        return back
    return ""

_DQ_GAME_TAB_LABELS = ("冒险", "战斗", "任务/剧情", "天赋树", "商店", "背包/装备", "设置")


def _dq_inject_click_game_tab(label: str) -> None:
    """按标签文字点击主界面 tab。

    关键点：
    1. Streamlit 的 tab 元素是 div[role="tab"]（非 button[role="tab"]）
    2. components.html() 的 iframe 带 allow-same-origin，可通过 window.parent 访问主页面
    3. st.html() 不执行 inline <script>，只能用 components.html()
    """
    want = json.dumps(str(label or ""), ensure_ascii=False)
    components.html(
        f"""
<script>
(function() {{
  var want = {want};
  function norm(s) {{ return String(s || "").replace(/\\s+/g, "").trim(); }}
  var target = norm(want);
  function tryClick(doc) {{
    if (!doc || !doc.querySelectorAll) return false;
    var bars = [];
    try {{
      var found = doc.querySelectorAll('[data-testid="stTabs"]');
      for (var i = 0; i < found.length; i++) bars.push(found[i]);
    }} catch (e0) {{}}
    if (!bars.length) bars.push(doc);
    for (var b = 0; b < bars.length; b++) {{
      var tabs = [];
      try {{ tabs = bars[b].querySelectorAll('[role="tab"]'); }} catch (e1) {{}}
      for (var j = 0; j < tabs.length; j++) {{
        var t = norm(tabs[j].innerText || tabs[j].textContent);
        if (t === target || t.indexOf(target) >= 0) {{
          tabs[j].click();
          return true;
        }}
      }}
    }}
    return false;
  }}
  function walk() {{
    // 先尝试当前 document（直连浏览器场景）
    try {{ if (tryClick(document)) return true; }} catch (e) {{}}
    // 再尝试 parent（Streamlit iframe 场景）
    try {{
      if (window.parent && window.parent !== window && tryClick(window.parent.document)) return true;
    }} catch (e) {{}}
    // 最后尝试 top（TeleAgent 多层 iframe 场景）
    try {{
      if (window.top && window.top !== window && tryClick(window.top.document)) return true;
    }} catch (e) {{}}
    return false;
  }}
  var n = 0;
  function tick() {{
    if (walk()) return;
    n += 1;
    if (n < 25) setTimeout(tick, 120);
  }}
  setTimeout(tick, 60);
}})();
</script>
""",
        height=1,
        width=1,
        scrolling=False,
    )


_DQ_MUSIC_DIR = os.path.join(os.path.dirname(__file__), "music")

def _dq_music_track_url(filename: str) -> str:
    """返回可缓存的音频 URL，避免每次 rerun 传输大体积 base64。"""
    safe = quote(str(filename or ""))
    base = _dq_browser_api_base()
    return f"{base}/api/music/{safe}" if base else f"/api/music/{safe}"


def _dq_battle_video_http_url(filename: str) -> str:
    """战斗弹窗 <video src> 用：与后端 video/ 文件名对应（仅 basename）。

    使用 _dq_browser_api_base()，避免 BACKEND_URL=localhost 时视频请求发到用户本机导致 ERR_CONNECTION_REFUSED。
    分离部署时请设置 PUBLIC_API_BASE，或由反代提供与页面同源的 /api/。
    """
    safe = quote(str(filename or ""))
    base = _dq_browser_api_base()
    return f"{base}/api/dq-battle-video/{safe}" if base else f"/api/dq-battle-video/{safe}"


def _dq_backend_request_base() -> str:
    """Streamlit 服务端请求后端 API 时的基址（与 BACKEND_URL 一致；空则默认本机 8083）。"""
    b = (BACKEND_URL or "").strip().rstrip("/")
    return b if b else "http://127.0.0.1:8083"


def _dq_pvp_url(path: str) -> str:
    p = path if path.startswith("/") else "/" + path
    return _dq_backend_request_base() + p


def _pvp_room_signature(room: Dict[str, Any]) -> str:
    """房间公开 JSON 的稳定指纹：用于轮询仅在数据变化时触发 st.rerun，避免定时整页重绘卡顿。"""
    try:
        raw = json.dumps(room or {}, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
    except Exception:
        return ""


def _dq_avatar_url_for_battle(kind: str, key: str, hero_gender: Optional[str] = None) -> str:
    """与冒险页战斗一致：从 img 按职业中文名或怪物名解析头像路径。"""
    img_dir = os.path.join(os.path.dirname(__file__), "img")
    role_to_cn = {
        "warrior": "战士",
        "cleric": "牧师",
        "mage": "法师",
        "hunter": "猎人",
        "rogue": "刺客",
    }
    if kind == "hero":
        role = str(key or "warrior")
        if role == "warrior":
            hg = str(hero_gender or "男").strip()
            if hg not in ("男", "女"):
                hg = "男"
            gendered = "战士_男" if hg == "男" else "战士_女"
            for ext in (".png", ".jpg", ".jpeg", ".webp"):
                p = os.path.join(img_dir, f"{gendered}{ext}")
                if os.path.exists(p):
                    return p
        base = role_to_cn.get(role, "战士")
        fallback = "战士"
    else:
        base = str(key or "史莱姆")
        fallback = "史莱姆"
    for nm in (base, fallback):
        for ext in (".png", ".jpg", ".jpeg", ".webp"):
            p = os.path.join(img_dir, f"{nm}{ext}")
            if os.path.exists(p):
                return p
    return ""


_DQ_BATTLE_ROLE_CN = {
    "warrior": "战士",
    "cleric": "牧师",
    "mage": "法师",
    "hunter": "猎人",
    "rogue": "刺客",
}


def _dq_safe_battle_video_segment(s: str) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    out = str(s or "")
    for c in bad:
        out = out.replace(c, "_")
    return out.strip() or "动作"


def _dq_battle_video_root() -> str:
    return os.path.join(os.path.dirname(__file__), "video")


def _dq_battle_video_dir_signature() -> float:
    """目录 mtime 作为缓存键：新增/删除视频文件后自动重建索引。"""
    root = _dq_battle_video_root()
    if not os.path.isdir(root):
        return 0.0
    try:
        return float(os.path.getmtime(root))
    except OSError:
        return 0.0


@st.cache_data(show_spinner=False)
def _dq_cached_battle_video_index(_dir_mtime: float) -> Dict[str, str]:
    """video/ 下无扩展名（与磁盘文件名一致）→ 绝对路径。按目录 mtime 失效缓存。"""
    root = _dq_battle_video_root()
    out: Dict[str, str] = {}
    if not os.path.isdir(root):
        return out
    exts = (".mp4", ".webm", ".mov", ".mkv")
    for fn in os.listdir(root):
        low = fn.lower()
        if not any(low.endswith(x) for x in exts):
            continue
        stem = os.path.splitext(fn)[0]
        p = os.path.join(root, fn)
        out[stem] = p
    return out


def _dq_battle_video_index() -> Dict[str, str]:
    return _dq_cached_battle_video_index(_dq_battle_video_dir_signature())


def _dq_resolve_battle_video_path(stem: str) -> str:
    m = _dq_battle_video_index()
    if stem in m:
        return m[stem]
    for k, v in m.items():
        if k.lower() == stem.lower():
            return v
    return ""


def _dq_paths_for_battle_video_stem(stem: str) -> List[str]:
    """与 stem 精确匹配，或 stem 为前缀的变体（如 战士_男_技能_连斩_2）。"""
    stem = str(stem or "").strip()
    if not stem:
        return []
    m = _dq_battle_video_index()
    out: List[str] = []
    stem_low = stem.lower()
    for k, pth in m.items():
        if not pth or not os.path.isfile(pth):
            continue
        if k == stem or k.lower() == stem_low:
            out.append(pth)
        elif k.startswith(stem + "_") or k.lower().startswith(stem_low + "_"):
            out.append(pth)
    return out


def _dq_random_battle_video_from_stems(stems: List[str]) -> str:
    import random

    raw = [str(s).strip() for s in (stems or []) if str(s).strip()]
    # 本回合若同时有普攻/防守等与技能，优先从带「_技能_」的 stem 中选，避免日志是圣疗却播了普攻
    skilled = [s for s in raw if "_技能_" in s]
    use_stems = skilled if skilled else raw
    cand: List[str] = []
    seen = set()
    for st in use_stems:
        for p in _dq_paths_for_battle_video_stem(str(st)):
            if p not in seen:
                seen.add(p)
                cand.append(p)
    return random.choice(cand) if cand else ""


def _dq_hero_battle_action_stem_and_label(
    state: Dict[str, Any],
    action_type: str,
    *,
    skill_sid: Optional[str],
    skill_catalog: Dict[str, str],
    potion_sample: Optional[Dict[str, Any]],
) -> Tuple[str, str]:
    """返回 (视频文件名 stem, 界面展示文案)。"""
    import dq_rpg as dq

    role = str(state.get("role", "warrior"))
    role_cn = _DQ_BATTLE_ROLE_CN.get(role, "战士")
    hg = str(state.get("hero_gender") or "男").strip()
    if hg not in ("男", "女"):
        hg = "男"
    act = str(action_type or "普攻")
    if act == "使用药水":
        act = "药水"
    if act == "普攻":
        seg = "普攻"
        label = "普攻"
    elif act == "技能":
        sid = str(skill_sid or "")
        label = dq.dq_skill_name(sid) if sid else "技能"
        cn_ui = skill_catalog.get(sid) if sid and sid in skill_catalog else None
        _sk = _dq_safe_battle_video_segment(cn_ui or label)
        # 视频命名：战士_男_技能_连斩.mp4（技能名在最后）
        seg = f"技能_{_sk}"
    elif act == "防守":
        seg, label = "防守", "防守"
    elif act == "药水":
        if potion_sample:
            nm = str(potion_sample.get("name", "药水") or "药水")
            seg = _dq_safe_battle_video_segment(nm)
            label = nm
        else:
            seg, label = "药水", "药水"
    elif act == "逃跑":
        seg, label = "逃跑", "逃跑"
    else:
        seg = _dq_safe_battle_video_segment(act)
        label = str(act)
    # 仅战士带性别（主角）；牧师/法师等视频名为 牧师_技能_xxx.mp4，无「男/女」段
    if role == "warrior":
        stem = f"{role_cn}_{hg}_{seg}"
    else:
        stem = f"{role_cn}_{seg}"
    return stem, label


def _dq_battle_video_path_after_submit(
    state: Dict[str, Any],
    atype: str,
    *,
    skill_sid: Optional[str],
    skill_catalog: Dict[str, str],
    potion_groups: Dict[str, Dict[str, Any]],
) -> str:
    """根据本回合提交的动作解析 video/ 下匹配文件（无则返回空串）。"""
    import dq_rpg as dq

    atype_s = str(atype or "")
    if atype_s == "使用药水":
        atype_s = "药水"
    potion_sample = None
    if atype_s == "药水":
        uk = st.session_state.get("dq_selected_potion_use")
        if uk is not None and str(uk) in potion_groups:
            potion_sample = potion_groups[str(uk)].get("sample")
    sid_use = str(skill_sid) if skill_sid and atype_s == "技能" else None
    stem, _ = _dq_hero_battle_action_stem_and_label(
        state,
        atype_s,
        skill_sid=sid_use,
        skill_catalog=skill_catalog,
        potion_sample=potion_sample,
    )
    path = _dq_resolve_battle_video_path(stem)
    # 兼容旧资源：战士_男_连斩.mp4（无「技能_」前缀）
    if not path and atype_s == "技能" and sid_use:
        role = str(state.get("role", "warrior"))
        role_cn = _DQ_BATTLE_ROLE_CN.get(role, "战士")
        hg = str(state.get("hero_gender") or "男").strip()
        if hg not in ("男", "女"):
            hg = "男"
        cn_ui = skill_catalog.get(sid_use) if sid_use in skill_catalog else None
        _sk = _dq_safe_battle_video_segment(cn_ui or dq.dq_skill_name(sid_use))
        if role == "warrior":
            stem_legacy = f"{role_cn}_{hg}_{_sk}"
        else:
            stem_legacy = f"{role_cn}_{_sk}"
        path = _dq_resolve_battle_video_path(stem_legacy)
    return path


def _dq_battle_finish_video_path(state: Dict[str, Any]) -> str:
    """战斗结束时优先使用结算动画：战士_男_牧师_刺客_胜利/失败.mp4。"""
    import random

    meta = state.get("meta") or {}
    outcome = str(meta.get("dq_last_battle_outcome") or "").strip().lower()
    if outcome == "win":
        result_tag = "胜利"
    elif outcome == "lose":
        result_tag = "失败"
    elif outcome == "flee":
        return ""
    else:
        # 旧存档无 meta：从后往前扫行，避免「上一场胜利」仍落在 tail 子串里导致本场失败误判为胜利（无限地牢连战尤甚）。
        battle_log = [str(x) for x in (meta.get("battle_log") or [])]
        overworld_log = [str(x) for x in (meta.get("log") or [])]
        combined = battle_log[-28:] + overworld_log[-28:]
        result_tag = ""
        for line in reversed(combined):
            if ("战斗失败" in line) or ("你倒下了" in line) or ("未获得经验掉落" in line):
                result_tag = "失败"
                break
            if "🏆 战斗胜利" in line:
                result_tag = "胜利"
                break
        if not result_tag:
            return ""

    role = str(state.get("role", "warrior"))
    role_cn = _DQ_BATTLE_ROLE_CN.get(role, "战士")
    parts: List[str] = [role_cn]
    if role == "warrior":
        hg = str(state.get("hero_gender") or "男").strip()
        if hg not in ("男", "女"):
            hg = "男"
        parts.append(hg)

    for mem in (state.get("party_members") or []):
        r = str(mem.get("role", "") or "").strip()
        if r:
            parts.append(_DQ_BATTLE_ROLE_CN.get(r, r))

    stem = "_".join([_dq_safe_battle_video_segment(x) for x in parts] + [result_tag])
    cand = _dq_paths_for_battle_video_stem(stem)
    return random.choice(cand) if cand else ""


def _dq_render_battle_video_popup(
    vpath: str,
    *,
    click_adventure_tab_after: bool = False,
    q1_act1_bgm_sync: bool = False,
    q1_act1_player_key: str = "",
) -> bool:
    """全屏遮罩挂到 Streamlit 父页面 body，避免 components 固定高度 iframe 播完后留大块空白。
    单击画面可立即结束播放并关闭遮罩（与播完/出错同逻辑）。
    click_adventure_tab_after：为 True 时在 ended/error/跳过后点击「冒险」标签（用于战斗已结束、播完再回大地图）。
    返回是否已注入播放组件（供 pending 剧情标记「已播」）。"""
    fn = os.path.basename(vpath)
    url = _dq_battle_video_http_url(fn)
    url_esc = html_escape.escape(url, quote=True)
    _adv_flag = "1" if click_adventure_tab_after else "0"
    _boot_extra = ""
    if q1_act1_bgm_sync:
        _prontera = "SoundTeMP - Theme of Prontera.mp3"
        _pk = html_escape.escape(q1_act1_player_key or "hero", quote=True)
        _rr = html_escape.escape(f"/api/music/{quote(_prontera)}", quote=True)
        _ra = html_escape.escape(_dq_music_track_url(_prontera), quote=True)
        _boot_extra = f' data-q1a1="1" data-ssk="{_pk}" data-resume-rel="{_rr}" data-resume-abs="{_ra}"'
    html = (
        f"""<div id="dqbv-boot" data-url="{url_esc}" data-click-adv="{_adv_flag}"{_boot_extra} style="display:none;width:0;height:0;" aria-hidden="true"></div>
<script>
(function() {{
  var boot = document.getElementById("dqbv-boot");
  if (!boot) return;
  var url = boot.getAttribute("data-url");
  var clickAdv = boot.getAttribute("data-click-adv") === "1";
  if (!url) return;
  var q1a1 = boot.getAttribute("data-q1a1") === "1";
  var ssKey = boot.getAttribute("data-ssk") || "hero";
  var resumeRel = boot.getAttribute("data-resume-rel") || "";
  var resumeAbs = boot.getAttribute("data-resume-abs") || "";
  function storKey() {{ return "dq_q1a1_vid_" + ssKey; }}
  function pauseGlobalBgmForStory() {{
    try {{
      var g = targetDoc.getElementById("dq-global-audio-player");
      if (!g) return;
      g.dataset.storyHold = "1";
      g.pause();
    }} catch (e6) {{}}
  }}
  function resumeGlobalBgmAfterQ1Story(natural) {{
    try {{
      var g = targetDoc.getElementById("dq-global-audio-player");
      if (g) delete g.dataset.storyHold;
      if (q1a1 && natural) {{
        try {{ sessionStorage.setItem(storKey(), "1"); }} catch (e7) {{}}
        if (g && (resumeRel || resumeAbs)) {{
          var cands = [];
          if (resumeRel) cands.push(resumeRel);
          if (resumeAbs && resumeAbs !== resumeRel) cands.push(resumeAbs);
          var p = 0;
          function tryCand() {{
            if (!g || p >= cands.length) {{
              if (g) g.play().catch(function () {{}});
              return;
            }}
            g.onerror = function () {{ p++; tryCand(); }};
            g.src = cands[p];
            g.load();
            g.play().catch(function () {{ p++; tryCand(); }});
          }}
          tryCand();
          return;
        }}
      }}
      if (g) g.play().catch(function () {{}});
    }} catch (e8) {{}}
  }}

  function shrinkComponentIframe() {{
    try {{
      var fe = window.frameElement;
      if (!fe) return;
      fe.style.cssText = "height:0!important;min-height:0!important;max-height:0!important;width:100%!important;border:0!important;display:block!important;overflow:hidden!important;margin:0!important;padding:0!important;line-height:0!important;";
      var w = fe.parentElement;
      if (w) {{
        w.style.height = "0";
        w.style.minHeight = "0";
        w.style.maxHeight = "0";
        w.style.padding = "0";
        w.style.margin = "0";
        w.style.overflow = "hidden";
        w.style.lineHeight = "0";
      }}
      var ww = w && w.parentElement;
      if (ww) {{
        ww.style.paddingBottom = "0";
        ww.style.marginBottom = "0";
        ww.style.minHeight = "0";
      }}
    }} catch (e) {{}}
  }}

  var targetDoc = null;
  try {{
    if (window.parent && window.parent !== window && window.parent.document) {{
      targetDoc = window.parent.document;
    }}
  }} catch (e1) {{ targetDoc = null; }}
  if (!targetDoc) targetDoc = document;

  var oid = "dqbv-overlay-root";
  var old = targetDoc.getElementById(oid);
  if (old) try {{ old.remove(); }} catch (e2) {{}}

  var root = targetDoc.createElement("div");
  root.id = oid;
  root.setAttribute("role", "dialog");
  root.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:rgba(15,23,42,0.78);display:flex;align-items:center;justify-content:center;padding:12px;box-sizing:border-box;";

  var card = targetDoc.createElement("div");
  card.style.cssText = "background:#1e293b;padding:14px;border-radius:14px;box-shadow:0 25px 80px rgba(0,0,0,0.5);max-width:min(96vw,920px);width:100%;box-sizing:border-box;";

  var v = targetDoc.createElement("video");
  v.setAttribute("playsinline", "");
  v.autoplay = true;
  v.src = url;
  v.style.cssText = "width:100%;max-height:78vh;display:block;border-radius:10px;background:#000;cursor:pointer;";
  v.setAttribute("title", "单击跳过");

  var finished = false;
  function finish(natural) {{
    if (finished) return;
    finished = true;
    try {{ v.pause(); v.removeAttribute("src"); v.load(); }} catch (e3) {{}}
    try {{ root.remove(); }} catch (e4) {{}}
    shrinkComponentIframe();
    resumeGlobalBgmAfterQ1Story(!!natural);
    if (clickAdv) {{
      setTimeout(function() {{
        try {{
          function norm(s) {{ return String(s || "").replace(/\\s+/g, ""); }}
          function go(doc) {{
            if (!doc || !doc.querySelectorAll) return false;
            var bars = [];
            try {{ bars = doc.querySelectorAll('[data-testid="stTabs"] [role="tab"]'); }} catch (eA) {{}}
            if (!bars || !bars.length) {{
              try {{ bars = doc.querySelectorAll('[role="tab"]'); }} catch (eB) {{ return false; }}
            }}
            for (var i = 0; i < bars.length; i++) {{
              var t = norm(bars[i].innerText || bars[i].textContent);
              if (t.indexOf("冒险") >= 0) {{ bars[i].click(); return true; }}
            }}
            return false;
          }}
          var w = window;
          for (var k = 0; k < 12; k++) {{
            try {{ if (go(w.document)) break; }} catch (eC) {{}}
            if (!w.parent || w.parent === w) break;
            try {{ w = w.parent; }} catch (eD) {{ break; }}
          }}
        }} catch (e5) {{}}
      }}, 120);
    }}
  }}

  v.addEventListener("click", function (ev) {{
    try {{ ev.preventDefault(); ev.stopPropagation(); }} catch (e0) {{}}
    finish(false);
  }});
  v.addEventListener("ended", function () {{ finish(true); }});
  v.addEventListener("error", function () {{ finish(false); }});

  card.appendChild(v);
  root.appendChild(card);
  targetDoc.body.appendChild(root);
  if (q1a1) pauseGlobalBgmForStory();

  v.play().catch(function () {{ finish(false); }});
  shrinkComponentIframe();
}})();
</script>"""
    )
    components.html(html, height=1, width=1, scrolling=False)
    return True


def _dq_q1_act1_split_video_paths(state: Dict[str, Any], dq: Any) -> List[str]:
    """
    Q1 第一幕分集：video/ 下「主线 stem」+ _P1 / _P2 / …（.mp4），按 P 后数字升序。
    无分集文件时返回空列表，由调用方回退到单文件 stem。
    """
    stem = str(dq.dq_main_story_video_stem(state) or "").strip()
    if not stem:
        return []
    cands = _dq_paths_for_battle_video_stem(stem)
    rx = re.compile(r"^" + re.escape(stem) + r"_P(\d+)$")
    scored: List[Tuple[int, str]] = []
    for pth in cands:
        base = os.path.splitext(os.path.basename(pth))[0]
        m = rx.match(base)
        if m and os.path.isfile(pth):
            scored.append((int(m.group(1)), pth))
    scored.sort(key=lambda x: x[0])
    return [p for _, p in scored]


def _dq_render_battle_video_popup_sequence(
    paths: List[str],
    *,
    click_adventure_tab_after: bool = False,
    q1_act1_bgm_sync: bool = False,
    q1_act1_player_key: str = "",
) -> bool:
    """同一遮罩内顺序播放多段本地视频（自动连播）；单段时委托给 _dq_render_battle_video_popup。成功注入返回 True。"""
    ok = [p for p in (paths or []) if p and os.path.isfile(p)]
    if not ok:
        return False
    if len(ok) == 1:
        return _dq_render_battle_video_popup(
            ok[0],
            click_adventure_tab_after=click_adventure_tab_after,
            q1_act1_bgm_sync=q1_act1_bgm_sync,
            q1_act1_player_key=q1_act1_player_key,
        )
    http_urls = [_dq_battle_video_http_url(os.path.basename(p)) for p in ok]
    payload = base64.b64encode(json.dumps(http_urls, ensure_ascii=False).encode("utf-8")).decode("ascii")
    _adv_flag = "1" if click_adventure_tab_after else "0"
    _boot_extra = ""
    if q1_act1_bgm_sync:
        _prontera = "SoundTeMP - Theme of Prontera.mp3"
        _pk = html_escape.escape(q1_act1_player_key or "hero", quote=True)
        _rr = html_escape.escape(f"/api/music/{quote(_prontera)}", quote=True)
        _ra = html_escape.escape(_dq_music_track_url(_prontera), quote=True)
        _boot_extra = f' data-q1a1="1" data-ssk="{_pk}" data-resume-rel="{_rr}" data-resume-abs="{_ra}"'
    html = (
        f"""<div id="dqbv-seq-boot" data-b64="{html_escape.escape(payload, quote=True)}" data-click-adv="{_adv_flag}"{_boot_extra} style="display:none;width:0;height:0;" aria-hidden="true"></div>
<script>
(function() {{
  var boot = document.getElementById("dqbv-seq-boot");
  if (!boot) return;
  var b64 = boot.getAttribute("data-b64");
  var clickAdv = boot.getAttribute("data-click-adv") === "1";
  if (!b64) return;
  var urls;
  try {{
    urls = JSON.parse(atob(b64));
  }} catch (e0) {{ return; }}
  if (!urls || !urls.length) return;
  var q1a1 = boot.getAttribute("data-q1a1") === "1";
  var ssKey = boot.getAttribute("data-ssk") || "hero";
  var resumeRel = boot.getAttribute("data-resume-rel") || "";
  var resumeAbs = boot.getAttribute("data-resume-abs") || "";
  function storKey() {{ return "dq_q1a1_vid_" + ssKey; }}
  function pauseGlobalBgmForStory() {{
    try {{
      var g = targetDoc.getElementById("dq-global-audio-player");
      if (!g) return;
      g.dataset.storyHold = "1";
      g.pause();
    }} catch (e6) {{}}
  }}
  function resumeGlobalBgmAfterQ1Story(natural) {{
    try {{
      var g = targetDoc.getElementById("dq-global-audio-player");
      if (g) delete g.dataset.storyHold;
      if (q1a1 && natural) {{
        try {{ sessionStorage.setItem(storKey(), "1"); }} catch (e7) {{}}
        if (g && (resumeRel || resumeAbs)) {{
          var cands = [];
          if (resumeRel) cands.push(resumeRel);
          if (resumeAbs && resumeAbs !== resumeRel) cands.push(resumeAbs);
          var p = 0;
          function tryCand() {{
            if (!g || p >= cands.length) {{
              if (g) g.play().catch(function () {{}});
              return;
            }}
            g.onerror = function () {{ p++; tryCand(); }};
            g.src = cands[p];
            g.load();
            g.play().catch(function () {{ p++; tryCand(); }});
          }}
          tryCand();
          return;
        }}
      }}
      if (g) g.play().catch(function () {{}});
    }} catch (e8) {{}}
  }}

  function shrinkComponentIframe() {{
    try {{
      var fe = window.frameElement;
      if (!fe) return;
      fe.style.cssText = "height:0!important;min-height:0!important;max-height:0!important;width:100%!important;border:0!important;display:block!important;overflow:hidden!important;margin:0!important;padding:0!important;line-height:0!important;";
      var w = fe.parentElement;
      if (w) {{
        w.style.height = "0";
        w.style.minHeight = "0";
        w.style.maxHeight = "0";
        w.style.padding = "0";
        w.style.margin = "0";
        w.style.overflow = "hidden";
        w.style.lineHeight = "0";
      }}
      var ww = w && w.parentElement;
      if (ww) {{
        ww.style.paddingBottom = "0";
        ww.style.marginBottom = "0";
        ww.style.minHeight = "0";
      }}
    }} catch (e) {{}}
  }}

  var targetDoc = null;
  try {{
    if (window.parent && window.parent !== window && window.parent.document) {{
      targetDoc = window.parent.document;
    }}
  }} catch (e1) {{ targetDoc = null; }}
  if (!targetDoc) targetDoc = document;

  var oid = "dqbv-overlay-root";
  var old = targetDoc.getElementById(oid);
  if (old) try {{ old.remove(); }} catch (e2) {{}}

  var root = targetDoc.createElement("div");
  root.id = oid;
  root.setAttribute("role", "dialog");
  root.style.cssText = "position:fixed;inset:0;z-index:2147483647;background:rgba(15,23,42,0.78);display:flex;align-items:center;justify-content:center;padding:12px;box-sizing:border-box;";

  var card = targetDoc.createElement("div");
  card.style.cssText = "background:#1e293b;padding:14px;border-radius:14px;box-shadow:0 25px 80px rgba(0,0,0,0.5);max-width:min(96vw,920px);width:100%;box-sizing:border-box;";

  var v = targetDoc.createElement("video");
  v.setAttribute("playsinline", "");
  v.autoplay = true;
  v.style.cssText = "width:100%;max-height:78vh;display:block;border-radius:10px;background:#000;cursor:pointer;";
  v.setAttribute("title", "单击跳过");

  var idx = 0;
  v.src = urls[0];

  var finished = false;
  function finish(natural) {{
    if (finished) return;
    finished = true;
    try {{ v.pause(); v.removeAttribute("src"); v.load(); }} catch (e3) {{}}
    try {{ root.remove(); }} catch (e4) {{}}
    shrinkComponentIframe();
    resumeGlobalBgmAfterQ1Story(!!natural);
    if (clickAdv) {{
      setTimeout(function() {{
        try {{
          function norm(s) {{ return String(s || "").replace(/\\s+/g, ""); }}
          function go(doc) {{
            if (!doc || !doc.querySelectorAll) return false;
            var bars = [];
            try {{ bars = doc.querySelectorAll('[data-testid="stTabs"] [role="tab"]'); }} catch (eA) {{}}
            if (!bars || !bars.length) {{
              try {{ bars = doc.querySelectorAll('[role="tab"]'); }} catch (eB) {{ return false; }}
            }}
            for (var i = 0; i < bars.length; i++) {{
              var t = norm(bars[i].innerText || bars[i].textContent);
              if (t.indexOf("冒险") >= 0) {{ bars[i].click(); return true; }}
            }}
            return false;
          }}
          var w = window;
          for (var k = 0; k < 12; k++) {{
            try {{ if (go(w.document)) break; }} catch (eC) {{}}
            if (!w.parent || w.parent === w) break;
            try {{ w = w.parent; }} catch (eD) {{ break; }}
          }}
        }} catch (e5) {{}}
      }}, 120);
    }}
  }}

  v.addEventListener("click", function (ev) {{
    try {{ ev.preventDefault(); ev.stopPropagation(); }} catch (e0) {{}}
    finish(false);
  }});
  v.addEventListener("ended", function () {{
    idx++;
    if (idx >= urls.length) {{ finish(true); return; }}
    v.src = urls[idx];
    v.play().catch(function () {{ finish(false); }});
  }});
  v.addEventListener("error", function () {{ finish(false); }});

  card.appendChild(v);
  root.appendChild(card);
  targetDoc.body.appendChild(root);
  if (q1a1) pauseGlobalBgmForStory();

  v.play().catch(function () {{ finish(false); }});
  shrinkComponentIframe();
}})();
</script>"""
    )
    components.html(html, height=1, width=1, scrolling=False)
    return True


def _dq_try_render_pending_story_video(state: Dict[str, Any], dq: Any) -> bool:
    """
    存在 pending_story 时尝试播放对应剧情视频；仅在真正注入播放器成功后写入 dq_last_story_video_key，
    避免「先写 key、后因文件校验失败未播」导致永不重试。
    """
    meta = state.get("meta") or {}
    pending_story = meta.get("pending_story")
    if not isinstance(pending_story, dict):
        return False
    _story_vid_key = f"{pending_story.get('sid', '')}_{pending_story.get('step', 0)}"
    _story_stem = dq.dq_main_story_video_stem(state)
    _seq_paths: List[str] = []
    _story_vpath = ""
    if (
        str(pending_story.get("sid", "")) == "q1_seal_whisper"
        and int(pending_story.get("step", 0) or 0) == 0
    ):
        _seq_paths = _dq_q1_act1_split_video_paths(state, dq)
    if _seq_paths:
        _story_vid_key = f"{_story_vid_key}_seq{len(_seq_paths)}"
    elif _story_stem:
        _story_vpath = _dq_resolve_battle_video_path(_story_stem)
        if not _story_vpath:
            _cands = _dq_paths_for_battle_video_stem(_story_stem)
            _story_vpath = _cands[0] if _cands else ""
    if st.session_state.get("dq_last_story_video_key") == _story_vid_key:
        return False
    _q1_act1 = (
        str(pending_story.get("sid", "")) == "q1_seal_whisper"
        and int(pending_story.get("step", 0) or 0) == 0
    )
    _pkey = _dq_q1_act1_storage_key_suffix(state)
    _sync_bgm = bool(
        _q1_act1
        and (
            bool(_seq_paths)
            or (bool(_story_vpath) and os.path.isfile(str(_story_vpath)))
        )
    )
    played = False
    if _seq_paths:
        played = bool(
            _dq_render_battle_video_popup_sequence(
                _seq_paths,
                click_adventure_tab_after=False,
                q1_act1_bgm_sync=_sync_bgm,
                q1_act1_player_key=_pkey,
            )
        )
    elif _story_vpath and os.path.isfile(_story_vpath):
        played = _dq_render_battle_video_popup(
            _story_vpath,
            click_adventure_tab_after=False,
            q1_act1_bgm_sync=_sync_bgm,
            q1_act1_player_key=_pkey,
        )
    if played:
        st.session_state["dq_last_story_video_key"] = _story_vid_key
    return played


def _dq_battle_unit_card(
    name: str,
    avatar_path: str,
    hp: int,
    max_hp: int,
    mp: int,
    max_mp: int,
    *,
    show_mp: bool = True,
) -> None:
    """与「冒险 → 战斗」页 `show_dq_game_page` 内嵌卡片同一套样式。"""

    def _pct(v: int, m: int) -> int:
        return int(max(0, min(100, round((v / max(1, m)) * 100))))

    hp_pct = _pct(hp, max_hp)
    mp_pct = _pct(mp, max_mp)
    safe_name = html_escape.escape(str(name or ""))
    with st.container(border=True):
        st.markdown(
            f"<div style='background:#f1f5f9;color:#1f2937;border:1px solid #dbe4ee;border-radius:8px;padding:4px 8px;margin-bottom:6px;font-weight:700;'>{safe_name}</div>",
            unsafe_allow_html=True,
        )
        ac1, ac2 = st.columns([1, 3])
        with ac1:
            if avatar_path:
                st.image(avatar_path, width=56)
        with ac2:
            st.markdown(f"HP {hp}/{max_hp}（{hp_pct}%）")
            st.markdown(
                f"<div style='height:8px;background:#2a2a2a;border-radius:6px;overflow:hidden;'><div style='width:{hp_pct}%;height:100%;background:#e74c3c;'></div></div>",
                unsafe_allow_html=True,
            )
            if show_mp:
                st.markdown(f"MP {mp}/{max_mp}（{mp_pct}%）")
                st.markdown(
                    f"<div style='height:8px;background:#2a2a2a;border-radius:6px;overflow:hidden;'><div style='width:{mp_pct}%;height:100%;background:#3498db;'></div></div>",
                    unsafe_allow_html=True,
                )


def _dq_pvp_dialog_reset() -> None:
    for k in (
        "dq_pvp_dialog",
        "dq_pvp_phase",
        "dq_pvp_room_id",
        "dq_pvp_role",
        "dq_pvp_token",
    ):
        st.session_state.pop(k, None)


def _dq_pvp_target_rows(
    battle: Dict[str, Any], my_role: str, hs: Dict[str, Any], gs: Dict[str, Any]
) -> List[Tuple[str, str]]:
    """当前玩家可攻击的对手单位 (target_id, 标签)；房主打 g_*，挑战者打 h_*。"""
    prefix = "g" if my_role == "host" else "h"
    opp_snap = gs if my_role == "host" else hs
    opp_hero = (battle.get("guest_hero") if my_role == "host" else battle.get("host_hero")) or {}
    opp_party = (battle.get("guest_party") if my_role == "host" else battle.get("host_party")) or []
    rows: List[Tuple[str, str]] = []
    hhp = int(opp_hero.get("hp", 0) or 0)
    if hhp > 0:
        rows.append(
            (
                f"{prefix}_hero",
                f"{opp_snap.get('hero_name', '?')}（主角） HP {hhp}",
            )
        )
    party_snap = opp_snap.get("party") or []
    for i, p in enumerate(party_snap):
        if not isinstance(p, dict) or i >= len(opp_party):
            continue
        hp_i = int(opp_party[i].get("hp", 0) or 0)
        if hp_i > 0:
            hn = str(opp_snap.get("hero_name", "?"))
            rows.append((f"{prefix}_p{i}", f"{hn}·{p.get('name', '?')}（队友） HP {hp_i}"))
    return rows


def _dq_pvp_alive_keys(battle: Dict[str, Any], role: str) -> List[str]:
    """本方当前存活单位 actor 键列表。"""
    side = "host" if role == "host" else "guest"
    hh = battle.get(f"{side}_hero") or {}
    pp = battle.get(f"{side}_party") or []
    keys: List[str] = []
    if int(hh.get("hp", 0) or 0) > 0:
        keys.append(f"{side}:hero")
    for i, row in enumerate(pp):
        if int(row.get("hp", 0) or 0) > 0:
            keys.append(f"{side}:p{i}")
    return keys


def _dq_pvp_card_title(ak: str, hs: Dict[str, Any], gs: Dict[str, Any]) -> str:
    """卡片标题：队友为 主角名·队友名。"""
    parts = ak.split(":")
    if len(parts) != 2:
        return ak
    side, slot = parts[0], parts[1]
    snap = hs if side == "host" else gs
    hn = str(snap.get("hero_name", "?"))
    if slot == "hero":
        return f"{hn}（主角）"
    if slot.startswith("p") and slot[1:].isdigit():
        i = int(slot[1:])
        pm = snap.get("party") or []
        if isinstance(pm, list) and i < len(pm) and isinstance(pm[i], dict):
            return f"{hn}·{pm[i].get('name', '?')}"
    return ak


def _dq_pvp_skills_for_actor(
    actor: str, my_role: str, hs: Dict[str, Any], gs: Dict[str, Any], local_snap: Dict[str, Any]
) -> List[str]:
    """轮到本地玩家时，按行动单位取技能栏（主角用本地快照；队友用房间内对方/己方已上传快照）。"""
    _ban = frozenset({"heavy_strike", "execution", "armor_break"})
    if my_role == "host" and actor.startswith("host:"):
        snap = local_snap if actor == "host:hero" else hs
    elif my_role == "guest" and actor.startswith("guest:"):
        snap = local_snap if actor == "guest:hero" else gs
    else:
        return []
    slot = actor.split(":")[-1] if ":" in actor else ""
    if slot == "hero":
        raw = list(snap.get("skills") or []) if isinstance(snap, dict) else []
    elif slot.startswith("p") and slot[1:].isdigit():
        idx = int(slot[1:])
        pm = (snap.get("party") or []) if isinstance(snap, dict) else []
        if isinstance(pm, list) and idx < len(pm) and isinstance(pm[idx], dict):
            raw = list(pm[idx].get("skills") or [])
        else:
            raw = []
    else:
        raw = []
    return [str(s) for s in raw if s and str(s) not in _ban]


def _pvp_render_side_battle_cards(
    title: str,
    hero_label: str,
    hero_snap: Dict[str, Any],
    hero_battle: Dict[str, Any],
    party_snap: Any,
    party_battle: Any,
) -> None:
    """PVP 对战：与单机战斗相同卡片样式，每行最多 3 张。"""
    st.markdown(f"##### {title}")
    lv = int(hero_snap.get("level", 1) or 1)
    hn = str(hero_snap.get("hero_name", hero_label))
    role_h = str(hero_snap.get("role", "warrior"))
    specs: List[Dict[str, Any]] = [
        {
            "name": f"{hn}（Lv{lv}）主角",
            "role": role_h,
            "hp": int(hero_battle.get("hp", 0) or 0),
            "max_hp": max(1, int(hero_snap.get("max_hp", 1) or 1)),
            "mp": int(hero_battle.get("mp", 0) or 0),
            "max_mp": max(1, int(hero_snap.get("max_mp", 1) or 1)),
            "show_mp": True,
        }
    ]
    ps = party_snap if isinstance(party_snap, list) else []
    pb = party_battle if isinstance(party_battle, list) else []
    for i, p in enumerate(ps):
        if not isinstance(p, dict) or i >= len(pb):
            break
        alv = int(p.get("level", lv) or lv)
        mm = int(p.get("max_mp", 0) or 0)
        specs.append(
            {
                "name": f"{hn}·{p.get('name', '?')}（Lv{alv}）",
                "role": str(p.get("role", "warrior")),
                "hp": int(pb[i].get("hp", 0) or 0),
                "max_hp": max(1, int(p.get("max_hp", 1) or 1)),
                "mp": int(pb[i].get("mp", 0) or 0),
                "max_mp": max(1, mm) if mm > 0 else 1,
                "show_mp": mm > 0,
            }
        )
    for i, c in enumerate(specs):
        if i % 3 == 0:
            row_cols = st.columns(3)
        hg0 = str(hero_snap.get("hero_gender") or "男") if i == 0 else None
        av = _dq_avatar_url_for_battle("hero", c["role"], hero_gender=hg0)
        with row_cols[i % 3]:
            _dq_battle_unit_card(
                name=c["name"],
                avatar_path=av,
                hp=c["hp"],
                max_hp=c["max_hp"],
                mp=c["mp"],
                max_mp=c["max_mp"],
                show_mp=bool(c["show_mp"]),
            )


def _pvp_render_room_phase_body(
    _dq_mod: Any,
    state: Dict[str, Any],
    rid: str,
    role: str,
    token: str,
    _leave: Any,
) -> None:
    """PVP 房间内 UI（等待 / 对战）；房间数据在整页渲染时拉取；轻量 fragment 仅轮询指纹，有变化才 st.rerun。"""
    room_data: Dict[str, Any] = {}
    try:
        rr = requests.get(_dq_pvp_url(f"/api/pvp/room/{rid}"), timeout=12)
        if rr.ok:
            room_data = (rr.json() or {}).get("room") or {}
            sig = _pvp_room_signature(room_data)
            if sig:
                st.session_state[f"pvp_room_sig_{rid}"] = sig
        else:
            st.error("房间已失效或服务器无响应，请关闭后重试。")
    except Exception as e:
        st.warning(f"同步房间失败：{e}")

    ph = str(room_data.get("phase") or "waiting")
    hs = room_data.get("host_snapshot") or {}
    gs = room_data.get("guest_snapshot") or {}
    gr = bool(room_data.get("guest_ready"))
    has_guest = bool(gs and str(gs.get("hero_name") or "").strip())

    st.markdown(f"### 房间 `{rid}`")
    st.markdown(
        f"- **槽位 1（房主）** {hs.get('hero_name', '—')} · Lv{hs.get('level', '?')}"
    )
    guest_line = (
        f"{gs.get('hero_name', '—')} · Lv{gs.get('level', '?')}"
        if has_guest
        else "（空）等待加入…"
    )
    st.markdown(f"- **槽位 2（挑战者）** {guest_line}")
    if has_guest:
        pm = gs.get("party") or []
        if isinstance(pm, list) and pm:
            st.caption(
                "对方队友："
                + "、".join(
                    f"{p.get('name', '?')}({p.get('role', '')})" for p in pm if isinstance(p, dict)
                )
            )

    st.markdown("---")
    st.caption("后台约每 5 秒检查一次；**仅当房间数据有变化时**才刷新界面，减少卡顿与灰屏闪烁。")

    if ph == "waiting":
        rf2, rf3 = st.columns([1, 2])
        with rf2:
            if role == "guest" and has_guest and not gr:
                if st.button("准备", type="primary", key="dq_pvp_ready"):
                    try:
                        r = requests.post(
                            _dq_pvp_url("/api/pvp/ready"),
                            json={"room_id": rid, "token": token},
                            timeout=12,
                        )
                        j = r.json() if r.content else {}
                        if r.ok and j.get("ok"):
                            st.rerun()
                        st.error(j.get("error", "准备失败"))
                    except Exception as e:
                        st.error(str(e))
        can_start = bool(role == "host" and has_guest and gr)
        with rf3:
            if role == "host":
                if st.button(
                    "开始对战",
                    type="primary",
                    key="dq_pvp_start",
                    disabled=not can_start,
                    help="需挑战者已进入并点击「准备」",
                ):
                    try:
                        r = requests.post(
                            _dq_pvp_url("/api/pvp/start"),
                            json={"room_id": rid, "token": token},
                            timeout=12,
                        )
                        j = r.json() if r.content else {}
                        if r.ok and j.get("ok"):
                            st.rerun()
                        st.error(j.get("error", "无法开始"))
                    except Exception as e:
                        st.error(str(e))
            else:
                st.caption("等待房主开始…（请先点「准备」）" if not gr else "等待房主开始对战…")

    elif ph == "battle":
        b = room_data.get("battle") or {}
        rnd = int(b.get("round") or 1)
        hh = b.get("host_hero") or {}
        gh = b.get("guest_hero") or {}
        hpp = b.get("host_party") or []
        gpp = b.get("guest_party") or []
        hn = str(hs.get("hero_name", "房主"))
        gn = str(gs.get("hero_name", "挑战者"))
        st.subheader("对战")
        st.caption(
            f"第 **{rnd}** 回合 · 为本方每名存活单位选择 **普攻 / 技能 / 防守**，一次性提交；"
            "双方均提交后服务器按 **先攻值（0～10 随机 + 有效 AGI）** 从高到低依次结算。"
        )

        _pvp_render_side_battle_cards(f"房主 · {hn}", hn, hs, hh, hs.get("party"), hpp)
        _pvp_render_side_battle_cards(f"挑战者 · {gn}", gn, gs, gh, gs.get("party"), gpp)

        logs = b.get("log") or []
        st.markdown(
            _dq_pvp_battle_log_html([str(x) for x in logs], max_lines=260, max_height="320px"),
            unsafe_allow_html=True,
        )
        res = b.get("result")
        h_sub = bool(b.get("host_plan_submitted"))
        g_sub = bool(b.get("guest_plan_submitted"))
        my_sub = h_sub if role == "host" else g_sub
        peer_sub = g_sub if role == "host" else h_sub
        tgt_rows = _dq_pvp_target_rows(b, role, hs, gs)
        local_snap = _dq_mod.dq_pvp_export_snapshot(state)
        local_keys = _dq_pvp_alive_keys(b, role)

        if not res:
            _pvp_side = "host" if role == "host" else "guest"
            _pvp_hero_def_cd = int(b.get(f"{_pvp_side}_defend_cd", 0) or 0)
            if my_sub and peer_sub:
                st.caption("双方已提交，正在同步结算…页面会自动刷新。")
            elif my_sub:
                st.info("你已提交本回合指令，等待对方提交。")
            elif peer_sub:
                st.warning("对方已提交，请为本方每名存活单位设好指令后点击「提交本回合指令」。")
            if not my_sub and local_keys:
                st.markdown("##### 本回合指令（一次性提交）")
                for ak in local_keys:
                    ct = _dq_pvp_card_title(ak, hs, gs)
                    st.markdown(f"**{ct}** (`{ak}`)")
                    c_mode, c_sk = st.columns([1.2, 2.8])
                    with c_mode:
                        _pvp_mode_opts = ["普攻", "技能", "防守"]
                        if str(ak) == f"{_pvp_side}:hero" and _pvp_hero_def_cd > 0:
                            _pvp_mode_opts = ["普攻", "技能"]
                        act_mode = st.radio(
                            "行动",
                            _pvp_mode_opts,
                            horizontal=True,
                            key=f"pvp_mode_{rid}_{rnd}_{ak}",
                            label_visibility="collapsed",
                        )
                    sks = _dq_pvp_skills_for_actor(ak, role, hs, gs, local_snap)
                    sid_cur = ""
                    need_t = False
                    with c_sk:
                        if act_mode == "技能" and sks:
                            st.caption("技能（单选）")
                            st.radio(
                                "技能",
                                sks,
                                format_func=lambda s: _dq_mod.dq_skill_name(s),
                                key=f"pvp_sk_{rid}_{rnd}_{ak}",
                                label_visibility="collapsed",
                                horizontal=len(sks) <= 5,
                            )
                            sid_cur = str(
                                st.session_state.get(f"pvp_sk_{rid}_{rnd}_{ak}") or sks[0]
                            )
                            need_t = bool(_dq_mod.dq_pvp_skill_needs_target(sid_cur))
                        elif act_mode == "技能":
                            st.caption("未装备可用技能")
                        elif act_mode == "防守":
                            st.caption("本回合防守")
                    show_enemy = bool(
                        tgt_rows
                        and (
                            act_mode == "普攻"
                            or (act_mode == "技能" and sks and need_t)
                        )
                    )
                    if show_enemy:
                        ids = [x[0] for x in tgt_rows]
                        labs = {x[0]: x[1] for x in tgt_rows}
                        st.caption("敌方目标（普攻与需选目标的技能共用，单选）")
                        st.radio(
                            "敌方目标",
                            ids,
                            format_func=lambda i: labs.get(i, i),
                            key=f"pvp_enemy_{rid}_{rnd}_{ak}",
                            label_visibility="collapsed",
                            horizontal=len(ids) <= 4,
                        )
                    elif act_mode == "普攻" and not tgt_rows:
                        st.caption("无可用目标")
                    elif act_mode == "技能" and sks and not need_t and tgt_rows:
                        st.caption("该技能无需选择敌方目标（将自动挂接）")
                if st.button("提交本回合指令", type="primary", key=f"pvp_submit_{rid}_{rnd}"):
                    plans: Dict[str, Any] = {}
                    ok = True
                    for ak in local_keys:
                        mode = st.session_state.get(f"pvp_mode_{rid}_{rnd}_{ak}", "普攻")
                        if mode == "防守":
                            plans[ak] = {"kind": "defend"}
                        elif mode == "普攻":
                            if not tgt_rows:
                                ok = False
                                break
                            tid = st.session_state.get(f"pvp_enemy_{rid}_{rnd}_{ak}")
                            if not tid:
                                ok = False
                                break
                            plans[ak] = {"kind": "attack", "target_id": tid}
                        else:
                            sks2 = _dq_pvp_skills_for_actor(ak, role, hs, gs, local_snap)
                            if not sks2:
                                ok = False
                                break
                            sid = st.session_state.get(f"pvp_sk_{rid}_{rnd}_{ak}")
                            if not sid:
                                sid = sks2[0]
                            need_t = _dq_mod.dq_pvp_skill_needs_target(str(sid))
                            body: Dict[str, Any] = {"kind": "skill", "sid": sid}
                            if need_t:
                                if not tgt_rows:
                                    ok = False
                                    break
                                tid = st.session_state.get(f"pvp_enemy_{rid}_{rnd}_{ak}")
                                if not tid:
                                    tid = tgt_rows[0][0]
                                body["target_id"] = tid
                            else:
                                if tgt_rows:
                                    body["target_id"] = tgt_rows[0][0]
                            plans[ak] = body
                    if not ok:
                        st.error("请为每名单位补全目标或技能。")
                    else:
                        try:
                            r = requests.post(
                                _dq_pvp_url("/api/pvp/battle/plan"),
                                json={"room_id": rid, "token": token, "plans": plans},
                                timeout=20,
                            )
                            j = r.json() if r.content else {}
                            if r.ok and j.get("ok"):
                                if j.get("resolved"):
                                    st.success("回合已结算！")
                                st.rerun()
                            st.error(j.get("error", "提交失败"))
                        except Exception as e:
                            st.error(str(e))
        else:
            if res == "host_win":
                st.success(f"🏆 {hn} 获胜！")
            else:
                st.success(f"🏆 {gn} 获胜！")

    st.markdown("---")
    if st.button("关闭并离开房间", key="dq_pvp_room_close"):
        _leave()
        st.rerun()


def _dq_render_pvp_dialog(_dq_mod: Any, state: Dict[str, Any]) -> None:
    """PVP：创建/加入房间、准备、开始；对战为同步回合（本方全员指令一次性提交，双方齐后按先攻结算）。"""
    dlg = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
    if not dlg or not st.session_state.get("dq_pvp_dialog"):
        return

    @dlg("⚔️ PVP 竞技场", width="large")
    def _pvp_inner() -> None:
        snap = _dq_mod.dq_pvp_export_snapshot(state)
        phase_ui = str(st.session_state.get("dq_pvp_phase") or "menu")
        rid = str(st.session_state.get("dq_pvp_room_id") or "")
        role = str(st.session_state.get("dq_pvp_role") or "")
        token = str(st.session_state.get("dq_pvp_token") or "")

        def _leave() -> None:
            try:
                if rid and token:
                    requests.post(
                        _dq_pvp_url("/api/pvp/leave"),
                        json={"room_id": rid, "token": token},
                        timeout=8,
                    )
            except Exception:
                pass
            _dq_pvp_dialog_reset()

        if phase_ui == "menu":
            st.caption("创建房间后告知对手 **4 位房间号**；对方选「加入房间」并输入相同号码。")
            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("创建房间", type="primary", key="dq_pvp_create"):
                    try:
                        r = requests.post(_dq_pvp_url("/api/pvp/create"), json={"snapshot": snap}, timeout=15)
                        j = r.json() if r.content else {}
                        if r.ok and j.get("ok"):
                            st.session_state["dq_pvp_room_id"] = str(j.get("room_id", ""))
                            st.session_state["dq_pvp_token"] = str(j.get("host_token", ""))
                            st.session_state["dq_pvp_role"] = "host"
                            st.session_state["dq_pvp_phase"] = "room"
                            st.rerun()
                        st.error(j.get("error", r.text or "创建失败"))
                    except Exception as e:
                        st.error(f"连接失败：{e}（请确认后端已启动并可访问）")
            with c2:
                if st.button("加入房间", key="dq_pvp_goto_join"):
                    st.session_state["dq_pvp_phase"] = "join"
                    st.rerun()
            with c3:
                if st.button("关闭", key="dq_pvp_close_menu"):
                    _leave()
                    st.rerun()
            return

        if phase_ui == "join":
            st.text_input("4 位房间号", max_chars=4, key="dq_pvp_join_code_in", placeholder="例如 0824")
            j1, j2 = st.columns(2)
            with j1:
                if st.button("确认加入", type="primary", key="dq_pvp_join_do"):
                    code = (st.session_state.get("dq_pvp_join_code_in") or "").strip()
                    if not (len(code) == 4 and code.isdigit()):
                        st.error("请输入 4 位数字房间号。")
                    else:
                        try:
                            r = requests.post(
                                _dq_pvp_url("/api/pvp/join"),
                                json={"room_id": code, "snapshot": snap},
                                timeout=15,
                            )
                            j = r.json() if r.content else {}
                            if r.ok and j.get("ok"):
                                st.session_state["dq_pvp_room_id"] = str(j.get("room_id", ""))
                                st.session_state["dq_pvp_token"] = str(j.get("guest_token", ""))
                                st.session_state["dq_pvp_role"] = "guest"
                                st.session_state["dq_pvp_phase"] = "room"
                                st.rerun()
                            st.error(j.get("error", r.text or "加入失败"))
                        except Exception as e:
                            st.error(f"连接失败：{e}")
            with j2:
                if st.button("返回", key="dq_pvp_join_back"):
                    st.session_state["dq_pvp_phase"] = "menu"
                    st.rerun()
            return

        if phase_ui == "room" and rid:
            _frag = getattr(st, "fragment", None)
            if callable(_frag):

                @_frag(run_every=timedelta(seconds=5))
                def _pvp_room_poll_if_changed() -> None:
                    try:
                        rr = requests.get(_dq_pvp_url(f"/api/pvp/room/{rid}"), timeout=12)
                        room = (rr.json() or {}).get("room") if rr.ok else {}
                        sig = _pvp_room_signature(room)
                        sk = f"pvp_room_sig_{rid}"
                        prev = st.session_state.get(sk)
                        if sig and prev is not None and prev != sig:
                            st.session_state[sk] = sig
                            st.rerun()
                    except Exception:
                        pass

                _pvp_room_poll_if_changed()
            _pvp_render_room_phase_body(_dq_mod, state, rid, role, token, _leave)
            return

        st.warning("房间状态异常，请关闭后重试。")
        if st.button("关闭", key="dq_pvp_bad_close"):
            _leave()
            st.rerun()

    _pvp_inner()


def _dq_q1_act1_storage_key_suffix(state: Optional[Dict[str, Any]]) -> str:
    """与剧情视频 JS 共用：sessionStorage 键后缀（角色名脱敏）。"""
    nm = str((state or {}).get("name") or "").strip()
    t = re.sub(r"[^a-zA-Z0-9_-]+", "_", nm)[:96]
    return t or "hero"


def _dq_q1_act1_has_playable_story_video(state: Dict[str, Any], dq: Any) -> bool:
    """Q1 第一幕是否存在可播放的本地剧情视频（分集或单文件）。"""
    seq = _dq_q1_act1_split_video_paths(state, dq)
    if seq:
        return True
    stem = str(dq.dq_main_story_video_stem(state) or "").strip()
    if not stem:
        return False
    p = _dq_resolve_battle_video_path(stem)
    return bool(p and os.path.isfile(p))


def _dq_suppress_starter_bgm_for_q1_act1_intro(state: Dict[str, Any], dq: Any) -> bool:
    """新号/读档仍在 Q1 第一幕且视频未自然播完时，暂缓破晓村（普隆德拉）背景音乐。"""
    if dq is None:
        return False
    if str(state.get("phase", "overworld") or "") == "battle":
        return False
    if str(state.get("location", "starter") or "") != "starter":
        return False
    meta = (state or {}).get("meta") or {}
    if not isinstance(meta, dict):
        return False
    if meta.get("q1_act1_intro_video_completed"):
        return False
    ps = meta.get("pending_story")
    if not isinstance(ps, dict):
        return False
    if str(ps.get("sid", "") or "") != "q1_seal_whisper":
        return False
    if int(ps.get("step", 0) or 0) != 0:
        return False
    return _dq_q1_act1_has_playable_story_video(state, dq)


def _dq_pick_music_plan(state: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    根据当前 DQ 状态选择音乐：
    - 登录界面：Title 循环
    - 区域与战斗：按用户指定曲目切换
    """
    if not state:
        return {
            "mode": "single",
            "tracks": ["SoundTeMP - Title.mp3"],
            "loop": True,
        }

    phase = str(state.get("phase", "overworld"))
    location = str(state.get("location", "starter"))

    if phase == "battle":
        battle = state.get("battle") or {}
        enemy = battle.get("enemy") or {}
        mid = str(enemy.get("mid", "") or "")
        if mid.startswith("boss_"):
            return {
                "mode": "single",
                "tracks": ["SoundTeMP - Wind of Tragedy.mp3"],
                "loop": True,
            }
        return {
            "mode": "single",
            "tracks": ["SoundTeMP - Risk your life.mp3"],
            "loop": True,
        }

    if location == "infinite":
        return {
            "mode": "single",
            "tracks": ["SoundTeMP - Theme of Payon.mp3"],
            "loop": True,
        }

    # Q2 诅咒森林
    if location == "forest":
        return {
            "mode": "single",
            "tracks": ["SoundTeMP - Theme of Geffen.mp3"],
            "loop": True,
        }

    # Q3~Q5：此前未单独分支，与 starter 一样落到默认 Prontera，听起来与 Q1 相同
    if location == "mines":
        return {
            "mode": "single",
            "tracks": ["SoundTeMP - Theme of Morroc.mp3"],
            "loop": True,
        }
    if location == "coast":
        return {
            "mode": "playlist",
            "tracks": [
                "SoundTeMP - Streamside.mp3",
                "SoundTeMP - Theme of Alberta.mp3",
            ],
            "loop": True,
        }
    # Q5 王座地牢
    if location == "throne":
        return {
            "mode": "single",
            "tracks": ["SoundTeMP - Labyrinth.mp3"],
            "loop": True,
        }

    # Q1 破晓村及周边（starter）及未知区域
    return {
        "mode": "single",
        "tracks": ["SoundTeMP - Theme of Prontera.mp3"],
        "loop": True,
    }


def _dq_sync_session_settings_from_state(state: Dict[str, Any]) -> None:
    """从游戏状态恢复系统设置到会话（用于读档/新开局后）。"""
    meta = (state or {}).get("meta", {}) if isinstance(state, dict) else {}
    raw = meta.get("system_settings", {}) if isinstance(meta, dict) else {}
    battle_anim = bool(raw.get("battle_anim", True)) if isinstance(raw, dict) else True
    st.session_state["dq_settings_battle_anim"] = battle_anim


def _dq_sync_state_settings_from_session(state: Dict[str, Any]) -> None:
    """将当前会话系统设置回写到 dq_state，确保随存档持久化。"""
    if not isinstance(state, dict):
        return
    meta = state.get("meta", {})
    if not isinstance(meta, dict):
        meta = {}
    meta["system_settings"] = {"battle_anim": bool(st.session_state.get("dq_settings_battle_anim", True))}
    state["meta"] = meta


def _dq_render_music_player(state: Dict[str, Any] = None, dq: Any = None) -> None:
    """在页面注入单例音频播放器，跨 rerun 根据状态切歌。"""
    plan = _dq_pick_music_plan(state)
    track_rels = [f"/api/music/{quote(str(name or ''))}" for name in plan["tracks"]]
    track_abs = [_dq_music_track_url(name) for name in plan["tracks"]]
    _suppress = bool(state and _dq_suppress_starter_bgm_for_q1_act1_intro(state, dq))
    _ptag = _dq_q1_act1_storage_key_suffix(state) if state else "hero"
    payload = {
        "mode": plan["mode"],
        "tracks_rel": track_rels,
        "tracks_abs": track_abs,
        "loop": bool(plan.get("loop", True)),
        "suppress_intro_bgm": _suppress,
        "player_tag": _ptag,
    }
    payload_json = json.dumps(payload, ensure_ascii=False)
    components.html(
        f"""
<script>
(function() {{
  const cfg = {payload_json};
  const parentDoc = window.parent && window.parent.document ? window.parent.document : document;
  let audio = parentDoc.getElementById("dq-global-audio-player");
  if (!audio) {{
    audio = parentDoc.createElement("audio");
    audio.id = "dq-global-audio-player";
    audio.style.display = "none";
    parentDoc.body.appendChild(audio);
  }}

  const pt = String(cfg.player_tag || "hero");
  const sk = "dq_q1a1_vid_" + pt.replace(/[^a-zA-Z0-9_-]/g, "_");
  let introDone = false;
  try {{ introDone = sessionStorage.getItem(sk) === "1"; }} catch (e0) {{}}
  if (!cfg.suppress_intro_bgm) {{
    try {{ sessionStorage.removeItem(sk); }} catch (e1) {{}}
  }}
  const holdIntro = !!(cfg.suppress_intro_bgm && !introDone);
  const gateKey = JSON.stringify(cfg) + "|h=" + (holdIntro ? "1" : "0");

  const prevGate = audio.dataset.gateKey || "";
  if (prevGate === gateKey) {{
    if (!holdIntro && audio.paused && !audio.dataset.storyHold) {{
      audio.play().catch(() => {{}});
    }}
    return;
  }}
  audio.dataset.gateKey = gateKey;
  audio.dataset.cfg = JSON.stringify(cfg);
  if (holdIntro) {{
    try {{ audio.pause(); }} catch (e2) {{}}
    return;
  }}

  delete audio.dataset.storyHold;
  audio.dataset.idx = "0";
  audio.loop = (cfg.mode === "single") && !!cfg.loop;

  const playWithFallback = (cands, p=0) => {{
    if (!cands || p >= cands.length) return;
    audio.onerror = () => playWithFallback(cands, p + 1);
    audio.src = cands[p];
    audio.load();
    audio.play().catch(() => {{}});
  }};
  const applyTrack = (idx) => {{
    if (!cfg.tracks_rel || !cfg.tracks_rel.length) return;
    const i = ((idx % cfg.tracks_rel.length) + cfg.tracks_rel.length) % cfg.tracks_rel.length;
    audio.dataset.idx = String(i);
    const cands = [];
    if (cfg.tracks_rel[i]) cands.push(cfg.tracks_rel[i]);
    if (cfg.tracks_abs && cfg.tracks_abs[i] && cfg.tracks_abs[i] !== cfg.tracks_rel[i]) cands.push(cfg.tracks_abs[i]);
    playWithFallback(cands, 0);
  }};

  audio.onended = null;
  if (cfg.mode === "playlist") {{
    audio.loop = false;
    audio.onended = () => {{
      const cur = parseInt(audio.dataset.idx || "0", 10);
      applyTrack(cur + 1);
    }};
  }}
  applyTrack(0);
}})();
</script>
""",
        height=1,
        width=1,
        scrolling=False,
    )


def _dq_story_to_paragraphs(text: str, sentences_per_paragraph: int = 3) -> str:
    """将长段文本按句子自动切分为自然段，便于阅读。"""
    src = str(text or "").strip()
    if not src:
        return ""
    # 若原文已有空行分段，直接保留
    if "\n\n" in src:
        return src
    lines = [ln.strip() for ln in src.splitlines() if ln.strip()]
    joined = " ".join(lines)
    # 按中文/英文句末标点切句，避免整块显示
    parts = re.split(r'(?<=[。！？!?；;])\s*', joined)
    sentences = [p.strip() for p in parts if p.strip()]
    if not sentences:
        return joined
    paras: List[str] = []
    for i in range(0, len(sentences), max(1, int(sentences_per_paragraph))):
        paras.append("".join(sentences[i:i + sentences_per_paragraph]))
    return "\n\n".join(paras)


def _dq_overworld_zone_display_name(
    state: Dict[str, Any], zone_map: Dict[str, str], current: str, dq_mod: Any
) -> str:
    """冒险页「当前区域」展示：无限地牢译为中文并显示层数与本段风格地图名。"""
    if str(current) != "infinite":
        return str(zone_map.get(current, current))
    floor = max(1, int((state.get("dungeon") or {}).get("floor", 1) or 1))
    try:
        zid = dq_mod._infinite_zone_for_floor(floor)
        zc = dq_mod._zone_catalog()
        seg = str((zc.get(zid) or {}).get("name", zid))
    except Exception:
        seg = "未知"
    return f"无限地牢 · 第 {floor} 层（本段：{seg}）"


# 六维缩写悬停说明（与技能标签的 title 浮层类似；雷达图用 SVG 原生 title）
_DQ_ATTR_LABEL_TIPS: Dict[str, str] = {
    "str": "力量 STR：提升物理攻击力，并影响部分近战与物理类技能。",
    "int": "智力 INT：提升法术伤害、治疗量与魔力相关效果；并显著影响魔防面板。",
    "dex": "灵巧 DEX：影响命中率，并关联部分物理技巧与猎人系输出。",
    "agi": "敏捷 AGI：影响出手顺序；闪避率主要来源之一（约每点 +0.32%，刺客队友约 +0.6%），部分职业与普攻/技能挂钩。",
    "luk": "幸运 LUK：影响暴击率、闪避率（约每点 +0.05%）与部分随机收益。",
    "vit": "体质 VIT：影响生命上限与物理防御（物防）；并少量提升魔防。",
}


def _dq_hexagon_attrs_panel_html(
    c_attrs: Dict[str, Any],
    uid_safe: str,
    pending_pts: int = 0,
    eq_bonus: Optional[Dict[str, int]] = None,
    *,
    hex_parts: Optional[Dict[str, Any]] = None,
) -> str:
    """
    六维雷达：顶点自顶顺时针 STR → INT → DEX → AGI → LUK → VIT；
    若传入 hex_parts（dq_unit_hexagon_parts），展示值为 total（基础+装备+军械+天赋六维）；
    否则兼容旧口径：基础 + eq_bonus。
    悬停为玩法说明 + 分项分解。
    """
    keys = ("str", "int", "dex", "agi", "luk", "vit")
    labels = ("STR", "INT", "DEX", "AGI", "LUK", "VIT")
    cx, cy = 100.0, 100.0
    r_outer = 58.0
    r_lbl = 74.0
    uid = re.sub(r"[^a-zA-Z0-9_]", "_", str(uid_safe or "hex"))[:48]
    use_parts = isinstance(hex_parts, dict) and hex_parts.get("total")
    eb = eq_bonus or {}
    vals = []
    for k in keys:
        if use_parts:
            vals.append(max(0, int((hex_parts.get("total") or {}).get(k, 0) or 0)))
        else:
            base_v = max(0, int(c_attrs.get(k, 0) or 0))
            eq_v = max(0, int(eb.get(k, 0) or 0))
            vals.append(base_v + eq_v)
    vmax = float(max(max(vals), 1))

    def _ring_points(radius: float) -> str:
        return " ".join(
            f"{cx + radius * math.cos(math.radians(-90.0 + i * 60.0)):.2f},"
            f"{cy + radius * math.sin(math.radians(-90.0 + i * 60.0)):.2f}"
            for i in range(6)
        )

    grid_outer = _ring_points(r_outer)
    grid_mid = _ring_points(r_outer * 0.55)
    grid_in = _ring_points(r_outer * 0.28)
    lbl_xy: List[tuple] = []
    for i in range(6):
        ang = math.radians(-90.0 + i * 60.0)
        lbl_xy.append((cx + r_lbl * math.cos(ang), cy + r_lbl * math.sin(ang)))

    radar_pts: List[str] = []
    for i in range(6):
        ang = math.radians(-90.0 + i * 60.0)
        ri = r_outer * (vals[i] / vmax)
        radar_pts.append(f"{cx + ri * math.cos(ang):.2f},{cy + ri * math.sin(ang):.2f}")
    radar_poly = " ".join(radar_pts)

    parts: List[str] = [
        '<div class="dq-hex-attrs" style="text-align:center;margin:4px 0 14px 0;">',
        f'<svg viewBox="0 0 200 200" width="100%" style="max-width:260px;height:auto;display:block;margin:0 auto;" '
        f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="六维属性雷达">',
        "<defs>",
        f'<linearGradient id="dqhx_radar_{uid}" x1="0%" y1="0%" x2="0%" y2="100%">',
        '<stop offset="0%" stop-color="#93c5fd" stop-opacity="0.55"/>',
        '<stop offset="100%" stop-color="#3b82f6" stop-opacity="0.35"/>',
        "</linearGradient>",
        "</defs>",
        f'<polygon points="{grid_outer}" fill="none" stroke="#e2e8f0" stroke-width="1.2" stroke-linejoin="round"/>',
        f'<polygon points="{grid_mid}" fill="none" stroke="#f1f5f9" stroke-width="0.9" stroke-linejoin="round"/>',
        f'<polygon points="{grid_in}" fill="none" stroke="#f1f5f9" stroke-width="0.9" stroke-linejoin="round"/>',
    ]
    if sum(vals) > 0:
        parts.append(
            f'<polygon points="{radar_poly}" fill="url(#dqhx_radar_{uid})" stroke="#2563eb" '
            f'stroke-width="1.8" stroke-linejoin="round" opacity="0.92"/>'
        )
    else:
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="4" fill="#e2e8f0" stroke="#cbd5e1" stroke-width="1"/>'
        )
    if int(pending_pts or 0) > 0:
        parts.append(
            f'<text x="{cx}" y="{cy - 2}" text-anchor="middle" font-size="10" fill="#64748b" font-family="system-ui,sans-serif">待分配</text>'
        )
        parts.append(
            f'<text x="{cx}" y="{cy + 14}" text-anchor="middle" font-size="17" font-weight="700" fill="#c2410c" font-family="system-ui,sans-serif">{int(pending_pts)}</text>'
        )
    else:
        parts.append(
            f'<text x="{cx}" y="{cy + 4}" text-anchor="middle" font-size="11" fill="#94a3b8" font-family="system-ui,sans-serif">六维</text>'
        )
    for i, k in enumerate(keys):
        v = vals[i]
        if use_parts:
            base_v = max(0, int((hex_parts.get("base") or {}).get(k, 0) or 0))
            eq_v = max(0, int((hex_parts.get("equip") or {}).get(k, 0) or 0))
            arm_v = max(0, int((hex_parts.get("armory") or {}).get(k, 0) or 0))
            tal_v = max(0, int((hex_parts.get("talent") or {}).get(k, 0) or 0))
        else:
            base_v = max(0, int(c_attrs.get(k, 0) or 0))
            eq_v = max(0, int((eq_bonus or {}).get(k, 0) or 0))
            arm_v = 0
            tal_v = 0
        tx, ty = lbl_xy[i]
        tip_intro = _DQ_ATTR_LABEL_TIPS.get(k, f"{labels[i]}：六维属性。")
        if use_parts:
            tip_raw = f"{tip_intro}\n基础：{base_v}\n装备：+{eq_v}\n军械：+{arm_v}\n天赋：+{tal_v}\n合计：{v}"
        else:
            tip_raw = f"{tip_intro}\n基础：{base_v}\n装备：+{eq_v}\n合计：{v}"
        tip_xml = html_escape.escape(tip_raw, quote=True)
        parts.append('<g style="cursor:help;">')
        parts.append(f"<title>{tip_xml}</title>")
        parts.append(
            f'<text x="{tx:.1f}" y="{ty - 5:.1f}" text-anchor="middle" font-size="10" fill="#64748b" '
            f'font-family="system-ui,sans-serif">{labels[i]}</text>'
        )
        parts.append(
            f'<text x="{tx:.1f}" y="{ty + 9:.1f}" text-anchor="middle" font-size="13.5" font-weight="700" fill="#0f172a" '
            f'font-family="system-ui,sans-serif">{v}</text>'
        )
        parts.append("</g>")
    parts.append("</svg></div>")
    return "\n".join(parts)


def _dq_battle_log_rows_html(lines: List[str], max_lines: int = 220) -> str:
    """战斗日志正文（多行 div），与单机/PVP 共用：最新在上、回合分隔行样式、【】关键词着色。"""
    if not lines:
        return ""
    chunk = lines[-max_lines:]
    rev = list(reversed(chunk))
    blocks: List[str] = []
    _red_keys = ("蓄力", "咒术", "灼焰", "毒雾", "乱斩", "援护", "爆发", "回复术")
    _boss_name_markers = ("枯萎之王", "熔岩巨像", "潮汐女巫", "王座守卫")

    for raw in rev:
        s = str(raw)
        esc = html_escape.escape(s)
        _boss_skill_line = any(m in s for m in _boss_name_markers)
        if "════════" in s and "回合" in s:
            blocks.append(
                f'<div style="margin:12px 0 6px 0;padding:6px 10px;background:linear-gradient(90deg,#f1f5f9,#e2e8f0);'
                f'border-left:4px solid #334155;border-radius:4px;font-weight:700;color:#0f172a;'
                f'font-size:13px;letter-spacing:0.02em;">{esc}</div>'
            )
            continue

        def _sub_bracket(m: Any) -> str:
            inner = m.group(0)
            if _boss_skill_line:
                return f'<span style="color:#ea580c;font-weight:700;">{inner}</span>'
            if any(k in inner for k in _red_keys):
                return f'<span style="color:#dc2626;font-weight:700;">{inner}</span>'
            return inner

        colored = re.sub(r"【[^】]+】", _sub_bracket, esc)
        _act_head = s.strip().startswith("▶")
        _head_style = (
            "font-weight:700;color:#0f172a;margin-top:10px;padding-top:6px;border-top:1px dashed #e2e8f0;"
            if _act_head
            else ""
        )
        blocks.append(
            f'<div style="color:#1e293b;font-size:14px;line-height:1.55;margin:1px 0;padding:2px 0;{_head_style}">{colored}</div>'
        )
    return "".join(blocks)


def _dq_battle_log_html(lines: List[str], max_lines: int = 220, max_height: str = "320px") -> str:
    """战斗日志：最新在上；回合分隔行加粗；怪物技能名【…】中含蓄力/咒术等关键词时红色加亮。"""
    rows = _dq_battle_log_rows_html(lines, max_lines)
    if not rows:
        return (
            f"<div style=\"max-height:{max_height};overflow-y:auto;padding:10px;color:#64748b;"
            f'background:#fafafa;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:10px;">（暂无战斗记录）</div>'
        )
    return (
        f'<div style="max-height:{max_height};overflow-y:auto;padding:10px 12px;background:#fafafa;'
        f'border:1px solid #e2e8f0;border-radius:8px;margin-bottom:10px;">{rows}</div>'
    )


def _dq_pvp_battle_log_html(lines: List[str], max_lines: int = 220, max_height: str = "300px") -> str:
    """PVP 战报：与单机战斗日志同一套行样式，外框红边 +「战斗日志」标题。"""
    rows = _dq_battle_log_rows_html(lines, max_lines)
    if not rows:
        rows = '<div style="color:#64748b;padding:6px 4px;">（暂无战斗记录）</div>'
    return (
        f'<div style="border:2px solid #ef4444;border-radius:10px;padding:10px 12px 12px;'
        f"background:linear-gradient(165deg,#fff5f5 0%,#ffffff 55%);margin-bottom:12px;box-shadow:0 1px 2px rgba(239,68,68,0.12);\">"
        f'<div style="font-weight:800;color:#b91c1c;font-size:15px;margin:0 0 8px 0;letter-spacing:0.04em;">📜 战斗日志</div>'
        f'<div style="max-height:{max_height};overflow-y:auto;padding:10px 12px;background:#fafafa;'
        f'border:1px solid #fecaca;border-radius:8px;">{rows}</div></div>'
    )


def _dq_fresh_new_game_ops_hint(state: Dict[str, Any], initial_pending_pts: int = 5) -> bool:
    """新开局：Lv1、无经验、初始能力点尚未分配时，显示加点与存档引导。"""
    if int(state.get("level", 1) or 1) != 1:
        return False
    if int(state.get("exp", 0) or 0) != 0:
        return False
    if int(state.get("pending_stat_points", 0) or 0) != int(initial_pending_pts):
        return False
    return True


def _dq_stat_tutorial_enabled(state: Dict[str, Any], initial_pending_pts: int = 5) -> bool:
    """首次开局加点教学：仅在 Lv1 初始点未分配时启用。"""
    return _dq_fresh_new_game_ops_hint(state, initial_pending_pts)


def _dq_party_hp_or_mp_below_half(state: Dict[str, Any]) -> bool:
    """主角或任一存活队友的当前 HP 或 MP 占上限比例低于 50%。"""
    mhp = max(1, int(state.get("max_hp", 1) or 1))
    mmp = max(1, int(state.get("max_mp", 1) or 1))
    hp = int(state.get("hp", 0) or 0)
    mp = int(state.get("mp", 0) or 0)
    if hp / float(mhp) < 0.5 or mp / float(mmp) < 0.5:
        return True
    for m in state.get("party_members") or []:
        if not isinstance(m, dict):
            continue
        if int(m.get("hp", 0) or 0) <= 0:
            continue
        xh = max(1, int(m.get("max_hp", 1) or 1))
        xm = max(1, int(m.get("max_mp", 1) or 1))
        h = int(m.get("hp", 0) or 0)
        p = int(m.get("mp", 0) or 0)
        if h / float(xh) < 0.5 or p / float(xm) < 0.5:
            return True
    return False


DQ_STAT_KEYS = ("str", "int", "dex", "agi", "luk", "vit")


def dq_stat_widget_key(base_key: str, sk: str) -> str:
    return f"dq_card_{base_key}_{sk}"


def dq_stat_keep_key(base_key: str, sk: str) -> str:
    return f"dq_stat_keep_{base_key}_{sk}"


def dq_restore_stat_draft(session: MutableMapping[str, Any], base_key: str, sk: str) -> int:
    """widget key 被清掉时，从 keep key 恢复本次未确认分配。"""
    wk = dq_stat_widget_key(base_key, sk)
    kk = dq_stat_keep_key(base_key, sk)
    if wk not in session:
        session[wk] = int(session.get(kk, 0) or 0)
    return int(session.get(wk, 0) or 0)


def dq_persist_stat_draft(session: MutableMapping[str, Any], base_key: str, sk: str) -> None:
    wk = dq_stat_widget_key(base_key, sk)
    if wk not in session:
        return
    session[dq_stat_keep_key(base_key, sk)] = int(session.get(wk, 0) or 0)


def dq_clear_stat_draft(session: MutableMapping[str, Any], base_key: str) -> None:
    """仅清掉已确认角色的草稿，不影响其他人。"""
    for sk in DQ_STAT_KEYS:
        session.pop(dq_stat_widget_key(base_key, sk), None)
        session.pop(dq_stat_keep_key(base_key, sk), None)


def _dq_reset_stat_alloc_session_on_level_up(state: Dict[str, Any]) -> None:
    """主角或队友等级上升时，清空加点面板的 session 草稿，避免沿用上一轮未提交或已过期分配。"""
    hero_lv = int(state.get("level", 1) or 1)
    k_snap = "dq_alloc_snap_hero_lv"
    prev_h = st.session_state.get(k_snap)
    if prev_h is None:
        st.session_state[k_snap] = hero_lv
    elif hero_lv > int(prev_h):
        dq_clear_stat_draft(st.session_state, "hero")
        st.session_state[k_snap] = hero_lv
    else:
        st.session_state[k_snap] = hero_lv

    for mem in state.get("party_members") or []:
        mid = str(mem.get("mid") or "").strip()
        if not mid:
            continue
        mlv = int(mem.get("level", hero_lv) or hero_lv)
        mk = f"dq_alloc_snap_lv_{mid}"
        prev_m = st.session_state.get(mk)
        if prev_m is None:
            st.session_state[mk] = mlv
        elif mlv > int(prev_m):
            dq_clear_stat_draft(st.session_state, mid)
            st.session_state[mk] = mlv
        else:
            st.session_state[mk] = mlv

def show_dq_game_page():
    """仙境Hero：DQ 风格长篇文字 RPG"""
    import random
    import time
    import dq_rpg as dq

    if "dq_settings_battle_anim" not in st.session_state:
        if isinstance(st.session_state.get("dq_state"), dict):
            _dq_sync_session_settings_from_state(st.session_state.get("dq_state"))
        st.session_state.setdefault("dq_settings_battle_anim", True)

    st.title("🧙 仙境Hero")
    st.caption("欢迎来到仙境Hero；存档需设置校验密码；载入时若该姓名已设密码则需输入正确密码。")

    if "dq_state" not in st.session_state:
        _female_block_msg = st.session_state.pop("_dq_female_role_blocked_msg", None)
        if _female_block_msg:
            st.error(str(_female_block_msg))

        _del_fb = st.session_state.pop("dq_csv_del_feedback", None)
        if _del_fb == "ok":
            st.success("已从 CSV 删除该姓名的存档记录，已返回开始界面。")
        elif _del_fb == "err":
            _de = st.session_state.pop("dq_csv_del_err", "未知错误")
            st.error(f"删除失败：{_de}")
        _dq_render_music_player(None)

        if st.session_state.get("dq_home_pwd_prompt"):
            pending = str(st.session_state.get("dq_home_pwd_pending_name") or "").strip()
            st.info(f"载入「{pending}」需要输入该校验密码。")
            st.text_input("校验密码", type="password", key="dq_home_load_pwd")
            hp1, hp2 = st.columns(2)
            with hp1:
                if st.button("确认载入", type="primary", key="dq_home_load_pwd_ok"):
                    pwd_try = (st.session_state.get("dq_home_load_pwd") or "").strip()
                    if not pwd_try:
                        st.error("请输入校验密码。")
                    else:
                        try:
                            st.session_state.dq_state = dq.dq_load_state_from_csv(pending, pwd_try)
                            dq.dq_migrate_legacy_state(st.session_state.dq_state)
                            if str(st.session_state.dq_state.get("hero_gender") or "男").strip() == "女":
                                st.session_state.pop("dq_state", None)
                                st.session_state["_dq_female_role_blocked_msg"] = "女性角色剧情正在开发中，暂无法载入该存档。"
                                st.session_state.pop("dq_home_pwd_prompt", None)
                                st.session_state.pop("dq_home_pwd_pending_name", None)
                                st.rerun()
                            st.session_state["dq_settings_force_hydrate"] = True
                            st.session_state["dq_loaded_save_name"] = pending
                            meta = st.session_state.dq_state.get("meta", {})
                            meta.setdefault("log", [])
                            meta.setdefault("battle_log", [])
                            st.session_state.dq_state["meta"] = meta
                            st.session_state.pop("dq_home_pwd_prompt", None)
                            st.session_state.pop("dq_home_pwd_pending_name", None)
                            st.rerun()
                        except Exception as e:
                            st.error(f"载入失败：{e}")
            with hp2:
                if st.button("取消", key="dq_home_load_pwd_cancel"):
                    st.session_state.pop("dq_home_pwd_prompt", None)
                    st.session_state.pop("dq_home_pwd_pending_name", None)
                    st.rerun()
            return

        confirm_key = "dq_new_game_overwrite_confirm"
        if st.session_state.get(confirm_key):
            pending = str(st.session_state[confirm_key])
            st.warning(f"姓名「{pending}」在 CSV 中已有存档，开始新游戏将覆盖该条记录。")
            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("确认覆盖并开始新游戏", type="primary", key="dq_overwrite_yes"):
                    _ow_hg = str(st.session_state.get("dq_hero_gender_home", "男")).strip()
                    if _ow_hg != "男":
                        st.session_state["_dq_female_role_blocked_msg"] = "女性角色剧情正在开发中。"
                        st.rerun()
                    st.session_state.dq_state = dq.dq_new_game(pending, hero_gender=_ow_hg)
                    st.session_state["dq_settings_force_hydrate"] = True
                    del st.session_state[confirm_key]
                    st.rerun()
            with bc2:
                if st.button("取消", key="dq_overwrite_no"):
                    del st.session_state[confirm_key]
                    st.rerun()
            return

        save_entries = dq.dq_list_csv_save_entries()
        col_new, col_saved = st.columns(2, gap="large")
        with col_new:
            st.subheader("开始新冒险")
            if str(st.session_state.get("dq_hero_gender_home", "男")).strip() != "男":
                st.session_state["dq_hero_gender_home"] = "男"
            col_gender, col_form = st.columns([1, 2], gap="small")
            with col_gender:
                st.selectbox("性别", ["男"], key="dq_hero_gender_home")
                st.caption("女性角色剧情正在开发中。")
                _home_gender = str(st.session_state.get("dq_hero_gender_home", "男")).strip()
                _home_prev = _dq_avatar_url_for_battle(
                    "hero",
                    "warrior",
                    _home_gender if _home_gender in ("男", "女") else "男",
                )
                if _home_prev:
                    st.image(_home_prev, width="stretch")
            with col_form:
                name = st.text_input("冒险者姓名", value="", key="dq_name_input")
                if st.button("🌱 开始（创建新存档）", type="primary", key="dq_new_game_btn"):
                    nm = (name or "").strip()
                    _hg = str(st.session_state.get("dq_hero_gender_home", "男")).strip()
                    if _hg != "男":
                        st.error("女性角色剧情正在开发中。")
                        st.stop()
                    if not nm:
                        st.error("请先填写冒险者姓名。")
                    elif dq.dq_csv_has_save(nm):
                        st.session_state[confirm_key] = nm
                        st.rerun()
                    else:
                        st.session_state.dq_state = dq.dq_new_game(name, hero_gender=_hg)
                        st.session_state["dq_settings_force_hydrate"] = True
                        st.rerun()
            st.info("进入游戏后点「存档」并设置校验密码；下次用相同姓名载入时，若已设密码需输入正确密码。")
        with col_saved:
            st.subheader("已存档姓名")
            if save_entries:
                for i, ent in enumerate(save_entries):
                    nm = str(ent.get("name") or "").strip()
                    ts = (ent.get("updated_at") or "").strip() or "—"
                    if st.button(
                        f"📂 载入「{nm}」",
                        key=f"dq_load_saved_{i}_{nm}",
                        help=f"存档时间：{ts}",
                    ):
                        if dq.dq_csv_row_requires_password(nm):
                            st.session_state["dq_home_pwd_prompt"] = True
                            st.session_state["dq_home_pwd_pending_name"] = nm
                            st.rerun()
                        else:
                            try:
                                st.session_state.dq_state = dq.dq_load_state_from_csv(nm, None)
                                dq.dq_migrate_legacy_state(st.session_state.dq_state)
                                if str(st.session_state.dq_state.get("hero_gender") or "男").strip() == "女":
                                    st.session_state.pop("dq_state", None)
                                    st.session_state["_dq_female_role_blocked_msg"] = "女性角色剧情正在开发中，暂无法载入该存档。"
                                    st.rerun()
                                st.session_state["dq_settings_force_hydrate"] = True
                                st.session_state["dq_loaded_save_name"] = nm
                                meta = st.session_state.dq_state.get("meta", {})
                                meta.setdefault("log", [])
                                meta.setdefault("battle_log", [])
                                st.session_state.dq_state["meta"] = meta
                                st.rerun()
                            except Exception as e:
                                st.error(f"载入失败：{e}")
            else:
                st.caption("暂无已存档姓名。")

        return

    state = st.session_state.dq_state
    if not isinstance(state, dict) or "hp" not in state or "level" not in state:
        st.session_state.dq_state = dq.dq_new_game("勇者")
        st.session_state["dq_settings_force_hydrate"] = True
        st.rerun()

    # 旧存档：补齐六维属性并重算攻防
    if "attrs" not in st.session_state.dq_state:
        st.session_state.dq_state = dq.dq_migrate_state(st.session_state.dq_state)
        st.rerun()

    if st.session_state.pop("dq_settings_force_hydrate", False):
        # 仅在新游戏/首次进入时清除视频标记；读档时保留标记避免剧情视频重复播放
        _is_new_game = not st.session_state.get("dq_loaded_save_name")
        if _is_new_game:
            st.session_state.pop("dq_last_story_video_key", None)
        st.session_state.pop("dq_loaded_save_name", None)
        _dq_sync_session_settings_from_state(st.session_state.dq_state)
    _dq_sync_state_settings_from_session(st.session_state.dq_state)

    _dq_render_music_player(state, dq)

    dq.dq_migrate_legacy_state(st.session_state.dq_state)
    dq.dq_ensure_q1_opening_story(st.session_state.dq_state)

    # 被动恢复：每次页面渲染都结算一次（若不进入旅店）
    try:
        st.session_state.dq_state = dq.dq_time_regen(st.session_state.dq_state, int(time.time()))
    except Exception:
        # 不影响游戏主流程
        pass
    state = st.session_state.dq_state

    # 随机源改为后端 5 种子池混合，读档后会刷新池，避免战斗流程完全可预测
    def _rng_for(salt: str) -> random.Random:
        return dq.dq_make_rng(st.session_state.dq_state, salt)

    # 全局日志裁剪，避免越玩越卡（各动作后自动保留最近条数）
    def _trim_log():
        meta = st.session_state.dq_state.get("meta", {})
        meta["log"] = meta.get("log", [])[-220:]
        meta["battle_log"] = meta.get("battle_log", [])[-220:]
        st.session_state.dq_state["meta"] = meta

    def _dq_log_display_rev(lines: list, max_lines: int = 220) -> str:
        """界面展示：只取最近若干条，且最新一条在最上方。"""
        if not lines:
            return ""
        chunk = lines[-max_lines:]
        return "\n".join(reversed(chunk))

    _dq_skill_labels = {
        "lianzhan": "连斩",
        "heavy_strike": "援护",
        "whirlwind": "旋风斩",
        "deep_cut": "深割",
        "armor_break": "盾反",
        "blood_rage": "嗜血",
        "execution": "战吼",
        "holy_heal": "圣疗",
        "group_prayer": "群体祈祷",
        "judgement": "神圣惩戒",
        "divine_bless": "圣光赐福",
        "arcane_bolt": "奥术冲击",
        "fire_blast": "爆炎术",
        "chain_lightning": "连锁闪电",
        "meteor": "陨星术",
        "aim_shot": "瞄准射击",
        "pierce_arrow": "穿透箭",
        "volley": "连射",
        "eagle_eye": "鹰眼狙击",
        "quick_stab": "快速刺击",
        "shadow_step": "影袭",
        "venom_edge": "毒刃",
        "assassinate": "暗杀",
        "mob_goblin_fireball": "地精·火球术",
        "mob_sprite_lightning": "野灵·雷电术",
        "mob_miner_guard": "矿坑傀儡·守护姿态",
        "mob_sea_curse_heal": "海祸咒灵·治愈术",
        "mob_throne_brave": "王座卫兵·勇气斩",
    }

    _dq_potion_uses = getattr(
        dq,
        "BATTLE_POTION_USES",
        frozenset({"heal_potion", "mp_potion", "dual_potion", "full_heal_potion", "full_mp_potion", "golden_apple", "revive_potion"}),
    )
    # 主角战斗技能下拉顺序（与「连斩→援护→旋风斩」设计一致；勿再把援护插到首位）
    _dq_hero_battle_skill_order = (
        "lianzhan",
        "heavy_strike",
        "whirlwind",
        "deep_cut",
        "armor_break",
        "blood_rage",
        "execution",
    )

    def _dq_avatar_url(kind: str, key: str, *, hero_gender: Optional[str] = None) -> str:
        """从本地 img 文件夹按名称读取头像。"""
        return _dq_avatar_url_for_battle(kind, key, hero_gender=hero_gender)

    def _dq_potion_display(it):
        meta = it.get("meta") or {}
        u = meta.get("use")
        ph = int(meta.get("heal_pct", getattr(dq, "POTION_HP_PCT", 35)))
        pm = int(meta.get("mp_pct", getattr(dq, "POTION_MP_PCT", 30)))
        dh = int(meta.get("heal_pct", getattr(dq, "POTION_DUAL_HP_PCT", 25)))
        dm = int(meta.get("mp_pct", getattr(dq, "POTION_DUAL_MP_PCT", 20)))
        if u == "heal_potion":
            return f"{it.get('name', '?')}（最大HP×{ph}%）"
        if u == "mp_potion":
            return f"{it.get('name', '?')}（最大MP×{pm}%）"
        if u == "dual_potion":
            return f"{it.get('name', '?')}（最大HP×{dh}% + 最大MP×{dm}%）"
        if u == "full_heal_potion":
            fh = int(meta.get("heal_pct", 100))
            return f"{it.get('name', '?')}（最大HP×{fh}%）"
        if u == "full_mp_potion":
            fm = int(meta.get("mp_pct", 100))
            return f"{it.get('name', '?')}（最大MP×{fm}%）"
        if u == "golden_apple":
            gh = int(meta.get("heal_pct", 100))
            gm = int(meta.get("mp_pct", 100))
            return f"{it.get('name', '?')}（最大HP×{gh}% + 最大MP×{gm}%）"
        if u == "revive_potion":
            rh = int(meta.get("revive_hp_pct", 30))
            rm = int(meta.get("revive_mp_pct", 30))
            return f"{it.get('name', '?')}（复活倒地队友：HP×{rh}% + MP×{rm}%）"
        return str(it.get("name", "?"))

    # 顶部角色信息
    phase = state.get("phase", "overworld")
    st.markdown("---")

    # 快速操作：REF / 清空日志 / 读档 / 存档 CSV / 删除磁盘存档 / PVP（放到标题下方）
    colA, colB, colC, colD, colE, colF = st.columns([1, 1, 1, 1, 1, 1])
    with colA:
        if st.button("♻️ REF", key="dq_reset_btn"):
            st.session_state["dq_refresh_prompt"] = True
    with colB:
        if st.button("🧹 清空日志", key="dq_trim_log_btn", help="清空冒险日志与战斗日志（仅当前存档会话内）"):
            st.session_state["dq_trim_log_prompt"] = True
            st.rerun()
    with colC:
        if st.button("📂 读档", key="dq_load_csv_btn", help="从 games/dq_saves.csv 选择并读取存档"):
            st.session_state["dq_load_csv_prompt"] = True
            st.rerun()
    with colD:
        if st.button("💾 存档", key="dq_save_csv_btn", help="按当前角色名写入 games/dq_saves.csv，需设置校验密码"):
            st.session_state["dq_save_csv_prompt"] = True
            st.rerun()
    with colE:
        if st.button("🗑️ 删除存档", key="dq_delete_csv_btn", help="仅从 CSV 删除当前角色名的记录，不重置内存中的游戏"):
            st.session_state["dq_delete_csv_prompt"] = True
            st.rerun()
    with colF:
        if st.button(
            "⚔️ PVP",
            key="dq_pvp_open_btn",
            help="联机对战：需后端服务；创建/加入 4 位房间号",
        ):
            st.session_state["dq_pvp_dialog"] = True
            st.session_state["dq_pvp_phase"] = "menu"
            st.rerun()

    _dq_render_pvp_dialog(dq, state)

    # 升级经验条（当前 Lv -> 下一级）
    exp = int(state.get("exp", 0) or 0)
    exp_to_next = int(state.get("exp_to_next", 0) or 0)
    lv = int(state.get("level", 1) or 1)
    ex1, ex2, ex3 = st.columns([5, 1, 1])
    with ex1:
        if exp_to_next > 0:
            pct = max(0.0, min(1.0, exp / max(1, exp_to_next)))
            st.markdown(
                f"""
<div style="width:92%;">
  <div style="font-size:13px;margin-bottom:6px;">经验进度：{exp}/{exp_to_next}（升级）</div>
  <div style="height:32px;background:#e5e7eb;border-radius:999px;overflow:hidden;">
    <div style="height:100%;width:{pct*100:.1f}%;background:linear-gradient(90deg,#fdba74,#f97316,#c2410c);"></div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
        elif lv >= dq.MAX_PLAYER_LEVEL:
            st.success(
                f"已达等级上限 Lv{dq.MAX_PLAYER_LEVEL}（主角成长技能在 Lv1/6/12/18/24/30 解锁）"
            )
        else:
            st.info("经验进度暂不可用")
    with ex2:
        st.metric("体力", f"{int(state.get('stamina', 0))}/{int(state.get('max_stamina', 0))}")
    with ex3:
        st.metric("金币", f"{int(state.get('gold', 0))}")

    _dq_reset_stat_alloc_session_on_level_up(state)

    inn_cost = int(dq.dq_inn_cost(state)) if hasattr(dq, "dq_inn_cost") else 100
    _init_pts = int(getattr(dq, "INITIAL_ABILITY_POINTS", 5) or 5)
    if _dq_stat_tutorial_enabled(state, _init_pts):
        st.session_state["dq_stat_tutorial_active"] = True
        st.session_state.setdefault("dq_stat_tutorial_step", "str")
    elif int(state.get("pending_stat_points", 0) or 0) <= 0:
        st.session_state["dq_stat_tutorial_active"] = False
    tutorial_active_global = bool(st.session_state.get("dq_stat_tutorial_active", False))
    st.markdown("### 💡 操作建议")
    if _dq_fresh_new_game_ops_hint(state, _init_pts):
        st.info(
            f"初始 {_init_pts} 点加点很重要：STR 为力量，VIT 为体质（物防/生命），DEX 为命中，INT 影响魔防，建议按需分配。"
            "将鼠标悬停在属性名称上可查看详细介绍。切换到「冒险」标签后点击「探索」可进行冒险。"
            "存档时请自行设置校验密码，读档时需输入该密码验证，以确保存档私密。"
        )
    elif _dq_party_hp_or_mp_below_half(state):
        st.info(
            f"队伍有人 HP 或 MP 低于 50%：建议前往旅店休息恢复（消耗 {inn_cost} 金币，全员 HP/MP/体力回满并清除异常）。"
        )
    elif state.get("stamina", 0) < 5:
        st.info(
            f"你的体力不足：可以去旅店回满（消耗 {inn_cost} 金币），或等待被动恢复。"
        )
    else:
        st.info("探索会触发遭遇战；无限地牢则更适合长时间刷怪与成长。")

    # 角色卡片（主角 + 队友）：每行 3 张卡
    cs = dq.dq_combat_stat_summary(state)
    attrs = state.get("attrs") or {}
    pending = int(state.get("pending_stat_points", 0) or 0)
    eq_attr_bonus = dq.dq_equipment_attr_bonus(state)
    talent_labels = dq.dq_talent_choice_labels()
    skill_desc_map = dq.dq_skill_descriptions() if hasattr(dq, "dq_skill_descriptions") else {}
    role_desc = {
        "cleric": "牧师：优先治疗血量最低友方；若全员满血则释放攻击法术（INT 影响治疗/法术）。",
        "mage": "法师：自动释放法术攻击随机目标（INT 影响法术伤害）。",
        "hunter": "猎人：自动远程攻击随机目标（DEX 与攻击力挂钩）。",
        "rogue": "盗贼：自动突袭随机目标（AGI 与攻击力挂钩，暴击更高）。",
        "warrior": "战士：更偏近战与生存，通常担任前排（STR 影响攻击力）。",
    }

    def _dq_expander_panel_metric(label: str, value: str) -> None:
        """展开详情内战斗四维：一行 4 列；字号偏大、flex 纵向零间距。"""
        st.markdown(
            f'<div class="dq-expander-stat-metric" style="display:flex;flex-direction:column;'
            f'gap:0;line-height:1;margin:0;padding:0;align-items:flex-start;">'
            f'<span style="font-size:0.98rem;color:#6b7280;line-height:1;margin:0;padding:0;">{label}</span>'
            f'<span style="font-size:1.22rem;font-weight:600;line-height:1.02;margin:0;padding:0;">{value}</span>'
            f"</div>",
            unsafe_allow_html=True,
        )

    def _skill_tags_html(skill_ids: List[str]) -> str:
        tags: List[str] = []
        for sid in skill_ids:
            sid_s = str(sid)
            label = _dq_skill_labels.get(sid_s, sid_s)
            desc = str(skill_desc_map.get(sid_s, "暂无说明"))
            label_e = (
                label.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            desc_e = (
                desc.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )
            tags.append(
                f'<span title="{desc_e}" '
                'style="display:inline-block;padding:2px 8px;margin:2px;border:1px solid #d1d5db;'
                'border-radius:999px;font-size:12px;background:#f8fafc;">'
                f'{label_e}</span>'
            )
        return "".join(tags)

    def _stat_bar_html(cur: int, mx: int, color: str, label: str) -> str:
        cur_i = int(cur or 0)
        mx_i = max(1, int(mx or 1))
        pct = max(0.0, min(100.0, (cur_i / mx_i) * 100.0))
        return (
            f'<div style="margin:4px 0 8px 0;">'
            f'  <div style="font-size:12px;margin-bottom:4px;">{label} {cur_i}/{mx_i}</div>'
            f'  <div style="height:10px;background:#e5e7eb;border-radius:999px;overflow:hidden;">'
            f'    <div style="height:100%;width:{pct:.1f}%;background:{color};"></div>'
            f'  </div>'
            f'</div>'
        )

    st.markdown("### 👤 角色卡片")
    prev_lv_for_expand = st.session_state.get("dq_prev_level_for_expand")
    hero_auto_expand = bool(prev_lv_for_expand is not None and lv > int(prev_lv_for_expand))
    st.session_state["dq_prev_level_for_expand"] = int(lv)
    cards: List[Dict[str, Any]] = [
        {
            "kind": "hero",
            "name": state.get("name", "勇者"),
            "role": state.get("role", "warrior"),
            "level": int(state.get("level", 1) or 1),
            "data": state,
        }
    ]
    members = state.get("party_members", []) or []
    for mem in members:
        cards.append(
            {
                "kind": "ally",
                "mid": mem.get("mid"),
                "name": mem.get("name", "队友"),
                "role": str(mem.get("role", "")),
                "level": int(mem.get("level", state.get("level", 1)) or 1),
                "data": mem,
            }
        )
    if len(cards) == 1:
        st.info("暂无队友卡片（完成剧情后可招募队友）。")
    _dq_stat_commit_pending_rerun = False
    for card in cards:
        persist_key = "hero" if card["kind"] == "hero" else str(card.get("mid", "ally"))
        for sk in DQ_STAT_KEYS:
            dq_persist_stat_draft(st.session_state, persist_key, sk)
    for i in range(0, len(cards), 3):
        row = cards[i:i + 3]
        cols = st.columns(3)
        for idx, card in enumerate(row):
            with cols[idx]:
                with st.container(border=True):
                    cdata = card["data"]
                    if card["kind"] == "hero":
                        title_text = f"主角｜{card['name']}（{card['role']}） Lv{card['level']}"
                    else:
                        title_text = f"队友｜{card['name']}（{card['role']}） Lv{card['level']}"
                    hp_now = int(cdata.get("hp", 0) or 0)
                    hp_max = int(cdata.get("max_hp", 1) or 1)
                    mp_now = int(cdata.get("mp", 0) or 0)
                    mp_max = int(cdata.get("max_mp", 1) or 1)
                    st.markdown(f"**{title_text}**")
                    st.markdown(_stat_bar_html(hp_now, hp_max, "#ef4444", "HP"), unsafe_allow_html=True)
                    st.markdown(_stat_bar_html(mp_now, mp_max, "#3b82f6", "MP"), unsafe_allow_html=True)

                    # 升级当次强制展开；有待分配点数时每轮 rerun 仍 expanded=True，否则点 +/- 加点会收起面板
                    c_pending_expand = int(cdata.get("pending_stat_points", 0) or 0)
                    expand_details = (card["kind"] == "hero" and hero_auto_expand) or c_pending_expand > 0
                    if expand_details:
                        expander_ctx = st.expander("展开详情", expanded=True)
                    else:
                        expander_ctx = st.expander("展开详情")

                    with expander_ctx:
                        panel_stats = dq.dq_unit_panel_summary(
                            cdata,
                            ref_enemy_atk=int(cs.get("ref_atk", 18) or 18),
                            is_player=bool(card["kind"] == "hero"),
                            party_armory=state.get("party_armory"),
                            map_resources=state.get("resources"),
                        ) if hasattr(dq, "dq_unit_panel_summary") else {
                            "hit_pct": 0.0,
                            "crit_pct": 0.0,
                            "eva_pct": 0.0,
                            "def_mit_pct": 0.0,
                            "mdef_mit_pct": 0.0,
                        }
                        st.markdown(
                            """
<style>
div[data-testid="stMarkdownContainer"] p:has(.dq-expander-stat-metric) {
  margin: 0 !important;
  padding: 0 !important;
  line-height: 1.05 !important;
}
</style>
""",
                            unsafe_allow_html=True,
                        )
                        ab1, ab2, ab3, ab4, ab5 = st.columns(5)
                        with ab1:
                            _dq_expander_panel_metric("命中率", f"{panel_stats.get('hit_pct', 0.0)}%")
                        with ab2:
                            _dq_expander_panel_metric("暴击率", f"{panel_stats.get('crit_pct', 0.0)}%")
                        with ab3:
                            _dq_expander_panel_metric("闪避率", f"{panel_stats.get('eva_pct', 0.0)}%")
                        with ab4:
                            _dq_expander_panel_metric("物免", f"{panel_stats.get('def_mit_pct', 0.0)}%")
                        with ab5:
                            _dq_expander_panel_metric("魔免", f"{panel_stats.get('mdef_mit_pct', 0.0)}%")
                        st.markdown(
                            '<div style="height:10px" aria-hidden="true"></div>',
                            unsafe_allow_html=True,
                        )
                        st.caption(role_desc.get(str(card["role"]), "队友：自动参与战斗。"))
                        st.caption(
                            f"面板：物防 {int(cdata.get('def', 0) or 0)}　魔防 {int(cdata.get('mdef', 0) or 0)}"
                        )
                        c_attrs = cdata.get("attrs") or {}
                        c_pending = int(cdata.get("pending_stat_points", 0) or 0)
                        base_key = "hero" if card["kind"] == "hero" else str(card.get("mid", "ally"))
                        _stat_keys_order = ("str", "int", "dex", "agi", "luk", "vit")
                        _stat_pairs = [
                            ("str", "STR"),
                            ("int", "INT"),
                            ("dex", "DEX"),
                            ("agi", "AGI"),
                            ("luk", "LUK"),
                            ("vit", "VIT"),
                        ]
                        hex_parts = None
                        if hasattr(dq, "dq_unit_hexagon_parts"):
                            try:
                                hex_parts = dq.dq_unit_hexagon_parts(
                                    cdata,
                                    is_player=bool(card["kind"] == "hero"),
                                    party_armory=state.get("party_armory"),
                                )
                            except Exception:
                                hex_parts = None
                        if hex_parts is None:
                            if card["kind"] == "hero":
                                arm_h = (
                                    (state.get("party_armory") or {}).get(str(state.get("role", "warrior")), {})
                                    if isinstance(state.get("party_armory"), dict)
                                    else {}
                                )
                                eq_card = {
                                    "str": int(eq_attr_bonus.get("str", 0) or 0) + int(arm_h.get("str_bonus", 0) or 0),
                                    "int": int(eq_attr_bonus.get("int", 0) or 0) + int(arm_h.get("int_bonus", 0) or 0),
                                    "dex": int(eq_attr_bonus.get("dex", 0) or 0) + int(arm_h.get("dex_bonus", 0) or 0),
                                    "agi": int(eq_attr_bonus.get("agi", 0) or 0) + int(arm_h.get("agi_bonus", 0) or 0),
                                    "luk": int(eq_attr_bonus.get("luk", 0) or 0),
                                    "vit": int(eq_attr_bonus.get("vit", 0) or 0),
                                }
                            else:
                                mem_eq_bonus = dq._compute_equip_attr_bonus(cdata.get("equipped") or {}) if hasattr(dq, "_compute_equip_attr_bonus") else {}
                                arm = (state.get("party_armory") or {}).get(str(card["role"]), {}) if isinstance(state.get("party_armory"), dict) else {}
                                eq_card = {
                                    "str": int(mem_eq_bonus.get("str", 0) or 0),
                                    "int": int(mem_eq_bonus.get("int", 0) or 0) + int(arm.get("int_bonus", 0) or 0),
                                    "dex": int(mem_eq_bonus.get("dex", 0) or 0) + int(arm.get("dex_bonus", 0) or 0),
                                    "agi": int(mem_eq_bonus.get("agi", 0) or 0) + int(arm.get("agi_bonus", 0) or 0),
                                    "luk": int(mem_eq_bonus.get("luk", 0) or 0),
                                    "vit": int(mem_eq_bonus.get("vit", 0) or 0),
                                }
                            hex_html = _dq_hexagon_attrs_panel_html(
                                c_attrs, f"{base_key}_{i}_{idx}", c_pending, eq_bonus=eq_card
                            )
                        else:
                            hex_html = _dq_hexagon_attrs_panel_html(
                                c_attrs, f"{base_key}_{i}_{idx}", c_pending, hex_parts=hex_parts
                            )
                        st.markdown(hex_html, unsafe_allow_html=True)
                        # 有待分配点数时：按「一行2个属性」展示（共3行）
                        if c_pending > 0:
                            tutorial_active = bool(
                                tutorial_active_global and card["kind"] == "hero" and base_key == "hero"
                            )
                            tutorial_step = str(st.session_state.get("dq_stat_tutorial_step", "str"))
                            target_attr = ""
                            if tutorial_active:
                                if tutorial_step not in ("str", "vit", "commit"):
                                    tutorial_step = "str"
                                    st.session_state["dq_stat_tutorial_step"] = "str"
                                target_attr = "str" if tutorial_step == "str" else ("vit" if tutorial_step == "vit" else "")
                                if tutorial_step == "str":
                                    st.markdown(
                                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin:6px 0 8px 0;">'
                                        "👉 第 1 步：请点 STR 的「＋」3 次。其余位置暂不可操作。</div>",
                                        unsafe_allow_html=True,
                                    )
                                elif tutorial_step == "vit":
                                    st.markdown(
                                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin:6px 0 8px 0;">'
                                        "👉 第 2 步：请点 VIT 的「＋」2 次。其余位置暂不可操作。</div>",
                                        unsafe_allow_html=True,
                                    )
                                else:
                                    st.markdown(
                                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin:6px 0 8px 0;">'
                                        "👉 第 3 步：请点击下方「✅ 主角加点」完成本次引导。</div>",
                                        unsafe_allow_html=True,
                                    )
                                st.markdown('<div id="dq-stat-guide-anchor"></div>', unsafe_allow_html=True)
                                last_step = str(st.session_state.get("dq_stat_tutorial_last_scroll_step", ""))
                                if last_step != tutorial_step:
                                    st.session_state["dq_stat_tutorial_last_scroll_step"] = tutorial_step
                                    components.html(
                                        """
<script>
setTimeout(() => {
  const el = window.parent.document.querySelector('#dq-stat-guide-anchor');
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
}, 120);
</script>
""",
                                        height=1,
                                        width=1,
                                        scrolling=False,
                                    )

                            def _render_alloc_cell(sk: str, slab: str) -> None:
                                alloc_key = f"dq_card_{base_key}_{sk}"
                                cur = dq_restore_stat_draft(st.session_state, base_key, sk)
                                total_c = sum(
                                    int(st.session_state.get(f"dq_card_{base_key}_{k}", 0) or 0)
                                    for k in _stat_keys_order
                                )
                                max_for_sk = max(0, c_pending - (total_c - cur))
                                cur_clamped = max(0, min(cur, max_for_sk))
                                if cur_clamped != cur:
                                    st.session_state[alloc_key] = cur_clamped
                                st.caption(f"{slab} · 本次分配")

                                def _alloc_dec_click() -> None:
                                    st.session_state[alloc_key] = max(
                                        0, int(st.session_state.get(alloc_key, 0) or 0) - 1
                                    )

                                def _alloc_inc_click() -> None:
                                    cu = int(st.session_state.get(alloc_key, 0) or 0)
                                    new_v = min(int(max_for_sk), cu + 1)
                                    st.session_state[alloc_key] = new_v
                                    if tutorial_active:
                                        if tutorial_step == "str" and sk == "str" and new_v >= 3:
                                            st.session_state["dq_stat_tutorial_step"] = "vit"
                                        elif tutorial_step == "vit" and sk == "vit" and new_v >= 2:
                                            st.session_state["dq_stat_tutorial_step"] = "commit"

                                b_left, b_mid, b_right = st.columns([1, 1.2, 1], gap="small")
                                lock_other = bool(tutorial_active and tutorial_step in ("str", "vit"))
                                disable_for_this_attr = bool(lock_other and sk != target_attr)
                                with b_left:
                                    st.button(
                                        "−",
                                        key=f"dq_stat_dec_{base_key}_{sk}",
                                        width="stretch",
                                        type="secondary",
                                        help="减 1 点",
                                        on_click=_alloc_dec_click,
                                        disabled=bool(tutorial_active),
                                    )
                                with b_mid:
                                    st.number_input(
                                        f"{slab} 点数",
                                        min_value=0,
                                        max_value=max(0, int(max_for_sk)),
                                        step=1,
                                        key=alloc_key,
                                        label_visibility="collapsed",
                                        help=f"可直接输入 0～{max_for_sk}，或用两侧按钮",
                                        disabled=bool(tutorial_active),
                                    )
                                with b_right:
                                    st.button(
                                        "＋",
                                        key=f"dq_stat_inc_{base_key}_{sk}",
                                        width="stretch",
                                        type=(
                                            "primary"
                                            if bool(
                                                tutorial_active
                                                and sk == target_attr
                                                and tutorial_step in ("str", "vit")
                                            )
                                            else "secondary"
                                        ),
                                        help="加 1 点（仍受待分配总数限制）",
                                        on_click=_alloc_inc_click,
                                        disabled=bool(
                                            disable_for_this_attr or (tutorial_active and tutorial_step == "commit")
                                        ),
                                    )
                                dq_persist_stat_draft(st.session_state, base_key, sk)

                            for r in range(0, len(_stat_pairs), 2):
                                row_pairs = _stat_pairs[r : r + 2]
                                c_left, c_right = st.columns(2, gap="small")
                                with c_left:
                                    _render_alloc_cell(*row_pairs[0])
                                if len(row_pairs) > 1:
                                    with c_right:
                                        _render_alloc_cell(*row_pairs[1])
                        c_skills = cdata.get("skills") or []
                        if c_skills:
                            st.markdown(
                                f"<div>技能：{_skill_tags_html([str(s) for s in c_skills])}</div>",
                                unsafe_allow_html=True,
                            )
                        c_talent = cdata.get("talent_picked") or {}
                        if isinstance(c_talent, dict) and c_talent:
                            t_items = [f"{lv0}级:{talent_labels.get(str(cid), str(cid))}" for lv0, cid in sorted(c_talent.items(), key=lambda x: int(x[0]) if str(x[0]).isdigit() else 999)]
                            st.caption("天赋：" + "、".join(t_items))

                        if c_pending > 0:
                            st.caption(f"待分配：{c_pending} 点")
                            v_str = int(st.session_state.get(f"dq_card_{base_key}_str", 0) or 0)
                            v_int = int(st.session_state.get(f"dq_card_{base_key}_int", 0) or 0)
                            v_dex = int(st.session_state.get(f"dq_card_{base_key}_dex", 0) or 0)
                            v_agi = int(st.session_state.get(f"dq_card_{base_key}_agi", 0) or 0)
                            v_luk = int(st.session_state.get(f"dq_card_{base_key}_luk", 0) or 0)
                            v_vit = int(st.session_state.get(f"dq_card_{base_key}_vit", 0) or 0)
                            total_c = v_str + v_int + v_dex + v_agi + v_luk + v_vit
                            st.caption(f"合计：{total_c}/{c_pending}")
                            if card["kind"] == "hero":
                                commit_locked = bool(tutorial_active and tutorial_step != "commit")
                                if st.button(
                                    "✅ 主角加点",
                                    type="primary",
                                    key=f"dq_card_commit_{base_key}",
                                    disabled=commit_locked,
                                ):
                                    if total_c != c_pending:
                                        st.error(f"六项之和必须等于 {c_pending}")
                                    else:
                                        try:
                                            alloc = {"str": v_str, "int": v_int, "dex": v_dex, "agi": v_agi, "luk": v_luk, "vit": v_vit}
                                            st.session_state.dq_state = dq.dq_allocate_stats(st.session_state.dq_state, alloc)
                                            for other in cards:
                                                other_key = "hero" if other["kind"] == "hero" else str(other.get("mid", "ally"))
                                                if other_key == base_key:
                                                    continue
                                                for sk in DQ_STAT_KEYS:
                                                    dq_persist_stat_draft(st.session_state, other_key, sk)
                                            dq_clear_stat_draft(st.session_state, base_key)
                                            if tutorial_active:
                                                st.session_state["dq_stat_tutorial_active"] = False
                                                st.session_state["dq_stat_tutorial_step"] = "done"
                                                st.session_state["dq_stat_tutorial_jump_adventure"] = True
                                            _trim_log()
                                            _dq_stat_commit_pending_rerun = True
                                        except Exception as e:
                                            st.error(str(e))
                            else:
                                if st.button("✅ 队友加点", type="primary", key=f"dq_card_commit_{base_key}"):
                                    try:
                                        v_map = {"str": v_str, "int": v_int, "dex": v_dex, "agi": v_agi, "luk": v_luk, "vit": v_vit}
                                        st.session_state.dq_state = dq.dq_allocate_party_member_stats(st.session_state.dq_state, card.get("mid"), v_map)
                                        for other in cards:
                                            other_key = "hero" if other["kind"] == "hero" else str(other.get("mid", "ally"))
                                            if other_key == base_key:
                                                continue
                                            for sk in DQ_STAT_KEYS:
                                                dq_persist_stat_draft(st.session_state, other_key, sk)
                                        dq_clear_stat_draft(st.session_state, base_key)
                                        _trim_log()
                                        _dq_stat_commit_pending_rerun = True
                                    except Exception as e:
                                        st.error(str(e))

    if _dq_stat_commit_pending_rerun:
        st.rerun()

    # 已按要求移除技能图鉴模块

    dlg = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
    meta_cur = state.get("meta") or {}
    pending_clue_fb = meta_cur.get("pending_clue_quiz_feedback")
    pending_notice_q = meta_cur.get("pending_unlock_notice_queue") or []
    pending_talent = meta_cur.get("pending_talent")
    pending_rep = meta_cur.get("pending_skill_replace")
    if dlg and isinstance(pending_clue_fb, dict):
        _fb_level = str(pending_clue_fb.get("level", "mid"))
        _fb_text = str(pending_clue_fb.get("text", "") or "")
        _fb_score = int(pending_clue_fb.get("score", 0) or 0)

        @dlg("📣 关键线索反馈")
        def _dq_clue_feedback_dialog():
            st.markdown(f"**{pending_clue_fb.get('title', '领悟反馈')}**")
            if _fb_level == "good":
                st.success(_fb_text or "你做出了一个优秀选择。")
            elif _fb_level == "bad":
                st.error(_fb_text or "这次选择带来了不利结果。")
            else:
                st.info(_fb_text or "这次选择结果中性。")
            st.caption(f"本次领悟得分：{_fb_score} 分")
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 1, 1])
            with c2:
                if st.button("确认", type="primary", key="dq_clue_feedback_ack"):
                    st.session_state.dq_state = dq.dq_ack_clue_quiz_feedback(st.session_state.dq_state)
                    _trim_log()
                    st.rerun()

        _dq_clue_feedback_dialog()
    elif dlg and isinstance(pending_notice_q, list) and pending_notice_q:
        notice = pending_notice_q[0] if isinstance(pending_notice_q[0], dict) else {}

        @dlg("✨ 成长提示", dismissible=False)
        def _dq_unlock_notice_dialog():
            st.markdown(f"**{notice.get('title', '成长提示')}**")
            for ln in (notice.get("lines") or []):
                st.markdown(f"- {ln}")
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 1, 1])
            with c2:
                if st.button("确认", type="primary", key="dq_unlock_notice_ack"):
                    st.session_state.dq_state = dq.dq_ack_unlock_notice(st.session_state.dq_state)
                    _qt_after_ack = (
                        (st.session_state.dq_state.get("meta") or {}).get("q1_post_act1_tutorial") or {}
                    )
                    if isinstance(_qt_after_ack, dict) and bool(_qt_after_ack.get("active")):
                        if str(_qt_after_ack.get("focus", "")) == "backpack_tab":
                            # 稀有掉落弹窗全部确认后，教程切到背包页继续装备教学
                            st.session_state["dq_force_tab_idx_once"] = 5
                    st.rerun()

        _dq_unlock_notice_dialog()
    elif dlg and isinstance(pending_talent, dict):
        choices = pending_talent.get("choices") or {}
        t_opts = [k for k in choices.keys()]

        @dlg("🌟 选择天赋")
        def _dq_talent_dialog():
            st.markdown(f"**{pending_talent.get('title', '天赋选择')}**")
            if not t_opts:
                st.error("当前没有可选天赋。")
                return
            pick = st.radio(
                "请选择一个天赋",
                t_opts,
                format_func=lambda x: str(choices.get(x, x)),
                key=f"dq_talent_dialog_pick_{pending_talent.get('level', 0)}_{pending_talent.get('role', '')}",
            )
            st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
            c1, c2, c3 = st.columns([1, 1, 1])
            with c2:
                if st.button("确认", type="primary", key="dq_talent_dialog_confirm"):
                    st.session_state.dq_state = dq.dq_resolve_talent_choice(st.session_state.dq_state, pick)
                    _trim_log()
                    st.rerun()

        _dq_talent_dialog()
    elif dlg and isinstance(pending_rep, dict):
        rep_target = pending_rep.get("target") or {"type": "player"}
        rep_new_sid = str(pending_rep.get("new", ""))
        rep_new_name = str(pending_rep.get("name", "新技能"))
        rep_target_type = str(rep_target.get("type", "player"))
        if rep_target_type != "player":
            st.session_state.dq_state = dq.dq_skip_skill_replace(st.session_state.dq_state)
            st.rerun()
        rep_target_name = "主角" if rep_target_type == "player" else str(rep_target.get("name", "队友"))
        rep_cur_skills = []
        if rep_target_type == "player":
            rep_cur_skills = [s for s in (state.get("skills") or []) if s]
        else:
            rep_mid = str(rep_target.get("mid", ""))
            mem = next((m for m in (state.get("party_members") or []) if str(m.get("mid", "")) == rep_mid), None)
            rep_cur_skills = [s for s in ((mem or {}).get("skills") or []) if s]
        rep_opts = [s for s in rep_cur_skills if s != rep_new_sid]

        @dlg("📖 技能替换")
        def _dq_skill_replace_dialog():
            st.warning(f"{rep_target_name} 可习得「{rep_new_name}」，但技能栏已满（最多 4 个）。")
            if rep_new_sid == "lianzhan":
                st.caption("连斩：连续挥砍 2 次，每段按 1.5 倍普通攻击结算伤害；每段独立 20% 概率未命中。")
            if not rep_opts:
                st.error("当前无可替换技能。")
                if st.button("放弃该新技能", key="dq_pending_skill_skip_fallback"):
                    st.session_state.dq_state = dq.dq_skip_skill_replace(st.session_state.dq_state)
                    st.rerun()
                return
            pick = st.selectbox(
                "要替换掉的技能",
                rep_opts,
                format_func=lambda x: _dq_skill_labels.get(str(x), str(x)),
                key=f"dq_pending_skill_remove_{rep_target_type}_{rep_target_name}",
            )
            c1, c2, c3 = st.columns([1, 1, 1])
            with c1:
                if st.button("放弃该新技能", key="dq_pending_skill_skip"):
                    st.session_state.dq_state = dq.dq_skip_skill_replace(st.session_state.dq_state)
                    st.rerun()
            with c3:
                if st.button("确认", type="primary", key="dq_pending_skill_confirm"):
                    try:
                        st.session_state.dq_state = dq.dq_resolve_skill_replace(st.session_state.dq_state, str(pick))
                        _trim_log()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        _dq_skill_replace_dialog()

    if st.session_state.get("dq_save_csv_prompt"):
        if dlg:
            @dlg("💾 存档")
            def _dq_save_csv_dialog():
                st.markdown(
                    """
<div style="padding:10px 12px;border:1px solid #86efac;border-radius:10px;background:#f0fdf4;">
  <div style="font-weight:700;color:#14532d;margin-bottom:4px;">确认将当前进度写入 CSV 存档</div>
  <div style="color:#166534;font-size:13px;">请设置校验密码；下次用该姓名载入时需输入此密码。</div>
</div>
""",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                st.text_input("校验密码", type="password", key="dq_save_csv_p1")
                st.text_input("再次输入确认", type="password", key="dq_save_csv_p2")
                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
                sp1, sp2, sp3, sp4, sp5 = st.columns([1, 1, 0.5, 1, 1])
                with sp2:
                    if st.button("确认", type="primary", key="dq_save_csv_do"):
                        p1 = (st.session_state.get("dq_save_csv_p1") or "").strip()
                        p2 = (st.session_state.get("dq_save_csv_p2") or "").strip()
                        if not p1:
                            st.error("校验密码不能为空。")
                        elif p1 != p2:
                            st.error("两次输入的密码不一致。")
                        else:
                            try:
                                _dq_sync_state_settings_from_session(st.session_state.dq_state)
                                dq.dq_save_state_to_csv(st.session_state.dq_state, p1)
                                st.session_state["dq_save_csv_prompt"] = False
                                st.session_state["dq_csv_save_feedback"] = "ok"
                            except Exception as e:
                                st.session_state["dq_csv_save_feedback"] = "err"
                                st.session_state["dq_csv_save_err"] = str(e)
                            st.rerun()
                with sp4:
                    if st.button("取消", key="dq_save_csv_cancel"):
                        st.session_state["dq_save_csv_prompt"] = False
                        st.rerun()
            _dq_save_csv_dialog()
        else:
            st.markdown("##### 保存到 CSV")
            st.caption("请设置校验密码；下次用该姓名载入时需输入此密码。")
            st.text_input("校验密码", type="password", key="dq_save_csv_p1")
            st.text_input("再次输入确认", type="password", key="dq_save_csv_p2")
            sp1, sp2 = st.columns(2)
            with sp1:
                if st.button("确认保存", type="primary", key="dq_save_csv_do"):
                    p1 = (st.session_state.get("dq_save_csv_p1") or "").strip()
                    p2 = (st.session_state.get("dq_save_csv_p2") or "").strip()
                    if not p1:
                        st.error("校验密码不能为空。")
                    elif p1 != p2:
                        st.error("两次输入的密码不一致。")
                    else:
                        try:
                            _dq_sync_state_settings_from_session(st.session_state.dq_state)
                            dq.dq_save_state_to_csv(st.session_state.dq_state, p1)
                            st.session_state["dq_save_csv_prompt"] = False
                            st.session_state["dq_csv_save_feedback"] = "ok"
                        except Exception as e:
                            st.session_state["dq_csv_save_feedback"] = "err"
                            st.session_state["dq_csv_save_err"] = str(e)
                        st.rerun()
            with sp2:
                if st.button("取消", key="dq_save_csv_cancel"):
                    st.session_state["dq_save_csv_prompt"] = False
                    st.rerun()

    if st.session_state.get("dq_load_csv_prompt"):
        saved_names = dq.dq_list_csv_save_names()
        if dlg:
            @dlg("📂 读取存档")
            def _dq_load_csv_dialog():
                if not saved_names:
                    st.info("当前没有可读取的存档。")
                    if st.button("关闭", key="dq_load_csv_close_empty"):
                        st.session_state["dq_load_csv_prompt"] = False
                        st.rerun()
                    return
                st.caption("请选择要读取的存档。若该存档设置了校验密码，下一步会要求输入密码。")
                picked = st.selectbox("存档名", saved_names, key="dq_load_csv_name_pick")
                c1, c2, c3 = st.columns([1, 1, 1])
                with c1:
                    if st.button("读取", type="primary", key="dq_load_csv_do"):
                        nm = str(picked or "").strip()
                        if not nm:
                            st.error("请选择存档名。")
                            return
                        st.session_state["dq_load_csv_prompt"] = False
                        if dq.dq_csv_row_requires_password(nm):
                            st.session_state["dq_load_csv_pwd_prompt"] = True
                            st.session_state["dq_load_csv_pending_name"] = nm
                        else:
                            try:
                                st.session_state.dq_state = dq.dq_load_state_from_csv(nm, None)
                                st.session_state["dq_settings_force_hydrate"] = True
                                dq.dq_migrate_legacy_state(st.session_state.dq_state)
                                meta = st.session_state.dq_state.get("meta", {})
                                meta.setdefault("log", [])
                                meta.setdefault("battle_log", [])
                                st.session_state.dq_state["meta"] = meta
                            except Exception as e:
                                st.error(f"读档失败：{e}")
                                return
                        st.rerun()
                with c3:
                    if st.button("取消", key="dq_load_csv_cancel"):
                        st.session_state["dq_load_csv_prompt"] = False
                        st.rerun()
            _dq_load_csv_dialog()
        else:
            if not saved_names:
                st.info("当前没有可读取的存档。")
                st.session_state["dq_load_csv_prompt"] = False
            else:
                st.markdown("##### 读取存档")
                picked = st.selectbox("存档名", saved_names, key="dq_load_csv_name_pick_inline")
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("读取", type="primary", key="dq_load_csv_do_inline"):
                        nm = str(picked or "").strip()
                        st.session_state["dq_load_csv_prompt"] = False
                        if dq.dq_csv_row_requires_password(nm):
                            st.session_state["dq_load_csv_pwd_prompt"] = True
                            st.session_state["dq_load_csv_pending_name"] = nm
                        else:
                            try:
                                st.session_state.dq_state = dq.dq_load_state_from_csv(nm, None)
                                st.session_state["dq_settings_force_hydrate"] = True
                                dq.dq_migrate_legacy_state(st.session_state.dq_state)
                                meta = st.session_state.dq_state.get("meta", {})
                                meta.setdefault("log", [])
                                meta.setdefault("battle_log", [])
                                st.session_state.dq_state["meta"] = meta
                            except Exception as e:
                                st.error(f"读档失败：{e}")
                                return
                        st.rerun()
                with c2:
                    if st.button("取消", key="dq_load_csv_cancel_inline"):
                        st.session_state["dq_load_csv_prompt"] = False
                        st.rerun()

    if st.session_state.get("dq_load_csv_pwd_prompt"):
        pending = str(st.session_state.get("dq_load_csv_pending_name") or "").strip()
        if dlg:
            @dlg("🔐 存档校验密码")
            def _dq_load_csv_pwd_dialog():
                st.info(f"读取「{pending}」需要输入校验密码。")
                st.text_input("校验密码", type="password", key="dq_load_csv_pwd")
                p1, p2, p3 = st.columns([1, 1, 1])
                with p1:
                    if st.button("确认读取", type="primary", key="dq_load_csv_pwd_ok"):
                        pwd_try = (st.session_state.get("dq_load_csv_pwd") or "").strip()
                        if not pwd_try:
                            st.error("请输入校验密码。")
                            return
                        try:
                            st.session_state.dq_state = dq.dq_load_state_from_csv(pending, pwd_try)
                            st.session_state["dq_settings_force_hydrate"] = True
                            dq.dq_migrate_legacy_state(st.session_state.dq_state)
                            meta = st.session_state.dq_state.get("meta", {})
                            meta.setdefault("log", [])
                            meta.setdefault("battle_log", [])
                            st.session_state.dq_state["meta"] = meta
                            st.session_state["dq_load_csv_pwd_prompt"] = False
                            st.session_state["dq_load_csv_pending_name"] = ""
                            st.rerun()
                        except Exception as e:
                            st.error(f"读档失败：{e}")
                with p3:
                    if st.button("取消", key="dq_load_csv_pwd_cancel"):
                        st.session_state["dq_load_csv_pwd_prompt"] = False
                        st.session_state["dq_load_csv_pending_name"] = ""
                        st.rerun()
            _dq_load_csv_pwd_dialog()
        else:
            st.info(f"读取「{pending}」需要输入校验密码。")
            st.text_input("校验密码", type="password", key="dq_load_csv_pwd_inline")
            p1, p2 = st.columns(2)
            with p1:
                if st.button("确认读取", type="primary", key="dq_load_csv_pwd_ok_inline"):
                    pwd_try = (st.session_state.get("dq_load_csv_pwd_inline") or "").strip()
                    if not pwd_try:
                        st.error("请输入校验密码。")
                    else:
                        try:
                            st.session_state.dq_state = dq.dq_load_state_from_csv(pending, pwd_try)
                            st.session_state["dq_settings_force_hydrate"] = True
                            dq.dq_migrate_legacy_state(st.session_state.dq_state)
                            meta = st.session_state.dq_state.get("meta", {})
                            meta.setdefault("log", [])
                            meta.setdefault("battle_log", [])
                            st.session_state.dq_state["meta"] = meta
                            st.session_state["dq_load_csv_pwd_prompt"] = False
                            st.session_state["dq_load_csv_pending_name"] = ""
                            st.rerun()
                        except Exception as e:
                            st.error(f"读档失败：{e}")
            with p2:
                if st.button("取消", key="dq_load_csv_pwd_cancel_inline"):
                    st.session_state["dq_load_csv_pwd_prompt"] = False
                    st.session_state["dq_load_csv_pending_name"] = ""
                    st.rerun()

    if st.session_state.get("dq_trim_log_prompt"):
        if dlg:
            @dlg("🧹 清空日志确认")
            def _dq_trim_log_dialog():
                st.markdown(
                    """
<div style="padding:10px 12px;border:1px solid #fbbf24;border-radius:10px;background:#fffbeb;">
  <div style="font-weight:700;color:#92400e;margin-bottom:4px;">该操作会清空当前存档会话日志</div>
  <div style="color:#78350f;font-size:13px;">将清空冒险日志与战斗日志，但不会影响角色属性、背包和存档文件。</div>
</div>
""",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
                p1, p2, p3, p4, p5 = st.columns([1, 1, 0.5, 1, 1])
                with p2:
                    if st.button("确认", type="primary", key="dq_trim_log_yes"):
                        meta = st.session_state.dq_state.get("meta", {})
                        meta["log"] = []
                        meta["battle_log"] = []
                        st.session_state.dq_state["meta"] = meta
                        st.session_state["dq_trim_log_prompt"] = False
                        st.rerun()
                with p4:
                    if st.button("取消", key="dq_trim_log_no"):
                        st.session_state["dq_trim_log_prompt"] = False
                        st.rerun()
            _dq_trim_log_dialog()
        else:
            st.warning("确认清空当前会话日志？（不会影响角色、背包与磁盘存档）")
            p1, p2 = st.columns(2)
            with p1:
                if st.button("确认清空", type="primary", key="dq_trim_log_yes"):
                    meta = st.session_state.dq_state.get("meta", {})
                    meta["log"] = []
                    meta["battle_log"] = []
                    st.session_state.dq_state["meta"] = meta
                    st.session_state["dq_trim_log_prompt"] = False
                    st.rerun()
            with p2:
                if st.button("取消", key="dq_trim_log_no"):
                    st.session_state["dq_trim_log_prompt"] = False
                    st.rerun()

    if st.session_state.get("dq_delete_csv_prompt"):
        nm = (state.get("name") or "勇者").strip() or "勇者"
        if dlg:
            @dlg("🗑️ 删除存档确认")
            def _dq_delete_csv_dialog():
                st.markdown(
                    f"""
<div style="padding:10px 12px;border:1px solid #fca5a5;border-radius:10px;background:#fef2f2;">
  <div style="font-weight:700;color:#991b1b;margin-bottom:4px;">确认删除姓名「{nm}」的 CSV 存档记录？</div>
  <div style="color:#7f1d1d;font-size:13px;">仅删除 games/dq_saves.csv 对应行，当前内存中的游戏进度不会被重置。</div>
</div>
""",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
                dp1, dp2, dp3, dp4, dp5 = st.columns([1, 1, 0.5, 1, 1])
                with dp2:
                    if st.button("确认", type="primary", key="dq_delete_csv_yes"):
                        try:
                            dq.dq_delete_save_from_csv(nm)
                            st.session_state["dq_delete_csv_prompt"] = False
                            st.session_state["dq_csv_del_feedback"] = "ok"
                            st.session_state.pop("dq_state", None)
                            for _k in (
                                "dq_load_csv_prompt",
                                "dq_load_csv_pwd_prompt",
                                "dq_load_csv_pending_name",
                                "dq_save_csv_prompt",
                                "dq_trim_log_prompt",
                                "dq_refresh_prompt",
                            ):
                                st.session_state.pop(_k, None)
                        except Exception as e:
                            st.session_state["dq_csv_del_feedback"] = "err"
                            st.session_state["dq_csv_del_err"] = str(e)
                        st.rerun()
                with dp4:
                    if st.button("取消", key="dq_delete_csv_no"):
                        st.session_state["dq_delete_csv_prompt"] = False
                        st.rerun()
            _dq_delete_csv_dialog()
        else:
            st.warning(f"确认从 games/dq_saves.csv 删除姓名「{nm}」的存档记录？（仅删磁盘 CSV 行，当前游戏进度仍在内存中）")
            dp1, dp2 = st.columns(2)
            with dp1:
                if st.button("确认删除", type="primary", key="dq_delete_csv_yes"):
                    try:
                        dq.dq_delete_save_from_csv(nm)
                        st.session_state["dq_delete_csv_prompt"] = False
                        st.session_state["dq_csv_del_feedback"] = "ok"
                        st.session_state.pop("dq_state", None)
                        for _k in (
                            "dq_load_csv_prompt",
                            "dq_load_csv_pwd_prompt",
                            "dq_load_csv_pending_name",
                            "dq_save_csv_prompt",
                            "dq_trim_log_prompt",
                            "dq_refresh_prompt",
                        ):
                            st.session_state.pop(_k, None)
                    except Exception as e:
                        st.session_state["dq_csv_del_feedback"] = "err"
                        st.session_state["dq_csv_del_err"] = str(e)
                    st.rerun()
            with dp2:
                if st.button("取消", key="dq_delete_csv_no"):
                    st.session_state["dq_delete_csv_prompt"] = False
                    st.rerun()

    _fb = st.session_state.pop("dq_csv_save_feedback", None)
    if _fb == "ok":
        st.success("已保存到 games/dq_saves.csv（已写入校验密码哈希）。")
    elif _fb == "err":
        _e = st.session_state.pop("dq_csv_save_err", "未知错误")
        st.error(f"保存失败：{_e}")

    # 删除成功时的提示在「无 dq_state」开始界面展示；此处仅处理删除失败（仍在游戏内）
    _dfb = st.session_state.pop("dq_csv_del_feedback", None)
    if _dfb == "err":
        _de = st.session_state.pop("dq_csv_del_err", "未知错误")
        st.error(f"删除失败：{_de}")

    if st.session_state.get("dq_refresh_prompt", False):
        def _apply_ref_actions(ref_actions: List[str]) -> None:
            ds = st.session_state.dq_state
            logs: List[str] = []
            if "full" in ref_actions:
                ds["hp"] = int(ds.get("max_hp", 1) or 1)
                ds["mp"] = int(ds.get("max_mp", 1) or 1)
                ds["stamina"] = int(ds.get("max_stamina", 0) or 0)
                ds["status_effects"] = []
                for m in ds.get("party_members", []) or []:
                    m["hp"] = int(m.get("max_hp", 1) or 1)
                    m["mp"] = int(m.get("max_mp", 0) or 0)
                logs.append("回满状态")
            if "level_up" in ref_actions:
                need = int(ds.get("exp_to_next", 0) or 0)
                if int(ds.get("level", 1) or 1) < int(getattr(dq, "MAX_PLAYER_LEVEL", 30) or 30) and need > 0:
                    ds["exp"] = int(ds.get("exp", 0) or 0) + need
                    if hasattr(dq, "_maybe_level_up"):
                        dq._maybe_level_up(ds, _rng_for("ref_level_up"), ds.setdefault("meta", {}).setdefault("log", []))
                    logs.append("立刻升级")
                else:
                    logs.append("立刻升级（已在等级上限）")
            if "gold_10k" in ref_actions:
                ds["gold"] = int(ds.get("gold", 0) or 0) + 10000
                logs.append("金币+10000")
            if logs:
                ds.setdefault("meta", {}).setdefault("log", []).append("♻️ REF 刷新执行：" + "、".join(logs) + "。")

        if dlg:
            @dlg("♻️ REF 刷新")
            def _dq_refresh_dialog():
                st.markdown(
                    """
<div style="padding:10px 12px;border:1px solid #93c5fd;border-radius:10px;background:#eff6ff;">
  <div style="font-weight:700;color:#1e3a8a;margin-bottom:4px;">REF 刷新：选择要执行的操作</div>
  <div style="color:#1e40af;font-size:13px;">勾选后输入密码，确认即立即生效。</div>
</div>
""",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                ref_actions = st.multiselect(
                    "选择操作（可多选）",
                    ["full", "level_up", "gold_10k"],
                    default=["full"],
                    format_func=lambda x: {
                        "full": "1）回满状态",
                        "level_up": "2）立刻升级",
                        "gold_10k": "3）金币 +10000",
                    }.get(x, x),
                    key="dq_refresh_actions",
                )
                rp1, rp2, rp3 = st.columns([1, 2, 1])
                with rp2:
                    refresh_pwd = st.text_input("密码", value="", type="password", key="dq_refresh_pwd")
                st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
                rb1, rb2, rb3, rb4, rb5 = st.columns([1, 1, 0.5, 1, 1])
                with rb2:
                    if st.button("确认", key="dq_refresh_confirm_btn", type="primary"):
                        if refresh_pwd != "879879":
                            st.error("密码错误，无法执行 REF 刷新。")
                        elif not ref_actions:
                            st.error("请至少选择一个操作。")
                        else:
                            _apply_ref_actions(ref_actions)
                            st.session_state["dq_refresh_prompt"] = False
                            st.rerun()
                with rb4:
                    if st.button("取消", key="dq_refresh_cancel_btn"):
                        st.session_state["dq_refresh_prompt"] = False
                        st.rerun()
            _dq_refresh_dialog()
        else:
            st.info("请选择 REF 操作并输入密码后确认。")
            ref_actions = st.multiselect(
                "选择操作（可多选）",
                ["full", "level_up", "gold_10k"],
                default=["full"],
                format_func=lambda x: {
                    "full": "1）回满状态",
                    "level_up": "2）立刻升级",
                    "gold_10k": "3）金币 +10000",
                }.get(x, x),
                key="dq_refresh_actions",
            )
            rp1, rp2, rp3 = st.columns([2, 1, 1])
            with rp1:
                refresh_pwd = st.text_input("密码", value="", type="password", key="dq_refresh_pwd")
            with rp2:
                if st.button("确认刷新", key="dq_refresh_confirm_btn", type="primary"):
                    if refresh_pwd != "879879":
                        st.error("密码错误，无法执行 REF 刷新。")
                    elif not ref_actions:
                        st.error("请至少选择一个操作。")
                    else:
                        _apply_ref_actions(ref_actions)
                        st.session_state["dq_refresh_prompt"] = False
                        st.rerun()
            with rp3:
                if st.button("取消", key="dq_refresh_cancel_btn"):
                    st.session_state["dq_refresh_prompt"] = False
                    st.rerun()

    # 战斗相位切换时自动跳转标签：
    # - 遇战：自动切到「战斗」
    # - 结算结束：自动切回「冒险」
    prev_phase = st.session_state.get("dq_prev_phase")
    auto_tab_idx = None
    if prev_phase is None:
        st.session_state["dq_prev_phase"] = phase
        # 首次渲染即处于战斗中（如刷新/直链）：勿播放上一残留的提交后视频
        if phase == "battle":
            st.session_state.pop("dq_battle_video_popup_path", None)
    else:
        if prev_phase != phase:
            if phase == "battle":
                auto_tab_idx = 1  # 战斗
                # 新一场战斗：重置动作标签，避免沿用上局 meta/session（如逃跑）与本次选择（如技能）冲突
                st.session_state["dq_battle_action_type"] = "普攻"
                st.session_state.pop("dq_battle_target_pick", None)
                # 仅「执行动作」提交后才应弹视频，进战瞬间清掉残留路径
                st.session_state.pop("dq_battle_video_popup_path", None)
            elif prev_phase == "battle" and phase != "battle":
                # 有待播的结算视频时勿立刻切 tab，播完由 JS 点回「冒险」
                if not st.session_state.get("dq_battle_video_popup_path"):
                    auto_tab_idx = 0  # 冒险
            st.session_state["dq_prev_phase"] = phase

    if st.session_state.get("dq_stat_tutorial_jump_adventure", False) and phase != "battle":
        auto_tab_idx = 0
    _force_tab_once = st.session_state.pop("dq_force_tab_idx_once", None)
    if _force_tab_once is not None:
        try:
            _fidx = int(_force_tab_once)
            # 战斗中不允许「强制切离战斗」的一次性跳转（如残留的背包 5），
            # 否则会覆盖「遇怪→切战斗」的跳转，导致玩家停在错误的页面。
            if phase != "battle" or _fidx == 1:
                auto_tab_idx = _fidx
        except Exception:
            pass
    q1_tut_global = (state.get("meta") or {}).get("q1_post_act1_tutorial") or {}
    q1_tut_focus_global = str((q1_tut_global or {}).get("focus", ""))
    if (
        q1_tut_focus_global in ("backpack_tab", "equip_button", "equip_pick", "show_equipped")
        and phase != "battle"
        and not dq.dq_has_blocking_modal_notice(state)
    ):
        auto_tab_idx = 5

    _dq_try_render_pending_story_video(st.session_state.dq_state, dq)

    tabs = st.tabs(["冒险", "战斗", "任务/剧情", "天赋树", "商店", "背包/装备", "设置"])
    if auto_tab_idx is not None:
        try:
            _lab = _DQ_GAME_TAB_LABELS[int(auto_tab_idx)]
        except Exception:
            _lab = "冒险"
        # 去重：同一 phase 切换只注入一次 JS，避免 rerun 导致重复弹窗/闪烁
        # 注意：token 必须包含单调递增的序列号，保证每次切换（含第二次、第三次遇怪）
        # 都是唯一事件。若只用 _lab_phase_prev_phase，第二次遇怪会与第一次 token 相同而被去重跳过。
        _switch_token = (
            f"{_lab}_{phase}_{prev_phase}_"
            f"{st.session_state.get('dq_tab_switch_seq', 0)}"
        )
        if st.session_state.get("dq_last_tab_switch_token") != _switch_token:
            st.session_state["dq_last_tab_switch_token"] = _switch_token
            st.session_state["dq_tab_switch_seq"] = (
                st.session_state.get("dq_tab_switch_seq", 0) + 1
            )
            _dq_inject_click_game_tab(_lab)
    if q1_tut_focus_global == "backpack_tab":
        pass

    if st.session_state.pop("dq_battle_focus_battle_tab_for_video", False):
        _dq_inject_click_game_tab("战斗")

    # ---------------- 冒险（非战斗） ----------------
    with tabs[0]:
        if st.session_state.get("dq_stat_tutorial_jump_adventure", False):
            st.markdown(
                """
<style>
.dq-tutorial-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  z-index: 99990;
  pointer-events: none;
}
.st-key-dq_stat_tutorial_continue {
  position: relative;
  z-index: 100000;
  margin-top: 8px;
}
.st-key-dq_story_pick_submit,
.st-key-dq_clue_story_ack_x,
.st-key-dq_clue_story_ack_fallback_x {
  position: relative;
  z-index: 100000;
}
.st-key-dq_stat_tutorial_continue div[data-testid="stButton"] > button,
.st-key-dq_stat_tutorial_continue button[kind="primary"],
.st-key-dq_story_pick_submit div[data-testid="stButton"] > button,
.st-key-dq_story_pick_submit button[kind="primary"],
.st-key-dq_clue_story_ack_x div[data-testid="stButton"] > button,
.st-key-dq_clue_story_ack_fallback_x div[data-testid="stButton"] > button {
  font-weight: 800 !important;
  font-size: 1.06rem !important;
  background: linear-gradient(90deg, #ef4444 0%, #dc2626 100%) !important;
  color: #ffffff !important;
  border: 3px solid #b91c1c !important;
  border-radius: 12px !important;
  outline: 3px solid rgba(254, 202, 202, 0.98) !important;
  outline-offset: 2px !important;
  box-shadow: 0 0 0 4px rgba(254, 202, 202, 0.95), 0 0 22px rgba(239, 68, 68, 0.50) !important;
}
.st-key-dq_stat_tutorial_continue div[data-testid="stButton"] > button:hover:enabled,
.st-key-dq_stat_tutorial_continue button[kind="primary"]:hover:enabled,
.st-key-dq_story_pick_submit div[data-testid="stButton"] > button:hover:enabled,
.st-key-dq_story_pick_submit button[kind="primary"]:hover:enabled {
  filter: brightness(1.08);
}
</style>
<div class="dq-tutorial-overlay" aria-hidden="true"></div>
""",
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="border:3px solid #ef4444;border-radius:10px;padding:10px 12px;'
                'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:10px;position:relative;z-index:100000;">'
                "新手加点已完成。请阅读本页内容后，点击下方「确定并继续」。</div>",
                unsafe_allow_html=True,
            )
            components.html(
                """
<script>
setTimeout(() => {
  window.parent.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
}, 120);
</script>
""",
                height=1,
                width=1,
                scrolling=False,
            )
            meta_hint = state.get("meta") or {}
            _has_story_continue_btn = isinstance(meta_hint.get("pending_story"), dict)
            if not _has_story_continue_btn:
                if st.button("确定并继续", type="primary", key="dq_stat_tutorial_continue"):
                    st.session_state["dq_stat_tutorial_jump_adventure"] = False
                    st.success("已完成新手引导，接下来可自由探索。")
                    st.rerun()
        if phase == "battle":
            st.warning("当前处于战斗中，请到「战斗」标签操作。")
        else:
            # 剧情互动优先：存在 pending_story 时，先完成剧情选择再继续探索/旅行
            meta = state.get("meta") or {}
            q1_tut = meta.get("q1_post_act1_tutorial")
            q1_tut_active = isinstance(q1_tut, dict) and bool(q1_tut.get("active"))
            q1_tut_focus = str((q1_tut or {}).get("focus", "explore_btn"))
            if q1_tut_active and q1_tut_focus == "log_then_explore":
                _recent_logs = [str(x) for x in (meta.get("log") or [])][-10:]
                if any("获得道具：" in ln for ln in _recent_logs):
                    st.session_state.dq_state.setdefault("meta", {}).setdefault(
                        "q1_post_act1_tutorial", {}
                    )["focus"] = "backpack_tab"
                    q1_tut_focus = "backpack_tab"
            if q1_tut_active:
                if q1_tut_focus == "explore_btn":
                    focus_css = ".st-key-dq_explore_btn > div[data-testid='stButton'] > button"
                elif q1_tut_focus == "backpack_tab":
                    focus_css = ".dq-no-focus-target"
                elif q1_tut_focus == "adventure_rest":
                    focus_css = ".st-key-dq_rest_btn > div[data-testid='stButton'] > button"
                elif q1_tut_focus == "adventure_infinite":
                    focus_css = ".st-key-dq_infinite_btn > div[data-testid='stButton'] > button"
                elif q1_tut_focus == "log_then_explore":
                    focus_css = (
                        ".st-key-dq_advlog_focus_wrap textarea, "
                        ".st-key-dq_explore_btn > div[data-testid='stButton'] > button"
                    )
                else:
                    focus_css = ".st-key-dq_advlog_focus_wrap textarea"
                st.markdown(
                    f"""
<style>
.dq-q1-tut-overlay {{
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.40);
  z-index: 99970;
  pointer-events: none;
}}
.st-key-dq_explore_btn,
.st-key-dq_rest_btn,
.st-key-dq_infinite_btn,
.st-key-dq_advlog_focus_wrap {{
  position: relative;
  z-index: 100000;
}}
.st-key-dq_advlog_focus_wrap textarea,
.st-key-dq_explore_btn > div[data-testid='stButton'] > button,
.st-key-dq_rest_btn > div[data-testid='stButton'] > button,
.st-key-dq_infinite_btn > div[data-testid='stButton'] > button {{
  border: 1px solid transparent !important;
  box-shadow: none !important;
}}
{focus_css} {{
  border: 3px solid #ef4444 !important;
  box-shadow: 0 0 0 4px rgba(254, 202, 202, 0.95), 0 0 18px rgba(239, 68, 68, 0.45) !important;
}}
</style>
<div class="dq-q1-tut-overlay" aria-hidden="true"></div>
""",
                    unsafe_allow_html=True,
                )
                if q1_tut_focus == "explore_btn":
                    st.markdown(
                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                        "🎯 新手指引：请点击左侧「🧭 探索（5体力）」按钮。</div>",
                        unsafe_allow_html=True,
                    )
                elif q1_tut_focus == "log_then_explore":
                    st.markdown(
                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                        "🎯 新手指引：请查看右侧「冒险日志」中的本次探索结果，然后再点一次探索。</div>",
                        unsafe_allow_html=True,
                    )
                elif q1_tut_focus == "backpack_tab":
                    st.markdown(
                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                        "🎯 新手指引：请点击上方「背包/装备」标签，继续装备教学。</div>",
                        unsafe_allow_html=True,
                    )
                elif q1_tut_focus == "adventure_rest":
                    st.markdown(
                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                        "🎯 新手指引：点击旅店休息可恢复角色HP/MP和体力值。</div>",
                        unsafe_allow_html=True,
                    )
                elif q1_tut_focus == "adventure_infinite":
                    st.markdown(
                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                        "🎯 新手指引：无限地牢可提供练级获取装备的途径，挑战过难可以选择训练并选择已通关层数。</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                        'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                        "🎯 新手指引：请查看右侧「冒险日志」中的本次探索结果，然后再点一次探索。</div>",
                        unsafe_allow_html=True,
                    )
            if not isinstance(meta.get("pending_story"), dict):
                st.session_state.pop("dq_last_story_video_key", None)
            pending_clue_story = meta.get("pending_clue_story")
            if isinstance(pending_clue_story, dict):
                clue_title = str(pending_clue_story.get("title", "关键线索"))
                clue_id = str(pending_clue_story.get("id", "") or "")
                clue_story = _dq_story_to_paragraphs(str(pending_clue_story.get("story", "") or ""))
                escaped_story = (
                    clue_story.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace('"', "&quot;")
                    .replace("\n", "<br/>")
                )
                ch_shuf = pending_clue_story.get("choices_shuffled") or []
                interaction = str(pending_clue_story.get("interaction", "") or "")
                dlg = getattr(st, "dialog", None) or getattr(st, "experimental_dialog", None)
                if dlg:
                    @dlg(f"📜 关键线索：{clue_title}", width="large")
                    def _dq_clue_story_dialog():
                        st.markdown(
                            '<p style="margin:0 0 10px 0;color:#334155;font-size:14px;font-weight:600;line-height:1.5;">'
                            "阅读线索后，与内心的声音对话并三选一（每条线索仅一次机会，影响本图领悟总分）。"
                            "</p>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"""
<style>
.dq-clue-wrap {{
  position: relative;
  height: 420px;
  overflow: hidden;
  border: 1px solid #475569;
  border-radius: 10px;
  padding: 12px;
  background: linear-gradient(165deg, #0f172a 0%, #1e293b 100%);
  color: #f8fafc;
}}
.dq-clue-scroll {{
  position: absolute;
  left: 12px;
  right: 12px;
  line-height: 1.95;
  font-size: 16px;
  font-weight: 500;
  color: #f8fafc;
  -webkit-font-smoothing: antialiased;
  text-shadow: 0 1px 2px rgba(0,0,0,0.45);
  /* 滚完后黑屏短暂停留，再从头循环（避免一直停在全黑） */
  animation: dqClueScroll 38s linear infinite;
}}
@keyframes dqClueScroll {{
  0% {{ transform: translateY(100%); }}
  88% {{ transform: translateY(-105%); }}
  100% {{ transform: translateY(-105%); }}
}}
</style>
<div class="dq-clue-wrap">
  <div class="dq-clue-scroll">{escaped_story}</div>
</div>
""",
                            unsafe_allow_html=True,
                        )
                        st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
                        if interaction:
                            st.markdown(f"**与主角的对话**")
                            st.info(interaction)
                        if ch_shuf and len(ch_shuf) >= 1:
                            labels = [str(o.get("text", "?")) for o in ch_shuf]
                            pick = st.radio(
                                "你的回应",
                                list(range(len(labels))),
                                format_func=lambda i: labels[int(i)],
                                key=f"dq_clue_quiz_pick_{clue_id}",
                            )
                            if st.button("确认领悟", type="primary", key=f"dq_clue_quiz_submit_{clue_id}"):
                                sel = ch_shuf[int(pick)] if int(pick) < len(ch_shuf) else {}
                                sc = int(sel.get("score", 0) or 0)
                                ans = str(sel.get("answer", "") or "")
                                st.session_state.dq_state = dq.dq_record_clue_quiz_answer(
                                    st.session_state.dq_state, clue_id, sc, ans
                                )
                                st.session_state["dq_stat_tutorial_jump_adventure"] = False
                                _trim_log()
                                st.rerun()
                        else:
                            if st.button("我已阅读，继续冒险", type="primary", key=f"dq_clue_story_ack_{clue_id or 'x'}"):
                                if clue_id:
                                    st.session_state.dq_state = dq.dq_record_clue_quiz_answer(
                                        st.session_state.dq_state, clue_id, 3
                                    )
                                else:
                                    st.session_state.dq_state.setdefault("meta", {})["pending_clue_story"] = None
                                st.session_state["dq_stat_tutorial_jump_adventure"] = False
                                _trim_log()
                                st.rerun()

                    _dq_clue_story_dialog()
                else:
                    st.markdown(f"### 📜 关键线索：{clue_title}")
                    st.markdown(clue_story)
                    if interaction:
                        st.markdown(f"**与主角的对话**")
                        st.info(interaction)
                    if ch_shuf and len(ch_shuf) >= 1:
                        labels = [str(o.get("text", "?")) for o in ch_shuf]
                        pick = st.radio(
                            "你的回应",
                            list(range(len(labels))),
                            format_func=lambda i: labels[int(i)],
                            key=f"dq_clue_quiz_pick_inline_{clue_id}",
                        )
                        if st.button("确认领悟", type="primary", key=f"dq_clue_quiz_submit_inline_{clue_id}"):
                            sel = ch_shuf[int(pick)] if int(pick) < len(ch_shuf) else {}
                            sc = int(sel.get("score", 0) or 0)
                            ans = str(sel.get("answer", "") or "")
                            st.session_state.dq_state = dq.dq_record_clue_quiz_answer(
                                st.session_state.dq_state, clue_id, sc, ans
                            )
                            st.session_state["dq_stat_tutorial_jump_adventure"] = False
                            _trim_log()
                            st.rerun()
                    else:
                        if st.button("我已阅读，继续冒险", type="primary", key=f"dq_clue_story_ack_fallback_{clue_id or 'x'}"):
                            if clue_id:
                                st.session_state.dq_state = dq.dq_record_clue_quiz_answer(
                                    st.session_state.dq_state, clue_id, 3
                                )
                            else:
                                st.session_state.dq_state.setdefault("meta", {})["pending_clue_story"] = None
                            st.session_state["dq_stat_tutorial_jump_adventure"] = False
                            _trim_log()
                            st.rerun()
                st.stop()

            pending_story = meta.get("pending_story")
            if isinstance(pending_story, dict):
                st.markdown(f"### 剧情互动：{pending_story.get('title', '主线剧情')}")
                if (
                    str(pending_story.get("sid", "")) == "q1_seal_whisper"
                    and int(pending_story.get("step", 0) or 0) == 0
                ):
                    st.caption("若配置了分集动画（…第一幕_P1、_P2…）将自动连播；然后请阅读正文并继续。")
                else:
                    st.caption("请选择你的回应。选错将中断本次推进，并触发惩罚分支（HP/MP/体力受损，后续难度上升）。")
                triggered = pending_story.get("triggered") or []
                if triggered:
                    st.caption("本次触发剧情：" + "、".join([str(x) for x in triggered]))
                scene = pending_story.get("scene", "")
                st.write(scene)

                choices = pending_story.get("choices") or {}
                choice_ids = list(choices.keys())
                if choice_ids:
                    picked = st.radio(
                        "你的选择",
                        choice_ids,
                        format_func=lambda cid: str(choices.get(cid, cid)),
                        key=f"dq_story_pick_{pending_story.get('step', 0)}",
                    )
                    if st.button("确定并继续", type="primary", key="dq_story_pick_submit"):
                        st.session_state.dq_state = dq.dq_resolve_story_choice(
                            state, picked, _rng_for(f"story_{pending_story.get('sid', 'main')}")
                        )
                        st.session_state["dq_stat_tutorial_jump_adventure"] = False
                        _trim_log()
                        st.rerun()
                st.stop()

            zones = dq.dq_available_zones(state)
            zone_ids = [z["id"] for z in zones]
            current = state.get("location", "starter")
            zone_map = {z["id"]: z.get("name", z["id"]) for z in zones}
            # 同排：左栏「选择区域并旅行」+ 下方竖排按钮；右栏「冒险日志」
            col_zone, col_advlog = st.columns([0.72, 1.28])
            with col_zone:
                current_name = _dq_overworld_zone_display_name(state, zone_map, current, dq)
                st.markdown(f"**📍 当前区域：** {current_name}")
                st.markdown(
                    """
                    <style>
                    /* 标题与下拉框之间留白收紧 */
                    p.dq-travel-title {
                        margin: 0 0 0.2rem 0 !important;
                        padding: 0 !important;
                        line-height: 1.55;
                    }
                    .st-key-dq_zone_travel_sel {
                        margin-top: 0 !important;
                    }
                    div[data-testid="stHorizontalBlock"]:has(.st-key-dq_travel_btn) {
                        margin-top: 0 !important;
                    }
                    .st-key-dq_travel_btn button[kind="primary"] {
                        background-color: #16a34a !important;
                        color: #ffffff !important;
                        border: 1px solid #15803d !important;
                    }
                    .st-key-dq_travel_btn button[kind="primary"]:hover:enabled {
                        background-color: #15803d !important;
                        border-color: #166534 !important;
                    }
                    .st-key-dq_travel_btn button[kind="primary"]:disabled {
                        background-color: #86efac !important;
                        color: #f0fdf4 !important;
                        border-color: #bbf7d0 !important;
                        opacity: 0.85;
                    }
                    </style>
                    <p class="dq-travel-title"><strong>选择区域并旅行</strong></p>
                    """,
                    unsafe_allow_html=True,
                )
                row_sel, row_go = st.columns(
                    [2.6, 1.1], gap="small", vertical_alignment="center"
                )
                with row_sel:
                    sel = st.selectbox(
                        "zone_travel",
                        zone_ids,
                        index=zone_ids.index(current) if current in zone_ids else 0,
                        format_func=lambda zid: zone_map.get(zid, zid),
                        label_visibility="collapsed",
                        key="dq_zone_travel_sel",
                        disabled=bool(q1_tut_active),
                    )
                hero_lv = int(state.get("level", 1) or 1)
                z_lo, z_hi = (1, 30)
                if hasattr(dq, "dq_zone_level_range"):
                    try:
                        z_lo, z_hi = dq.dq_zone_level_range(sel)
                    except Exception:
                        z_lo, z_hi = (1, 30)
                need_confirm_low_lv = int(z_lo) > 1 and hero_lv < int(z_lo)
                with row_go:
                    if st.button(
                        "🚶 前往",
                        key="dq_travel_btn",
                        type="primary",
                        width="stretch",
                        help="移动至下拉框所选区域",
                        disabled=(sel == current) or bool(q1_tut_active),
                    ):
                        if need_confirm_low_lv:
                            st.session_state["dq_travel_lowlv_confirm"] = {
                                "target": sel,
                                "name": zone_map.get(sel, sel),
                                "lo": int(z_lo),
                                "hi": int(z_hi),
                            }
                        else:
                            st.session_state.dq_state["location"] = sel
                        st.rerun()
                if st.button(
                    "🧭 探索（5体力）",
                    type="primary",
                    disabled=state.get("stamina", 0) < 5,
                    key="dq_explore_btn",
                    width="stretch",
                ):
                    st.session_state.dq_state = dq.dq_explore(state, _rng_for("explore"))
                    _trim_log()
                    st.rerun()
                if st.button(
                    "🛖 旅店休息",
                    key="dq_rest_btn",
                    help=f"消耗 {inn_cost} 金币，全员 HP/MP/体力回满并清除异常",
                    width="stretch",
                    disabled=bool(q1_tut_active and q1_tut_focus != "adventure_rest"),
                ):
                    st.session_state.dq_state = dq.dq_rest(state, _rng_for("rest"))
                    _qt_adv = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                    if bool(_qt_adv.get("active")) and str(_qt_adv.get("focus", "")) == "adventure_rest":
                        _qt_adv["focus"] = "adventure_infinite"
                    _trim_log()
                    st.rerun()
                floor = int(state.get("dungeon", {}).get("floor", 1))
                if st.button(
                    f"🌀 无限地牢（第{floor}层）",
                    type="secondary",
                    key="dq_infinite_btn",
                    width="stretch",
                    disabled=bool(q1_tut_active and q1_tut_focus != "adventure_infinite"),
                ):
                    st.session_state["dq_infinite_mode_open"] = not bool(
                        st.session_state.get("dq_infinite_mode_open")
                    )
                    _qt_adv = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                    if bool(_qt_adv.get("active")) and str(_qt_adv.get("focus", "")) == "adventure_infinite":
                        _qt_adv["active"] = False
                        _qt_adv["focus"] = "done"
                    st.rerun()
                if st.session_state.get("dq_infinite_mode_open"):
                    with st.container(border=True):
                        st.markdown("##### 🌀 无尽模式入口")
                        st.caption(
                            "挑战：进入当前最高层；训练：从 1～最高层−1 选层，进度不保存，每次都会刷新怪物。"
                        )
                        mode = st.radio(
                            "选择模式",
                            ["挑战", "训练"],
                            horizontal=True,
                            key="dq_infinite_entry_mode",
                            label_visibility="collapsed",
                        )
                        if mode == "挑战":
                            if st.button(
                                "进入挑战",
                                type="primary",
                                key="dq_infinite_go_challenge",
                                width="stretch",
                            ):
                                st.session_state.dq_state = dq.dq_open_infinite_dungeon_battle(state, _rng_for("inf"))
                                st.session_state.pop("dq_infinite_mode_open", None)
                                _trim_log()
                                st.rerun()
                            if st.button("取消", key="dq_infinite_mode_cancel_challenge", width="stretch"):
                                st.session_state.pop("dq_infinite_mode_open", None)
                                st.rerun()
                        else:
                            top_floor = max(1, int(state.get("dungeon", {}).get("floor", 1) or 1))
                            max_train_floor = max(0, top_floor - 1)
                            if max_train_floor <= 0:
                                st.info("当前最高层为 1 层，尚无可训练楼层。请先通过挑战推进层数。")
                                if st.button("关闭", key="dq_infinite_train_close", width="stretch"):
                                    st.session_state.pop("dq_infinite_mode_open", None)
                                    st.rerun()
                            else:
                                st.caption("训练楼层")
                                train_floor = st.selectbox(
                                    "训练楼层",
                                    list(range(1, max_train_floor + 1)),
                                    index=max_train_floor - 1,
                                    key="dq_infinite_train_floor",
                                    label_visibility="collapsed",
                                )
                                if st.button(
                                    "进入训练",
                                    type="primary",
                                    key="dq_infinite_go_train",
                                    width="stretch",
                                ):
                                    st.session_state.dq_state = dq.dq_open_infinite_dungeon_training_battle(
                                        state, _rng_for("inf_train"), int(train_floor)
                                    )
                                    st.session_state.pop("dq_infinite_mode_open", None)
                                    _trim_log()
                                    st.rerun()
                                if st.button("取消", key="dq_infinite_mode_cancel_train", width="stretch"):
                                    st.session_state.pop("dq_infinite_mode_open", None)
                                    st.rerun()
            with col_advlog:
                with st.container(key="dq_advlog_focus_wrap"):
                    with st.expander("📜 冒险日志", expanded=True):
                        meta = st.session_state.dq_state.get("meta", {})
                        log = meta.get("log", [])
                        turn = int(meta.get("turn", 0) or 0)
                        st.text_area(
                            " ",
                            value=_dq_log_display_rev(log, 220),
                            height=320,
                            disabled=True,
                            label_visibility="collapsed",
                            key=f"dq_overworld_log_textarea_{turn}",
                        )

            if st.session_state.get("dq_travel_lowlv_confirm"):
                cfm = st.session_state.get("dq_travel_lowlv_confirm") or {}
                tname = str(cfm.get("name", "该区域"))
                lo = int(cfm.get("lo", 1) or 1)
                hi = int(cfm.get("hi", 30) or 30)
                st.warning(
                    f"⚠️ 前方区域怪物很强（建议等级 {lo}-{hi}）。你当前等级偏低，是否继续前往「{tname}」？"
                )
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("继续前往", type="primary", key="dq_travel_lowlv_yes"):
                        target = str((st.session_state.get("dq_travel_lowlv_confirm") or {}).get("target", "") or "")
                        if target:
                            st.session_state.dq_state["location"] = target
                        st.session_state.pop("dq_travel_lowlv_confirm", None)
                        st.rerun()
                with cc2:
                    if st.button("取消", key="dq_travel_lowlv_no"):
                        st.session_state.pop("dq_travel_lowlv_confirm", None)
                        st.rerun()

    # ---------------- 战斗（回合制） ----------------
    with tabs[1]:
        _pop_battle_vid = st.session_state.pop("dq_battle_video_popup_path", None)
        if (
            _pop_battle_vid
            and os.path.isfile(str(_pop_battle_vid))
            and st.session_state.get("dq_settings_battle_anim", True)
        ):
            _dq_render_battle_video_popup(
                str(_pop_battle_vid),
                click_adventure_tab_after=(str(phase) != "battle"),
            )

        if phase != "battle":
            st.info("当前不在战斗中。点击「探索」或「无限地牢挑战」开始一场回合制战斗。")
            meta = st.session_state.dq_state.get("meta", {})
            blog = meta.get("battle_log", [])
            if blog:
                with st.expander("📜 战斗日志（最近战斗·最新在上）", expanded=False):
                    st.markdown(
                        _dq_battle_log_html(blog, 220, max_height="240px"),
                        unsafe_allow_html=True,
                    )
        else:
            _mp_insufficient_notice = bool(st.session_state.pop("dq_mp_insufficient_notice", False))
            battle = state.get("battle", {})
            q1_tut_b = (state.get("meta") or {}).get("q1_post_act1_tutorial") or {}
            q1_battle_tut_active = bool(
                isinstance(q1_tut_b, dict)
                and bool(q1_tut_b.get("active"))
                and str(q1_tut_b.get("focus", "")).startswith("battle_")
            )
            q1_battle_focus = str(q1_tut_b.get("focus", "")) if isinstance(q1_tut_b, dict) else ""
            if q1_battle_tut_active:
                if q1_battle_focus == "battle_skill":
                    b_focus_css = ".st-key-dq_battle_act_1 > div[data-testid='stButton'] > button"
                    b_tip = "🎯 战斗引导：先点击「技能」。"
                elif q1_battle_focus == "battle_attack":
                    b_focus_css = ".st-key-dq_battle_act_0 > div[data-testid='stButton'] > button"
                    b_tip = "🎯 战斗引导：已尝试 3 次技能仍未击杀，请改用「普攻」。"
                elif q1_battle_focus == "battle_execute":
                    b_focus_css = ".st-key-dq_battle_submit_btn > div[data-testid='stFormSubmitButton'] > button"
                    b_tip = "🎯 战斗引导：点击「✅ 执行动作」。"
                else:
                    b_focus_css = ".st-key-dq_battle_log_focus_wrap"
                    b_tip = "🎯 战斗引导：查看右侧战斗日志，然后继续下一轮技能操作。"
                st.markdown(
                    f"""
<style>
.dq-q1-battle-overlay {{
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.42);
  z-index: 99970;
  pointer-events: none;
}}
.st-key-dq_battle_log_focus_wrap,
.st-key-dq_battle_submit_btn,
.st-key-dq_battle_act_1 {{
  position: relative;
  z-index: 100000;
}}
{b_focus_css} {{
  border: 3px solid #ef4444 !important;
  border-radius: 10px !important;
  box-shadow: 0 0 0 4px rgba(254, 202, 202, 0.95), 0 0 18px rgba(239, 68, 68, 0.45) !important;
}}
</style>
<div class="dq-q1-battle-overlay" aria-hidden="true"></div>
""",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                    'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                    + b_tip
                    + "</div>",
                    unsafe_allow_html=True,
                )
            enemies = battle.get("enemies") or ([battle.get("enemy")] if battle.get("enemy") else [])
            alive_enemies = [e for e in enemies if e and int(e.get("hp", 0) or 0) > 0]
            player_hp = int(battle.get("player_hp", 0))
            player_max_hp = int(battle.get("player_max_hp", 1))
            player_mp = int(battle.get("player_mp", 0))
            allies = battle.get("allies", []) or []

            st.markdown("### 敌我状态（卡片）")
            st.markdown("#### 我方")
            friend_cards: List[Dict[str, Any]] = [{
                "name": f"{state.get('name', '勇者')}（Lv{int(state.get('level', 1) or 1)}）",
                "avatar": _dq_avatar_url(
                    "hero",
                    state.get("role", "warrior"),
                    hero_gender=str(state.get("hero_gender") or "男"),
                ),
                "hp": player_hp,
                "max_hp": player_max_hp,
                "mp": player_mp,
                "max_mp": int(battle.get("player_max_mp", 1) or 1),
                "subtitle": "战士",
                "show_mp": True,
            }]
            for a in allies:
                ah = int(a.get("hp", 0) or 0)
                amh = int(a.get("max_hp", 1) or 1)
                amp = int(a.get("mp", 0) or 0)
                ampm = int(a.get("max_mp", 1) or 1)
                role = str(a.get("role", ""))
                alv = int(a.get("level", state.get("level", 1)) or 1)
                friend_cards.append(
                    {
                        "name": f"{str(a.get('name', '队友'))}（Lv{alv}）",
                        "avatar": _dq_avatar_url("hero", role),
                        "hp": ah,
                        "max_hp": amh,
                        "mp": amp,
                        "max_mp": ampm,
                        "subtitle": f"队友·{role}",
                        "show_mp": True,
                    }
                )
            for i, c in enumerate(friend_cards):
                if i % 3 == 0:
                    row_cols = st.columns(3)
                with row_cols[i % 3]:
                    _dq_battle_unit_card(
                        name=c["name"],
                        avatar_path=c["avatar"],
                        hp=c["hp"],
                        max_hp=c["max_hp"],
                        mp=c["mp"],
                        max_mp=c["max_mp"],
                        show_mp=bool(c["show_mp"]),
                    )

            st.markdown("#### 敌方")
            if alive_enemies:
                for i, e in enumerate(alive_enemies[:5]):
                    eh = int(e.get("hp", 0) or 0)
                    emh = int(e.get("max_hp", 1) or 1)
                    emp = int(e.get("mp", 0) or 0)
                    empm = int(e.get("max_mp", max(1, emp)) or max(1, emp))
                    elv = int(e.get("level", 1) or 1)
                    if i % 3 == 0:
                        row_cols = st.columns(3)
                    enemy_label = f"{str(e.get('name', '未知怪物'))}（Lv{elv}）"
                    with row_cols[i % 3]:
                        _dq_battle_unit_card(
                            name=enemy_label,
                            avatar_path=_dq_avatar_url("enemy", e.get("name", "史莱姆")),
                            hp=eh,
                            max_hp=emh,
                            mp=emp,
                            max_mp=empm,
                            show_mp=False,
                        )
            else:
                st.info("敌人：—")

            # 技能/药水数据：具体下拉仅在选择了「技能」「药水」时在动作区下方渲染（与动作合并）
            all_skills = state.get("skills", []) or []
            skill_catalog = {
                "lianzhan": "连斩",
                "heavy_strike": "援护",
                "whirlwind": "旋风斩",
                "deep_cut": "深割",
                "armor_break": "盾反",
                "blood_rage": "嗜血",
                "execution": "战吼",
            }
            skill_mp_map: Dict[str, int] = {}
            if hasattr(dq, "_skill_catalog"):
                try:
                    _sc = dq._skill_catalog()
                    skill_mp_map = {str(k): int(getattr(v, "mp_cost", 0) or 0) for k, v in (_sc or {}).items()}
                except Exception:
                    skill_mp_map = {}
            _have_sk = frozenset(s for s in all_skills if s in skill_catalog)
            valid_skills = [s for s in _dq_hero_battle_skill_order if s in _have_sk]
            valid_skills += sorted(s for s in _have_sk if s not in valid_skills)
            sid_default = st.session_state.get("dq_selected_skill_id")
            if sid_default not in valid_skills:
                sid_default = valid_skills[0] if valid_skills else None

            # 药水选择（与技能一致：下拉选择；同类合并显示为 ×N）
            potion_items = []
            for it in state.get("inventory", []):
                meta = it.get("meta", {}) or {}
                if meta.get("use") in _dq_potion_uses and int(it.get("qty", 0)) > 0:
                    potion_items.append(it)
            potion_groups: Dict[str, Dict[str, Any]] = {}
            for it in potion_items:
                meta = it.get("meta", {}) or {}
                u = str(meta.get("use", ""))
                if not u:
                    continue
                if u not in potion_groups:
                    potion_groups[u] = {
                        "qty": 0,
                        "sample": it,
                        "ids": [],
                    }
                potion_groups[u]["qty"] += int(it.get("qty", 0) or 0)
                potion_groups[u]["ids"].append(it.get("item_id"))
            potion_option_keys = [
                k
                for k in ("heal_potion", "mp_potion", "dual_potion", "full_heal_potion", "full_mp_potion", "golden_apple", "revive_potion")
                if k in potion_groups
            ] + [
                k
                for k in potion_groups.keys()
                if k not in {"heal_potion", "mp_potion", "dual_potion", "full_heal_potion", "full_mp_potion", "golden_apple", "revive_potion"}
            ]
            preferred_potion = st.session_state.get("dq_selected_potion_use")
            if preferred_potion not in potion_option_keys:
                preferred_potion = potion_option_keys[0] if potion_option_keys else None

            _def_cd_battle = int((battle.get("defend_cd") if isinstance(battle, dict) else 0) or 0)
            action_options = ["普攻", "技能", "防守", "药水", "逃跑"]
            if _def_cd_battle > 0:
                action_options = [x for x in action_options if x != "防守"]
                if st.session_state.get("dq_battle_action_type") == "防守":
                    st.session_state["dq_battle_action_type"] = "普攻"
            action_col, log_col = st.columns([1.1, 0.9])
            with action_col:
                # 动作必须放在表单外：表单内控件在提交前不同步 session_state。
                # 使用按钮组替代 radio，增大可点区域。
                # 上次选择同时写入 meta.battle_ui_last_action，避免提交后重跑时 session 键丢失又变回普攻。
                st.caption("选择动作")
                _meta_ui = state.get("meta") or {}
                _from_save = _meta_ui.get("battle_ui_last_action")
                if _from_save == "使用药水":
                    _from_save = "药水"
                if _from_save not in action_options:
                    _from_save = None
                _cur_act = st.session_state.get("dq_battle_action_type")
                if _cur_act == "使用药水":
                    _cur_act = "药水"
                    st.session_state["dq_battle_action_type"] = "药水"
                if _cur_act not in action_options:
                    _cur_act = _from_save or "普攻"
                    st.session_state["dq_battle_action_type"] = _cur_act
                _act_cols = st.columns(len(action_options))
                for _i, _opt in enumerate(action_options):
                    with _act_cols[_i]:
                        if st.button(
                            _opt,
                            key=f"dq_battle_act_{_i}",
                            type="primary" if _cur_act == _opt else "secondary",
                            width="stretch",
                        ):
                            st.session_state["dq_battle_action_type"] = _opt
                            _qt_act = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                            if bool(_qt_act.get("active")):
                                _qf = str(_qt_act.get("focus", ""))
                                if _qf in ("battle_skill", "battle_log", "battle_attack"):
                                    if str(_opt) == "技能" and _qf != "battle_attack":
                                        _qt_act["focus"] = "battle_execute"
                                    elif str(_opt) == "普攻" and _qf == "battle_attack":
                                        _qt_act["focus"] = "battle_execute"
                            if str(_opt) not in ("普攻", "技能"):
                                st.session_state.pop("dq_battle_target_pick", None)
                            st.rerun()
                atype_outer = st.session_state.get("dq_battle_action_type", "普攻")
                if q1_battle_tut_active and q1_battle_focus in ("battle_skill", "battle_log", "battle_attack"):
                    if str(atype_outer) == "技能" and q1_battle_focus != "battle_attack":
                        st.session_state.dq_state.setdefault("meta", {}).setdefault(
                            "q1_post_act1_tutorial", {}
                        )["focus"] = "battle_execute"
                        q1_battle_focus = "battle_execute"
                    elif str(atype_outer) == "普攻" and q1_battle_focus == "battle_attack":
                        st.session_state.dq_state.setdefault("meta", {}).setdefault(
                            "q1_post_act1_tutorial", {}
                        )["focus"] = "battle_execute"
                        q1_battle_focus = "battle_execute"
                if _def_cd_battle > 0:
                    st.caption(f"🛡️ 防守冷却中（剩余 {_def_cd_battle} 回合），本回合无法再次防守。")

                if atype_outer == "技能":
                    if valid_skills:
                        st.markdown("##### 📌 本回合技能")
                        if _mp_insufficient_notice:
                            st.warning("MP不足，无法执行行动。请改选普攻或消耗更低/先补 MP。")
                        _battle_cd = (state.get("battle") or {}).get("skill_cd") or {}

                        def _dq_skill_select_fmt(x):
                            lab = f"{skill_catalog.get(x, x)}（MP-{int(skill_mp_map.get(str(x), 0) or 0)}）"
                            if str(x) in ("execution", "armor_break"):
                                c = int(_battle_cd.get(str(x), 0) or 0)
                                if c > 0:
                                    lab += f" · 冷却{c}回合"
                            return lab

                        st.radio(
                            "选择技能",
                            valid_skills,
                            index=valid_skills.index(sid_default) if sid_default in valid_skills else 0,
                            format_func=_dq_skill_select_fmt,
                            key="dq_selected_skill_id",
                        )
                        skill_desc_map = dq.dq_skill_descriptions()
                        selected_sid = st.session_state.get("dq_selected_skill_id")
                        if selected_sid:
                            st.caption(skill_desc_map.get(selected_sid, "暂无技能描述。"))
                    else:
                        st.warning("当前没有任何技能。请先探索/升级后再来战斗。")

                if atype_outer == "药水":
                    if potion_option_keys:
                        st.markdown("##### 🧪 本回合药水")
                        st.radio(
                            "选择药水",
                            potion_option_keys,
                            index=potion_option_keys.index(preferred_potion)
                            if preferred_potion in potion_option_keys
                            else 0,
                            format_func=lambda uk: f"{(potion_groups[uk]['sample']).get('name', '药水')} ×{int(potion_groups[uk]['qty'] or 0)}",
                            key="dq_selected_potion_use",
                            horizontal=True,
                        )
                        selected_use = st.session_state.get("dq_selected_potion_use")
                        if selected_use in potion_groups:
                            st.caption(_dq_potion_display(potion_groups[selected_use]["sample"]))
                    else:
                        st.caption("当前无可用药水。")

                with st.form("dq_battle_form"):
                    atype = st.session_state.get("dq_battle_action_type", "普攻")
                    if str(atype) == "使用药水":
                        atype = "药水"
                        st.session_state["dq_battle_action_type"] = "药水"
                    if str(atype) not in action_options:
                        atype = "普攻"
                    sid = None
                    item_id = None
                    item_target = "player"
                    target_id = None
                    defend_target = "player"
                    skill_catalog = {
                        "lianzhan": "连斩",
                        "heavy_strike": "援护",
                        "whirlwind": "旋风斩",
                        "deep_cut": "深割",
                        "armor_break": "盾反",
                        "blood_rage": "嗜血",
                        "execution": "战吼",
                    }
                    skill_mp_map: Dict[str, int] = {}
                    if hasattr(dq, "_skill_catalog"):
                        try:
                            _sc = dq._skill_catalog()
                            skill_mp_map = {str(k): int(getattr(v, "mp_cost", 0) or 0) for k, v in (_sc or {}).items()}
                        except Exception:
                            skill_mp_map = {}
                    player_skills = state.get("skills", [])
                    _have_ps = frozenset(s for s in player_skills if s in skill_catalog)
                    valid_skills = [s for s in _dq_hero_battle_skill_order if s in _have_ps]
                    valid_skills += sorted(s for s in _have_ps if s not in valid_skills)
                    preferred_sid = st.session_state.get("dq_selected_skill_id") or state.get("selected_skill_id")
                    sid_default = preferred_sid if preferred_sid in valid_skills else (valid_skills[0] if valid_skills else None)
                    enemy_target_opts: List[str] = []
                    enemy_target_to_eid: Dict[str, str] = {}
                    enemy_target_label: Dict[str, str] = {}
                    for i, e in enumerate(alive_enemies):
                        eid = str(e.get("eid") or f"idx_{i}")
                        opt = f"{i}|{eid}"
                        enemy_target_opts.append(opt)
                        enemy_target_to_eid[opt] = eid
                        enemy_target_label[opt] = f"{e.get('name', '敌人')}（Lv{int(e.get('level', 1) or 1)}）"

                    if atype == "技能":
                        sid = sid_default
                        if not sid:
                            st.warning("你还没有可用技能。升级或在战斗中成长后再来。")
                    elif atype == "药水":
                        if not potion_option_keys:
                            st.warning("背包中没有可战斗使用的药水（恢复/魔力/混合）。请探索、商店购买或去旅店/等待被动恢复后再战。")
                        else:
                            selected_use = st.session_state.get("dq_selected_potion_use")
                            grp = potion_groups.get(str(selected_use or ""))
                            if grp:
                                ids = [x for x in grp.get("ids", []) if x]
                                item_id = str(ids[0]) if ids else None
                            selected_use_for_target = str(selected_use or "")
                            item_target_opts = ["player"]
                            item_target_label = {"player": f"主角（{state.get('name', '勇者')}）"}
                            if selected_use_for_target == "revive_potion":
                                item_target_opts = []
                                item_target_label = {}
                                for al in (battle.get("allies", []) or []):
                                    if int(al.get("hp", 0) or 0) > 0:
                                        continue
                                    aid = str(al.get("aid") or al.get("mid") or "")
                                    if not aid:
                                        continue
                                    opt = f"ally:{aid}"
                                    item_target_opts.append(opt)
                                    item_target_label[opt] = f"倒地队友（{al.get('name', '队友')}）"
                                if not item_target_opts:
                                    st.warning("当前没有倒地队友，复活药水无法使用。")
                            else:
                                for al in (battle.get("allies", []) or []):
                                    if int(al.get("hp", 0) or 0) <= 0:
                                        continue
                                    aid = str(al.get("aid") or al.get("mid") or "")
                                    if not aid:
                                        continue
                                    opt = f"ally:{aid}"
                                    item_target_opts.append(opt)
                                    item_target_label[opt] = f"队友（{al.get('name', '队友')}）"
                            if not item_target_opts:
                                item_target_opts = ["player"]
                                item_target_label["player"] = f"主角（{state.get('name', '勇者')}）"
                            _it = st.radio(
                                "药水目标",
                                item_target_opts,
                                format_func=lambda x: item_target_label.get(str(x), str(x)),
                                key="dq_battle_item_target",
                                horizontal=True,
                            )
                            item_target = str(_it or "player")
                    elif atype == "防守":
                        defend_opts = ["player"]
                        defend_label = {"player": "守护自己（减伤65%）"}
                        for al in (battle.get("allies", []) or []):
                            if int(al.get("hp", 0) or 0) <= 0:
                                continue
                            aid = str(al.get("aid") or al.get("mid") or "")
                            if not aid:
                                continue
                            key = f"ally:{aid}"
                            defend_opts.append(key)
                            defend_label[key] = f"守护 {al.get('name', '队友')}（减伤45%，命中其时双方各承受减伤后的一半）"
                        chosen_def = st.radio(
                            "防守目标",
                            defend_opts,
                            format_func=lambda x: defend_label.get(str(x), str(x)),
                            key="dq_battle_defend_target",
                        )
                        defend_target = str(chosen_def or "player")

                    # 仅普攻/技能且敌人≥2 时显示目标；单敌人不显示选择框，直接锁定唯一 eid
                    if str(atype) in ("普攻", "技能") and enemy_target_opts:
                        if len(enemy_target_opts) > 1:
                            st.caption("多目标：本回合请选择要攻击的敌人。")
                            target_opt = st.radio(
                                "选择攻击目标",
                                enemy_target_opts,
                                format_func=lambda tid: enemy_target_label.get(str(tid), str(tid)),
                                key="dq_battle_target_pick",
                            )
                            target_id = enemy_target_to_eid.get(str(target_opt))
                        else:
                            target_id = enemy_target_to_eid.get(enemy_target_opts[0])

                    submitted = st.form_submit_button("✅ 执行动作", key="dq_battle_submit_btn")

            if submitted:
                action = None
                if atype == "普攻":
                    if len(alive_enemies) > 1 and not target_id:
                        st.error("多敌人时请先在「选择攻击目标」中指定要攻击的怪物。")
                        st.stop()
                    action = {"kind": "attack", "target_id": target_id}
                elif atype == "技能":
                    if not sid:
                        st.error("当前没有可用技能")
                        st.stop()
                    if len(alive_enemies) > 1 and not target_id:
                        st.error("多敌人时请先在「选择攻击目标」中指定目标。")
                        st.stop()
                    action = {"kind": "skill", "sid": sid, "target_id": target_id}
                elif atype == "防守":
                    action = {"kind": "defend", "defend_target": defend_target}
                elif atype == "药水":
                    if not item_id:
                        st.error("请先在背包中选择一瓶药水")
                        st.stop()
                    if str(st.session_state.get("dq_selected_potion_use") or "") == "revive_potion":
                        if not str(item_target).startswith("ally:"):
                            st.error("复活药水只能对倒地队友使用。")
                            st.stop()
                    action = {"kind": "item", "item_id": item_id, "item_target": item_target}
                elif atype == "逃跑":
                    action = {"kind": "flee"}

                st.session_state.dq_state = dq.dq_battle_action(state, action, _rng_for("battle"))
                if q1_battle_tut_active:
                    _qt = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                    if str(action.get("kind")) == "skill":
                        _qt["skill_try_count"] = int(_qt.get("skill_try_count", 0) or 0) + 1
                    else:
                        _qt["skill_try_count"] = int(_qt.get("skill_try_count", 0) or 0)
                    if str(st.session_state.dq_state.get("phase", "overworld")) == "battle":
                        _alive_after = (
                            (st.session_state.dq_state.get("battle") or {}).get("enemies")
                            or ([(st.session_state.dq_state.get("battle") or {}).get("enemy")]
                                if (st.session_state.dq_state.get("battle") or {}).get("enemy")
                                else [])
                        )
                        _slime_alive = any(
                            isinstance(e, dict)
                            and str(e.get("mid", "")) == "slime"
                            and int(e.get("hp", 0) or 0) > 0
                            for e in _alive_after
                        )
                        if _slime_alive and int(_qt.get("skill_try_count", 0) or 0) >= 3:
                            _qt["focus"] = "battle_attack"
                        else:
                            _qt["focus"] = "battle_log"
                    else:
                        _qt["active"] = True
                        # 胜利结算已设 drop_notice/backpack_tab；有掉落弹窗时切背包会叠开第二个 dialog
                        _q_notice = (st.session_state.dq_state.get("meta") or {}).get(
                            "pending_unlock_notice_queue"
                        ) or []
                        if not (isinstance(_q_notice, list) and _q_notice):
                            _qt["focus"] = "backpack_tab"
                            st.session_state["dq_force_tab_idx_once"] = 5
                        st.session_state.pop("dq_battle_focus_battle_tab_for_video", None)
                _m = st.session_state.dq_state.setdefault("meta", {})
                _m["battle_ui_last_action"] = str(atype)
                st.session_state["dq_battle_action_type"] = str(atype)
                _blog_after = (_m.get("battle_log") or [])
                _action_aborted = bool(dq.dq_battle_action_was_aborted(st.session_state.dq_state))
                if _action_aborted and _blog_after and "MP不足，无法执行行动" in str(_blog_after[-1]):
                    st.session_state["dq_mp_insufficient_notice"] = True
                if not _action_aborted:
                    _battle_after = st.session_state.dq_state.get("battle") or {}
                    _phase_after = str(st.session_state.dq_state.get("phase", "overworld") or "overworld")
                    # 若本次操作直接结束战斗，优先播放结算动画（胜利/失败）而非技能动作动画。
                    _submit_vid = _dq_battle_finish_video_path(st.session_state.dq_state) if _phase_after != "battle" else ""
                    if not _submit_vid:
                        _turn_stems = list(_battle_after.get("dq_turn_video_stems") or [])
                        _submit_vid = _dq_random_battle_video_from_stems(_turn_stems)
                    if not _submit_vid and action is not None:
                        _submit_vid = _dq_battle_video_path_after_submit(
                            st.session_state.dq_state,
                            str(atype),
                            skill_sid=sid,
                            skill_catalog=skill_catalog,
                            potion_groups=potion_groups,
                        )
                    if _submit_vid and os.path.isfile(_submit_vid) and st.session_state.get("dq_settings_battle_anim", True):
                        st.session_state["dq_battle_video_popup_path"] = _submit_vid
                        _q1_tut_now = (st.session_state.dq_state.get("meta") or {}).get("q1_post_act1_tutorial") or {}
                        _q1_skip_focus_battle = bool(
                            isinstance(_q1_tut_now, dict)
                            and str(_q1_tut_now.get("focus", "")) in ("backpack_tab", "equip_button", "equip_pick", "show_equipped")
                        )
                        if _phase_after != "battle" and not _q1_skip_focus_battle:
                            st.session_state["dq_battle_focus_battle_tab_for_video"] = True
                else:
                    st.session_state.pop("dq_battle_video_popup_path", None)
                _trim_log()
                st.rerun()

            # 战斗日志：与动作区同排
            with log_col:
                with st.container(key="dq_battle_log_focus_wrap"):
                    with st.expander("📜 战斗日志（当次详情·最新在上）", expanded=True):
                        meta = st.session_state.dq_state.get("meta", {})
                        blog = meta.get("battle_log", [])
                        st.markdown(
                            _dq_battle_log_html(blog, 220, max_height="320px"),
                            unsafe_allow_html=True,
                        )

    # ---------------- 任务/剧情 ----------------
    with tabs[2]:
        _q1_tut_task = (state.get("meta") or {}).get("q1_post_act1_tutorial") or {}
        _q1_task_active = bool(isinstance(_q1_tut_task, dict) and bool(_q1_tut_task.get("active")))
        _q1_task_focus = str((_q1_tut_task or {}).get("focus", ""))
        if _q1_task_active and _q1_task_focus in ("task_overview", "task_wait_finish"):
            st.markdown(
                """
<style>
.dq-task-tut-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.40);
  z-index: 99970;
  pointer-events: auto;
}
.st-key-dq_tutorial_task_list,
.st-key-dq_tutorial_to_adv_btn {
  position: relative;
  z-index: 100000;
}
.st-key-dq_tutorial_task_list {
  border: 3px solid #ef4444 !important;
  border-radius: 10px !important;
  box-shadow: 0 0 0 4px rgba(254,202,202,0.95), 0 0 18px rgba(239,68,68,0.45) !important;
}
.st-key-dq_tutorial_to_adv_btn > div[data-testid="stButton"] > button {
  border: 3px solid #ef4444 !important;
  box-shadow: 0 0 0 4px rgba(254,202,202,0.95), 0 0 18px rgba(239,68,68,0.45) !important;
  font-weight: 800 !important;
}
</style>
<div class="dq-task-tut-overlay" aria-hidden="true"></div>
""",
                unsafe_allow_html=True,
            )
            st.markdown(
                '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                "🎯 新手指引：此处查看主线任务和分支任务进度，下翻点击「继续冒险」按钮回到冒险。</div>",
                unsafe_allow_html=True,
            )
            st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})["focus"] = "task_wait_finish"
        with st.container(key="dq_tutorial_task_list"):
            st.markdown("### 任务列表")
            quest = state.get("quest", {})
            st.info(f"当前主线触发条件：{dq.dq_mainline_hint(state)}")
            quests = quest.get("quests", [])
            for q in quests:
                done = bool(q.get("done"))
                prog = int(q.get("progress", 0))
                need = int(q.get("need", 1))
                prefix = "✅" if done else "⬜"
                st.markdown(f"{prefix} **{q.get('title','任务')}**  {prog}/{need}")
                st.caption(q.get("desc", ""))
        if _q1_task_active and _q1_task_focus in ("task_overview", "task_wait_finish"):
            if st.button("➡️ 继续冒险", key="dq_tutorial_to_adv_btn", type="primary"):
                _qt_done = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                _qt_done["active"] = True
                _qt_done["focus"] = "adventure_rest"
                st.session_state["dq_force_tab_idx_once"] = 0
                st.rerun()
            components.html(
                """
<script>
setTimeout(() => {
  const task = window.parent.document.querySelector('.st-key-dq_tutorial_task_list');
  if (task) task.scrollIntoView({ behavior: 'smooth', block: 'center' });
  const btn = window.parent.document.querySelector('.st-key-dq_tutorial_to_adv_btn button');
  if (btn) btn.focus();
}, 80);
</script>
""",
                height=1,
                width=1,
                scrolling=False,
            )

        st.markdown("### 故事进度")
        clue_now = int(dq.dq_clue_count(state))
        need_q = int(getattr(dq, "CLUE_QUIZ_MIN_SCORE", 5) or 5)
        st.write(
            f"关键线索（唯一收集）：{clue_now}　"
            f"每条线索需在弹窗中三选一领悟（0/1/3 分）；**同图三条领悟总分 ≥ {need_q} 分**才激活该图地图特效。"
        )
        journal = dq.dq_clue_journal_status(state)
        if journal:
            for z in journal:
                zname = str(z.get("zone_name", z.get("zone_id", "区域")))
                fc = int(z.get("found_count", 0) or 0)
                tt = max(1, int(z.get("total", 1) or 1))
                qsum = int(z.get("quiz_zone_sum", 0) or 0)
                qmax = int(z.get("quiz_max_score", 9) or 9)
                qneed = int(z.get("quiz_need_score", need_q) or need_q)
                qall = bool(z.get("quiz_all_answered"))
                tag = "✅" if bool(z.get("effect_unlocked")) else "⬜"
                if bool(z.get("effect_unlocked")):
                    st.markdown(
                        f"""
<div style="display:inline-block; background:linear-gradient(90deg,#FFE58A,#FFD666); color:#5C3B00; border:1px solid #E6B800; border-radius:999px; padding:4px 10px; font-size:12px; font-weight:700; margin:2px 0 6px 0;">
  🏅 {zname} 已激活地图特效（{fc}/{tt}，领悟 {qsum}/{qmax} 分）
</div>
""",
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption(
                        f"{tag} {zname}：{fc}/{tt} 条线索｜"
                        f"本图领悟分 **{qsum}/{qmax}**（需 ≥{qneed} 且三条均作答）"
                        + ("" if qall else "｜尚有线索未作答")
                    )
                for c in (z.get("clues") or []):
                    found = bool(c.get("found"))
                    qs = c.get("quiz_score")
                    qs_note = ""
                    if found:
                        if c.get("quiz_answered"):
                            qs_note = f"　领悟：<b>{int(qs) if qs is not None else 0}</b> 分"
                        else:
                            qs_note = "　领悟：待弹窗作答"
                    bg = "#EAF8EE" if found else "#F5F6F7"
                    bd = "#7FCF9B" if found else "#D6D9DD"
                    icon = "✅" if found else "⬜"
                    st.markdown(
                        f"""
<div style="background:{bg}; border:1px solid {bd}; border-radius:10px; padding:8px 10px; margin:4px 0;">
  <div style="font-weight:600;">{icon} {c.get('title', '')}{qs_note}</div>
  <div style="font-size:12px; color:#4A5568;">{c.get('desc', '')}</div>
</div>
""",
                        unsafe_allow_html=True,
                    )
                if bool(z.get("effect_unlocked")):
                    st.caption(f"  🏁 已触发特效：{z.get('effect_title', '')}（{z.get('effect_desc', '')}）")
        flags = state.get("story_flags", {}).get("artifacts", {})
        st.markdown("### 主线圣物进度")
        relics = [
            ("守护印记", bool(flags.get("seal"))),
            ("灵矿之心", bool(flags.get("ore"))),
            ("潮汐之钥", bool(flags.get("key"))),
            ("勇者之章", bool(flags.get("chapter"))),
        ]
        r1, r2 = st.columns(2)
        for i, (name, ok) in enumerate(relics):
            bg = "#EAF8EE" if ok else "#F8F9FB"
            bd = "#7FCF9B" if ok else "#D6D9DD"
            fg = "#1F6F43" if ok else "#5F6B7A"
            icon = "✅" if ok else "🔒"
            txt = "已获得" if ok else "未获得"
            box = f"""
<div style="background:{bg}; border:1px solid {bd}; border-radius:12px; padding:10px 12px; margin:4px 0;">
  <div style="font-size:14px; font-weight:700; color:{fg};">{icon} {name}</div>
  <div style="font-size:12px; color:{fg}; margin-top:2px;">状态：{txt}</div>
</div>
"""
            with (r1 if i % 2 == 0 else r2):
                st.markdown(box, unsafe_allow_html=True)

    # ---------------- 天赋树 ----------------
    with tabs[3]:
        st.markdown("### 天赋树")
        meta = state.get("meta") or {}
        pending_talent = meta.get("pending_talent")
        cur_lv = int(state.get("level", 1) or 1)
        if isinstance(pending_talent, dict) and pending_talent.get("choices"):
            st.markdown(f"#### 待选择：{pending_talent.get('title', '选择天赋')}")
            st.caption("当角色达到 10/20/30 级时，会在这里出现可选天赋。")
            if pending_talent.get("target"):
                tgt = pending_talent["target"]
                st.caption(
                    f"目标：{'主角' if tgt.get('type') == 'player' else '队友'}"
                    f"（{pending_talent.get('role', '')}）"
                )
            choices = pending_talent.get("choices") or {}
            choice_ids = list(choices.keys())
            picked = None
            if choice_ids:
                picked = st.radio(
                    "你的选择",
                    choice_ids,
                    format_func=lambda cid: str(choices.get(cid, cid)),
                    key=f"dq_talent_pick_{pending_talent.get('level', 0)}_{pending_talent.get('role', '')}",
                )
            if picked and st.button("确定并继续", type="primary", key="dq_talent_pick_submit"):
                st.session_state.dq_state = dq.dq_resolve_talent_choice(state, picked)
                _trim_log()
                st.rerun()
        else:
            st.info("当前没有待选择天赋。达到 10/20/30 级后会在此显示。")

        # 预览：等级未到也可提前查看
        st.markdown("#### 天赋预览（未到等级仅预览，不可选择）")
        role_cn_map = getattr(dq, "ROLE_CN", {"warrior": "战士", "cleric": "牧师", "mage": "法师", "hunter": "猎人", "rogue": "刺客"})
        talent_defs = getattr(dq, "TALENT_CHOICE_DEFS", {})
        talent_levels = sorted(set(int(v.get("level", 0) or 0) for v in talent_defs.values()))

        preview_targets = [("player", str(state.get("role", "warrior")), str(state.get("name", "主角")), state.get("talent_picked") or {})]
        for mem in state.get("party_members", []) or []:
            preview_targets.append(
                (
                    "member",
                    str(mem.get("role", "")),
                    str(mem.get("name", "队友")),
                    mem.get("talent_picked") or {},
                )
            )

        for _, role, who_name, picked_map in preview_targets:
            if not role:
                continue
            st.markdown(f"**{who_name} · {role_cn_map.get(role, role)}**")
            for lv_need in talent_levels:
                cids = [k for k, v in talent_defs.items() if str(v.get("role", "")) == role and int(v.get("level", 0) or 0) == lv_need]
                if not cids:
                    continue
                picked_cid = str(picked_map.get(str(lv_need), "")) if isinstance(picked_map, dict) else ""
                if picked_cid in cids:
                    label = str(talent_defs.get(picked_cid, {}).get("label", picked_cid))
                    st.caption(f"✅ Lv{lv_need}：已选择「{label}」")
                else:
                    lock_tag = "（可选）" if cur_lv >= lv_need else f"（Lv{lv_need} 解锁）"
                    labels = " / ".join([str(talent_defs.get(cid, {}).get("label", cid)) for cid in cids])
                    st.caption(f"⬜ Lv{lv_need}{lock_tag}：{labels}")

    # ---------------- 商店 ----------------
    with tabs[4]:
        if phase == "battle":
            st.warning("战斗中无法购物。")
        else:
            shop_err = st.session_state.pop("dq_shop_err", None)
            shop_ok = st.session_state.pop("dq_shop_ok", None)
            if shop_err:
                st.warning(shop_err)
            if shop_ok:
                st.success(shop_ok)
            st.markdown("### 村庄杂货")
            st.caption(
                "购买基础药水与制式装备（普通品质，副属性随机）。**商店装备与职业武器的主属性**＝"
                "购买瞬间的主角等级 ÷3 向下取整，写入物品后**不随升级变化**；**副属性额外**＝"
                "当前地牢记录层数 ÷4 向下取整（未推进无限地牢时多为 0）。"
                "掉落装备品质：普通→精良→史诗→传说；饰品额外可能为至尊（掉率极低）。"
                "掉落装备主属性按等级 ÷3 缩放，副属性额外加地牢层 ÷4。"
            )
            inv_max = int(getattr(dq, "INVENTORY_MAX_SLOTS", 48))
            used = dq.dq_inventory_slots_used(state)
            st.metric("背包格子占用", f"{used} / {inv_max}")
            catalog = dq.dq_shop_catalog()
            hero_lv_shop = max(1, int(state.get("level", 1) or 1))
            dungeon_floor_shop = max(1, int((state.get("dungeon") or {}).get("floor", 1) or 1))
            shop_main_preview = (
                int(dq.dq_shop_main_val_at_purchase(hero_lv_shop))
                if hasattr(dq, "dq_shop_main_val_at_purchase")
                else hero_lv_shop // 3
            )
            shop_sub_floor_preview = (
                int(dq.dq_shop_sub_bonus_from_dungeon_floor(dungeon_floor_shop))
                if hasattr(dq, "dq_shop_sub_bonus_from_dungeon_floor")
                else max(0, dungeon_floor_shop // 4)
            )
            for row in catalog:
                c1, c2, c3 = st.columns([3, 1, 1])
                with c1:
                    extra = ""
                    if row.get("kind") == "potion":
                        pu = row.get("potion_use", "heal_potion")
                        ph = getattr(dq, "POTION_HP_PCT", 35)
                        pm = getattr(dq, "POTION_MP_PCT", 30)
                        dh = getattr(dq, "POTION_DUAL_HP_PCT", 25)
                        dm = getattr(dq, "POTION_DUAL_MP_PCT", 20)
                        if pu == "heal_potion":
                            extra = f"（最大HP×{ph}%）"
                        elif pu == "mp_potion":
                            extra = f"（最大MP×{pm}%）"
                        elif pu == "dual_potion":
                            extra = f"（最大HP×{dh}% + 最大MP×{dm}%）"
                    elif row.get("kind") == "party_weapon":
                        role_cn = {"warrior": "战士", "cleric": "牧师", "mage": "法师", "hunter": "猎人", "rogue": "盗贼"}
                        role_main_lab = {
                            "warrior": "力量",
                            "cleric": "智慧",
                            "mage": "智慧",
                            "hunter": "精准",
                            "rogue": "敏捷",
                        }
                        role = str(row.get("role", ""))
                        mk = role_main_lab.get(role, "主属性")
                        bonus_parts = []
                        if float(row.get("atk_bonus", 0.0) or 0.0) > 0:
                            bonus_parts.append(f"攻击+{int(float(row.get('atk_bonus', 0.0) or 0.0)*100)}%")
                        if float(row.get("spell_bonus", 0.0) or 0.0) > 0:
                            bonus_parts.append(f"法伤+{int(float(row.get('spell_bonus', 0.0) or 0.0)*100)}%")
                        if float(row.get("heal_bonus", 0.0) or 0.0) > 0:
                            bonus_parts.append(f"治疗+{int(float(row.get('heal_bonus', 0.0) or 0.0)*100)}%")
                        bp = ("；" + "，".join(bonus_parts)) if bonus_parts else ""
                        _pw_sub_total = 1 + shop_sub_floor_preview
                        extra = (
                            f"（{role_cn.get(role, role)}专属：{mk}+{shop_main_preview}（Lv{hero_lv_shop}÷3）{bp}；"
                            f"副词条种类随机，副属数值＝1＋（地牢{dungeon_floor_shop}层÷4）＝{_pw_sub_total}）"
                        )
                    elif row.get("kind") == "equip":
                        slot = str(row.get("slot", ""))
                        slot_lab = dq.SLOT_CN.get(slot, slot)
                        main_attr = dq.SLOT_MAIN_ATTR.get(slot, "")
                        if main_attr:
                            ma_disp = str(main_attr).upper()
                            extra = (
                                f"（{slot_lab}：主属性{ma_disp}+{shop_main_preview}"
                                f"（Lv÷3）；副词条随机（1～3）并加地牢{dungeon_floor_shop}层÷4＝+{shop_sub_floor_preview}）"
                            )
                        else:
                            extra = f"（{slot_lab}：属性副词条随机）"
                    elif row.get("kind") == "respec_orb":
                        extra = "（使用后选择主角或队友，重置六维并返还已分配能力点）"
                    elif row.get("kind") == "talent_respec_orb":
                        extra = "（使用后选择主角或队友，重置已选天赋并重新进行 Lv10/20/30 二选一）"
                    st.markdown(f"**{row['name']}**{extra} — **{row['price']}** 金")
                with c3:
                    if st.button("购买", key=f"dq_buy_{row['key']}"):
                        price = int(row.get("price", 0) or 0)
                        gold_now = int(state.get("gold", 0) or 0)
                        if gold_now < price:
                            st.session_state["dq_shop_err"] = (
                                f"钱不够，无法购买（{row.get('name', '物品')} 需 {price} 金币，当前 {gold_now}）。"
                            )
                        else:
                            st.session_state.dq_state = dq.dq_buy(state, row["key"], _rng_for(f"shop_{row['key']}"))
                            st.session_state.pop("dq_shop_err", None)
                            st.session_state["dq_shop_ok"] = f"购买成功：{row.get('name', '物品')} ×1"
                            _trim_log()
                        st.rerun()

            with st.expander("饰品特殊能力说明", expanded=False):
                for k, v in getattr(dq, "ACCESSORY_SPECIALS", {}).items():
                    st.markdown(f"**{v.get('name', k)}**：{v.get('desc', '')}")

            with st.expander("技能说明书大全", expanded=False):
                if hasattr(dq, "dq_skill_manual_sections"):
                    _sections = dq.dq_skill_manual_sections()
                    if not _sections:
                        st.caption("暂无技能说明。")
                    else:
                        for _role_title, _pairs in _sections:
                            st.markdown(f"#### {_role_title}")
                            for sid, desc in _pairs:
                                sname = _dq_skill_labels.get(str(sid), str(sid))
                                st.markdown(f"**{sname}**（`{sid}`）：{desc}")
                else:
                    skill_desc_map = dq.dq_skill_descriptions() if hasattr(dq, "dq_skill_descriptions") else {}
                    if not skill_desc_map:
                        st.caption("暂无技能说明。")
                    else:
                        _pairs = sorted(
                            skill_desc_map.items(),
                            key=lambda kv: _dq_skill_labels.get(str(kv[0]), str(kv[0])),
                        )
                        for sid, desc in _pairs:
                            sname = _dq_skill_labels.get(str(sid), str(sid))
                            st.markdown(f"**{sname}**（`{sid}`）：{desc}")

    # ---------------- 背包/装备 ----------------
    with tabs[5]:
        _q1_tut_bag = (state.get("meta") or {}).get("q1_post_act1_tutorial") or {}
        _q1_bag_active = bool(isinstance(_q1_tut_bag, dict) and bool(_q1_tut_bag.get("active")))
        _q1_bag_focus = str((_q1_tut_bag or {}).get("focus", ""))
        _q1_bag_focus_effective = _q1_bag_focus
        if _q1_bag_active and _q1_bag_focus == "backpack_tab":
            # 首次进入背包即直接进入「装备按钮高亮」态，避免用户看到“已切页但未高亮”
            st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})["focus"] = "equip_button"
            _q1_bag_focus_effective = "equip_button"
        _q1_target_equip_id = str((_q1_tut_bag or {}).get("target_equip_item_id", "") or "")
        if _q1_bag_active and _q1_bag_focus_effective in ("equip_button", "equip_pick", "show_equipped"):
            _bag_focus_css = ""
            _bag_focus_extra_css = ""
            if _q1_bag_focus_effective == "equip_button":
                _bag_focus_css = ".st-key-dq_tutorial_equip_pick_btn > div[data-testid='stButton'] > button"
            elif _q1_bag_focus_effective == "show_equipped":
                _bag_focus_css = ".st-key-dq_tutorial_equipped_block"
                _bag_focus_extra_css = """
.st-key-dq_tutorial_equipped_block {
  background: #ffffff !important;
  border-radius: 10px !important;
  padding: 8px !important;
}
"""
            elif _q1_bag_focus_effective == "equip_pick":
                _bag_focus_css = "div[data-testid='stDialog'], .st-key-dq_tutorial_equip_pick_panel"
            st.markdown(
                f"""
<style>
.dq-q1-bag-overlay {{
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.40);
  z-index: 99970;
  pointer-events: none;
}}
.st-key-dq_tutorial_equip_pick_btn,
.st-key-dq_tutorial_equipped_panel {{
  position: relative;
  z-index: 100000;
}}
{_bag_focus_css} {{
  border: 3px solid #ef4444 !important;
  border-radius: 10px !important;
  box-shadow: 0 0 0 4px rgba(254, 202, 202, 0.95), 0 0 18px rgba(239, 68, 68, 0.45) !important;
}}
{_bag_focus_extra_css}
</style>
<div class="dq-q1-bag-overlay" aria-hidden="true"></div>
""",
                unsafe_allow_html=True,
            )
            if _q1_bag_focus_effective == "equip_button":
                st.markdown(
                    '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                    'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                    "🎯 新手指引：请滚轮下滑找到这件装备，点击这件战利品的「装备」按钮。</div>",
                    unsafe_allow_html=True,
                )
            elif _q1_bag_focus_effective == "equip_pick":
                st.markdown(
                    '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                    'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                    "🎯 新手指引：在弹窗里选择穿戴对象并确认，可看到穿戴后的变化。</div>",
                    unsafe_allow_html=True,
                )
            elif _q1_bag_focus_effective == "show_equipped":
                st.markdown(
                    """
<style>
.st-key-dq_tutorial_to_task_btn {
  position: relative;
  z-index: 100000;
}
.st-key-dq_tutorial_to_task_btn > div[data-testid="stButton"] > button {
  border: 3px solid #ef4444 !important;
  box-shadow: 0 0 0 4px rgba(254, 202, 202, 0.95), 0 0 18px rgba(239, 68, 68, 0.45) !important;
  font-weight: 800 !important;
}
</style>
<div id="dq-tutorial-next-btn-anchor"></div>
""",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    '<div style="border:3px solid #ef4444;border-radius:10px;padding:8px 10px;'
                    'background:#fff1f2;color:#7f1d1d;font-weight:700;margin-bottom:8px;position:relative;z-index:100000;">'
                    "🎯 新手指引：滚轮下滑可在「装备穿戴」中查看穿戴后的效果。点击下方按钮继续到「任务/剧情」。</div>",
                    unsafe_allow_html=True,
                )
                components.html(
                    """
<script>
setTimeout(() => {
  const anchor = window.parent.document.querySelector('#dq-tutorial-next-btn-anchor');
  if (anchor) {
    anchor.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
  const btn = window.parent.document.querySelector('.st-key-dq_tutorial_to_task_btn button');
  if (btn) {
    btn.focus();
  }
}, 100);
</script>
""",
                    height=1,
                    width=1,
                    scrolling=False,
                )
                if st.button("➡️ 继续（前往任务/剧情）", key="dq_tutorial_to_task_btn", type="primary"):
                    _qt_next = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                    _qt_next["focus"] = "task_overview"
                    st.session_state["dq_force_tab_idx_once"] = 2
                    st.rerun()
        st.markdown("### 物品与材料")
        st.caption(
            "背包为固定格子数；五种区域材料（草药、瘴气孢子、灵矿、海盐晶、王座残铁）占用格子，与药水、装备相同。满格时新掉落无法拾取。"
        )

        inv_max = int(getattr(dq, "INVENTORY_MAX_SLOTS", 48))
        used = dq.dq_inventory_slots_used(state)
        st.metric("背包格子", f"{used} / {inv_max}")
        inv = state.get("inventory", [])

        st.markdown("#### 背包格子（可视化）")
        slot_cells = dq.dq_inventory_slot_cells(state, inv_max)
        for row in range(6):
            cols = st.columns(8)
            for c in range(8):
                idx = row * 8 + c
                with cols[c]:
                    lab = slot_cells[idx] if idx < len(slot_cells) else None
                    if lab:
                        st.caption(lab)
                    else:
                        st.caption("—")

        _pu = getattr(
            dq,
            "BATTLE_POTION_USES",
            frozenset({"heal_potion", "mp_potion", "dual_potion", "full_heal_potion", "full_mp_potion", "golden_apple"}),
        )
        potions = [it for it in inv if (it.get("meta", {}) or {}).get("use") in _pu and int(it.get("qty", 0)) > 0]
        mat_items = [it for it in inv if (it.get("meta", {}) or {}).get("kind") == "material" and int(it.get("qty", 0)) > 0]
        utility_items = [
            it
            for it in inv
            if (it.get("meta", {}) or {}).get("kind") in ("respec_orb", "talent_respec_orb")
            and int(it.get("qty", 0)) > 0
        ]
        eq_slots = tuple(getattr(dq, "EQUIPMENT_SLOTS", ("weapon", "shield", "helmet", "mail", "belt", "accessory")))
        slot_cn = getattr(dq, "SLOT_CN", {})
        equips = [it for it in inv if (it.get("meta", {}) or {}).get("slot") in eq_slots and int(it.get("qty", 0)) > 0]
        if _q1_bag_active and _q1_bag_focus_effective in ("equip_button",) and not _q1_target_equip_id and equips:
            _q1_target_equip_id = str(equips[0].get("item_id", "") or "")
            st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})[
                "target_equip_item_id"
            ] = _q1_target_equip_id

        st.markdown("#### 药水 / 材料 / 功能道具")
        c_pot, c_mat, c_util = st.columns(3)
        with c_pot:
            _dq_inv_category_badge("药水", "pot")
            if potions:
                potion_groups: Dict[str, Dict[str, Any]] = {}
                for it in potions:
                    meta = it.get("meta") or {}
                    use_key = str(meta.get("use") or "")
                    if use_key not in potion_groups:
                        potion_groups[use_key] = {"items": [], "name": str(it.get("name", "药水")), "qty": 0, "meta": meta}
                    potion_groups[use_key]["items"].append(it)
                    potion_groups[use_key]["qty"] += int(it.get("qty", 0) or 0)

                order = ["heal_potion", "mp_potion", "dual_potion", "full_heal_potion", "full_mp_potion", "golden_apple", "revive_potion"]
                for use_key in [k for k in order if k in potion_groups] + [k for k in potion_groups if k not in order]:
                    grp = potion_groups[use_key]
                    gname = grp["name"]
                    gqty = int(grp["qty"] or 0)
                    gmeta = grp["meta"] or {}
                    raw_sp = int(gmeta.get("sell_price") or getattr(dq, "POTION_UNIT_SELL_PRICE", {}).get(use_key, 0))
                    sp = max(1, int(raw_sp * float(getattr(dq, "SELL_PRICE_RATIO", 0.20))))
                    r1, r2, r3 = st.columns([4, 1, 1])
                    with r1:
                        st.write(f"{gname} ×{gqty}　回收 **{sp}** 金/个")
                    with r2:
                        if st.button("卖1", key=f"dq_sell1_pot_grp_{use_key}"):
                            sid = None
                            for pit in grp["items"]:
                                if int(pit.get("qty", 0) or 0) > 0:
                                    sid = pit.get("item_id")
                                    break
                            if sid:
                                st.session_state.dq_state = dq.dq_sell_item(state, sid, 1)
                                _trim_log()
                            st.rerun()
                    with r3:
                        if st.button("全卖", key=f"dq_sellall_pot_grp_{use_key}"):
                            new_state = state
                            for pit in list(grp["items"]):
                                pid = pit.get("item_id")
                                if pid:
                                    new_state = dq.dq_sell_item(new_state, pid)
                            st.session_state.dq_state = new_state
                            _trim_log()
                            st.rerun()
            else:
                _dq_inv_empty_hint("暂无药水")

        with c_mat:
            _dq_inv_category_badge("材料", "mat")
            if mat_items:
                _mat_prices = getattr(dq, "MATERIAL_UNIT_SELL_PRICE", {})
                for it in mat_items[:40]:
                    meta = it.get("meta") or {}
                    mn = meta.get("material_name", "?")
                    raw_sp = int(meta.get("sell_price") or _mat_prices.get(mn, 0))
                    sp = max(1, int(raw_sp * float(getattr(dq, "SELL_PRICE_RATIO", 0.20))))
                    r1, r2, r3 = st.columns([4, 1, 1])
                    with r1:
                        st.write(f"{it.get('name')} ×{it.get('qty')}　回收 **{sp}** 金/个")
                    with r2:
                        if st.button("卖1", key=f"dq_sell1_mat_{it['item_id']}"):
                            st.session_state.dq_state = dq.dq_sell_item(state, it["item_id"], 1)
                            _trim_log()
                            st.rerun()
                    with r3:
                        if st.button("全卖", key=f"dq_sellall_mat_{it['item_id']}"):
                            st.session_state.dq_state = dq.dq_sell_item(state, it["item_id"])
                            _trim_log()
                            st.rerun()
            else:
                _dq_inv_empty_hint("暂无材料")

        with c_util:
            _dq_inv_category_badge("功能道具", "util")
            if utility_items:
                for it in utility_items[:20]:
                    _uk = str((it.get("meta", {}) or {}).get("kind", "") or "")
                    rr1, rr2 = st.columns([4, 1])
                    with rr1:
                        if _uk == "talent_respec_orb":
                            st.write(
                                f"{it.get('name', '功能道具')} ×{int(it.get('qty', 0) or 0)}"
                                "（清空已选天赋，按当前等级重新选择 Lv10/20/30）"
                            )
                        else:
                            st.write(
                                f"{it.get('name', '功能道具')} ×{int(it.get('qty', 0) or 0)}"
                                "（使用时可选择主角或队友，重置加点并返还能力点）"
                            )
                    with rr2:
                        if _uk == "talent_respec_orb":
                            if st.button("使用", key=f"dq_use_talent_orb_{it['item_id']}"):
                                st.session_state["dq_talent_orb_pick_prompt"] = True
                                st.session_state["dq_talent_orb_pick_item_id"] = str(it.get("item_id", "") or "")
                                st.rerun()
                        else:
                            if st.button("使用", key=f"dq_use_respec_{it['item_id']}"):
                                st.session_state["dq_respec_pick_prompt"] = True
                                st.session_state["dq_respec_pick_item_id"] = str(it.get("item_id", "") or "")
                                st.rerun()

            if st.session_state.get("dq_talent_orb_pick_prompt"):
                pick_item_id = str(st.session_state.get("dq_talent_orb_pick_item_id", "") or "")
                pick_item = next(
                    (
                        x
                        for x in utility_items
                        if str(x.get("item_id", "")) == pick_item_id
                        and (x.get("meta", {}) or {}).get("kind") == "talent_respec_orb"
                    ),
                    None,
                )
                pm_talent = state.get("party_members", []) or []
                role_cn_talent = {
                    "warrior": "战士",
                    "cleric": "牧师",
                    "mage": "法师",
                    "hunter": "猎人",
                    "rogue": "刺客",
                }
                wearer_opts_t = ["hero"] + [str(m.get("mid", "")) for m in pm_talent if str(m.get("mid", ""))]
                wearer_labels_t = {"hero": f"{state.get('name', '主角')}（主角）"}
                for m in pm_talent:
                    mid = str(m.get("mid", ""))
                    if mid:
                        wearer_labels_t[mid] = (
                            f"{m.get('name', '队友')}（"
                            f"{role_cn_talent.get(str(m.get('role', '')), str(m.get('role', '')))}）"
                        )
                if pick_item:
                    if dlg:

                        @dlg("天赋宝珠")
                        def _dq_talent_orb_pick_dialog():
                            st.markdown(
                                "将清空该角色**已选择的全部天赋**，并按当前等级重新排队 **Lv10 / Lv20 / Lv30** 的天赋二选一（消耗宝珠 ×1）。"
                            )
                            st.caption(f"道具：{pick_item.get('name', '天赋宝珠')}")
                            who = st.selectbox(
                                "重置天赋对象",
                                wearer_opts_t,
                                format_func=lambda x: wearer_labels_t.get(str(x), str(x)),
                                key=f"dq_talent_orb_pick_target_{pick_item_id}",
                            )
                            c1, c2, c3 = st.columns([1, 1, 1])
                            with c2:
                                if st.button("确认使用", type="primary", key=f"dq_talent_orb_confirm_{pick_item_id}"):
                                    tgt = "hero" if str(who) == "hero" else str(who)
                                    st.session_state.dq_state = dq.dq_use_talent_respec_orb(
                                        state, pick_item_id, tgt
                                    )
                                    st.session_state["dq_talent_orb_pick_prompt"] = False
                                    st.session_state["dq_talent_orb_pick_item_id"] = ""
                                    _trim_log()
                                    st.rerun()
                            with c3:
                                if st.button("取消", key=f"dq_talent_orb_cancel_{pick_item_id}"):
                                    st.session_state["dq_talent_orb_pick_prompt"] = False
                                    st.session_state["dq_talent_orb_pick_item_id"] = ""
                                    st.rerun()

                        _dq_talent_orb_pick_dialog()
                    else:
                        st.info("请选择对象后确认。")
                        who = st.selectbox(
                            "重置天赋对象",
                            wearer_opts_t,
                            format_func=lambda x: wearer_labels_t.get(str(x), str(x)),
                            key=f"dq_talent_orb_pick_target_inline_{pick_item_id}",
                        )
                        ic1, ic2 = st.columns(2)
                        with ic1:
                            if st.button("确认使用", type="primary", key=f"dq_talent_orb_confirm_inline_{pick_item_id}"):
                                tgt = "hero" if str(who) == "hero" else str(who)
                                st.session_state.dq_state = dq.dq_use_talent_respec_orb(state, pick_item_id, tgt)
                                st.session_state["dq_talent_orb_pick_prompt"] = False
                                st.session_state["dq_talent_orb_pick_item_id"] = ""
                                _trim_log()
                                st.rerun()
                        with ic2:
                            if st.button("取消", key=f"dq_talent_orb_cancel_inline_{pick_item_id}"):
                                st.session_state["dq_talent_orb_pick_prompt"] = False
                                st.session_state["dq_talent_orb_pick_item_id"] = ""
                                st.rerun()
                else:
                    st.session_state["dq_talent_orb_pick_prompt"] = False
                    st.session_state["dq_talent_orb_pick_item_id"] = ""

            if st.session_state.get("dq_respec_pick_prompt"):
                pick_item_id = str(st.session_state.get("dq_respec_pick_item_id", "") or "")
                pick_item = next(
                    (
                        x
                        for x in utility_items
                        if str(x.get("item_id", "")) == pick_item_id
                        and (x.get("meta", {}) or {}).get("kind") == "respec_orb"
                    ),
                    None,
                )
                pm_respec = state.get("party_members", []) or []
                role_cn_respec = {
                    "warrior": "战士",
                    "cleric": "牧师",
                    "mage": "法师",
                    "hunter": "猎人",
                    "rogue": "刺客",
                }
                wearer_opts_r = ["hero"] + [str(m.get("mid", "")) for m in pm_respec if str(m.get("mid", ""))]
                wearer_labels_r = {"hero": f"{state.get('name', '主角')}（主角）"}
                for m in pm_respec:
                    mid = str(m.get("mid", ""))
                    if mid:
                        wearer_labels_r[mid] = (
                            f"{m.get('name', '队友')}（"
                            f"{role_cn_respec.get(str(m.get('role', '')), str(m.get('role', '')))}）"
                        )
                if pick_item:
                    if dlg:

                        @dlg("角色属性重新分配宝珠")
                        def _dq_respec_pick_dialog():
                            st.markdown("将对象六维重置为 **1**，已投入点数全部返还到待分配，并 **回满 HP/MP**（消耗宝珠 ×1）。")
                            st.caption(f"道具：{pick_item.get('name', '宝珠')}")
                            who = st.selectbox(
                                "重置对象",
                                wearer_opts_r,
                                format_func=lambda x: wearer_labels_r.get(str(x), str(x)),
                                key=f"dq_respec_pick_target_{pick_item_id}",
                            )
                            c1, c2, c3 = st.columns([1, 1, 1])
                            with c2:
                                if st.button("确认使用", type="primary", key=f"dq_respec_confirm_{pick_item_id}"):
                                    tgt = "hero" if str(who) == "hero" else str(who)
                                    st.session_state.dq_state = dq.dq_use_respec_orb(
                                        state, pick_item_id, tgt
                                    )
                                    st.session_state["dq_respec_pick_prompt"] = False
                                    st.session_state["dq_respec_pick_item_id"] = ""
                                    _trim_log()
                                    st.rerun()
                            with c3:
                                if st.button("取消", key=f"dq_respec_cancel_{pick_item_id}"):
                                    st.session_state["dq_respec_pick_prompt"] = False
                                    st.session_state["dq_respec_pick_item_id"] = ""
                                    st.rerun()

                        _dq_respec_pick_dialog()
                    else:
                        st.info("请选择重置对象后确认。")
                        who = st.selectbox(
                            "重置对象",
                            wearer_opts_r,
                            format_func=lambda x: wearer_labels_r.get(str(x), str(x)),
                            key=f"dq_respec_pick_target_inline_{pick_item_id}",
                        )
                        ic1, ic2 = st.columns(2)
                        with ic1:
                            if st.button("确认使用", type="primary", key=f"dq_respec_confirm_inline_{pick_item_id}"):
                                tgt = "hero" if str(who) == "hero" else str(who)
                                st.session_state.dq_state = dq.dq_use_respec_orb(state, pick_item_id, tgt)
                                st.session_state["dq_respec_pick_prompt"] = False
                                st.session_state["dq_respec_pick_item_id"] = ""
                                _trim_log()
                                st.rerun()
                        with ic2:
                            if st.button("取消", key=f"dq_respec_cancel_inline_{pick_item_id}"):
                                st.session_state["dq_respec_pick_prompt"] = False
                                st.session_state["dq_respec_pick_item_id"] = ""
                                st.rerun()
                else:
                    st.session_state["dq_respec_pick_prompt"] = False
                    st.session_state["dq_respec_pick_item_id"] = ""
            if not utility_items:
                _dq_inv_empty_hint("暂无功能道具")

        # 装备穿戴：主角与队友统一展示（全槽位；每行最多 3 人）
        with st.container(key="dq_tutorial_equipped_panel"):
            st.markdown("#### 装备穿戴")
        with st.container(key="dq_tutorial_equipped_data_wrap"):
            role_cn = {"warrior": "战士", "cleric": "牧师", "mage": "法师", "hunter": "猎人", "rogue": "刺客"}
            party_members = state.get("party_members", []) or []
        def _equip_brief(it: Dict[str, Any]) -> str:
            meta = (it or {}).get("meta", {}) or {}
            bits: List[str] = []
            mk = str(meta.get("main_attr", "") or "")
            mv = int(meta.get("main_val", 0) or 0)
            if mk and mv:
                bits.append(f"{mk.upper()}+{mv}")
            sk = str(meta.get("sub_attr", "") or "")
            sv = int(meta.get("sub_val", 0) or 0)
            if sk and sv:
                bits.append(f"{sk.upper()}+{sv}")
            for k, nm in (("atk_bonus", "攻击力"), ("spell_bonus", "法伤"), ("heal_bonus", "治疗")):
                pv = float(meta.get(k, 0.0) or 0.0)
                if pv > 0:
                    bits.append(f"{nm}+{int(round(pv * 100))}%")
            # 与 dq_format_equipment_item 一致：攻击/闪避/免伤/暴击等百分比词条
            for k, nm in (
                ("atk_pct", "攻击加成"),
                ("eva_bonus", "闪避加成"),
                ("mit_bonus", "免伤加成"),
                ("crit_bonus", "暴击加成"),
                ("hit_bonus", "命中加成"),
            ):
                pv = float(meta.get(k, 0.0) or 0.0)
                if pv > 0:
                    bits.append(f"{nm}+{int(round(pv * 100))}%")
            _acc_spec = getattr(dq, "ACCESSORY_SPECIALS", {}) or {}
            _sids = meta.get("special_ids")
            if isinstance(_sids, list) and _sids:
                for _sid in _sids:
                    sp = _acc_spec.get(str(_sid))
                    if isinstance(sp, dict) and sp.get("name"):
                        bits.append(str(sp["name"]))
            else:
                _sid_one = meta.get("special_id")
                if _sid_one:
                    sp = _acc_spec.get(str(_sid_one))
                    if isinstance(sp, dict) and sp.get("name"):
                        bits.append(str(sp["name"]))
            if not bits:
                return "—"
            return " ｜ ".join(bits)
        wearers: List[Dict[str, Any]] = [
            {
                "kind": "hero",
                "id": "hero",
                "name": str(state.get("name", "主角")),
                "role": str(state.get("role", "warrior")),
                "equipped": state.get("equipped") or {},
            }
        ]
        for mem in party_members:
            wearers.append(
                {
                    "kind": "member",
                    "id": str(mem.get("mid", "")),
                    "name": str(mem.get("name", "队友")),
                    "role": str(mem.get("role", "")),
                    "equipped": mem.get("equipped") or {},
                }
            )
        with st.container(key="dq_tutorial_equipped_block"):
            for _wi in range(0, len(wearers), 3):
                _wchunk = wearers[_wi : _wi + 3]
                _wcols = st.columns(3)
                for _ci, w in enumerate(_wchunk):
                    with _wcols[_ci]:
                        w_name = w.get("name", "角色")
                        w_role = role_cn.get(str(w.get("role", "")), str(w.get("role", "")))
                        with st.expander(
                            f"{w_name}（{w_role}）",
                            expanded=bool(_q1_bag_active and _q1_bag_focus in ("equip_pick", "show_equipped")),
                        ):
                            for sid in eq_slots:
                                lab = slot_cn.get(sid, sid)
                                cur = (w.get("equipped") or {}).get(sid)
                                cur_name = cur.get("name", "—") if isinstance(cur, dict) else "—"
                                c1, c2 = st.columns([4, 1])
                                with c1:
                                    if isinstance(cur, dict) and cur_name != "—":
                                        _em = cur.get("meta") or {}
                                        _bg, _fg, _bd = _dq_equipment_quality_colors(_em)
                                        _safe_nm = html_escape.escape(str(cur_name))
                                        st.markdown(
                                            f"**{lab}**：<span style=\"display:inline-block;background:{_bg};color:{_fg};"
                                            f"border:1px solid {_bd};border-radius:8px;padding:2px 10px;font-weight:700;\">"
                                            f"{_safe_nm}</span>",
                                            unsafe_allow_html=True,
                                        )
                                    else:
                                        st.markdown(f"**{lab}**：{cur_name}")
                                    if cur:
                                        st.caption(_equip_brief(cur))
                                with c2:
                                    if cur:
                                        if w.get("kind") == "hero":
                                            if st.button(
                                                f"卸下",
                                                key=f"dq_unequip_hero_{sid}_{_wi}_{_ci}",
                                            ):
                                                st.session_state.dq_state = dq.dq_unequip_slot(state, sid)
                                                _trim_log()
                                                st.rerun()
                                        else:
                                            if st.button(
                                                f"卸下",
                                                key=f"dq_unequip_member_{w.get('id')}_{sid}_{_wi}_{_ci}",
                                            ):
                                                st.session_state.dq_state = dq.dq_member_unequip_slot(
                                                    state, str(w.get("id", "")), sid
                                                )
                                                _trim_log()
                                                st.rerun()

        st.markdown("#### 背包装备（可穿上 / 出售）")
        _eq_err_msg = st.session_state.pop("dq_equip_err_msg", None)
        if _eq_err_msg:
            st.error(str(_eq_err_msg))
        if equips:
            with st.container(key="dq_tutorial_equip_pick_panel"):
                if st.session_state.get("dq_equip_pick_prompt") and not dq.dq_has_blocking_modal_notice(state):
                    pick_item_id = str(st.session_state.get("dq_equip_pick_item_id", "") or "")
                    pick_item = next((x for x in equips if str(x.get("item_id", "")) == pick_item_id), None)
                    if pick_item:
                        wearer_opts = ["hero"] + [str(m.get("mid", "")) for m in party_members if str(m.get("mid", ""))]
                        wearer_labels = {"hero": f"{state.get('name', '主角')}（主角）"}
                        for m in party_members:
                            mid = str(m.get("mid", ""))
                            if mid:
                                wearer_labels[mid] = f"{m.get('name', '队友')}（{role_cn.get(str(m.get('role', '')), str(m.get('role', '')))}）"
                        if dlg:
                            @dlg("装备")
                            def _dq_pick_equip_target_dialog():
                                _pm = pick_item.get("meta") or {}
                                _bgp, _fgp, _bdp = _dq_equipment_quality_colors(_pm)
                                _np = html_escape.escape(str(pick_item.get("name", "装备")))
                                st.markdown(
                                    f"请选择穿戴对象：<span style=\"display:inline-block;background:{_bgp};color:{_fgp};"
                                    f"border:1px solid {_bdp};border-radius:8px;padding:2px 10px;font-weight:700;\">"
                                    f"{_np}</span>",
                                    unsafe_allow_html=True,
                                )
                                who = st.radio(
                                    "人物",
                                    wearer_opts,
                                    format_func=lambda x: wearer_labels.get(str(x), str(x)),
                                    key=f"dq_equip_pick_target_{pick_item_id}",
                                    horizontal=True,
                                )
                                c1, c2, c3 = st.columns([1, 1, 1])
                                with c2:
                                    if st.button("确认", type="primary", key=f"dq_equip_pick_confirm_{pick_item_id}"):
                                        st.session_state["dq_equip_pick_prompt"] = False
                                        st.session_state["dq_equip_pick_item_id"] = ""
                                        # 职业署名限制（武器）前端先校验，避免静默失败。
                                        meta_eq = pick_item.get("meta") or {}
                                        slot = meta_eq.get("slot")
                                        req_roles = meta_eq.get("req_roles")
                                        if str(slot) == "weapon" and isinstance(req_roles, list) and req_roles:
                                            if str(who) == "hero":
                                                actual_role = str(state.get("role", "warrior"))
                                            else:
                                                actual_role = ""
                                                for m in party_members:
                                                    if str(m.get("mid", "")) == str(who):
                                                        actual_role = str(m.get("role", ""))
                                                        break
                                            allow = any(str(actual_role) == str(r) for r in req_roles)
                                            if not allow:
                                                st.session_state["dq_equip_err_msg"] = "该职业不可装备该类型的装备。"
                                                _trim_log()
                                                st.rerun()

                                        if str(who) == "hero":
                                            st.session_state.dq_state = dq.dq_equip_item(state, pick_item_id)
                                        else:
                                            st.session_state.dq_state = dq.dq_member_equip_item(state, str(who), pick_item_id)
                                        _qt_bag = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                                        if bool(_qt_bag.get("active")):
                                            _qt_bag["focus"] = "show_equipped"
                                            _qt_bag["target_equip_item_id"] = str(pick_item_id)

                                        # 后置校验：如果装备未生效且是武器署名限制，则强制提示。
                                        if str(slot) == "weapon" and isinstance(req_roles, list) and req_roles:
                                            pick_id_s = str(pick_item_id)
                                            if str(who) == "hero":
                                                after_item = (st.session_state.dq_state.get("equipped") or {}).get(slot)
                                            else:
                                                after_item = None
                                                for m in (st.session_state.dq_state.get("party_members") or []) or []:
                                                    if str(m.get("mid", "")) == str(who):
                                                        after_item = (m.get("equipped") or {}).get(slot)
                                                        break
                                            equipped_ok = bool(after_item) and str(after_item.get("item_id", "")) == pick_id_s
                                            if not equipped_ok:
                                                st.session_state["dq_equip_err_msg"] = "该职业不可装备该类型的装备。"
                                        _trim_log()
                                        st.rerun()
                                with c3:
                                    if st.button("取消", key=f"dq_equip_pick_cancel_{pick_item_id}"):
                                        st.session_state["dq_equip_pick_prompt"] = False
                                        st.session_state["dq_equip_pick_item_id"] = ""
                                        st.rerun()
                            _dq_pick_equip_target_dialog()
                        else:
                            _pm2 = pick_item.get("meta") or {}
                            _bgp2, _fgp2, _bdp2 = _dq_equipment_quality_colors(_pm2)
                            _np2 = html_escape.escape(str(pick_item.get("name", "装备")))
                            st.markdown(
                                f"请选择穿戴对象：<span style=\"display:inline-block;background:{_bgp2};color:{_fgp2};"
                                f"border:1px solid {_bdp2};border-radius:8px;padding:2px 10px;font-weight:700;\">"
                                f"{_np2}</span>",
                                unsafe_allow_html=True,
                            )
                            who = st.radio(
                                "人物",
                                wearer_opts,
                                format_func=lambda x: wearer_labels.get(str(x), str(x)),
                                key=f"dq_equip_pick_target_inline_{pick_item_id}",
                                horizontal=True,
                            )
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("确认", type="primary", key=f"dq_equip_pick_confirm_inline_{pick_item_id}"):
                                    st.session_state["dq_equip_pick_prompt"] = False
                                    st.session_state["dq_equip_pick_item_id"] = ""

                                    # 职业署名限制（武器）前端先校验，避免静默失败。
                                    meta_eq = pick_item.get("meta") or {}
                                    slot = meta_eq.get("slot")
                                    req_roles = meta_eq.get("req_roles")
                                    if str(slot) == "weapon" and isinstance(req_roles, list) and req_roles:
                                        if str(who) == "hero":
                                            actual_role = str(state.get("role", "warrior"))
                                        else:
                                            actual_role = ""
                                            for m in party_members:
                                                if str(m.get("mid", "")) == str(who):
                                                    actual_role = str(m.get("role", ""))
                                                    break
                                        allow = any(str(actual_role) == str(r) for r in req_roles)
                                        if not allow:
                                            st.session_state["dq_equip_err_msg"] = "该职业不可装备该类型的装备。"
                                            _trim_log()
                                            st.rerun()

                                    if str(who) == "hero":
                                        st.session_state.dq_state = dq.dq_equip_item(state, pick_item_id)
                                    else:
                                        st.session_state.dq_state = dq.dq_member_equip_item(state, str(who), pick_item_id)
                                    _qt_bag = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                                    if bool(_qt_bag.get("active")):
                                        _qt_bag["focus"] = "show_equipped"
                                        _qt_bag["target_equip_item_id"] = str(pick_item_id)

                                    # 后置校验：如果装备未生效且是武器署名限制，则强制提示。
                                    if str(slot) == "weapon" and isinstance(req_roles, list) and req_roles:
                                        pick_id_s = str(pick_item_id)
                                        if str(who) == "hero":
                                            after_item = (st.session_state.dq_state.get("equipped") or {}).get(slot)
                                        else:
                                            after_item = None
                                            for m in (st.session_state.dq_state.get("party_members") or []) or []:
                                                if str(m.get("mid", "")) == str(who):
                                                    after_item = (m.get("equipped") or {}).get(slot)
                                                    break
                                        equipped_ok = bool(after_item) and str(after_item.get("item_id", "")) == pick_id_s
                                        if not equipped_ok:
                                            st.session_state["dq_equip_err_msg"] = "该职业不可装备该类型的装备。"
                                    _trim_log()
                                    st.rerun()
                            with c2:
                                if st.button("取消", key=f"dq_equip_pick_cancel_inline_{pick_item_id}"):
                                    st.session_state["dq_equip_pick_prompt"] = False
                                    st.session_state["dq_equip_pick_item_id"] = ""
                                    st.rerun()
            for i in range(0, min(40, len(equips)), 4):
                row = equips[i:i + 4]
                cols = st.columns(4)
                for j, it in enumerate(row):
                    meta = it.get("meta", {}) or {}
                    slot = meta.get("slot")
                    raw_sp_eq = int(meta.get("sell_price") or 0)
                    sp_eq = max(1, int(raw_sp_eq * float(getattr(dq, "SELL_PRICE_RATIO", 0.20))))
                    with cols[j]:
                        with st.container(border=True):
                            _bg_eq, _fg_eq, _bd_eq = _dq_equipment_quality_colors(meta)
                            _nm_eq = html_escape.escape(_dq_equip_card_title_name(str(it.get("name") or "装备")))
                            _sl_eq = html_escape.escape(str(slot_cn.get(slot, slot)))
                            st.markdown(
                                f"""
<div style="padding:8px 10px;border:1px solid {_bd_eq};border-radius:10px;background:{_bg_eq};">
  <div style="font-weight:700;color:{_fg_eq};margin-bottom:4px;">{_sl_eq} · {_nm_eq}</div>
</div>
""",
                                unsafe_allow_html=True,
                            )
                            _dq_backpack_equip_card_details(it, dq)
                            b1, b2 = st.columns(2)
                            with b1:
                                _equip_btn_key = (
                                    "dq_tutorial_equip_pick_btn"
                                    if bool(_q1_bag_active and _q1_bag_focus_effective == "equip_button" and str(it.get("item_id", "")) == _q1_target_equip_id)
                                    else f"dq_equip_pick_{i}_{j}_{it['item_id']}"
                                )
                                if st.button("装备", key=_equip_btn_key):
                                    st.session_state["dq_equip_pick_prompt"] = True
                                    st.session_state["dq_equip_pick_item_id"] = str(it["item_id"])
                                    _qt_bag = st.session_state.dq_state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
                                    if bool(_qt_bag.get("active")):
                                        _qt_bag["focus"] = "equip_pick"
                                        _qt_bag["target_equip_item_id"] = str(it["item_id"])
                                    st.rerun()
                            with b2:
                                if st.button("出售", key=f"dq_sell_eq_{i}_{j}_{it['item_id']}"):
                                    st.session_state.dq_state = dq.dq_sell_item(state, it["item_id"])
                                    _trim_log()
                                    st.rerun()
        else:
            st.info("暂无可穿装备（商店或战斗掉落）。")

    # ---------------- 设置（独立标签，在「背包/装备」右侧） ----------------
    with tabs[6]:
        st.markdown("### 系统设置")
        st.caption("默认开启。关闭后不再弹出战斗全屏技能视频。")
        st.toggle(
            "战斗动画",
            value=True,
            key="dq_settings_battle_anim",
            help="关闭后执行动作不再弹出全屏战斗视频。",
        )

    # 日志已分别放到「冒险 / 战斗」标签页中


def _dq_ensure_game_assets() -> bool:
    """首次进入：检查 img / music / video 是否齐全，缺了先下载再进游戏。"""
    from pathlib import Path

    import asset_bootstrap as ab

    if st.session_state.get("dq_assets_skip") or st.session_state.get("dq_assets_ok"):
        return True

    root = Path(__file__).resolve().parent
    missing = ab.find_missing_assets(root)
    if not missing:
        st.session_state["dq_assets_ok"] = True
        return True

    st.markdown(
        """
        <style>
        .block-container { padding-top: 2.4rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _left, mid, _right = st.columns([0.5, 3.0, 0.5])
    with mid:
        st.markdown("## 游戏资源下载")
        st.caption("首次进入会检查 img、music、video 三个文件夹是否齐全。")
        st.caption(f"仓库：{ab.REPO_URL}")
        st.warning(f"当前缺少 {len(missing)} 个文件。")
        if ab.git_available():
            st.info("已检测到 Git，将优先从 Gitee 仓库拉取资源。")
        else:
            st.info("未检测到 Git，将直接从 Gitee 下载缺失文件。")

        failed = st.session_state.get("dq_asset_failed") or []
        if st.session_state.get("dq_asset_need_choice"):
            st.error(f"有 {len(failed)} 个文件没有下完。")
            with st.expander("查看失败文件", expanded=True):
                for item in failed[:80]:
                    st.text(str(item.get("path") or item))
                extra = len(failed) - 80
                if extra > 0:
                    st.caption(f"其余 {extra} 个未列出。")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("重试下载", type="primary", width="stretch"):
                    st.session_state.pop("dq_asset_need_choice", None)
                    st.session_state.pop("dq_asset_failed", None)
                    st.session_state["dq_asset_do_sync"] = True
                    st.rerun()
            with c2:
                if st.button("跳过下载，直接进入游戏", width="stretch"):
                    st.session_state["dq_assets_skip"] = True
                    st.rerun()
            return False

        if not st.session_state.get("dq_asset_do_sync"):
            with st.expander(f"缺少的文件（{len(missing)}）"):
                for item in missing[:80]:
                    st.text(str(item.get("path") or ""))
                extra = len(missing) - 80
                if extra > 0:
                    st.caption(f"其余 {extra} 个未列出。")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("开始下载", type="primary", width="stretch"):
                    st.session_state["dq_asset_do_sync"] = True
                    st.rerun()
            with c2:
                if st.button("跳过下载，直接进入游戏", width="stretch"):
                    st.session_state["dq_assets_skip"] = True
                    st.rerun()
            return False

        log_box = st.status("正在准备资源…", expanded=True)
        bar = st.progress(0, text="准备中")

        def _on_progress(i: int, n: int, msg: str) -> None:
            total = max(int(n or 1), 1)
            bar.progress(min(1.0, float(i) / float(total)), text=str(msg or ""))
            log_box.write(str(msg or ""))

        try:
            result = ab.sync_missing_assets(root, progress_cb=_on_progress)
        except Exception as e:
            log_box.update(label="下载失败", state="error")
            st.session_state["dq_asset_failed"] = [{"path": str(e)}]
            st.session_state["dq_asset_need_choice"] = True
            st.session_state.pop("dq_asset_do_sync", None)
            st.rerun()
            return False

        still = result.failed or ab.find_missing_assets(root)
        if still:
            log_box.update(label="部分文件失败", state="error")
            st.session_state["dq_asset_failed"] = still
            st.session_state["dq_asset_need_choice"] = True
            st.session_state.pop("dq_asset_do_sync", None)
            st.rerun()
            return False

        log_box.update(label="资源已就绪", state="complete")
        st.session_state["dq_assets_ok"] = True
        st.rerun()
        return False


def main():
    if not _dq_ensure_game_assets():
        return
    show_dq_game_page()


if __name__ == "__main__":
    main()
