import os
import time
import threading
import uuid
import random as _pvp_random
from typing import Dict, Any
import mimetypes
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS

app = Flask(__name__)
CORS(app)
MUSIC_DIR = os.path.join(os.path.dirname(__file__), "music")
VIDEO_DIR = os.path.join(os.path.dirname(__file__), "video")
IMG_DIR = os.path.join(os.path.dirname(__file__), "img")


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "healthy"})

@app.route('/api/test', methods=['GET'])
def test_endpoint():
    """测试端点"""
    return jsonify({
        "message": "后端服务运行正常",
        "timestamp": "2024-01-01 12:00:00"
    })


@app.route('/api/music/<path:filename>', methods=['GET'])
def serve_music_file(filename: str):
    """提供背景音乐静态文件，便于浏览器缓存，避免前端反复传 base64。"""
    try:
        # 限定目录并阻止路径穿越
        safe_name = os.path.basename(filename or "")
        if not safe_name:
            return jsonify({"error": "invalid filename"}), 400
        if not os.path.exists(os.path.join(MUSIC_DIR, safe_name)):
            return jsonify({"error": "file not found"}), 404
        # 强缓存：首次下载后尽量走本地缓存，减少重复回源
        resp = send_from_directory(MUSIC_DIR, safe_name, mimetype="audio/mpeg")
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/dq-img/<path:filename>', methods=['GET'])
def serve_dq_img(filename: str):
    """仙境 Hero 头像/立绘（供 bootstrap 预下载与前端展示）。"""
    try:
        safe_name = os.path.basename(filename or "")
        if not safe_name:
            return jsonify({"error": "invalid filename"}), 400
        if not os.path.isfile(os.path.join(IMG_DIR, safe_name)):
            return jsonify({"error": "file not found"}), 404
        mt = mimetypes.guess_type(safe_name)[0] or "image/jpeg"
        resp = send_from_directory(IMG_DIR, safe_name, mimetype=mt)
        resp.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/dq-battle-video/<path:filename>', methods=['GET'])
def serve_dq_battle_video(filename: str):
    """仙境 Hero 战斗动作短视频（供弹窗 <video> 播放，仅允许 video/ 目录内文件名）。"""
    try:
        safe_name = os.path.basename(filename or "")
        if not safe_name:
            return jsonify({"error": "invalid filename"}), 400
        full = os.path.join(VIDEO_DIR, safe_name)
        if not os.path.isfile(full):
            return jsonify({"error": "file not found"}), 404
        mt = mimetypes.guess_type(safe_name)[0] or "video/mp4"
        # conditional=True 支持 Range 请求，避免部分浏览器/环境下 <video> 黑屏无法起播
        resp = send_file(full, mimetype=mt, conditional=True, max_age=86400)
        resp.headers["Cache-Control"] = "public, max-age=86400"
        resp.headers.setdefault("Accept-Ranges", "bytes")
        return resp
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -----------------------------------------------------------------------------
# PVP 联机房间（进程内内存；多 worker 部署时需改为 Redis 等共享存储）
# -----------------------------------------------------------------------------
_pvp_lock = threading.Lock()
_pvp_rooms: Dict[str, Any] = {}


def _pvp_gen_room_id() -> str:
    for _ in range(900):
        rid = f"{_pvp_random.randint(0, 9999):04d}"
        if rid not in _pvp_rooms:
            return rid
    return uuid.uuid4().hex[:6]


def _pvp_scrub_battle_for_public(b: Dict[str, Any]) -> Dict[str, Any]:
    """不向前端泄露对方具体指令，仅标记是否已提交。"""
    if not isinstance(b, dict):
        return b
    out = dict(b)
    out["host_plan_submitted"] = out.get("host_plan") is not None
    out["guest_plan_submitted"] = out.get("guest_plan") is not None
    out.pop("host_plan", None)
    out.pop("guest_plan", None)
    return out


def _pvp_public_view(room: Dict[str, Any]) -> Dict[str, Any]:
    import copy

    out = {k: v for k, v in room.items() if k not in ("host_token", "guest_token")}
    if "battle" in out and isinstance(out.get("battle"), dict):
        out = dict(out)
        out["battle"] = _pvp_scrub_battle_for_public(copy.deepcopy(out["battle"]))
    return out


def _pvp_init_battle(room: Dict[str, Any]) -> None:
    import dq_rpg as _dq

    hs = room.get("host_snapshot") or {}
    gs = room.get("guest_snapshot") or {}
    room["phase"] = "battle"
    room["battle"] = _dq.dq_pvp_battle_init(hs if isinstance(hs, dict) else {}, gs if isinstance(gs, dict) else {})


@app.route("/api/pvp/create", methods=["POST"])
def pvp_create():
    data = request.get_json(silent=True) or {}
    snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else {}
    with _pvp_lock:
        rid = _pvp_gen_room_id()
        host_token = uuid.uuid4().hex
        _pvp_rooms[rid] = {
            "room_id": rid,
            "host_snapshot": snapshot,
            "guest_snapshot": None,
            "guest_ready": False,
            "phase": "waiting",
            "host_token": host_token,
            "guest_token": None,
            "created": time.time(),
        }
    return jsonify({"ok": True, "room_id": rid, "host_token": host_token})


@app.route("/api/pvp/join", methods=["POST"])
def pvp_join():
    data = request.get_json(silent=True) or {}
    rid = str(data.get("room_id") or "").strip()
    snapshot = data.get("snapshot") if isinstance(data.get("snapshot"), dict) else {}
    if len(rid) != 4 or not rid.isdigit():
        return jsonify({"ok": False, "error": "房间号须为 4 位数字"}), 400
    with _pvp_lock:
        room = _pvp_rooms.get(rid)
        if not room:
            return jsonify({"ok": False, "error": "房间不存在"}), 404
        if room.get("phase") != "waiting":
            return jsonify({"ok": False, "error": "房间已开始或已结束"}), 400
        if room.get("guest_snapshot"):
            return jsonify({"ok": False, "error": "房间已满"}), 400
        guest_token = uuid.uuid4().hex
        room["guest_snapshot"] = snapshot
        room["guest_token"] = guest_token
        room["guest_ready"] = False
    return jsonify({"ok": True, "room_id": rid, "guest_token": guest_token})


@app.route("/api/pvp/room/<rid>", methods=["GET"])
def pvp_room_get(rid):
    rid = str(rid or "").strip()
    with _pvp_lock:
        room = _pvp_rooms.get(rid)
        if not room:
            return jsonify({"ok": False, "error": "not_found"}), 404
        return jsonify({"ok": True, "room": _pvp_public_view(room)})


@app.route("/api/pvp/ready", methods=["POST"])
def pvp_ready():
    data = request.get_json(silent=True) or {}
    rid = str(data.get("room_id") or "").strip()
    token = str(data.get("token") or "").strip()
    with _pvp_lock:
        room = _pvp_rooms.get(rid)
        if not room or room.get("guest_token") != token:
            return jsonify({"ok": False, "error": "forbidden"}), 403
        room["guest_ready"] = True
    return jsonify({"ok": True})


@app.route("/api/pvp/start", methods=["POST"])
def pvp_start():
    data = request.get_json(silent=True) or {}
    rid = str(data.get("room_id") or "").strip()
    token = str(data.get("token") or "").strip()
    with _pvp_lock:
        room = _pvp_rooms.get(rid)
        if not room or room.get("host_token") != token:
            return jsonify({"ok": False, "error": "forbidden"}), 403
        if not room.get("guest_snapshot"):
            return jsonify({"ok": False, "error": "缺少对手"}), 400
        if not room.get("guest_ready"):
            return jsonify({"ok": False, "error": "对手未准备"}), 400
        if room.get("phase") != "waiting":
            return jsonify({"ok": False, "error": "状态错误"}), 400
        _pvp_init_battle(room)
    return jsonify({"ok": True})


@app.route("/api/pvp/battle/plan", methods=["POST"])
def pvp_battle_plan():
    """同步回合：提交本方所有存活单位的指令；双方均提交后服务器一次结算。"""
    import dq_rpg as _dq

    data = request.get_json(silent=True) or {}
    rid = str(data.get("room_id") or "").strip()
    token = str(data.get("token") or "").strip()
    plans = data.get("plans") if isinstance(data.get("plans"), dict) else {}
    seed = (hash(rid) ^ hash(token) ^ int(time.time() * 1000)) % (2**31)
    rng = _pvp_random.Random(seed)
    with _pvp_lock:
        room = _pvp_rooms.get(rid)
        if not room or room.get("phase") != "battle":
            return jsonify({"ok": False, "error": "不在对战中"}), 400
        b = room.get("battle") or {}
        if b.get("result"):
            return jsonify({"ok": False, "error": "对战已结束"}), 400
        if token not in (room.get("host_token"), room.get("guest_token")):
            return jsonify({"ok": False, "error": "forbidden"}), 403
        side = "host" if token == room.get("host_token") else "guest"
        r_before = int(b.get("round") or 1)
        err = _dq.dq_pvp_submit_plans(b, side, plans)
        if err:
            return jsonify({"ok": False, "error": err}), 400
        rerr = _dq.dq_pvp_resolve_round(b, rng)
        if rerr:
            return jsonify({"ok": False, "error": rerr}), 400
        resolved = int(b.get("round") or 1) > r_before
        room["battle"] = b
    return jsonify(
        {
            "ok": True,
            "resolved": resolved,
            "room": _pvp_public_view(room),
        }
    )


@app.route("/api/pvp/battle/action", methods=["POST"])
def pvp_battle_action():
    import dq_rpg as _dq

    data = request.get_json(silent=True) or {}
    rid = str(data.get("room_id") or "").strip()
    token = str(data.get("token") or "").strip()
    kind = str(data.get("kind") or data.get("action") or "").strip().lower()
    if kind in ("", "atk"):
        kind = "attack"
    payload = {
        "kind": kind,
        "actor": data.get("actor"),
        "sid": data.get("sid"),
        "target_id": data.get("target_id"),
        "defend_target": data.get("defend_target"),
    }
    seed = (hash(rid) ^ hash(token) ^ int(time.time() * 1000)) % (2**31)
    rng = _pvp_random.Random(seed)
    with _pvp_lock:
        room = _pvp_rooms.get(rid)
        if not room or room.get("phase") != "battle":
            return jsonify({"ok": False, "error": "不在对战中"}), 400
        b = room.get("battle") or {}
        if b.get("result"):
            return jsonify({"ok": False, "error": "对战已结束"}), 400
        ba = str(b.get("actor") or "").strip()
        if not ba:
            t = b.get("turn")
            ba = "host:hero" if t == "host" else ("guest:hero" if t == "guest" else "")
        if not payload.get("actor"):
            payload["actor"] = ba
        act_side = str(ba.split(":", 1)[0]) if ":" in ba else ""
        if act_side == "host" and token != room.get("host_token"):
            return jsonify({"ok": False, "error": "不是你的回合"}), 403
        if act_side == "guest" and token != room.get("guest_token"):
            return jsonify({"ok": False, "error": "不是你的回合"}), 403
        if act_side not in ("host", "guest"):
            return jsonify({"ok": False, "error": "回合状态异常"}), 400
        side = "host" if token == room.get("host_token") else "guest"
        nb, _logs, err = _dq.dq_pvp_apply_action(b, side, payload, rng)
        if err:
            return jsonify({"ok": False, "error": err}), 400
        room["battle"] = nb
    return jsonify({"ok": True})


@app.route("/api/pvp/leave", methods=["POST"])
def pvp_leave():
    data = request.get_json(silent=True) or {}
    rid = str(data.get("room_id") or "").strip()
    token = str(data.get("token") or "").strip()
    with _pvp_lock:
        room = _pvp_rooms.get(rid)
        if not room:
            return jsonify({"ok": True})
        ph = room.get("phase")
        if token and token == room.get("host_token"):
            _pvp_rooms.pop(rid, None)
        elif token and token == room.get("guest_token"):
            if ph == "waiting":
                room["guest_snapshot"] = None
                room["guest_token"] = None
                room["guest_ready"] = False
            else:
                room["guest_snapshot"] = None
                room["guest_token"] = None
                room["guest_ready"] = False
    return jsonify({"ok": True})


if __name__ == "__main__":
    host = os.environ.get("BACKEND_HOST", "0.0.0.0")
    port = int(os.environ.get("BACKEND_PORT", "8083"))
    debug = os.environ.get("BACKEND_DEBUG", "False").lower() == "true"

    print("启动仙境Hero 后端服务...")
    print(f"服务地址: http://{host}:{port}")
    print("API:")
    print("  GET  /api/health")
    print("  GET  /api/test")
    print("  GET  /api/music/<filename>")
    print("  GET  /api/dq-img/<filename>")
    print("  GET  /api/dq-battle-video/<filename>")
    print("  PVP: POST /api/pvp/create | join | ready | start | battle/plan | battle/action | leave")
    print("       GET  /api/pvp/room/<房间号>")
    app.run(host=host, port=port, debug=debug)
