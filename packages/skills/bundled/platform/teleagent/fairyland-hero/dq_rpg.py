import base64
import copy
import csv
import hashlib
import io
import json
import os
import random
import secrets
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def clamp_int(x: Any, lo: int, hi: int, default: Optional[int] = None) -> int:
    try:
        v = int(x)
        if v < lo:
            return lo
        if v > hi:
            return hi
        return v
    except Exception:
        return default if default is not None else lo


def export_state(state: Dict[str, Any]) -> str:
    # 存档基准时间：导出时刻写入，保证“过了几小时再登录”时能补足恢复
    st = copy.deepcopy(state)
    st.setdefault("meta", {})
    st["meta"]["last_regen_ts"] = int(time.time())
    raw = json.dumps(st, ensure_ascii=False, separators=(",", ":"))
    b = raw.encode("utf-8")
    return base64.b64encode(b).decode("ascii")


def import_state(s: str) -> Dict[str, Any]:
    b = base64.b64decode(s.strip())
    raw = b.decode("utf-8")
    state = json.loads(raw)
    # 简单校验字段存在；不做深度攻击面处理（仅供本项目可信导入）
    if not isinstance(state, dict) or "v" not in state:
        raise ValueError("存档格式不正确")
    # 兼容旧版本/前端校验：只要关键战斗字段齐全即可继续
    if "hp" not in state or "level" not in state or "exp" not in state:
        raise ValueError("存档缺少关键字段")
    out = copy.deepcopy(state)
    _ensure_attrs(out)
    _ensure_equipped_slots(out)
    _migrate_materials_to_inventory(out)
    out.setdefault("party_members", [])
    out.setdefault("party_armory", {})
    out.setdefault("resources", {})
    out["resources"].setdefault("clue_quiz_scores", {})
    _apply_clue_milestones(out)
    dq_ensure_clue_quiz_pending(out)
    out.setdefault("role", "warrior")
    out.setdefault("talents", [])
    out.setdefault("talent_picked", {})
    out.setdefault("meta", {}).setdefault("pending_talent", None)
    _clamp_player_level(out)
    _recalc_player_from_equipment(out)
    out["hp"] = min(int(out.get("hp", 0) or 0), int(out.get("max_hp", 1) or 1))
    out["mp"] = min(int(out.get("mp", 0) or 0), int(out.get("max_mp", 1) or 1))
    return out


RNG_POOL_SIZE = 5


def _refresh_rng_pool(state: Dict[str, Any]) -> None:
    """刷新随机种子池；用于新游戏或读档后打散后续战斗流程。"""
    meta = state.setdefault("meta", {})
    base_seed = int(state.get("seed", 1) or 1)
    pool = []
    for i in range(RNG_POOL_SIZE):
        # 系统随机 + 时间 + 主种子混合，避免读档后流程完全可预测
        s = (
            int(secrets.randbelow(2**31 - 1))
            ^ int(time.time_ns() & 0x7FFFFFFF)
            ^ int((base_seed + 1315423911 * (i + 1)) & 0x7FFFFFFF)
        )
        pool.append(max(1, s))
    meta["rng_pool"] = pool
    meta["rng_pool_tick"] = 0


def _ensure_rng_pool(state: Dict[str, Any], *, refresh: bool = False) -> None:
    meta = state.setdefault("meta", {})
    pool = meta.get("rng_pool")
    valid = isinstance(pool, list) and len(pool) == RNG_POOL_SIZE and all(isinstance(x, int) and x > 0 for x in pool)
    if refresh or not valid:
        _refresh_rng_pool(state)
    else:
        meta["rng_pool_tick"] = int(meta.get("rng_pool_tick", 0) or 0)


def dq_make_rng(state: Dict[str, Any], salt: str) -> random.Random:
    """
    统一 RNG 入口：混合主种子 + 5种子池 + turn + salt，并推进 tick。
    读档时会刷新种子池，因此同一存档多次读档后战斗出招不会完全重演。
    """
    _ensure_rng_pool(state)
    meta = state.setdefault("meta", {})
    pool = meta.get("rng_pool") or [1] * RNG_POOL_SIZE
    tick = int(meta.get("rng_pool_tick", 0) or 0)
    turn = int(meta.get("turn", 0) or 0)
    base_seed = int(state.get("seed", 1) or 1)
    salt_key = f"{salt}|{turn}|{tick}"
    salt_hash = int(hashlib.sha256(salt_key.encode("utf-8")).hexdigest()[:16], 16)
    mix = base_seed ^ salt_hash ^ (turn * 99991 + (tick + 1) * 131071)
    for i, v in enumerate(pool):
        mix ^= (int(v) & 0x7FFFFFFF) << (i % 13)
        mix ^= (int(v) * (i + 3) * 2654435761) & 0xFFFFFFFF
    meta["rng_pool_tick"] = tick + 1
    return random.Random(int(mix & 0xFFFFFFFFFFFFFFFF))


def _dq_ensure_saves_csv_layout() -> None:
    """若项目根目录仍有旧的 dq_saves.csv，且 games/ 下尚无存档，则移入 games/。"""
    root = Path(__file__).resolve().parent
    legacy = root / "dq_saves.csv"
    games_dir = root / "games"
    target = games_dir / "dq_saves.csv"
    if legacy.is_file() and not target.is_file():
        games_dir.mkdir(parents=True, exist_ok=True)
        try:
            legacy.replace(target)
        except OSError:
            pass


def dq_saves_csv_path() -> str:
    """存档表路径：项目下 games/dq_saves.csv。"""
    _dq_ensure_saves_csv_layout()
    return str(Path(__file__).resolve().parent / "games" / "dq_saves.csv")


def _dq_atomic_write_text(path: str, text: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(p.parent), prefix="dq_saves_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as wf:
            wf.write(text)
        os.replace(tmp, p)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def dq_list_csv_save_names() -> List[str]:
    """CSV 中已存在的冒险者姓名（去重、排序）。"""
    path = dq_saves_csv_path()
    if not os.path.isfile(path):
        return []
    names: List[str] = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "name" not in reader.fieldnames:
                return []
            for row in reader:
                n = (row.get("name") or "").strip()
                if n:
                    names.append(n)
    except OSError:
        return []
    return sorted(set(names))


def dq_list_csv_save_entries() -> List[Dict[str, str]]:
    """开始界面用：返回 [{name, updated_at}, …]；同名保留最后一行；按存档时间新→旧排序。"""
    path = dq_saves_csv_path()
    if not os.path.isfile(path):
        return []
    raw: List[Dict[str, str]] = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "name" not in reader.fieldnames:
                return []
            for row in reader:
                n = (row.get("name") or "").strip()
                if not n:
                    continue
                raw.append({"name": n, "updated_at": (row.get("updated_at") or "").strip()})
    except OSError:
        return []

    def _ts_key(s: str) -> float:
        t = (s or "").strip()
        if len(t) >= 19:
            try:
                return time.mktime(time.strptime(t[:19], "%Y-%m-%d %H:%M:%S"))
            except Exception:
                return 0.0
        return 0.0

    by_name: Dict[str, str] = {}
    for e in raw:
        by_name[e["name"]] = e["updated_at"]
    merged = [{"name": n, "updated_at": t} for n, t in by_name.items()]
    # 按存档时间倒序（最新在上）；无/无效时间视为 0，排在最后；时间相同按姓名升序
    merged.sort(key=lambda x: (-_ts_key(x["updated_at"]), x["name"]))
    return merged


SAVE_CSV_FIELDNAMES = ("name", "save_data", "updated_at", "pwd_salt", "pwd_hash")


def _dq_generate_password_salt() -> str:
    return secrets.token_hex(16)


def _dq_hash_save_password(salt: str, password: str) -> str:
    raw = (salt or "") + "\0" + (password or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def dq_csv_row_requires_password(name: str) -> bool:
    """CSV 中该姓名行是否已设置校验密码（非旧版无密码存档）。"""
    n = (name or "").strip()
    if not n:
        return False
    path = dq_saves_csv_path()
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "name" not in reader.fieldnames:
                return False
            for row in reader:
                if (row.get("name") or "").strip() == n:
                    return bool((row.get("pwd_hash") or "").strip())
    except OSError:
        return False
    return False


def dq_delete_save_from_csv(name: str) -> None:
    """从 CSV 中删除指定姓名的存档行；若文件不存在或无该行则不写盘。"""
    n = (name or "").strip()
    if not n:
        raise ValueError("姓名为空")
    path = dq_saves_csv_path()
    if not os.path.isfile(path):
        return
    fieldnames = list(SAVE_CSV_FIELDNAMES)
    rows: List[Dict[str, str]] = []
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "name" not in reader.fieldnames:
                return
            for row in reader:
                if (row.get("name") or "").strip() == n:
                    continue
                rows.append({k: (row.get(k) or "") for k in fieldnames})
    except OSError:
        raise
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    _dq_atomic_write_text(path, buf.getvalue())


def dq_csv_has_save(name: str) -> bool:
    n = (name or "").strip()
    if not n:
        return False
    path = dq_saves_csv_path()
    if not os.path.isfile(path):
        return False
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "name" not in reader.fieldnames:
                return False
            for row in reader:
                if (row.get("name") or "").strip() == n:
                    return True
    except OSError:
        return False
    return False


def dq_load_state_from_csv(name: str, password: Optional[str] = None) -> Dict[str, Any]:
    """按冒险者姓名从 CSV 读取存档并 `import_state`。
    若该行已设置 pwd_hash，则必须提供正确 password；旧版无密码行可不填密码。"""
    n = (name or "").strip()
    if not n:
        raise ValueError("请输入冒险者姓名")
    path = dq_saves_csv_path()
    if not os.path.isfile(path):
        raise FileNotFoundError("尚未保存过任何存档（缺少 games/dq_saves.csv）")
    blob: Optional[str] = None
    salt = ""
    phash = ""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "name" not in reader.fieldnames:
            raise FileNotFoundError("存档文件格式不正确")
        for row in reader:
            if (row.get("name") or "").strip() == n:
                blob = (row.get("save_data") or "").strip()
                salt = (row.get("pwd_salt") or "").strip()
                phash = (row.get("pwd_hash") or "").strip()
                break
    if not blob:
        raise FileNotFoundError(f"未找到姓名为「{n}」的存档")
    if phash:
        if not (password or "").strip():
            raise ValueError("该存档已设置校验密码，请输入密码")
        if _dq_hash_save_password(salt, password.strip()) != phash:
            raise ValueError("校验密码错误")
    out = import_state(blob)
    _ensure_rng_pool(out, refresh=True)
    dq_ensure_q1_opening_story(out)
    return out


def dq_save_state_to_csv(state: Dict[str, Any], password: str) -> None:
    """将当前进度按角色姓名写入/覆盖 CSV 一行；password 为校验密码（明文仅用于本次哈希，写入 salt+hash）。"""
    name = (state.get("name") or "").strip()
    if not name:
        raise ValueError("角色姓名为空，无法保存到 CSV")
    pwd = (password or "").strip()
    if not pwd:
        raise ValueError("请设置校验密码后再保存")
    blob = export_state(state)
    path = dq_saves_csv_path()
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    fieldnames = list(SAVE_CSV_FIELDNAMES)
    pwd_salt = _dq_generate_password_salt()
    pwd_hash = _dq_hash_save_password(pwd_salt, pwd)
    rows: List[Dict[str, str]] = []
    if os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames and "name" in reader.fieldnames:
                    for row in reader:
                        r = {k: (row.get(k) or "") for k in fieldnames}
                        if (r.get("name") or "").strip() != name:
                            rows.append(r)
        except OSError:
            rows = []
    rows.append(
        {
            "name": name,
            "save_data": blob,
            "updated_at": ts,
            "pwd_salt": pwd_salt,
            "pwd_hash": pwd_hash,
        }
    )
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    _dq_atomic_write_text(path, buf.getvalue())


def _clamp_player_level(state: Dict[str, Any]) -> None:
    """等级上限与满级经验条。"""
    lv = max(1, int(state.get("level", 1) or 1))
    if lv > MAX_PLAYER_LEVEL:
        state["level"] = MAX_PLAYER_LEVEL
        lv = MAX_PLAYER_LEVEL
    else:
        state["level"] = lv
    if lv >= MAX_PLAYER_LEVEL:
        state["exp_to_next"] = 0
    else:
        nxt, _ = _player_level_curve(lv)
        state["exp_to_next"] = int(nxt)


def dq_migrate_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """运行中旧存档补齐六维并重算战斗数值（无副作用时可反复调用）。"""
    out = copy.deepcopy(state)
    _ensure_attrs(out)
    _ensure_equipped_slots(out)
    _migrate_materials_to_inventory(out)
    _migrate_inventory_equipment_attrs(out)
    out.setdefault("party_members", [])
    out.setdefault("party_armory", {})
    out.setdefault("role", "warrior")
    out.setdefault("talents", [])
    out.setdefault("talent_picked", {})
    out.setdefault("meta", {}).setdefault("pending_talent", None)
    out.setdefault("resources", {}).setdefault("clue", 0)
    out.setdefault("resources", {}).setdefault("clues_found", [])
    out.setdefault("resources", {}).setdefault("clue_effect_maps", [])
    out.setdefault("resources", {}).setdefault("clue_quiz_scores", {})
    _apply_clue_milestones(out)
    dq_ensure_clue_quiz_pending(out)
    for m in out.get("party_members", []) or []:
        m.setdefault("skills", [])
        m.setdefault("talents", [])
        m.setdefault("talent_picked", {})
        m.setdefault("equipped", {s: None for s in EQUIPMENT_SLOTS})
        if isinstance(m.get("attrs"), dict):
            _migrate_attrs_dict_inplace(m["attrs"])
        _normalize_member_pending_points(m, int(out.get("level", m.get("level", 1)) or 1))
        _sync_member_skills(out, m)
        _recalc_member_stats(m, int(out.get("level", m.get("level", 1)) or 1), out.get("party_armory"), out.get("resources"))
    _clamp_player_level(out)
    _strip_retired_common_skills(out)
    _recalc_player_from_equipment(out)
    out["hp"] = min(int(out.get("hp", 0) or 0), int(out.get("max_hp", 1) or 1))
    out["mp"] = min(int(out.get("mp", 0) or 0), int(out.get("max_mp", 1) or 1))
    pending = out.setdefault("meta", {}).get("pending_story")
    if isinstance(pending, dict):
        sid = str(pending.get("sid", "") or "")
        if sid in ("q1_seal_whisper", "q2_forest_echo", "q3_mines_crack", "q4_tide_price", "q5_throne_last"):
            step = int(pending.get("step", 0) or 0)
            pending.update(_main_story_scene(sid, step))
    return out


def _ensure_meta_logs(state: Dict[str, Any]) -> None:
    meta = state.setdefault("meta", {})
    if "log" not in meta or not isinstance(meta.get("log"), list):
        meta["log"] = []
    if "battle_log" not in meta or not isinstance(meta.get("battle_log"), list):
        meta["battle_log"] = []


# 六维属性：升级后由玩家手动分配（vit 体质影响生命与物防面板；def/mdef 为战斗面板数值，非分配项）
ATTR_KEYS: Tuple[str, ...] = ("str", "int", "dex", "agi", "luk", "vit")
# 六维中文（与装备主/副属性、界面展示一致：战士→力量 str，法师/牧师→智慧 int，猎人→精准 dex，刺客→敏捷 agi）
ATTR_CN: Dict[str, str] = {
    "str": "力量",
    "int": "智慧",
    "dex": "精准",
    "agi": "敏捷",
    "luk": "幸运",
    "vit": "体力",
}
STAT_POINTS_PER_LEVEL = 2
INITIAL_ABILITY_POINTS = 5  # 开局可分配能力点（六维初始均为 1）

# 装备：六槽主属性（副属性随机）
EQUIPMENT_SLOTS: Tuple[str, ...] = ("weapon", "shield", "helmet", "mail", "belt", "accessory")
# 新手教学战斗：只掉落非武器，避免非法师/弓等职业专属武器战士无法装备
Q1_TUTORIAL_NON_WEAPON_SLOTS: Tuple[str, ...] = ("shield", "helmet", "mail", "belt", "accessory")
SLOT_MAIN_ATTR: Dict[str, str] = {
    "weapon": "str",
    "shield": "vit",
    "helmet": "int",
    "mail": "agi",
    "belt": "dex",
    "accessory": "luk",
}
SLOT_CN: Dict[str, str] = {
    "weapon": "武器",
    "shield": "盾牌",
    "helmet": "头盔",
    "mail": "铠甲",
    "belt": "腰带",
    "accessory": "饰品",
}
QUALITY_CN: Dict[str, str] = {
    "normal": "普通",
    "fine": "精良",
    "epic": "史诗",
    "legend": "传说",
    "supreme": "至尊",
}
QUALITY_MULT: Dict[str, float] = {
    "normal": 1.0,
    "fine": 1.14,
    "epic": 1.32,
    "legend": 1.55,
    "supreme": 1.95,
}
# 先判定是否掉落装备，再按“Q阶段”与槽位权重随机品质（Q越高，高品质占比越高）
# tier: 1=Q1, 2=Q2, 3=Q3, 4=Q4, 5=Q5
QUALITY_WEIGHTS_BY_TIER_NON_ACC: Dict[int, List[Tuple[str, float]]] = {
    1: [("normal", 0.74), ("fine", 0.225), ("epic", 0.03), ("legend", 0.005)],
    2: [("normal", 0.67), ("fine", 0.255), ("epic", 0.055), ("legend", 0.02)],
    3: [("normal", 0.60), ("fine", 0.26), ("epic", 0.095), ("legend", 0.045)],
    4: [("normal", 0.50), ("fine", 0.27), ("epic", 0.15), ("legend", 0.08)],
    5: [("normal", 0.40), ("fine", 0.29), ("epic", 0.20), ("legend", 0.11)],
}
QUALITY_WEIGHTS_BY_TIER_ACC: Dict[int, List[Tuple[str, float]]] = {
    1: [("normal", 0.71), ("fine", 0.235), ("epic", 0.04), ("legend", 0.014), ("supreme", 0.001)],
    2: [("normal", 0.64), ("fine", 0.255), ("epic", 0.07), ("legend", 0.031), ("supreme", 0.004)],
    3: [("normal", 0.57), ("fine", 0.26), ("epic", 0.11), ("legend", 0.053), ("supreme", 0.007)],
    4: [("normal", 0.47), ("fine", 0.27), ("epic", 0.16), ("legend", 0.09), ("supreme", 0.01)],
    5: [("normal", 0.37), ("fine", 0.29), ("epic", 0.21), ("legend", 0.12), ("supreme", 0.01)],
}
INVENTORY_MAX_SLOTS = 48

# 战斗用药水：按当前最大 HP/MP 的百分比恢复（战斗中用 battle 的 player_max_hp / player_max_mp）
POTION_HP_PCT = 60
POTION_MP_PCT = 40
POTION_DUAL_HP_PCT = 50
POTION_DUAL_MP_PCT = 30
POTION_FULL_HP_PCT = 100
POTION_FULL_MP_PCT = 100
POTION_GOLDEN_HP_PCT = 100
POTION_GOLDEN_MP_PCT = 100
POTION_REVIVE_HP_PCT = 30
POTION_REVIVE_MP_PCT = 30
BATTLE_POTION_USES = frozenset(
    {
        "heal_potion",
        "mp_potion",
        "dual_potion",
        "full_heal_potion",
        "full_mp_potion",
        "golden_apple",
        "revive_potion",
    }
)
# 防守/守护姿态：本回合敌人下一次直接攻击伤害倍率（与文案「减伤 X%」对应：保留比例 = 1−X/100）
DEFEND_SELF_INCOMING_MULT = 0.35  # 守护自己：减伤 65%
DEFEND_GUARD_ALLY_INCOMING_MULT = 0.55  # 守护队友：减伤 45%（直击主角或被守护队友受击先乘此系数）
# 援护：全队受到的敌方直接伤害再×该系数（额外约 20% 免伤）
COVER_PARTY_INCOMING_MULT = 0.80
COVER_PARTY_DURATION_TURNS = 3
# 战士「战吼」「盾反」共用冷却回合数（与技能释放当回合不计入递减，在回合结束时递减）
WARRIOR_SPECIAL_SKILL_CD_TURNS = 3
# 盾反：本回合敌方单体/指向主角的命中强制打主角；主角受到的该部分直接伤害再×此系数（额外约 20% 免伤）
SHIELD_COUNTER_PLAYER_INCOMING_MULT = 0.80
# 盾反：实际扣血后，将这部分伤害的该比例反弹给当次攻击的敌人
SHIELD_COUNTER_REFLECT_FRAC = 0.30
# 战吼：全队对敌直接伤害倍率；持续回合数（含释放当回合在内，每完整回合结束减 1）
WAR_CRY_ATK_MULT = 1.20
WAR_CRY_DURATION_TURNS = 2
# 主角「防守」：使用后当回合末先写入该值再减 1，故下一完整回合开始时仍 >0 不可再用，再下一回合可用（隔 1 回合）。
PLAYER_DEFEND_COOLDOWN_TURNS = 2
# 牧师 AI：预计单次治疗中「过量治疗占比」超过此值则不放圣疗/群体祈祷，优先惩戒等其它行动（期望治疗量按公式取随机系数均值）。
CLERIC_MAX_OVERHEAL_RATIO = 0.20
# 友方当前生命比例 ≤ 此值时无视过量治疗判定，仍放圣疗/群体祈祷。
CLERIC_OVERHEAL_IGNORE_MAX_HP_RATIO = 0.50
# 群体祈祷：基础随机触发概率；当主角与两名存活队友共三人血量均未满时提高概率
CLERIC_GROUP_PRAYER_CHANCE_BASE = 0.28
CLERIC_GROUP_PRAYER_CHANCE_ALL_THREE_NOT_FULL = 0.82

# 法师队友：四系法术 MP 消耗（原 4/6/8/12，上调以降低续航碾压）
MAGE_MP_ARCANE_BOLT = 6
MAGE_MP_FIRE_BLAST = 9
MAGE_MP_CHAIN_LIGHTNING = 12
MAGE_MP_METEOR = 16
# 法师 INT→法术技能攻击面（与 _player_mage_spell_att、队友法师 AI 一致）
MAGE_INT_SPELL_ATK_MULT = 1.95
# 爆炎术：基础倍率；30% 附加可叠加灼烧（见 _mage_apply_fire_blast_burn）
MAGE_FIRE_BLAST_BASE_POWER = 1.28
MAGE_FIRE_BLAST_BURN_CHANCE = 0.30
MAGE_BURN_STACK_MAX = 3
MAGE_BURN_TURNS = 3
MAGE_BURN_MAX_HP_PCT_PER_STACK = 0.05
# 连锁闪电：共 3 段，每段倍率为完整技能倍率×该系数
MAGE_CHAIN_HIT_POWER_FRAC = 0.5
MAGE_CHAIN_EXTRA_HITS = 2

# 牧师队友：技能 MP（上调以降低战斗中蓝量过于宽裕）
CLERIC_MP_HOLY_HEAL = 7
CLERIC_MP_GROUP_PRAYER = 11
CLERIC_MP_JUDGEMENT = 8
CLERIC_MP_DIVINE_BLESS = 14
# 猎人队友：技能 MP（按成长阶梯）
HUNTER_MP_AIM_SHOT = 4
HUNTER_MP_PIERCE_ARROW = 6
HUNTER_MP_VOLLEY = 8
HUNTER_MP_EAGLE_EYE = 10
# 连射：固定段数与单段倍率（天赋仍加成在单段上）
HUNTER_VOLLEY_HITS = 2
HUNTER_VOLLEY_HIT_POWER = 0.85
# 穿透箭：对额外目标的溅射倍率
HUNTER_PIERCE_SPLASH_POWER = 0.2
# 鹰眼狙击：主目标倍率（与队友 AI 权重一致）
HUNTER_EAGLE_EYE_POWER = 1.75
HUNTER_EAGLE_EYE_BLIND_CHANCE = 0.10
HUNTER_BLIND_MISS_CHANCE = 0.50
# 猎人队友：物攻以 DEX 为底盘；军械 STR 加成弱化；物防面板略低于战士
HUNTER_DEX_ATK_MULT = 1.76
HUNTER_STR_ARMORY_ATK_MULT = 0.60
HUNTER_DEF_PANEL_MULT = 0.90
# 猎人：雷达图上的 DEX 含加点+装备+军械+天赋；物攻 DEX 底盘须与之一致，避免「合计 DEX 很高但 atk 很低」
# 盗贼队友：技能 MP（按成长阶梯）
ROGUE_MP_QUICK_STAB = 4
ROGUE_MP_SHADOW_STEP = 6
ROGUE_MP_VENOM_EDGE = 8
ROGUE_MP_ASSASSINATE = 10
# 刺客：STR→面板 atk 系数低于战士；物攻另加「有效 AGI×系数」（与 _effective_attrs 口径一致，含军械/天赋 AGI）；不再用 DEX 折算进物攻
ROGUE_STR_ATK_MULT = 1.60
ROGUE_AGI_ATK_BONUS_MULT = 0.66
# 刺客：有效 AGI 每点换算闪避（其余职业 0.0032 且合计硬顶 32%）
ROGUE_AGI_EVA_PER_POINT = 0.0066
# 刺客：DEF→最大生命 的系数（显著低于牧师/法师，避免堆 DEF 撑血）
ROGUE_HP_DEF_COEF = 4.5
# 刺客：承伤时参与伤害公式的有效 DEF 比例（大幅降低堆防的减伤收益；面板等效免伤与此一致）
ROGUE_INCOMING_DEF_EFFECTIVE_MULT = 0.32
# 快速刺击：每刀为「普攻」同公式的倍率；第2～4刀依次 70%/30%/10% 概率追加，最多 4 刀
QUICK_STAB_HIT_POWER = 0.6
QUICK_STAB_CHAIN_PROBS = (0.70, 0.30, 0.10)
# 惩戒术伤害：倍率与 INT 系数（略上调）
CLERIC_JUDGEMENT_POWER = 1.16
CLERIC_JUDGEMENT_INT_SCALE = 2.38
# 战败金币惩罚：普通区域与无限地牢分开配置
LOSE_GOLD_RATIO_NORMAL = 0.18
LOSE_GOLD_RATIO_INFINITE = 0.03

# 旅店与被动恢复（每 5 分钟）
INN_COST_PER_MEMBER = 30
DEFAULT_MAX_STAMINA = 120
PASSIVE_REGEN_INTERVAL_SEC = 5 * 60
PASSIVE_REGEN_HP_PER_INTERVAL = 2
PASSIVE_REGEN_MP_PER_INTERVAL = 1
PASSIVE_REGEN_STAMINA_PER_INTERVAL = 5

ACCESSORY_SPECIALS: Dict[str, Dict[str, Any]] = {
    "execute": {"name": "裁决", "desc": "造成伤害后：非 Boss 且目标生命低于 22% 时，2.5% 概率直接斩杀。"},
    "gold_hoard": {"name": "贪婪", "desc": "战斗胜利时金币 +28%。"},
    "soul_drink": {"name": "噬魔", "desc": "造成伤害时，将伤害值的 4% 转化为 MP。"},
    "thorn_shell": {"name": "荆棘", "desc": "受到敌人伤害后反弹 8%（至少 1）。"},
    "purify": {"name": "净化", "desc": "回合开始时 15% 概率清除一个异常状态。"},
    "giant_slayer": {"name": "破胆", "desc": "对非 Boss 敌人伤害 +10%（对 Boss 无效）。"},
}

SKILL_DESCRIPTIONS: Dict[str, str] = {
    "lianzhan": "连续挥砍 2 次，每段按 0.95 倍普攻结算；每段独立 10% 未命中（与 DEX 命中无关）。",
    "heavy_strike": "援护：消耗 8 MP，使你与存活队友受到的敌方直接伤害额外降低约 20%（持续 3 回合）。",
    "whirlwind": "对选中目标倍率约 1.48；余威随机溅射另一名敌人（相对主斩倍率×0.38）；仅一名敌人时余威落在同一目标。",
    "deep_cut": "深割伤口，倍率约 1.78；30% 概率使非 Boss 流血 3 回合，每回合按当前生命约 10% 结算。",
    "armor_break": (
        "盾反：本回合敌方行动阶段，所有敌人的攻击优先以你为目标；"
        "你因此受到的敌方直接伤害额外降低约 20%，并将实际所受伤害的 30% 反弹给当次攻击者。"
        "敌方先手时，盾反在敌方行动前即生效。冷却 3 回合。"
    ),
    "blood_rage": "嗜血斩击，倍率约 1.88；命中后按伤害 12% 回复生命。",
    "execution": "战吼：全队对敌人造成的直接伤害提高 20%，持续 2 回合（含释放当回合）；冷却 3 回合。",
    "holy_heal": "牧师基础治疗术，优先治疗最低血量目标。",
    "group_prayer": "牧师群体祈祷：两名以上友方未满血时概率触发群疗；主角与两名存活队友均未满血时触发率显著提高。",
    "judgement": "牧师惩戒强化，攻击法术伤害提升。",
    "divine_bless": "牧师圣光赐福：当按敌方目标规则估算，本回合普攻伤害上界之期望足以击杀某友方时，为其施加1回合伤害免疫；多目标时优先主角，其次牧师自身，否则选最危急者（冷却3回合）。若主角为战士且本回合已开盾反，则不赐福主角而改赐福其他符合条件的队友；若无则本回合不施放赐福并改施其他行动。敌方先手时先于敌方行动结算。",
    "arcane_bolt": "法师基础奥术冲击。",
    "fire_blast": (
        "爆炎术：基础倍率约 1.28（仍受「寒焰」等加成）。30% 概率附加灼烧：最多叠 3 层，"
        "每层使每回合按最大生命 5% 扣血（层数相乘，如 2 层为 10%）；持续 3 回合，再次触发时叠层并刷新回合数。"
        "灼烧对主线 Boss（boss_*）无效。"
    ),
    "chain_lightning": (
        "连锁闪电：默认 3 段（1 次主目标 +2 次弹射），每段倍率为完整连锁倍率的一半（0.5×）。"
        "第 1 段打当前选中目标；后续段在存活敌人中随机弹射（可重复命中同一单位）。"
        "若中途敌人全灭则后续段不再释放。天赋「雷链」：每段伤害再×0.9，并额外+1 次弹射。"
    ),
    "meteor": (
        "陨星术：对场上全体存活敌人释放；先按单体规则掷出一次总伤害（含暴击），再将总伤害平均分给每个敌人（余数由前几位各多 1 点）。"
    ),
    "aim_shot": "瞄准射击：必中（不经过自身命中率与对方闪避判定），按倍率对单体造成远程物伤。天赋「齐射」使本技能倍率额外+10%。",
    "pierce_arrow": "穿透箭：对主目标按倍率造成伤害；并对除主目标外的其他敌人附加溅射（倍率约 0.2）：场上仅 2 名敌人时另一名必吃溅射；3 名时另两名各吃一次；4 名及以上时在其余敌人中随机 2 名各吃一次。天赋「贯穿」使主箭倍率额外+10%、溅射倍率额外+5%。",
    "volley": "连射：连续 2 次远程物伤，每次倍率约 0.85；若当前目标中途死亡，余下次数随机选择仍存活敌人。天赋「节制」使每段独立暴击率额外+30%（与基础暴击相加，有上限）。",
    "eagle_eye": "鹰眼狙击：倍率约 1.75；对非 Boss 约 10% 概率附加致盲，使其下次攻击有 50% 概率失手（先于常规闪避判定）；致盲对 Boss 无效。天赋「重击」使本技能倍率额外+10%、致盲概率额外+20%。",
    "quick_stab": "快速刺击：每刀为普攻伤害的约 60%；第1刀必尝试，第2～4刀依次有70%、30%、10%概率追加，最多4刀（各刀独立判定暴击）。",
    "shadow_step": "影袭：基础约 1.22 倍普攻伤害；若目标当前生命比例高于 90%，额外 +0.1 倍伤害。",
    "venom_edge": "毒刃：约 1.32 倍伤害；50% 概率使非 Boss 流血 3 回合，每回合按当前生命约 10% 结算。",
    "assassinate": "暗杀：约 1.48 倍伤害；若目标当前生命低于 40%，10% 概率直接击杀（Boss 无效）。佩戴饰品「裁决」时：先判定暗杀必杀，未触发再按饰品裁决斩杀规则结算。",
    # 怪物招式（非主角技能，仅遇敌时由对应小怪使用；sid 以 mob_ 前缀区分）
    "mob_goblin_fireball": (
        "地精「火球术」：消耗约 4 MP，法术单体伤害（伤害倍率约 1.12，"
        "等效魔攻由攻击、MP 与等级折算）。约 20% 概率在行动中优先于蓄力与普通攻击发动；可闪避。"
    ),
    "mob_sprite_lightning": (
        "野灵「雷电术」：消耗约 6 MP，雷电法术单体伤害（倍率约 1.38）；"
        "不附加中毒。约 20% 概率发动；可闪避。"
    ),
    "mob_miner_guard": (
        "矿坑傀儡「守护姿态」：消耗约 4 MP，进入守护姿态；"
        "持续若干回合内，你对其造成的直接伤害额外乘以约 0.70（体感约减伤 30%）。"
        "每回合结束缩短持续；发动概率约 20%，先于蓄力与普攻。"
    ),
    "mob_sea_curse_heal": (
        "海祸咒灵「治愈术」：消耗约 7 MP，自身回复生命；"
        "当前生命低于约 90% 时较易发动，回复量与最大生命与攻击相关。发动约 20% 概率。"
    ),
    "mob_throne_brave": (
        "王座卫兵「勇气斩」：消耗约 8 MP，物理单体高倍率伤害（约 1.82 倍）；"
        "约 20% 概率发动。王座守卫战斗中召唤的卫兵与此相同招式池；可闪避。"
    ),
}

# 技能说明书大全：按职业分组（sid 应覆盖 SKILL_DESCRIPTIONS；遗漏的键会归入「其他」）
SKILL_MANUAL_ROLE_ORDER: Tuple[str, ...] = ("warrior", "cleric", "mage", "hunter", "rogue", "monster")
SKILL_MANUAL_ROLE_CN: Dict[str, str] = {
    "warrior": "战士",
    "cleric": "牧师",
    "mage": "法师",
    "hunter": "猎人",
    "rogue": "刺客",
    "monster": "怪物招式",
}
SKILL_MANUAL_SIDS_BY_ROLE: Dict[str, Tuple[str, ...]] = {
    "warrior": (
        "lianzhan",
        "heavy_strike",
        "whirlwind",
        "deep_cut",
        "armor_break",
        "blood_rage",
        "execution",
    ),
    "cleric": ("holy_heal", "group_prayer", "judgement", "divine_bless"),
    "mage": ("arcane_bolt", "fire_blast", "chain_lightning", "meteor"),
    "hunter": ("aim_shot", "pierce_arrow", "volley", "eagle_eye"),
    "rogue": ("quick_stab", "shadow_step", "venom_edge", "assassinate"),
    "monster": (
        "mob_goblin_fireball",
        "mob_sprite_lightning",
        "mob_miner_guard",
        "mob_sea_curse_heal",
        "mob_throne_brave",
    ),
}

DQ_SHOP_ITEMS: List[Dict[str, Any]] = [
    {"key": "pot_hp", "name": "恢复药水", "price": 100, "kind": "potion", "potion_use": "heal_potion"},
    {"key": "pot_mp", "name": "魔力药水", "price": 120, "kind": "potion", "potion_use": "mp_potion"},
    {"key": "pot_dual", "name": "混合药水", "price": 150, "kind": "potion", "potion_use": "dual_potion"},
    {"key": "respec_orb", "name": "角色属性重新分配宝珠", "price": 5000, "kind": "respec_orb"},
    {"key": "talent_respec_orb", "name": "天赋宝珠", "price": 3000, "kind": "talent_respec_orb"},
    # 制式装备：主属性在 dq_buy 时按「当时主角等级÷3 取整」；副属性额外加「当时地牢记录层÷4」，见 _shop_make_equip_item
    {"key": "eq_sh", "name": "木盾", "price": 880, "kind": "equip", "slot": "shield"},
    {"key": "eq_hm", "name": "皮帽", "price": 820, "kind": "equip", "slot": "helmet"},
    {"key": "eq_ml", "name": "皮甲", "price": 1050, "kind": "equip", "slot": "mail"},
    {"key": "eq_bt", "name": "旅者腰带", "price": 780, "kind": "equip", "slot": "belt"},
    {"key": "eq_ac", "name": "铜戒指", "price": 1300, "kind": "equip", "slot": "accessory"},
    # 队友职业武器：主属性同上（购入时锁定；str_bonus 等仅作文档/旧档兼容，购买时不读）
    {"key": "pw_warrior_1", "name": "守誓战剑", "price": 1420, "kind": "party_weapon", "role": "warrior", "tier": 1},
    {"key": "pw_cleric_1", "name": "祈愿法典", "price": 1400, "kind": "party_weapon", "role": "cleric", "tier": 1},
    {"key": "pw_mage_1", "name": "霜火长杖", "price": 1450, "kind": "party_weapon", "role": "mage", "tier": 1},
    {"key": "pw_hunter_1", "name": "风脊长弓", "price": 1350, "kind": "party_weapon", "role": "hunter", "tier": 1},
    {"key": "pw_rogue_1", "name": "夜行双刃", "price": 1380, "kind": "party_weapon", "role": "rogue", "tier": 1},
]

# 药水回收价（约购入价一半，与商店标价配套）
POTION_UNIT_SELL_PRICE: Dict[str, int] = {
    "heal_potion": 50,
    "mp_potion": 60,
    "dual_potion": 75,
    "full_heal_potion": 150,
    "full_mp_potion": 160,
    "golden_apple": 220,
    "revive_potion": 300,
}
# 材料单价（出售给商店）
MATERIAL_UNIT_SELL_PRICE: Dict[str, int] = {
    "草药": 120,
    "瘴气孢子": 140,
    "灵矿": 180,
    "海盐晶": 150,
    "王座残铁": 200,
}

# 主线五图各独占一种采集材料（战斗掉落与探索采集共用；无限地牢按层映射到 Q1~Q5）
ZONE_EXCLUSIVE_MATERIAL: Dict[str, str] = {
    "starter": "草药",
    "forest": "瘴气孢子",
    "mines": "灵矿",
    "coast": "海盐晶",
    "throne": "王座残铁",
}
# 全局出售折损：降低 80%（仅保留 20%）
SELL_PRICE_RATIO: float = 0.20


def _potion_unit_sell_price(use: str) -> int:
    return int(POTION_UNIT_SELL_PRICE.get(str(use), 100))


def _potion_restore_from_meta(battle: Dict[str, Any], meta: Dict[str, Any], use: str) -> Tuple[int, int]:
    """根据 meta 中的 heal_pct/mp_pct（缺省用全局常量）计算本次恢复的 HP/MP 量。"""
    mx_hp = max(1, int(battle.get("player_max_hp", 1)))
    mx_mp = max(1, int(battle.get("player_max_mp", 1)))
    m = meta or {}
    if use == "heal_potion":
        pct = int(m.get("heal_pct", POTION_HP_PCT))
        pct = max(1, min(100, pct))
        return int(mx_hp * pct / 100), 0
    if use == "mp_potion":
        pct = int(m.get("mp_pct", POTION_MP_PCT))
        pct = max(1, min(100, pct))
        return 0, int(mx_mp * pct / 100)
    if use == "dual_potion":
        hp_pct = max(1, min(100, int(m.get("heal_pct", POTION_DUAL_HP_PCT))))
        mp_pct = max(1, min(100, int(m.get("mp_pct", POTION_DUAL_MP_PCT))))
        return int(mx_hp * hp_pct / 100), int(mx_mp * mp_pct / 100)
    if use == "full_heal_potion":
        pct = max(1, min(100, int(m.get("heal_pct", POTION_FULL_HP_PCT))))
        return int(mx_hp * pct / 100), 0
    if use == "full_mp_potion":
        pct = max(1, min(100, int(m.get("mp_pct", POTION_FULL_MP_PCT))))
        return 0, int(mx_mp * pct / 100)
    if use == "golden_apple":
        hp_pct = max(1, min(100, int(m.get("heal_pct", POTION_GOLDEN_HP_PCT))))
        mp_pct = max(1, min(100, int(m.get("mp_pct", POTION_GOLDEN_MP_PCT))))
        return int(mx_hp * hp_pct / 100), int(mx_mp * mp_pct / 100)
    if use == "revive_potion":
        hp_pct = max(1, min(100, int(m.get("revive_hp_pct", POTION_REVIVE_HP_PCT))))
        mp_pct = max(1, min(100, int(m.get("revive_mp_pct", POTION_REVIVE_MP_PCT))))
        return int(mx_hp * hp_pct / 100), int(mx_mp * mp_pct / 100)
    return 0, 0


def _material_unit_sell_price(name: str) -> int:
    return int(MATERIAL_UNIT_SELL_PRICE.get(str(name), 80))


def _apply_sell_price_ratio(raw_price: int) -> int:
    return max(1, int(max(0, int(raw_price)) * SELL_PRICE_RATIO))


def _compute_equip_sell_price(meta: Dict[str, Any]) -> int:
    q = str(meta.get("quality", "normal"))
    qm = float(QUALITY_MULT.get(q, 1.0))
    main = int(meta.get("main_val", 2))
    sub = int(meta.get("sub_val", 1))
    base = int(main * 22 + sub * 11)
    return max(15, int(base * qm))


def _make_material_item(name: str, qty: int, rng: random.Random) -> Dict[str, Any]:
    sp = _material_unit_sell_price(name)
    return {
        "item_id": _new_id("mat", rng),
        "name": f"材料·{name}",
        "qty": max(1, int(qty)),
        "meta": {"kind": "material", "material_name": name, "sell_price": sp},
    }


def dq_try_add_material_stack(state: Dict[str, Any], name: str, qty: int, rng: random.Random) -> Tuple[bool, str]:
    """材料放入背包并占 1 格；同名堆叠。"""
    if qty <= 0:
        return True, ""
    inv = state.setdefault("inventory", [])
    for it in inv:
        meta = it.get("meta") or {}
        if meta.get("kind") == "material" and meta.get("material_name") == name:
            it["qty"] = int(it.get("qty", 0) or 0) + int(qty)
            return True, ""
    it = _make_material_item(name, qty, rng)
    ok, bad = dq_try_add_inventory(state, [it])
    if bad:
        return False, "背包已满"
    return True, ""


def _migrate_materials_to_inventory(state: Dict[str, Any]) -> None:
    mats = state.get("materials") or []
    if not mats:
        return
    seed = int(state.get("seed", 0) or 0) ^ 0xC0FFEE
    rng = random.Random(seed)
    for m in mats:
        nm = str(m.get("name", "草药"))
        q = int(m.get("qty", 0) or 0)
        if q <= 0:
            continue
        dq_try_add_material_stack(state, nm, q, rng)
    state["materials"] = []


def dq_migrate_legacy_state(state: Dict[str, Any]) -> None:
    """每次进入游戏界面时调用：旧版独立材料栏并入背包。"""
    _migrate_materials_to_inventory(state)
    _migrate_inventory_equipment_attrs(state)
    state.setdefault("party_members", [])
    state.setdefault("party_armory", {})
    state.setdefault("role", "warrior")
    _hg = str(state.get("hero_gender") or "男").strip()
    state["hero_gender"] = _hg if _hg in ("男", "女") else "男"
    state.setdefault("talents", [])
    state.setdefault("talent_picked", {})
    state.setdefault("meta", {}).setdefault("pending_talent", None)
    state.setdefault("resources", {}).setdefault("clue", 0)
    state.setdefault("resources", {}).setdefault("clues_found", [])
    state.setdefault("resources", {}).setdefault("clue_effect_maps", [])
    state.setdefault("resources", {}).setdefault("clue_quiz_scores", {})
    _apply_clue_milestones(state)
    dq_ensure_clue_quiz_pending(state)
    for m in state.get("party_members", []) or []:
        m.setdefault("skills", [])
        m.setdefault("talents", [])
        m.setdefault("talent_picked", {})
        m.setdefault("equipped", {s: None for s in EQUIPMENT_SLOTS})
        if isinstance(m.get("attrs"), dict):
            _migrate_attrs_dict_inplace(m["attrs"])
        _normalize_member_pending_points(m, int(state.get("level", m.get("level", 1)) or 1))
        _sync_member_skills(state, m)
        _recalc_member_stats(m, int(state.get("level", m.get("level", 1)) or 1), state.get("party_armory"), state.get("resources"))

    # 导入/老存档：补齐所有已达成等级但尚未选择的天赋（含高等级招募漏发场景）
    meta = state.setdefault("meta", {})
    meta.setdefault("pending_unlock_notice_queue", [])
    legacy_q = meta.get("pending_skill_queue")
    if isinstance(legacy_q, list) and legacy_q and not meta.get("pending_skill_replace_queue"):
        meta["pending_skill_replace_queue"] = [
            {"target": {"type": "player"}, "new": x.get("new"), "name": x.get("name")}
            for x in legacy_q
            if isinstance(x, dict) and x.get("new")
        ]
    meta.setdefault("pending_skill_replace_queue", [])
    if not isinstance(meta.get("pending_skill_replace"), dict):
        q0 = meta.get("pending_skill_replace_queue") or []
        meta["pending_skill_replace"] = q0[0] if isinstance(q0, list) and q0 else None
    lv = int(state.get("level", 1) or 1)
    for tl in TALENT_LEVELS:
        if lv < int(tl):
            continue
        _queue_talent_choice(
            state,
            target={"type": "player"},
            role=str(state.get("role", "warrior")),
            level=int(tl),
        )
        for mem in state.get("party_members", []) or []:
            _queue_talent_choice(
                state,
                target={"type": "member", "mid": str(mem.get("mid", ""))},
                role=str(mem.get("role", "")),
                level=int(tl),
            )
    _strip_retired_common_skills(state)


def _migrate_attrs_dict_inplace(attrs: Optional[Dict[str, Any]]) -> None:
    """旧存档 attrs 中的 def 迁移为体质 vit（六维）。"""
    if not isinstance(attrs, dict):
        return
    if "def" in attrs:
        d_old = int(attrs.get("def") or 1)
        attrs.pop("def", None)
        attrs["vit"] = max(int(attrs.get("vit", 1) or 1), d_old)


def _migrate_item_meta_attr_keys(it: Optional[Dict[str, Any]]) -> None:
    if not isinstance(it, dict):
        return
    meta = it.get("meta")
    if not isinstance(meta, dict):
        return
    for fld in ("main_attr", "sub_attr"):
        if meta.get(fld) == "def":
            meta[fld] = "vit"


def _migrate_inventory_equipment_attrs(state: Dict[str, Any]) -> None:
    eq = state.get("equipped")
    if isinstance(eq, dict):
        for s in EQUIPMENT_SLOTS:
            _migrate_item_meta_attr_keys(eq.get(s))
    inv = state.get("inventory")
    if isinstance(inv, list):
        for it in inv:
            _migrate_item_meta_attr_keys(it)


def _ensure_member_attrs(member: Dict[str, Any]) -> None:
    cur = member.get("attrs")
    if not isinstance(cur, dict):
        cur = {}
    _migrate_attrs_dict_inplace(cur)
    defaults = {"str": 1, "int": 1, "dex": 1, "agi": 1, "luk": 1, "vit": 1}
    for k in ATTR_KEYS:
        if k not in cur:
            cur[k] = defaults[k]
        else:
            cur[k] = clamp_int(cur[k], 1, 999, defaults[k])
    member["attrs"] = cur


def _ensure_attrs(state: Dict[str, Any]) -> None:
    """兼容旧存档：补齐 attrs / pending_stat_points。"""
    defaults = {"str": 1, "int": 1, "dex": 1, "agi": 1, "luk": 1, "vit": 1}
    cur = state.get("attrs")
    if not isinstance(cur, dict):
        cur = {}
    _migrate_attrs_dict_inplace(cur)
    for k in ATTR_KEYS:
        if k not in cur:
            cur[k] = defaults[k]
        else:
            cur[k] = clamp_int(cur[k], 1, 999, defaults[k])
    state["attrs"] = cur
    state.setdefault("pending_stat_points", 0)
    state["pending_stat_points"] = max(0, int(state.get("pending_stat_points", 0) or 0))


def _enemy_is_boss(enemy: Dict[str, Any]) -> bool:
    return str(enemy.get("mid", "") or "").startswith("boss_")


# 主线 Boss（boss_*）免疫来自我方的持续伤害与控制类异常（与 Q 无关，凡 boss_ 均适用）
BOSS_DEBUFF_IMMUNE_KINDS = frozenset({"bleed", "poison", "burn_stack", "blind"})


def _strip_boss_debuff_immunities(enemy: Dict[str, Any]) -> None:
    """移除 Boss 不应承受的 debuff；每回合持续结算前调用，兼容旧存档已挂上的异常。"""
    if not _enemy_is_boss(enemy):
        return
    effs = enemy.get("effects") or []
    enemy["effects"] = [
        x for x in effs if isinstance(x, dict) and str(x.get("kind", "")) not in BOSS_DEBUFF_IMMUNE_KINDS
    ]


def _ensure_equipped_slots(state: Dict[str, Any]) -> None:
    """保证 equipped 含六槽键。"""
    eq = state.setdefault("equipped", {})
    for s in EQUIPMENT_SLOTS:
        eq.setdefault(s, None)


def dq_skill_descriptions() -> Dict[str, str]:
    return dict(SKILL_DESCRIPTIONS)


def dq_skill_name(sid: str) -> str:
    sk = _skill_catalog().get(str(sid))
    return sk.name if sk else str(sid or "")


def dq_pvp_skill_needs_target(sid: str) -> bool:
    """PVP：是否需要选择对手单位（治疗/祝福等不需选敌方目标，由服务端挂接虚拟目标）。"""
    sk = _skill_catalog().get(str(sid))
    if not sk:
        return True
    if sk.kind in ("damage", "double_slash", "quick_stab_chain", "drain"):
        return True
    return False


def dq_skill_manual_sections() -> List[Tuple[str, List[Tuple[str, str]]]]:
    """技能说明书：[(职业标题, [(sid, 说明), ...]), ...]，供界面按职业分块展示。"""
    desc = SKILL_DESCRIPTIONS
    covered: set = set()
    out: List[Tuple[str, List[Tuple[str, str]]]] = []
    for role in SKILL_MANUAL_ROLE_ORDER:
        sids = SKILL_MANUAL_SIDS_BY_ROLE.get(str(role), ())
        pairs: List[Tuple[str, str]] = []
        for sid in sids:
            if sid in desc:
                pairs.append((sid, desc[sid]))
                covered.add(sid)
        lab = SKILL_MANUAL_ROLE_CN.get(str(role), str(role))
        if pairs:
            out.append((lab, pairs))
    rest = sorted([sid for sid in desc if sid not in covered])
    if rest:
        out.append(("其他", [(sid, desc[sid]) for sid in rest]))
    return out


def dq_format_equipment_item(it: Dict[str, Any]) -> str:
    """装备数值与说明（用于界面）。"""
    meta = it.get("meta") or {}
    slot = meta.get("slot", "?")
    slot_lab = SLOT_CN.get(str(slot), str(slot))
    q = meta.get("quality", "normal")
    q_lab = QUALITY_CN.get(str(q), str(q))
    lines = [f"【{it.get('name', '装备')}】", f"部位：{slot_lab}　品质：{q_lab}"]
    spl = meta.get("shop_purchase_hero_level")
    if spl is not None:
        lines.append(f"商店购入（当时主角 Lv{int(spl)}，主属性数值已锁定）")
    if meta.get("main_attr") in ATTR_KEYS:
        lines.append(f"主属性 {meta['main_attr'].upper()} +{int(meta.get('main_val', 0) or 0)}")
    if meta.get("sub_attr") in ATTR_KEYS:
        lines.append(f"副属性 {meta['sub_attr'].upper()} +{int(meta.get('sub_val', 0) or 0)}")
    for k, lab in (("atk_bonus", "物攻加成"), ("spell_bonus", "法伤加成"), ("heal_bonus", "治疗加成")):
        pv = float(meta.get(k, 0.0) or 0.0)
        if pv > 0:
            lines.append(f"{lab} +{int(round(pv * 100))}%")
    req_roles = meta.get("req_roles")
    if isinstance(req_roles, list) and req_roles:
        req_cn = "、".join([ROLE_CN.get(str(r), str(r)) for r in req_roles])
        lines.append(f"职业署名：{req_cn} 才可装备")
    for k, lab in (
        ("atk_pct", "攻击加成"),
        ("eva_bonus", "闪避加成"),
        ("mit_bonus", "免伤加成"),
        ("crit_bonus", "暴击加成"),
        ("hit_bonus", "命中加成"),
    ):
        pv = float(meta.get(k, 0.0) or 0.0)
        if pv > 0:
            lines.append(f"{lab} +{int(round(pv * 100))}%")
    sids = meta.get("special_ids")
    if isinstance(sids, list) and sids:
        for _sid in sids:
            if _sid in ACCESSORY_SPECIALS:
                sp = ACCESSORY_SPECIALS[_sid]
                lines.append(f"饰品能力：{sp['name']} — {sp['desc']}")
    else:
        sid = meta.get("special_id")
        if sid and sid in ACCESSORY_SPECIALS:
            sp = ACCESSORY_SPECIALS[sid]
            lines.append(f"饰品能力：{sp['name']} — {sp['desc']}")
    return "\n".join(lines)


def _compute_equip_attr_bonus(equipped: Dict[str, Any]) -> Dict[str, int]:
    out = {k: 0 for k in ATTR_KEYS}
    if not equipped:
        return out
    for slot in EQUIPMENT_SLOTS:
        it = equipped.get(slot)
        if not it:
            continue
        meta = it.get("meta") or {}
        mk = meta.get("main_attr")
        if mk == "def":
            mk = "vit"
        mv = int(meta.get("main_val", 0) or 0)
        if mk in ATTR_KEYS and mv:
            out[mk] += mv
        sk = meta.get("sub_attr")
        if sk == "def":
            sk = "vit"
        sv = int(meta.get("sub_val", 0) or 0)
        if sk in ATTR_KEYS and sv:
            out[sk] += sv
    return out


def _effective_attrs(state: Dict[str, Any]) -> Dict[str, int]:
    """
    主角有效六维：加点 + 装备 + 队伍军械（按当前职业）+ 天赋整数加成。
    与 dq_unit_hexagon_parts 的 total、队友 _effective_attrs_party_member 口径一致，供命中/闪避/技能等与战斗结算对齐。
    """
    _ensure_attrs(state)
    b = state.get("equip_attr_bonus")
    if not isinstance(b, dict):
        b = _compute_equip_attr_bonus(state.get("equipped") or {})
    armory = {k: 0 for k in ATTR_KEYS}
    if isinstance(state.get("party_armory"), dict):
        role = str(state.get("role", "warrior"))
        arm = (state.get("party_armory") or {}).get(role)
        if isinstance(arm, dict):
            armory["str"] = max(0, int(arm.get("str_bonus", 0) or 0))
            armory["int"] = max(0, int(arm.get("int_bonus", 0) or 0))
            armory["dex"] = max(0, int(arm.get("dex_bonus", 0) or 0))
            armory["agi"] = max(0, int(arm.get("agi_bonus", 0) or 0))
    talent_f = _talent_flat_attr_bonus(list(state.get("talents") or []))
    return {k: int(state["attrs"].get(k, 0)) + int(b.get(k, 0)) + armory[k] + talent_f[k] for k in ATTR_KEYS}


def dq_equipment_attr_bonus(state: Dict[str, Any]) -> Dict[str, int]:
    """装备对六维的加成（不含 attrs 本体），供界面显示「基础 +X」。"""
    _ensure_attrs(state)
    return dict(_compute_equip_attr_bonus(state.get("equipped") or {}))


def _talent_flat_attr_bonus(talent_ids: Optional[List[str]]) -> Dict[str, int]:
    """天赋 effects 中若含 str/int/dex/agi/luk/vit 的整数加成则汇总（当前多为 0，便于以后扩展）。"""
    out = {k: 0 for k in ATTR_KEYS}
    for tid in talent_ids or []:
        eff = (TALENT_CHOICE_DEFS.get(str(tid), {}) or {}).get("effects") or {}
        if not isinstance(eff, dict):
            continue
        for k in ATTR_KEYS:
            if k not in eff:
                continue
            try:
                v = eff.get(k)
                if isinstance(v, bool):
                    continue
                if isinstance(v, (int, float)):
                    out[k] += int(v)
            except (TypeError, ValueError):
                pass
    return out


def _player_battle_physical_att(state: Dict[str, Any]) -> int:
    """主角普攻/物系技能用的攻击面：面板 atk（刺客已在 _apply_attrs_to_base 中并入 AGI×系数与军械折算）。"""
    return int(state.get("atk", 0) or 0)


def _effective_attrs_party_member(member: Dict[str, Any], party_armory: Optional[Dict[str, Any]] = None) -> Dict[str, int]:
    """队友有效六维：与 dq_unit_hexagon_parts 的 total 一致（含军械库 STR/INT/DEX/AGI 加成）。"""
    _ensure_member_attrs(member)
    raw = member.get("attrs") or {}
    defaults = {"str": 1, "int": 1, "dex": 1, "agi": 1, "luk": 1, "vit": 1}
    base = {k: max(0, int(raw.get(k, defaults.get(k, 1)) or 0)) for k in ATTR_KEYS}
    eq = _compute_equip_attr_bonus(member.get("equipped") or {})
    equip_i = {k: max(0, int(eq.get(k, 0) or 0)) for k in ATTR_KEYS}
    armory = {k: 0 for k in ATTR_KEYS}
    if isinstance(party_armory, dict):
        role = str(member.get("role", ""))
        arm = party_armory.get(role)
        if isinstance(arm, dict):
            armory["str"] = max(0, int(arm.get("str_bonus", 0) or 0))
            armory["int"] = max(0, int(arm.get("int_bonus", 0) or 0))
            armory["dex"] = max(0, int(arm.get("dex_bonus", 0) or 0))
            armory["agi"] = max(0, int(arm.get("agi_bonus", 0) or 0))
    talent_f = _talent_flat_attr_bonus(list(member.get("talents") or []))
    return {k: base[k] + equip_i[k] + armory[k] + talent_f[k] for k in ATTR_KEYS}


def dq_unit_hexagon_parts(
    unit: Dict[str, Any],
    *,
    is_player: bool,
    party_armory: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    角色卡片六维分解：基础加点、装备词条、队伍军械（按单位职业从 party_armory 读取）、天赋六维整数加成。
    主角与队友均含军械分解；「合计」与 _effective_attrs / _effective_attrs_party_member 一致。
    """
    if is_player:
        _ensure_attrs(unit)
    else:
        _ensure_member_attrs(unit)
    raw = unit.get("attrs") or {}
    defaults = {"str": 1, "int": 1, "dex": 1, "agi": 1, "luk": 1, "vit": 1}
    base = {k: max(0, int(raw.get(k, defaults.get(k, 1)) or 0)) for k in ATTR_KEYS}
    eq = _compute_equip_attr_bonus(unit.get("equipped") or {})
    equip_i = {k: max(0, int(eq.get(k, 0) or 0)) for k in ATTR_KEYS}
    armory = {k: 0 for k in ATTR_KEYS}
    if isinstance(party_armory, dict):
        role = str(unit.get("role", "warrior" if is_player else "") or "")
        arm = party_armory.get(role)
        if isinstance(arm, dict):
            armory["str"] = max(0, int(arm.get("str_bonus", 0) or 0))
            armory["int"] = max(0, int(arm.get("int_bonus", 0) or 0))
            armory["dex"] = max(0, int(arm.get("dex_bonus", 0) or 0))
            armory["agi"] = max(0, int(arm.get("agi_bonus", 0) or 0))
    talent_f = _talent_flat_attr_bonus(list(unit.get("talents") or []))
    total = {k: base[k] + equip_i[k] + armory[k] + talent_f[k] for k in ATTR_KEYS}
    return {
        "base": base,
        "equip": equip_i,
        "armory": armory,
        "talent": talent_f,
        "total": total,
    }


def dq_inventory_slots_used(state: Dict[str, Any]) -> int:
    n = 0
    for it in state.get("inventory", []) or []:
        q = int(it.get("qty", 0) or 0)
        if q <= 0:
            continue
        meta = it.get("meta") or {}
        if meta.get("use") in BATTLE_POTION_USES:
            n += 1
        elif meta.get("kind") == "material":
            n += 1
        elif meta.get("slot"):
            n += max(1, q)
        else:
            n += 1
    return n


def dq_inventory_slot_cells(state: Dict[str, Any], max_slots: int = 48) -> List[Optional[str]]:
    """
    与 dq_inventory_slots_used 同口径的「格子」展开，供背包可视化。
    药水/材料：每栈占 1 格，数量大于 1 时在文案中显示 ×N；装备：占 max(1,q) 格。
    勿用 inventory 列表下标直接当格子（与占用数不一致）。
    """
    nmax = max(0, int(max_slots))
    cells: List[Optional[str]] = [None] * nmax
    si = 0
    for it in state.get("inventory", []) or []:
        q = int(it.get("qty", 0) or 0)
        if q <= 0:
            continue
        meta = it.get("meta") or {}
        raw_name = str(it.get("name", "?")).strip() or "?"
        if meta.get("use") in BATTLE_POTION_USES:
            need = 1
            label = f"{raw_name[:7]}×{q}" if q > 1 else raw_name[:10]
        elif meta.get("kind") == "material":
            need = 1
            label = f"{raw_name[:7]}×{q}" if q > 1 else raw_name[:10]
        elif meta.get("slot"):
            need = max(1, q)
            label = raw_name[:10]
        else:
            need = 1
            label = raw_name[:10]
        for _ in range(need):
            if si >= nmax:
                return cells
            cells[si] = label
            si += 1
    return cells


def dq_try_add_inventory(state: Dict[str, Any], items: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """尽量放入背包；返回 (成功描述, 失败描述)。格子满则整件丢弃。"""
    ok: List[str] = []
    bad: List[str] = []
    inv = state.setdefault("inventory", [])
    for it in items:
        need = 1
        meta = it.get("meta") or {}
        if meta.get("slot"):
            need = max(1, int(it.get("qty", 1) or 1))
        elif meta.get("use") in BATTLE_POTION_USES:
            need = 1
        elif meta.get("kind") == "material":
            need = 1
        if dq_inventory_slots_used(state) + need > INVENTORY_MAX_SLOTS:
            bad.append(it.get("name", "物品"))
            continue
        inv.append(it)
        ok.append(it.get("name", "物品"))
    return ok, bad


def _quality_tier_for_zone(zone_id: str, floor: int) -> int:
    """掉落品质阶段：Q1~Q5。无限地牢按层级映射到同一套阶段。"""
    zid = str(zone_id or "")
    if zid == "starter":
        return 1
    if zid == "forest":
        return 2
    if zid == "mines":
        return 3
    if zid == "coast":
        return 4
    if zid == "throne":
        return 5
    if zid == "infinite":
        # 与「每 6 层一 Q」一致：按当前层映射到 Q1～Q5 掉落阶段
        return _quality_tier_for_zone(_infinite_zone_for_floor(max(1, int(floor or 1))), floor)
    return 3


def _pick_quality(rng: random.Random, slot: str, zone_id: str, floor: int) -> str:
    tier = _quality_tier_for_zone(zone_id, floor)
    if slot == "accessory":
        weights = QUALITY_WEIGHTS_BY_TIER_ACC.get(tier, QUALITY_WEIGHTS_BY_TIER_ACC[3])
    else:
        weights = QUALITY_WEIGHTS_BY_TIER_NON_ACC.get(tier, QUALITY_WEIGHTS_BY_TIER_NON_ACC[3])
    r = rng.random()
    t = 0.0
    for q, w in weights:
        t += w
        if r <= t:
            return q
    return weights[-1][0]


def _quality_bonus_level(quality: str) -> int:
    order = {"normal": 0, "fine": 1, "epic": 2, "legend": 3, "supreme": 4}
    return int(order.get(str(quality), 0))


def _roll_sub_attr(rng: random.Random, main: str) -> Tuple[str, int]:
    pool = [k for k in ATTR_KEYS if k != main]
    sk = rng.choice(pool)
    sv = rng.randint(1, 3)
    return sk, sv


# 装备名称中的六维关键词 → 副属性键；仅当该维 ≠ 主属性时生效（与 SLOT_MAIN_ATTR 一致）
_EQUIP_NAME_SUB_KEYWORDS: Tuple[Tuple[str, str], ...] = (
    ("力量", "str"),
    ("智慧", "int"),
    ("精准", "dex"),
    ("敏捷", "agi"),
    ("幸运", "luk"),
    ("体力", "vit"),
)


def _sub_attr_hint_from_equip_name(name: str, main_attr: str) -> Optional[str]:
    """名称含「力量/智慧/精准…」且与主属性不同时，副属性强制为该维；否则返回 None（走随机副属）。"""
    s = str(name or "")
    if not s:
        return None
    main = str(main_attr or "")
    for kw, ak in _EQUIP_NAME_SUB_KEYWORDS:
        if kw in s:
            if ak != main and ak in ATTR_KEYS:
                return ak
            return None
    return None


def _maybe_roll_accessory_special(rng: random.Random, quality: str) -> Optional[str]:
    if quality not in ("legend", "supreme", "epic"):
        return None
    base = 0.06 if quality == "epic" else (0.14 if quality == "legend" else 0.35)
    if rng.random() > base:
        return None
    ids = list(ACCESSORY_SPECIALS.keys())
    return rng.choice(ids)


def _roll_accessory_epic_extra(rng: random.Random) -> Dict[str, float]:
    k = rng.choice(["atk_pct", "eva_bonus", "mit_bonus", "crit_bonus"])
    return {k: 0.01}


def _roll_combat_percent_affix(rng: random.Random, pct: float) -> Dict[str, float]:
    """随机一条战斗百分比词条（攻击/闪避/免伤/暴击）。"""
    keys = ["atk_pct", "eva_bonus", "mit_bonus", "crit_bonus"]
    return {str(rng.choice(keys)): max(0.0, float(pct))}


def _roll_accessory_special_ids(rng: random.Random, count: int) -> List[str]:
    ids = list(ACCESSORY_SPECIALS.keys())
    rng.shuffle(ids)
    n = max(0, min(int(count), len(ids)))
    return ids[:n]


def _player_magic_power(state: Dict[str, Any]) -> int:
    """INT：魔法伤害基准（用于火/雷等法术系技能）。"""
    _ensure_attrs(state)
    lv = int(state.get("level", 1))
    i = int(_effective_attrs(state)["int"])
    return max(1, int(i * 2.5 + lv * 1.8))


def _player_mage_spell_att(state: Dict[str, Any]) -> int:
    """法师技能攻击面：与队友法师 AI 一致（INT×MAGE_INT_SPELL_ATK_MULT×法伤加成；INT 含 _effective_attrs 军械）。"""
    _ensure_attrs(state)
    i = int(_effective_attrs(state).get("int", 1) or 1)
    role = str(state.get("role", "") or "")
    arm: Dict[str, Any] = {}
    if isinstance(state.get("party_armory"), dict):
        arm = (state.get("party_armory") or {}).get(role) or {}
    wm: Dict[str, Any] = {}
    w_it = (state.get("equipped") or {}).get("weapon")
    if isinstance(w_it, dict):
        wm = w_it.get("meta") or {}
    spell_bonus = 1.0 + float((arm or {}).get("spell_bonus", 0.0) or 0.0) + float(wm.get("spell_bonus", 0.0) or 0.0)
    return max(9, int(i * float(MAGE_INT_SPELL_ATK_MULT) * spell_bonus))


def _hp_def_coef_by_role(role: str) -> float:
    """体质 → 最大生命：base_max_hp = 20 + VIT×coef + Lv×4（再乘装备 hp% 等）。战士 coef 最高。"""
    r = str(role or "")
    if r == "warrior":
        return 7.2  # 战士：每 1 点 VIT 约 +7.2 最大 HP（同等级下 VIT 对血量影响最大）
    if r == "hunter":
        return 5.8
    if r == "rogue":
        return float(ROGUE_HP_DEF_COEF)
    if r in {"cleric", "mage"}:
        return 5.0
    return 6.0


def _incoming_def_effective_for_unit(role: Optional[str], raw_def: Any) -> int:
    """承伤与面板「等效免伤」：刺客仅按较低比例享受 DEF 减伤，与堆防战士等区分。"""
    rd = max(1, int(raw_def or 1))
    if str(role or "") == "rogue":
        return max(1, int(round(rd * float(ROGUE_INCOMING_DEF_EFFECTIVE_MULT))))
    return rd


def _incoming_mdef_effective_for_unit(role: Optional[str], raw_mdef: Any) -> int:
    """魔法承伤：刺客与物防一致，仅按较低比例享受 MDEF 减伤。"""
    rm = max(1, int(raw_mdef or 1))
    if str(role or "") == "rogue":
        return max(1, int(round(rm * float(ROGUE_INCOMING_DEF_EFFECTIVE_MULT))))
    return rm


def _battle_player_incoming_resist(battle: Dict[str, Any], *, magical: bool) -> int:
    if magical:
        return int(battle.get("player_mdef", 1) or 1)
    return int(battle.get("player_def", 1) or 1)


def _battle_ally_incoming_resist(ally: Dict[str, Any], *, magical: bool) -> int:
    if magical:
        return _incoming_mdef_effective_for_unit(str(ally.get("role", "")), int(ally.get("mdef", 1) or 1))
    return _incoming_def_effective_for_unit(str(ally.get("role", "")), int(ally.get("def", 1) or 1))


# Q4 幽影海岸「海妖系」敌人（幽魂 / 海祸咒灵 / 暗夜飞蛾 / 潮汐女巫）：普攻与蓄力亦按魔法伤害结算
COAST_SEA_MAGIC_ENEMY_MIDS = frozenset({"wraith", "sea_curse", "night_moth", "boss_sea_witch"})


def _enemy_sea_magic_attack_resist(enemy: Dict[str, Any], battle: Dict[str, Any], target: Dict[str, Any]) -> int:
    """海妖系对玩家的普攻/蓄力：使用 MDEF；非海妖仍用物防。"""
    mag = str(enemy.get("mid", "") or "") in COAST_SEA_MAGIC_ENEMY_MIDS
    if target.get("kind") == "player":
        return _battle_player_incoming_resist(battle, magical=mag)
    ally = battle["allies"][int(target["idx"])]
    return _battle_ally_incoming_resist(ally, magical=mag)


def _role_hit_rate(role: str, dex_with_equip: int) -> float:
    coef = float(ROLE_DEX_HIT_COEF.get(str(role or ""), 1.0) or 1.0)
    dex_score = max(0.0, float(max(0, int(dex_with_equip or 0))) * coef)
    progress = min(1.0, dex_score / FULL_HIT_DEX_NEED)
    return max(BASE_HIT_RATE, min(1.0, BASE_HIT_RATE + (1.0 - BASE_HIT_RATE) * progress))


def _apply_attrs_to_base(state: Dict[str, Any]) -> None:
    """
    根据六维（含装备主/副属性加成）+ 等级计算基础战斗数值写入 state['base']，
    再经 _recalc_player_from_equipment 汇总为面板攻防等。
    """
    _ensure_attrs(state)
    state["equip_attr_bonus"] = _compute_equip_attr_bonus(state.get("equipped") or {})
    bonus = state["equip_attr_bonus"]
    a = state["attrs"]
    lv = int(state.get("level", 1))
    s = int(a["str"]) + int(bonus.get("str", 0))
    i = int(a["int"]) + int(bonus.get("int", 0))
    ag = int(a["agi"]) + int(bonus.get("agi", 0))
    vit = int(a["vit"]) + int(bonus.get("vit", 0))

    role = str(state.get("role", "warrior"))
    talent_f = _talent_flat_attr_bonus(list(state.get("talents") or []))
    arm_role = (state.get("party_armory") or {}).get(role) if isinstance(state.get("party_armory"), dict) else None
    dex_arm_p = int(arm_role.get("dex_bonus", 0) or 0) if isinstance(arm_role, dict) else 0
    d_ex = int(a.get("dex", 0)) + int(bonus.get("dex", 0))

    if role == "hunter":
        grow_h = _member_role_attr_mult("hunter")
        dex_raw = d_ex + dex_arm_p + int(talent_f.get("dex", 0) or 0)
        dex_attr = max(1, int(dex_raw * float(grow_h.get("dex", 1.0) or 1.0)))
        base_atk = max(3, int(3 + dex_attr * float(HUNTER_DEX_ATK_MULT) + lv * 0.6))
        if isinstance(arm_role, dict):
            base_atk = int(base_atk * (1.0 + float(arm_role.get("atk_bonus", 0.0) or 0.0)))
            base_atk += int(int(arm_role.get("str_bonus", 0) or 0) * float(HUNTER_STR_ARMORY_ATK_MULT))
    elif role == "rogue":
        str_atk_coef = float(ROGUE_STR_ATK_MULT)
        base_atk = max(3, int(3 + s * str_atk_coef + lv * 0.6))
        if isinstance(arm_role, dict):
            base_atk = int(base_atk * (1.0 + float(arm_role.get("atk_bonus", 0.0) or 0.0)))
            base_atk += int(int(arm_role.get("str_bonus", 0) or 0) * float(ROGUE_STR_ATK_MULT))
        # 与队友 _recalc_member_stats：有效 AGI（attrs+装备+军械+天赋）× 系数
        ea_rg = _effective_attrs(state)
        agi_eff = int(ea_rg.get("agi", 0) or 0)
        base_atk = max(3, int(base_atk) + int(agi_eff * float(ROGUE_AGI_ATK_BONUS_MULT)))
    else:
        base_atk = max(3, int(3 + s * 1.35 + lv * 0.6))

    if role == "hunter":
        base_def = max(2, int(2 + vit * float(HUNTER_DEF_PANEL_MULT) + lv * 0.45))
    else:
        base_def = max(2, int(2 + vit * 0.95 + lv * 0.45))
    base_mdef = max(1, int(1 + i * 0.95 + vit * 0.28 + lv * 0.40))
    base_agi = max(4, int(4 + ag * 1.05 + lv * 0.25))
    hp_def_coef = _hp_def_coef_by_role(role)
    base_max_hp = max(20, int(20 + vit * hp_def_coef + lv * 4))
    clue_hp_pct = float((state.get("resources") or {}).get("clue_bonus_hp_pct", 0.0) or 0.0)
    if clue_hp_pct > 0:
        base_max_hp = max(20, int(base_max_hp * (1.0 + clue_hp_pct)))
    base_max_mp = max(8, int(8 + i * 4 + lv * 2))

    state["base"] = {
        "atk": base_atk,
        "def": base_def,
        "mdef": base_mdef,
        "agi": base_agi,
        "max_hp": base_max_hp,
        "max_mp": base_max_mp,
    }


def dq_allocate_stats(state: Dict[str, Any], allocation: Dict[str, int]) -> Dict[str, Any]:
    """将 pending_stat_points 全部分配到六维，总和必须等于剩余点数。"""
    state = copy.deepcopy(state)
    _ensure_attrs(state)
    pending = int(state.get("pending_stat_points", 0) or 0)
    if pending <= 0:
        return state
    total = 0
    for k in ATTR_KEYS:
        total += int(allocation.get(k, 0) or 0)
    if total != pending:
        raise ValueError(f"分配点数之和需等于可分配点数 {pending}（当前合计 {total}）")
    for k in ATTR_KEYS:
        v = int(allocation.get(k, 0) or 0)
        if v < 0:
            raise ValueError("单项点数不能为负")
        state["attrs"][k] = int(state["attrs"].get(k, 0)) + v
    state["pending_stat_points"] = 0
    _recalc_player_from_equipment(state)
    # 加点后上限变化（含 INT→MP、VIT→HP 等）：生命与魔力回满
    state["hp"] = int(state.get("max_hp", 1))
    state["mp"] = int(state.get("max_mp", 1))
    state.setdefault("meta", {}).setdefault("log", []).append(
        f"📊 能力点已分配：STR {state['attrs']['str']} / INT {state['attrs']['int']} / "
        f"DEX {state['attrs']['dex']} / AGI {state['attrs']['agi']} / LUK {state['attrs']['luk']} / VIT {state['attrs']['vit']}。"
        f" HP/MP 已回满。"
    )
    return state


def dq_allocate_party_member_stats(state: Dict[str, Any], member_mid: str, allocation: Dict[str, int]) -> Dict[str, Any]:
    """
    给招募队友分配能力点。
    - 分配后该成员 HP/MP 回满
    - 不影响主角装备与数值计算（队友目前无装备）
    """
    state = copy.deepcopy(state)
    members = state.setdefault("party_members", [])
    member = None
    for m in members:
        if m.get("mid") == member_mid:
            member = m
            break
    if not member:
        raise ValueError("未找到队伍成员")

    _ensure_attrs(state)
    pending = int(member.get("pending_stat_points", 0) or 0)
    if pending <= 0:
        return state

    total = 0
    for k in ATTR_KEYS:
        total += int(allocation.get(k, 0) or 0)
    if total != pending:
        raise ValueError(f"分配点数之和需等于可分配点数 {pending}（当前合计 {total}）")

    for k in ATTR_KEYS:
        v = int(allocation.get(k, 0) or 0)
        if v < 0:
            raise ValueError("单项点数不能为负")
        member["attrs"][k] = int(member["attrs"].get(k, 0) or 0) + v

    member["pending_stat_points"] = 0
    member["level"] = int(state.get("level", member.get("level", 1)) or 1)
    _recalc_member_stats(member, member["level"], state.get("party_armory"), state.get("resources"))
    member["hp"] = int(member.get("max_hp", 1) or 1)
    member["mp"] = int(member.get("max_mp", 1) or 1)

    state.setdefault("meta", {}).setdefault("log", []).append(
        f"📊 能力点已分配：{member.get('name','队友')}（{member.get('role','')}）HP/MP 已回满。"
    )
    return state


def dq_use_respec_orb(state: Dict[str, Any], item_id: str, target: str = "hero") -> Dict[str, Any]:
    """
    使用「角色属性重新分配宝珠」：
    - 主角（target=\"hero\"）：六维重置为 1，已投入点数返还到 pending_stat_points
    - 队友（target 为队友 mid）：同上，作用于该队员
    """
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        state.setdefault("meta", {}).setdefault("log", []).append("战斗中无法使用该道具。")
        return state
    _ensure_attrs(state)
    inv = state.setdefault("inventory", [])
    idx = None
    for i, it in enumerate(inv):
        if it.get("item_id") == item_id and int(it.get("qty", 0) or 0) > 0:
            idx = i
            break
    if idx is None:
        state.setdefault("meta", {}).setdefault("log", []).append("未找到可用的重新分配宝珠。")
        return state

    it = inv[idx]
    meta = it.get("meta") or {}
    if str(meta.get("kind", "")) != "respec_orb":
        state.setdefault("meta", {}).setdefault("log", []).append("该物品不是重新分配宝珠。")
        return state

    who = str(target or "hero").strip() or "hero"

    def _consume_orb() -> None:
        it["qty"] = int(it.get("qty", 1) or 1) - 1
        if int(it.get("qty", 0) or 0) <= 0:
            inv.pop(idx)
        state["inventory"] = inv

    if who == "hero":
        refunded = 0
        for k in ATTR_KEYS:
            cur = int(state["attrs"].get(k, 1) or 1)
            refunded += max(0, cur - 1)
            state["attrs"][k] = 1
        state["pending_stat_points"] = int(state.get("pending_stat_points", 0) or 0) + refunded
        _recalc_player_from_equipment(state)
        state["hp"] = int(state.get("max_hp", 1) or 1)
        state["mp"] = int(state.get("max_mp", 1) or 1)
        _consume_orb()
        state.setdefault("meta", {}).setdefault("log", []).append(
            f"🔮 使用角色属性重新分配宝珠（主角）：返还 {refunded} 点能力点，可重新加点（HP/MP 已回满）。"
        )
        return state

    member = None
    for m in state.get("party_members", []) or []:
        if str(m.get("mid", "")) == who:
            member = m
            break
    if not member:
        state.setdefault("meta", {}).setdefault("log", []).append("未找到该队友，宝珠未消耗。")
        return state

    attrs = member.setdefault("attrs", {k: 1 for k in ATTR_KEYS})
    refunded_m = 0
    for k in ATTR_KEYS:
        cur = int(attrs.get(k, 1) or 1)
        refunded_m += max(0, cur - 1)
        attrs[k] = 1
    member["pending_stat_points"] = int(member.get("pending_stat_points", 0) or 0) + refunded_m
    lv_m = int(member.get("level", state.get("level", 1)) or 1)
    _recalc_member_stats(member, lv_m, state.get("party_armory"), state.get("resources"))
    member["hp"] = int(member.get("max_hp", 1) or 1)
    member["mp"] = int(member.get("max_mp", 1) or 1)
    _consume_orb()
    nm = str(member.get("name", "队友"))
    state.setdefault("meta", {}).setdefault("log", []).append(
        f"🔮 使用角色属性重新分配宝珠（{nm}）：返还 {refunded_m} 点能力点，可重新加点（HP/MP 已回满）。"
    )
    return state


def dq_use_talent_respec_orb(state: Dict[str, Any], item_id: str, target: str = "hero") -> Dict[str, Any]:
    """
    使用「天赋宝珠」：清空指定主角或队友的已选天赋，并按当前等级重新排队 Lv10/20/30 天赋二选一。
    """
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        state.setdefault("meta", {}).setdefault("log", []).append("战斗中无法使用该道具。")
        return state
    inv = state.setdefault("inventory", [])
    idx = None
    for i, it in enumerate(inv):
        if it.get("item_id") == item_id and int(it.get("qty", 0) or 0) > 0:
            idx = i
            break
    if idx is None:
        state.setdefault("meta", {}).setdefault("log", []).append("未找到可用的天赋宝珠。")
        return state
    it = inv[idx]
    meta = it.get("meta") or {}
    if str(meta.get("kind", "")) != "talent_respec_orb":
        state.setdefault("meta", {}).setdefault("log", []).append("该物品不是天赋宝珠。")
        return state

    who = str(target or "hero").strip() or "hero"

    def _consume_orb() -> None:
        it["qty"] = int(it.get("qty", 1) or 1) - 1
        if int(it.get("qty", 0) or 0) <= 0:
            inv.pop(idx)
        state["inventory"] = inv

    if who == "hero":
        lv = int(state.get("level", 1) or 1)
        role = str(state.get("role", "warrior"))
        eligible = [tl for tl in TALENT_LEVELS if lv >= int(tl)]
        if not eligible:
            state.setdefault("meta", {}).setdefault("log", []).append(
                "主角尚未解锁任何天赋档位（需达到 Lv10），天赋宝珠未消耗。"
            )
            return state
        _purge_pending_talent_entries_for_target(state, is_player=True)
        state["talents"] = []
        state["talent_picked"] = {}
        _recalc_player_from_equipment(state)
        for tl in eligible:
            _queue_talent_choice(
                state, target={"type": "player"}, role=role, level=int(tl), silent=True
            )
        _consume_orb()
        _queue_unlock_notice(
            state,
            "天赋重置",
            [f"{state.get('name', '主角')}（主角）的天赋已重置，请依次重新选择 Lv10/20/30 天赋。"],
        )
        state.setdefault("meta", {}).setdefault("log", []).append(
            f"🔮 使用天赋宝珠（主角）：已重置天赋，请完成天赋界面中的重新选择。"
        )
        return state

    member = None
    for m in state.get("party_members", []) or []:
        if str(m.get("mid", "")) == who:
            member = m
            break
    if not member:
        state.setdefault("meta", {}).setdefault("log", []).append("未找到该队友，宝珠未消耗。")
        return state
    lv_m = int(member.get("level", state.get("level", 1)) or 1)
    role_m = str(member.get("role", ""))
    eligible_m = [tl for tl in TALENT_LEVELS if lv_m >= int(tl)]
    if not eligible_m:
        state.setdefault("meta", {}).setdefault("log", []).append(
            f"{member.get('name', '队友')} 尚未解锁任何天赋档位（需达到 Lv10），天赋宝珠未消耗。"
        )
        return state
    _purge_pending_talent_entries_for_target(state, is_player=False, mid=str(member.get("mid", "")))
    member["talents"] = []
    member["talent_picked"] = {}
    _recalc_member_stats(member, lv_m, state.get("party_armory"), state.get("resources"))
    nm = str(member.get("name", "队友"))
    for tl in eligible_m:
        _queue_talent_choice(
            state,
            target={"type": "member", "mid": str(member.get("mid", ""))},
            role=role_m,
            level=int(tl),
            silent=True,
        )
    _consume_orb()
    _queue_unlock_notice(
        state,
        "天赋重置",
        [f"{nm} 的天赋已重置，请依次重新选择 Lv10/20/30 天赋。"],
    )
    state.setdefault("meta", {}).setdefault("log", []).append(f"🔮 使用天赋宝珠（{nm}）：已重置天赋，请完成天赋界面中的重新选择。")
    return state


def _new_id(prefix: str, rng: random.Random) -> str:
    return f"{prefix}_{rng.randint(100000, 999999)}"


@dataclass
class Skill:
    sid: str
    name: str
    mp_cost: int
    kind: str  # "damage" | "double_slash" | "quick_stab_chain" | "drain" | "heal" | "buff" | "cover_party" | "war_cry" | "shield_counter"
    power: float
    accuracy: float


def _skill_catalog() -> Dict[str, Skill]:
    return {
        "atk": Skill("atk", "普攻", 0, "damage", power=1.0, accuracy=1.0),
        # 连斩：两段物攻，每段 power 倍率；每段独立 miss（在战斗中单独判定，不用 accuracy）
        "lianzhan": Skill("lianzhan", "连斩", 4, "double_slash", power=0.95, accuracy=1.0),
        # 盗贼：多段刺击（队友/未来主角共用数值常量）
        "quick_stab": Skill(
            "quick_stab",
            "快速刺击",
            ROGUE_MP_QUICK_STAB,
            "quick_stab_chain",
            power=QUICK_STAB_HIT_POWER,
            accuracy=1.0,
        ),
        # 战士成长技能（1/6/12/18/24/30）
        "heavy_strike": Skill("heavy_strike", "援护", 8, "cover_party", power=1.0, accuracy=1.0),
        "whirlwind": Skill("whirlwind", "旋风斩", 6, "damage", power=1.48, accuracy=0.88),
        "deep_cut": Skill("deep_cut", "深割", 7, "damage", power=1.78, accuracy=0.87),
        "armor_break": Skill("armor_break", "盾反", 8, "shield_counter", power=1.0, accuracy=1.0),
        "blood_rage": Skill("blood_rage", "嗜血", 9, "drain", power=1.88, accuracy=0.88),
        "execution": Skill("execution", "战吼", 12, "war_cry", power=1.0, accuracy=1.0),
        # 队友扩展技能
        "holy_heal": Skill("holy_heal", "圣疗", CLERIC_MP_HOLY_HEAL, "heal", power=1.0, accuracy=1.0),
        "group_prayer": Skill("group_prayer", "群体祈祷", CLERIC_MP_GROUP_PRAYER, "heal", power=1.0, accuracy=1.0),
        "judgement": Skill("judgement", "惩戒术", CLERIC_MP_JUDGEMENT, "damage", power=1.0, accuracy=1.0),
        "divine_bless": Skill("divine_bless", "圣光赐福", CLERIC_MP_DIVINE_BLESS, "buff", power=1.0, accuracy=1.0),
        "eagle_eye": Skill("eagle_eye", "鹰眼狙击", HUNTER_MP_EAGLE_EYE, "damage", power=HUNTER_EAGLE_EYE_POWER, accuracy=0.93),
        # 法师（主角/队友手动）：与 _allies_auto_action 法师分支同 MP 与倍率
        "arcane_bolt": Skill("arcane_bolt", "奥术冲击", MAGE_MP_ARCANE_BOLT, "damage", power=1.22, accuracy=1.0),
        "fire_blast": Skill("fire_blast", "爆炎术", MAGE_MP_FIRE_BLAST, "damage", power=MAGE_FIRE_BLAST_BASE_POWER, accuracy=1.0),
        "chain_lightning": Skill("chain_lightning", "连锁闪电", MAGE_MP_CHAIN_LIGHTNING, "damage", power=1.45, accuracy=1.0),
        "meteor": Skill("meteor", "陨星术", MAGE_MP_METEOR, "damage", power=1.75, accuracy=1.0),
        # 猎人 / 刺客（主角与 PVP 展示名；战斗结算走通用物伤分支时可再细化多段/溅射）
        "aim_shot": Skill("aim_shot", "瞄准射击", HUNTER_MP_AIM_SHOT, "damage", power=1.24, accuracy=1.0),
        "pierce_arrow": Skill("pierce_arrow", "穿透箭", HUNTER_MP_PIERCE_ARROW, "damage", power=1.30, accuracy=0.88),
        "volley": Skill("volley", "连射", HUNTER_MP_VOLLEY, "damage", power=HUNTER_VOLLEY_HIT_POWER, accuracy=0.85),
        "shadow_step": Skill("shadow_step", "影袭", ROGUE_MP_SHADOW_STEP, "damage", power=1.22, accuracy=0.88),
        "venom_edge": Skill("venom_edge", "毒刃", ROGUE_MP_VENOM_EDGE, "damage", power=1.32, accuracy=0.88),
        "assassinate": Skill("assassinate", "暗杀", ROGUE_MP_ASSASSINATE, "damage", power=1.48, accuracy=0.88),
    }


MAX_PLAYER_LEVEL = 30
MAX_PLAYER_SKILLS = 4
MAX_MEMBER_SKILLS = 4
LIANZHAN_MISS_PER_HIT = 0.10
BASE_HIT_RATE = 0.80
FULL_HIT_DEX_NEED = 20.0
ROLE_DEX_HIT_COEF: Dict[str, float] = {
    "warrior": 1.0,
    "cleric": 1.0,
    "mage": 1.0,
    "hunter": 1.0,
    "rogue": 1.0,
}


def _queue_unlock_notice(state: Dict[str, Any], title: str, lines: List[str]) -> None:
    meta = state.setdefault("meta", {})
    q = meta.get("pending_unlock_notice_queue")
    if not isinstance(q, list):
        q = []
    q.append({"title": str(title or "成长提示"), "lines": [str(x) for x in (lines or []) if str(x).strip()]})
    meta["pending_unlock_notice_queue"] = q


def dq_has_blocking_modal_notice(state: Dict[str, Any]) -> bool:
    """前端 Streamlit 同一时刻只能开一个 dialog：掉落/成长/天赋等未确认提示视为占用。"""
    meta = (state or {}).get("meta") or {}
    if isinstance(meta.get("pending_clue_quiz_feedback"), dict):
        return True
    q = meta.get("pending_unlock_notice_queue")
    if isinstance(q, list) and len(q) > 0:
        return True
    if isinstance(meta.get("pending_talent"), dict):
        return True
    if isinstance(meta.get("pending_skill_replace"), dict):
        return True
    return False


def dq_ack_unlock_notice(state: Dict[str, Any]) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    meta = state.setdefault("meta", {})
    q = meta.get("pending_unlock_notice_queue")
    if not isinstance(q, list) or not q:
        meta["pending_unlock_notice_queue"] = []
        q = []
    else:
        q = q[1:]
        meta["pending_unlock_notice_queue"] = q
    qtm = meta.get("q1_post_act1_tutorial")
    if isinstance(qtm, dict) and bool(qtm.get("active")) and not q:
        if str(qtm.get("focus", "")) == "drop_notice":
            qtm["focus"] = "backpack_tab"
    return state


def _collect_rare_drop_names(items: List[Dict[str, Any]]) -> List[str]:
    """战斗/探索中需弹窗提示的稀有掉落：装备、复活药水、Q2+ 稀有药水（满血/满蓝/金苹果）。"""
    out: List[str] = []
    for it in (items or []):
        if not isinstance(it, dict):
            continue
        meta = it.get("meta") or {}
        use = str(meta.get("use", ""))
        slot = str(meta.get("slot", ""))
        is_equip = slot in EQUIPMENT_SLOTS
        is_revive = use == "revive_potion"
        is_rare_pot = use in ("full_heal_potion", "full_mp_potion", "golden_apple")
        if not (is_equip or is_revive or is_rare_pot):
            continue
        nm = str(it.get("name", "稀有掉落"))
        if is_equip:
            line = nm
        elif use == "full_heal_potion":
            pct = max(1, min(100, int(meta.get("heal_pct", POTION_FULL_HP_PCT))))
            line = f"{nm}（最大HP×{pct}%）"
        elif use == "full_mp_potion":
            pct = max(1, min(100, int(meta.get("mp_pct", POTION_FULL_MP_PCT))))
            line = f"{nm}（最大MP×{pct}%）"
        elif use == "golden_apple":
            line = f"{nm}（HP+MP 全满）"
        elif use == "revive_potion":
            rh = max(1, min(100, int(meta.get("revive_hp_pct", POTION_REVIVE_HP_PCT))))
            rm = max(1, min(100, int(meta.get("revive_mp_pct", POTION_REVIVE_MP_PCT))))
            line = f"{nm}（复活：HP×{rh}% + MP×{rm}%）"
        else:
            line = nm
        if line and line not in out:
            out.append(line)
    return out


def _queue_skill_replace(state: Dict[str, Any], target: Dict[str, Any], sid: str, name: str) -> None:
    meta = state.setdefault("meta", {})
    q = meta.get("pending_skill_replace_queue")
    if not isinstance(q, list):
        q = []
    entry = {"target": target or {"type": "player"}, "new": sid, "name": name}
    if not any(
        isinstance(x, dict)
        and x.get("new") == sid
        and isinstance(x.get("target"), dict)
        and x.get("target", {}).get("type") == entry["target"].get("type")
        and x.get("target", {}).get("mid") == entry["target"].get("mid")
        for x in q
    ):
        q.append(entry)
    meta["pending_skill_replace_queue"] = q
    if not isinstance(meta.get("pending_skill_replace"), dict):
        meta["pending_skill_replace"] = q[0] if q else None


def _try_grant_skill(player: Dict[str, Any], sid: str, learned: List[str], logs: List[str]) -> None:
    """主角习得技能；已满上限则进入替换队列。"""
    if sid not in _skill_catalog():
        return
    if sid in player["skills"]:
        return
    sk = _skill_catalog()[sid]
    if len(player["skills"]) < MAX_PLAYER_SKILLS:
        player["skills"].append(sid)
        learned.append(sk.name)
        logs.append(f"📘 习得新技能：{sk.name}")
        return
    _queue_skill_replace(player, {"type": "player"}, sid, sk.name)
    q = player.get("meta", {}).get("pending_skill_replace_queue") or []
    logs.append(
        f"📖 可习得「{sk.name}」，技能栏已满（最多 {MAX_PLAYER_SKILLS} 个），请在界面选择要替换的技能。"
        + (f"（另有 {len(q) - 1} 个技能在排队）" if len(q) > 1 else "")
    )


def dq_resolve_skill_replace(state: Dict[str, Any], remove_sid: str) -> Dict[str, Any]:
    """用 pending 队列队首的新技能替换 remove_sid（支持主角与队友）。"""
    state = copy.deepcopy(state)
    meta = state.setdefault("meta", {})
    pending = meta.get("pending_skill_replace")
    if not pending or not isinstance(pending, dict):
        return state
    new_sid = pending.get("new")
    if not new_sid or new_sid not in _skill_catalog():
        meta["pending_skill_replace"] = None
        meta["pending_skill_replace_queue"] = []
        return state
    tgt = pending.get("target") or {"type": "player"}
    target_skills: List[str]
    target_name = str(state.get("name", "主角"))
    if str(tgt.get("type", "player")) == "member":
        mid = str(tgt.get("mid", ""))
        mem = next((m for m in (state.get("party_members") or []) if str(m.get("mid", "")) == mid), None)
        if not isinstance(mem, dict):
            raise ValueError("队友不存在，无法完成技能替换")
        target_skills = list(mem.get("skills") or [])
        target_name = str(mem.get("name", "队友"))
        if new_sid in target_skills:
            pass
        elif remove_sid not in target_skills or remove_sid == new_sid:
            raise ValueError("请选择一个当前已装备的队友技能进行替换")
        else:
            mem["skills"] = [s for s in target_skills if s != remove_sid] + [new_sid]
    else:
        target_skills = list(state.get("skills") or [])
        if new_sid in target_skills:
            pass
        elif remove_sid not in target_skills or remove_sid == new_sid:
            raise ValueError("请选择一个当前已装备的技能进行替换")
        else:
            state["skills"] = [s for s in target_skills if s != remove_sid] + [new_sid]
    old_nm = _skill_catalog().get(remove_sid, Skill(remove_sid, remove_sid, 0, "damage", 1.0, 1.0)).name
    new_nm = _skill_catalog()[new_sid].name
    meta.setdefault("log", []).append(f"技能替换（{target_name}）：「{old_nm}」→「{new_nm}」。")

    q = meta.get("pending_skill_replace_queue")
    if not isinstance(q, list):
        q = []
    if q and isinstance(q[0], dict) and q[0].get("new") == new_sid and q[0].get("target") == tgt:
        q = q[1:]
    else:
        q = [
            x
            for x in q
            if not (
                isinstance(x, dict)
                and x.get("new") == new_sid
                and isinstance(x.get("target"), dict)
                and x.get("target", {}).get("type") == str(tgt.get("type", "player"))
                and x.get("target", {}).get("mid") == str(tgt.get("mid", ""))
            )
        ]
    meta["pending_skill_replace_queue"] = q
    meta["pending_skill_replace"] = q[0] if q else None
    return state


def dq_skip_skill_replace(state: Dict[str, Any]) -> Dict[str, Any]:
    """跳过当前队首待替换技能（放弃习得该技能）。"""
    state = copy.deepcopy(state)
    meta = state.setdefault("meta", {})
    q = meta.get("pending_skill_replace_queue")
    if not isinstance(q, list) or not q:
        meta["pending_skill_replace_queue"] = []
        meta["pending_skill_replace"] = None
        return state
    cur = q.pop(0)
    if isinstance(cur, dict):
        nm = str(cur.get("name", "未知技能"))
        tgt = cur.get("target") or {}
        who = "主角" if str(tgt.get("type", "player")) == "player" else str(tgt.get("name") or "队友")
        meta.setdefault("log", []).append(f"已放弃习得：{who} 的「{nm}」。")
    meta["pending_skill_replace_queue"] = q
    meta["pending_skill_replace"] = q[0] if q else None
    return state


def _zone_catalog() -> Dict[str, Dict[str, Any]]:
    # unlock_by 表示 boss_victories 需要达到多少
    return {
        "starter": {
            "id": "starter",
            "name": "破晓村与周边",
            "unlock_by": 0,
            "boss": None,
            "monsters": ["slime", "rat", "goblin"],
            "events": ["草药采集", "旧井传闻"],
        },
        "forest": {
            "id": "forest",
            "name": "诅咒森林",
            "unlock_by": 99,
            "boss": "boss_witherling",
            "monsters": ["bog_worm", "wither_vine", "sprite"],
            "events": ["灵体低语", "被困的商队"],
        },
        "mines": {
            "id": "mines",
            "name": "遗忘矿坑",
            "unlock_by": 1,
            "boss": "boss_golem",
            "monsters": ["skeleton", "miner_golem", "mine_spider"],
            "events": ["裂缝的回声", "黑市旧商柜"],
        },
        "coast": {
            "id": "coast",
            "name": "幽影海岸",
            "unlock_by": 2,
            "boss": "boss_sea_witch",
            "monsters": ["wraith", "sea_curse", "reef_crab"],
            "events": ["潮汐诅咒", "海鸥带来的信"],
        },
        "throne": {
            "id": "throne",
            "name": "王座地牢",
            "unlock_by": 3,
            "boss": "boss_throne_guard",
            "monsters": ["night_moth", "throne_guard", "witherling"],
            "events": ["王座的回音", "守门者的考题"],
        },
        "infinite": {
            "id": "infinite",
            "name": "无限地牢（无尽挑战）",
            "unlock_by": 0,
            "boss": None,
            "monsters": [],
            "events": ["未知来路", "深处的风声"],
        },
    }


def _monster_catalog() -> Dict[str, Dict[str, Any]]:
    # stats scale by floor/level
    return {
        "slime": {"name": "史莱姆", "hp": (22, 38), "atk": (5, 8), "def": (1, 3), "agi": (4, 7), "mp": 0},
        "rat": {"name": "污水鼠", "hp": (18, 30), "atk": (6, 10), "def": (1, 3), "agi": (8, 12), "mp": 0},
        "goblin": {"name": "地精", "hp": (28, 55), "atk": (9, 14), "def": (2, 5), "agi": (6, 10), "mp": (4, 11)},
        "witherling": {"name": "枯萎精灵", "hp": (30, 62), "atk": (10, 16), "def": (2, 6), "agi": (7, 12), "mp": (8, 14)},
        "sprite": {"name": "野灵", "hp": (26, 50), "atk": (10, 15), "def": (2, 5), "agi": (9, 15), "mp": (6, 12)},
        "skeleton": {"name": "骨骸兵", "hp": (35, 70), "atk": (12, 19), "def": (3, 7), "agi": (6, 10), "mp": 0},
        "miner_golem": {"name": "矿坑傀儡", "hp": (70, 120), "atk": (16, 24), "def": (6, 12), "agi": (4, 7), "mp": (6, 14)},
        "wraith": {"name": "幽魂", "hp": (45, 85), "atk": (13, 21), "def": (3, 7), "agi": (7, 12), "mp": (10, 18)},
        "sea_curse": {"name": "海祸咒灵", "hp": (55, 100), "atk": (14, 23), "def": (3, 8), "agi": (6, 12), "mp": (14, 22)},
        # Q2 森林替代：腐沼蠕虫 / 枯藤妖（数值略高于原 Q1 地精、原枯萎精灵）
        "bog_worm": {"name": "腐沼蠕虫", "hp": (34, 62), "atk": (11, 17), "def": (3, 6), "agi": (7, 11), "mp": 0},
        "wither_vine": {"name": "枯藤妖", "hp": (36, 70), "atk": (11, 18), "def": (3, 7), "agi": (8, 13), "mp": (9, 15)},
        # Q3 矿坑：矿穴魔蛛（原幽魂位，偏物理与敏捷）
        "mine_spider": {"name": "矿穴魔蛛", "hp": (50, 92), "atk": (14, 22), "def": (4, 9), "agi": (8, 13), "mp": (8, 14)},
        # Q4 海岸：暗礁鬼蟹（原骨骸兵位，偏防御）
        "reef_crab": {"name": "暗礁鬼蟹", "hp": (62, 110), "atk": (13, 22), "def": (5, 11), "agi": (5, 10), "mp": 0},
        # Q5 王座：暗夜飞蛾（原海祸咒灵位，偏法伤与 MP）
        "night_moth": {"name": "暗夜飞蛾", "hp": (66, 118), "atk": (15, 25), "def": (4, 9), "agi": (9, 15), "mp": (16, 24)},
        "throne_guard": {"name": "王座卫兵", "hp": (90, 160), "atk": (18, 30), "def": (6, 13), "agi": (5, 10), "mp": (8, 16)},
        # bosses
        "boss_witherling": {"name": "枯萎之王", "hp": (220, 360), "atk": (28, 46), "def": (10, 20), "agi": (8, 16), "mp": (60, 90)},
        "boss_golem": {"name": "熔岩巨像", "hp": (260, 420), "atk": (32, 54), "def": (14, 26), "agi": (5, 12), "mp": 0},
        "boss_sea_witch": {"name": "潮汐女巫", "hp": (240, 390), "atk": (24, 40), "def": (8, 18), "agi": (10, 18), "mp": (70, 110)},
        "boss_throne_guard": {"name": "王座守卫", "hp": (320, 520), "atk": (30, 54), "def": (13, 26), "agi": (8, 16), "mp": 0},
    }


def _make_player(name: str, rng_seed: int, hero_gender: str = "男") -> Dict[str, Any]:
    rng = random.Random(rng_seed)
    hg = str(hero_gender or "男").strip()
    if hg not in ("男", "女"):
        hg = "男"
    p: Dict[str, Any] = {
        "name": name.strip()[:20] if name else "勇者",
        # 主角职业：当前版本固定为「战士」，其它职业来自招募伙伴
        "role": "warrior",
        # 主角性别（仅影响前端 img/战士_男|战士_女 等立绘）
        "hero_gender": hg,
        "v": 1,
        "seed": rng_seed,
        "rng_state": None,  # 这里不用手动序列化 RNG，靠存档种子 + 事件记录仍可复现大部分体验
        "level": 1,
        "exp": 0,
        "exp_to_next": 80,
        # hp/mp/atk/def/agi 由六维属性计算后写入
        "hp": 0,
        "max_hp": 0,
        "mp": 0,
        "max_mp": 0,
        "atk": 0,
        "def": 0,
        "mdef": 0,
        "agi": 0,
        "attrs": {
            "str": 1,
            "int": 1,
            "dex": 1,
            "agi": 1,
            "luk": 1,
            "vit": 1,
        },
        "pending_stat_points": INITIAL_ABILITY_POINTS,
        "gold": 800,
        "stamina": DEFAULT_MAX_STAMINA,
        "max_stamina": DEFAULT_MAX_STAMINA,
        "equipped": {
            "weapon": None,
            "shield": None,
            "helmet": None,
            "mail": None,
            "belt": None,
            "accessory": None,
        },
        "inventory": [],  # {item_id, name, qty, meta}
        "materials": [],  # {mid, name, qty}
        # 队伍新增成员（不含主角）；战斗与培养系统会用到
        # 成员结构：{mid, name, role, level, attrs, pending_stat_points, hp, max_hp, mp, max_mp, atk, def, agi}
        "party_members": [],
        # 队伍职业武器库：{role: {name,tier,int_bonus,dex_bonus,agi_bonus,atk_bonus,spell_bonus,heal_bonus}}
        "party_armory": {},
        "skills": ["lianzhan"],
        # 天赋树（10/20/30级 2选1）
        "talents": [],
        "talent_picked": {},
        "boss_victories": 0,
        "unlocked_zones": ["starter"],
        "location": "starter",
        "phase": "overworld",  # overworld | battle | gameover
        "encounter": None,  # enemy dict when battle
        "battle": None,
        "quest": {
            "chapter": 0,
            "quests": [
                {"qid": "q1", "title": "破晓之誓", "desc": "在破晓村周边找到并说服第一位同伴加入队伍。", "need": 1, "progress": 0, "done": False},
                {"qid": "q2", "title": "森林的回声", "desc": "击败枯萎之王，阻止瘴气扩散。", "need": 1, "progress": 0, "done": False},
                {"qid": "q3", "title": "矿坑的裂纹", "desc": "收集灵矿并击败熔岩巨像。", "need": 1, "progress": 0, "done": False},
                {"qid": "q4", "title": "潮汐的代价", "desc": "击败潮汐女巫，并带回潮汐之钥。", "need": 1, "progress": 0, "done": False},
                {"qid": "q5", "title": "王座的挑战", "desc": "击败王座守卫，夺回勇者之章。", "need": 1, "progress": 0, "done": False},
            ],
        },
        "story_flags": {
            "artifacts": {
                "seal": False,
                "ore": False,
                "key": False,
                "chapter": False,
            }
        },
        "meta": {
            "log": [],
            "battle_log": [],
            "turn": 0,
        },
        "resources": {
            "clue": 0,  # 关键线索（唯一收集项数量）
            "clues_found": [],  # 已发现线索 id（去重）
            "clue_effect_maps": [],  # 已触发“每图集齐3条”特效的地图 id
            "clue_quiz_scores": {},  # 线索 id -> 领悟分 0/1/3（每条仅一次）
        },
        "dungeon": {
            "mode": "infinite",
            "floor": 1,
            "wins": 0,
            "last_boss_at": None,
        },
        "status_effects": [],  # player effects
        "defend_turn": False,
    }
    _ensure_attrs(p)
    _apply_attrs_to_base(p)
    _recalc_player_from_equipment(p)
    p["hp"] = int(p["max_hp"])
    p["mp"] = int(p["max_mp"])
    _clamp_player_level(p)
    return p


def _party_size(state: Dict[str, Any]) -> int:
    return 1 + len(state.get("party_members", []) or [])


def dq_inn_cost(state: Dict[str, Any]) -> int:
    """旅店费用：每个成员 30 金币（含主角）。"""
    return int(INN_COST_PER_MEMBER) * int(_party_size(state))


def _member_initial_pending_points(level: int) -> int:
    # 与主角的成长一致：开局 INITIAL_ABILITY_POINTS + (level-1) * STAT_POINTS_PER_LEVEL
    lv = max(1, int(level or 1))
    return int(INITIAL_ABILITY_POINTS + (lv - 1) * STAT_POINTS_PER_LEVEL)


def _member_base_attrs(role: str) -> Dict[str, int]:
    """队友初始六维：统一全 1。职业差异仅体现在成长权重。"""
    return {"str": 1, "int": 1, "dex": 1, "agi": 1, "luk": 1, "vit": 1}


def _member_role_attr_mult(role: str) -> Dict[str, float]:
    """队友职业成长权重（同样的加点在不同职业上体感不同）。"""
    role = str(role or "")
    table: Dict[str, Dict[str, float]] = {
        "warrior": {"str": 1.22, "int": 1.00, "dex": 1.00, "agi": 0.86, "luk": 0.86, "vit": 1.22},
        "cleric": {"str": 0.85, "int": 1.22, "dex": 1.00, "agi": 1.00, "luk": 1.18, "vit": 0.85},
        "mage": {"str": 0.84, "int": 1.24, "dex": 1.00, "agi": 1.16, "luk": 1.00, "vit": 0.84},
        "hunter": {"str": 1.00, "int": 0.85, "dex": 1.22, "agi": 1.22, "luk": 1.00, "vit": 0.85},
        "rogue": {"str": 1.18, "int": 0.84, "dex": 1.00, "agi": 1.22, "luk": 1.00, "vit": 0.84},
    }
    return dict(table.get(role, {"str": 1.0, "int": 1.0, "dex": 1.0, "agi": 1.0, "luk": 1.0, "vit": 1.0}))


def _normalize_member_pending_points(member: Dict[str, Any], owner_level: int) -> None:
    """
    修正队友能力点：按“累计应得 - 已分配”重新计算 pending_stat_points。
    例如 Lv3 且未分配时：5 + 2*(3-1) = 9 点。
    """
    lv = max(1, int(owner_level or member.get("level", 1) or 1))
    member["level"] = lv
    attrs = member.get("attrs") or {}
    base_attrs = _member_base_attrs(str(member.get("role", "")))
    spent = 0
    for k in ATTR_KEYS:
        base_v = int(base_attrs.get(k, 1) or 1)
        spent += max(0, int(attrs.get(k, base_v) or base_v) - base_v)
    total = _member_initial_pending_points(lv)
    member["pending_stat_points"] = max(0, int(total - spent))


def _member_role_config() -> Dict[str, Dict[str, Any]]:
    # role 只用于战斗 AI / 技能权重；具体加点由 attrs 决定
    return {
        "cleric": {"name": "黄晓茹", "tag": "牧师", "focus": "int_heal"},
        "mage": {"name": "王曦媛", "tag": "法师", "focus": "int_damage"},
        "hunter": {"name": "朱齐旻", "tag": "猎人", "focus": "dex_atk"},
        "rogue": {"name": "田可园", "tag": "盗贼", "focus": "agi_atk"},
    }


def _member_skill_table() -> Dict[str, List[Tuple[int, str]]]:
    return {
        "cleric": [(1, "holy_heal"), (9, "judgement"), (18, "group_prayer"), (27, "divine_bless")],
        "mage": [(1, "arcane_bolt"), (9, "fire_blast"), (18, "chain_lightning"), (27, "meteor")],
        "hunter": [(1, "aim_shot"), (9, "pierce_arrow"), (18, "volley"), (27, "eagle_eye")],
        "rogue": [(1, "quick_stab"), (9, "shadow_step"), (18, "venom_edge"), (27, "assassinate")],
    }


def _sync_member_skills(state: Dict[str, Any], member: Dict[str, Any], logs: Optional[List[str]] = None) -> None:
    role = str(member.get("role", ""))
    lv = max(1, int(member.get("level", 1) or 1))
    old_skills = [str(s) for s in (member.get("skills") or []) if s]
    unlocked: List[str] = [sid for need_lv, sid in _member_skill_table().get(role, []) if lv >= need_lv]
    member["skills"] = unlocked[:MAX_MEMBER_SKILLS]
    learned_names: List[str] = []
    for sid in member["skills"]:
        if sid not in old_skills:
            learned_names.append(_skill_catalog().get(sid, Skill(sid, sid, 0, "damage", 1.0, 1.0)).name)
    if logs is not None and learned_names:
        nm = member.get("name", "队友")
        logs.append(f"✨ 队友成长：{nm} 学会了 " + "、".join(learned_names))
    if learned_names:
        _queue_unlock_notice(state, f"{member.get('name', '队友')} 技能成长", [f"新技能：{x}" for x in learned_names])


def _recalc_member_stats(
    member: Dict[str, Any],
    level: int,
    party_armory: Optional[Dict[str, Any]] = None,
    resources: Optional[Dict[str, Any]] = None,
) -> None:
    # 复用主角同一套六维公式；成员可穿戴装备（武器带职业署名限制）
    _ensure_member_attrs(member)
    attrs = member.get("attrs") or {}
    role = str(member.get("role", ""))
    grow = _member_role_attr_mult(role)
    eq_bonus = _compute_equip_attr_bonus(member.get("equipped") or {})
    talent_f = _talent_flat_attr_bonus(list(member.get("talents") or []))
    arm_early = (party_armory or {}).get(str(member.get("role", ""))) if isinstance(party_armory, dict) else None
    dex_arm_early = int(arm_early.get("dex_bonus", 0) or 0) if isinstance(arm_early, dict) else 0
    luk_attr = int(attrs.get("luk", 1) or 1) + int(eq_bonus.get("luk", 0) or 0)
    s_raw = int(attrs.get("str", 1) or 1) + int(eq_bonus.get("str", 0) or 0)
    i_raw = int(attrs.get("int", 1) or 1) + int(eq_bonus.get("int", 0) or 0)
    agi_raw = int(attrs.get("agi", 1) or 1) + int(eq_bonus.get("agi", 0) or 0)
    df_raw = int(attrs.get("vit", 1) or 1) + int(eq_bonus.get("vit", 0) or 0)
    dex_raw = int(attrs.get("dex", 1) or 1) + int(eq_bonus.get("dex", 0) or 0)
    if role == "hunter":
        # 与 dq_unit_hexagon_parts 的 DEX 合计一致（军械整段 DEX 参与成长×1.28，不再仅 0.35 折算）
        dex_raw = dex_raw + dex_arm_early + int(talent_f.get("dex", 0) or 0)
    s = max(1, int(s_raw * float(grow.get("str", 1.0) or 1.0)))
    i = max(1, int(i_raw * float(grow.get("int", 1.0) or 1.0)))
    agi = max(1, int(agi_raw * float(grow.get("agi", 1.0) or 1.0)))
    df = max(1, int(df_raw * float(grow.get("vit", 1.0) or 1.0)))
    dex_attr = max(1, int(dex_raw * float(grow.get("dex", 1.0) or 1.0)))
    luk_eff = max(1, int(luk_attr * float(grow.get("luk", 1.0) or 1.0)))
    lv = max(1, int(level or member.get("level", 1) or 1))

    if role == "hunter":
        base_atk = max(3, int(3 + dex_attr * float(HUNTER_DEX_ATK_MULT) + lv * 0.6))
        base_def = max(2, int(2 + df * float(HUNTER_DEF_PANEL_MULT) + lv * 0.45))
    elif role == "rogue":
        base_atk = max(3, int(3 + s * float(ROGUE_STR_ATK_MULT) + lv * 0.6))
        base_def = max(2, int(2 + df * 0.95 + lv * 0.45))
    else:
        base_atk = max(3, int(3 + s * 1.35 + lv * 0.6))
        base_def = max(2, int(2 + df * 0.95 + lv * 0.45))
    base_agi = max(4, int(4 + agi * 1.05 + luk_eff * 0.08 + lv * 0.25))
    hp_def_coef = _hp_def_coef_by_role(role)
    base_max_hp = max(20, int(20 + df * hp_def_coef + lv * 4))  # 体质 -> HP（按职业系数）
    base_max_mp = max(8, int(8 + i * 4 + lv * 2))
    base_mdef = max(1, int(1 + i * 0.95 + df * 0.28 + lv * 0.40))

    # 职业武器加成
    arm = (party_armory or {}).get(str(member.get("role", ""))) if isinstance(party_armory, dict) else None
    if isinstance(arm, dict):
        arm_str = int(arm.get("str_bonus", 0) or 0)
        dex_arm = int(arm.get("dex_bonus", 0) or 0)
        base_atk = int(base_atk * (1.0 + float(arm.get("atk_bonus", 0.0) or 0.0)))
        if role == "hunter":
            base_atk += int(arm_str * float(HUNTER_STR_ARMORY_ATK_MULT))
        elif role == "rogue":
            base_atk += int(arm_str * float(ROGUE_STR_ATK_MULT))
        else:
            base_atk += int(arm_str * 1.35)
            dex_eff_non = dex_attr + dex_arm
            base_atk += int(dex_eff_non * 0.35)
        base_max_hp = int(base_max_hp * (1.0 + float(arm.get("hp_bonus", 0.0) or 0.0)))
        base_max_mp = int(base_max_mp * (1.0 + float(arm.get("mp_bonus", 0.0) or 0.0)))
        base_agi += int(arm.get("agi_bonus", 0) or 0)
        i += int(arm.get("int_bonus", 0) or 0)
        # 猎人：dex_raw 已含军械 DEX，dex_attr 勿再加 dex_arm，避免 _dex_eff 重复计数
        if role == "hunter":
            dex_eff = int(dex_attr)
        else:
            dex_eff = int(dex_attr + dex_arm)
        base_max_mp += int(i * 0.6)
        member["_dex_eff"] = dex_eff
    else:
        member["_dex_eff"] = int(dex_attr)

    if role == "rogue":
        ea_rg = _effective_attrs_party_member(member, party_armory)
        agi_eff_r = int(ea_rg.get("agi", 0) or 0)
        base_atk = max(3, int(base_atk) + int(agi_eff_r * float(ROGUE_AGI_ATK_BONUS_MULT)))

    clue_hp_pct = float((resources or {}).get("clue_bonus_hp_pct", 0.0) or 0.0)
    if clue_hp_pct > 0:
        base_max_hp = max(20, int(base_max_hp * (1.0 + clue_hp_pct)))

    member["atk"] = base_atk
    member["def"] = base_def
    member["mdef"] = base_mdef
    member["agi"] = base_agi
    member["max_hp"] = base_max_hp
    member["max_mp"] = base_max_mp
    hp_cur = member.get("hp", base_max_hp)
    mp_cur = member.get("mp", base_max_mp)
    member["hp"] = min(int(base_max_hp if hp_cur is None else hp_cur), base_max_hp)
    member["mp"] = min(int(base_max_mp if mp_cur is None else mp_cur), base_max_mp)


def _add_recruit_member(state: Dict[str, Any], role: str) -> None:
    """
    招募成员：加入队伍、与主角同等级、生成可分配点数。
    选择后立即回满 HP/MP，便于玩家继续推进剧情。
    """
    role = str(role or "")
    cfg = _member_role_config().get(role)
    if not cfg:
        return
    level = int(state.get("level", 1) or 1)
    members = state.setdefault("party_members", [])
    # 已招募则跳过（允许同存档重复触发时避免重复添加）
    for m in members:
        if m.get("role") == role:
            return

    pending = _member_initial_pending_points(level)
    member = {
        "mid": f"mem_{role}",
        "name": cfg["name"],
        "role": role,
        "level": level,
        "attrs": _member_base_attrs(role),
        "pending_stat_points": pending,
        # 成员天赋树（10/20/30级 2选1）
        "talents": [],
        "talent_picked": {},
        # 成员装备（当前版本只要求支持武器专属）
        "equipped": {s: None for s in EQUIPMENT_SLOTS},
        "hp": 0,
        "max_hp": 0,
        "mp": 0,
        "max_mp": 0,
        "atk": 0,
        "def": 0,
        "mdef": 0,
        "agi": 0,
        "skills": [],
    }
    _sync_member_skills(state, member)
    _recalc_member_stats(member, level, state.get("party_armory"), state.get("resources"))
    member["hp"] = int(member.get("max_hp", 1))
    member["mp"] = int(member.get("max_mp", 0) or 0)
    members.append(member)
    state.setdefault("meta", {}).setdefault("log", []).append(f"🤝 新队员加入：{cfg['tag']} {member['name']}（Lv{level}）！")
    # 高等级招募时，补齐所有已达成但尚未选择的天赋档位（10/20/30）
    cur_lv = int(state.get("level", level) or level)
    for tl in TALENT_LEVELS:
        if cur_lv >= int(tl):
            _queue_talent_choice(
                state,
                target={"type": "member", "mid": str(member.get("mid", ""))},
                role=str(role),
                level=int(tl),
            )


def _player_level_curve(level: int) -> Tuple[int, int]:
    # exp needed roughly quadratic
    exp = 70 + (level - 1) * (level - 1) * 18
    return exp, exp


# 战士主角：在 1/6/12/18/24/30 习得技能
WARRIOR_SKILL_BY_LEVEL: Dict[int, str] = {
    1: "lianzhan",
    6: "heavy_strike",
    12: "whirlwind",
    18: "deep_cut",
    24: "armor_break",
    30: "execution",
}


# ====== 天赋树（10/20/30级 2选1）======
TALENT_LEVELS: Tuple[int, ...] = (10, 20, 30)
ROLE_CN: Dict[str, str] = {"warrior": "战士", "cleric": "牧师", "mage": "法师", "hunter": "猎人", "rogue": "刺客"}

TALENT_CHOICE_DEFS: Dict[str, Dict[str, Any]] = {
    # 战士
    "warrior_t10_a": {"role": "warrior", "level": 10, "label": "破锋：物理伤害+8%", "effects": {"phys_dmg_bonus": 0.08}},
    "warrior_t10_b": {"role": "warrior", "level": 10, "label": "坚壁：闪避+10%", "effects": {"eva_bonus": 0.10}},
    "warrior_t20_a": {"role": "warrior", "level": 20, "label": "铁骨：承伤-10%", "effects": {"received_mult": 0.90}},
    "warrior_t20_b": {"role": "warrior", "level": 20, "label": "破空：暴击率+10%", "effects": {"crit_bonus": 0.10}},
    "warrior_t30_a": {"role": "warrior", "level": 30, "label": "无畏：血量低于20%时攻击力+20%", "effects": {"low_hp_atk_bonus": 0.20}},
    "warrior_t30_b": {"role": "warrior", "level": 30, "label": "守天：闪避后回复20%生命", "effects": {"dodge_heal_pct": 0.20}},
    # 牧师
    "cleric_t10_a": {"role": "cleric", "level": 10, "label": "圣意：治疗+20%", "effects": {"heal_bonus": 0.20}},
    "cleric_t10_b": {"role": "cleric", "level": 10, "label": "净流：治疗时净化异常（25%）", "effects": {"heal_purify_chance": 0.25}},
    "cleric_t20_a": {"role": "cleric", "level": 20, "label": "神罚：惩戒术伤害+20%", "effects": {"judgement_power_bonus": 0.20}},
    "cleric_t20_b": {
        "role": "cleric",
        "level": 20,
        "label": "同祈：过量治疗30%转为惩戒，随机打击敌人",
        "effects": {"overheal_smite_ratio": 0.30},
    },
    "cleric_t30_a": {"role": "cleric", "level": 30, "label": "赐福：群体祈祷改为必触发", "effects": {"group_prayer_force": 1.0}},
    "cleric_t30_b": {"role": "cleric", "level": 30, "label": "光辉：惩戒术暴击+少许", "effects": {"judgement_crit_bonus": 0.04}},
    # 法师
    "mage_t10_a": {"role": "mage", "level": 10, "label": "寒焰：爆炎术更强", "effects": {"fire_power_bonus": 0.25}},
    "mage_t10_b": {"role": "mage", "level": 10, "label": "灵闪：5%概率连续释放2次奥术冲击", "effects": {"arcane_double_chance": 0.05}},
    "mage_t20_a": {"role": "mage", "level": 20, "label": "专注：法术伤害+8%", "effects": {"spell_power_bonus": 0.08}},
    "mage_t20_b": {
        "role": "mage",
        "level": 20,
        "label": "雷链：连锁闪电伤害-10%、弹射+1",
        "effects": {"chain_lightning_damage_mult": 0.90, "chain_lightning_extra_hits": 1},
    },
    "mage_t30_a": {"role": "mage", "level": 30, "label": "彗核：陨星术威力+30%", "effects": {"meteor_power_bonus": 0.30}},
    "mage_t30_b": {"role": "mage", "level": 30, "label": "星盾：闪避+15%", "effects": {"eva_bonus": 0.15}},
    # 猎人
    "hunter_t10_a": {"role": "hunter", "level": 10, "label": "齐射：精准射击倍率+10%", "effects": {"aim_shot_power_bonus": 0.10}},
    "hunter_t10_b": {
        "role": "hunter",
        "level": 10,
        "label": "贯穿：穿透箭主箭+10%、溅射+5%",
        "effects": {"pierce_main_power_bonus": 0.10, "pierce_splash_power_bonus": 0.05},
    },
    "hunter_t20_a": {"role": "hunter", "level": 20, "label": "死眼：暴击率+15%", "effects": {"crit_bonus": 0.15}},
    "hunter_t20_b": {"role": "hunter", "level": 20, "label": "疾风：闪避+13%", "effects": {"eva_bonus": 0.13}},
    "hunter_t30_a": {
        "role": "hunter",
        "level": 30,
        "label": "重击：鹰眼倍率+10%、致盲概率+20%",
        "effects": {"eagle_eye_power_bonus": 0.10, "eagle_eye_blind_chance_bonus": 0.20},
    },
    "hunter_t30_b": {"role": "hunter", "level": 30, "label": "节制：连射每段暴击率+30%", "effects": {"volley_hit_crit_bonus": 0.30}},
    # 刺客
    "rogue_t10_a": {"role": "rogue", "level": 10, "label": "朦胧：高血量目标时影袭更强", "effects": {"shadow_high_hp_bonus": 0.20}},
    "rogue_t10_b": {"role": "rogue", "level": 10, "label": "连击：快速刺击连段更易触发", "effects": {"quick_stab_chain_bonus": 0.10}},
    "rogue_t20_a": {"role": "rogue", "level": 20, "label": "毒牙：流血伤害与持续强化", "effects": {"bleed_pct_flat": 0.05, "bleed_turns_bonus": 1}},
    "rogue_t20_b": {"role": "rogue", "level": 20, "label": "潜行：闪避+14%", "effects": {"eva_bonus": 0.14}},
    "rogue_t30_a": {
        "role": "rogue",
        "level": 30,
        "label": "致命：暗杀威力+5%，低血必杀+5%",
        "effects": {"assassinate_power_bonus": 0.05, "assassinate_execute_chance_bonus": 0.05},
    },
    "rogue_t30_b": {"role": "rogue", "level": 30, "label": "血誓：暴击率+12%", "effects": {"crit_bonus": 0.12}},
}


def _quick_stab_chain_probs_for_talents(talent_ids: Optional[List[str]]) -> Tuple[float, float, float]:
    bonus = 0.0
    for tid in talent_ids or []:
        if str(tid) == "rogue_t10_b":
            eff = (TALENT_CHOICE_DEFS.get("rogue_t10_b", {}) or {}).get("effects") or {}
            bonus = float(eff.get("quick_stab_chain_bonus", 0.0) or 0.0)
            break
    return tuple(min(1.0, float(p) + bonus) for p in QUICK_STAB_CHAIN_PROBS)


def _talent_combat_flat_bonuses(talent_ids: Optional[List[str]]) -> Dict[str, float]:
    """
    聚合天赋中与面板/承伤相关的比例加成（与 TALENT_CHOICE_DEFS.effects 键一致）。
    - eva_bonus / crit_bonus / mit_bonus / hit_bonus：同类相加
    - received_mult：同类相乘（如铁骨 0.9）
    """
    out = {"eva_bonus": 0.0, "crit_bonus": 0.0, "mit_bonus": 0.0, "hit_bonus": 0.0, "received_mult": 1.0}
    for tid in talent_ids or []:
        eff = (TALENT_CHOICE_DEFS.get(str(tid), {}) or {}).get("effects") or {}
        if not isinstance(eff, dict):
            continue
        for k in ("eva_bonus", "crit_bonus", "mit_bonus", "hit_bonus"):
            if k in eff:
                out[k] += float(eff.get(k, 0.0) or 0.0)
        if "received_mult" in eff:
            out["received_mult"] *= float(eff.get("received_mult", 1.0) or 1.0)
    return out


def dq_talent_choice_labels() -> Dict[str, str]:
    """前端：天赋选择 id -> 展示文案。"""
    return {k: str(v.get("label", k)) for k, v in TALENT_CHOICE_DEFS.items()}


def _talent_choice_ids(role: str, level: int) -> List[str]:
    role = str(role or "")
    level = int(level or 0)
    ids = [k for k, v in TALENT_CHOICE_DEFS.items() if v.get("role") == role and int(v.get("level", 0) or 0) == level]
    # 每个等级固定 2 个选项
    return sorted(ids)[:2]


def _purge_pending_talent_entries_for_target(state: Dict[str, Any], *, is_player: bool, mid: str = "") -> None:
    """移除待选天赋队列中与指定主角/队友相关的条目，并在必要时提升队列下一项为当前 pending。"""
    meta = state.setdefault("meta", {})

    def _matches_pending(p: Any) -> bool:
        if not isinstance(p, dict):
            return False
        t = p.get("target") or {}
        if is_player:
            return str(t.get("type", "")) == "player"
        return str(t.get("type", "")) == "member" and str(t.get("mid", "")) == str(mid)

    q_raw = meta.get("pending_talent_queue")
    q = [x for x in (q_raw if isinstance(q_raw, list) else []) if isinstance(x, dict) and not _matches_pending(x)]
    meta["pending_talent_queue"] = q
    cur = meta.get("pending_talent")
    if isinstance(cur, dict) and _matches_pending(cur):
        meta["pending_talent"] = None
    if not isinstance(meta.get("pending_talent"), dict) and q:
        meta["pending_talent"] = q.pop(0)
        meta["pending_talent_queue"] = q


def _queue_talent_choice(
    state: Dict[str, Any], target: Dict[str, Any], role: str, level: int, *, silent: bool = False
) -> None:
    meta = state.setdefault("meta", {})
    meta.setdefault("pending_talent_queue", [])
    queue: List[Dict[str, Any]] = meta["pending_talent_queue"]
    level = int(level or 0)

    # 已有选择则不再排队
    if target.get("type") == "player":
        picked = (state.get("talent_picked") or {}).get(str(level))
        if picked:
            return
    else:
        mid = str(target.get("mid", ""))
        mem = next((m for m in (state.get("party_members") or []) if str(m.get("mid", "")) == mid), None)
        if not mem:
            return
        picked = (mem.get("talent_picked") or {}).get(str(level))
        if picked:
            return

    cids = _talent_choice_ids(role, level)
    if len(cids) != 2:
        return
    # 已在当前待选/队列中则不重复排队（避免旧档迁移或重复触发导致弹窗堆叠）
    cur_pending = meta.get("pending_talent")
    if isinstance(cur_pending, dict):
        t0 = cur_pending.get("target") or {}
        if (
            str((t0 or {}).get("type", "")) == str(target.get("type", ""))
            and str((t0 or {}).get("mid", "")) == str(target.get("mid", ""))
            and int(cur_pending.get("level", 0) or 0) == level
        ):
            return
    for it in queue:
        if not isinstance(it, dict):
            continue
        t1 = it.get("target") or {}
        if (
            str((t1 or {}).get("type", "")) == str(target.get("type", ""))
            and str((t1 or {}).get("mid", "")) == str(target.get("mid", ""))
            and int(it.get("level", 0) or 0) == level
        ):
            return

    choices = {cid: str(TALENT_CHOICE_DEFS.get(cid, {}).get("label", cid)) for cid in cids}
    pending = {
        "target": target,
        "role": str(role),
        "level": level,
        "choices": choices,
        "title": f"{ROLE_CN.get(str(role), str(role))} 天赋树（Lv{level}）",
    }
    queue.append(pending)
    if not isinstance(meta.get("pending_talent"), dict) or meta.get("pending_talent") is None:
        meta["pending_talent"] = queue.pop(0)
    if not silent:
        who = (
            "主角"
            if target.get("type") == "player"
            else str((target or {}).get("name") or ROLE_CN.get(str(role), "队友"))
        )
        _queue_unlock_notice(state, "天赋解锁", [f"{who} 达到 Lv{int(level)}，可选择新天赋。"])


def dq_resolve_talent_choice(state: Dict[str, Any], choice_id: str) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    _ensure_meta_logs(state)
    meta = state.setdefault("meta", {})
    pending = meta.get("pending_talent")
    if not isinstance(pending, dict):
        return state
    choices = pending.get("choices") or {}
    if choice_id not in choices:
        return state

    target = pending.get("target") or {}
    role = str(pending.get("role", ""))
    level = int(pending.get("level", 0) or 0)
    if level not in TALENT_LEVELS:
        meta["pending_talent"] = None
        return state

    # 写入选择结果（玩家/成员）
    if target.get("type") == "player":
        state.setdefault("talents", [])
        state.setdefault("talent_picked", {})
        if choice_id not in state["talents"]:
            state["talents"].append(choice_id)
        state["talent_picked"][str(level)] = choice_id
    else:
        mid = str(target.get("mid", ""))
        for mem in state.get("party_members", []) or []:
            if str(mem.get("mid", "")) == mid:
                mem.setdefault("talents", [])
                mem.setdefault("talent_picked", {})
                if choice_id not in mem["talents"]:
                    mem["talents"].append(choice_id)
                mem["talent_picked"][str(level)] = choice_id
                break

    meta.setdefault("log", []).append(
        f"🌟 天赋选择完成：{pending.get('title','')} 选择「{choices.get(choice_id, choice_id)}」。"
    )

    # 弹出下一个 pending（如果队列还有）
    queue = meta.get("pending_talent_queue") or []
    if isinstance(queue, list) and queue:
        meta["pending_talent"] = queue.pop(0)
    else:
        meta["pending_talent"] = None
    meta["pending_talent_queue"] = queue if isinstance(queue, list) else []
    return state


def _maybe_level_up(player: Dict[str, Any], rng: random.Random, logs: List[str]) -> None:
    """升级：获得可分配能力点，由玩家在界面分配至六维；不再随机涨属性。"""
    _ = rng
    while (
        player["level"] < MAX_PLAYER_LEVEL
        and int(player.get("exp_to_next", 0) or 0) > 0
        and player["exp"] >= player["exp_to_next"]
    ):
        player["exp"] -= player["exp_to_next"]
        player["level"] += 1
        _ensure_attrs(player)
        player["pending_stat_points"] = int(player.get("pending_stat_points", 0) or 0) + STAT_POINTS_PER_LEVEL

        learned: List[str] = []
        sid_unlock = WARRIOR_SKILL_BY_LEVEL.get(player["level"])
        if sid_unlock:
            _try_grant_skill(player, sid_unlock, learned, logs)

        if player["level"] >= MAX_PLAYER_LEVEL:
            player["exp_to_next"] = 0
        else:
            player["exp_to_next"], _ = _player_level_curve(player["level"])
        _apply_attrs_to_base(player)
        _recalc_player_from_equipment(player)
        # 升级：生命与魔力回满，清除异常状态
        player["hp"] = int(player.get("max_hp", 1))
        player["mp"] = int(player.get("max_mp", 1))
        player["status_effects"] = []

        logs.append(
            f"✨ 你升级了！Lv{player['level']}，获得 {STAT_POINTS_PER_LEVEL} 点能力点（请在「角色属性」中分配）。"
            f" HP/MP 已回满，异常状态已清除。"
        )
        _q2_try_force_wither_on_reach_level(player, int(player.get("level", 1) or 1), logs)
        _q3_try_force_golem_on_reach_level(player, int(player.get("level", 1) or 1), logs)
        _q4_try_force_sea_witch_on_reach_level(player, int(player.get("level", 1) or 1), logs)
        _q5_try_force_throne_guard_on_reach_level(player, int(player.get("level", 1) or 1), logs)
        if learned:
            logs.append("✅ 本次升级习得技能：" + "、".join(learned))
            _queue_unlock_notice(player, "主角技能成长", [f"新技能：{x}" for x in learned])

        # 天赋树（10/20/30级触发 2选1）
        if int(player.get("level", 1) or 1) in TALENT_LEVELS:
            _queue_talent_choice(
                player,
                target={"type": "player"},
                role=str(player.get("role", "warrior")),
                level=int(player.get("level", 1) or 1),
            )
            for mem in player.get("party_members", []) or []:
                _queue_talent_choice(
                    player,
                    target={"type": "member", "mid": str(mem.get("mid", ""))},
                    role=str(mem.get("role", "")),
                    level=int(player.get("level", 1) or 1),
                )
        # 队友同步升级：等级一致，能力点可分配，学习新技能
        members = player.setdefault("party_members", [])
        for mem in members:
            mem["level"] = int(player["level"])
            mem["pending_stat_points"] = int(mem.get("pending_stat_points", 0) or 0) + STAT_POINTS_PER_LEVEL
            _sync_member_skills(player, mem, logs)
            _recalc_member_stats(mem, int(player["level"]), player.get("party_armory"), player.get("resources"))
            mem["hp"] = int(mem.get("max_hp", 1))
            mem["mp"] = int(mem.get("max_mp", 0))


def _recalc_player_from_equipment(player: Dict[str, Any]) -> None:
    if "base" not in player:
        player["base"] = {
            "atk": player["atk"],
            "def": player["def"],
            "mdef": player.get("mdef", max(1, int(player.get("def", 1) or 1))),
            "agi": player["agi"],
            "max_hp": player["max_hp"],
            "max_mp": player["max_mp"],
        }
    _apply_attrs_to_base(player)
    base = player["base"]
    player["atk"] = base["atk"]
    player["def"] = base["def"]
    player["mdef"] = base["mdef"]
    player["agi"] = base["agi"]
    player["max_hp"] = base["max_hp"]
    player["max_mp"] = base["max_mp"]
    player["hp"] = min(player["hp"], player["max_hp"])
    player["mp"] = min(player["mp"], player["max_mp"])


def dq_combat_stat_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    供角色界面展示：与 _compute_damage / 普攻暴击率一致的参考数值。
    使用按等级估算的参考敌防、参考敌攻，便于理解「约」字区间（非战斗中某一固定怪）。
    """
    _ensure_attrs(state)
    _recalc_player_from_equipment(state)
    ea = _effective_attrs(state)
    luk = int(ea.get("luk", 0))
    eagi = int(ea.get("agi", 0))
    atk = int(state.get("atk", 0))
    pdef = int(state.get("def", 0))
    pdef_mit = _incoming_def_effective_for_unit(str(state.get("role", "warrior")), pdef)
    pmdef = int(state.get("mdef", 1) or 1)
    pmdef_mit = _incoming_mdef_effective_for_unit(str(state.get("role", "warrior")), pmdef)
    lv = max(1, int(state.get("level", 1) or 1))

    crit_rate = _player_crit_rate(state)
    crit_pct = round(crit_rate * 100, 1)

    ref_enemy_def = max(1, int(2 + lv * 1.6))
    power = 1.0
    raw_base = atk * power - ref_enemy_def * (0.55 + 0.15 * power)
    base = max(1, int(raw_base))
    atk_lo = max(1, int(base * 0.88))
    atk_hi = max(1, int(base * 1.12))
    atk_c_lo = max(1, int(atk_lo * 1.7))
    atk_c_hi = max(1, int(atk_hi * 1.7))

    # 防御「等效减伤」示意：用略高于低阶怪的参考攻，避免 def/低攻 比值过大导致百分比虚高
    ref_enemy_atk_mit = max(18, int(12 + lv * 2.4))
    pow_e = 1.0
    term_def = pdef_mit * (0.55 + 0.15 * pow_e)
    atk_component = ref_enemy_atk_mit * pow_e
    if atk_component > 0:
        raw_pct = (term_def / (atk_component + term_def * 0.25)) * 100
        mit_pct = min(32.0, max(0.0, raw_pct * 0.72))
    else:
        mit_pct = 0.0
    mit_pct = round(mit_pct, 1)
    acc_extra = _accessory_extra_bonus(state)
    tb_m = _talent_combat_flat_bonuses(list(state.get("talents") or []))
    mit_pct = round(
        min(
            32.0,
            mit_pct
            + float(acc_extra.get("mit_bonus", 0.0) or 0.0) * 100.0
            + float(tb_m.get("mit_bonus", 0.0) or 0.0) * 100.0
            + max(0.0, 1.0 - float(tb_m.get("received_mult", 1.0) or 1.0)) * 100.0,
        ),
        1,
    )

    term_mdef = pmdef_mit * (0.55 + 0.15 * pow_e)
    if atk_component > 0:
        raw_pct_m = (term_mdef / (atk_component + term_mdef * 0.25)) * 100
        mdef_mit_pct = min(32.0, max(0.0, raw_pct_m * 0.72))
    else:
        mdef_mit_pct = 0.0
    mdef_mit_pct = round(
        min(
            32.0,
            mdef_mit_pct
            + float(acc_extra.get("mit_bonus", 0.0) or 0.0) * 100.0
            + float(tb_m.get("mit_bonus", 0.0) or 0.0) * 100.0
            + max(0.0, 1.0 - float(tb_m.get("received_mult", 1.0) or 1.0)) * 100.0,
        ),
        1,
    )

    eva = _player_evasion_chance(state)
    eva_pct = round(eva * 100, 1)

    return {
        "atk_lo": atk_lo,
        "atk_hi": atk_hi,
        "atk_c_lo": atk_c_lo,
        "atk_c_hi": atk_c_hi,
        "crit_pct": crit_pct,
        "def_mit_pct": mit_pct,
        "mdef_mit_pct": mdef_mit_pct,
        "eva_pct": eva_pct,
        "ref_def": ref_enemy_def,
        "ref_atk": ref_enemy_atk_mit,
    }


def dq_unit_panel_summary(
    unit: Dict[str, Any],
    ref_enemy_atk: int = 18,
    is_player: bool = False,
    party_armory: Optional[Dict[str, Any]] = None,
    map_resources: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """
    统一面板展示口径（主角/队友）：
    - 命中率 hit_pct（普攻/物系技能失手判定，与 _role_hit_rate + 天赋/饰品命中加成 一致）
    - 暴击率 crit_pct（与 _player_crit_rate / _unit_crit_rate_for_panel 一致）
    - 闪避率 eva_pct（与 _unit_evasion_chance 一致；主角从 state 读 party_armory；队友需传入 party_armory；地图线索用 map_resources / 主角用 unit[\"resources\"]）
    - 等效免伤 def_mit_pct（防御公式 + 饰品/天赋免伤 + 承伤乘数折算）
    """
    u = unit or {}
    if is_player:
        _ensure_attrs(u)
        ea = _effective_attrs(u)
    else:
        _ensure_member_attrs(u)
        ea = _effective_attrs_party_member(u, party_armory)
    pdef = int(u.get("def", 1) or 1)
    pmdef = int(u.get("mdef", 1) or 1)
    role_s = str(u.get("role", "warrior"))
    pdef_mit = _incoming_def_effective_for_unit(role_s, pdef)
    pmdef_mit = _incoming_mdef_effective_for_unit(role_s, pmdef)
    dex_for_hit = int(ea.get("dex", u.get("_dex_eff", 1) or 1) or 0)
    tb = _talent_combat_flat_bonuses(list(u.get("talents") or []))
    acc_x = _accessory_extra_bonus(u)
    hit_bonus = float(tb.get("hit_bonus", 0.0)) + float(acc_x.get("hit_bonus", 0.0) or 0.0)
    hit_rate = min(1.0, _role_hit_rate(role_s, dex_for_hit) + hit_bonus)
    hit_pct = round(min(100.0, max(0.0, hit_rate * 100.0)), 1)

    crit_pct = round(
        min(45.0, _unit_crit_rate_for_panel(u, is_player=is_player, map_resources=map_resources) * 100.0), 1
    )

    eva_ch = _unit_evasion_chance(
        u,
        is_player=is_player,
        party_armory=party_armory,
        map_resources=map_resources if not is_player else None,
    )
    eva_cap = 100.0 if str(u.get("role", "") or "") == "rogue" else 32.0
    eva_pct = round(min(eva_cap, eva_ch * 100.0), 1)

    ref_atk = max(1, int(ref_enemy_atk or 18))
    term_def = pdef_mit * (0.55 + 0.15 * 1.0)
    atk_component = ref_atk * 1.0
    if atk_component > 0:
        raw_pct = (term_def / (atk_component + term_def * 0.25)) * 100
        def_mit_pct = round(min(32.0, max(0.0, raw_pct * 0.72)), 1)
    else:
        def_mit_pct = 0.0
    term_mdef = pmdef_mit * (0.55 + 0.15 * 1.0)
    if atk_component > 0:
        raw_pct_m = (term_mdef / (atk_component + term_mdef * 0.25)) * 100
        mdef_mit_pct0 = round(min(32.0, max(0.0, raw_pct_m * 0.72)), 1)
    else:
        mdef_mit_pct0 = 0.0
    rm = float(tb.get("received_mult", 1.0) or 1.0)
    extra_mit = float(acc_x.get("mit_bonus", 0.0) or 0.0) * 100.0 + float(tb.get("mit_bonus", 0.0) or 0.0) * 100.0
    if rm < 1.0:
        extra_mit += (1.0 - rm) * 100.0
    def_mit_pct = round(min(32.0, def_mit_pct + extra_mit), 1)
    mdef_mit_pct = round(min(32.0, mdef_mit_pct0 + extra_mit), 1)

    return {
        "hit_pct": hit_pct,
        "crit_pct": crit_pct,
        "eva_pct": eva_pct,
        "def_mit_pct": def_mit_pct,
        "mdef_mit_pct": mdef_mit_pct,
    }


def _enemy_stats(
    monster_id: str,
    player_level: int,
    rng: random.Random,
    scale: float,
    enemy_level: Optional[int] = None,
) -> Dict[str, Any]:
    cat = _monster_catalog()[monster_id]
    hp_lo, hp_hi = cat["hp"]
    atk_lo, atk_hi = cat["atk"]
    def_lo, def_hi = cat["def"]
    agi_lo, agi_hi = cat["agi"]
    hp = int(rng.uniform(hp_lo, hp_hi) * scale)
    atk = int(rng.uniform(atk_lo, atk_hi) * scale)
    dfn = int(rng.uniform(def_lo, def_hi) * scale)
    agi = int(rng.uniform(agi_lo, agi_hi) * (0.9 + 0.1 * rng.random()) * (0.7 + 0.3 * scale))
    mp = 0
    if isinstance(cat.get("mp"), tuple):
        mp = int(rng.uniform(cat["mp"][0], cat["mp"][1]) * scale)
    elif isinstance(cat.get("mp"), int):
        mp = cat["mp"]
    # 显示等级：默认严格在主角 ±2；也可由外部显式指定
    if enemy_level is None:
        plv = max(1, int(player_level or 1))
        elv = rng.randint(max(1, plv - 2), min(80, plv + 2))
    else:
        elv = max(1, min(80, int(enemy_level)))
    # 玩家每级能力点提升到 2 后，整体提高怪物基础成长，避免单技能秒杀（HP 成长略调高，低级怪也不会过脆）
    lv_mul_hp = 1.0 + (elv - 1) * 0.12
    lv_mul_atk = 1.0 + (elv - 1) * 0.072
    lv_mul_def = 1.0 + (elv - 1) * 0.082
    lv_mul_agi = 1.0 + (elv - 1) * 0.055
    hp = max(1, int(hp * lv_mul_hp))
    atk = max(1, int(atk * lv_mul_atk))
    dfn = max(1, int(dfn * lv_mul_def))
    agi = max(1, int(agi * lv_mul_agi))
    if mp > 0:
        mp = max(1, int(mp * (1.0 + (elv - 1) * 0.055)))
    # 与主角等级差导致体感显著变化：高你1级变难打，高你2级明显更硬更痛
    diff = int(elv - max(1, int(player_level or 1)))
    if diff > 0:
        hp = max(1, int(hp * (1.0 + 0.36 * diff)))
        atk = max(1, int(atk * (1.0 + 0.38 * diff)))
        dfn = max(1, int(dfn * (1.0 + 0.30 * diff)))
        agi = max(1, int(agi * (1.0 + 0.16 * diff)))
        if mp > 0:
            mp = max(1, int(mp * (1.0 + 0.20 * diff)))
    elif diff < 0:
        # 低于主角等级时不再额外削弱，保持原始强度
        pass
    return {
        "mid": monster_id,
        "name": cat["name"],
        "level": elv,
        "hp": hp,
        "max_hp": hp,
        "atk": atk,
        "def": dfn,
        "agi": agi,
        "mp": mp,
        "max_mp": mp,
        "effects": [],  # enemy-side effects
        "ai": {"special_cd": rng.randint(2, 5)},
    }


ZONE_ENEMY_LEVEL_RANGES: Dict[str, Tuple[int, int]] = {
    "starter": (1, 6),   # Q1：破晓村附近（遇敌等级不高于 6）
    "forest": (6, 12),   # Q2：诅咒森林（不高于 12）
    "mines": (12, 18),   # Q3：遗忘矿坑（不高于 18）
    "coast": (18, 24),   # Q4：幽影海岸（不高于 24）
    "throne": (24, 30),  # Q5：王座地牢（不高于 30）
}

BOSS_FIXED_LEVELS: Dict[str, int] = {
    "boss_witherling": 12,    # Q2
    "boss_golem": 18,         # Q3
    "boss_sea_witch": 24,     # Q4
    "boss_throne_guard": 30,  # Q5
}


def _zone_enemy_level_range(zone_id: str) -> Tuple[int, int]:
    return ZONE_ENEMY_LEVEL_RANGES.get(str(zone_id), (1, 30))


def dq_zone_level_range(zone_id: str) -> Tuple[int, int]:
    """供前端读取区域建议等级范围。"""
    return _zone_enemy_level_range(str(zone_id))


def _zone_max_enemy_lv_cap(zone_id: str) -> Optional[int]:
    """主线五图遇敌等级上限（Q1~Q5）；无限地牢等返回 None。"""
    z = ZONE_ENEMY_LEVEL_RANGES.get(str(zone_id))
    if z:
        return int(z[1])
    return None


def _is_player_trivializing_zone(player_level: int, zone_id: str) -> bool:
    """
    主角等级 ≥ 该区域遇敌等级上限 + 3 时，视为「碾压」该图：
    - 探索未遇敌：不给保底经验与金币；
    - 战斗胜利：不给金币。
    仅对 Q1~Q5 五张主线地图生效；无限地牢不受影响。
    """
    if str(zone_id) == "infinite":
        return False
    zm = _zone_max_enemy_lv_cap(zone_id)
    if zm is None:
        return False
    plv = max(1, int(player_level or 1))
    return plv >= zm + 3


def _roll_zone_enemy_level(zone_id: str, player_level: int, rng: random.Random, is_boss: bool = False) -> int:
    zone_lo, zone_hi = _zone_enemy_level_range(zone_id)
    plv = max(1, int(player_level or 1))
    # 主角未达到该区域下限：固定刷该区域下限怪
    if plv < int(zone_lo):
        return int(zone_lo)
    # 硬约束：怪物等级只在主角 ±2 范围内
    hero_lo = max(1, plv - 2)
    hero_hi = min(80, plv + 2)
    lo = max(int(zone_lo), hero_lo)
    hi = min(int(zone_hi), hero_hi)
    if lo > hi:
        # 若区域段与±2无交集，仍优先满足“只在±2内”
        lo, hi = hero_lo, hero_hi
    # 非 Boss：降低“高于主角等级”怪物出现概率（仍保留小概率高压战）
    if not is_boss:
        levels = list(range(lo, hi + 1))
        weights: List[float] = []
        for lvx in levels:
            diff = lvx - plv
            # 以“同级”为主峰：同级出现概率最高；高于主角等级明显更低
            if diff == 0:
                w = 2.4
            elif diff == -1:
                w = 1.2
            elif diff <= -2:
                w = 1.0
            elif diff == 1:
                w = 0.25
            else:  # diff >= 2（当前约束下最多 +2）
                w = 0.08
            weights.append(w)
        lv = int(rng.choices(levels, weights=weights, k=1)[0])
    else:
        lv = rng.randint(lo, hi)
    if is_boss:
        lv = min(hi, max(lo, lv + 1))
    lv = max(1, min(80, int(lv)))
    _zr = ZONE_ENEMY_LEVEL_RANGES.get(str(zone_id))
    if _zr is not None:
        lv = min(lv, int(_zr[1]))
    return lv


def _can_trigger_story_boss_by_level(state: Dict[str, Any], boss_id: str) -> bool:
    """Q2~Q5：主角与 Boss 固定等级相差不超过 2 级才可能遇到 Boss。"""
    hero_lv = max(1, int(state.get("level", 1) or 1))
    boss_lv = int(BOSS_FIXED_LEVELS.get(str(boss_id), hero_lv))
    return abs(hero_lv - boss_lv) <= 2


def _make_enemy_for_zone(zone_id: str, player_level: int, rng: random.Random, boss: bool = False, floor: int = 1) -> Dict[str, Any]:
    cat = _monster_catalog()
    if boss:
        # choose a specific boss id
        raise ValueError("boss should be built with explicit monster id")
    monsters = _zone_catalog()[zone_id]["monsters"]
    if not monsters:
        # infinite dungeon fallback
        monsters = [
            "slime",
            "rat",
            "goblin",
            "skeleton",
            "wraith",
            "sea_curse",
            "throne_guard",
            "witherling",
            "sprite",
            "bog_worm",
            "wither_vine",
            "mine_spider",
            "reef_crab",
            "night_moth",
        ]
    m = rng.choice(monsters)
    # 主线地图以区域等级段为主，floor 只给少量补偿
    zone_lv = _roll_zone_enemy_level(zone_id, player_level, rng, is_boss=False)
    scale = 1.0 + max(0, floor - 1) * 0.04
    # cap scale to avoid runaway
    scale = min(scale, 4.5)
    return _enemy_stats(m, player_level, rng, scale, enemy_level=zone_lv)


def _apply_status_tick(state: Dict[str, Any], target: str, rng: random.Random, logs: List[str]) -> None:
    # target: "player" only implemented
    if target != "player":
        return
    if not state.get("status_effects"):
        return
    new_effects = []
    for e in state["status_effects"]:
        e = copy.deepcopy(e)
        e["turns"] -= 1
        kind = e["kind"]
        if kind == "burn":
            continue  # 已废弃；仅 burn_stack 生效
        if kind == "burn_stack":
            mx = max(1, int(state["battle"].get("player_max_hp", 1) or 1))
            stacks = min(MAGE_BURN_STACK_MAX, int(e.get("stacks", 1) or 1))
            pct = float(e.get("pct_per_stack", MAGE_BURN_MAX_HP_PCT_PER_STACK) or MAGE_BURN_MAX_HP_PCT_PER_STACK)
            dmg = max(1, int(mx * pct * stacks))
            if state["battle"]["player_hp"] > 0:
                state["battle"]["player_hp"] = max(0, state["battle"]["player_hp"] - dmg)
                logs.append(f"🔥 你受到灼烧伤害-{dmg}（{stacks}层）")
        elif kind == "poison":
            dmg = int(e["dmg"])
            state["battle"]["player_hp"] = max(0, state["battle"]["player_hp"] - dmg)
            logs.append(f"☠️ 你受到毒伤害-{dmg}")
        if e["turns"] > 0:
            new_effects.append(e)
    state["status_effects"] = new_effects


def _apply_enemy_effect_ticks(battle: Dict[str, Any], logs: List[str]) -> None:
    """敌方异常结算：流血（默认当前生命×10%，可被效果 pct 覆盖）；中毒（最大生命10%）。"""
    enemies = battle.get("enemies") or ([battle.get("enemy")] if battle.get("enemy") else [])
    for e in enemies:
        if not isinstance(e, dict):
            continue
        if int(e.get("hp", 0) or 0) <= 0:
            continue
        _strip_boss_debuff_immunities(e)
        effs = e.get("effects") or []
        if not effs:
            continue
        new_effs: List[Dict[str, Any]] = []
        for ef in effs:
            if not isinstance(ef, dict):
                continue
            kind = str(ef.get("kind", ""))
            turns = int(ef.get("turns", 0) or 0)
            if kind == "bleed":
                pct = float(ef.get("pct", 0.10) or 0.10)
                dmg = max(1, int(int(e.get("hp", 0) or 0) * pct))
                e["hp"] = max(0, int(e.get("hp", 0) or 0) - dmg)
                logs.append(f"🩸 {e.get('name','敌人')} 流血发作，损失 {dmg} 生命。")
            elif kind == "poison":
                mh = max(1, int(e.get("max_hp", 1) or 1))
                dmg = max(1, int(mh * 0.10))
                e["hp"] = max(0, int(e.get("hp", 0) or 0) - dmg)
                logs.append(f"☠️ {e.get('name','敌人')} 中毒发作，损失 {dmg} 生命。")
            elif kind == "blind":
                # 致盲在敌方出手时消耗，不在回合开始衰减
                new_effs.append(copy.deepcopy(ef))
                continue
            elif kind == "burn_stack":
                stacks = min(
                    MAGE_BURN_STACK_MAX,
                    int(ef.get("stacks", 1) or 1),
                )
                pct_ps = float(ef.get("pct_per_stack", MAGE_BURN_MAX_HP_PCT_PER_STACK) or MAGE_BURN_MAX_HP_PCT_PER_STACK)
                mh = max(1, int(e.get("max_hp", 1) or 1))
                dmg = max(1, int(mh * pct_ps * stacks))
                e["hp"] = max(0, int(e.get("hp", 0) or 0) - dmg)
                logs.append(
                    f"🔥 {e.get('name','敌人')} 灼烧发作（{stacks}层），损失 {dmg} 生命（每回合最大生命×{pct_ps * stacks * 100:.0f}%）。"
                )
            turns -= 1
            if turns > 0 and int(e.get("hp", 0) or 0) > 0:
                ef2 = copy.deepcopy(ef)
                ef2["turns"] = turns
                new_effs.append(ef2)
        e["effects"] = new_effs


def _hunter_pierce_splash_targets(
    es_now: List[Dict[str, Any]], main_e: Dict[str, Any], rng: random.Random
) -> List[Dict[str, Any]]:
    """穿透箭溅射：2 怪时另一名必中；3 怪时另两名各中；4+ 时在其余中随机 2 名。"""
    tid = str(main_e.get("eid") or "")
    alive = [x for x in es_now if int(x.get("hp", 0) or 0) > 0]
    if tid:
        rest = [x for x in alive if str(x.get("eid") or "") != tid]
    else:
        rest = [x for x in alive if x is not main_e]
    m = len(rest)
    if m == 0:
        return []
    if m <= 2:
        return rest
    return rng.sample(rest, 2)


def _enemy_blind_consume_and_maybe_whiff(enemy: Dict[str, Any], rng: random.Random, logs: List[str]) -> bool:
    """敌人若带致盲则消耗之；50% 本次攻击直接失手。返回 True 表示应视为未命中并结束本次攻击。"""
    effs = enemy.get("effects") or []
    for i, ef in enumerate(effs):
        if not isinstance(ef, dict) or str(ef.get("kind")) != "blind":
            continue
        enemy["effects"] = [x for j, x in enumerate(effs) if j != i]
        lv_tag = f"Lv{enemy.get('level', '?')}"
        nm = enemy.get("name", "敌人")
        if rng.random() < HUNTER_BLIND_MISS_CHANCE:
            logs.append(f"👁 {nm}（{lv_tag}）因致盲攻击失手！")
            return True
        logs.append(f"👁 {nm}（{lv_tag}）强忍致盲仍发起攻击。")
        return False
    return False


def _player_apply_burn_stack(state: Dict[str, Any], logs: List[str]) -> None:
    """玩家灼烧：与敌方 burn_stack 相同规则（叠层、最大生命×5%/层/回合，最高 3 层，3 回合刷新）。"""
    battle = state.get("battle") or {}
    mx = max(1, int(battle.get("player_max_hp", 1) or 1))
    old_stacks = 0
    new_effs: List[Dict[str, Any]] = []
    for ef in state.get("status_effects") or []:
        if isinstance(ef, dict) and str(ef.get("kind")) == "burn_stack":
            old_stacks = int(ef.get("stacks", 1) or 1)
            continue
        new_effs.append(ef)
    stacks = min(MAGE_BURN_STACK_MAX, old_stacks + 1)
    new_effs.append(
        {
            "kind": "burn_stack",
            "turns": MAGE_BURN_TURNS,
            "stacks": stacks,
            "pct_per_stack": MAGE_BURN_MAX_HP_PCT_PER_STACK,
        }
    )
    state["status_effects"] = new_effs
    pct_turn = stacks * MAGE_BURN_MAX_HP_PCT_PER_STACK * 100.0
    logs.append(f"🔥 你被灼烧×{stacks}（{MAGE_BURN_TURNS}回合，每回合最大生命约 {pct_turn:.0f}%）！")


def _mage_apply_fire_blast_burn(target: Dict[str, Any], rng: random.Random, logs: List[str]) -> None:
    """爆炎术：30% 概率附加/叠加灼烧，最高 3 层；每回合按最大生命×(5%×层数) 扣血，持续 3 回合（刷新回合数）。"""
    if _enemy_is_boss(target):
        return
    if rng.random() >= MAGE_FIRE_BLAST_BURN_CHANCE:
        return
    old_stacks = 0
    new_effs: List[Dict[str, Any]] = []
    for ef in target.get("effects") or []:
        if isinstance(ef, dict) and str(ef.get("kind")) == "burn_stack":
            old_stacks = int(ef.get("stacks", 1) or 1)
            continue
        new_effs.append(ef)
    stacks = min(MAGE_BURN_STACK_MAX, old_stacks + 1)
    new_effs.append(
        {
            "kind": "burn_stack",
            "turns": MAGE_BURN_TURNS,
            "stacks": stacks,
            "pct_per_stack": MAGE_BURN_MAX_HP_PCT_PER_STACK,
        }
    )
    target["effects"] = new_effs
    pct_turn = stacks * MAGE_BURN_MAX_HP_PCT_PER_STACK * 100.0
    logs.append(
        f"🔥 {target.get('name','敌人')} 灼烧×{stacks}（{MAGE_BURN_TURNS}回合，每回合最大生命约 {pct_turn:.0f}%）！"
    )


def _compute_damage(att: int, dfn: int, power: float, rng: random.Random, crit_rate: float, crit_bonus: float = 1.7) -> Tuple[int, bool]:
    base = att * power - dfn * (0.55 + 0.15 * power)
    base = max(1, int(base))
    spread = rng.uniform(0.88, 1.12)
    dmg = max(1, int(base * spread))
    is_crit = rng.random() < crit_rate
    if is_crit:
        dmg = int(dmg * crit_bonus)
    return dmg, is_crit


def _unit_evasion_chance(
    unit: Dict[str, Any],
    *,
    is_player: bool,
    party_armory: Optional[Dict[str, Any]] = None,
    map_resources: Optional[Dict[str, Any]] = None,
) -> float:
    """
    AGI + LUK 换算 + 天赋/探索/饰品 eva_bonus 合计为闪避概率。
    - 刺客（rogue）：AGI 每点约 +0.0065 闪避概率（约 0.65%/点），不设 32% 硬顶，仅限制在 [0, 100%]。
    - 其他职业：AGI 每点 +0.0032（约 0.32%），上述合计受 32% 硬顶（含天赋与场景加成在内）。
    """
    if is_player:
        ea = _effective_attrs(unit)
    else:
        ea = _effective_attrs_party_member(unit, party_armory)
    agi_v = int(ea.get("agi", 0))
    luk_v = int(ea.get("luk", 0))
    tb = _talent_combat_flat_bonuses(list(unit.get("talents") or []))
    eva_bonus = float(tb.get("eva_bonus", 0.0))
    _clue_res = (unit.get("resources") if is_player else map_resources) or {}
    eva_bonus += float(_clue_res.get("clue_bonus_eva", 0.0) or 0.0)
    eva_bonus += float(_accessory_extra_bonus(unit).get("eva_bonus", 0.0) or 0.0)
    agi_eva_coef = float(ROGUE_AGI_EVA_PER_POINT) if str(unit.get("role", "") or "") == "rogue" else 0.0032
    raw = max(0.0, agi_v * agi_eva_coef + luk_v * 0.0005 + eva_bonus)
    if str(unit.get("role", "") or "") == "rogue":
        return min(1.0, raw)
    return min(0.32, raw)


def _player_evasion_chance(state: Dict[str, Any]) -> float:
    return _unit_evasion_chance(state, is_player=True)


def _ally_evasion(ally: Dict[str, Any], state: Dict[str, Any]) -> float:
    return _unit_evasion_chance(
        ally,
        is_player=False,
        party_armory=state.get("party_armory"),
        map_resources=state.get("resources"),
    )


def _accessory_special_id(state: Dict[str, Any]) -> Optional[str]:
    acc = (state.get("equipped") or {}).get("accessory")
    if not acc:
        return None
    return (acc.get("meta") or {}).get("special_id")


def _unit_accessory_special_ids(unit: Dict[str, Any]) -> List[str]:
    """读取任意单位（主角/队友）饰品 special ids。"""
    acc = (unit.get("equipped") or {}).get("accessory")
    if not isinstance(acc, dict):
        return []
    meta = acc.get("meta") or {}
    ids = meta.get("special_ids")
    if isinstance(ids, list):
        return [str(x) for x in ids if str(x)]
    sid = meta.get("special_id")
    return [str(sid)] if sid else []


def _accessory_special_ids(state: Dict[str, Any]) -> List[str]:
    return _unit_accessory_special_ids(state)


def _party_has_special_id(state: Dict[str, Any], sid: str) -> bool:
    sid = str(sid or "")
    if not sid:
        return False
    if sid in _unit_accessory_special_ids(state):
        return True
    for mem in state.get("party_members", []) or []:
        if isinstance(mem, dict) and sid in _unit_accessory_special_ids(mem):
            return True
    return False


def _accessory_extra_bonus(state: Dict[str, Any]) -> Dict[str, float]:
    out = {"atk_pct": 0.0, "eva_bonus": 0.0, "mit_bonus": 0.0, "crit_bonus": 0.0, "hit_bonus": 0.0}
    eq = state.get("equipped") or {}
    if not isinstance(eq, dict):
        return out
    # 历史命名保留：当前汇总全身装备中的百分比词条，确保非饰品装备词条也生效
    for slot in EQUIPMENT_SLOTS:
        it = eq.get(slot)
        if not isinstance(it, dict):
            continue
        meta = it.get("meta") or {}
        for k in out.keys():
            out[k] += float(meta.get(k, 0.0) or 0.0)
    return out


def _unit_crit_rate_for_panel(
    unit: Dict[str, Any], *, is_player: bool, map_resources: Optional[Dict[str, Any]] = None
) -> float:
    """与主角普攻/物系技能暴击率公式一致（供详情与战斗共用）。"""
    if is_player:
        _ensure_attrs(unit)
        ea = _effective_attrs(unit)
    else:
        _ensure_member_attrs(unit)
        ea = _effective_attrs_party_member(unit, None)
    luk = int(ea.get("luk", 0))
    eagi = int(ea.get("agi", 0))
    tb = _talent_combat_flat_bonuses(list(unit.get("talents") or []))
    bonus = float(tb.get("crit_bonus", 0.0))
    _clue_res = (unit.get("resources") if is_player else map_resources) or {}
    bonus += float(_clue_res.get("clue_bonus_crit", 0.0) or 0.0)
    bonus += float(_accessory_extra_bonus(unit).get("crit_bonus", 0.0) or 0.0)
    return min(0.45, 0.04 + luk * 0.0040 + eagi / 900.0 + bonus)


def _player_crit_rate(state: Dict[str, Any]) -> float:
    return _unit_crit_rate_for_panel(state, is_player=True)


def _player_incoming_mitigation(state: Dict[str, Any]) -> Tuple[float, float]:
    """主角承伤：(received_mult, flat_mit)，伤害 = raw * rm * max(0, 1 - flat_mit)。"""
    tb = _talent_combat_flat_bonuses(list(state.get("talents") or []))
    rm = float(tb.get("received_mult", 1.0) or 1.0)
    mit = float(_accessory_extra_bonus(state).get("mit_bonus", 0.0) or 0.0) + float(tb.get("mit_bonus", 0.0) or 0.0)
    mit = min(0.95, mit)
    return rm, mit


def _cover_party_incoming_mult(battle: Dict[str, Any]) -> float:
    """援护：全队额外免伤时，敌方直接伤害乘该系数（约 20% 减伤；与天赋/饰品承伤叠乘）。"""
    if int(battle.get("cover_party_turns", 0) or 0) > 0:
        return float(COVER_PARTY_INCOMING_MULT)
    return 1.0


def _shield_counter_pre_player_incoming(battle: Dict[str, Any], dmg: int) -> int:
    """盾反生效时：主角作为该次直接伤害目标，在代入天赋/饰品承伤前先乘额外免伤。"""
    d = int(dmg)
    if d <= 0:
        return d
    if bool(battle.get("shield_counter_active")):
        return max(0, int(d * SHIELD_COUNTER_PLAYER_INCOMING_MULT))
    return d


def _shield_counter_reflect_after_player_hit(
    battle: Dict[str, Any], enemy: Dict[str, Any], hp_loss: int, logs: List[str]
) -> None:
    """盾反：按实际扣血将一定比例反弹给当次攻击者。"""
    if not bool(battle.get("shield_counter_active")):
        return
    if int(hp_loss or 0) <= 0:
        return
    if int(enemy.get("hp", 0) or 0) <= 0:
        return
    ref = int(hp_loss * SHIELD_COUNTER_REFLECT_FRAC)
    if ref <= 0:
        return
    enemy["hp"] = max(0, int(enemy.get("hp", 0) or 0) - ref)
    logs.append(f"🛡️ 盾反：反弹 {ref} 伤害至 {enemy.get('name', '敌人')}。")


def _battle_track_player_damage_taken_this_turn(battle: Dict[str, Any], amount: int) -> None:
    """累计本回合主角实际受到的来自敌方的伤害（统计用）。"""
    if int(amount or 0) <= 0:
        return
    battle["player_damage_taken_this_turn"] = int(battle.get("player_damage_taken_this_turn", 0) or 0) + int(amount)


def _apply_enemy_physical_hit(state: Dict[str, Any], enemy: Dict[str, Any], dmg: int, logs: List[str]) -> None:
    battle = state["battle"]
    rm, mit_bonus = _player_incoming_mitigation(state)
    cm = _cover_party_incoming_mult(battle)
    dmg1 = int(dmg * cm)
    dmg1 = _shield_counter_pre_player_incoming(battle, dmg1)
    dmg2 = int(dmg1 * rm * max(0.0, 1.0 - mit_bonus))
    battle["player_hp"] = max(0, battle["player_hp"] - dmg2)
    _battle_track_player_damage_taken_this_turn(battle, dmg2)
    _shield_counter_reflect_after_player_hit(battle, enemy, dmg2, logs)
    if "thorn_shell" in _accessory_special_ids(state) and dmg2 > 0 and enemy.get("hp", 0) > 0:
        ref = max(1, int(dmg2 * 0.08))
        enemy["hp"] = max(0, enemy["hp"] - ref)
        logs.append(f"✨ 饰品触发（主角）：「荆棘」反弹 {ref} 伤害！")


def _dmg_vs_enemy_mult(state: Dict[str, Any], enemy: Dict[str, Any]) -> float:
    bonus = 1.0 + float(_accessory_extra_bonus(state).get("atk_pct", 0.0) or 0.0)
    if "giant_slayer" in _accessory_special_ids(state) and not _enemy_is_boss(enemy):
        bonus *= 1.10
    if str(enemy.get("mid")) == "miner_golem" and int(enemy.get("miner_guard_stance_turns", 0) or 0) > 0:
        bonus *= float(MINER_GUARD_INCOMING_MULT)
    return bonus


def _enemy_spell_attack(enemy: Dict[str, Any]) -> int:
    """小怪施法用等效魔攻（与物攻区分，略低于同 atk 的玩家魔法）。"""
    atk = int(enemy.get("atk", 1) or 1)
    mp = int(enemy.get("mp", 0) or 0)
    lv = max(1, int(enemy.get("level", 1) or 1))
    return max(5, int(atk * 0.40 + mp * 0.88 + lv * 1.05))


def _enemy_resist_for_spell_hit(enemy: Dict[str, Any]) -> int:
    """我方/队友法术对敌方结算：优先 mdef，否则 def（小怪表仅有物防）。"""
    return max(0, int(enemy.get("mdef", enemy.get("def", 0)) or 0))


def _try_warrior_dodge_heal(state: Dict[str, Any], battle: Dict[str, Any], logs: List[str]) -> None:
    """战士30级天赋-守天：闪避一次攻击后，回复20%最大生命。"""
    talents = set(state.get("talents") or [])
    if "warrior_t30_b" not in talents:
        return
    pct = float(TALENT_CHOICE_DEFS.get("warrior_t30_b", {}).get("effects", {}).get("dodge_heal_pct", 0.0) or 0.0)
    if pct <= 0:
        return
    max_hp = int(battle.get("player_max_hp", 1) or 1)
    hp_now = int(battle.get("player_hp", 0) or 0)
    if hp_now <= 0 or hp_now >= max_hp:
        return
    heal = max(1, int(max_hp * pct))
    battle["player_hp"] = min(max_hp, hp_now + heal)
    logs.append(f"🛡️ 守天触发：你闪避后回复了 {heal} HP。")


def _try_execute_amulet(state: Dict[str, Any], enemy: Dict[str, Any], rng: random.Random, logs: List[str]) -> None:
    if "execute" not in _accessory_special_ids(state) or _enemy_is_boss(enemy):
        return
    if enemy.get("hp", 0) <= 0:
        return
    ratio = enemy["hp"] / max(1, enemy["max_hp"])
    if ratio > 0.22:
        return
    if rng.random() < 0.025:
        enemy["hp"] = 0
        logs.append("✨ 饰品触发（主角）：「裁决」触发斩杀！")


def _try_soul_drink(state: Dict[str, Any], battle: Dict[str, Any], dmg: int, logs: List[str]) -> None:
    if "soul_drink" not in _accessory_special_ids(state) or dmg <= 0:
        return
    g = max(1, int(dmg * 0.04))
    battle["player_mp"] = min(int(battle["player_max_mp"]), int(battle["player_mp"]) + g)
    logs.append(f"✨ 饰品触发（主角）：「噬魔」回复 MP +{g}")


ENEMY_CHARGE_MULT = 2.2

# 怪物/Boss 主动招式、蓄力、普攻附带异常、被动附加等「招数」发动概率基准（统一为 20%）
MONSTER_SPECIAL_MOVE_CHANCE = 0.20

# 枯萎之王（Q2 Boss）
WITHER_BOSS_AURA_MULT = 0.9
WITHER_BOSS_REFLECT_RATIO = 0.34
WITHER_BOSS_AOE_MP_COST = 14
WITHER_BOSS_REFLECT_MP_COST = 10
WITHER_BOSS_SPECIAL_SKILL_CHANCE = MONSTER_SPECIAL_MOVE_CHANCE
WITHER_BOSS_AOE_POWER = 0.58
GOLEM_SKILL1_CHANCE = MONSTER_SPECIAL_MOVE_CHANCE
GOLEM_SKILL2_CHANCE = MONSTER_SPECIAL_MOVE_CHANCE
GOLEM_SKILL1_POWER = 0.88
GOLEM_SKILL2_POWER = 0.95
# 熔核震地：每名目标第 1 次吃基础伤害，之后每次对该目标伤害 ×2（叠层为已命中次数）
GOLEM_QUAKE_BASE_DMG = 16
SEA_WITCH_SKILL1_CHANCE = MONSTER_SPECIAL_MOVE_CHANCE
SEA_WITCH_SKILL2_CHANCE = MONSTER_SPECIAL_MOVE_CHANCE
SEA_WITCH_SKILL1_POWER = 0.88
SEA_WITCH_SKILL2_POWER = 1.42
THRONE_SKILL1_CHANCE = MONSTER_SPECIAL_MOVE_CHANCE
THRONE_SKILL2_CHANCE = MONSTER_SPECIAL_MOVE_CHANCE
THRONE_SKILL1_POWER = 1.28
THRONE_SKILL2_POWER = 0.88  

# 小怪专属技能（原为主角「通用」技能池；现仅由对应怪物使用）
GOBLIN_FIREBALL_MP = 4
GOBLIN_FIREBALL_POWER = 1.12
SPRITE_LIGHTNING_MP = 6
SPRITE_LIGHTNING_POWER = 1.38
MINER_GUARD_MP = 4
# 矿坑傀儡守护：对其直接伤害保留约 70%（减伤 30%）
MINER_GUARD_INCOMING_MULT = 0.70
SEA_CURSE_HEAL_MP = 7
THRONE_GUARD_BRAVE_MP = 8
THRONE_GUARD_BRAVE_POWER = 1.82

# 已改为怪物专属、不再从主角技能池习得的 sid（迁移时从技能栏剔除）
RETIRED_PLAYER_COMMON_SKILL_SIDS = frozenset({"fire", "lightning", "heal", "guard", "brave_slash"})


def _strip_retired_common_skills(state: Dict[str, Any]) -> None:
    """旧存档若仍装备已移除的通用技能，从主角与队友技能栏剔除。"""
    if not isinstance(state, dict):
        return
    bad = RETIRED_PLAYER_COMMON_SKILL_SIDS
    state["skills"] = [str(s) for s in (state.get("skills") or []) if str(s) not in bad]
    for m in state.get("party_members") or []:
        if not isinstance(m, dict):
            continue
        m["skills"] = [str(s) for s in (m.get("skills") or []) if str(s) not in bad]


# Q2 第一幕：主角等级低于此时，诅咒森林探索不会弹出第一幕剧情
Q2_ACT1_MIN_LEVEL = 10
# Q1：第二/第三幕改为探索随机触发，并有等级门槛
Q1_ACT2_MIN_LEVEL = 2
Q1_ACT3_MIN_LEVEL = 3
Q1_ACT_RANDOM_CHANCE = 0.22
# Q2：升至该等级时，下次诅咒森林探索必遇枯萎之王（未完成 Q2 且未处于击败后待第二幕时）
Q2_WITHER_FORCE_LEVEL = 14
# 战败于枯萎之王后，诅咒森林随机遭遇 Boss 的额外概率累加（与第一幕「一般」档叠加，有上限）
Q2_WITHER_FAIL_BOSS_CHANCE_ADD = 0.08
Q2_WITHER_BOSS_CHANCE_ADD_MAX = 0.36

# Q3/Q4：达到等级时下次对应区域必遇 Boss；战败后累加随机遭遇概率（与 Q2 规则一致）
Q3_GOLEM_FORCE_LEVEL = 20
Q4_SEA_WITCH_FORCE_LEVEL = 26
Q3_FAIL_BOSS_CHANCE_ADD = 0.08
Q3_BOSS_CHANCE_ADD_MAX = 0.36
Q4_FAIL_BOSS_CHANCE_ADD = 0.08
Q4_BOSS_CHANCE_ADD_MAX = 0.36
# Q4：第一幕起在海岸随机触发；主角低于该等级时不触发前两幕剧情
Q4_ACT1_MIN_LEVEL = 18
# 幽影海岸每次探索触发第一幕或第二幕的概率（须已完成前置幕且未完成该幕）
Q4_ACT_RANDOM_CHANCE = 0.20
# Q5：王座地牢前三幕探索随机触发；Lv30 起下次探索必遇王座守卫（未完成前置幕则先强制剧情）
Q5_THRONE_GUARD_FORCE_LEVEL = 30
Q5_FAIL_BOSS_CHANCE_ADD = 0.08
Q5_BOSS_CHANCE_ADD_MAX = 0.36
Q5_ACT1_MIN_LEVEL = 24
Q5_ACT_RANDOM_CHANCE = 0.20


def _q2_try_force_wither_on_reach_level(state: Dict[str, Any], new_level: int, logs: List[str]) -> None:
    """主角升到 Q2_WITHER_FORCE_LEVEL 时：标记下次森林探索必遇枯萎之王。"""
    if int(new_level) != Q2_WITHER_FORCE_LEVEL:
        return
    if _is_boss_defeated(state, "boss_witherling"):
        return
    meta = state.setdefault("meta", {})
    if meta.get("q2_witherling_beaten_pending_echo"):
        return
    meta["q2_force_boss_next"] = True
    logs.append(
        f"🌿 你已达到 Lv{Q2_WITHER_FORCE_LEVEL}：诅咒森林深处的瘴气与你共鸣，下次在森林探索将直面枯萎之王。"
    )


def _q2_bump_wither_encounter_chance_on_fail(state: Dict[str, Any], battle: Dict[str, Any], logs: List[str]) -> None:
    """于诅咒森林战败且对方含枯萎之王时，提高后续随机遭遇该 Boss 的概率。"""
    if str(state.get("location", "")) != "forest":
        return
    if _is_boss_defeated(state, "boss_witherling"):
        return
    meta = state.setdefault("meta", {})
    if meta.get("q2_witherling_beaten_pending_echo"):
        return
    enemies_all = battle.get("enemies") or ([battle.get("enemy")] if battle.get("enemy") else [])
    if not any(isinstance(e, dict) and str(e.get("mid")) == "boss_witherling" for e in enemies_all):
        return
    cur = float(meta.get("q2_boss_chance_add", 0) or 0)
    nxt = min(Q2_WITHER_BOSS_CHANCE_ADD_MAX, cur + Q2_WITHER_FAIL_BOSS_CHANCE_ADD)
    if nxt <= cur:
        return
    meta["q2_boss_chance_add"] = nxt
    logs.append(
        f"🌿 你在枯萎之王面前受挫，但记住了瘴气的节律：诅咒森林遭遇枯萎之王的概率提高了（+{int(Q2_WITHER_FAIL_BOSS_CHANCE_ADD * 100)}%，累计加成最高 {int(Q2_WITHER_BOSS_CHANCE_ADD_MAX * 100)}%）。"
    )


def _q3_try_force_golem_on_reach_level(state: Dict[str, Any], new_level: int, logs: List[str]) -> None:
    if int(new_level) != Q3_GOLEM_FORCE_LEVEL:
        return
    if _is_boss_defeated(state, "boss_golem"):
        return
    meta = state.setdefault("meta", {})
    if meta.get("q3_golem_beaten_pending_echo"):
        return
    meta["q3_force_boss_next"] = True
    logs.append(
        f"⚒️ 你已达到 Lv{Q3_GOLEM_FORCE_LEVEL}：矿坑深处热浪翻涌，下次在遗忘矿坑探索将直面熔岩巨像。"
    )


def _q4_try_force_sea_witch_on_reach_level(state: Dict[str, Any], new_level: int, logs: List[str]) -> None:
    if int(new_level) != Q4_SEA_WITCH_FORCE_LEVEL:
        return
    if _is_boss_defeated(state, "boss_sea_witch"):
        return
    meta = state.setdefault("meta", {})
    if meta.get("q4_sea_witch_beaten_pending_echo"):
        return
    meta["q4_force_boss_next"] = True
    logs.append(
        f"🌊 你已达到 Lv{Q4_SEA_WITCH_FORCE_LEVEL}：海风里传来不祥咏唱。"
        f"下次在幽影海岸探索将直面潮汐女巫；若第一幕或第二幕尚未成功完成，将优先强制触发对应幕，全部完成后再遭遇 Boss。"
    )


def _q3_bump_golem_encounter_chance_on_fail(state: Dict[str, Any], battle: Dict[str, Any], logs: List[str]) -> None:
    if str(state.get("location", "")) != "mines":
        return
    if _is_boss_defeated(state, "boss_golem"):
        return
    meta = state.setdefault("meta", {})
    if meta.get("q3_golem_beaten_pending_echo"):
        return
    enemies_all = battle.get("enemies") or ([battle.get("enemy")] if battle.get("enemy") else [])
    if not any(isinstance(e, dict) and str(e.get("mid")) == "boss_golem" for e in enemies_all):
        return
    cur = float(meta.get("q3_boss_chance_add", 0) or 0)
    nxt = min(Q3_BOSS_CHANCE_ADD_MAX, cur + Q3_FAIL_BOSS_CHANCE_ADD)
    if nxt <= cur:
        return
    meta["q3_boss_chance_add"] = nxt
    logs.append(
        f"⚒️ 你在熔岩巨像面前受挫，但摸清了热浪节律：遗忘矿坑遭遇熔岩巨像的概率提高了（+{int(Q3_FAIL_BOSS_CHANCE_ADD * 100)}%，累计加成最高 {int(Q3_BOSS_CHANCE_ADD_MAX * 100)}%）。"
    )


def _q4_bump_sea_witch_encounter_chance_on_fail(state: Dict[str, Any], battle: Dict[str, Any], logs: List[str]) -> None:
    if str(state.get("location", "")) != "coast":
        return
    if _is_boss_defeated(state, "boss_sea_witch"):
        return
    meta = state.setdefault("meta", {})
    if meta.get("q4_sea_witch_beaten_pending_echo"):
        return
    enemies_all = battle.get("enemies") or ([battle.get("enemy")] if battle.get("enemy") else [])
    if not any(isinstance(e, dict) and str(e.get("mid")) == "boss_sea_witch" for e in enemies_all):
        return
    cur = float(meta.get("q4_boss_chance_add", 0) or 0)
    nxt = min(Q4_BOSS_CHANCE_ADD_MAX, cur + Q4_FAIL_BOSS_CHANCE_ADD)
    if nxt <= cur:
        return
    meta["q4_boss_chance_add"] = nxt
    logs.append(
        f"🌊 你在潮汐女巫面前受挫，但记住了潮线：幽影海岸遭遇潮汐女巫的概率提高了（+{int(Q4_FAIL_BOSS_CHANCE_ADD * 100)}%，累计加成最高 {int(Q4_BOSS_CHANCE_ADD_MAX * 100)}%）。"
    )


def _q5_try_force_throne_guard_on_reach_level(state: Dict[str, Any], new_level: int, logs: List[str]) -> None:
    if int(new_level) != Q5_THRONE_GUARD_FORCE_LEVEL:
        return
    if _is_boss_defeated(state, "boss_throne_guard"):
        return
    meta = state.setdefault("meta", {})
    if meta.get("q5_throne_guard_beaten_pending_echo"):
        return
    meta["q5_force_boss_next"] = True
    logs.append(
        f"👑 你已达到 Lv{Q5_THRONE_GUARD_FORCE_LEVEL}：王座地牢深处甲胄铿鸣。"
        f"下次在「王座地牢」探索将直面王座守卫；若前三幕尚未成功完成，将优先强制触发对应幕，全部完成后再遭遇 Boss。"
    )


def _q5_bump_throne_guard_encounter_chance_on_fail(state: Dict[str, Any], battle: Dict[str, Any], logs: List[str]) -> None:
    if str(state.get("location", "")) != "throne":
        return
    if _is_boss_defeated(state, "boss_throne_guard"):
        return
    meta = state.setdefault("meta", {})
    if meta.get("q5_throne_guard_beaten_pending_echo"):
        return
    enemies_all = battle.get("enemies") or ([battle.get("enemy")] if battle.get("enemy") else [])
    if not any(isinstance(e, dict) and str(e.get("mid")) == "boss_throne_guard" for e in enemies_all):
        return
    cur = float(meta.get("q5_boss_chance_add", 0) or 0)
    nxt = min(Q5_BOSS_CHANCE_ADD_MAX, cur + Q5_FAIL_BOSS_CHANCE_ADD)
    if nxt <= cur:
        return
    meta["q5_boss_chance_add"] = nxt
    logs.append(
        f"👑 你在王座守卫面前受挫，但看清了门廊节奏：王座地牢遭遇王座守卫的概率提高了（+{int(Q5_FAIL_BOSS_CHANCE_ADD * 100)}%，累计加成最高 {int(Q5_BOSS_CHANCE_ADD_MAX * 100)}%）。"
    )


def _potion_item_from_use(rng: random.Random, use: str) -> Dict[str, Any]:
    """构造一瓶战斗药水物品（use 为 meta.use）。"""
    name_map = {
        "dual_potion": "混合药水",
        "full_heal_potion": "特级恢复药水",
        "full_mp_potion": "特级魔力药水",
        "golden_apple": "金苹果",
        "revive_potion": "复活药水",
    }
    nm = name_map.get(use, "药水")
    if use == "dual_potion":
        mu = {
            "use": "dual_potion",
            "heal_pct": POTION_DUAL_HP_PCT,
            "mp_pct": POTION_DUAL_MP_PCT,
            "sell_price": _potion_unit_sell_price("dual_potion"),
        }
    elif use == "full_heal_potion":
        mu = {"use": "full_heal_potion", "heal_pct": POTION_FULL_HP_PCT, "sell_price": _potion_unit_sell_price("full_heal_potion")}
    elif use == "full_mp_potion":
        mu = {"use": "full_mp_potion", "mp_pct": POTION_FULL_MP_PCT, "sell_price": _potion_unit_sell_price("full_mp_potion")}
    elif use == "golden_apple":
        mu = {
            "use": "golden_apple",
            "heal_pct": POTION_GOLDEN_HP_PCT,
            "mp_pct": POTION_GOLDEN_MP_PCT,
            "sell_price": _potion_unit_sell_price("golden_apple"),
        }
    elif use == "revive_potion":
        mu = {
            "use": "revive_potion",
            "revive_hp_pct": POTION_REVIVE_HP_PCT,
            "revive_mp_pct": POTION_REVIVE_MP_PCT,
            "sell_price": _potion_unit_sell_price("revive_potion"),
        }
    else:
        mu = {"use": "heal_potion", "heal_pct": POTION_HP_PCT, "sell_price": _potion_unit_sell_price("heal_potion")}
        nm = "恢复药水"
    return {"item_id": _new_id("pot", rng), "name": nm, "qty": 1, "meta": mu}


def _wither_boss_kill_extra_loot(rng: random.Random) -> List[Dict[str, Any]]:
    """击败枯萎之王：额外掉落 2 瓶随机特效药水 + 低概率金苹果。"""
    pool = ["dual_potion", "full_heal_potion", "full_mp_potion", "revive_potion"]
    out: List[Dict[str, Any]] = []
    for _ in range(2):
        out.append(_potion_item_from_use(rng, str(rng.choice(pool))))
    if rng.random() < 0.12:
        out.append(_potion_item_from_use(rng, "golden_apple"))
    return out


def _apply_wither_boss_incoming_damage(
    enemy: Dict[str, Any],
    raw_dmg: int,
    battle: Dict[str, Any],
    logs: List[str],
    *,
    reflect_from: str,
    ally_idx: int = -1,
) -> int:
    """
    枯萎之王：枯萎光环使受到的直接伤害×0.9；若带有枯萎反噬则反弹部分伤害后清除标记。
    reflect_from: \"player\" | \"ally\"
    """
    raw_in = max(0, int(raw_dmg))
    if int(battle.get("war_cry_turns", 0) or 0) > 0 and str(reflect_from) in ("player", "ally"):
        raw_in = max(0, int(raw_in * WAR_CRY_ATK_MULT))
    if str(enemy.get("mid")) != "boss_witherling":
        d = max(0, int(raw_in))
        enemy["hp"] = max(0, int(enemy.get("hp", 0) or 0) - d)
        return d
    dmg = max(1, int(raw_in * WITHER_BOSS_AURA_MULT))
    if enemy.get("wither_reflect_next"):
        enemy["wither_reflect_next"] = False
        ref = max(1, int(dmg * WITHER_BOSS_REFLECT_RATIO))
        if reflect_from == "player":
            battle["player_hp"] = max(0, int(battle.get("player_hp", 0) or 0) - ref)
            _battle_track_player_damage_taken_this_turn(battle, ref)
            logs.append(f"🌿 枯萎反噬！你受到 {ref} 点反弹伤害。")
        elif reflect_from == "ally" and ally_idx >= 0:
            allies = battle.get("allies") or []
            if ally_idx < len(allies):
                al = allies[ally_idx]
                al["hp"] = max(0, int(al.get("hp", 0) or 0) - ref)
                logs.append(f"🌿 枯萎反噬！{al.get('name', '队友')} 受到 {ref} 点反弹伤害。")
    enemy["hp"] = max(0, int(enemy.get("hp", 0) or 0) - dmg)
    return dmg


def _wither_boss_aoe_attack(state: Dict[str, Any], battle: Dict[str, Any], enemy: Dict[str, Any], rng: random.Random, logs: List[str]) -> None:
    """枯萎之王【枯萎凋零】：对主角与存活队友各造成一次范围打击。"""
    lv_tag = f"Lv{enemy.get('level', '?')}"
    atk0 = max(1, int(enemy.get("atk", 1) or 1))
    agi0 = int(enemy.get("agi", 1) or 1)
    crit_rate = min(0.12, 0.04 + agi0 / 650.0)
    logs.append(f"{enemy['name']}（{lv_tag}）释放【枯萎凋零】，瘴气席卷全队！")
    if int(battle.get("player_hp", 0) or 0) > 0:
        if rng.random() < _player_evasion_chance(state):
            logs.append("你勉强躲开枯萎凋零的主要冲击。")
        else:
            tdef = _battle_player_incoming_resist(battle, magical=True)
            dmg, is_crit = _compute_damage(atk0, tdef, WITHER_BOSS_AOE_POWER, rng, crit_rate)
            dmg = _apply_defend_mult_to_damage(battle, dmg)
            _apply_enemy_physical_hit(state, enemy, dmg, logs)
            logs.append(f"瘴气席卷：对你造成 {dmg}{'（暴击）' if is_crit else ''}。")
    allies = battle.get("allies") or []
    for idx, al in enumerate(allies):
        if int(al.get("hp", 0) or 0) <= 0:
            continue
        if rng.random() < _ally_evasion(al, state):
            logs.append(f"{al.get('name', '队友')} 躲开了枯萎凋零。")
            continue
        tdef = _battle_ally_incoming_resist(al, magical=True)
        dmg, is_crit = _compute_damage(atk0, tdef, WITHER_BOSS_AOE_POWER, rng, crit_rate)
        dmg = int(dmg * _cover_party_incoming_mult(battle))
        al["hp"] = max(0, int(al.get("hp", 0) or 0) - dmg)
        logs.append(f"瘴气席卷：对 {al.get('name', '队友')} 造成 {dmg}{'（暴击）' if is_crit else ''}。")


def _apply_defend_mult_to_damage(battle: Dict[str, Any], dmg: int) -> int:
    """仅在造成实际伤害时消耗「本回合减伤」效果（蓄力/未命中不消耗）。"""
    m = float(battle.get("next_enemy_damage_mult", 1.0) or 1.0)
    m = max(0.0, min(1.0, m))
    if m < 1.0:
        battle["next_enemy_damage_mult"] = 1.0
    return int(dmg * m)


def _effective_zone_for_material(zone_id: str, floor: int) -> str:
    """无限地牢按层映射到 Q1~Q5，与装备品质阶段一致。"""
    z = str(zone_id or "starter")
    if z == "infinite":
        return _infinite_zone_for_floor(max(1, int(floor or 1)))
    return z


# 区域材料：① 先判定是否掉落；② 再判定个数（两步独立）。
# ① 掉率：Q1/Q2（starter、forest）18%；Q3～Q5（mines、coast、throne）25%；探索采集 14%。
MATERIAL_ZONE_DROP_P_FOREST_TIER: float = 0.18
MATERIAL_ZONE_DROP_P_OTHER: float = 0.25
EXPLORE_MATERIAL_CHANCE: float = 0.14

# ② 仅在「确定会掉材料」之后：个数 1/2/3 的相对权重为 100% : 50% : 25%（归一化后约 4/7、2/7、1/7）
MATERIAL_QTY_WEIGHTS: Tuple[float, float, float] = (100.0, 50.0, 25.0)


def _roll_material_qty_weighted_halving(rng: random.Random, max_qty: int = 3) -> int:
    """
    掉落成功后的个数：按 MATERIAL_QTY_WEIGHTS（100:50:25）在 1～max_qty 中加权随机。
    max_qty 默认 3，即仅 1、2、3 三种可能。
    """
    max_qty = max(1, min(3, int(max_qty)))
    weights = list(MATERIAL_QTY_WEIGHTS[:max_qty])
    total = sum(weights)
    r = rng.random() * total
    acc = 0.0
    for k, w in enumerate(weights, start=1):
        acc += w
        if r <= acc:
            return k
    return max_qty


def _roll_zone_exclusive_material(zone_effective: str, rng: random.Random) -> Optional[Dict[str, Any]]:
    """各区域至多掉落一种独占材料：先判定掉落，再按 halving 权重抽数量。"""
    name = ZONE_EXCLUSIVE_MATERIAL.get(str(zone_effective))
    if not name:
        return None
    p = MATERIAL_ZONE_DROP_P_FOREST_TIER if str(zone_effective) in ("starter", "forest") else MATERIAL_ZONE_DROP_P_OTHER
    if rng.random() >= p:
        return None
    qty = _roll_material_qty_weighted_halving(rng)
    return {"mid": _new_id("mat", rng), "name": name, "qty": qty}


def _loot_for_zone(
    zone_id: str, enemy: Dict[str, Any], rng: random.Random, floor: int = 1
) -> Tuple[int, List[Dict[str, Any]], List[Dict[str, Any]]]:
    gold = 5 + int(rng.uniform(0, 1) * 25)
    mats: List[Dict[str, Any]] = []
    items: List[Dict[str, Any]] = []
    mat_z = _effective_zone_for_material(zone_id, floor)
    mdrop = _roll_zone_exclusive_material(mat_z, rng)
    if mdrop:
        mats.append(mdrop)

    # Potions（掉率下调）
    if rng.random() < 0.08:
        r2 = rng.random()
        if r2 < 0.68:
            mu = {"use": "heal_potion", "heal_pct": POTION_HP_PCT, "sell_price": _potion_unit_sell_price("heal_potion")}
            items.append({"item_id": _new_id("pot", rng), "name": "恢复药水", "qty": 1, "meta": mu})
        elif r2 < 0.88:
            mu = {"use": "mp_potion", "mp_pct": POTION_MP_PCT, "sell_price": _potion_unit_sell_price("mp_potion")}
            items.append({"item_id": _new_id("pot", rng), "name": "魔力药水", "qty": 1, "meta": mu})
        else:
            mu = {
                "use": "dual_potion",
                "heal_pct": POTION_DUAL_HP_PCT,
                "mp_pct": POTION_DUAL_MP_PCT,
                "sell_price": _potion_unit_sell_price("dual_potion"),
            }
            items.append({"item_id": _new_id("pot", rng), "name": "混合药水", "qty": 1, "meta": mu})
    # Q2+ 稀有药水：掉率显著低于普通药水（仅掉落，不在商店出售）
    if zone_id in ("forest", "mines", "coast", "throne") and rng.random() < 0.01:
        rr = rng.random()
        if rr < 0.42:
            mu = {
                "use": "full_heal_potion",
                "heal_pct": POTION_FULL_HP_PCT,
                "sell_price": _potion_unit_sell_price("full_heal_potion"),
            }
            items.append({"item_id": _new_id("pot", rng), "name": "特级恢复药水", "qty": 1, "meta": mu})
        elif rr < 0.84:
            mu = {
                "use": "full_mp_potion",
                "mp_pct": POTION_FULL_MP_PCT,
                "sell_price": _potion_unit_sell_price("full_mp_potion"),
            }
            items.append({"item_id": _new_id("pot", rng), "name": "特级魔力药水", "qty": 1, "meta": mu})
        else:
            mu = {
                "use": "golden_apple",
                "heal_pct": POTION_GOLDEN_HP_PCT,
                "mp_pct": POTION_GOLDEN_MP_PCT,
                "sell_price": _potion_unit_sell_price("golden_apple"),
            }
            items.append({"item_id": _new_id("pot", rng), "name": "金苹果", "qty": 1, "meta": mu})
    # 复活药水：仅 Q4/Q5 场景，极低概率（1%）
    if zone_id in ("coast", "throne") and rng.random() < 0.01:
        mu = {
            "use": "revive_potion",
            "revive_hp_pct": POTION_REVIVE_HP_PCT,
            "revive_mp_pct": POTION_REVIVE_MP_PCT,
            "sell_price": _potion_unit_sell_price("revive_potion"),
        }
        items.append({"item_id": _new_id("pot", rng), "name": "复活药水", "qty": 1, "meta": mu})
    return gold, items, mats


def dq_time_regen(state: Dict[str, Any], now_ts: Optional[int] = None) -> Dict[str, Any]:
    """
    被动恢复结算：若不进入旅店，按每 5 分钟 +2HP/+1MP/+5体力，
    单项到顶即停止恢复；同时对已招募队友也做同样 HP/MP 恢复。
    """
    state = copy.deepcopy(state)
    _ensure_meta_logs(state)
    if now_ts is None:
        now_ts = int(time.time())
    meta = state.setdefault("meta", {})
    last_ts = meta.get("last_regen_ts")
    if last_ts is None:
        meta["last_regen_ts"] = int(now_ts)
        return state
    last_ts = int(last_ts or 0)
    now_ts = int(now_ts or 0)
    if now_ts <= last_ts:
        return state

    elapsed = now_ts - last_ts
    ticks = elapsed // PASSIVE_REGEN_INTERVAL_SEC
    if ticks <= 0:
        return state

    # 推进计时器（避免战斗期间“离线挂机回血”）
    meta["last_regen_ts"] = last_ts + ticks * PASSIVE_REGEN_INTERVAL_SEC

    if state.get("phase") != "overworld":
        return state

    def _regen_unit(cur_hp: int, max_hp: int, cur_mp: int, max_mp: int) -> Tuple[int, int]:
        cur_hp = min(max_hp, max(0, int(cur_hp)))
        cur_mp = min(max_mp, max(0, int(cur_mp)))
        gain_hp = PASSIVE_REGEN_HP_PER_INTERVAL * ticks
        gain_mp = PASSIVE_REGEN_MP_PER_INTERVAL * ticks
        cur_hp = min(max_hp, cur_hp + gain_hp)
        cur_mp = min(max_mp, cur_mp + gain_mp)
        return cur_hp, cur_mp

    # 玩家
    old_hp = int(state.get("hp", 0) or 0)
    old_mp = int(state.get("mp", 0) or 0)
    old_stm = int(state.get("stamina", 0) or 0)
    state["hp"], state["mp"] = _regen_unit(
        state.get("hp", 0),
        int(state.get("max_hp", 1) or 1),
        state.get("mp", 0),
        int(state.get("max_mp", 1) or 1),
    )
    state["stamina"] = min(
        int(state.get("max_stamina", 1) or 1),
        int(state.get("stamina", 0) or 0) + PASSIVE_REGEN_STAMINA_PER_INTERVAL * ticks,
    )

    # 队友（无体力，只回 HP/MP）
    ally_old: List[Tuple[int, int]] = []
    allies = state.get("party_members", []) or []
    for mem in allies:
        ally_old.append((int(mem.get("hp", 0) or 0), int(mem.get("mp", 0) or 0)))
    for mem in state.get("party_members", []) or []:
        mem["hp"], mem["mp"] = _regen_unit(
            mem.get("hp", 0),
            int(mem.get("max_hp", 1) or 1),
            mem.get("mp", 0),
            int(mem.get("max_mp", 1) or 1),
        )

    changed = (
        int(state.get("hp", 0) or 0) != old_hp
        or int(state.get("mp", 0) or 0) != old_mp
        or int(state.get("stamina", 0) or 0) != old_stm
        or any(
            int(state.get("party_members", [])[i].get("hp", 0) or 0) != ally_old[i][0]
            or int(state.get("party_members", [])[i].get("mp", 0) or 0) != ally_old[i][1]
            for i in range(len(ally_old))
        )
    )
    if changed:
        # 只在确实发生过恢复时记日志，避免刷太多
        meta.setdefault("log", [])
        meta["log"].append(
            f"⏳ 被动恢复（{ticks} 次·每次5分钟）：HP+{PASSIVE_REGEN_HP_PER_INTERVAL * ticks}、"
            f"MP+{PASSIVE_REGEN_MP_PER_INTERVAL * ticks}、体力+{PASSIVE_REGEN_STAMINA_PER_INTERVAL * ticks}。"
        )
    return state


def _equipment_name_templates() -> Dict[str, List[str]]:
    # 含「力量/智慧/精准/敏捷/幸运/体力」的名称会触发 _sub_attr_hint_from_equip_name，使副属性与名字一致（与主属性冲突则仍随机副属）
    return {
        "weapon": ["木剑", "铁剑", "钢剑", "战斧", "手半剑", "智慧短刃", "敏捷匕首"],
        "shield": ["木盾", "铁盾", "塔盾", "骑士盾", "坚卫盾", "力量塔盾", "智慧圣盾", "敏捷轻盾"],
        "helmet": ["皮帽", "铁盔", "战盔", "力量战盔", "敏捷皮帽", "智慧冠", "法师冠"],
        "mail": ["皮甲", "锁甲", "板甲", "游侠外套", "轻型鳞甲", "力量板甲", "智慧链甲"],
        "belt": ["皮腰带", "力量腰带", "精准腰带", "射手扣带", "旅者束带", "智慧束腰", "敏捷绑带"],
        "accessory": ["铜戒", "银戒", "护符", "力量之戒", "智慧吊坠", "精准耳环", "敏捷挂坠", "幸运骨饰"],
    }


def _weighted_slot_pick(zone_id: str, rng: random.Random) -> str:
    if zone_id in ("starter", "forest"):
        bias = {"weapon": 0.20, "shield": 0.14, "helmet": 0.14, "mail": 0.22, "belt": 0.15, "accessory": 0.15}
    elif zone_id in ("mines",):
        bias = {"weapon": 0.18, "shield": 0.20, "helmet": 0.12, "mail": 0.24, "belt": 0.13, "accessory": 0.13}
    elif zone_id in ("coast",):
        bias = {"weapon": 0.14, "shield": 0.12, "helmet": 0.16, "mail": 0.18, "belt": 0.14, "accessory": 0.26}
    elif zone_id in ("throne",):
        bias = {"weapon": 0.16, "shield": 0.14, "helmet": 0.14, "mail": 0.18, "belt": 0.12, "accessory": 0.26}
    else:
        bias = {"weapon": 0.18, "shield": 0.15, "helmet": 0.14, "mail": 0.20, "belt": 0.14, "accessory": 0.19}
    r = rng.random()
    t = 0.0
    for s, w in bias.items():
        t += w
        if r <= t:
            return s
    return "weapon"


def _build_drop_equipment(
    zone_id: str,
    player_level: int,
    floor: int,
    rng: random.Random,
    weapon_role: Optional[str] = None,
    weapon_req_roles: Optional[List[str]] = None,
    forced_quality: Optional[str] = None,
    force_slot: Optional[str] = None,
) -> Dict[str, Any]:
    """随机生成掉落装备；武器可带「职业署名」限制。forced_quality 指定时固定该品质（须为已知档位）。
    force_slot 指定时固定部位（须为 EQUIPMENT_SLOTS 之一），用于教学等场景。"""
    plv = max(1, int(player_level))
    if force_slot and str(force_slot) in EQUIPMENT_SLOTS:
        slot = str(force_slot)
    else:
        slot = _weighted_slot_pick(zone_id, rng)
    quality = (
        str(forced_quality)
        if forced_quality and str(forced_quality) in QUALITY_MULT
        else _pick_quality(rng, slot, zone_id, floor)
    )

    main_attr = SLOT_MAIN_ATTR[slot]
    if slot == "weapon" and weapon_role:
        role_main_attr = {
            "warrior": "str",
            "hunter": "dex",
            "rogue": "agi",
            "mage": "int",
            "cleric": "int",
        }
        main_attr = role_main_attr.get(str(weapon_role), main_attr)
    base_main = 2 + plv // 3 + rng.randint(0, 2)
    mult = QUALITY_MULT.get(quality, 1.0)
    main_val = max(1, int(base_main * mult * rng.uniform(0.92, 1.08)))

    tmpl = _equipment_name_templates()
    base_name = rng.choice(tmpl.get(slot, ["装备"]))
    if slot == "weapon" and weapon_role:
        role_weapon_templates = {
            "warrior": ["战剑", "钢剑", "战斧", "手半剑", "力量重剑"],
            "cleric": ["祈愿法典", "神官法杖", "圣银权杖", "智慧祷言"],
            "mage": ["霜火长杖", "奥术长杖", "星隙法杖", "智慧法杖"],
            "hunter": ["猎弓", "长弓", "疾风弩", "精准猎弓"],
            "rogue": ["夜行双刃", "影刃短匕", "毒刃双匕", "敏捷短刀"],
        }
        base_name = rng.choice(role_weapon_templates.get(str(weapon_role), tmpl.get("weapon", ["武器"])))

    sub_hint = _sub_attr_hint_from_equip_name(base_name, main_attr)
    if sub_hint is not None:
        sub_attr = sub_hint
        sub_v = rng.randint(1, 3)
    else:
        sub_attr, sub_v = _roll_sub_attr(rng, main_attr)
    dungeon_floor = max(1, int(floor))
    floor_sub_bonus = max(0, dungeon_floor // 4)
    sub_val = max(1, int(sub_v * (0.85 + 0.15 * mult) * rng.uniform(0.9, 1.1)) + floor_sub_bonus)

    q_lab = QUALITY_CN.get(quality, "")
    meta: Dict[str, Any] = {
        "slot": slot,
        "quality": quality,
        "main_attr": main_attr,
        "main_val": main_val,
        "sub_attr": sub_attr,
        "sub_val": sub_val,
    }

    # 饰品稀有词条：
    # - 史诗及以上：随机 1 条战斗加成（攻击/闪避/免伤/暴击）+1%
    # - 传说：额外 1 条饰品特殊能力
    # - 至尊：额外 2 条饰品特殊能力
    if slot == "accessory":
        if quality in ("epic", "legend", "supreme"):
            meta.update(_roll_accessory_epic_extra(rng))
        if quality == "legend":
            sp_ids = _roll_accessory_special_ids(rng, 1)
            if sp_ids:
                meta["special_ids"] = sp_ids
                meta["special_names"] = [ACCESSORY_SPECIALS[s]["name"] for s in sp_ids if s in ACCESSORY_SPECIALS]
                meta["special_id"] = sp_ids[0]
                meta["special_name"] = ACCESSORY_SPECIALS[sp_ids[0]]["name"]
        elif quality == "supreme":
            sp_ids = _roll_accessory_special_ids(rng, 2)
            if sp_ids:
                meta["special_ids"] = sp_ids
                meta["special_names"] = [ACCESSORY_SPECIALS[s]["name"] for s in sp_ids if s in ACCESSORY_SPECIALS]
                meta["special_id"] = sp_ids[0]
                meta["special_name"] = ACCESSORY_SPECIALS[sp_ids[0]]["name"]
    elif slot in ("shield", "helmet", "mail", "belt"):
        # 非饰品、非武器：史诗/传说获得随机战斗词条
        if quality == "epic":
            meta.update(_roll_combat_percent_affix(rng, 0.01))
        elif quality == "legend":
            meta.update(_roll_combat_percent_affix(rng, 0.02))

    name: str
    if slot == "weapon" and weapon_role:
        role_cn = ROLE_CN.get(str(weapon_role), str(weapon_role))
        prefix = f"【{role_cn}专属】"
        name = f"「{q_lab}」{prefix}{base_name}" if quality != "normal" else f"{prefix}{base_name}"
        meta["req_roles"] = weapon_req_roles or [weapon_role]
        q_lv = _quality_bonus_level(quality)
        bonus_pct = round(q_lv * 0.01, 4)
        if bonus_pct > 0:
            if str(weapon_role) in {"warrior", "hunter", "rogue"}:
                meta["atk_bonus"] = bonus_pct
            elif str(weapon_role) == "mage":
                meta["spell_bonus"] = bonus_pct
            elif str(weapon_role) == "cleric":
                meta["heal_bonus"] = bonus_pct
    else:
        name = f"「{q_lab}」{base_name}" if quality != "normal" else base_name

    meta["sell_price"] = _compute_equip_sell_price(meta)
    return {"item_id": _new_id(slot, rng), "name": name, "qty": 1, "meta": meta}


def _grant_q2_wither_spoils(state: Dict[str, Any], choice_id: str, rng: random.Random) -> None:
    """枯萎之王战后三选一：对应传说 / 史诗 / 精良随机一件（选项文案不暴露档位）。"""
    qmap = {"q2_pick_a": "legend", "q2_pick_b": "epic", "q2_pick_c": "fine"}
    q = qmap.get(str(choice_id))
    if not q:
        return
    plv = max(1, int(state.get("level", 1) or 1))
    floor = max(1, int((state.get("dungeon") or {}).get("floor", 1) or 1))
    it = _build_drop_equipment("forest", plv, floor, rng, forced_quality=q)
    ok, _bad = dq_try_add_inventory(state, [it])
    meta = state.setdefault("meta", {})
    q_cn = QUALITY_CN.get(q, q)
    nm = it.get("name", "装备")
    if ok:
        meta.setdefault("log", []).append(f"晶屑凝成一件{q_cn}装备：{nm}。")
        _queue_unlock_notice(state, "🎁 枯萎余烬", [f"获得：{nm}"])
    else:
        meta.setdefault("log", []).append("⚠️ 背包已满，未能带走余烬化成的装备。")


def _grant_mainline_boss_spoils(state: Dict[str, Any], sid: str, choice_id: str, rng: random.Random) -> None:
    """Q2~Q5 Boss 后奖励幕：三选一随机装备（文案不直接暴露品质）。"""
    cfg = {
        "q2_forest_echo": {
            "zone": "forest",
            "title": "🎁 枯萎余烬",
            "ok_log": "晶屑凝成一件{q_cn}装备：{name}。",
            "full_log": "⚠️ 背包已满，未能带走余烬化成的装备。",
            "map": {"q2_pick_a": "legend", "q2_pick_b": "epic", "q2_pick_c": "fine"},
        },
        "q3_mines_crack": {
            "zone": "mines",
            "title": "🎁 熔核回响",
            "ok_log": "熔核裂纹淬出一件{q_cn}装备：{name}。",
            "full_log": "⚠️ 背包已满，未能带走熔核淬出的装备。",
            "map": {"q3_pick_a": "legend", "q3_pick_b": "epic", "q3_pick_c": "fine"},
        },
        "q4_tide_price": {
            "zone": "coast",
            "title": "🎁 潮汐遗馈",
            "ok_log": "潮汐泡沫结成一件{q_cn}装备：{name}。",
            "full_log": "⚠️ 背包已满，未能带走潮汐遗馈化成的装备。",
            "map": {"q4_pick_a": "legend", "q4_pick_b": "epic", "q4_pick_c": "fine"},
        },
        "q5_throne_last": {
            "zone": "throne",
            "title": "🎁 王座余辉",
            "ok_log": "王座余辉铸成一件{q_cn}装备：{name}。",
            "full_log": "⚠️ 背包已满，未能带走王座余辉化成的装备。",
            "map": {"q5_pick_a": "legend", "q5_pick_b": "epic", "q5_pick_c": "fine"},
        },
    }
    c = cfg.get(str(sid))
    if not isinstance(c, dict):
        return
    q = (c.get("map") or {}).get(str(choice_id))
    if not q:
        return
    plv = max(1, int(state.get("level", 1) or 1))
    floor = max(1, int((state.get("dungeon") or {}).get("floor", 1) or 1))
    it = _build_drop_equipment(str(c.get("zone", "starter")), plv, floor, rng, forced_quality=str(q))
    ok, _bad = dq_try_add_inventory(state, [it])
    meta = state.setdefault("meta", {})
    q_cn = QUALITY_CN.get(str(q), str(q))
    nm = it.get("name", "装备")
    if ok:
        meta.setdefault("log", []).append(str(c.get("ok_log", "获得一件{q_cn}装备：{name}。")).format(q_cn=q_cn, name=nm))
        _queue_unlock_notice(state, str(c.get("title", "🎁 Boss 遗馈")), [f"获得：{nm}"])
    else:
        meta.setdefault("log", []).append(str(c.get("full_log", "⚠️ 背包已满，未能带走Boss遗馈装备。")))


def _maybe_drop_equipment(
    zone_id: str,
    player_level: int,
    floor: int,
    rng: random.Random,
    weapon_focus_roles: Optional[List[str]] = None,
) -> Optional[Dict[str, Any]]:
    depth = max(0, floor - 1)
    base_chance = 0.08 + depth * 0.006 + max(0, player_level - 1) * 0.004
    base_chance = min(0.42, base_chance)
    if rng.random() > base_chance:
        return None
    weapon_role = None
    weapon_req_roles = None
    if weapon_focus_roles:
        weapon_role = str(rng.choice(weapon_focus_roles))
        # 与商店专属口径一致：掉落专属武器固定单职业
        weapon_req_roles = [weapon_role]
    return _build_drop_equipment(
        zone_id,
        player_level,
        floor,
        rng,
        weapon_role=weapon_role,
        weapon_req_roles=weapon_req_roles,
    )


def _weapon_focus_roles_for_enemy(enemy: Dict[str, Any]) -> List[str]:
    """根据怪物类型：掉落武器偏向的职业（用于署名限制）。"""
    mid = str(enemy.get("mid", ""))
    if mid in {"wraith", "sea_curse", "boss_sea_witch", "night_moth"}:
        return ["mage", "cleric"]
    if mid in {"skeleton", "witherling", "boss_witherling", "bog_worm", "wither_vine", "reef_crab"}:
        return ["rogue", "warrior"]
    if mid in {"miner_golem", "boss_golem", "throne_guard", "boss_throne_guard", "mine_spider"}:
        return ["hunter", "warrior"]
    return ["warrior", "hunter", "rogue"]


def _enemy_xp_and_drop(player_level: int, enemy: Dict[str, Any], rng: random.Random, zone_id: str, floor: int) -> Tuple[int, int, List[Dict[str, Any]], List[Dict[str, Any]]]:
    # XP scaling
    base = int((enemy["max_hp"] ** 0.5) * 2.6)
    enemy_lv = max(1, int(enemy.get("level", player_level) or player_level or 1))
    plv = max(1, int(player_level or 1))
    # 等级越高经验越高；并对“高于主角等级”的怪额外给经验补偿
    lv_mul = 1.0 + max(0, enemy_lv - 1) * 0.14
    lv_diff = max(0, enemy_lv - plv)
    # 越级奖励下调：控制在同级经验约 2~3 倍区间
    diff_mul = 1.0 + lv_diff * 0.12
    if lv_diff > 0:
        diff_mul *= (1.0 + 0.28 * lv_diff)
    xp = max(12, int(base * (0.85 + rng.random() * 0.4) * (0.92 + 0.08 * floor / max(1, floor)) * lv_mul * diff_mul))
    # bonus for boss
    if enemy["mid"].startswith("boss_"):
        xp = int(xp * 3.1)
    # 怪物等级低于主角3级及以上：不再获得经验
    if enemy_lv <= plv - 3:
        xp = 0
    bonus_gold, potions, mats = _loot_for_zone(zone_id, enemy, rng, floor)
    if _is_player_trivializing_zone(plv, zone_id):
        gold = 0
    else:
        gold = 8 + int(rng.uniform(0, 1) * 35)
        if enemy["mid"].startswith("boss_"):
            gold = int(gold * 3.4)
        gold += bonus_gold
    items = potions
    # equipment
    eq = _maybe_drop_equipment(zone_id, player_level, floor, rng, weapon_focus_roles=_weapon_focus_roles_for_enemy(enemy))
    if eq:
        items.append(eq)
    if str(enemy.get("mid")) == "boss_witherling":
        items.extend(_wither_boss_kill_extra_loot(rng))
    return xp, gold, items, mats


def dq_equip_item(state: Dict[str, Any], item_id: str) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state
    _ensure_equipped_slots(state)
    inv = state.get("inventory", [])
    item = None
    for it in inv:
        if it.get("item_id") == item_id and it.get("qty", 0) > 0:
            item = it
            break
    if not item:
        return state
    slot = (item.get("meta", {}) or {}).get("slot")
    if slot not in EQUIPMENT_SLOTS:
        return state
    # 职业署名限制（仅武器）
    req_roles = (item.get("meta", {}) or {}).get("req_roles")
    if slot == "weapon" and isinstance(req_roles, list) and req_roles:
        p_role = str(state.get("role", "warrior"))
        allow = any(p_role == str(r) for r in req_roles)
        if not allow:
            state.setdefault("meta", {}).setdefault("log", []).append(
                f"装备失败：{item.get('name', '武器')} 署名职业为「{'、'.join([ROLE_CN.get(str(r), str(r)) for r in req_roles])}」，你无法装备。"
            )
            return state
    # unequip existing
    old = state.get("equipped", {}).get(slot)
    # remove exactly one matched item (avoid deleting all duplicates with same item_id)
    rm_idx = next((idx for idx, itx in enumerate(inv) if itx is item), None)
    if rm_idx is None:
        rm_idx = next((idx for idx, itx in enumerate(inv) if itx.get("item_id") == item_id and int(itx.get("qty", 0) or 0) > 0), -1)
    if rm_idx is None or rm_idx < 0:
        return state
    del inv[rm_idx]
    state["inventory"] = inv
    state["equipped"][slot] = item
    if old:
        # add back to inventory
        state["inventory"].append(old)
    _recalc_player_from_equipment(state)
    slot_lab = SLOT_CN.get(slot, slot)
    state["meta"]["log"].append(f"🧷 你装备了：{item.get('name')}（{slot_lab}）。")
    return state


def dq_unequip_slot(state: Dict[str, Any], slot: str) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state
    _ensure_equipped_slots(state)
    if slot not in EQUIPMENT_SLOTS:
        return state
    old = state.get("equipped", {}).get(slot)
    if not old:
        return state
    if dq_inventory_slots_used(state) >= INVENTORY_MAX_SLOTS:
        state.setdefault("meta", {}).setdefault("log", []).append("背包已满，无法卸下（请先腾出格子）。")
        return state
    state["equipped"][slot] = None
    state.setdefault("inventory", []).append(old)
    _recalc_player_from_equipment(state)
    state["meta"]["log"].append(f"卸下装备：{old.get('name')}。")
    return state


def dq_member_equip_item(state: Dict[str, Any], member_mid: str, item_id: str) -> Dict[str, Any]:
    """给指定队友装备任意部位（武器支持职业署名限制）。"""
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state

    _ensure_attrs(state)
    _ensure_equipped_slots(state)

    members = state.get("party_members", []) or []
    mem = next((m for m in members if str(m.get("mid", "")) == str(member_mid)), None)
    if not mem:
        return state

    inv = state.get("inventory", [])
    item = None
    for it in inv:
        if it.get("item_id") == item_id and int(it.get("qty", 0) or 0) > 0:
            item = it
            break
    if not item:
        return state

    meta = item.get("meta", {}) or {}
    slot = str(meta.get("slot", ""))
    if slot not in EQUIPMENT_SLOTS:
        return state

    req_roles = meta.get("req_roles")
    if slot == "weapon" and isinstance(req_roles, list) and req_roles:
        m_role = str(mem.get("role", ""))
        allow = any(m_role == str(r) for r in req_roles)
        if not allow:
            state.setdefault("meta", {}).setdefault("log", []).append(
                f"装备失败：{item.get('name', '武器')} 署名职业为「{'、'.join([ROLE_CN.get(str(r), str(r)) for r in req_roles])}」，{mem.get('name','队友')}无法装备。"
            )
            return state

    # 从背包仅移除一件（避免同 item_id 重复时整组被删）
    rm_idx = next((idx for idx, itx in enumerate(inv) if itx is item), None)
    if rm_idx is None:
        rm_idx = next((idx for idx, itx in enumerate(inv) if itx.get("item_id") == item_id and int(itx.get("qty", 0) or 0) > 0), -1)
    if rm_idx is None or rm_idx < 0:
        return state
    del inv[rm_idx]
    state["inventory"] = inv

    mem.setdefault("equipped", {s: None for s in EQUIPMENT_SLOTS})
    old_item = mem.get("equipped", {}).get(slot)
    mem["equipped"][slot] = item

    if old_item:
        ok, bad = dq_try_add_inventory(state, [old_item])
        if bad:
            state.setdefault("meta", {}).setdefault("log", []).append("背包已满，旧装备丢弃。")

    # 重算成员战斗面板：保留当前 HP/MP，只截断到新上限
    _recalc_member_stats(mem, int(state.get("level", mem.get("level", 1)) or 1), state.get("party_armory"), state.get("resources"))

    slot_lab = SLOT_CN.get(slot, slot)
    state.setdefault("meta", {}).setdefault("log", []).append(f"🧷 {mem.get('name','队友')} 装备了：{item.get('name','装备')}（{slot_lab}）")
    return state


def dq_member_unequip_slot(state: Dict[str, Any], member_mid: str, slot: str) -> Dict[str, Any]:
    """卸下队友指定部位。"""
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state

    members = state.get("party_members", []) or []
    mem = next((m for m in members if str(m.get("mid", "")) == str(member_mid)), None)
    if not mem:
        return state

    if slot not in EQUIPMENT_SLOTS:
        return state

    mem.setdefault("equipped", {s: None for s in EQUIPMENT_SLOTS})
    old_item = mem.get("equipped", {}).get(slot)
    if not old_item:
        return state

    if dq_inventory_slots_used(state) >= INVENTORY_MAX_SLOTS:
        state.setdefault("meta", {}).setdefault("log", []).append("背包已满，无法卸下队友装备。")
        return state

    state.setdefault("inventory", []).append(old_item)
    mem["equipped"][slot] = None
    # 重算成员战斗面板：保留当前 HP/MP，只截断到新上限
    _recalc_member_stats(mem, int(state.get("level", mem.get("level", 1)) or 1), state.get("party_armory"), state.get("resources"))
    slot_lab = SLOT_CN.get(slot, slot)
    state.setdefault("meta", {}).setdefault("log", []).append(f"卸下队友装备：{mem.get('name','队友')}（{slot_lab}）。")
    return state


def dq_member_equip_weapon(state: Dict[str, Any], member_mid: str, item_id: str) -> Dict[str, Any]:
    """兼容旧调用：队友装备武器。"""
    return dq_member_equip_item(state, member_mid, item_id)


def dq_member_unequip_weapon(state: Dict[str, Any], member_mid: str) -> Dict[str, Any]:
    """兼容旧调用：队友卸下武器。"""
    state = dq_member_unequip_slot(state, member_mid, "weapon")
    return state


def dq_shop_catalog() -> List[Dict[str, Any]]:
    return copy.deepcopy(DQ_SHOP_ITEMS)


def dq_shop_main_val_at_purchase(hero_level: int) -> int:
    """商店购入的装备/职业武器主属性数值：购买时主角等级÷3 向下取整，写入物品后不再随升级变化。"""
    return max(0, int(hero_level) // 3)


def dq_shop_sub_bonus_from_dungeon_floor(dungeon_floor: int) -> int:
    """商店制式装备副属性额外点数：当前地牢记录层数÷4 向下取整（主线未进地牢时多为 1 层→0）。"""
    return max(0, int(max(1, int(dungeon_floor or 1))) // 4)


def _shop_make_equip_item(
    defn: Dict[str, Any],
    rng: random.Random,
    main_val: int,
    purchase_hero_level: int,
    dungeon_floor: int = 1,
) -> Dict[str, Any]:
    slot = str(defn["slot"])
    main_attr = SLOT_MAIN_ATTR[slot]
    sub_attr, sub_val = _roll_sub_attr(rng, main_attr)
    _hint = _sub_attr_hint_from_equip_name(str(defn.get("name", "") or ""), main_attr)
    if _hint is not None:
        sub_attr = _hint
        sub_val = rng.randint(1, 3)
    sub_floor = dq_shop_sub_bonus_from_dungeon_floor(dungeon_floor)
    meta: Dict[str, Any] = {
        "slot": slot,
        "quality": "normal",
        "main_attr": main_attr,
        "main_val": int(main_val),
        "sub_attr": sub_attr,
        "sub_val": max(1, int(sub_val) + sub_floor),
        "shop_purchase_hero_level": int(purchase_hero_level),
    }
    meta["sell_price"] = _compute_equip_sell_price(meta)
    return {"item_id": _new_id("buy", rng), "name": defn["name"], "qty": 1, "meta": meta}


def dq_sell_item(state: Dict[str, Any], item_id: str, sell_qty: Optional[int] = None) -> Dict[str, Any]:
    """出售背包内药水/材料/未穿戴装备；战斗中不可用。"""
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state
    _ensure_equipped_slots(state)
    inv = state.get("inventory", [])
    idx = None
    for i, it in enumerate(inv):
        if it.get("item_id") == item_id:
            idx = i
            break
    if idx is None:
        return state
    it = inv[idx]
    meta = it.get("meta") or {}
    q = int(it.get("qty", 0) or 0)
    if q <= 0:
        return state

    slot = meta.get("slot")
    if slot in EQUIPMENT_SLOTS:
        raw_price = int(meta.get("sell_price") or _compute_equip_sell_price(meta))
        price = _apply_sell_price_ratio(raw_price)
        inv.pop(idx)
        state["inventory"] = inv
        state["gold"] = int(state.get("gold", 0) or 0) + price
        state.setdefault("meta", {}).setdefault("log", []).append(f"💰 出售 {it.get('name')}，+{price} 金币。")
        _recalc_player_from_equipment(state)
        return state

    if meta.get("use") in BATTLE_POTION_USES:
        raw_unit = int(meta.get("sell_price") or _potion_unit_sell_price(str(meta.get("use", ""))))
        unit = _apply_sell_price_ratio(raw_unit)
        sq = q if sell_qty is None else min(q, max(1, int(sell_qty)))
        gain = unit * sq
        nq = q - sq
        if nq <= 0:
            inv.pop(idx)
        else:
            it["qty"] = nq
        state["inventory"] = inv
        state["gold"] = int(state.get("gold", 0) or 0) + gain
        state.setdefault("meta", {}).setdefault("log", []).append(f"💰 出售 {it.get('name')} ×{sq}，+{gain} 金币。")
        return state

    if meta.get("kind") == "material":
        mname = str(meta.get("material_name", ""))
        raw_unit = int(meta.get("sell_price") or _material_unit_sell_price(mname))
        unit = _apply_sell_price_ratio(raw_unit)
        sq = q if sell_qty is None else min(q, max(1, int(sell_qty)))
        gain = unit * sq
        nq = q - sq
        if nq <= 0:
            inv.pop(idx)
        else:
            it["qty"] = nq
        state["inventory"] = inv
        state["gold"] = int(state.get("gold", 0) or 0) + gain
        state.setdefault("meta", {}).setdefault("log", []).append(f"💰 出售 {it.get('name')} ×{sq}，+{gain} 金币。")
        return state

    state.setdefault("meta", {}).setdefault("log", []).append("该物品无法出售。")
    return state


def dq_buy(state: Dict[str, Any], shop_key: str, rng: random.Random) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state
    _ensure_equipped_slots(state)
    defn = next((x for x in DQ_SHOP_ITEMS if x.get("key") == shop_key), None)
    if not defn:
        return state
    price = int(defn["price"])
    if int(state.get("gold", 0) or 0) < price:
        state.setdefault("meta", {}).setdefault("log", []).append(f"钱不够，无法购买（{defn['name']} 需 {price} 金币）。")
        return state
    hero_lv = max(1, int(state.get("level", 1) or 1))
    dungeon_floor_buy = max(1, int((state.get("dungeon") or {}).get("floor", 1) or 1))
    shop_main = dq_shop_main_val_at_purchase(hero_lv)
    if defn["kind"] == "potion":
        pu = str(defn.get("potion_use", "heal_potion"))
        meta_p: Dict[str, Any] = {"use": pu}
        if pu == "heal_potion":
            meta_p["heal_pct"] = POTION_HP_PCT
        elif pu == "mp_potion":
            meta_p["mp_pct"] = POTION_MP_PCT
        elif pu == "dual_potion":
            meta_p["heal_pct"] = POTION_DUAL_HP_PCT
            meta_p["mp_pct"] = POTION_DUAL_MP_PCT
        else:
            meta_p = {"use": "heal_potion", "heal_pct": POTION_HP_PCT}
        meta_p["sell_price"] = _potion_unit_sell_price(meta_p.get("use", "heal_potion"))
        it = {"item_id": _new_id("pot", rng), "name": defn["name"], "qty": 1, "meta": meta_p}
    elif defn["kind"] == "equip":
        it = _shop_make_equip_item(defn, rng, shop_main, hero_lv, dungeon_floor_buy)
    elif defn["kind"] == "party_weapon":
        role = str(defn.get("role", ""))
        role_main_attr = {
            "warrior": "str",
            "cleric": "int",
            "mage": "int",
            "hunter": "dex",
            "rogue": "agi",
        }
        main_attr = role_main_attr.get(role, "str")
        main_val = int(shop_main)
        sub_attr, _ = _roll_sub_attr(rng, main_attr)
        _pw_hint = _sub_attr_hint_from_equip_name(str(defn.get("name", "") or ""), main_attr)
        if _pw_hint is not None:
            sub_attr = _pw_hint
        sub_pw = max(1, 1 + dq_shop_sub_bonus_from_dungeon_floor(dungeon_floor_buy))
        meta_pw: Dict[str, Any] = {
            "slot": "weapon",
            "quality": "normal",
            "main_attr": main_attr,
            "main_val": main_val,
            "sub_attr": sub_attr,
            # 专属武器：基础副属性 +1，另加地牢层÷4
            "sub_val": sub_pw,
            "req_roles": [role],
            "shop_purchase_hero_level": int(hero_lv),
            "atk_bonus": float(defn.get("atk_bonus", 0.0) or 0.0),
            "spell_bonus": float(defn.get("spell_bonus", 0.0) or 0.0),
            "heal_bonus": float(defn.get("heal_bonus", 0.0) or 0.0),
        }
        meta_pw["sell_price"] = _compute_equip_sell_price(meta_pw)
        it = {"item_id": _new_id("buy", rng), "name": defn.get("name", "职业武器"), "qty": 1, "meta": meta_pw}
    elif defn["kind"] == "respec_orb":
        it = {
            "item_id": _new_id("orb", rng),
            "name": defn["name"],
            "qty": 1,
            "meta": {"kind": "respec_orb"},
        }
    elif defn["kind"] == "talent_respec_orb":
        it = {
            "item_id": _new_id("orb", rng),
            "name": defn["name"],
            "qty": 1,
            "meta": {"kind": "talent_respec_orb"},
        }
    else:
        return state
    ok, bad = dq_try_add_inventory(state, [it])
    if bad:
        state.setdefault("meta", {}).setdefault("log", []).append("背包已满，无法购买。")
        return state
    state["gold"] = int(state.get("gold", 0) or 0) - price
    state.setdefault("meta", {}).setdefault("log", []).append(f"🛒 购入：{defn['name']}（-{price} 金币）。")
    _recalc_player_from_equipment(state)
    return state


def dq_clue_count(state: Dict[str, Any]) -> int:
    res = state.get("resources") or {}
    found = res.get("clues_found") or []
    return len({str(x) for x in found if str(x)})


CLUE_ZONE_DEFS: Dict[str, List[Dict[str, str]]] = {
    "starter": [
        {"id": "q1_old_well_mark", "title": "古井边的三道划痕", "desc": "井沿下方三道划痕，像某人留下的方向暗语。", "story": "你在破晓村外那口被藤蔓缠住的古井旁停下脚步。井口石圈冰冷，月色斜落，像一枚沉默的瞳孔注视着每个将远行的人。村里的老人说，这口井在王都尚未陷落时就已存在，井水曾映出王旗、婚礼与丰收，也映出过战火后的灰烬。你俯身时，看见井沿内侧有三道几乎被岁月磨平的划痕，深浅不一，间距却异常整齐。它们不是野兽留下的，更像某种仓促中的记号：第一道朝北偏东，第二道指向林地边缘，第三道则落在无人认领的旧驿道方向。你试着把三道划痕连成线，脑海里浮现出一条绕开巡游怪群、却必经荒坟与断桥的隐路。更奇怪的是，当你指尖触到第三道痕时，井底传来极轻的回音，像有人隔着很远的年代低声提醒，你忽然感觉到这声音似乎很是熟悉，有点像姐姐的呼唤，但是缺少了姐姐那种温柔和提醒，相反让你感觉到是刻骨的寒冷，指引着你离开这座城镇，这难道是姐姐留给你的暗号么？你并不好决定，在井边你迟疑的思考着"},
        {"id": "q1_dawn_banner", "title": "曾经往事", "desc": "木塔残旗与旧绣线里，藏着与姐姐年少时的约定。", "story": "村口木塔上的破晓旗早已褪色，风从裂口里穿过，发出像叹息又像低语的声音。你攀上摇晃的梯板，不是为了看旗面写了什么，而是旗角那一道歪歪扭扭的针脚——那是姐姐的手艺。许多年前，你们曾在这塔下拉钩：谁先离开村子，就要在旗上留一条只有自己能认出的记号；若有一天回来，看见记号还在，就说明另一个人没有忘记。她缝进暗纹里的是一句很轻的话：“往前走，别回头，但别把心弄丢了。”你指尖抚过褪色的线，往事像潮水涌上来：她替你挡过风雨，也替你扛过责骂；你答应过她，无论世界变成什么样，都要把“还能相信的人”留在身边。但是如今旗上居然出现了另外2个奇怪的符号，字迹是新的，但在日晒雨淋中，已经模糊不清，只能隐隐约约的看到零零散散的几笔划和几乎被雨水冲没的小字——像约定，也像未寄出的家书。风再次掀起布角，拍在你手背上，像姐姐最后一次拍你肩膀那样用力又克制。"},
        {"id": "q1_guard_diary", "title": "守夜人的最后一页", "desc": "札记写道：六芒星会指引神的孩子。", "story": "你在古井旁倒塌的岗亭里翻到一本发霉的守夜日志。前面的页码大多在记天气、巡逻、口粮与火把消耗，字迹平稳得像一段再普通不过的村庄日常。直到最后几页，墨色开始发散，笔画也出现断裂：北侧林缘出现不明脚印；夜里听见不是狼也不是人的叫声；第二批巡路人迟迟未归。最后一页只剩半张，边缘被火烫出卷曲的黑痕。你小心摊平，看到那句几乎写进纸纤维里的话——“别靠近进那片森林，除非你是神的孩子”后面本应还有内容，却只剩一道急促的墨痕，像执笔者在回头时被什么打断。你盯着这行字很久，忽然读出了另一层意思：守夜人并不是在劝退，而是在告诫“独行的勇气”并不等于“能活着回来”。结界的外面也许是混沌的世界，诅咒会沿河谷扩散，矿脉会因贪婪而失控，海岸会因仪式而失去节律。任何一个人都可能在错误时机变成下一段日志中的缺席者。你合上日志时，岗亭外风声忽然变轻，像某位早已离开的守夜人终于把嘱托递到了正确的人手里。你把这页内容抄入手册，并在旁边写下自己的回应：姐姐，我会找到你的。"},
    ],
    "forest": [
        {"id": "q2_root_whisper", "title": "树根下的呢喃", "desc": "同一句求救声在森林中反复回响，像被困太久的梦。", "story": "离开破晓村，就去了西边记载中的枯木森林，村里人喜欢称呼为“诅咒森林”，森林深处没有真正的静默。你蹲下身时，潮湿泥土下传来一阵断续的低语，像许多喉咙在同一口气里重复一个词：“放了我”。你拨开落叶，露出互相缠绕的粗根，纹理之间竟夹着细小骨片与旧织带。村里的传说说，瘴气最初不是天灾，而是一场失败封印导致的，许多人并非死于瘴气，而是死在“森林低语”的恐惧里。你把耳朵贴近树根，低语突然清晰，变成不同年龄、不同口音的人声，像整片森林在替失踪者说遗言。你本能地后退半步，却又被一种更强烈的念头拉住：这些声音不是要拖人下去，而是在寻找能听见它们的人。你沿根系摸索，发现其中一段刻着古老的巡林符号，恰好与破晓村古井划痕的第一道方向吻合。两处线索在此刻连上，像世界在暗处缓慢拼接自己的真相。你忽然明白，森林并非单纯的阻止人们进入，它可能是是世界变异最早的地方；可能是这场回流灾厄向外扩散的后果。那些低语在你起身时渐渐散去，只剩一句几乎听不见的话——“带我们走出去。”"},
        {"id": "q2_moss_route", "title": "苔色指引图", "desc": "苔纹拼成一张路径图，指向枯萎森林的深处。", "story": "你在一面倾倒石碑上看见苔藓以异常整齐的方式生长。最初它只是杂乱绿斑，可当阳光从枝隙斜照，明暗交错，纹路忽然像一张压缩过的指引图：三条主线、两处回避区、一段必须在暮色前通过的窄谷。你伸指描摹，发现每一处转折都对应附近树干上的旧刀痕，显然这是有人有意留下的路线编码。石碑底部还压着半枚破损铜扣，铸着王都旧军团徽记，说明最早进入林心的不只是猎人，还有曾执行封锁任务的正规队伍。可他们最终为什么全数撤离，档案又为何在村里被抹去？你顺着苔图推演，终点恰落在“神秘”可能盘踞的腐木祭坛附近。那不是一条最快的路，却是伤亡最少的路——绕开巨型孢子群，避开夜行藤怪，保留体力应对某些严峻的战斗。你意识到，这份“自然写成的地图”似乎是姐姐留给你的教程：为什么王国的军队在这里全军覆没了，因为这些提示有很多是你小时候和姐姐只有彼此才知道的俚语，正常人看这段信息只会觉得是一段无用的信息，但是对于你来说确是重要的提醒。你回头望向来路，村庄方向只剩一缕灰蓝色炊烟，而更远的矿坑天际已有赤光浮动。主线的每一幕都在逼近，时间并不站在你这边。你把苔图完整誊录进手册，旁边写下警语：若路看起来太顺，先怀疑那是不是陷阱；若路看起来太难，先确认它是否能活着抵达终点。"},
        {"id": "q2_elk_totem", "title": "鹿灵失落图腾", "desc": "图腾背面刻着古井到林心的细线，像指引寻找姐姐的路。", "story": "在一片被风吹得东倒西歪的蕨丛后，你找到一座半埋在泥里的鹿角图腾。木头已经发黑，角端裂开，却仍保留着祭祀涂料的痕迹。你把它翻过来，背面刻着一组细线：起点是古井，途经破晓旗塔与林缘旧桥，终点指向森林中心一处被圈出的空地。那条线极细，却比任何地图都坚定，像有人在失去力气前把“回去的路”最后确认了一遍。图腾侧边还有几道短刻，记录着潮汐月相与风向变化，与你在海岸听过的老航图方法几乎一致。你忽然意识到，这个是一篇姐姐小时候教过你的童谣，童谣传唱的线索，散落在不同地图，等待后来者重新拼起。图腾握在手里很轻，却让你第一次真正感到姐姐可能就在不远的地方等你；你若听懂这童谣，就可能改写自己和同伴后续的命运。远处林心传来低沉吼声，像某个古老存在被惊动。你将图腾重新包好，背在身后，心里多了一个念头：森林的腐朽的原因也许就在眼前，是某个未知的魔物主宰着这片森林，是时候解放这片区域了，童谣里面传唱的，是这片森林原来的名字“黎明之森”"},
    ],
    "mines": [
        {"id": "q3_crack_sound", "title": "地缝里的倒计时", "desc": "裂隙回声有固定节律，像下一次塌方的前奏。", "story": "黎明之森解放之后，随着指引去海边，途径一片废弃的矿坑，裂缝深处泛着不自然的赤光。你停在断轨旁，听见地底传来规律震颤：三短、一长、两短，随后是石屑簌簌落下。起初你以为是随机塌方，可当这节律第三次重复，你意识到那更像倒计时。矿工们曾靠敲击声判断支柱承压，如今整座矿坑像一台失控的巨鼓，把“下一次崩塌”的时间提前写在空气里。你贴着岩壁前进，手掌能感到热度一波波传来，仿佛岩层下有巨大心脏在跳。传闻中的熔岩巨像也许并非凭空诞生，而是长期过采、魔能残渣与封印破损共同催出的灾祸形态。你忽然理解森林里那些求救低语为何一路延伸到这里：灾厄从来不是单点，它会沿着人类最贪婪、最脆弱的裂缝扩散。你把这段节律记成符号，发现它恰好能用于预测短时落石窗口，为之后突入深层争取十几秒生机。十几秒在平时毫无意义，但足够决定一支队伍是全员撤离还是集体埋葬。你抬头望向上方断裂的吊桥，心里第一次生出一种清醒的恐惧：自己的能力可能决定着矿井下众多人的存亡，自己肩负的是沉重的生命。"},
        {"id": "q3_black_ledger", "title": "烧焦工账残页", "desc": "矿车编号与失踪矿工名单一一对应，真相被人抹过。", "story": "你在熄灭的炉槽旁捡到一叠被火烤卷的工账残页，纸边发脆，稍用力就会碎成灰。账页前半还在记录最普通的出勤、矿车载重与工资扣罚，后半却突然改成一串难懂代号。你对照矿车编号与村里失踪名单，发现它们一一对应：某号车最后一次入坑后，负责那班的矿工就在村册里被划成“迁出”或“病亡”，但没有任何葬礼记录。更诡异的是，账页上多次出现“深井回收”字样，后面接的是非标准工时与封口费金额。你想起海岸线索里提过的“疏散路径暗码”，想起森林里旧军团撤离痕迹，三个区域在此刻被同一条线穿透——有人长期知道灾厄扩散，却选择掩盖真相，把普通人当作可替换的损耗。你心里涌起怒意，却又被一种更冷的现实压住：仅凭愤怒无法改变战局，必须把证据带出矿坑，才能让后续城镇与队伍做出正确防灾部署。你将残页按编号整理，并在手册标注“优先保护档案袋，战斗时不得丢失”。这片土地是继续被谎言吞没，还是终于有人愿意承认代价、重建秩序。矿道尽头忽然传来金属断裂声，你把残页塞进防水囊，知道自己已经没有回头路。"},
        {"id": "q3_ember_compass", "title": "余烬指针", "desc": "这枚罗盘只在高温时转向，直指巨像沉睡区。", "story": "在废弃升降井旁，你找到一枚外壳烧黑的罗盘。它在常温下像坏掉的玩具，指针僵在原地，直到你靠近熔岩裂缝，针尖突然抖动并稳定指向西南。你试着后退，指针又慢慢归零；再次靠近，方向再次锁定。它不是测磁装置，而是测“热压场”的旧工程仪，专门用于判断地下熔流主脉。罗盘背面刻着一句几乎看不清的话：“光，呼吸。”你按这提示观察周围热浪，发现裂缝喷涌并非持续，而是像巨兽呼吸般有节律起伏。把罗盘方向与呼吸间隔叠在一起，便能推断熔岩巨像的沉睡区与苏醒周期。你忽然想到，这枚工具或许曾属于最后一批试图封坑的人，他们没能活着离开，却把“怎么活着接近核心”的方法留了下来。你抬眼望向矿坑深部，赤红雾气像幕布一样翻卷，身后远处隐约能听到地表风声。已经从“冒险者成长”变成“与灾难竞速”：若你错过窗口，巨像会在最糟时机醒来；若你把握住窗口，就能在代价可控范围内结束这幕灾祸。你把余烬罗盘挂在胸前，感受它随着热浪轻微震动，像一个沉默却可靠的同伴。此刻你终于明白，所谓传奇从不是天赋赋予，而是一次次在崩坏边缘把细小情报拼成生路。"},
    ],
    "coast": [
        {"id": "q4_tide_note", "title": "潮线手稿", "desc": "潮线标注出女巫咏唱的空档，像海给你的机会。", "story": "幽影海岸的潮汐不再遵守月相。你在坍塌码头下找到一卷被盐晶包裹的手稿，展开后是一张密密麻麻的潮线图：每一道潮峰都标着时间、风向与异常回旋区，其中三段空白被朱笔圈出，旁边写着“咏唱断点”。你尝试比对最近几次海浪节律，发现这三段空白正对应潮汐女巫施术后必须换息的极短窗口。那意味着她并非无懈可击，只是普通人从未掌握过“何时出手”。手稿末页还夹着一枚退色印章，署名是早年海防测绘官。原来在王都失序前，海岸曾有一整套严谨的观测体系，后来被战争与恐慌打散，才让“超自然灾祸不可抵抗”的传言占了上风。你把手稿摊在石上，海风吹得纸角颤动，仿佛多年后终于有人再次阅读这份不该被遗忘的工作。你想起森林与矿坑里的线索：每一幕都有人提前看见风险，也有人努力留下应对方法；真正让世界失控的，不只是怪物本身，还有背后隐身的力量在推动。不知道为何姐姐要把海岸线的港口作为下一个传递信息的中转站，但是既然到了这里，就要把那位自以为掌控海潮的女巫从高台上拉回现实。"},
        {"id": "q4_lighthouse_oil", "title": "灯塔旧配方", "desc": "老守夜人留下的油料配方，足够照亮整夜风浪。", "story": "你在废弃灯塔底层找到一只密封铜罐，里面塞着油渍浸透的配方纸。配方并不复杂：海藻脂、鲸蜡渣、矿坑提炼的轻焦油，以及一种只在破晓村湿地生长的苦香草。比例旁边写着“风暴夜也不可灭”。你按纸上的比例在临时炉里试配，点燃后火焰并不明亮，却异常稳定，像一只安静却固执的眼睛。灯塔守夜人的笔记夹在后页：当海岸出现不自然逆潮时，不要急着召集渔船，先点起高塔，让所有离岸者看见“还有归航坐标”。这句话让你喉咙发紧。你突然明白，所谓守护不总是挥剑冲锋，有时只是先把“方向”保住。更重要的是，配方里出现的材料横跨三个区域：村庄草药、矿坑焦油、海岸海藻。世界观在此处再次闭环——这片大陆的生存本来就依赖区域协作，而灾厄恰恰靠切断协作来扩大伤口。若未来可以重建秩序，这些旧技术或许会比任何庆功词都更有价值。夜色压向海面，远处隐约传来女巫咏唱般的低频震鸣。你点起试验灯，昏黄光柱穿过雾幕，照出一条狭窄却真实的返港线。那一刻你确信，哪怕未来仍艰险，只要有人愿意持续点灯，黑潮就永远无法彻底吞没人群。"},
        {"id": "q4_shell_code", "title": "贝壳密语", "desc": "贝纹拼出的暗码，记录了港口疏散的安全路径。", "story": "港湾浅滩上散落着许多裂开的白贝。你本想捡几枚做标记，却在其中一枚内壁看见细小刻痕：三短两长，重复三次。你继续搜集，发现不同贝壳的纹路可以拼成一组完整暗码，格式和矿坑工账中的代号规则惊人相似。把它们按潮位顺序排列后，解出的竟是“港口疏散路径”：先走旧盐仓背街，再绕灯塔斜坡，最后从北侧断堤离岸，避开女巫常驻吟唱区。你蹲在礁石间，海浪拍上来又退下去，像在重复某种不被记载的历史。显然曾有人在最混乱时试图组织撤离，并把路线藏在最不起眼、最不易被敌方注意的介质里。你想起木塔残旗上与姐姐的约定，想起守夜日志里中断的句子，忽然明白“未归者”不只是失败者，很多人是在给后来者争取时间。贝壳暗码还有一段附注：“若看见三次红闪，说明北堤已失守，改走内湾旧渔道。”这条应急分支让你背脊发凉——写下它的人很可能亲历过一次几乎全灭的夜晚。你把暗码完整誊抄，并在队伍笔记里标成“非战斗关键情报”。未来你或许会在与灾厄战前组织多地撤离，这些看似边角的线索将成为拯救平民的硬依据。海风带着咸味灌进胸腔，你收起最后一枚贝壳，心里只剩一个念头：你不是来见证末日的，你是来把幸存路径重新交回人群手里的，也许这就是姐姐一直想传达给你的信仰。"},
    ],
    "throne": [
        {"id": "q5_gate_rune", "title": "王座门廊旧符", "desc": "残符是警告还是暗示。", "story": "撤离了海岸线，渡船达到指引之岛，灾厄来临之前，王座地牢门廊的石柱就矗立在岛屿的中心，仿佛每一代挑战者都在这里被迫停下。你在最左侧断柱背面摸到一段残符，线条断裂却结构完整，明显不是装饰纹样，而是用于“削弱护甲共鸣”的古战术铭文。你按顺序描摹，符纹竟在掌下微微发热，随后迅速冷却，像只愿短暂回应仍然理解旧规则的人。你立刻想到王座守卫那层近乎不讲理的防护：硬拼会被拖入消耗战，而残符正提供了一个极短破防窗口。到此刻似乎姐姐的线索已经断了，原本一路上留下印记也因为海岸线的升潮断了，也许王座的古城，是寻找到姐姐新线索的希望，你不想失去方向，还是决定和队友踏入地下王座"},
        {"id": "q5_mirror_piece", "title": "裂镜残片", "desc": "镜中映出的不是自己，而是过去。", "story": "你在王座回廊尽头捡到一块裂镜残片。镜面蒙着灰，却能在火把下映出异常清晰的画面：不是你现在所处的走廊，而是一场早年的溃败。镜中人穿着旧王都制式甲，队形本来完整，却在守卫的连续冲锋下瞬间断裂。有人想回头救同伴，却被后排混乱挤散；有人急于冲锋终结战斗，反而触发了第二重机关。你看着这一幕，像在旁观一堂迟到多年的失败复盘课。残片边缘刻着极细的注记：“恐惧会让人忘记队形，愤怒会让人忘记节奏。”你把它翻到背面，发现还有一段磨损严重的坐标符号，恰好对应王座厅内两处可短暂停驻的安全角。你终于明白这不是诅咒物，而是训练用战术镜，被后人误当成不祥遗物。一路以来你收集的线索多半指向“去哪儿”，而这块裂镜第一次明确告诉你“到那里之后如何不重蹈覆辙”。你把镜片贴近胸甲，镜片居然开始播放一段影片，影片中你看到了姐姐，坐在王座的中心，仿佛在开口说着一些什么，那表情熟悉又陌生，当你想仔细观看的时候，景象却消失了，你收起镜片，反复擦拭却没能再次呈现刚才的景象"},
        {"id": "q5_last_oath", "title": "终誓之湮", "desc": "这份誓言说明你的前方不是荣耀，而是托付。", "story": "在王座后厅的石匣里，你找到一卷被蜡封保存的手抄誓文。封蜡印记早已破碎，但纸张依然完整，显然有人刻意把它藏在最不容易被战火波及的位置。誓文开头并不宏大，只写着几条朴素的约定：我亲爱的弟弟，能找到这里，说明你的努力有目共睹，继续向着王座之剑指引的方向来寻找我吧，我在世界的尽头等你。你越读越慢，仿佛血液都已经凝固，这似乎是姐姐可以留下给你的线索，你有太多的疑问了，第一次对姐姐的身份产生了莫名的恐慌，姐姐还是那个熟悉的善良的爱着自己的姐姐么？我不置可否，因为这景象与自己印象中的姐姐完全不同。你抬头，第一次以“英雄”而并非是“弟弟”的身份走向那道门。"},
    ],
}

CLUE_STEP_CHANCES: Dict[str, List[float]] = {
    # 每个 Q（地图）单独计数：第1条 > 第2条 > 第3条（与 clues_found 里「本图线索 id」数量对应，跨图互不影响）
    "starter": [0.68, 0.22, 0.15],
    "forest": [0.72, 0.24, 0.14],
    # 第 3 条原 0.055 与「仅未遇敌才掷骰」叠加后期望过低；略上调便于收尾（仍非必出）
    "mines": [0.63, 0.22, 0.16],
    "coast": [0.60, 0.20, 0.12],
    "throne": [0.56, 0.18, 0.11],
}

# 探索未遇敌时，先掷此概率才会进入「小事件→_discover_zone_clue」；再乘 CLUE_STEP_CHANCES[step] 才是本次探索命中线索的概率
CLUE_EXPLORE_EVENT_CHANCE: Dict[str, float] = {
    "starter": 0.20,
    "forest": 0.20,
    "mines": 0.20,
    "coast": 0.20,
    "throne": 0.20,
}

CLUE_MAP_EFFECTS: Dict[str, Dict[str, Any]] = {
    "starter": {"title": "乡路熟识", "desc": "最大体力 +60（永久）"},
    "forest": {"title": "林间商路", "desc": "战斗金币收益 +12%（永久）"},
    "mines": {"title": "裂隙预判", "desc": "闪避 +2%（永久）"},
    "coast": {"title": "潮汐祝福", "desc": "最大HP +5%（永久，全队）"},
    "throne": {"title": "王座洞察", "desc": "暴击率 +5%（永久）"},
}

# 幽影海岸「潮汐祝福」：写入 resources.clue_bonus_hp_pct；主角（_apply_attrs_to_base）与队友（_recalc_member_stats）同口径
CLUE_COAST_HP_BONUS_PCT = 0.05

# 集齐一图 3 条线索后，需三条「领悟」总分 ≥ 此值才激活地图特效（每条线索答题 0/1/3 分）
CLUE_QUIZ_MIN_SCORE = 5

# 每条关键线索：与内心/主角的对话引子 + 三个选项（分值 3 / 1 / 0）
CLUE_QUIZ_BY_ID: Dict[str, Dict[str, Any]] = {
    "q1_old_well_mark": {
        "prompt": "你望着井沿划痕，心里有个声音在问：下去看看？",
        "options": [
            {"text": "观察三道痕的指向，用笔记记录下，脑子里搜寻姐姐过去的回忆。", "score": 3, "answer": "你据此绘根据三道痕的指向，发现神秘的气息不在井内，找到了周边树藤下的宝物，似乎是可以互换起神秘力量的钥匙。"},
            {"text": "似乎有姐姐的气息，先回村打听，再决定方向。", "score": 1, "answer": "村里人提供的线索似乎没有帮助，再回来查看的时候痕迹已经消失。"},
            {"text": "感觉是姐姐留下的线索，一定要跳下井看看。", "score": 0, "answer": "仓促下井，被神秘力量束缚，眼睛一黑，晕了过去。"},
        ],
    },
    "q1_dawn_banner": {
        "prompt": "想起与姐姐的约定，你对自己说——",
        "options": [
            {"text": "带着心往前走，可能符号是伙伴的指引，尝试去找寻相关线索。", "score": 3, "answer": "你反复思考和姐姐之间的誓约，猜测这可能是姐姐留下未来与你同行的冒险的伙伴，对于前路的抉择少了些动摇，坚定的走出自己的路。"},
            {"text": "整理情绪，从过去的回忆中再慢慢思考线索的由来。", "score": 1, "answer": "你暂时稳住了自己，但约定仍像雾里的轮廓，尚未完全融入你未来的行动中。"},
            {"text": "怀疑符号可能是周边异变的线索，想多查看下原因，搜索周围环境", "score": 0, "answer": "你忽略曾经的约定，过分的谨慎和敌视周边的线索，错过了一些重要的伙伴信息。"},
        ],
    },
    "q1_guard_diary": {
        "prompt": "守夜人的最后一页像在盯着你，你会回应——",
        "options": [
            {"text": "未来寻找姐姐可能需要更多同伴，试图在守夜人手册中寻找信息，并组建属于自己的队伍。", "score": 3, "answer": "你成功组建了自己的小队，复杂路段的风险被显著分摊。"},
            {"text": "查看守夜人的日志，了解更多周边信息，为后续的探索做准备。", "score": 1, "answer": "准备尚可，离开破晓村之后，周边的障碍确实从手册中获得了解决，但是手册并不是万能的，后续的探索还需要更多信息手册中并没有提及，还是需要寻找伙伴。"},
            {"text": "想尽快找到姐姐，自己努力了16年，就是为了此时此刻能更快速找到姐姐，不能在等了，姐姐或许处于危险之中，必须尽快找到姐姐。", "score": 0, "answer": "独自旅行压力颇大，急切的搜寻姐姐的新导致你在关键节点缺乏支援，局势很快失去控制。"},
        ],
    },
    "q2_root_whisper": {
        "prompt": "树根下的呢喃让你不安，你内心回应——",
        "options": [
            {"text": "通过树根记下方位与符号，把求救声当成线索而非诅咒。", "score": 3, "answer": "你解出了根系回响的规律，成功避开了诅咒的反噬，安全平稳的进入诅咒森林，进行后续的探索。"},
            {"text": "先退到安全处，等收集到了更多信息后再探。", "score": 1, "answer": "你避免了风险，但也失去了追踪热线索的窗口。"},
            {"text": "树根可能是怪物的诅咒，用来迷惑你的心智，快刀斩乱麻，立刻烧毁树根，避免神智被侵蚀。", "score": 0, "answer": "你破坏了关键痕迹，原本可利用的线索彻底中断。"},
        ],
    },
    "q2_moss_route": {
        "prompt": "苔图指向险路，你在心里权衡——",
        "options": [
            {"text": "按苔图并结合可能是姐姐的暗示琢磨路线，试图找出最佳的路线方案。", "score": 3, "answer": "你以更低代价穿过高危区，队伍状态保持完整。"},
            {"text": "避免之前军队去过的地方，已经是失败的结论，没必要自己再去尝试一次", "score": 1, "answer": "方案可用但反复试错，行程与资源都被拉长。"},
            {"text": "可能这并不是姐姐留下的暗语，是某种力量误导自己，选择最短的路线穿过森林，免得夜长梦多。", "score": 0, "answer": "硬闯触发伏击，你不得不在混乱中仓促撤离。"},
        ],
    },
    "q2_elk_totem": {
        "prompt": "图腾背面的细线像指引未来的路，你对自己说——",
        "options": [
            {"text": "把图腾的信息和童谣结合起来。", "score": 3, "answer": "你建立了跨区域索引，结合起来发现很多线索，并且很快的寻找到了诅咒的本体。"},
            {"text": "图腾和童谣似乎有些地方冲突，拿不准是谁更正确，都尝试一下不遗漏任何线索才是最争取的选择。", "score": 1, "answer": "花费了更多的时间在尝试中，使得自己和队友被诅咒腐蚀得更深，不过好在也发现了诅咒的本体"},
            {"text": "图腾不可信，记忆中姐姐是不会欺骗自己的，会想童谣中的信息来决定下一步如何走。", "score": 0, "answer": "你丢弃图腾中的重要信息，童谣的记忆模糊导致了很多误导，后续推理链出现断层，没能主动发现诅咒本体，而是被动的遭遇到了诅咒，被打了一个措手不及"},
        ],
    },
    "q3_crack_sound": {
        "prompt": "地缝节律像倒计时敲在你心上，你选择——",
        "options": [
            {"text": "按照节律的节奏，来抢那十几秒窗口，尝试救出更多的人。", "score": 3, "answer": "你精准踩中安全窗口，成功穿过裂缝带，找到了矿洞中被困的人们。"},
            {"text": "拼尽自己的全力，去拯救被困的人，无论如何都不能后退。", "score": 1, "answer": "你盲目的使用蛮力去破开矿口，结果导致了更大的塌方，但在你的坚持不懈中，就出了一部分的人们，另一部分由于时间被困太久，已经杳无音讯了。"},
            {"text": "要接受命运，不要过分的干预别人的命运，有时候给自己独自拯救无可厚非，但是带着自己的队友一起涉嫌，不是一个队长应该有的觉悟", "score": 0, "answer": "一屋不扫何以扫天下，苍生不救何以救世间，你的觉悟被队友质疑，队友主动要求救助被困人员，你无奈跟上，由于耽误时间过久，只拯救出小部分被困人员。"},
        ],
    },
    "q3_black_ledger": {
        "prompt": "工账上的真相令人愤怒，你告诉自己——",
        "options": [
            {"text": "把证据带出去，可能灾厄的背后和人类也有关联。", "score": 3, "answer": "证据成为了你执行正义的宝剑，想抹黑你的人无从下手，你也感受到了，或许整个皇室已经被怪物渗透。"},
            {"text": "先清除灾厄，避免灾厄扩散，工账的内容等结束后再去深究", "score": 1, "answer": "虽然击杀了灾厄，但是在战斗中工账遗失，没有了证据后续无从下手，但是你记住了关键信息，尝试在暗地里解决灾厄的人类同党"},
            {"text": "把工账上的信息上报给皇家军队，让正规军来自查勾结的同党", "score": 0, "answer": "灾厄可能是人为的，当你联系了正规军之后没有任何动静，你就知道，正规军可能也已经沦陷，重要的证据还交给了敌人，并且暴露了自己"},
        ],
    },
    "q3_ember_compass": {
        "prompt": "余烬指针在热浪里颤动，你心想——",
        "options": [
            {"text": "跟着罗盘的节律走。", "score": 3, "answer": "你用罗盘与节律完成同步，牢牢抓住了主动权，选择灾厄最脆弱的时候，发起了进攻。"},
            {"text": "靠近裂缝试试指针。", "score": 1, "answer": "罗盘给出了正确的道路，但是由于过分靠近，立刻进入了战斗。"},
            {"text": "罗盘反馈不稳定，要依赖一部分直觉。", "score": 0, "answer": "失去校准后判断全面漂移，推进被迫中断。"},
        ],
    },
    "q4_tide_note": {
        "prompt": "潮线手稿在风里翻动，你暗自决定——",
        "options": [
            {"text": "分析手稿中的节奏，等女巫吟唱的间隙出手。", "score": 3, "answer": "你抓住潮咒断点反制成功，战局明显向你倾斜。"},
            {"text": "这是女巫的主场，要等退潮时再想战术。", "score": 1, "answer": "确实退潮影响了女巫的能力，但是因此牺牲了更多无辜的人。"},
            {"text": "女巫的咏唱是通过声音干扰心神实现的，那么遮住自己的听力或许奏效。", "score": 0, "answer": "盲目自以为是的想法让你陷入潮咒连击，诅咒并不是按照你想象的遮住听力就会失效的，局势迅速恶化。"},
        ],
    },
    "q4_lighthouse_oil": {
        "prompt": "灯塔让你想到责任，你对自己说——",
        "options": [
            {"text": "先点亮灯塔，照亮渔船归家的路。", "score": 3, "answer": "灯塔恢复后撤离路线清晰，回归的渔船给你带来了潮汐女巫重要信息，潮汐诅咒并不是靠声音传播，而是通过眼睛的对视。"},
            {"text": "优先点亮海岸线的光，灯塔离你太远，过去会耽误大量时间。", "score": 1, "answer": "你救助了靠近岸边的渔船，但是更多的渔船因此迷失了方向。"},
            {"text": "擒贼先擒王，你已经听到了女巫的歌声，可能就在不远处的礁石附近，女巫挟持了不少渔民，尽快去拯救他们，否则无辜的渔民会被吸食精气直至死亡。", "score": 0, "answer": "女巫的歌声环绕在整个海岸线上，你在海雾中多次走散，迷失在女巫的歌声中。"},
        ],
    },
    "q4_shell_code": {
        "prompt": "贝壳暗码指向生路，你心里回应——",
        "options": [
            {"text": "把疏散路径交给需要的人，这是托付。", "score": 3, "answer": "你完成了有效疏散，海岸伤亡被压到最低。"},
            {"text": "自己负责疏散渔民，周边出了很多鱼怪，你需要保护大家。", "score": 1, "answer": "你总是想亲力亲为，虽然疏散了你周围的人，但整体撤离效率一般。"},
            {"text": "如果不能解决女巫，周围所有的人都无法获救，疏散郁闷不如寻找女巫并解决掉问题的根源。", "score": 0, "answer": "你放弃引导后现场秩序崩坏，未获救的渔民也一直让你在与女巫战斗中分心。"},
        ],
    },
    "q5_gate_rune": {
        "prompt": "残符在掌下发热，你默念——",
        "options": [
            {"text": "危险造就。", "score": 3, "answer": "你成功整合前线经验，终章推进变得稳定可控。"},
            {"text": "先记下符文形状。", "score": 1, "answer": "你留下了基础记录，但尚未形成完整战术链。"},
            {"text": "一刀秒了守卫就行，花里胡哨。", "score": 0, "answer": "你忽视机制细节，正面冲击被迅速反制。"},
        ],
    },
    "q5_mirror_piece": {
        "prompt": "裂镜里的溃败让你手抖，你告诉自己——",
        "options": [
            {"text": "恐惧和愤怒都要管：队形与节奏不能丢。", "score": 3, "answer": "你及时稳住阵型，镜域反扑被有效遏制。"},
            {"text": "下次别冲太猛。", "score": 1, "answer": "你意识到问题，但调整仍停留在口头层面。"},
            {"text": "镜子里是别人，我不会重蹈覆辙……吧。", "score": 0, "answer": "你否认风险导致旧错重演，队伍承压明显上升。"},
        ],
    },
    "q5_last_oath": {
        "prompt": "誓文问你愿不愿被追责，你回答——",
        "options": [
            {"text": "愿承担重建与联络，荣耀不如托付。", "score": 3, "answer": "你的承诺换来稳定支援，终局后的秩序开始重建。"},
            {"text": "先打赢再说。", "score": 1, "answer": "你专注当前战斗，但忽略了战后治理的准备。"},
            {"text": "我只想要被歌颂。", "score": 0, "answer": "你把目标收缩为个人名望，团队信任明显下降。"},
        ],
    },
}


def _clue_quiz_for_id(cid: str) -> Dict[str, Any]:
    q = CLUE_QUIZ_BY_ID.get(str(cid))
    if not q:
        return {
            "prompt": "线索在心间沉淀，你听见自己的声音在问：该如何前行？",
            "options": [
                {"text": "冷静规划，把发现与同伴、后续行动连在一起。", "score": 3, "answer": "你的判断形成正循环，后续行动更有把握。"},
                {"text": "谨慎观察，暂缓一步。", "score": 1, "answer": "你避免了冒进风险，但整体推进速度偏慢。"},
                {"text": "先不管，冲动行事。", "score": 0, "answer": "你忽视了线索价值，导致后续决策连续偏差。"},
            ],
        }
    return q


def _build_pending_clue_story_payload(picked: Dict[str, Any], zone_id: str, rng: random.Random) -> Dict[str, Any]:
    cid = str(picked.get("id", "") or "")
    quiz = _clue_quiz_for_id(cid)
    opts = [dict(x) for x in (quiz.get("options") or [])]
    if len(opts) < 3:
        while len(opts) < 3:
            opts.append({"text": "……", "score": 0})
    rng.shuffle(opts)
    return {
        "id": cid,
        "title": str(picked.get("title", cid)),
        "zone_id": str(zone_id),
        "story": str(picked.get("story", picked.get("desc", ""))),
        "interaction": str(quiz.get("prompt", "")),
        "choices_shuffled": opts,
    }


def dq_ensure_clue_quiz_pending(state: Dict[str, Any]) -> None:
    """若已有线索尚未作答，排队弹出第一条（不覆盖已有 pending）。"""
    meta = state.setdefault("meta", {})
    if meta.get("pending_clue_story"):
        return
    res = state.setdefault("resources", {})
    scores = res.setdefault("clue_quiz_scores", {})
    found = {str(x) for x in (res.get("clues_found") or []) if str(x)}
    seed = int(state.get("seed", 0) or 0) ^ 0xC10E
    rng = random.Random(seed)
    for zone_id in ("starter", "forest", "mines", "coast", "throne"):
        for d in CLUE_ZONE_DEFS.get(zone_id, []) or []:
            cid = str(d.get("id", "") or "")
            if cid in found and cid not in scores:
                meta["pending_clue_story"] = _build_pending_clue_story_payload(d, zone_id, rng)
                return


def _build_clue_quiz_feedback(clue_title: str, score: int, answer_text: str = "") -> Dict[str, str]:
    sc = int(score or 0)
    ans = str(answer_text or "").strip()
    if sc >= 3:
        return {
            "level": "good",
            "title": "✨ 领悟反馈：判断精准",
            "text": ans or f"你对「{clue_title}」的回应稳健而清晰，获得了积极结果。",
        }
    if sc >= 1:
        return {
            "level": "mid",
            "title": "🧭 领悟反馈：方向尚可",
            "text": ans or f"你对「{clue_title}」的回应较为保守，结果中性，仍有优化空间。",
        }
    return {
        "level": "bad",
        "title": "⚠️ 领悟反馈：决策失误",
        "text": ans or f"你对「{clue_title}」的回应偏离关键线索，触发了不利结果。",
    }


def dq_ack_clue_quiz_feedback(state: Dict[str, Any]) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    state.setdefault("meta", {})["pending_clue_quiz_feedback"] = None
    return state


def dq_record_clue_quiz_answer(state: Dict[str, Any], clue_id: str, score: int, answer_text: str = "") -> Dict[str, Any]:
    """记录一条线索的领悟得分（0/1/3），每条仅一次；并尝试结算地图特效。"""
    state = copy.deepcopy(state)
    cid = str(clue_id or "").strip()
    if not cid:
        return state
    res = state.setdefault("resources", {})
    scores = res.setdefault("clue_quiz_scores", {})
    if cid in scores:
        return state
    allowed = {int(o.get("score", -1)) for o in _clue_quiz_for_id(cid).get("options", [])}
    if int(score) not in allowed:
        return state
    scores[cid] = int(score)
    meta = state.setdefault("meta", {})
    meta["pending_clue_story"] = None
    title = cid
    for zd in CLUE_ZONE_DEFS.values():
        for d in zd or []:
            if str(d.get("id", "")) == cid:
                title = str(d.get("title", cid))
                break
    fb = _build_clue_quiz_feedback(title, int(score), answer_text)
    meta["pending_clue_quiz_feedback"] = {
        "title": str(fb.get("title", "领悟反馈")),
        "text": str(fb.get("text", "")),
        "level": str(fb.get("level", "mid")),
        "clue_title": str(title),
        "score": int(score),
    }
    state.setdefault("meta", {}).setdefault("log", []).append(
        f"📣 线索反馈：{fb.get('text', '')}"
    )
    state.setdefault("meta", {}).setdefault("log", []).append(f"📜 关键线索「{title}」领悟得分：{int(score)} 分。")
    dq_ensure_clue_quiz_pending(state)
    _apply_clue_milestones(state)
    return state


def _reapply_clue_max_stamina(state: Dict[str, Any]) -> None:
    """按 resources.clue_bonus_max_stamina 重算 max_stamina（默认 120 + 线索加成）。"""
    res = state.setdefault("resources", {})
    bonus = max(0, int(res.get("clue_bonus_max_stamina", 0) or 0))
    cap = int(DEFAULT_MAX_STAMINA) + bonus
    state["max_stamina"] = cap
    cur = int(state.get("stamina", 0) or 0)
    state["stamina"] = min(cur, cap)


def _apply_clue_milestones(state: Dict[str, Any]) -> None:
    """
    每张地图 3 条线索集齐且均已「领悟作答」后，若三条得分之和 ≥ CLUE_QUIZ_MIN_SCORE，触发地图特效。
    """
    res = state.setdefault("resources", {})
    # 潮汐祝福：旧档 8% 统一为当前常量（全队加成仍由 clue_bonus_hp_pct 驱动）
    if float(res.get("clue_bonus_hp_pct", 0.0) or 0.0) > CLUE_COAST_HP_BONUS_PCT:
        res["clue_bonus_hp_pct"] = CLUE_COAST_HP_BONUS_PCT
    found = {str(x) for x in (res.get("clues_found") or []) if str(x)}
    # 兼容旧存档：若只有旧版 clue 数量，则按顺序映射到新线索集合
    legacy_count = max(0, int(res.get("clue", 0) or 0))
    if not found and legacy_count > 0:
        all_ids: List[str] = []
        for z in ("starter", "forest", "mines", "coast", "throne"):
            for d in CLUE_ZONE_DEFS.get(z, []):
                cid = str(d.get("id", ""))
                if cid:
                    all_ids.append(cid)
        found = set(all_ids[:legacy_count])
    effected = {str(x) for x in (res.get("clue_effect_maps") or []) if str(x)}
    logs = state.setdefault("meta", {}).setdefault("log", [])
    scores_map = res.get("clue_quiz_scores") or {}

    for zone_id, defs in CLUE_ZONE_DEFS.items():
        zone_ids = {str(d.get("id", "")) for d in defs if str(d.get("id", ""))}
        if zone_id in effected:
            continue
        if not (zone_ids and zone_ids.issubset(found)):
            continue
        zone_score = 0
        all_answered = True
        for zcid in zone_ids:
            if zcid not in scores_map:
                all_answered = False
                break
            zone_score += int(scores_map.get(zcid, 0) or 0)
        if not all_answered:
            continue
        if zone_score < CLUE_QUIZ_MIN_SCORE:
            fail_logged = {str(x) for x in (res.get("clue_zone_score_fail_logged") or []) if str(x)}
            if zone_id not in fail_logged:
                fail_logged.add(zone_id)
                res["clue_zone_score_fail_logged"] = sorted(list(fail_logged))
                zname = str(_zone_catalog().get(zone_id, {}).get("name", zone_id))
                logs.append(
                    f"🏁 {zname} 三条线索已齐，但领悟总分 {zone_score} 未满 {CLUE_QUIZ_MIN_SCORE} 分，地图特效未激活。"
                )
            continue
        if zone_id == "starter":
            res["clue_bonus_max_stamina"] = max(int(res.get("clue_bonus_max_stamina", 0) or 0), 60)
            _reapply_clue_max_stamina(state)
            state["stamina"] = min(int(state["max_stamina"]), int(state.get("stamina", 0) or 0) + 60)
        elif zone_id == "forest":
            res["clue_bonus_gold_pct"] = max(float(res.get("clue_bonus_gold_pct", 0.0) or 0.0), 0.12)
        elif zone_id == "mines":
            res["clue_bonus_eva"] = max(float(res.get("clue_bonus_eva", 0.0) or 0.0), 0.02)
        elif zone_id == "coast":
            res["clue_bonus_hp_pct"] = max(float(res.get("clue_bonus_hp_pct", 0.0) or 0.0), CLUE_COAST_HP_BONUS_PCT)
        elif zone_id == "throne":
            res["clue_bonus_crit"] = max(float(res.get("clue_bonus_crit", 0.0) or 0.0), 0.05)
        effected.add(zone_id)
        ef = CLUE_MAP_EFFECTS.get(zone_id, {})
        logs.append(f"🏁 线索集齐且领悟达标，特效触发【{zone_id}】：{ef.get('title','地图加成')}（{ef.get('desc','已生效')}）。")

    # 旧存档：已记录 starter 地图特效但尚未写入（或写入过低）体力加成字段
    if "starter" in effected and int(res.get("clue_bonus_max_stamina", 0) or 0) < 60:
        res["clue_bonus_max_stamina"] = 60

    res["clues_found"] = sorted(list(found))
    res["clue"] = len(found)
    res["clue_effect_maps"] = sorted(list(effected))
    _reapply_clue_max_stamina(state)


def dq_clue_journal_status(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    res = state.get("resources") or {}
    found = {str(x) for x in (res.get("clues_found") or []) if str(x)}
    effected = {str(x) for x in (res.get("clue_effect_maps") or []) if str(x)}
    scores_map = res.get("clue_quiz_scores") or {}
    out: List[Dict[str, Any]] = []
    for zone_id in ("starter", "forest", "mines", "coast", "throne"):
        defs = CLUE_ZONE_DEFS.get(zone_id, [])
        rows: List[Dict[str, Any]] = []
        zone_ids: List[str] = []
        zone_quiz_sum = 0
        for d in defs:
            cid = str(d.get("id", ""))
            if cid:
                zone_ids.append(cid)
            qv_i: Optional[int] = None
            if cid in scores_map:
                try:
                    qv_i = int(scores_map.get(cid, 0) or 0)
                    zone_quiz_sum += qv_i
                except (TypeError, ValueError):
                    qv_i = None
            rows.append(
                {
                    "id": cid,
                    "title": str(d.get("title", cid)),
                    "desc": str(d.get("desc", "")),
                    "found": cid in found,
                    "quiz_score": qv_i,
                    "quiz_answered": cid in scores_map,
                }
            )
        need = CLUE_QUIZ_MIN_SCORE
        max_pts = 9
        out.append(
            {
                "zone_id": zone_id,
                "zone_name": _zone_catalog().get(zone_id, {}).get("name", zone_id),
                "found_count": sum(1 for r in rows if r.get("found")),
                "total": len(rows),
                "effect_unlocked": zone_id in effected,
                "effect_title": str((CLUE_MAP_EFFECTS.get(zone_id) or {}).get("title", "")),
                "effect_desc": str((CLUE_MAP_EFFECTS.get(zone_id) or {}).get("desc", "")),
                "clues": rows,
                "quiz_zone_sum": zone_quiz_sum,
                "quiz_need_score": need,
                "quiz_max_score": max_pts,
                "quiz_all_answered": bool(zone_ids) and all(x in scores_map for x in zone_ids),
            }
        )
    return out


def _zone_has_unfound_clues(state: Dict[str, Any], zone_id: str) -> bool:
    """当前地图 CLUE_ZONE_DEFS 中是否仍有未写入 clues_found 的线索。"""
    res = state.get("resources") or {}
    found = {str(x) for x in (res.get("clues_found") or []) if str(x)}
    for d in CLUE_ZONE_DEFS.get(str(zone_id), []) or []:
        cid = str(d.get("id", "") or "")
        if cid and cid not in found:
            return True
    return False


def _discover_zone_clue(state: Dict[str, Any], zone_id: str, rng: random.Random) -> Tuple[Optional[Dict[str, str]], bool]:
    """返回 (线索定义, 是否首次发现)。

    每张地图（starter/forest/...）各自统计本图已发现线索数 step，再用 CLUE_STEP_CHANCES[zone_id][step]；
    与别图线索无关。线索 id 存在全局 clues_found，但 step 只数「本图 defs 里已收录的 id」。
    """
    res = state.setdefault("resources", {})
    found = {str(x) for x in (res.get("clues_found") or []) if str(x)}
    defs = CLUE_ZONE_DEFS.get(str(zone_id), [])
    if not defs:
        return None, False
    zone_defs = [d for d in defs if str(d.get("id", ""))]
    zone_found = [d for d in zone_defs if str(d.get("id", "")) in found]
    zone_unfound = [d for d in zone_defs if str(d.get("id", "")) not in found]
    if not zone_unfound:
        return None, False

    step = min(len(zone_found), 2)
    chance = float(CLUE_STEP_CHANCES.get(str(zone_id), [0.60, 0.18, 0.06])[step])
    if rng.random() >= chance:
        return None, False

    # 仅从“未触发线索”中抽取，保证同线索只触发一次
    picked = rng.choice(zone_unfound)
    cid = str(picked.get("id", ""))
    found.add(cid)
    res["clues_found"] = sorted(list(found))
    res["clue"] = len(found)
    res.setdefault("clue_quiz_scores", {})

    # 记录待前端弹窗：长文 + 与主角沟通 + 三选一领悟（结算在 dq_record_clue_quiz_answer）
    state.setdefault("meta", {})["pending_clue_story"] = _build_pending_clue_story_payload(
        picked, str(zone_id), rng
    )
    return picked, True


def dq_new_game(player_name: str, seed: Optional[int] = None, hero_gender: Optional[str] = None) -> Dict[str, Any]:
    if seed is None:
        seed = random.randint(1, 10**9)
    hg = str(hero_gender or "男").strip()
    if hg not in ("男", "女"):
        hg = "男"
    state = _make_player(player_name, seed, hero_gender=hg)
    _ensure_rng_pool(state, refresh=True)
    state["meta"]["log"].append("📜 你翻开冒险者的手册。序章开始：破晓村的风比往常更早来临。")
    if "lianzhan" not in state["skills"]:
        state["skills"] = ["lianzhan"]
    dq_ensure_q1_opening_story(state)
    return state


def dq_reset_new_game(state: Dict[str, Any], player_name: str) -> Dict[str, Any]:
    seed = random.randint(1, 10**9)
    hg = str((state or {}).get("hero_gender") or "男").strip()
    if hg not in ("男", "女"):
        hg = "男"
    return dq_new_game(player_name, seed=seed, hero_gender=hg)


def _ensure_inventory_integrity(state: Dict[str, Any]) -> None:
    # merge same potion items by item_id (we don't do full item identity; only for qty)
    inv = state.get("inventory", [])
    for it in inv:
        it["qty"] = clamp_int(it.get("qty", 0), 0, 999999, 0)


def dq_get_summary(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "level": state.get("level", 1),
        "hp": state.get("hp"),
        "max_hp": state.get("max_hp"),
        "mp": state.get("mp"),
        "max_mp": state.get("max_mp"),
        "gold": state.get("gold"),
        "location": state.get("location"),
        "phase": state.get("phase"),
    }


def dq_available_zones(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    zones = list(_zone_catalog().values())
    unlocked = set(state.get("unlocked_zones", []))
    boss_v = state.get("boss_victories", 0)
    out = []
    for z in zones:
        if z["id"] == "infinite":
            # 无限地牢仅保留「按钮入口」，不再作为区域旅行项显示
            continue
        if z["unlock_by"] <= boss_v or z["id"] in unlocked:
            out.append(z)
    return out


def _q1_get_quest(state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    quest = (state.get("quest") or {}).get("quests") or []
    for q in quest:
        if q.get("qid") == "q1":
            return q
    return None


def _q1_is_done(state: Dict[str, Any]) -> bool:
    q1 = _q1_get_quest(state)
    return bool(q1 and q1.get("done"))


def _q1_should_roll_act2(state: Dict[str, Any]) -> bool:
    if _q1_is_done(state):
        return False
    if int(state.get("level", 1) or 1) < Q1_ACT2_MIN_LEVEL:
        return False
    if state.get("location") != "starter":
        return False
    meta = state.get("meta") or {}
    if meta.get("pending_story"):
        return False
    if not bool(meta.get("q1_act1_done")):
        return False
    if bool(meta.get("q1_act2_done")):
        return False
    if bool(meta.get("q1_post_act1_tutorial", {}).get("active")):
        return False
    return True


def _q1_should_roll_act3(state: Dict[str, Any]) -> bool:
    if _q1_is_done(state):
        return False
    if int(state.get("level", 1) or 1) < Q1_ACT3_MIN_LEVEL:
        return False
    if state.get("location") != "starter":
        return False
    meta = state.get("meta") or {}
    if meta.get("pending_story"):
        return False
    if not bool(meta.get("q1_act2_done")):
        return False
    if bool(meta.get("q1_act3_done")):
        return False
    return True


def _q2_is_done(state: Dict[str, Any]) -> bool:
    quest = (state.get("quest") or {}).get("quests") or []
    for q in quest:
        if q.get("qid") == "q2":
            return bool(q.get("done"))
    return False


def _q2_should_start_act1(state: Dict[str, Any]) -> bool:
    """Q2 第一幕：主角 ≥Lv10、尚未选择且可进行剧情时，在诅咒森林探索优先弹出。"""
    if int(state.get("level", 1) or 1) < Q2_ACT1_MIN_LEVEL:
        return False
    if state.get("location") != "forest":
        return False
    meta = state.get("meta") or {}
    if meta.get("pending_story"):
        return False
    if meta.get("q2_echo_act1_done"):
        return False
    if meta.get("q2_witherling_beaten_pending_echo"):
        return False
    qs = ((state.get("quest") or {}).get("quests") or [])
    q2 = next((q for q in qs if isinstance(q, dict) and q.get("qid") == "q2"), None)
    if not q2 or q2.get("done"):
        return False
    return True


def _q4_mainline_active(state: Dict[str, Any]) -> bool:
    qs = ((state.get("quest") or {}).get("quests") or [])
    q4 = next((q for q in qs if isinstance(q, dict) and q.get("qid") == "q4"), None)
    return bool(q4 and not q4.get("done"))


def _q4_should_roll_act1(state: Dict[str, Any]) -> bool:
    """Q4 第一幕：海岸探索随机触发（未完成第一幕、Boss 未败时）。"""
    if not _q4_mainline_active(state):
        return False
    if int(state.get("level", 1) or 1) < Q4_ACT1_MIN_LEVEL:
        return False
    if state.get("location") != "coast":
        return False
    meta = state.get("meta") or {}
    if meta.get("pending_story"):
        return False
    if meta.get("q4_sea_witch_beaten_pending_echo"):
        return False
    if meta.get("q4_act1_done"):
        return False
    if _is_boss_defeated(state, "boss_sea_witch"):
        return False
    return True


def _q4_should_roll_act2(state: Dict[str, Any]) -> bool:
    """Q4 第二幕：须已成功完成第一幕。"""
    if not _q4_mainline_active(state):
        return False
    if int(state.get("level", 1) or 1) < Q4_ACT1_MIN_LEVEL:
        return False
    if state.get("location") != "coast":
        return False
    meta = state.get("meta") or {}
    if meta.get("pending_story"):
        return False
    if meta.get("q4_sea_witch_beaten_pending_echo"):
        return False
    if not meta.get("q4_act1_done"):
        return False
    if meta.get("q4_act2_done"):
        return False
    if _is_boss_defeated(state, "boss_sea_witch"):
        return False
    return True


def _q5_mainline_active(state: Dict[str, Any]) -> bool:
    qs = ((state.get("quest") or {}).get("quests") or [])
    q5 = next((q for q in qs if isinstance(q, dict) and q.get("qid") == "q5"), None)
    return bool(q5 and not q5.get("done"))


def _q5_should_roll_act1(state: Dict[str, Any]) -> bool:
    if not _q5_mainline_active(state):
        return False
    if int(state.get("level", 1) or 1) < Q5_ACT1_MIN_LEVEL:
        return False
    if state.get("location") != "throne":
        return False
    meta = state.get("meta") or {}
    if meta.get("pending_story"):
        return False
    if meta.get("q5_throne_guard_beaten_pending_echo"):
        return False
    if meta.get("q5_act1_done"):
        return False
    if _is_boss_defeated(state, "boss_throne_guard"):
        return False
    return True


def _q5_should_roll_act2(state: Dict[str, Any]) -> bool:
    if not _q5_mainline_active(state):
        return False
    if int(state.get("level", 1) or 1) < Q5_ACT1_MIN_LEVEL:
        return False
    if state.get("location") != "throne":
        return False
    meta = state.get("meta") or {}
    if meta.get("pending_story"):
        return False
    if meta.get("q5_throne_guard_beaten_pending_echo"):
        return False
    if not meta.get("q5_act1_done"):
        return False
    if meta.get("q5_act2_done"):
        return False
    if _is_boss_defeated(state, "boss_throne_guard"):
        return False
    return True


def _q5_should_roll_act3(state: Dict[str, Any]) -> bool:
    if not _q5_mainline_active(state):
        return False
    if int(state.get("level", 1) or 1) < Q5_ACT1_MIN_LEVEL:
        return False
    if state.get("location") != "throne":
        return False
    meta = state.get("meta") or {}
    if meta.get("pending_story"):
        return False
    if meta.get("q5_throne_guard_beaten_pending_echo"):
        return False
    if not meta.get("q5_act1_done") or not meta.get("q5_act2_done"):
        return False
    if meta.get("q5_act3_done"):
        return False
    if _is_boss_defeated(state, "boss_throne_guard"):
        return False
    return True


def _grant_q2_act1_strong_potion(state: Dict[str, Any], rng: random.Random) -> None:
    """第一幕「好」档：随机一瓶强效档药水（特级/金苹果/复活）。"""
    rr = rng.random()
    if rr < 0.36:
        rare = {
            "item_id": _new_id("pot", rng),
            "name": "特级恢复药水",
            "qty": 1,
            "meta": {"use": "full_heal_potion", "heal_pct": POTION_FULL_HP_PCT, "sell_price": _potion_unit_sell_price("full_heal_potion")},
        }
        extra = f"最大HP×{POTION_FULL_HP_PCT}%"
    elif rr < 0.72:
        rare = {
            "item_id": _new_id("pot", rng),
            "name": "特级魔力药水",
            "qty": 1,
            "meta": {"use": "full_mp_potion", "mp_pct": POTION_FULL_MP_PCT, "sell_price": _potion_unit_sell_price("full_mp_potion")},
        }
        extra = f"最大MP×{POTION_FULL_MP_PCT}%"
    elif rr < 0.92:
        rare = {
            "item_id": _new_id("pot", rng),
            "name": "金苹果",
            "qty": 1,
            "meta": {
                "use": "golden_apple",
                "heal_pct": POTION_GOLDEN_HP_PCT,
                "mp_pct": POTION_GOLDEN_MP_PCT,
                "sell_price": _potion_unit_sell_price("golden_apple"),
            },
        }
        extra = f"最大HP×{POTION_GOLDEN_HP_PCT}% + 最大MP×{POTION_GOLDEN_MP_PCT}%"
    else:
        rare = {
            "item_id": _new_id("pot", rng),
            "name": "复活药水",
            "qty": 1,
            "meta": {
                "use": "revive_potion",
                "revive_hp_pct": POTION_REVIVE_HP_PCT,
                "revive_mp_pct": POTION_REVIVE_MP_PCT,
                "sell_price": _potion_unit_sell_price("revive_potion"),
            },
        }
        extra = f"复活后 HP×{POTION_REVIVE_HP_PCT}% / MP×{POTION_REVIVE_MP_PCT}%"
    ok, _ = dq_try_add_inventory(state, [rare])
    meta = state.setdefault("meta", {})
    if ok:
        meta.setdefault("log", []).append(f"第一幕的馈赠：获得「{rare['name']}」（{extra}）。")
        _queue_unlock_notice(state, "🎁 第一幕馈赠", [f"获得：{rare.get('name', '药水')}"])
    else:
        meta.setdefault("log", []).append("你触到一瓶强效药水，但背包已满，未能带走。")


def _apply_q2_act1_choice(state: Dict[str, Any], choice_id: str, rng: random.Random) -> None:
    """Q2 第一幕三选一：好=随机强效药水；一般=提高遇枯萎之王概率；坏=下次探索强制进入 Boss 战。"""
    meta = state.setdefault("meta", {})
    cid = str(choice_id)
    if cid == "q2_a1_good":
        _grant_q2_act1_strong_potion(state, rng)
    elif cid == "q2_a1_mid":
        meta["q2_boss_chance_add"] = 0.12
        meta.setdefault("log", []).append("你记住了风里最稳的节拍：在诅咒森林，遇见枯萎之王的概率提高了。")
    elif cid == "q2_a1_bad":
        meta["q2_force_boss_next"] = True
        meta.setdefault("log", []).append("你不再绕路：下一次在诅咒森林探索时，将直面枯萎之王。")


def dq_mainline_hint(state: Dict[str, Any]) -> str:
    """当前主线推进提示（下一步做什么）。"""
    qs = ((state.get("quest") or {}).get("quests") or [])
    qmap = {str(q.get("qid", "")): q for q in qs if isinstance(q, dict)}
    if not bool((qmap.get("q1") or {}).get("done")):
        return (
            "Q1 破晓之誓：在「破晓村与周边」探索触发主线，先阅毕第一幕童年回忆，再在第二、三幕完成古井抉择并邀请首位伙伴；"
            "完成后才会解锁「诅咒森林」。"
        )
    if not bool((qmap.get("q2") or {}).get("done")):
        plv = int(state.get("level", 1) or 1)
        if plv < Q2_ACT1_MIN_LEVEL:
            return (
                f"Q2 森林的回声：主角达到 Lv{Q2_ACT1_MIN_LEVEL} 后，在「诅咒森林」探索才会触发第一幕；"
                "之后需击败枯萎之王并完成第二幕余烬选择。"
            )
        return "Q2 森林的回声：在「诅咒森林」完成第一幕抉择后，击败枯萎之王，再完成第二幕余烬奖品选择。"
    if not bool((qmap.get("q3") or {}).get("done")):
        return "Q3 矿坑的裂纹：先在「遗忘矿坑」完成招募抉择（猎人/盗贼入队），再击败熔岩巨像并完成战后装备三选一。"
    if not bool((qmap.get("q4") or {}).get("done")):
        plv4 = int(state.get("level", 1) or 1)
        if plv4 < Q4_ACT1_MIN_LEVEL:
            return (
                f"Q4 潮汐的代价：主角达到 Lv{Q4_ACT1_MIN_LEVEL} 后，在「幽影海岸」探索可随机触发第一幕与第二幕；"
                "完成第二幕后才会遭遇潮汐女巫，击败女巫后进入第三幕装备三选一。"
            )
        return (
            "Q4 潮汐的代价：在「幽影海岸」依次完成第一幕、第二幕（探索随机触发，Lv26 起若未完成的幕将优先强制触发），"
            "之后击败潮汐女巫并完成第三幕装备三选一。"
        )
    if not bool((qmap.get("q5") or {}).get("done")):
        plv5 = int(state.get("level", 1) or 1)
        if plv5 < Q5_ACT1_MIN_LEVEL:
            return (
                f"Q5 王座的挑战：主角达到 Lv{Q5_ACT1_MIN_LEVEL} 后，在「王座地牢」探索可随机触发第一至第三幕；"
                "完成第三幕后才会遭遇王座守卫，击败守卫后进入第四幕装备三选一。"
            )
        return (
            "Q5 王座的挑战：在「王座地牢」依次完成第一至第三幕（探索随机触发，Lv30 起若未完成的幕将优先强制触发），"
            "之后击败王座守卫并完成第四幕装备三选一。"
        )
    return "主线已通关：可继续无限地牢、养成、刷装备与收集全地图线索。"


# 主线剧情视频：`{职业中文}_{男|女（仅战士）}_剧情_Qn_第x幕` → video/ 下同名 .mp4
MAIN_STORY_VIDEO_QTAG_BY_SID: Dict[str, str] = {
    "q1_seal_whisper": "Q1",
    "q2_forest_echo": "Q2",
    "q3_mines_crack": "Q3",
    "q4_tide_price": "Q4",
    "q5_throne_last": "Q5",
}
MAIN_STORY_VIDEO_ACT_LABELS: Tuple[str, ...] = ("第一幕", "第二幕", "第三幕", "第四幕")


def dq_main_story_video_stem(state: Dict[str, Any]) -> str:
    """
    根据 meta.pending_story 生成剧情视频文件名（无扩展名）。
    例：战士、性别男、Q1 第一幕 → 「战士_男_剧情_Q1_第一幕」。
    非战士职业与战斗视频规则一致：不加性别段。
    """
    pending = (state.get("meta") or {}).get("pending_story")
    if not isinstance(pending, dict):
        return ""
    sid = str(pending.get("sid", "") or "")
    qtag = MAIN_STORY_VIDEO_QTAG_BY_SID.get(sid)
    if not qtag:
        return ""
    step = int(pending.get("step", 0) or 0)
    labels = MAIN_STORY_VIDEO_ACT_LABELS
    si = min(max(step, 0), len(labels) - 1)
    act = labels[si]
    role = str(state.get("role", "warrior"))
    role_cn = ROLE_CN.get(role, "战士")
    hg = str(state.get("hero_gender") or "男").strip()
    if hg not in ("男", "女"):
        hg = "男"
    mid = f"剧情_{qtag}_{act}"
    if role == "warrior":
        return f"{role_cn}_{hg}_{mid}"
    return f"{role_cn}_{mid}"


Q1_ACT1_BACKSTORY_SCENE = """
你还记得破晓村最初的气味吗？那是泥土被晨露浸软后的腥甜，是灶火与干草混在一起的安全感。父母走得很早，早到你几乎来不及把他们的面容刻成清晰的脸，只剩下一些零碎的印象：父亲手掌的粗茧，母亲哼过半句的歌。此后岁月里，世界缩小成两个人的屋檐——你和姐姐。

姐姐并不是天生就会当“大人”的。她也不过比你大上几岁，却在一夜之间把脊背挺得更直，把声音放得更稳。她学着煮粥，学着补衣，学着在邻里之间欠身道谢；她把最好的那块薯蓣推到你碗里，说自己“不爱吃甜的”。你知道那是谎话，可你也知道，有些谎话比真话更烫。邻人并非冷漠：东头的阿婆会多送一篮鸡蛋，西边的木匠会替你修牢歪斜的栅栏；他们不说怜悯，只说“孩子，多吃点”。你在这些沉默的好意里长大，像一株被许多人顺手浇灌的苗。

你们的日常细得像针脚。春天翻土时，姐姐会在田埂上画一道浅浅的线，告诉你哪一行该撒哪种种子；夏天她把凉茶晾在井边，看你满头大汗地从练桩上下来，只轻轻说“慢些，别呛着”；秋天你们一起把收成码进仓，她数捆数，你负责把麻绳勒紧；冬天炉火噼啪，她把你的手拢在掌心搓热，讲一些半截的故事——故事里的英雄总会回家。你们也吵架，吵你偷吃腌菜、吵你把膝盖摔破，可夜里她仍会摸黑起来，替你掖好被角。

若要把记忆再翻得细一点：溪边洗脚时溅起的水花，夏夜躺在晒谷场上数过的星子，她教你认的第一个字写在木片上的那一横一竖。你生过一场热病，她三天没合眼，额头抵着你的额头试温，像用自己的命去换你的平稳。你也曾和姐姐在雨后的田埂上追过青蛙，裤脚溅满泥点，被她笑着骂“小泥猴”，却仍递来干布；你也曾在除夕夜与她分食一块难得的糖，糖在舌尖化开时，你们约定来年要把篱笆修成全村最整齐。她教你不要把软弱露给外人看，却允许你在她面前哭湿过袖子。你也曾假装睡着，听她对着父母的牌位低声说话，声音碎在夜里，像细小的玻璃。那时你不懂，如今回想，才明白她早就在替你挡某种你看不见的风。

那时候你以为，这样的日子会像田垄一样一行接一行，延伸到看不见的远方。

直到那一天。黄昏比往常更薄，村口狗吠得乱。姐姐推门进来时，衣角沾着泥，脸色白得像月光浸过。她的手在抖，却仍先给你倒了一杯水。她说，她要去很远的地方，有些事必须她亲自去了结。她嘱咐你千万千万要活下去，要把自己养得结实；在你十六岁成年之前，不要离开这座村庄，无论听到什么、看到什么。她从怀里取出一封信，信封厚得过分，火漆却还没封死，仿佛她也还在犹豫。她说，这封信只能在你满十六岁那天拆开；在那之前，连想都不要想。她说，姐姐一直很爱你。那句话落得很轻，却像钉子一样钉进你的少年时代。

第二天，屋里空了半边。灶上的粥还温着，她的外衣却不在了。你跑到村口，跑到井边，跑到所有你们曾并肩走过的地方，世界仍旧安静得残忍。从那天起，你把自己种进田里，也种进日复一日的操练里。你养牛、放羊、喂鸡，把篱笆补得一道比一道结实；你在黎明前起床，对着木桩挥拳，直到虎口裂开又结痂。你在等一个数字：十六岁。那不只是年龄，更像一扇门。

你长大，村庄却似乎在另一侧悄然坏损。邻人的笑容变得迟缓，问候像从很远的地方传来，带着不自然的停顿。集市上的谈话日复一日重复，像同一卷线被笨拙地缠绕着。有时你问一句寻常的话，对方要愣上半晌，才慢慢吐出两个字，眼神却不聚焦在你身上，仿佛穿透你，望向某个空洞的模板。孩童的嬉闹声少了，狗也不常吠了，连风声都像是贴着地面滑行，少了从前的起伏。你心里掠过一丝异样，像看见水面下有一道不属于自己的影子——可日子还能过，田还能种，你便把那点诡异按进心底，像按下一枚暂时不发作的刺。村庄的教堂钟摆、磨坊水车、甚至井绳摩擦井沿的节奏，都曾让你觉得“永恒”；可当你后来回想，永恒有时只是结界均匀的呼吸。

十六岁生日那天，你没有摆酒，没有宾客。你坐在门槛上，从柜底取出那封信。纸页泛黄，墨迹却仍清晰，仿佛多年里有人在暗处替你保管着它的锋利。信上写着：亲爱的弟弟，当你读到这些字时，这座村庄外围的结界或许已经快要碎裂。你从小到大生活的地方，并不是世间无数村落中普通的一座；它是为你单独修筑的壳，用来缓冲两个世界之间的落差。我们真实所处的天地，可能与你在这里所见、所感并不相同。不要恨任何人，他们大多只是“被安排来陪你长大”的影子。你要尽快真正长大，然后离开这里。随信附有半幅地图与几条暗记，那是通往我所在方向的路。来找我。如果还来得及，让我再看你一眼。

你读得很慢，每个字都在胸腔里敲一下。风从破晓村外吹来，带着你熟悉了一辈子的草腥与尘土味，此刻却像第一次被你真正闻见。你抬起头，天际线仍旧温柔，村庄仍旧安静——可你知道，从这一刻起，你脚下的土地不再是全部的真实。你把信折好，像把一段童年轻轻合上；而前方，长路才刚露出第一道裂光。童年像一幅绣品：正面是炊烟与笑声，背面是密密麻麻、为你一个人穿过的线。你终于明白，自己为何要在那些年里，把身体练得如此坚硬——因为有人把柔软留给了你，又把最硬的告别，写在未拆的信里。
"""

def _q1_story_scene(step: int) -> Dict[str, Any]:
    # 所有叙事文本都以状态机方式存储到 pending_story，避免前端重复写逻辑
    if step == 0:
        return {
            "title": "破晓低语·第一幕：童年、姐姐与未拆的信",
            "scene": Q1_ACT1_BACKSTORY_SCENE.strip(),
            "triggered": ["破晓低语·第一幕"],
            "choices": {
                "q1_read_done": "掩卷起身，回到此刻的破晓村",
            },
        }
    if step == 1:
        return {
            "title": "破晓低语·第二幕：碎光与求证",
            "scene": "你在破晓村外的古井旁，遇见一名独自守夜的旅人。\n\n她（他）说：\n“一个人很难穿过诅咒森林。你真的准备好带着别人一起承担风险了吗？”\n\n风从村口吹来，火把微微颤动。",
            "triggered": ["破晓低语·第二幕"],
            "choices": {
                "listen": "先停下，听它把话说完",
                "take": "不解释，直接催促对方立刻跟上",
                "walkaway": "不想耽搁，独自离开"
            },
        }
    return {
        "title": "破晓低语·第三幕：并肩而行",
        "scene": "旅人在火光里看着你，终于点头。\n\n“如果要进森林，我们就先约定：不是谁命令谁，而是彼此托底。”\n\n你决定邀请哪位同伴先加入队伍？",
        "triggered": ["破晓低语·第三幕"],
        "choices": {
            "cleric": "邀请黄晓茹（牧师）先同行：稳住队伍、先保命",
            "mage": "邀请王曦媛（法师）先同行：快速清场、提升输出"
        },
    }


def _q1_start_interactive_story(state: Dict[str, Any]) -> None:
    meta = state.setdefault("meta", {})
    meta["pending_story"] = {
        "sid": "q1_seal_whisper",
        "step": 0,
    }
    # 把场景内容也写入，前端可直接展示
    meta["pending_story"].update(_q1_story_scene(0))


def dq_ensure_q1_opening_story(state: Dict[str, Any]) -> None:
    """登录读档或新游戏后：若 Q1 未完成且无其它 pending 主线剧情，则进入破晓低语第一幕。"""
    if _q1_is_done(state):
        return
    meta = state.setdefault("meta", {})
    if meta.get("pending_story"):
        return
    if bool(meta.get("q1_act1_done")):
        return
    _q1_start_interactive_story(state)


def _main_story_scene(sid: str, step: int) -> Dict[str, Any]:
    if sid == "q1_seal_whisper":
        return _q1_story_scene(step)
    if sid == "q2_forest_echo":
        if step == 0:
            return {
                "title": "森林的回声·第一幕：林缘的走法",
                "scene": "瘴气在树梢间低伏，像一条犹豫的河。你站在三条几乎一样的岔口前：苔痕、风声、枯枝的断裂声，各自指向不同的“深入”。\n\n这里没有路标，只有态度——你决定用哪一种方式，走进枯萎之王的阴影里？",
                "triggered": ["森林的回声·第一幕"],
                "choices": {
                    "q2_a1_good": "沿苔痕最浅的小径绕半圈：让脚步先学会呼吸，再谈胜负。",
                    "q2_a1_mid": "循着风里最稳的节拍前进：不抢先机，只把概率握在可见处。",
                    "q2_a1_bad": "踩断枯枝径直深入：把犹豫留在身后，让阴影自己找上门。",
                },
            }
        return {
            "title": "森林的回声·第二幕：王座余烬",
            "scene": "枯萎之王崩解成灰，林间风声忽然整齐，像有人把散落的句子重新排成一行。\n\n腐木祭坛上，三枚同样大小的晶屑微微发亮，纹路却各不相同。你只能带走其中一枚——它会渗入你的行囊，成为下一段路途的质地。",
            "triggered": ["森林的回声·第二幕"],
            "choices": {
                "q2_pick_a": "拾起最沉静的那枚：光在内部缓慢折返，像把耐心炼成形状。",
                "q2_pick_b": "拾起最均衡的那枚：不冷也不烫，像把分寸握在掌心。",
                "q2_pick_c": "拾起最锋利的那枚：边缘微割手指，却让你更清醒。",
            },
        }

    if sid == "q3_mines_crack":
        if step == 0:
            return {
                "title": "矿坑的裂纹·第一幕：回声里的名字",
                "scene": "矿坑深处热浪翻涌。碎石缝里有一串被火烤黑的名字，像矿工留下的点名簿。\n\n你看见其中一行字：\n“若有人回到这里，请把我们带回天光。”",
                "triggered": ["矿坑的裂纹·第一幕"],
                "choices": {
                    "remember": "把名字记下，向更深处走",
                    "rush": "不管这些，先找灵矿之心",
                    "retreat": "这里太危险，先离开",
                },
            }
        if step == 1:
            return {
                "title": "矿坑的裂纹·第二幕：拿到之后",
                "scene": "你捧着那枚仍发烫的矿核，光在掌心跳动。\n\n井道外，一群疲惫的矿工后裔正望着你：\n他们在等的，不只是“矿石”，而是一个“交代”。",
                "triggered": ["矿坑的裂纹·第二幕"],
                "choices": {
                    "share": "先守住裂隙，再带走矿心：朱齐旻（猎人）加入小队",
                    "keep": "不分给谁，独自带走矿心：田可园（盗贼）加入小队",
                },
            }
        return {
            "title": "矿坑的裂纹·第三幕：熔核遗馈",
            "scene": "熔岩巨像坠入冷却的裂隙，赤红热流慢慢平息。\n\n碎裂的熔核边缘浮出三枚矿纹残片，像是灾厄最后的回声。你只能带走其中一枚。",
            "triggered": ["矿坑的裂纹·第三幕"],
            "choices": {
                "q3_pick_a": "选最沉稳的一枚：纹路厚重，像被锤炼过无数次。",
                "q3_pick_b": "选最均衡的一枚：光泽柔和，像把锋芒藏在秩序里。",
                "q3_pick_c": "选最锐利的一枚：边缘清脆，像一声短促却坚定的金鸣。",
            },
        }

    if sid == "q4_tide_price":
        if step == 0:
            return {
                "title": "潮汐的代价·第一幕：海边来信",
                "scene": "幽影海岸的风里夹着盐粒与低语。岸边漂来一封潮湿的信，字迹模糊：\n“钥匙可以开门，也可以开伤口。”\n\n远处渔火摇晃，像一只只尚未闭上的眼。",
                "triggered": ["潮汐的代价·第一幕"],
                "choices": {
                    "read": "把信读完，再决定去向",
                    "tear": "撕掉信件，钥匙最重要",
                    "sell": "先回村，把钥匙换成钱",
                },
            }
        if step == 1:
            return {
                "title": "潮汐的代价·第二幕：钥匙属于谁",
                "scene": "港口老灯塔前，守夜人递给你一盏破灯。\n\n“先让眼前的人活下去，再谈远方的使命。海给你的托付，不该只换一个人的前程。”\n\n你看见浪头里，还有人家在等火光。",
                "triggered": ["潮汐的代价·第二幕"],
                "choices": {
                    "light": "先点亮灯塔，安置村民，再收回钥匙",
                    "leave": "不耽搁，直接带钥匙赶往下一站",
                },
            }
        return {
            "title": "潮汐的代价·第三幕：潮汐遗馈",
            "scene": "女巫的潮咒散去，海面留下三枚缓缓旋转的潮晶。\n\n每一枚都映出不同的浪纹与光色，你只能挑选其一。",
            "triggered": ["潮汐的代价·第三幕"],
            "choices": {
                "q4_pick_a": "选最沉静的一枚：像深海，安静却有重量。",
                "q4_pick_b": "选最明亮的一枚：像潮头，平衡而有弹性。",
                "q4_pick_c": "选最锋利的一枚：像碎浪，凌厉而清醒。",
            },
        }

    # q5_throne_last：4幕（新增 Boss 后奖励幕）；未知 sid 不得回落到 Q5
    if sid == "q5_throne_last":
        if step == 0:
            return {
                "title": "王座的挑战·第一幕：门前",
                "scene": "你站在王座地牢的入口。门扉紧闭，冷风里却像有人在发问。\n\n石壁上刻着一行字：\n“你要带着谁，走到终点？”\n\n回声在廊道里来回，像无数脚步，又像只剩你自己的影子。",
                "triggered": ["王座的挑战·第一幕"],
                "choices": {
                    "everyone": "带着一路遇见的人与名字",
                    "myself": "只带自己，别的都不重要",
                    "power": "只带力量，其他都可舍弃",
                },
            }
        if step == 1:
            return {
                "title": "王座的挑战·第二幕：镜中人",
                "scene": "长廊深处，一面裂镜斜倚在墙边。镜中的你满身尘土，却仍在向前。\n\n镜面字迹般浮起一行问话：\n“如果终点没有掌声，你还会坚持吗？”",
                "triggered": ["王座的挑战·第二幕"],
                "choices": {
                    "yes": "会。因为有人在黑夜里等天亮",
                    "no": "不会。没有回报就没有意义",
                },
            }
        if step == 2:
            return {
                "title": "王座的挑战·第三幕：勇者之章",
                "scene": "半空悬着一页微光，像会呼吸的纸，看不清落款。\n\n它最后问：\n“你要把这章写成荣耀，还是写成责任？”",
                "triggered": ["王座的挑战·第三幕"],
                "choices": {
                    "duty": "写成责任：让后来的人少走一点弯路",
                    "glory": "写成荣耀：让世界记住我的名字",
                },
            }
        return {
            "title": "王座的挑战·第四幕：王座余辉",
            "scene": "守卫倒下后，王座大厅的裂缝中浮起三道淡金余辉。\n\n它们像未竟誓言的余温，静静等待你做出最后一次选择。",
            "triggered": ["王座的挑战·第四幕"],
            "choices": {
                "q5_pick_a": "选最沉稳的一道：像守护，厚重而长久。",
                "q5_pick_b": "选最均衡的一道：像秩序，克制却不失锋芒。",
                "q5_pick_c": "选最锐利的一道：像决断，短促却一锤定音。",
            },
        }

    return {
        "title": str(sid or "未知剧情"),
        "scene": "",
        "triggered": [],
        "choices": {},
    }


def _start_main_story(state: Dict[str, Any], sid: str, start_step: int = 0) -> None:
    meta = state.setdefault("meta", {})
    step0 = max(0, int(start_step))
    meta["pending_story"] = {"sid": sid, "step": step0}
    meta["pending_story"].update(_main_story_scene(sid, step0))


def _complete_story_by_sid(state: Dict[str, Any], sid: str) -> None:
    # 成功结算 q2~q5：任务完成 + 主线旗标 + 区域解锁
    quest = (state.get("quest") or {}).get("quests") or []
    if sid == "q2_forest_echo":
        state["boss_victories"] = max(1, state.get("boss_victories", 0) + 1)
        state["story_flags"]["artifacts"]["seal"] = True
        for q in quest:
            if q.get("qid") == "q2":
                q["progress"] = q.get("need", 1)
                q["done"] = True
        if "mines" not in state.get("unlocked_zones", []):
            state["unlocked_zones"].append("mines")
        m2 = state.setdefault("meta", {})
        m2.pop("q2_witherling_beaten_pending_echo", None)
        m2.pop("q2_boss_chance_add", None)
        m2.pop("q2_force_boss_next", None)
        m2.setdefault("log", []).append("📖 森林的回声归于平静。你真正听见了被遗忘的人。")
        return
    if sid == "q3_mines_crack":
        state["boss_victories"] = max(2, state.get("boss_victories", 0) + 1)
        state["story_flags"]["artifacts"]["ore"] = True
        for q in quest:
            if q.get("qid") == "q3":
                q["progress"] = q.get("need", 1)
                q["done"] = True
        if "coast" not in state.get("unlocked_zones", []):
            state["unlocked_zones"].append("coast")
        m3 = state.setdefault("meta", {})
        m3.pop("q3_golem_beaten_pending_echo", None)
        m3.pop("q3_boss_chance_add", None)
        m3.pop("q3_force_boss_next", None)
        m3.pop("q3_recruit_done", None)
        state.setdefault("meta", {}).setdefault("log", []).append("⚒️ 裂隙被封住，矿坑终于再次听见人的脚步。")
        return
    if sid == "q4_tide_price":
        state["boss_victories"] = max(3, state.get("boss_victories", 0) + 1)
        state["story_flags"]["artifacts"]["key"] = True
        for q in quest:
            if q.get("qid") == "q4":
                q["progress"] = q.get("need", 1)
                q["done"] = True
        if "throne" not in state.get("unlocked_zones", []):
            state["unlocked_zones"].append("throne")
        m4 = state.setdefault("meta", {})
        m4.pop("q4_sea_witch_beaten_pending_echo", None)
        m4.pop("q4_boss_chance_add", None)
        m4.pop("q4_force_boss_next", None)
        m4.pop("q4_act1_done", None)
        m4.pop("q4_act2_done", None)
        state.setdefault("meta", {}).setdefault("log", []).append("🌊 灯塔亮起，潮汐不再只是代价。")
        return
    if sid == "q5_throne_last":
        state["story_flags"]["artifacts"]["chapter"] = True
        for q in quest:
            if q.get("qid") == "q5":
                q["progress"] = q.get("need", 1)
                q["done"] = True
        m5 = state.setdefault("meta", {})
        m5.pop("q5_throne_guard_beaten_pending_echo", None)
        m5.pop("q5_boss_chance_add", None)
        m5.pop("q5_force_boss_next", None)
        m5.pop("q5_act1_done", None)
        m5.pop("q5_act2_done", None)
        m5.pop("q5_act3_done", None)
        state.setdefault("meta", {}).setdefault("log", []).append("👑 你把勇者之章写成了责任。黑夜仍在，但有人看见了黎明。")


def _story_success_choices(sid: str, step: int) -> List[str]:
    """
    返回当前幕允许“选对并可推进”的选项 id 列表。
    q2~q5 的“奖励幕”均为三选一成功并映射装备品质；q3 第二幕招募 2 选 1 均算成功。
    """
    table = {
        ("q1_seal_whisper", 0): ["q1_read_done"],
        ("q1_seal_whisper", 1): ["listen"],
        ("q1_seal_whisper", 2): ["cleric", "mage"],
        ("q2_forest_echo", 0): ["q2_a1_good", "q2_a1_mid", "q2_a1_bad"],
        ("q2_forest_echo", 1): ["q2_pick_a", "q2_pick_b", "q2_pick_c"],
        ("q3_mines_crack", 0): ["remember"],
        ("q3_mines_crack", 1): ["share", "keep"],
        ("q3_mines_crack", 2): ["q3_pick_a", "q3_pick_b", "q3_pick_c"],
        ("q4_tide_price", 0): ["read"],
        ("q4_tide_price", 1): ["light"],
        ("q4_tide_price", 2): ["q4_pick_a", "q4_pick_b", "q4_pick_c"],
        ("q5_throne_last", 0): ["everyone"],
        ("q5_throne_last", 1): ["yes"],
        ("q5_throne_last", 2): ["duty"],
        ("q5_throne_last", 3): ["q5_pick_a", "q5_pick_b", "q5_pick_c"],
    }
    return list(table.get((sid, step), []))


def _story_steps(sid: str) -> int:
    if sid in {"q3_mines_crack", "q4_tide_price"}:
        return 3
    if sid == "q5_throne_last":
        return 4
    if sid == "q2_forest_echo":
        return 2
    if sid == "q1_seal_whisper":
        return 3
    return 2


def _apply_story_penalty(state: Dict[str, Any], sid: str, step: int, rng: random.Random) -> None:
    # 选错后进入失败分支：多类型随机惩罚（资源/装备/属性/Boss强化等）
    meta = state.setdefault("meta", {})
    scar_key = f"{sid}_scar"
    add = 2 if sid == "q5_throne_last" else 1
    meta[scar_key] = int(meta.get(scar_key, 0) or 0) + add

    logs = meta.setdefault("log", [])
    penalties_applied: List[str] = []

    # 基础惩罚（始终存在）
    hp_loss = max(4, int(state.get("max_hp", 1) * (0.06 + 0.02 * step)))
    mp_loss = max(2, int(state.get("max_mp", 1) * (0.08 + 0.02 * step)))
    stamina_loss = 6 + step * 2
    state["hp"] = max(1, int(state.get("hp", 1) or 1) - hp_loss)
    state["mp"] = max(0, int(state.get("mp", 0) or 0) - mp_loss)
    state["stamina"] = max(0, int(state.get("stamina", 0) or 0) - stamina_loss)
    penalties_applied.append(f"HP-{hp_loss}/MP-{mp_loss}/体力-{stamina_loss}")

    # 惩罚池：抽 1~2 个额外惩罚
    pool = ["gold", "inventory", "equip_break", "attr_drop", "boss_boost", "boss_skill"]
    picks = 1 if step == 0 else 2
    rng.shuffle(pool)
    for kind in pool[:picks]:
        if kind == "gold":
            cur_gold = int(state.get("gold", 0) or 0)
            if cur_gold > 0:
                pct = rng.uniform(0.08, 0.22)
                lose = min(cur_gold, max(1, int(cur_gold * pct)))
                state["gold"] = cur_gold - lose
                penalties_applied.append(f"金币-{lose}（约{int(pct*100)}%）")

        elif kind == "inventory":
            inv = state.get("inventory", []) or []
            if inv:
                idx = rng.randrange(len(inv))
                it = inv[idx]
                q = max(1, int(it.get("qty", 1) or 1))
                meta_it = it.get("meta") or {}
                if meta_it.get("slot"):
                    lost_name = it.get("name", "装备")
                    inv.pop(idx)
                    penalties_applied.append(f"背包损失：{lost_name}")
                else:
                    lose_q = max(1, int(q * rng.uniform(0.25, 0.6)))
                    lose_q = min(q, lose_q)
                    it["qty"] = q - lose_q
                    lost_name = it.get("name", "物资")
                    if it["qty"] <= 0:
                        inv.pop(idx)
                    penalties_applied.append(f"背包损失：{lost_name}×{lose_q}")
                state["inventory"] = inv

        elif kind == "equip_break":
            eq = state.get("equipped") or {}
            non_empty = [s for s in EQUIPMENT_SLOTS if eq.get(s)]
            if non_empty:
                slot = rng.choice(non_empty)
                broken = eq.get(slot)
                eq[slot] = None
                state["equipped"] = eq
                _recalc_player_from_equipment(state)
                penalties_applied.append(f"装备碎裂：{SLOT_CN.get(slot, slot)}「{(broken or {}).get('name','?')}」")

        elif kind == "attr_drop":
            _ensure_attrs(state)
            ak = rng.choice(list(ATTR_KEYS))
            drop = 1 if step == 0 else rng.choice([1, 2])
            old = int(state["attrs"].get(ak, 1) or 1)
            state["attrs"][ak] = max(1, old - drop)
            _recalc_player_from_equipment(state)
            state["hp"] = min(int(state.get("hp", 1)), int(state.get("max_hp", 1)))
            state["mp"] = min(int(state.get("mp", 0)), int(state.get("max_mp", 1)))
            penalties_applied.append(f"属性衰减：{ak.upper()}-{drop}")

        elif kind == "boss_boost":
            curse = meta.setdefault("boss_curse", {})
            boost = curse.setdefault("boost", {"charges": 0, "hp_mult": 1.0, "atk_mult": 1.0, "def_mult": 1.0, "agi_mult": 1.0})
            boost["charges"] = int(boost.get("charges", 0) or 0) + 1
            boost["hp_mult"] = min(1.60, float(boost.get("hp_mult", 1.0)) + 0.08 + 0.02 * step)
            boost["atk_mult"] = min(1.50, float(boost.get("atk_mult", 1.0)) + 0.06 + 0.02 * step)
            boost["def_mult"] = min(1.45, float(boost.get("def_mult", 1.0)) + 0.05 + 0.02 * step)
            boost["agi_mult"] = min(1.35, float(boost.get("agi_mult", 1.0)) + 0.03 + 0.01 * step)
            penalties_applied.append("后续主线Boss强化（一次）")

        elif kind == "boss_skill":
            curse = meta.setdefault("boss_curse", {})
            sp = curse.setdefault("special", {"charges": 0, "open_charge": False})
            sp["charges"] = int(sp.get("charges", 0) or 0) + 1
            sp["open_charge"] = True
            penalties_applied.append("后续主线Boss获得特殊开场（蓄力）")

    if penalties_applied:
        logs.append("失败分支惩罚：" + "；".join(penalties_applied) + "。")


def dq_resolve_story_choice(state: Dict[str, Any], choice_id: str, rng: random.Random) -> Dict[str, Any]:
    """
    处理剧情互动的玩家选择。
    目前实现：q1 破晓低语（第一幕为散文无分支；第二幕起多分支，选错会增加难度/中断本次推进）。
    """
    state = copy.deepcopy(state)
    _ensure_meta_logs(state)
    meta = state.setdefault("meta", {})
    pending = meta.get("pending_story")
    if not isinstance(pending, dict):
        return state
    sid = str(pending.get("sid", ""))
    if sid not in ("q1_seal_whisper", "q2_forest_echo", "q3_mines_crack", "q4_tide_price", "q5_throne_last"):
        return state
    if choice_id is None:
        return state

    step = int(pending.get("step", 0) or 0)
    ok_choices = _story_success_choices(sid, step)
    if choice_id not in ok_choices:
        _apply_story_penalty(state, sid, step, rng)
        meta.setdefault("log", []).append(
            f"分支触发：{pending.get('title', sid)}（失败路线）本次中断推进。"
        )
        meta["pending_story"] = None
        return state

    # Q2 第一幕：选完即结束本段 pending，第二幕仅在击败枯萎之王后单独触发
    if sid == "q2_forest_echo" and step == 0:
        _apply_q2_act1_choice(state, choice_id, rng)
        meta["q2_echo_act1_done"] = True
        meta["pending_story"] = None
        meta.setdefault("log", []).append("✅ 森林的回声·第一幕已结束。继续探索直至遇见并击败枯萎之王。")
        return state

    # Q3 第二幕：先执行入队，再决定是否立刻进入第三幕（奖励幕）
    if sid == "q3_mines_crack" and step == 1:
        if choice_id == "share":
            _add_recruit_member(state, "hunter")
        elif choice_id == "keep":
            _add_recruit_member(state, "rogue")
        meta["q3_recruit_done"] = True
        if not _is_boss_defeated(state, "boss_golem"):
            meta.setdefault("log", []).append("🤝 新同伴已加入。下一步：前往矿坑深处击败熔岩巨像。")
            meta["pending_story"] = None
            return state

    # Q4 第一幕：完成即标记，第二幕需在海岸探索中另行触发
    if sid == "q4_tide_price" and step == 0:
        meta["q4_act1_done"] = True
        meta["pending_story"] = None
        meta.setdefault("log", []).append("✅ 潮汐的代价·第一幕已完成。继续在幽影海岸探索以触发第二幕。")
        return state

    # Q4 第二幕：完成后才可能遭遇潮汐女巫
    if sid == "q4_tide_price" and step == 1:
        meta["q4_act2_done"] = True
        meta["pending_story"] = None
        meta.setdefault("log", []).append("✅ 潮汐的代价·第二幕已完成。你已在海岸站稳脚跟，或将遭遇潮汐女巫。")
        return state

    # Q5 第一～三幕：各自在探索中触发，完成后才可能出现王座守卫
    if sid == "q5_throne_last" and step == 0:
        meta["q5_act1_done"] = True
        meta["pending_story"] = None
        meta.setdefault("log", []).append("✅ 王座的挑战·第一幕已完成。继续在王座地牢探索以触发第二幕。")
        return state
    if sid == "q5_throne_last" and step == 1:
        meta["q5_act2_done"] = True
        meta["pending_story"] = None
        meta.setdefault("log", []).append("✅ 王座的挑战·第二幕已完成。继续在王座地牢探索以触发第三幕。")
        return state
    if sid == "q5_throne_last" and step == 2:
        meta["q5_act3_done"] = True
        meta["pending_story"] = None
        meta.setdefault("log", []).append("✅ 王座的挑战·第三幕已完成。王座深处或将迎来最终守卫。")
        return state

    # 选对：推进到下一幕，或结算完成
    total = _story_steps(sid)
    if step + 1 < total:
        next_step = step + 1
        old_triggered = pending.get("triggered") or []
        if sid == "q1_seal_whisper":
            if step == 0 and choice_id == "q1_read_done":
                # 与前端一致：第一幕「已确认」后存档可恢复破晓村 BGM，无需依赖浏览器 sessionStorage
                meta["q1_act1_intro_video_completed"] = True
                meta["q1_act1_done"] = True
                # 第一幕后先进入新手探索引导：不立刻进入第二幕
                meta["q1_post_act1_tutorial"] = {
                    "active": True,
                    "explore_count": 0,
                    "focus": "explore_btn",  # explore_btn | log_result
                }
                meta["pending_story"] = None
                meta.setdefault("log", []).append("🎯 新手引导：请先点击「探索」继续推进（第一幕结束后教学）。")
                return state
            if step == 1 and choice_id == "listen":
                # 第二幕改为“独立完成”，第三幕需在后续探索中随机触发
                meta["q1_act2_done"] = True
                meta["pending_story"] = None
                meta.setdefault("log", []).append("✅ 破晓低语·第二幕已完成：继续探索，待时机成熟将触发第三幕。")
                return state
            nxt = _q1_story_scene(next_step)
        else:
            nxt = _main_story_scene(sid, next_step)
        pending["step"] = next_step
        pending.update(nxt)
        new_triggered = nxt.get("triggered") or []
        pending["triggered"] = old_triggered + [x for x in new_triggered if x not in old_triggered]
        meta["pending_story"] = pending
        meta.setdefault("log", []).append(f"已触发剧情：{pending.get('title')}")
        return state

    # 最后一幕成功
    if sid == "q1_seal_whisper":
        meta["q1_act3_done"] = True
        q1 = _q1_get_quest(state)
        if q1:
            q1["progress"] = int(q1.get("need", 1) or 1)
            q1["done"] = True
        if choice_id == "cleric":
            _add_recruit_member(state, "cleric")
        elif choice_id == "mage":
            _add_recruit_member(state, "mage")
        if "forest" not in state.get("unlocked_zones", []):
            state.setdefault("unlocked_zones", []).append("forest")
        meta["q1_scar"] = 0
        meta.setdefault("log", []).append("✅ 破晓之誓完成：首位伙伴已加入，诅咒森林已解锁。")
        meta.setdefault("log", []).append("触发剧情：破晓低语（三幕完成）")
        meta["pending_story"] = None
        return state

    if (
        (sid == "q2_forest_echo" and step == 1)
        or (sid == "q3_mines_crack" and step == 2)
        or (sid == "q4_tide_price" and step == 2)
        or (sid == "q5_throne_last" and step == 3)
    ):
        _grant_mainline_boss_spoils(state, sid, choice_id, rng)

    _complete_story_by_sid(state, sid)
    meta.setdefault("log", []).append(f"✅ 主线推进成功：{sid}")
    meta["pending_story"] = None
    return state


def dq_explore(state: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state
    state["meta"]["turn"] = int(state.get("meta", {}).get("turn", 0)) + 1
    if state.get("stamina", 0) <= 0:
        state["meta"]["log"].append("你太疲惫了，去旅店或等待被动恢复吧。")
        return state

    zone_id = state.get("location", "starter")
    # stamina cost（q1 错选会增加诅咒负担：森林体力消耗变高）
    cost = 5
    q1 = _q1_get_quest(state)
    scar = int((state.get("meta") or {}).get("q1_scar", 0) or 0)
    if zone_id == "forest" and q1 and not q1.get("done") and scar > 0:
        cost += scar
    state["stamina"] = max(0, state["stamina"] - cost)

    meta = state.setdefault("meta", {})
    q1_tutorial = meta.get("q1_post_act1_tutorial")
    if isinstance(q1_tutorial, dict) and bool(q1_tutorial.get("active")):
        t_cnt = int(q1_tutorial.get("explore_count", 0) or 0)
        # 教学第 1 次探索：固定不遇怪，展示探索结果
        if t_cnt <= 0:
            q1_tutorial["explore_count"] = 1
            q1_tutorial["focus"] = "log_then_explore"
            gain_gold = 10
            gain_xp = 5
            state["gold"] = int(state.get("gold", 0) or 0) + gain_gold
            state["exp"] = int(state.get("exp", 0) or 0) + gain_xp
            lines = [f"本次探索结果：你在路上捡到一些物资：获得 {gain_gold} 金币，经验 +{gain_xp}。"]
            _maybe_level_up(state, rng, lines)
            state["meta"]["log"].append("\n".join(lines))
            return state
        # 教学第 2 次探索：固定遭遇 Lv1 史莱姆
        if t_cnt == 1:
            q1_tutorial["explore_count"] = 2
            q1_tutorial["active"] = True
            q1_tutorial["focus"] = "battle_skill"
            meta["q1_post_act1_tutorial_done"] = True
            hero_lv_t = int(state.get("level", 1) or 1)
            enemy = _enemy_stats("slime", hero_lv_t, rng, scale=1.0, enemy_level=1)
            enemy["mid"] = "slime"
            enemy["name"] = _monster_catalog()["slime"]["name"]
            state = dq_start_battle(state, enemy)
            state["meta"]["log"].append("本次探索结果：⚔️ 新手教学触发：你遭遇了 Lv1 史莱姆！")
            state["meta"]["log"].append(
                f"📖 教学完成：当主角达到 Lv{Q1_ACT2_MIN_LEVEL} 后，继续在破晓村探索可随机触发「破晓低语·第二幕」。"
            )
            return state

    # Q1：第一幕后，第二幕改为探索随机触发（需等级门槛）
    if _q1_should_roll_act2(state) and rng.random() < Q1_ACT_RANDOM_CHANCE:
        _start_main_story(state, "q1_seal_whisper", 1)
        ttl = state["meta"]["pending_story"].get("title", "破晓低语·第二幕")
        state["meta"]["log"].append(
            f"📘 {ttl}（随机触发；需 Lv{Q1_ACT2_MIN_LEVEL}+，并已完成第一幕后教学）"
        )
        return state
    # Q1：第三幕同样随机触发（不再由第二幕必定衔接）
    if _q1_should_roll_act3(state) and rng.random() < Q1_ACT_RANDOM_CHANCE:
        _start_main_story(state, "q1_seal_whisper", 2)
        ttl = state["meta"]["pending_story"].get("title", "破晓低语·第三幕")
        state["meta"]["log"].append(
            f"📘 {ttl}（随机触发；需 Lv{Q1_ACT3_MIN_LEVEL}+，且第二幕已完成）"
        )
        return state

    # Q2 第一幕「坏」档：下一次诅咒森林探索直接切入枯萎之王战（已击败并待第二幕时不触发）
    if zone_id == "forest" and meta.get("q2_force_boss_next") and not meta.get("q2_witherling_beaten_pending_echo"):
        zf = _zone_catalog().get("forest", {})
        boss_id = "boss_witherling"
        if zf.get("boss") == boss_id and not _is_boss_defeated(state, boss_id):
            meta["q2_force_boss_next"] = False
            hero_lv = int(state.get("level", 1) or 1)
            floor_fb = max(1, int(state.get("dungeon", {}).get("floor", 1) or 1))
            boss_lv = int(BOSS_FIXED_LEVELS.get(boss_id, hero_lv))
            enemy = _enemy_stats(boss_id, hero_lv, rng, scale=1.0 + floor_fb * 0.03, enemy_level=boss_lv)
            enemy["mid"] = boss_id
            enemy["name"] = _monster_catalog()[boss_id]["name"]
            state = dq_start_battle(state, enemy)
            state["meta"]["log"].append(f"本次探索结果：🎭 腐息扑面……{enemy['name']} 已挡在你面前！")
            return state

    # Q3：Lv20 必遇熔岩巨像（仅在“已完成Q3招募剧情”后触发，避免跳过猎人/刺客入队）
    if (
        zone_id == "mines"
        and meta.get("q3_force_boss_next")
        and bool(meta.get("q3_recruit_done"))
        and not meta.get("q3_golem_beaten_pending_echo")
    ):
        zm = _zone_catalog().get("mines", {})
        boss_id_q3 = "boss_golem"
        if zm.get("boss") == boss_id_q3 and not _is_boss_defeated(state, boss_id_q3):
            meta["q3_force_boss_next"] = False
            hero_lv = int(state.get("level", 1) or 1)
            floor_fb = max(1, int(state.get("dungeon", {}).get("floor", 1) or 1))
            boss_lv = int(BOSS_FIXED_LEVELS.get(boss_id_q3, hero_lv))
            enemy = _enemy_stats(boss_id_q3, hero_lv, rng, scale=1.0 + floor_fb * 0.03, enemy_level=boss_lv)
            enemy["mid"] = boss_id_q3
            enemy["name"] = _monster_catalog()[boss_id_q3]["name"]
            state = dq_start_battle(state, enemy)
            state["meta"]["log"].append(f"本次探索结果：🎭 热浪扑面……{enemy['name']} 已挡在你面前！")
            return state

    # Q4：Lv26 起下次海岸「必遇潮汐女巫」——若前两幕未成功完成则 100% 先触发对应幕（不消耗必遇标记）
    if zone_id == "coast" and meta.get("q4_force_boss_next") and not meta.get("q4_sea_witch_beaten_pending_echo"):
        zc = _zone_catalog().get("coast", {})
        boss_id_q4 = "boss_sea_witch"
        if zc.get("boss") == boss_id_q4 and not _is_boss_defeated(state, boss_id_q4):
            if not bool(meta.get("q4_act1_done")):
                _start_main_story(state, "q4_tide_price", 0)
                ttl = state["meta"]["pending_story"].get("title", "潮汐的代价·第一幕")
                state["meta"]["log"].append(f"🌊 {ttl}（必遇 Boss 已推迟：须先完成第一幕）")
                return state
            if not bool(meta.get("q4_act2_done")):
                _start_main_story(state, "q4_tide_price", 1)
                ttl = state["meta"]["pending_story"].get("title", "潮汐的代价·第二幕")
                state["meta"]["log"].append(f"🌊 {ttl}（必遇 Boss 已推迟：须先完成第二幕）")
                return state
            meta["q4_force_boss_next"] = False
            hero_lv = int(state.get("level", 1) or 1)
            floor_fb = max(1, int(state.get("dungeon", {}).get("floor", 1) or 1))
            boss_lv = int(BOSS_FIXED_LEVELS.get(boss_id_q4, hero_lv))
            enemy = _enemy_stats(boss_id_q4, hero_lv, rng, scale=1.0 + floor_fb * 0.03, enemy_level=boss_lv)
            enemy["mid"] = boss_id_q4
            enemy["name"] = _monster_catalog()[boss_id_q4]["name"]
            state = dq_start_battle(state, enemy)
            state["meta"]["log"].append(f"本次探索结果：🎭 海雾翻涌……{enemy['name']} 已挡在你面前！")
            return state

    # Q4：幽影海岸随机触发第一幕 / 第二幕（完成第二幕后才可能随机遭遇潮汐女巫，见下方 Boss 判定）
    if zone_id == "coast" and _q4_should_roll_act1(state) and rng.random() < Q4_ACT_RANDOM_CHANCE:
        _start_main_story(state, "q4_tide_price", 0)
        ttl = state["meta"]["pending_story"].get("title", "潮汐的代价·第一幕")
        state["meta"]["log"].append(f"🌊 {ttl}（请在冒险页做出选择）")
        return state
    if zone_id == "coast" and _q4_should_roll_act2(state) and rng.random() < Q4_ACT_RANDOM_CHANCE:
        _start_main_story(state, "q4_tide_price", 1)
        ttl = state["meta"]["pending_story"].get("title", "潮汐的代价·第二幕")
        state["meta"]["log"].append(f"🌊 {ttl}（请在冒险页做出选择）")
        return state

    # Q5：Lv30 起下次王座「必遇王座守卫」——若前三幕未成功完成则 100% 先触发对应幕
    if zone_id == "throne" and meta.get("q5_force_boss_next") and not meta.get("q5_throne_guard_beaten_pending_echo"):
        zt = _zone_catalog().get("throne", {})
        boss_id_q5 = "boss_throne_guard"
        if zt.get("boss") == boss_id_q5 and not _is_boss_defeated(state, boss_id_q5):
            if not bool(meta.get("q5_act1_done")):
                _start_main_story(state, "q5_throne_last", 0)
                ttl = state["meta"]["pending_story"].get("title", "王座的挑战·第一幕")
                state["meta"]["log"].append(f"👑 {ttl}（必遇 Boss 已推迟：须先完成第一幕）")
                return state
            if not bool(meta.get("q5_act2_done")):
                _start_main_story(state, "q5_throne_last", 1)
                ttl = state["meta"]["pending_story"].get("title", "王座的挑战·第二幕")
                state["meta"]["log"].append(f"👑 {ttl}（必遇 Boss 已推迟：须先完成第二幕）")
                return state
            if not bool(meta.get("q5_act3_done")):
                _start_main_story(state, "q5_throne_last", 2)
                ttl = state["meta"]["pending_story"].get("title", "王座的挑战·第三幕")
                state["meta"]["log"].append(f"👑 {ttl}（必遇 Boss 已推迟：须先完成第三幕）")
                return state
            meta["q5_force_boss_next"] = False
            hero_lv = int(state.get("level", 1) or 1)
            floor_fb = max(1, int(state.get("dungeon", {}).get("floor", 1) or 1))
            boss_lv = int(BOSS_FIXED_LEVELS.get(boss_id_q5, hero_lv))
            enemy = _enemy_stats(boss_id_q5, hero_lv, rng, scale=1.0 + floor_fb * 0.03, enemy_level=boss_lv)
            enemy["mid"] = boss_id_q5
            enemy["name"] = _monster_catalog()[boss_id_q5]["name"]
            state = dq_start_battle(state, enemy)
            state["meta"]["log"].append(f"本次探索结果：🎭 甲胄铿鸣……{enemy['name']} 已挡在你面前！")
            return state

    # Q5：王座地牢随机触发第一幕 / 第二幕 / 第三幕（完成第三幕后才可能随机遭遇王座守卫）
    if zone_id == "throne" and _q5_should_roll_act1(state) and rng.random() < Q5_ACT_RANDOM_CHANCE:
        _start_main_story(state, "q5_throne_last", 0)
        ttl = state["meta"]["pending_story"].get("title", "王座的挑战·第一幕")
        state["meta"]["log"].append(f"👑 {ttl}（请在冒险页做出选择）")
        return state
    if zone_id == "throne" and _q5_should_roll_act2(state) and rng.random() < Q5_ACT_RANDOM_CHANCE:
        _start_main_story(state, "q5_throne_last", 1)
        ttl = state["meta"]["pending_story"].get("title", "王座的挑战·第二幕")
        state["meta"]["log"].append(f"👑 {ttl}（请在冒险页做出选择）")
        return state
    if zone_id == "throne" and _q5_should_roll_act3(state) and rng.random() < Q5_ACT_RANDOM_CHANCE:
        _start_main_story(state, "q5_throne_last", 2)
        ttl = state["meta"]["pending_story"].get("title", "王座的挑战·第三幕")
        state["meta"]["log"].append(f"👑 {ttl}（请在冒险页做出选择）")
        return state

    # Q2 第一幕：未完成时优先弹出（消耗本次探索体力，不进入下方随机遭遇）
    if _q2_should_start_act1(state):
        _start_main_story(state, "q2_forest_echo", 0)
        ttl = state["meta"]["pending_story"].get("title", "森林的回声·第一幕")
        state["meta"]["log"].append(f"🌲 {ttl}（请在冒险页做出选择）")
        return state

    # Q3：先触发“矿坑的裂纹”招募分支（猎人/刺客先加入），再去挑战熔岩巨像
    if (
        zone_id == "mines"
        and not _is_boss_defeated(state, "boss_golem")
        and not bool(meta.get("q3_recruit_done"))
        and not isinstance(meta.get("pending_story"), dict)
    ):
        _start_main_story(state, "q3_mines_crack", 0)
        ttl = state["meta"]["pending_story"].get("title", "矿坑的裂纹·第一幕")
        state["meta"]["log"].append(f"⛏️ {ttl}（请在冒险页做出选择）")
        return state

    zone = _zone_catalog().get(zone_id, _zone_catalog()["starter"])
    floor = state.get("dungeon", {}).get("floor", 1)

    roll = rng.random()
    encounter_chance = 0.38 if zone_id != "starter" else 0.28
    boss_chance = 0.06 if zone.get("boss") else 0.0
    if zone_id == "forest" and str(zone.get("boss")) == "boss_witherling":
        extra = float(meta.get("q2_boss_chance_add", 0) or 0)
        boss_chance = min(0.42, boss_chance + extra)
    if zone_id == "mines" and str(zone.get("boss")) == "boss_golem":
        extra3 = float(meta.get("q3_boss_chance_add", 0) or 0)
        boss_chance = min(0.42, boss_chance + extra3)
    if zone_id == "coast" and str(zone.get("boss")) == "boss_sea_witch":
        extra4 = float(meta.get("q4_boss_chance_add", 0) or 0)
        boss_chance = min(0.42, boss_chance + extra4)
    if zone_id == "throne" and str(zone.get("boss")) == "boss_throne_guard":
        extra5 = float(meta.get("q5_boss_chance_add", 0) or 0)
        boss_chance = min(0.42, boss_chance + extra5)
    hero_lv = int(state.get("level", 1) or 1)

    if roll < encounter_chance:
        # start battle
        if zone_id in ("forest", "mines", "coast", "throne") and zone.get("boss") and not _is_boss_defeated(state, zone.get("boss")):
            # occasionally boss "story encounter"
            boss_id = str(zone.get("boss"))
            echo_pending = (
                (boss_id == "boss_witherling" and bool(meta.get("q2_witherling_beaten_pending_echo")))
                or (boss_id == "boss_golem" and bool(meta.get("q3_golem_beaten_pending_echo")))
                or (boss_id == "boss_sea_witch" and bool(meta.get("q4_sea_witch_beaten_pending_echo")))
                or (boss_id == "boss_throne_guard" and bool(meta.get("q5_throne_guard_beaten_pending_echo")))
            )
            q4_sea_witch_allowed = boss_id != "boss_sea_witch" or bool(meta.get("q4_act2_done"))
            q5_throne_guard_allowed = boss_id != "boss_throne_guard" or bool(meta.get("q5_act3_done"))
            if (
                _can_trigger_story_boss_by_level(state, boss_id)
                and rng.random() < boss_chance
                and not echo_pending
                and q4_sea_witch_allowed
                and q5_throne_guard_allowed
            ):
                boss_id = zone.get("boss")
                boss_lv = int(BOSS_FIXED_LEVELS.get(str(boss_id), hero_lv))
                enemy = _enemy_stats(boss_id, hero_lv, rng, scale=1.0 + floor * 0.03, enemy_level=boss_lv)
                enemy["mid"] = boss_id
                enemy["name"] = _monster_catalog()[boss_id]["name"]
                state = dq_start_battle(state, enemy)
                state["meta"]["log"].append(f"本次探索结果：🎭 {zone['name']} 深处传来低沉的脚步声……你遇见了 {enemy['name']}！")
                return state

        enemy = _make_enemy_for_zone(zone_id, state["level"], rng, boss=False, floor=max(1, floor))
        state = dq_start_battle(state, enemy)
        state["meta"]["log"].append(f"本次探索结果：⚔️ 你遭遇了 {enemy['name']}！")
        return state

    # no encounter: loot / event
    plv0 = int(state.get("level", 1) or 1)
    if _is_player_trivializing_zone(plv0, zone_id):
        lines = ["本次探索结果：未遭遇敌人。该区域对你而言过于轻松（等级超过本图遇敌上限≥3级），未获得保底经验与金币。"]
    else:
        explore_xp = 5 + plv0 // 10
        gold_gain = rng.randint(3, 14)
        state["exp"] = int(state.get("exp", 0) or 0) + explore_xp
        state["gold"] = int(state.get("gold", 0) or 0) + gold_gain
        lines = [f"本次探索结果：你在路上搜刮到一些物资：获得 {gold_gain} 金币，经验 +{explore_xp}。"]
    # 药水（掉率下调）
    if rng.random() < 0.08:
        r2 = rng.random()
        if r2 < 0.65:
            pot = {"item_id": _new_id("pot", rng), "name": "恢复药水", "qty": 1, "meta": {"use": "heal_potion", "heal_pct": POTION_HP_PCT}}
            pot["meta"]["sell_price"] = _potion_unit_sell_price("heal_potion")
            extra = f"最大HP×{POTION_HP_PCT}%"
        elif r2 < 0.88:
            pot = {"item_id": _new_id("pot", rng), "name": "魔力药水", "qty": 1, "meta": {"use": "mp_potion", "mp_pct": POTION_MP_PCT}}
            pot["meta"]["sell_price"] = _potion_unit_sell_price("mp_potion")
            extra = f"最大MP×{POTION_MP_PCT}%"
        else:
            pot = {
                "item_id": _new_id("pot", rng),
                "name": "混合药水",
                "qty": 1,
                "meta": {"use": "dual_potion", "heal_pct": POTION_DUAL_HP_PCT, "mp_pct": POTION_DUAL_MP_PCT},
            }
            pot["meta"]["sell_price"] = _potion_unit_sell_price("dual_potion")
            extra = f"最大HP×{POTION_DUAL_HP_PCT}% + 最大MP×{POTION_DUAL_MP_PCT}%"
        ok, bad = dq_try_add_inventory(state, [pot])
        if ok:
            lines.append(f"另外得到「{pot['name']}」（{extra}）。")
        else:
            lines.append("你捡到药水，但背包已满，只好留在原地。")
    # Q2+ 稀有药水探索掉落（掉率远低于普通药水）
    if zone_id in ("forest", "mines", "coast", "throne") and rng.random() < 0.01:
        rr = rng.random()
        if rr < 0.42:
            rare = {
                "item_id": _new_id("pot", rng),
                "name": "特级恢复药水",
                "qty": 1,
                "meta": {"use": "full_heal_potion", "heal_pct": POTION_FULL_HP_PCT, "sell_price": _potion_unit_sell_price("full_heal_potion")},
            }
            rare_extra = f"最大HP×{POTION_FULL_HP_PCT}%"
        elif rr < 0.84:
            rare = {
                "item_id": _new_id("pot", rng),
                "name": "特级魔力药水",
                "qty": 1,
                "meta": {"use": "full_mp_potion", "mp_pct": POTION_FULL_MP_PCT, "sell_price": _potion_unit_sell_price("full_mp_potion")},
            }
            rare_extra = f"最大MP×{POTION_FULL_MP_PCT}%"
        else:
            rare = {
                "item_id": _new_id("pot", rng),
                "name": "金苹果",
                "qty": 1,
                "meta": {"use": "golden_apple", "heal_pct": POTION_GOLDEN_HP_PCT, "mp_pct": POTION_GOLDEN_MP_PCT, "sell_price": _potion_unit_sell_price("golden_apple")},
            }
            rare_extra = f"最大HP×{POTION_GOLDEN_HP_PCT}% + 最大MP×{POTION_GOLDEN_MP_PCT}%"
        ok_r, _ = dq_try_add_inventory(state, [rare])
        if ok_r:
            lines.append(f"💎 稀有掉落：得到「{rare['name']}」（{rare_extra}）。")
            rare_lines = _collect_rare_drop_names([rare])
            if rare_lines:
                _queue_unlock_notice(state, "🎁 稀有掉落", [f"获得：{x}" for x in rare_lines])
        else:
            lines.append("你看见一件稀有药水，但背包已满，未能带走。")
    # materials（每图独占一种区域材料；无限地牢按层映射到 Q1~Q5）
    if rng.random() < EXPLORE_MATERIAL_CHANCE:
        mat_z = _effective_zone_for_material(zone_id, max(1, int(floor or 1)))
        mats_name = ZONE_EXCLUSIVE_MATERIAL.get(mat_z)
        if not mats_name:
            mats_name = "草药"
        qty = _roll_material_qty_weighted_halving(rng)
        ok_m, _ = dq_try_add_material_stack(state, mats_name, qty, rng)
        if ok_m:
            lines.append(f"采集到材料：{mats_name} ×{qty}（已放入背包）。")
        else:
            lines.append(f"采集到材料 {mats_name} ×{qty}，但背包已满，无法带走。")
    # small story events（概率见 CLUE_EXPLORE_EVENT_CHANCE，诅咒森林略高便于 Q2 线索）
    clue_event_p = float(CLUE_EXPLORE_EVENT_CHANCE.get(str(zone_id), 0.12))
    # Lv≥本图遇敌上限+3 时几乎总进战斗，未遇敌分支很少 → 线索掷骰机会极少；若本图仍有未收集线索，则未遇敌时必进入线索掷骰
    if _is_player_trivializing_zone(plv0, zone_id) and _zone_has_unfound_clues(state, zone_id):
        clue_event_p = 1.0
    if rng.random() < clue_event_p:
        ev = rng.choice(zone["events"])
        clue_def, is_new = _discover_zone_clue(state, zone_id, rng)
        if clue_def:
            exp_to_next_now = max(1, int(state.get("exp_to_next", 1) or 1))
            clue_xp_gain = max(1, int(exp_to_next_now * 0.20))
            state["exp"] = int(state.get("exp", 0) or 0) + clue_xp_gain
            lines.append(f"事件：{ev}。你发现了关键线索【{clue_def.get('title','未知线索')}】。")
            lines.append(f"关键线索奖励：经验 +{clue_xp_gain}（当前经验条20%）。")
        else:
            lines.append(f"事件：{ev}。你暂未发现有效线索。")
    # q1 破晓低语：登录/新档已由 dq_ensure_q1_opening_story 挂上；此处兜底未挂上的旧档
    if zone_id == "starter" and not _q1_is_done(state):
        meta = state.get("meta") or {}
        if not meta.get("pending_story"):
            dq_ensure_q1_opening_story(state)
            if state["meta"].get("pending_story"):
                pending_title = state["meta"]["pending_story"].get("title", "破晓低语")
                lines.append(f"你听见一段特殊剧情在胸口回响：{pending_title}（需要你在界面选择继续）。")
    _maybe_level_up(state, rng, lines)
    state["meta"]["log"].append("\n".join(lines))
    return state


def _is_boss_defeated(state: Dict[str, Any], boss_key: str) -> bool:
    # 按主线任务完成状态判定 Boss 是否已击败，避免与 artifacts 标记混用导致提前“视为已击败”
    qid_map = {
        "boss_witherling": "q2",
        "boss_golem": "q3",
        "boss_sea_witch": "q4",
        "boss_throne_guard": "q5",
    }
    qid = qid_map.get(str(boss_key))
    if not qid:
        return False
    quests = ((state.get("quest") or {}).get("quests") or [])
    for q in quests:
        if str(q.get("qid", "")) == qid:
            return bool(q.get("done"))
    return False


def dq_rest(state: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    # 旅店：按人数扣 dq_inn_cost 金币，全员 HP/MP/体力回满，并清除玩家异常状态
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state
    _ensure_meta_logs(state)
    now_ts = int(time.time())
    # 先结算被动恢复，避免“刚好等满了但点旅店看不到”
    state = dq_time_regen(state, now_ts)

    state["meta"]["turn"] = int(state.get("meta", {}).get("turn", 0)) + 1
    cost = int(dq_inn_cost(state))
    gold_now = int(state.get("gold", 0) or 0)
    if gold_now < cost:
        state["meta"]["log"].append(f"钱不够，无法进入旅店（需 {cost} 金币，当前 {gold_now}）。")
        return state
    state["gold"] = gold_now - cost

    state["hp"] = int(state.get("max_hp", 1) or 1)
    state["mp"] = int(state.get("max_mp", 1) or 1)
    state["stamina"] = int(state.get("max_stamina", 0) or 0)
    state["status_effects"] = []
    # 队友回满（不影响队友的异常状态，因为目前没有队友异常系统）
    for mem in state.get("party_members", []) or []:
        mem["hp"] = int(mem.get("max_hp", 1) or 1)
        mem["mp"] = int(mem.get("max_mp", 0) or 0)

    state["meta"]["last_regen_ts"] = now_ts
    state["meta"]["log"].append(f"🛖 旅店休息：消耗 {cost} 金币，全员回满（HP/MP/体力）并清除异常。")
    return state


def dq_start_battle(state: Dict[str, Any], enemy: Dict[str, Any]) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    _ensure_meta_logs(state)
    state.setdefault("meta", {}).pop("battle_ui_last_action", None)
    state.setdefault("meta", {}).pop("dq_last_battle_outcome", None)
    # 剧情失败惩罚：后续主线 Boss 强化 / 特殊开场
    if _enemy_is_boss(enemy):
        curse = (state.get("meta") or {}).get("boss_curse") or {}
        boost = curse.get("boost") or {}
        if int(boost.get("charges", 0) or 0) > 0:
            hp_mult = max(1.0, float(boost.get("hp_mult", 1.0) or 1.0))
            atk_mult = max(1.0, float(boost.get("atk_mult", 1.0) or 1.0))
            def_mult = max(1.0, float(boost.get("def_mult", 1.0) or 1.0))
            agi_mult = max(1.0, float(boost.get("agi_mult", 1.0) or 1.0))
            enemy["max_hp"] = max(1, int(enemy.get("max_hp", 1) * hp_mult))
            enemy["hp"] = int(enemy["max_hp"])
            enemy["atk"] = max(1, int(enemy.get("atk", 1) * atk_mult))
            enemy["def"] = max(1, int(enemy.get("def", 1) * def_mult))
            enemy["agi"] = max(1, int(enemy.get("agi", 1) * agi_mult))
            state["meta"]["log"].append("⚠️ 惩罚生效：本次主线Boss被黑潮强化。")
            boost["charges"] = max(0, int(boost.get("charges", 0) or 0) - 1)
            if boost["charges"] <= 0:
                curse.pop("boost", None)
            else:
                curse["boost"] = boost
            state.setdefault("meta", {})["boss_curse"] = curse
    state["phase"] = "battle"
    state["encounter"] = {"enemy": enemy}
    state["battle"] = {
        "enemy": enemy,
        "player_hp": state["hp"],
        "player_max_hp": state["max_hp"],
        "player_mp": state["mp"],
        "player_max_mp": state["max_mp"],
        "player_atk": state["atk"],
        "player_def": _incoming_def_effective_for_unit(str(state.get("role", "warrior")), int(state.get("def", 1) or 1)),
        "player_mdef": _incoming_mdef_effective_for_unit(str(state.get("role", "warrior")), int(state.get("mdef", 1) or 1)),
        "turn": 1,
        "result": None,
        "enemy_mp": enemy.get("mp", 0),
        "enemy_power_strike_pending": False,
        "next_enemy_damage_mult": 1.0,
        "cover_party_turns": 0,
        "skill_cd": {"execution": 0, "armor_break": 0},
        "defend_cd": 0,
        "taunt_pending_next_enemy": False,
        "taunt_active_this_enemy_phase": False,
        "shield_counter_active": False,
        "war_cry_turns": 0,
        "player_damage_taken_this_turn": 0,
    }
    if _enemy_is_boss(enemy):
        curse = (state.get("meta") or {}).get("boss_curse") or {}
        sp = curse.get("special") or {}
        if int(sp.get("charges", 0) or 0) > 0 and bool(sp.get("open_charge", False)):
            state["battle"]["enemy_power_strike_pending"] = True
            state["meta"]["log"].append("⚠️ 惩罚生效：Boss 开场蓄力。")
            sp["charges"] = max(0, int(sp.get("charges", 0) or 0) - 1)
            if sp["charges"] <= 0:
                curse.pop("special", None)
            else:
                curse["special"] = sp
            state.setdefault("meta", {})["boss_curse"] = curse
    state["defend_turn"] = False
    state.setdefault("status_effects", [])
    # 当次战斗详情：每次进入 battle 都清空 battle_log
    state["meta"]["battle_log"] = ["— 战斗开始 —"]
    return state


def _battle_log_append_round_separator(logs: List[str], battle: Dict[str, Any]) -> None:
    """在本回合日志末尾追加回合分隔行（配合界面「最新在上」反转后，分隔行显示在该回合动作之上）。"""
    rn = int(battle.get("turn", 1) or 1)
    logs.append(f"════════ 第 {rn} 回合 ════════")


def _on_battle_win(state: Dict[str, Any], enemy: Dict[str, Any], rng: random.Random, logs: List[str]) -> None:
    boss_key = enemy.get("mid")
    # Q3：若同伴已在Boss前加入，则击败熔岩巨像后进入奖励幕（第三幕）而非直接结算
    if str(boss_key) == "boss_golem" and bool((state.get("meta") or {}).get("q3_recruit_done")):
        _start_main_story(state, "q3_mines_crack", 2)
        ttl = (state.get("meta") or {}).get("pending_story", {}).get("title", "矿坑的裂纹·第三幕")
        state.setdefault("meta", {}).setdefault("log", []).append(f"✨ 你触发了一段关键剧情：{ttl}（请在冒险页做出选择）。")
        return
    # q2~q5 改为互动剧情：击败 boss 后只触发剧情，不立即完成任务
    mapping = {
        "boss_witherling": "q2_forest_echo",
        "boss_golem": "q3_mines_crack",
        "boss_sea_witch": "q4_tide_price",
        "boss_throne_guard": "q5_throne_last",
    }
    sid = mapping.get(str(boss_key))
    if not sid:
        return
    meta = state.setdefault("meta", {})
    pending = meta.get("pending_story")
    if isinstance(pending, dict):
        return
    if str(boss_key) == "boss_witherling":
        meta["q2_witherling_beaten_pending_echo"] = True
        meta.pop("q2_boss_chance_add", None)
        meta.pop("q2_force_boss_next", None)
    if str(boss_key) == "boss_golem":
        meta["q3_golem_beaten_pending_echo"] = True
        meta.pop("q3_boss_chance_add", None)
        meta.pop("q3_force_boss_next", None)
    if str(boss_key) == "boss_sea_witch":
        meta["q4_sea_witch_beaten_pending_echo"] = True
        meta.pop("q4_boss_chance_add", None)
        meta.pop("q4_force_boss_next", None)
    if str(boss_key) == "boss_throne_guard":
        meta["q5_throne_guard_beaten_pending_echo"] = True
        meta.pop("q5_boss_chance_add", None)
        meta.pop("q5_force_boss_next", None)
    if sid == "q2_forest_echo":
        start_step = 1
    elif sid == "q4_tide_price":
        start_step = 2
    elif sid == "q5_throne_last":
        start_step = 3
    else:
        start_step = 0
    _start_main_story(state, sid, start_step)
    ttl = (state.get("meta") or {}).get("pending_story", {}).get("title", sid)
    state["meta"]["log"].append(f"✨ 你触发了一段关键剧情：{ttl}（请在冒险页做出选择）。")


INFINITE_FLOORS_PER_Q = 6
INFINITE_ZONE_ORDER = ("starter", "forest", "mines", "coast", "throne")
# 无限地牢单场遭遇敌人数上限（含 Boss+小怪合计）
INFINITE_ENCOUNTER_MAX_ENEMIES = 3
# Q4 海岸 / Q5 王座：遇敌略降攻、降防（仅对应 location；攻在既有倍率上再 ×0.9）
COAST_ENEMY_ATK_MULT = 0.80  
COAST_ENEMY_DEF_MULT = 0.88
THRONE_ENEMY_ATK_MULT = 0.80  
THRONE_ENEMY_DEF_MULT = 0.88


def _infinite_zone_for_floor(floor: int) -> str:
    f = max(1, int(floor or 1))
    idx = (f - 1) // INFINITE_FLOORS_PER_Q
    return INFINITE_ZONE_ORDER[idx % len(INFINITE_ZONE_ORDER)]


def _infinite_boss_count_for_floor(floor: int) -> int:
    """无限地牢层数（非主角等级）：31+ 起带 Boss，50 层起封顶 3 个 Boss。"""
    f = max(1, int(floor or 1))
    if f < 31:
        return 0
    if f < 41:
        return 1
    if f < 50:
        return 2
    return 3


def _infinite_zone_boss_mid(zone_id: str) -> str:
    """主线区域 Boss；Q1 无区域 Boss 时用枯萎之王作无限地牢补位。"""
    b = (_zone_catalog().get(zone_id) or {}).get("boss")
    if b:
        return str(b)
    return "boss_witherling"


def _infinite_encounter_log_name(enemies: List[Dict[str, Any]]) -> str:
    if not enemies:
        return "敌人"
    names = [str(e.get("name") or "?") for e in enemies[:3]]
    if len(enemies) > 3:
        return "、".join(names) + f" 等×{len(enemies)}"
    return "、".join(names)


def _infinite_apply_party_scaling(enemies: List[Dict[str, Any]], party_n: int) -> None:
    """对齐 _build_enemy_group：按队伍人数强化多怪遭遇。"""
    pn = max(1, int(party_n))
    ex = max(0, pn - 1)
    for i, e in enumerate(enemies):
        is_b = _enemy_is_boss(e)
        if is_b:
            hp_m = 1.0 + ex * 0.10
            atk_m = 1.0 + ex * 0.05
            def_m = 1.0 + ex * 0.04
            agi_m = 1.0 + ex * 0.03
        elif i == 0:
            hp_m = 1.0 + ex * 0.07
            atk_m = 1.0 + ex * 0.05
            def_m = 1.0 + ex * 0.04
            agi_m = 1.0 + ex * 0.03
        else:
            hp_m = 1.0 + ex * 0.06
            atk_m = 1.0 + ex * 0.04
            def_m = 1.0 + ex * 0.03
            agi_m = 1.0
        e["max_hp"] = max(1, int(e.get("max_hp", e.get("hp", 1)) * hp_m))
        e["hp"] = int(e["max_hp"])
        e["atk"] = max(1, int(e.get("atk", 1) * atk_m))
        e["def"] = max(1, int(e.get("def", 1) * def_m))
        e["agi"] = max(1, int(e.get("agi", 1) * agi_m))


def _infinite_active_enemy_from_battle(battle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """失败/逃跑后保留同一层遭遇：多怪存为 _preset_enemies，单怪沿用 _locked_group。"""
    ens = [e for e in (battle.get("enemies") or []) if isinstance(e, dict)]
    if len(ens) > 1:
        return {
            "_preset_enemies": [copy.deepcopy(e) for e in ens],
            "name": _infinite_encounter_log_name(ens),
            "mid": "infinite_encounter",
        }
    if len(ens) == 1:
        ae = copy.deepcopy(ens[0])
        ae["_locked_group"] = True
        return ae
    e0 = battle.get("enemy")
    if isinstance(e0, dict):
        ae = copy.deepcopy(e0)
        ae["_locked_group"] = True
        return ae
    return None


def _build_infinite_dungeon_encounter(state: Dict[str, Any], floor: int, rng: random.Random) -> List[Dict[str, Any]]:
    """每 6 层对应 Q1～Q5 循环；小怪仅从该 Q 的 monsters 池随机；层数决定 Boss 数量与小怪配比。"""
    zone_id = _infinite_zone_for_floor(floor)
    z = _zone_catalog().get(zone_id) or _zone_catalog()["starter"]
    monsters = [str(m) for m in (z.get("monsters") or []) if not str(m).startswith("boss_")]
    if not monsters:
        monsters = ["slime", "rat", "goblin"]
    n_boss = _infinite_boss_count_for_floor(floor)
    hero_lv = min(max(1, int(state.get("level", 1) or 1)), MAX_PLAYER_LEVEL)
    scale = 1.0 + (floor - 1) * 0.055 + max(0, hero_lv - 1) * 0.02
    scale = min(scale, 6.0)
    out: List[Dict[str, Any]] = []
    cap_total = max(1, int(INFINITE_ENCOUNTER_MAX_ENEMIES))
    if n_boss <= 0:
        total = rng.randint(1, cap_total)
        for _ in range(total):
            mid = rng.choice(monsters)
            out.append(_enemy_stats(mid, hero_lv, rng, scale=scale, enemy_level=floor))
        return out
    boss_mid = _infinite_zone_boss_mid(zone_id)
    for _ in range(n_boss):
        out.append(_enemy_stats(boss_mid, hero_lv, rng, scale=scale, enemy_level=floor))
    max_extra = max(0, cap_total - n_boss)
    n_min = rng.randint(0, max_extra) if max_extra > 0 else 0
    for _ in range(n_min):
        mid = rng.choice(monsters)
        out.append(_enemy_stats(mid, hero_lv, rng, scale=scale, enemy_level=floor))
    if not out:
        out.append(_enemy_stats(rng.choice(monsters), hero_lv, rng, scale=scale, enemy_level=floor))
    return out


def _restore_overworld_location_after_infinite_dungeon(state: Dict[str, Any]) -> None:
    """无限地牢仅临时把 location 设为 infinite；回大地图时恢复进入前的区域（探索仍用原图）。"""
    if str(state.get("location", "")) != "infinite":
        return
    meta = state.setdefault("meta", {})
    saved = meta.pop("saved_overworld_location", None)
    if saved is not None:
        state["location"] = str(saved)
    else:
        state["location"] = "starter"


def dq_open_infinite_dungeon_battle(state: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    """
    在无限地牢挑战：每次点击会创建一场战斗并进入 battle。
    floor 每次胜利后 +1，失败则不增长。
    """
    state = copy.deepcopy(state)
    # allow from overworld only
    if state.get("phase") != "overworld":
        return state
    state["meta"]["turn"] = int(state.get("meta", {}).get("turn", 0)) + 1
    _prev_loc = str(state.get("location") or "starter")
    if _prev_loc == "infinite":
        _prev_loc = str((state.get("meta") or {}).get("saved_overworld_location") or "starter")
    state.setdefault("meta", {})["saved_overworld_location"] = _prev_loc
    state["location"] = "infinite"
    floor = max(1, state.get("dungeon", {}).get("floor", 1))
    rng_local = rng
    dungeon = state.setdefault("dungeon", {})
    dungeon["training_mode"] = False
    dungeon.pop("training_floor", None)
    # 无限地牢：若当前层已存在“未通关敌人”，则复用同一个敌人，不跳层也不重置敌人属性
    active_enemy = dungeon.get("active_enemy")
    active_floor = dungeon.get("active_enemy_floor")
    if isinstance(active_enemy, dict) and active_floor == floor:
        nm = active_enemy.get("name") or _infinite_encounter_log_name(active_enemy.get("_preset_enemies") or [])
        state["meta"]["log"].append(f"🌀 无限地牢·第{floor}层再次挑战：{nm}！")
        ae = copy.deepcopy(active_enemy)
        if isinstance(ae.get("_preset_enemies"), list) and len(ae["_preset_enemies"]) > 0:
            return dq_start_battle(state, ae, rng_local)
        ae["_locked_group"] = True
        return dq_start_battle(state, ae, rng_local)
    enemies = _build_infinite_dungeon_encounter(state, floor, rng_local)
    _infinite_apply_party_scaling(enemies, _party_size(state))
    for e in enemies:
        e["eid"] = f"e_{rng_local.randint(1000,9999)}"
        e["is_boss"] = _enemy_is_boss(e)
    wrapper = {
        "_preset_enemies": enemies,
        "name": _infinite_encounter_log_name(enemies),
        "mid": "infinite_encounter",
    }
    state["dungeon"]["active_enemy"] = wrapper
    state["dungeon"]["active_enemy_floor"] = floor
    state = dq_start_battle(state, wrapper, rng_local)
    state["meta"]["log"].append(f"🌀 无限地牢·第{floor}层遭遇：{wrapper['name']}！")
    return state


def dq_open_infinite_dungeon_training_battle(state: Dict[str, Any], rng: random.Random, floor: int) -> Dict[str, Any]:
    """无限地牢训练：从 1~(最高层-1) 选择一层进行训练，进度不保存，怪物每次重生。"""
    state = copy.deepcopy(state)
    if state.get("phase") != "overworld":
        return state
    state["meta"]["turn"] = int(state.get("meta", {}).get("turn", 0) or 0) + 1
    _prev_loc = str(state.get("location") or "starter")
    if _prev_loc == "infinite":
        _prev_loc = str((state.get("meta") or {}).get("saved_overworld_location") or "starter")
    state.setdefault("meta", {})["saved_overworld_location"] = _prev_loc
    state["location"] = "infinite"
    dungeon = state.setdefault("dungeon", {})
    top_floor = max(1, int(dungeon.get("floor", 1) or 1))
    train_floor = max(1, min(max(1, top_floor - 1), int(floor or 1)))
    dungeon["training_mode"] = True
    dungeon["training_floor"] = int(train_floor)
    # 训练不复用 active_enemy，确保每次点击均生成新怪
    dungeon.pop("active_enemy", None)
    dungeon.pop("active_enemy_floor", None)

    enemies = _build_infinite_dungeon_encounter(state, train_floor, rng)
    _infinite_apply_party_scaling(enemies, _party_size(state))
    for e in enemies:
        e["eid"] = f"e_{rng.randint(1000,9999)}"
        e["is_boss"] = _enemy_is_boss(e)
    wrapper = {
        "_preset_enemies": enemies,
        "name": _infinite_encounter_log_name(enemies),
        "mid": "infinite_encounter",
    }
    state = dq_start_battle(state, wrapper, rng)
    state["meta"]["log"].append(
        f"🧪 无限地牢训练·第{train_floor}层：遭遇 {wrapper['name']}（训练不保存层进度）。"
    )
    return state


# ====== Multi-enemy + party combat overrides ======
def _alive_enemies(battle: Dict[str, Any]) -> List[Dict[str, Any]]:
    es = battle.get("enemies") or []
    return [e for e in es if int(e.get("hp", 0) or 0) > 0]


def _alive_allies(battle: Dict[str, Any]) -> List[Dict[str, Any]]:
    allies = battle.get("allies") or []
    return [a for a in allies if int(a.get("hp", 0) or 0) > 0]


def _sync_primary_enemy(battle: Dict[str, Any]) -> None:
    alive = _alive_enemies(battle)
    battle["enemy"] = alive[0] if alive else (battle.get("enemies") or [None])[0]


def _all_targets_for_enemy(battle: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if int(battle.get("player_hp", 0) or 0) > 0:
        out.append({"kind": "player"})
    for i, a in enumerate(battle.get("allies", []) or []):
        if int(a.get("hp", 0) or 0) <= 0:
            continue
        out.append({"kind": "ally", "idx": i, "aid": a.get("aid")})
    return out


def _smart_enemy(enemy: Dict[str, Any]) -> bool:
    mid = str(enemy.get("mid", ""))
    return mid.startswith("boss_") or mid in {
        "wraith",
        "sea_curse",
        "throne_guard",
        "miner_golem",
        "night_moth",
        "mine_spider",
        "wither_vine",
        "reef_crab",
    }


def _pick_enemy_target(state: Dict[str, Any], battle: Dict[str, Any], enemy: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    cands = _all_targets_for_enemy(battle)
    if not cands:
        return {"kind": "none"}
    if bool(battle.get("taunt_active_this_enemy_phase")):
        for t in cands:
            if t.get("kind") == "player":
                return t
        return rng.choice(cands)
    if not _smart_enemy(enemy):
        return rng.choice(cands)
    # 有智慧怪：优先攻击当前血量比例最低目标
    best = None
    best_ratio = 2.0
    for t in cands:
        if t["kind"] == "player":
            hp = int(battle.get("player_hp", 0) or 0)
            mh = int(battle.get("player_max_hp", 1) or 1)
        else:
            idx = int(t.get("idx", -1))
            allies = battle.get("allies", []) or []
            if idx < 0 or idx >= len(allies):
                continue
            a = allies[idx]
            hp = int(a.get("hp", 0) or 0)
            mh = int(a.get("max_hp", 1) or 1)
        ratio = hp / max(1, mh)
        if ratio < best_ratio:
            best_ratio = ratio
            best = t
    return best or rng.choice(cands)


def _apply_enemy_hit_target(state: Dict[str, Any], enemy: Dict[str, Any], dmg: int, target: Dict[str, Any], logs: List[str]) -> None:
    battle = state["battle"]
    dmg = int(int(dmg) * _cover_party_incoming_mult(battle))
    battle.pop("_last_guard_applied", None)
    guard_cfg = battle.get("guard_cfg") or {}
    guard_target_kind = str(guard_cfg.get("target_kind", ""))
    guard_target_idx = int(guard_cfg.get("target_idx", -1) or -1)
    guard_target_aid = str(guard_cfg.get("target_aid", "") or "")
    guard_active = bool(guard_cfg.get("active", False))

    # 防守结算：
    # 1) 防守自己：主角被命中时伤害 * DEFEND_SELF_INCOMING_MULT（减伤 65%）
    # 2) 防守队友：主角被命中时伤害 * DEFEND_GUARD_ALLY_INCOMING_MULT（减伤 45%）
    # 3) 防守队友且队友被命中：先 *DEFEND_GUARD_ALLY_INCOMING_MULT，再由主角与该队友各承担一半
    if guard_active and dmg > 0:
        if target.get("kind") == "player":
            if guard_target_kind == "player":
                dmg = int(dmg * DEFEND_SELF_INCOMING_MULT)
                battle["_last_guard_applied"] = {"kind": "self", "shown_dmg": int(dmg)}
            elif guard_target_kind == "ally":
                dmg = int(dmg * DEFEND_GUARD_ALLY_INCOMING_MULT)
                battle["_last_guard_applied"] = {"kind": "guard_ally_player_hit", "shown_dmg": int(dmg)}
        elif target.get("kind") == "ally" and guard_target_kind == "ally":
            idx_t = int(target.get("idx", -1))
            allies = battle.get("allies") or []
            aid_t = ""
            if 0 <= idx_t < len(allies):
                aid_t = str(allies[idx_t].get("aid") or allies[idx_t].get("mid") or "")
            if (idx_t == guard_target_idx) or (guard_target_aid and aid_t and aid_t == guard_target_aid):
                reduced = int(dmg * DEFEND_GUARD_ALLY_INCOMING_MULT)
                shared = int(reduced * 0.50)
                # 队友分担一半
                if 0 <= idx_t < len(allies):
                    if int(allies[idx_t].get("immune_turns", 0) or 0) > 0:
                        logs.append(f"✨ 圣光护佑生效：{allies[idx_t].get('name', '队友')} 本次伤害被完全免疫。")
                    else:
                        allies[idx_t]["hp"] = max(0, int(allies[idx_t].get("hp", 0) or 0) - shared)
                        if (
                            "thorn_shell" in _unit_accessory_special_ids(allies[idx_t])
                            and shared > 0
                            and enemy.get("hp", 0) > 0
                        ):
                            ref = max(1, int(shared * 0.08))
                            enemy["hp"] = max(0, int(enemy.get("hp", 0) or 0) - ref)
                            logs.append(f"✨ 饰品触发（{allies[idx_t].get('name', '队友')}）：「荆棘」反弹 {ref} 伤害！")
                # 主角分担另一半（仍可触发主角免疫/减伤天赋）
                if int(battle.get("player_immune_turns", 0) or 0) > 0:
                    logs.append("✨ 圣光护佑生效：本次代守伤害被完全免疫。")
                else:
                    rm, mit_bonus = _player_incoming_mitigation(state)
                    dmg_p = int(shared * rm * max(0.0, 1.0 - mit_bonus))
                    battle["player_hp"] = max(0, int(battle.get("player_hp", 0) or 0) - dmg_p)
                    _battle_track_player_damage_taken_this_turn(battle, dmg_p)
                    if "thorn_shell" in _accessory_special_ids(state) and dmg_p > 0 and enemy.get("hp", 0) > 0:
                        ref = max(1, int(dmg_p * 0.08))
                        enemy["hp"] = max(0, int(enemy.get("hp", 0) or 0) - ref)
                        logs.append(f"✨ 饰品触发（主角）：「荆棘」反弹 {ref} 伤害！")
                tnm = "队友"
                allies = battle.get("allies") or []
                if 0 <= idx_t < len(allies):
                    tnm = str(allies[idx_t].get("name", "队友"))
                logs.append(f"🛡️ 代守生效：你与{tnm}各承受 {shared} 点伤害（原始 {dmg}）。")
                battle["_last_guard_applied"] = {"kind": "guard_ally_shared", "shown_dmg": int(shared)}
                return

    if target.get("kind") == "player":
        if int(battle.get("player_immune_turns", 0) or 0) > 0:
            logs.append("✨ 圣光护佑生效：本次伤害被完全免疫。")
            return
        dmg = _shield_counter_pre_player_incoming(battle, int(dmg))
        rm, mit_bonus = _player_incoming_mitigation(state)
        dmg2 = int(dmg * rm * max(0.0, 1.0 - mit_bonus))
        battle["player_hp"] = max(0, int(battle.get("player_hp", 0) or 0) - dmg2)
        _battle_track_player_damage_taken_this_turn(battle, dmg2)
        _shield_counter_reflect_after_player_hit(battle, enemy, dmg2, logs)
        if "thorn_shell" in _accessory_special_ids(state) and dmg > 0 and enemy.get("hp", 0) > 0:
            ref = max(1, int(dmg2 * 0.08))
            enemy["hp"] = max(0, int(enemy.get("hp", 0) or 0) - ref)
            logs.append(f"✨ 饰品触发（主角）：「荆棘」反弹 {ref} 伤害！")
        return
    allies = battle.get("allies") or []
    idx = int(target.get("idx", -1))
    if 0 <= idx < len(allies):
        if int(allies[idx].get("immune_turns", 0) or 0) > 0:
            logs.append(f"✨ 圣光护佑生效：{allies[idx].get('name', '队友')} 本次伤害被完全免疫。")
            return
        allies[idx]["hp"] = max(0, int(allies[idx].get("hp", 0) or 0) - int(dmg))
        if (
            "thorn_shell" in _unit_accessory_special_ids(allies[idx])
            and int(dmg) > 0
            and enemy.get("hp", 0) > 0
        ):
            ref = max(1, int(int(dmg) * 0.08))
            enemy["hp"] = max(0, int(enemy.get("hp", 0) or 0) - ref)
            logs.append(f"✨ 饰品触发（{allies[idx].get('name', '队友')}）：「荆棘」反弹 {ref} 伤害！")


def _pick_player_target(battle: Dict[str, Any], target_id: Optional[str]) -> Optional[Dict[str, Any]]:
    alive = _alive_enemies(battle)
    if not alive:
        return None
    if target_id:
        for e in alive:
            if str(e.get("eid")) == str(target_id):
                return e
    return alive[0]


def _cleric_expected_holy_heal_amount(i: int, heal_bonus: float, heal_talent_mul: float) -> int:
    """圣疗期望治疗量（与施放公式一致，uniform(0.9,1.1) 取期望 1.0）。"""
    return max(6, int((9 + i * 2.4) * heal_bonus * heal_talent_mul))


def _cleric_expected_group_heal_each(i: int, heal_bonus: float, heal_talent_mul: float) -> int:
    """群体祈祷每人恢复量期望（uniform(0.9,1.08) 取均值）。"""
    mid = (0.9 + 1.08) / 2.0
    return max(5, int((8 + i * 1.85) * mid * heal_bonus * heal_talent_mul))


def _cleric_overheal_ratio_single(missing_hp: int, heal_amount: int) -> float:
    """过量治疗占比 = max(0, 治疗量-缺失量) / 治疗量。"""
    if heal_amount <= 0:
        return 1.0
    waste = max(0, heal_amount - max(0, missing_hp))
    return waste / float(heal_amount)


def _cleric_overheal_ratio_group(heal_each: int, recipients: List[Dict[str, Any]]) -> float:
    """群体治疗：总浪费量 / 总治疗量（与每人实际可吃下的治疗量对齐）。"""
    n = len(recipients)
    if n <= 0 or heal_each <= 0:
        return 1.0
    total_vol = float(heal_each * n)
    total_waste = 0.0
    for t in recipients:
        mh = int(t["max_hp"])
        hp = int(t["hp"])
        missing = max(0, mh - hp)
        total_waste += float(max(0, heal_each - missing))
    return total_waste / total_vol


def _cleric_any_below_hp_ratio(rows: List[Dict[str, Any]], ratio_max: float) -> bool:
    """是否存在友方当前 HP/最大 HP ≤ ratio_max（用于危急例外）。"""
    for t in rows:
        hp = int(t.get("hp", 0) or 0)
        mh = max(1, int(t.get("max_hp", 1) or 1))
        if hp / float(mh) <= ratio_max:
            return True
    return False


def _cleric_upper_incoming_normal_on_target(
    state: Dict[str, Any], battle: Dict[str, Any], enemy: Dict[str, Any], target: Dict[str, Any]
) -> int:
    """敌方一次普攻（非蓄力）对目标的伤害上界，用于判断「若本回合被全部敌人各命中一次普攻则阵亡」。"""
    att = int(enemy.get("atk", 1) or 1)
    tdef = _enemy_sea_magic_attack_resist(enemy, battle, target)
    power = 1.15
    base = att * power - tdef * (0.55 + 0.15 * power)
    base = max(1, int(base))
    dmg = max(1, int(base * 1.12))
    dmg = int(dmg * 1.7)
    dmg = int(dmg * _cover_party_incoming_mult(battle))
    gc = battle.get("guard_cfg") or {}
    if bool(gc.get("active")) and target.get("kind") == "player":
        gtk = str(gc.get("target_kind", "") or "")
        if gtk == "player":
            dmg = int(dmg * DEFEND_SELF_INCOMING_MULT)
        elif gtk == "ally":
            dmg = int(dmg * DEFEND_GUARD_ALLY_INCOMING_MULT)
    if target.get("kind") == "player":
        if int(battle.get("player_immune_turns", 0) or 0) > 0:
            return 0
        rm, mit_bonus = _player_incoming_mitigation(state)
        return int(dmg * rm * max(0.0, 1.0 - mit_bonus))
    idx = int(target.get("idx", -1))
    allies = battle.get("allies") or []
    if 0 <= idx < len(allies) and int(allies[idx].get("immune_turns", 0) or 0) > 0:
        return 0
    return int(dmg)


def _cleric_bless_target_key(t: Dict[str, Any]) -> Tuple[str, int]:
    if t.get("kind") == "player":
        return ("player", -1)
    return ("ally", int(t.get("idx", -1)))


def _cleric_bless_targets_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return _cleric_bless_target_key(a) == _cleric_bless_target_key(b)


def _cleric_bless_smart_enemy_pref_target(battle: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """与 _pick_enemy_target 中「有智慧怪」分支一致：取当前血量比例最低者（无随机）。"""
    cands = _all_targets_for_enemy(battle)
    if not cands:
        return None
    best: Optional[Dict[str, Any]] = None
    best_ratio = 2.0
    allies = battle.get("allies", []) or []
    for t in cands:
        if t.get("kind") == "player":
            hp = int(battle.get("player_hp", 0) or 0)
            mh = max(1, int(battle.get("player_max_hp", 1) or 1))
        else:
            idx = int(t.get("idx", -1))
            if idx < 0 or idx >= len(allies):
                continue
            al = allies[idx]
            hp = int(al.get("hp", 0) or 0)
            mh = max(1, int(al.get("max_hp", 1) or 1))
        ratio = hp / float(max(1, mh))
        if ratio < best_ratio:
            best_ratio = ratio
            best = t
    return best or (cands[0] if cands else None)


def _cleric_expected_incoming_normal_on_target(
    state: Dict[str, Any], battle: Dict[str, Any], target: Dict[str, Any]
) -> int:
    """
    本回合敌方阶段：按与 _pick_enemy_target 一致的目标倾向，估算各敌人「一次普攻伤害上界」对 target 的期望总和。
    - taunt_pending_next_enemy（盾反等）：下一敌方阶段单体目标强制主角。
    - 有智慧怪：锁定当前血线比最低目标；仅当锁定目标即 target 时计入全额上界，否则 0。
    - 非智慧怪：在存活目标集合上均匀随机；期望贡献 = 上界 / 目标数。
    """
    cands = _all_targets_for_enemy(battle)
    n_c = max(1, len(cands))
    taunt_next = bool(battle.get("taunt_pending_next_enemy"))
    total = 0
    for e in _alive_enemies(battle):
        upper_one = _cleric_upper_incoming_normal_on_target(state, battle, e, target)
        if upper_one <= 0:
            continue
        if taunt_next:
            if target.get("kind") == "player":
                total += upper_one
            continue
        if _smart_enemy(e):
            pref = _cleric_bless_smart_enemy_pref_target(battle)
            if pref is not None and _cleric_bless_targets_equal(pref, target):
                total += upper_one
        else:
            total += int(upper_one / float(n_c))
    return int(total)


def _cleric_warrior_shield_counter_active_for_bless(state: Dict[str, Any], battle: Dict[str, Any]) -> bool:
    """主角为战士且本回合已开盾反：敌方阶段将集火主角，赐福不应再套在主角身上。"""
    if str(state.get("role", "")) != "warrior":
        return False
    return bool(battle.get("taunt_pending_next_enemy")) or bool(battle.get("shield_counter_active"))


def _cleric_bless_pick_target(
    state: Dict[str, Any],
    battle: Dict[str, Any],
    allies: List[Dict[str, Any]],
    cleric_ally_idx: int,
) -> Optional[Dict[str, Any]]:
    """
    圣光赐福目标：当「按敌方目标选择规则，本回合普攻伤害上界之期望足以击杀该友方」时入选。
    多目标时：主角优先；若主角未入选且牧师本人入选，则保牧师；否则在入选者中取当前 HP/最大 HP 最低者。
    若入选含主角但主角战士已开盾反，则从入选者中排除主角再按同上规则选取；排除后无人入选则返回 None（本回合不施放赐福）。
    """
    lethal: List[Dict[str, Any]] = []

    def _ratio_for(t: Dict[str, Any]) -> float:
        if t.get("kind") == "player":
            hp = int(battle.get("player_hp", 0) or 0)
            mh = max(1, int(battle.get("player_max_hp", 1) or 1))
            return hp / float(mh)
        ix = int(t.get("idx", -1))
        if 0 <= ix < len(allies):
            hp = int(allies[ix].get("hp", 0) or 0)
            mh = max(1, int(allies[ix].get("max_hp", 1) or 1))
            return hp / float(mh)
        return 1.0

    def _pick_from_lethal(lethal_list: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not lethal_list:
            return None
        if any(x.get("kind") == "player" for x in lethal_list):
            return {"kind": "player"}
        if any(x.get("kind") == "ally" and int(x.get("idx", -1)) == cleric_ally_idx for x in lethal_list):
            return {"kind": "ally", "idx": cleric_ally_idx}
        return min(lethal_list, key=_ratio_for)

    tp = {"kind": "player"}
    if int(battle.get("player_hp", 0) or 0) > 0 and int(battle.get("player_immune_turns", 0) or 0) <= 0:
        tot = _cleric_expected_incoming_normal_on_target(state, battle, tp)
        if int(battle.get("player_hp", 0) or 0) <= tot:
            lethal.append({"kind": "player"})

    for idx, al in enumerate(allies):
        if int(al.get("hp", 0) or 0) <= 0:
            continue
        if int(al.get("immune_turns", 0) or 0) > 0:
            continue
        ta = {"kind": "ally", "idx": idx}
        tot = _cleric_expected_incoming_normal_on_target(state, battle, ta)
        if int(al.get("hp", 0) or 0) <= tot:
            lethal.append({"kind": "ally", "idx": idx})

    if not lethal:
        return None
    tgt = _pick_from_lethal(lethal)
    if (
        tgt is not None
        and tgt.get("kind") == "player"
        and _cleric_warrior_shield_counter_active_for_bless(state, battle)
    ):
        lethal_no_player = [x for x in lethal if x.get("kind") != "player"]
        tgt = _pick_from_lethal(lethal_no_player)
    return tgt


def _cleric_try_divine_bless(
    state: Dict[str, Any],
    battle: Dict[str, Any],
    allies: List[Dict[str, Any]],
    ally_idx: int,
    a: Dict[str, Any],
    skills: set,
    name: str,
    rng: random.Random,
    logs: List[str],
) -> bool:
    """若满足条件则施放圣光赐福并返回 True（已扣 MP、写冷却、追加战报与技能视频）。"""
    role = str(a.get("role", ""))
    if role != "cleric":
        return False
    cur_turn = int(battle.get("turn", 1) or 1)
    bless_ready_turn = int(a.get("divine_bless_ready_turn", 1) or 1)
    if (
        "divine_bless" not in skills
        or int(a.get("mp", 0) or 0) < CLERIC_MP_DIVINE_BLESS
        or cur_turn < bless_ready_turn
    ):
        return False
    tgt = _cleric_bless_pick_target(state, battle, allies, ally_idx)
    if tgt is None:
        return False
    a["mp"] = max(0, int(a.get("mp", 0) or 0) - CLERIC_MP_DIVINE_BLESS)
    a["divine_bless_ready_turn"] = cur_turn + 3
    if tgt["kind"] == "player":
        battle["player_immune_turns"] = 1
        logs.append(f"{name} 施放圣光赐福（MP-{CLERIC_MP_DIVINE_BLESS}），主角获得1回合伤害免疫。")
    else:
        ix = int(tgt["idx"])
        allies[ix]["immune_turns"] = 1
        logs.append(
            f"{name} 施放圣光赐福（MP-{CLERIC_MP_DIVINE_BLESS}），{allies[ix].get('name','队友')} 获得1回合伤害免疫。"
        )
    _sk_db = _skill_catalog().get("divine_bless")
    _dq_append_ally_skill_video(battle, role, _sk_db.name if _sk_db else "圣光赐福")
    return True


def _cleric_divine_bless_before_enemy_phase(state: Dict[str, Any], rng: random.Random, logs: List[str]) -> None:
    """敌方即将先手行动时：先让存活牧师按规则判定并施放圣光赐福，避免免疫晚于敌方普攻结算。"""
    battle = state["battle"]
    allies = battle.get("allies") or []
    for ally_idx, a in enumerate(allies):
        if int(a.get("hp", 0) or 0) <= 0:
            continue
        skills = set(a.get("skills") or [])
        name = str(a.get("name", "队友"))
        if _cleric_try_divine_bless(state, battle, allies, ally_idx, a, skills, name, rng, logs):
            battle["_cleric_divine_bless_done_pre_enemy"] = True
            return


def _cleric_overheal_amount_group_before_heal(
    battle: Dict[str, Any], allies: List[Dict[str, Any]], heal_each: int
) -> int:
    """群体治疗施放前：若每人恢复 heal_each，总计会产生多少过量治疗。"""
    if heal_each <= 0:
        return 0
    total = 0
    php = int(battle.get("player_hp", 0) or 0)
    pmh = max(1, int(battle.get("player_max_hp", 1) or 1))
    total += max(0, heal_each - max(0, pmh - php))
    for al in allies:
        if int(al.get("hp", 0) or 0) <= 0:
            continue
        h = int(al.get("hp", 0) or 0)
        m = max(1, int(al.get("max_hp", 1) or 1))
        total += max(0, heal_each - max(0, m - h))
    return total


def _cleric_tongqi_overheal_smite(
    state: Dict[str, Any],
    battle: Dict[str, Any],
    ally_name: str,
    ally_idx: int,
    talents: Any,
    rng: random.Random,
    logs: List[str],
    overheal_total: int,
) -> None:
    """同祈（cleric_t20_b）：将过量治疗量按比例转为对随机存活敌人的直接伤害。"""
    if overheal_total <= 0 or "cleric_t20_b" not in talents:
        return
    ratio = float(
        TALENT_CHOICE_DEFS.get("cleric_t20_b", {}).get("effects", {}).get("overheal_smite_ratio", 0.30) or 0.30
    )
    if ratio <= 0:
        return
    es = _alive_enemies(battle)
    if not es:
        return
    raw = max(1, int(overheal_total * ratio))
    target_e = rng.choice(es)
    fd = _apply_wither_boss_incoming_damage(
        target_e, raw, battle, logs, reflect_from="ally", ally_idx=ally_idx
    )
    logs.append(
        f"同祈：{ally_name} 将 {overheal_total} 点过量治疗按 {int(ratio * 100)}% 转化为惩戒（{raw}），对 {target_e.get('name', '敌人')} 造成 {fd} 伤害。"
    )


def _dq_battle_video_safe_segment(s: str) -> str:
    bad = '<>:"/\\|?*\n\r\t'
    out = str(s or "")
    for c in bad:
        out = out.replace(c, "_")
    return out.strip() or "动作"


def _dq_append_turn_video_stem(battle: Dict[str, Any], stem: str) -> None:
    if not stem:
        return
    battle.setdefault("dq_turn_video_stems", []).append(stem)


def _dq_append_ally_skill_video(battle: Dict[str, Any], role: str, skill_display_name: str) -> None:
    rc = ROLE_CN.get(str(role), "战士")
    seg = _dq_battle_video_safe_segment(skill_display_name)
    _dq_append_turn_video_stem(battle, f"{rc}_技能_{seg}")


def _dq_append_ally_attack_video(battle: Dict[str, Any], role: str) -> None:
    rc = ROLE_CN.get(str(role), "战士")
    _dq_append_turn_video_stem(battle, f"{rc}_普攻")


def _dq_player_video_stem_from_action(state: Dict[str, Any], action: Dict[str, Any]) -> Optional[str]:
    kind = action.get("kind")
    role = str(state.get("role", "warrior"))
    role_cn = ROLE_CN.get(role, "战士")
    seg: Optional[str] = None
    if kind == "attack":
        seg = "普攻"
    elif kind == "skill":
        sid = str(action.get("sid") or "")
        sk = _skill_catalog().get(sid)
        label = sk.name if sk else sid
        seg = f"技能_{_dq_battle_video_safe_segment(label)}"
    elif kind == "defend":
        seg = "防守"
    elif kind == "item":
        nm = "药水"
        for it in state.get("inventory") or []:
            if it.get("item_id") == action.get("item_id"):
                nm = str(it.get("name", "药水") or "药水")
                break
        seg = _dq_battle_video_safe_segment(nm)
    elif kind == "flee":
        seg = "逃跑"
    if not seg:
        return None
    if role == "warrior":
        hg = str(state.get("hero_gender") or "男").strip()
        if hg not in ("男", "女"):
            hg = "男"
        return f"{role_cn}_{hg}_{seg}"
    return f"{role_cn}_{seg}"


def _dq_try_append_player_video_stem(state: Dict[str, Any], battle: Dict[str, Any], action: Dict[str, Any]) -> None:
    kind = action.get("kind")
    if kind == "flee":
        return
    if kind in ("attack", "skill"):
        if not _pick_player_target(battle, action.get("target_id")):
            return
    if kind == "skill":
        sid = action.get("sid")
        if sid not in _skill_catalog():
            return
    stem = _dq_player_video_stem_from_action(state, action)
    if stem:
        _dq_append_turn_video_stem(battle, stem)


def _allies_auto_action(state: Dict[str, Any], rng: random.Random, logs: List[str]) -> None:
    battle = state["battle"]
    enemies = _alive_enemies(battle)
    if not enemies:
        return
    allies = battle.get("allies") or []
    for ally_idx, a in enumerate(allies):
        if int(a.get("hp", 0) or 0) <= 0:
            continue
        role = str(a.get("role", ""))
        skills = set(a.get("skills") or [])
        arm = (state.get("party_armory") or {}).get(role, {}) if isinstance(state.get("party_armory"), dict) else {}
        talents = set(a.get("talents") or [])
        attrs = a.get("attrs") or {}
        eq_bonus = _compute_equip_attr_bonus(a.get("equipped") or {})
        weapon_meta = {}
        w_it = (a.get("equipped") or {}).get("weapon")
        if isinstance(w_it, dict):
            weapon_meta = w_it.get("meta") or {}
        s = int(attrs.get("str", 1) or 1) + int(eq_bonus.get("str", 0) or 0)
        i = int(attrs.get("int", 1) or 1) + int(eq_bonus.get("int", 0) or 0) + int(arm.get("int_bonus", 0) or 0)
        d = int(attrs.get("dex", 1) or 1) + int(eq_bonus.get("dex", 0) or 0) + int(arm.get("dex_bonus", 0) or 0)
        g = int(attrs.get("agi", 1) or 1) + int(eq_bonus.get("agi", 0) or 0) + int(arm.get("agi_bonus", 0) or 0)
        l = int(attrs.get("luk", 1) or 1) + int(eq_bonus.get("luk", 0) or 0)
        name = a.get("name", "队友")
        spell_bonus = 1.0 + float(arm.get("spell_bonus", 0.0) or 0.0) + float(weapon_meta.get("spell_bonus", 0.0) or 0.0)
        heal_bonus = 1.0 + float(arm.get("heal_bonus", 0.0) or 0.0) + float(weapon_meta.get("heal_bonus", 0.0) or 0.0)
        atk_bonus = 1.0 + float(arm.get("atk_bonus", 0.0) or 0.0) + float(weapon_meta.get("atk_bonus", 0.0) or 0.0)
        ally_hit_rate = _role_hit_rate(role, d)
        ally_special_ids = set(_unit_accessory_special_ids(a))
        _map_crit_bonus = float((state.get("resources") or {}).get("clue_bonus_crit", 0.0) or 0.0)

        def _acrit(c: float, cap: float = 0.45) -> float:
            """王座洞察等全局暴击率：与主角 resources.clue_bonus_crit 一致（连射等用 cap=0.85）。"""
            return min(cap, c + _map_crit_bonus)

        def _ally_post_damage_specials(target_enemy: Dict[str, Any], dealt: int) -> None:
            if dealt <= 0:
                return
            # 巨像猎手：对非Boss额外增伤（与主角同规则）
            if "giant_slayer" in ally_special_ids and not _enemy_is_boss(target_enemy):
                # 这里在伤害结算后做一次等效附加伤害，避免重写整段技能分支
                extra = max(1, int(dealt * 0.10))
                target_enemy["hp"] = max(0, int(target_enemy.get("hp", 0) or 0) - extra)
                logs.append(f"✨ 饰品触发（{name}）：「巨像猎手」追加 {extra} 伤害！")
                dealt += extra
            # 噬魔：造成伤害后回蓝
            if "soul_drink" in ally_special_ids:
                g = max(1, int(dealt * 0.04))
                a["mp"] = min(int(a.get("max_mp", 0) or 0), int(a.get("mp", 0) or 0) + g)
                logs.append(f"✨ 饰品触发（{name}）：「噬魔」回复 MP +{g}")
            # 裁决：在「暗杀」10%必杀未触发后的本段伤害之后判定（非Boss、生命≤22%时2.5%斩杀）
            if "execute" in ally_special_ids and not _enemy_is_boss(target_enemy):
                hp_now = int(target_enemy.get("hp", 0) or 0)
                hp_max = max(1, int(target_enemy.get("max_hp", 1) or 1))
                if hp_now > 0 and (hp_now / float(hp_max)) <= 0.22 and rng.random() < 0.025:
                    target_enemy["hp"] = 0
                    logs.append(f"✨ 饰品触发（{name}）：「裁决」触发斩杀！")

        def _random_enemy() -> Optional[Dict[str, Any]]:
            es = _alive_enemies(battle)
            return rng.choice(es) if es else None

        if role == "cleric":
            # 圣光赐福：敌方先手时已在敌方行动前结算，此处跳过以免重复施放
            if not bool(battle.get("_cleric_divine_bless_done_pre_enemy")) and _cleric_try_divine_bless(
                state, battle, allies, ally_idx, a, skills, name, rng, logs
            ):
                continue

            # 先治疗：任一友方未满则优先治疗最低血量比例
            heal_talent_mul = 1.0
            holy_heal_cost = CLERIC_MP_HOLY_HEAL
            group_prayer_cost = CLERIC_MP_GROUP_PRAYER
            mp_now = int(a.get("mp", 0) or 0)
            if "cleric_t10_a" in talents:
                heal_talent_mul += float(TALENT_CHOICE_DEFS.get("cleric_t10_a", {}).get("effects", {}).get("heal_bonus", 0.0) or 0.0)
            purify_chance = float(TALENT_CHOICE_DEFS.get("cleric_t10_b", {}).get("effects", {}).get("heal_purify_chance", 0.0) or 0.0) if "cleric_t10_b" in talents else 0.0
            group_prayer_chance = float(CLERIC_GROUP_PRAYER_CHANCE_BASE)
            group_prayer_force = "cleric_t30_a" in talents
            targets = [{"kind": "player", "hp": battle["player_hp"], "max_hp": battle["player_max_hp"]}]
            for idx, al in enumerate(allies):
                if int(al.get("hp", 0) or 0) > 0:
                    targets.append({"kind": "ally", "idx": idx, "hp": al.get("hp", 0), "max_hp": al.get("max_hp", 1)})
            need = [t for t in targets if int(t["hp"]) < int(t["max_hp"])]
            if need:
                # 主角 + 两名存活队友共三人皆未满血时，大幅提高群体祈祷触发率
                if len(need) >= 3:
                    group_prayer_chance = float(CLERIC_GROUP_PRAYER_CHANCE_ALL_THREE_NOT_FULL)
                tgt = min(need, key=lambda x: int(x["hp"]) / max(1, int(x["max_hp"])))
                group_recipients = [{"hp": int(battle["player_hp"]), "max_hp": int(battle["player_max_hp"])}]
                for idx, al in enumerate(allies):
                    if int(al.get("hp", 0) or 0) > 0:
                        group_recipients.append({"hp": int(al.get("hp", 0) or 0), "max_hp": int(al.get("max_hp", 1) or 1)})
                exp_group_each = _cleric_expected_group_heal_each(i, heal_bonus, heal_talent_mul)
                group_critical = _cleric_any_below_hp_ratio(need, CLERIC_OVERHEAL_IGNORE_MAX_HP_RATIO)
                group_overheal_ok = group_critical or (
                    _cleric_overheal_ratio_group(exp_group_each, group_recipients) <= CLERIC_MAX_OVERHEAL_RATIO
                )
                if (
                    "group_prayer" in skills
                    and len(need) >= 2
                    and mp_now >= group_prayer_cost
                    and (group_prayer_force or rng.random() < group_prayer_chance)
                    and group_overheal_ok
                ):
                    # 小群疗（过量治疗占比过高则不放，改试圣疗或输出）
                    a["mp"] = max(0, mp_now - group_prayer_cost)
                    heal_each = max(5, int((8 + i * 1.85) * rng.uniform(0.9, 1.08) * heal_bonus * heal_talent_mul))
                    ov_group = _cleric_overheal_amount_group_before_heal(battle, allies, heal_each)
                    battle["player_hp"] = min(int(battle["player_max_hp"]), int(battle["player_hp"]) + heal_each)
                    for idx, al in enumerate(allies):
                        if int(al.get("hp", 0) or 0) > 0:
                            allies[idx]["hp"] = min(int(allies[idx]["max_hp"]), int(allies[idx]["hp"]) + heal_each)
                    logs.append(f"{name} 施放群体祈祷（MP-{group_prayer_cost}），全队恢复 {heal_each} HP。")
                    _cleric_tongqi_overheal_smite(state, battle, name, ally_idx, talents, rng, logs, ov_group)
                    if purify_chance > 0 and state.get("status_effects"):
                        if rng.random() < purify_chance:
                            state["status_effects"].pop(0)
                            logs.append(f"{name} 的祈祷净化了一个异常状态。")
                    _sk_gp = _skill_catalog().get("group_prayer")
                    _dq_append_ally_skill_video(battle, role, _sk_gp.name if _sk_gp else "群体祈祷")
                    continue
                if mp_now < holy_heal_cost:
                    # MP 不足以使用圣疗，转为攻击行为
                    pass
                else:
                    missing_tgt = int(tgt["max_hp"]) - int(tgt["hp"])
                    exp_holy = _cleric_expected_holy_heal_amount(i, heal_bonus, heal_talent_mul)
                    tgt_ratio = int(tgt["hp"]) / max(1.0, float(int(tgt["max_hp"])))
                    holy_critical = tgt_ratio <= CLERIC_OVERHEAL_IGNORE_MAX_HP_RATIO
                    holy_overheal_ok = holy_critical or (
                        _cleric_overheal_ratio_single(missing_tgt, exp_holy) <= CLERIC_MAX_OVERHEAL_RATIO
                    )
                    if holy_overheal_ok:
                        a["mp"] = max(0, mp_now - holy_heal_cost)
                        heal = max(6, int((9 + i * 2.4) * rng.uniform(0.9, 1.1) * heal_bonus * heal_talent_mul))
                        ov_holy = 0
                        if tgt["kind"] == "player":
                            php = int(battle["player_hp"])
                            pmh = int(battle["player_max_hp"])
                            ov_holy = max(0, heal - max(0, pmh - php))
                            battle["player_hp"] = min(int(battle["player_max_hp"]), int(battle["player_hp"]) + heal)
                            logs.append(f"{name} 施放圣疗（MP-{holy_heal_cost}），主角恢复 {heal} HP。")
                        else:
                            idx = int(tgt["idx"])
                            h0 = int(allies[idx]["hp"])
                            m0 = int(allies[idx]["max_hp"])
                            ov_holy = max(0, heal - max(0, m0 - h0))
                            allies[idx]["hp"] = min(int(allies[idx]["max_hp"]), int(allies[idx]["hp"]) + heal)
                            logs.append(f"{name} 施放圣疗（MP-{holy_heal_cost}），{allies[idx].get('name','队友')} 恢复 {heal} HP。")
                        _cleric_tongqi_overheal_smite(state, battle, name, ally_idx, talents, rng, logs, ov_holy)
                        if purify_chance > 0 and state.get("status_effects"):
                            if rng.random() < purify_chance:
                                state["status_effects"].pop(0)
                                logs.append(f"{name} 的圣疗净化了一个异常状态。")
                        _sk_hh = _skill_catalog().get("holy_heal")
                        _dq_append_ally_skill_video(battle, role, _sk_hh.name if _sk_hh else "圣疗")
                        continue
            # 全员满血时使用攻击法术
            e = _random_enemy()
            if not e:
                break
            judgement_cost = CLERIC_MP_JUDGEMENT
            mp_now = int(a.get("mp", 0) or 0)
            if "judgement" in skills:
                if mp_now >= judgement_cost:
                    a["mp"] = max(0, mp_now - judgement_cost)
                    if rng.random() > ally_hit_rate:
                        logs.append(f"{name} 施放惩戒术（MP-{judgement_cost}）但未命中。")
                        _sk_j = _skill_catalog().get("judgement")
                        _dq_append_ally_skill_video(battle, role, _sk_j.name if _sk_j else "惩戒术")
                        continue
                    crit = min(0.28, 0.03 + g * 0.0016)
                    if "cleric_t30_b" in talents:
                        crit += float(TALENT_CHOICE_DEFS.get("cleric_t30_b", {}).get("effects", {}).get("judgement_crit_bonus", 0.0) or 0.0)
                        crit = min(0.45, crit)
                    power = float(CLERIC_JUDGEMENT_POWER)
                    if "cleric_t20_a" in talents:
                        power *= (1.0 + float(TALENT_CHOICE_DEFS.get("cleric_t20_a", {}).get("effects", {}).get("judgement_power_bonus", 0.0) or 0.0))
                    dmg, is_crit = _compute_damage(
                        max(8, int(i * CLERIC_JUDGEMENT_INT_SCALE * spell_bonus)),
                        _enemy_resist_for_spell_hit(e),
                        power,
                        rng,
                        _acrit(crit),
                    )
                    fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                    _ally_post_damage_specials(e, fd)
                    logs.append(f"{name} 施放惩戒术（MP-{judgement_cost}），对 {e.get('name','敌人')} 造成 {fd}{'（暴击）' if is_crit else ''}。")
                    _sk_j2 = _skill_catalog().get("judgement")
                    _dq_append_ally_skill_video(battle, role, _sk_j2.name if _sk_j2 else "惩戒术")
                else:
                    # MP 不足以施放惩戒术：自动降级为魔杖普攻
                    if rng.random() > ally_hit_rate:
                        logs.append(f"{name} MP不足，魔杖攻击未命中。")
                        _dq_append_ally_attack_video(battle, role)
                        continue
                    crit = min(0.12, 0.02 + l * 0.0012)
                    dmg, is_crit = _compute_damage(max(1, int((2 + s * 0.9) * atk_bonus)), int(e.get("def", 0) or 0), 0.95, rng, _acrit(crit))
                    fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                    _ally_post_damage_specials(e, fd)
                    logs.append(f"{name} MP不足，挥动魔杖攻击 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}。")
                    _dq_append_ally_attack_video(battle, role)
            else:
                # 未学惩戒术：改为低伤害魔杖普攻（按 STR 结算）
                if rng.random() > ally_hit_rate:
                    logs.append(f"{name} 的魔杖攻击未命中。")
                    _dq_append_ally_attack_video(battle, role)
                    continue
                crit = min(0.12, 0.02 + l * 0.0012)
                dmg, is_crit = _compute_damage(max(1, int((2 + s * 0.9) * atk_bonus)), int(e.get("def", 0) or 0), 0.95, rng, _acrit(crit))
                fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                _ally_post_damage_specials(e, fd)
                logs.append(f"{name} 挥动魔杖攻击 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}。")
                _dq_append_ally_attack_video(battle, role)
            continue

        if role == "mage":
            spell_power_mult = 1.0
            mage_mp = int(a.get("mp", 0) or 0)
            mage_max_mp = int(a.get("max_mp", 0) or 0) or 1
            mp_ratio = max(0.0, min(1.0, float(mage_mp) / float(mage_max_mp)))
            if "mage_t20_a" in talents:
                spell_power_mult += float(TALENT_CHOICE_DEFS.get("mage_t20_a", {}).get("effects", {}).get("spell_power_bonus", 0.0) or 0.0)
            meteor_chance = 0.20
            meteor_power_mult = 1.0
            if "mage_t30_a" in talents:
                meteor_power_mult += float(TALENT_CHOICE_DEFS.get("mage_t30_a", {}).get("effects", {}).get("meteor_power_bonus", 0.0) or 0.0)
            fire_power_mult = 1.0
            if "mage_t10_a" in talents:
                fire_power_mult += float(TALENT_CHOICE_DEFS.get("mage_t10_a", {}).get("effects", {}).get("fire_power_bonus", 0.0) or 0.0)
            chain_chance = 0.35
            chain_lightning_dmg_mult = 1.0
            chain_lightning_extra_hits = 0
            if "mage_t20_b" in talents:
                _t20b = (TALENT_CHOICE_DEFS.get("mage_t20_b", {}) or {}).get("effects") or {}
                chain_lightning_dmg_mult = float(_t20b.get("chain_lightning_damage_mult", 1.0) or 1.0)
                chain_lightning_extra_hits = int(_t20b.get("chain_lightning_extra_hits", 0) or 0)
            e = _random_enemy()
            if not e:
                break
            crit = min(0.33, 0.04 + g * 0.0018)
            p = 1.22
            skn = "奥术冲击"
            cost = 0
            use_spell = False
            # 增加随机性：在「可用的法术集合」里按权重随机选一个
            # - 高 MP 下也会偶尔选低消耗法术，避免“只有没蓝才放下一层”的单调行为
            # - 但会再根据“蓝量占比”做偏置：满蓝时更偏向高阶，不至于过于平均
            high_bias = 0.85 + 0.65 * mp_ratio      # 高阶在满蓝时权重上浮
            mid_bias = 0.90 + 0.40 * mp_ratio       # 中阶略上浮
            fire_bias = max(0.45, 0.95 - 0.30 * mp_ratio)   # 爆炎在满蓝时略降权
            arcane_bias = max(0.35, 0.90 - 0.35 * mp_ratio) # 奥术冲击在满蓝时显著降权
            cands: List[Tuple[float, str, int, float]] = []  # (weight, skn, cost, p_base)
            if "meteor" in skills and mage_mp >= MAGE_MP_METEOR:
                # meteor_chance 同时作为“权重倾向”
                cands.append((float(meteor_chance) * high_bias, "陨星术", MAGE_MP_METEOR, 1.75 * meteor_power_mult))
            if "chain_lightning" in skills and mage_mp >= MAGE_MP_CHAIN_LIGHTNING:
                cands.append((float(chain_chance) * mid_bias, "连锁闪电", MAGE_MP_CHAIN_LIGHTNING, 1.45))
            if "fire_blast" in skills and mage_mp >= MAGE_MP_FIRE_BLAST:
                # fire_blast 不再完全确定：加入权重，让 arcane 也有机会被选到
                fire_w = 0.70 * min(1.3, mage_mp / float(MAGE_MP_FIRE_BLAST))
                cands.append((fire_w * fire_bias, "爆炎术", MAGE_MP_FIRE_BLAST, MAGE_FIRE_BLAST_BASE_POWER * fire_power_mult))
            if "arcane_bolt" in skills and mage_mp >= MAGE_MP_ARCANE_BOLT:
                arcane_w = 0.45 * min(1.3, mage_mp / float(MAGE_MP_ARCANE_BOLT))
                cands.append((arcane_w * arcane_bias, "奥术冲击", MAGE_MP_ARCANE_BOLT, 1.22))

            if cands:
                total_w = sum(w for (w, _, _, _) in cands if w > 0)
                if total_w > 0:
                    r = rng.random() * total_w
                    for w, _skn, _cost, _p_base in cands:
                        if w <= 0:
                            continue
                        if r <= w:
                            skn = _skn
                            cost = _cost
                            p = float(_p_base)
                            use_spell = True
                            break
                        r -= w
            if use_spell:
                p *= spell_power_mult
                # 技能释放即消耗：即使命中失败也应扣除 MP
                a["mp"] = max(0, mage_mp - cost)
                _dq_append_ally_skill_video(battle, role, skn)
                if rng.random() > ally_hit_rate:
                    logs.append(f"{name} 释放{skn}（MP-{cost}）但未命中。")
                    continue
                att_v = max(9, int(i * float(MAGE_INT_SPELL_ATK_MULT) * spell_bonus))

                if skn == "陨星术":
                    es_al = _alive_enemies(battle)
                    if not es_al:
                        continue
                    total_dmg, is_crit = _compute_damage(att_v, _enemy_resist_for_spell_hit(es_al[0]), p, rng, _acrit(crit))
                    n = len(es_al)
                    base = total_dmg // n
                    rem = total_dmg % n
                    crit_note = "（暴击）" if is_crit else ""
                    logs.append(
                        f"{name} 释放陨星术（MP-{cost}），星陨总伤 {total_dmg}{crit_note}，由 {n} 名敌人均分。"
                    )
                    for ii, en in enumerate(es_al):
                        if int(en.get("hp", 0) or 0) <= 0:
                            continue
                        portion = base + (1 if ii < rem else 0)
                        if portion <= 0:
                            continue
                        fd = _apply_wither_boss_incoming_damage(en, portion, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                        _ally_post_damage_specials(en, fd)
                        logs.append(f"  → {en.get('name','敌人')} 受到 {fd}。")
                elif skn == "连锁闪电":
                    p_hit = p * MAGE_CHAIN_HIT_POWER_FRAC * chain_lightning_dmg_mult
                    tgt0 = e
                    if int(tgt0.get("hp", 0) or 0) <= 0:
                        es0 = _alive_enemies(battle)
                        if not es0:
                            continue
                        tgt0 = rng.choice(es0)
                    dmg1, is_crit1 = _compute_damage(att_v, _enemy_resist_for_spell_hit(tgt0), p_hit, rng, _acrit(crit))
                    fd1 = _apply_wither_boss_incoming_damage(tgt0, dmg1, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                    _ally_post_damage_specials(tgt0, fd1)
                    logs.append(
                        f"{name} 释放连锁闪电（MP-{cost}）主闪命中 {tgt0.get('name','敌人')}，造成 {fd1}{'（暴击）' if is_crit1 else ''}。"
                    )
                    for _ in range(MAGE_CHAIN_EXTRA_HITS + chain_lightning_extra_hits):
                        es_now = _alive_enemies(battle)
                        if not es_now:
                            break
                        tgt = rng.choice(es_now)
                        dmgh, is_crh = _compute_damage(att_v, _enemy_resist_for_spell_hit(tgt), p_hit, rng, _acrit(crit))
                        fdh = _apply_wither_boss_incoming_damage(tgt, dmgh, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                        _ally_post_damage_specials(tgt, fdh)
                        logs.append(
                            f"{name} 连锁闪电弹射命中 {tgt.get('name','敌人')}，造成 {fdh}{'（暴击）' if is_crh else ''}。"
                        )
                elif skn == "爆炎术":
                    dmg, is_crit = _compute_damage(att_v, _enemy_resist_for_spell_hit(e), p, rng, _acrit(crit))
                    fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                    _ally_post_damage_specials(e, fd)
                    logs.append(
                        f"{name} 释放爆炎术（MP-{cost}），对 {e.get('name','敌人')} 造成 {fd}{'（暴击）' if is_crit else ''}。"
                    )
                    _mage_apply_fire_blast_burn(e, rng, logs)
                else:
                    dmg, is_crit = _compute_damage(att_v, _enemy_resist_for_spell_hit(e), p, rng, _acrit(crit))
                    fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                    _ally_post_damage_specials(e, fd)
                    logs.append(
                        f"{name} 释放{skn}（MP-{cost}），对 {e.get('name','敌人')} 造成 {fd}{'（暴击）' if is_crit else ''}。"
                    )
                    if skn == "奥术冲击" and "mage_t10_b" in talents:
                        adc = float(TALENT_CHOICE_DEFS.get("mage_t10_b", {}).get("effects", {}).get("arcane_double_chance", 0.0) or 0.0)
                        if adc > 0 and rng.random() < adc:
                            dmg2, is_crit2 = _compute_damage(att_v, _enemy_resist_for_spell_hit(e), p, rng, _acrit(crit))
                            fd2 = _apply_wither_boss_incoming_damage(e, dmg2, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                            _ally_post_damage_specials(e, fd2)
                            logs.append(
                                f"{name} 灵闪！追加奥术冲击，对 {e.get('name','敌人')} 造成 {fd2}{'（暴击）' if is_crit2 else ''}。"
                            )
            else:
                # 兜底：法杖普通攻击。尽量给出“是否真因 MP 不足”的准确提示。
                mp_reason = (
                    ("arcane_bolt" in skills and mage_mp < MAGE_MP_ARCANE_BOLT)
                    or ("fire_blast" in skills and mage_mp < MAGE_MP_FIRE_BLAST)
                    or ("chain_lightning" in skills and mage_mp < MAGE_MP_CHAIN_LIGHTNING)
                    or ("meteor" in skills and mage_mp < MAGE_MP_METEOR)
                )
                reason_text = "MP不足" if mp_reason else "未释放法术"
                if rng.random() > ally_hit_rate:
                    logs.append(f"{name} {reason_text}，法杖攻击未命中。")
                    _dq_append_ally_attack_video(battle, role)
                    continue
                crit_w = min(0.12, 0.02 + l * 0.0012)
                dmg, is_crit = _compute_damage(max(1, int((2 + s * 0.9) * atk_bonus)), int(e.get("def", 0) or 0), 0.95, rng, _acrit(crit_w))
                fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                _ally_post_damage_specials(e, fd)
                logs.append(f"{name} {reason_text}，挥动法杖攻击 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}。")
                _dq_append_ally_attack_video(battle, role)
            continue

        if role == "hunter":
            crit_bonus_h = float(TALENT_CHOICE_DEFS.get("hunter_t20_a", {}).get("effects", {}).get("crit_bonus", 0.0) or 0.0) if "hunter_t20_a" in talents else 0.0
            aim_shot_power_bonus = (
                float(TALENT_CHOICE_DEFS.get("hunter_t10_a", {}).get("effects", {}).get("aim_shot_power_bonus", 0.0) or 0.0)
                if "hunter_t10_a" in talents
                else 0.0
            )
            pierce_main_bonus = (
                float(TALENT_CHOICE_DEFS.get("hunter_t10_b", {}).get("effects", {}).get("pierce_main_power_bonus", 0.0) or 0.0)
                if "hunter_t10_b" in talents
                else 0.0
            )
            pierce_splash_bonus = (
                float(TALENT_CHOICE_DEFS.get("hunter_t10_b", {}).get("effects", {}).get("pierce_splash_power_bonus", 0.0) or 0.0)
                if "hunter_t10_b" in talents
                else 0.0
            )
            eagle_power_bonus = (
                float(TALENT_CHOICE_DEFS.get("hunter_t30_a", {}).get("effects", {}).get("eagle_eye_power_bonus", 0.0) or 0.0)
                if "hunter_t30_a" in talents
                else 0.0
            )
            eagle_blind_bonus = (
                float(TALENT_CHOICE_DEFS.get("hunter_t30_a", {}).get("effects", {}).get("eagle_eye_blind_chance_bonus", 0.0) or 0.0)
                if "hunter_t30_a" in talents
                else 0.0
            )
            volley_hit_crit_bonus = (
                float(TALENT_CHOICE_DEFS.get("hunter_t30_b", {}).get("effects", {}).get("volley_hit_crit_bonus", 0.0) or 0.0)
                if "hunter_t30_b" in talents
                else 0.0
            )
            mp_now = int(a.get("mp", 0) or 0)
            mp_max = max(1, int(a.get("max_mp", 0) or 1))
            mp_ratio = max(0.0, min(1.0, float(mp_now) / float(mp_max)))
            es_now = _alive_enemies(battle)
            if not es_now:
                break
            enemy_n = len(es_now)

            def _hunter_hp_ratio(x: Dict[str, Any]) -> float:
                return int(x.get("hp", 0) or 0) / max(1.0, float(int(x.get("max_hp", 1) or 1)))

            low_hp_enemy = any(_hunter_hp_ratio(x) <= 0.35 for x in es_now)
            non_boss_on_field = [x for x in es_now if not _enemy_is_boss(x)]
            non_boss_n = len(non_boss_on_field)
            # 连射/鹰眼等会吃一次命中判定；命中率偏低时抬高「瞄准射击」权重
            hit_slip = max(0.0, min(0.22, 0.93 - float(ally_hit_rate)))
            crit = min(0.30, 0.03 + d * 0.0020 + crit_bonus_h)
            # 面板 atk 已由 DEX 主属性+等级在 _recalc_member_stats 中结算，此处不再混用 STR 底盘
            base_att = max(6, int(a.get("atk", 0) or 0))
            p = 1.05
            skill_name = "远程攻击"
            cost = 0
            e = rng.choice(es_now)
            cands_h: List[Tuple[float, str, int, float, str]] = []  # (weight, name, cost, power, target_mode)
            if "eagle_eye" in skills and mp_now >= HUNTER_MP_EAGLE_EYE:
                # 高倍率；致盲对 Boss 无效 → 不优先 Boss；场上有非 Boss 时致盲才有价值
                w_eg = 0.48 + 1.02 * mp_ratio
                if enemy_n <= 1:
                    w_eg += 0.78
                if non_boss_n >= 1:
                    w_eg += 0.48
                    if enemy_n >= 2:
                        w_eg += 0.26
                if non_boss_n == 0:
                    w_eg -= 0.26
                if enemy_n >= 4:
                    w_eg -= 0.32
                if mp_ratio < 0.33:
                    w_eg -= 0.58
                cands_h.append(
                    (
                        max(0.08, w_eg),
                        "鹰眼狙击",
                        HUNTER_MP_EAGLE_EYE,
                        HUNTER_EAGLE_EYE_POWER * (1.0 + eagle_power_bonus),
                        "non_boss_or_random",
                    )
                )
            if "volley" in skills and mp_now >= HUNTER_MP_VOLLEY:
                # 多段物伤：人多时强；一次失手会整段落空，命中不稳时降权
                w_v = 0.40
                if enemy_n >= 2:
                    w_v += 0.92
                if enemy_n >= 3:
                    w_v += 0.58
                if enemy_n == 1:
                    w_v += 0.22
                w_v -= 1.18 * hit_slip
                if mp_ratio < 0.30:
                    w_v -= 0.42
                _vnom = HUNTER_VOLLEY_HIT_POWER * HUNTER_VOLLEY_HITS
                cands_h.append((max(0.08, w_v), "连射", HUNTER_MP_VOLLEY, _vnom, "random"))
            if "pierce_arrow" in skills and mp_now >= HUNTER_MP_PIERCE_ARROW:
                # 主目标+溅射：≥2 敌人时价值高；单体时偏弱
                w_p = 0.36
                if enemy_n >= 2:
                    w_p += 1.08
                if enemy_n >= 3:
                    w_p += 0.28
                if enemy_n == 1:
                    w_p -= 0.52
                if low_hp_enemy:
                    w_p += 0.62
                w_p += 0.38 * (1.0 - mp_ratio) * (1.0 if enemy_n >= 2 else 0.35)
                cands_h.append(
                    (max(0.08, w_p), "穿透箭", HUNTER_MP_PIERCE_ARROW, 1.30 * (1.0 + pierce_main_bonus), "lowest_hp")
                )
            if "aim_shot" in skills and mp_now >= HUNTER_MP_AIM_SHOT:
                # 必中：缺蓝、队友命中差、收割残血时优先
                w_a = 0.46 + 0.72 * hit_slip + 0.58 * (1.0 - mp_ratio)
                if low_hp_enemy:
                    w_a += 0.48
                if enemy_n == 1 and mp_ratio < 0.42:
                    w_a += 0.32
                cands_h.append((max(0.08, w_a), "瞄准射击", HUNTER_MP_AIM_SHOT, 1.24 * (1.0 + aim_shot_power_bonus), "lowest_hp"))
            if cands_h:
                tw = sum(max(0.0, x[0]) for x in cands_h)
                if tw > 0:
                    rr = rng.random() * tw
                    for w, nm, cst, pw, tmode in cands_h:
                        ww = max(0.0, w)
                        if rr <= ww:
                            skill_name, cost, p = nm, cst, pw
                            if tmode == "lowest_hp":
                                e = min(
                                    es_now,
                                    key=lambda x: int(x.get("hp", 0) or 0) / max(1.0, float(int(x.get("max_hp", 1) or 1))),
                                )
                            elif tmode == "non_boss_or_random":
                                nb = [x for x in es_now if not _enemy_is_boss(x)]
                                e = rng.choice(nb) if nb else rng.choice(es_now)
                            break
                        rr -= ww
            if cost > 0:
                a["mp"] = max(0, mp_now - cost)
                _dq_append_ally_skill_video(battle, role, skill_name)
            aim_always_hit = skill_name == "瞄准射击"
            if not aim_always_hit and rng.random() > ally_hit_rate:
                if cost > 0:
                    logs.append(f"{name} 施放{skill_name}（MP-{cost}）但未命中。")
                else:
                    logs.append(f"{name} MP不足，远程攻击未命中。")
                    _dq_append_ally_attack_video(battle, role)
                continue
            volley_per = HUNTER_VOLLEY_HIT_POWER
            crit_volley = min(0.85, crit + volley_hit_crit_bonus)

            if skill_name == "连射":
                cur = e
                for hit_i in range(1, HUNTER_VOLLEY_HITS + 1):
                    es_live = _alive_enemies(battle)
                    if not es_live:
                        break
                    if int(cur.get("hp", 0) or 0) <= 0:
                        cur = rng.choice(es_live)
                    dmg, is_crit = _compute_damage(
                        max(6, int(base_att * atk_bonus)),
                        int(cur.get("def", 0) or 0),
                        volley_per,
                        rng,
                        _acrit(crit_volley, 0.85),
                    )
                    fd = _apply_wither_boss_incoming_damage(cur, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                    _ally_post_damage_specials(cur, fd)
                    logs.append(
                        f"{name} 施放连射（MP-{cost}）第{hit_i}箭命中 {cur.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}。"
                    )
                continue

            if skill_name == "穿透箭":
                dmg, is_crit = _compute_damage(max(6, int(base_att * atk_bonus)), int(e.get("def", 0) or 0), p, rng, _acrit(crit))
                fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                _ally_post_damage_specials(e, fd)
                logs.append(
                    f"{name} 施放穿透箭（MP-{cost}），主箭命中 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}。"
                )
                splash_p = HUNTER_PIERCE_SPLASH_POWER * (1.0 + pierce_splash_bonus)
                es2 = _alive_enemies(battle)
                for st in _hunter_pierce_splash_targets(es2, e, rng):
                    if int(st.get("hp", 0) or 0) <= 0:
                        continue
                    dmgs, is_cs = _compute_damage(
                        max(6, int(base_att * atk_bonus)),
                        int(st.get("def", 0) or 0),
                        splash_p,
                        rng,
                        _acrit(crit),
                    )
                    fds = _apply_wither_boss_incoming_damage(st, dmgs, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                    _ally_post_damage_specials(st, fds)
                    logs.append(
                        f"{name} 穿透箭溅射命中 {st.get('name','敌人')}，造成 {fds}{'（暴击）' if is_cs else ''}。"
                    )
                continue

            dmg, is_crit = _compute_damage(max(6, int(base_att * atk_bonus)), int(e.get("def", 0) or 0), p, rng, _acrit(crit))
            fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
            _ally_post_damage_specials(e, fd)
            extra_blind = ""
            if skill_name == "鹰眼狙击":
                _bp = min(1.0, HUNTER_EAGLE_EYE_BLIND_CHANCE + eagle_blind_bonus)
                if not _enemy_is_boss(e) and rng.random() < _bp:
                    e.setdefault("effects", [])
                    e["effects"] = [x for x in (e.get("effects") or []) if str(x.get("kind")) != "blind"]
                    e["effects"].append({"kind": "blind", "turns": 1})
                    extra_blind = "（致盲！）"
            if cost > 0:
                logs.append(
                    f"{name} 施放{skill_name}（MP-{cost}），命中 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}{extra_blind}"
                )
            else:
                logs.append(f"{name} MP不足，远程攻击命中 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}")
                _dq_append_ally_attack_video(battle, role)
            continue

        # rogue / default
        rogue_assassinate_chance = 0.18
        rogue_assassinate_power_bonus = float(TALENT_CHOICE_DEFS.get("rogue_t30_a", {}).get("effects", {}).get("assassinate_power_bonus", 0.0) or 0.0) if "rogue_t30_a" in talents else 0.0
        rogue_assassinate_execute_bonus = (
            float(TALENT_CHOICE_DEFS.get("rogue_t30_a", {}).get("effects", {}).get("assassinate_execute_chance_bonus", 0.0) or 0.0)
            if "rogue_t30_a" in talents
            else 0.0
        )
        shadow_high_hp_bonus = float(TALENT_CHOICE_DEFS.get("rogue_t10_a", {}).get("effects", {}).get("shadow_high_hp_bonus", 0.0) or 0.0) if "rogue_t10_a" in talents else 0.0
        bleed_turns_bonus = 0
        bleed_pct_flat = 0.0
        if "rogue_t20_a" in talents:
            _be = (TALENT_CHOICE_DEFS.get("rogue_t20_a", {}) or {}).get("effects") or {}
            bleed_turns_bonus = int(_be.get("bleed_turns_bonus", 0) or 0)
            bleed_pct_flat = float(_be.get("bleed_pct_flat", 0.0) or 0.0)
        stab_chain_probs = _quick_stab_chain_probs_for_talents(list(talents) if talents else [])
        mp_now = int(a.get("mp", 0) or 0)
        mp_max = max(1, int(a.get("max_mp", 0) or 1))
        mp_ratio = max(0.0, min(1.0, float(mp_now) / float(mp_max)))
        es_now = _alive_enemies(battle)
        if not es_now:
            break
        e = rng.choice(es_now)
        enemy_n = len(es_now)

        def _ally_enemy_hp_ratio(x: Dict[str, Any]) -> float:
            return int(x.get("hp", 0) or 0) / max(1.0, float(int(x.get("max_hp", 1) or 1)))

        max_hp_ratio_among = max(_ally_enemy_hp_ratio(x) for x in es_now)
        low_hp_enemy = any(_ally_enemy_hp_ratio(x) <= 0.30 for x in es_now)
        crit = min(0.40, 0.05 + g * 0.0022)
        # 面板 atk 已在 _recalc_member_stats 中含 AGI×系数（与 _effective_attrs_party_member 一致）
        base_att = max(6, int(a.get("atk", 0) or 0))
        p = 1.04
        skill_name = "暗袭"
        cost = 0
        cands_r: List[Tuple[float, str, int, float, str]] = []  # (weight, name, cost, power, target_mode)
        if "assassinate" in skills and mp_now >= ROGUE_MP_ASSASSINATE:
            w = (0.40 + rogue_assassinate_chance * 0.90) + (1.05 if low_hp_enemy else 0.0) + 0.25 * mp_ratio
            cands_r.append((w, "暗杀", ROGUE_MP_ASSASSINATE, 1.48 * (1.0 + rogue_assassinate_power_bonus), "lowest_hp"))
        if "shadow_step" in skills and mp_now >= ROGUE_MP_SHADOW_STEP:
            # 影袭对「当前生命>90%」目标有额外倍率：目标应选血线最高者（原 lowest_hp 与技能机制相反）
            w_sh = 0.48
            if max_hp_ratio_among > 0.90:
                w_sh += 1.22
            elif max_hp_ratio_among > 0.75:
                w_sh += 0.42
            elif max_hp_ratio_among < 0.55:
                w_sh -= 0.28
            w_sh += 0.20 * mp_ratio
            if enemy_n <= 2:
                w_sh += 0.22
            if mp_ratio < 0.28:
                w_sh -= 0.48
            cands_r.append((max(0.08, w_sh), "影袭", ROGUE_MP_SHADOW_STEP, 1.22, "highest_hp"))
        if "venom_edge" in skills and mp_now >= ROGUE_MP_VENOM_EDGE:
            w = 0.90 + 0.30 * mp_ratio + (0.25 if enemy_n >= 2 else 0.0)
            cands_r.append((w, "毒刃", ROGUE_MP_VENOM_EDGE, 1.32, "random"))
        if "quick_stab" in skills and mp_now >= ROGUE_MP_QUICK_STAB:
            # 快速刺击：低耗、多段；缺蓝或全场血线已压低时优先于影袭
            w_qs = 0.58 + 0.45 * (1.0 - mp_ratio)
            if max_hp_ratio_among <= 0.90:
                w_qs += 0.38
            if mp_ratio < 0.38:
                w_qs += 0.42
            if enemy_n >= 3:
                w_qs += 0.10
            if max_hp_ratio_among > 0.92 and mp_ratio > 0.45:
                w_qs -= 0.22
            cands_r.append((max(0.08, w_qs), "快速刺击", ROGUE_MP_QUICK_STAB, QUICK_STAB_HIT_POWER, "random"))
        if cands_r:
            tw = sum(max(0.0, x[0]) for x in cands_r)
            if tw > 0:
                rr = rng.random() * tw
                for w, nm, cst, pw, tmode in cands_r:
                    ww = max(0.0, w)
                    if rr <= ww:
                        skill_name, cost, p = nm, cst, pw
                        if tmode == "lowest_hp":
                            e = min(
                                es_now,
                                key=lambda x: int(x.get("hp", 0) or 0) / max(1.0, float(int(x.get("max_hp", 1) or 1))),
                            )
                        elif tmode == "highest_hp":
                            e = max(es_now, key=_ally_enemy_hp_ratio)
                        break
                    rr -= ww
        if cost > 0:
            a["mp"] = max(0, mp_now - cost)
        if skill_name == "快速刺击":
            _dq_append_ally_skill_video(battle, role, "快速刺击")
        elif cost > 0:
            _dq_append_ally_skill_video(battle, role, skill_name)
        else:
            _dq_append_ally_attack_video(battle, role)
        if skill_name == "快速刺击":
            for hit_i in range(1, 5):
                if hit_i > 1:
                    if rng.random() >= stab_chain_probs[hit_i - 2]:
                        break
                if int(e.get("hp", 0) or 0) <= 0:
                    break
                if hit_i == 1 and rng.random() > ally_hit_rate:
                    logs.append(f"{name} 施放{skill_name}（MP-{cost}）但未命中。")
                    break
                dmg, is_crit = _compute_damage(
                    max(6, int(base_att * atk_bonus)),
                    int(e.get("def", 0) or 0),
                    QUICK_STAB_HIT_POWER,
                    rng,
                    _acrit(crit),
                )
                fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
                _ally_post_damage_specials(e, fd)
                logs.append(
                    f"{name} 施放{skill_name}（MP-{cost}）第{hit_i}刀命中 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}。"
                )
            continue
        if rng.random() > ally_hit_rate:
            if cost > 0:
                logs.append(f"{name} 施放{skill_name}（MP-{cost}）但未命中。")
            else:
                logs.append(f"{name} MP不足，暗袭未命中。")
            continue
        mh = max(1, int(e.get("max_hp", 1) or 1))
        hp0 = int(e.get("hp", 0) or 0)
        hp_ratio = hp0 / float(mh)
        # 暗杀：先判定低血必杀（基础 10% + 致命天赋；当前生命<40%、非 Boss）；未触发再按倍率伤害，此后可触发饰品「裁决」
        if skill_name == "暗杀":
            _kill_p = 0.10 + rogue_assassinate_execute_bonus
            if not _enemy_is_boss(e) and hp_ratio < 0.40 and rng.random() < _kill_p:
                e["hp"] = 0
                logs.append(f"{name} 施放暗杀（MP-{cost}）触发必杀，{e.get('name','敌人')} 被当场击倒！")
                continue
            p_skill = 1.48 * (1.0 + rogue_assassinate_power_bonus)
        elif skill_name == "影袭":
            p_skill = 1.22 + (0.1 if hp_ratio > 0.9 else 0.0) + (shadow_high_hp_bonus if hp_ratio > 0.9 else 0.0)
        elif skill_name == "毒刃":
            p_skill = 1.32
        else:
            p_skill = p
        dmg, is_crit = _compute_damage(max(6, int(base_att * atk_bonus)), int(e.get("def", 0) or 0), p_skill, rng, _acrit(crit))
        fd = _apply_wither_boss_incoming_damage(e, dmg, battle, logs, reflect_from="ally", ally_idx=ally_idx)
        _ally_post_damage_specials(e, fd)
        high_hp_note = "（目标高血量，影袭额外增伤）" if skill_name == "影袭" and hp_ratio > 0.9 else ""
        if cost > 0:
            logs.append(
                f"{name} 施放{skill_name}（MP-{cost}），命中 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}{high_hp_note}。"
            )
        else:
            logs.append(
                f"{name} MP不足，暗袭命中 {e.get('name','敌人')}，造成 {fd}{'（暴击）' if is_crit else ''}{high_hp_note}。"
            )
        if skill_name == "毒刃" and not _enemy_is_boss(e) and rng.random() < 0.5:
            e.setdefault("effects", [])
            e["effects"] = [x for x in (e.get("effects") or []) if str(x.get("kind")) != "bleed"]
            b_turns = 3 + bleed_turns_bonus
            b_pct = 0.10 + bleed_pct_flat
            e["effects"].append({"kind": "bleed", "turns": b_turns, "pct": b_pct})
            logs.append(
                f"🩸 {e.get('name','敌人')} 流血（{b_turns}回合，每回合损失当前生命约{b_pct * 100:.1f}%）！"
            )


def _build_enemy_group(state: Dict[str, Any], lead_enemy: Dict[str, Any], rng: random.Random, zone_id: str, floor: int) -> List[Dict[str, Any]]:
    lead = copy.deepcopy(lead_enemy)
    party_n = _party_size(state)
    # Q1 区域（starter）固定单怪；与主线进度无关
    if zone_id == "starter":
        lead["eid"] = f"e_{rng.randint(1000,9999)}"
        return [lead]
    # 常规地图：多怪上限不超过小队人数（主角+队友），避免敌人数碾压
    # 无限地牢：取消该限制，仅保留最多 5 只
    max_n = 5 if str(zone_id) == "infinite" else min(5, max(1, party_n))
    is_boss = _enemy_is_boss(lead)
    if is_boss:
        total = rng.randint(min(2, max_n), max_n)
    else:
        total = rng.randint(1, max_n)
    group: List[Dict[str, Any]] = []
    lead["eid"] = f"e_{rng.randint(1000,9999)}"
    lead["is_boss"] = is_boss
    scale_party = 1.0 + max(0, party_n - 1) * (0.10 if is_boss else 0.07)
    lead["max_hp"] = max(1, int(lead.get("max_hp", lead.get("hp", 1)) * scale_party))
    lead["hp"] = int(lead["max_hp"])
    lead["atk"] = max(1, int(lead.get("atk", 1) * (1.0 + max(0, party_n - 1) * 0.05)))
    lead["def"] = max(1, int(lead.get("def", 1) * (1.0 + max(0, party_n - 1) * 0.04)))
    lead["agi"] = max(1, int(lead.get("agi", 1) * (1.0 + max(0, party_n - 1) * 0.03)))
    group.append(lead)

    if total <= 1:
        return group
    monsters = _zone_catalog().get(zone_id, _zone_catalog()["starter"]).get("monsters", []) or ["slime", "rat", "goblin"]
    for _ in range(total - 1):
        m = rng.choice(monsters)
        hero_lv = int(state.get("level", 1) or 1)
        zone_lv = int(floor) if str(zone_id) == "infinite" else _roll_zone_enemy_level(zone_id, hero_lv, rng, is_boss=False)
        e = _enemy_stats(m, hero_lv, rng, scale=1.0 + max(0, floor - 1) * 0.05, enemy_level=zone_lv)
        e["eid"] = f"e_{rng.randint(1000,9999)}"
        e["is_boss"] = False
        # 小怪随队伍人数略强化，避免多人太轻松
        e["max_hp"] = max(1, int(e["max_hp"] * (1.0 + max(0, party_n - 1) * 0.06)))
        e["hp"] = int(e["max_hp"])
        e["atk"] = max(1, int(e["atk"] * (1.0 + max(0, party_n - 1) * 0.04)))
        e["def"] = max(1, int(e["def"] * (1.0 + max(0, party_n - 1) * 0.03)))
        group.append(e)
    return group


def dq_start_battle(state: Dict[str, Any], enemy: Dict[str, Any], rng: Optional[random.Random] = None) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    _ensure_meta_logs(state)
    # 新战斗清空前端用的「上次动作」；否则上局逃跑等会残留在存档 meta，下局提交时可能被误用于恢复 UI
    state.setdefault("meta", {}).pop("battle_ui_last_action", None)
    state.setdefault("meta", {}).pop("dq_last_battle_outcome", None)
    zone_id = str(state.get("location", "starter"))
    floor = max(1, int((state.get("dungeon") or {}).get("floor", 1) or 1))
    rng_local = rng or random.Random(int(state.get("seed", 1)) + int(state.get("meta", {}).get("turn", 0)) * 131)
    preset = (enemy or {}).get("_preset_enemies")
    if isinstance(preset, list) and len(preset) > 0:
        enemies = []
        for e0 in preset:
            ee = copy.deepcopy(e0)
            if not ee.get("eid"):
                ee["eid"] = f"e_{rng_local.randint(1000,9999)}"
            ee["is_boss"] = _enemy_is_boss(ee)
            enemies.append(ee)
    elif bool((enemy or {}).get("_locked_group", False)):
        e0 = copy.deepcopy(enemy)
        e0.pop("_locked_group", None)
        if not e0.get("eid"):
            e0["eid"] = f"e_{rng_local.randint(1000,9999)}"
        e0["is_boss"] = _enemy_is_boss(e0)
        enemies = [e0]
    else:
        enemies = _build_enemy_group(state, enemy, rng_local, zone_id, floor)

    if zone_id == "coast":
        ca = float(COAST_ENEMY_ATK_MULT)
        cd = float(COAST_ENEMY_DEF_MULT)
        for e in enemies:
            e["atk"] = max(1, int(int(e.get("atk", 1) or 1) * ca))
            e["def"] = max(1, int(int(e.get("def", 1) or 1) * cd))
    if zone_id == "throne":
        ta = float(THRONE_ENEMY_ATK_MULT)
        td = float(THRONE_ENEMY_DEF_MULT)
        for e in enemies:
            e["atk"] = max(1, int(int(e.get("atk", 1) or 1) * ta))
            e["def"] = max(1, int(int(e.get("def", 1) or 1) * td))

    # 剧情失败惩罚：主线Boss可能被强化/开场蓄力
    curse = (state.get("meta") or {}).get("boss_curse") or {}
    boost = curse.get("boost") or {}
    special = curse.get("special") or {}
    boss_idx = next((i for i, e in enumerate(enemies) if _enemy_is_boss(e)), None)
    open_charge = False
    if boss_idx is not None and int(boost.get("charges", 0) or 0) > 0:
        b = enemies[boss_idx]
        b["max_hp"] = max(1, int(b["max_hp"] * max(1.0, float(boost.get("hp_mult", 1.0) or 1.0))))
        b["hp"] = int(b["max_hp"])
        b["atk"] = max(1, int(b["atk"] * max(1.0, float(boost.get("atk_mult", 1.0) or 1.0))))
        b["def"] = max(1, int(b["def"] * max(1.0, float(boost.get("def_mult", 1.0) or 1.0))))
        b["agi"] = max(1, int(b["agi"] * max(1.0, float(boost.get("agi_mult", 1.0) or 1.0))))
        state["meta"]["log"].append("⚠️ 惩罚生效：本次主线Boss被黑潮强化。")
        boost["charges"] = max(0, int(boost.get("charges", 0) or 0) - 1)
        if boost["charges"] <= 0:
            curse.pop("boost", None)
        else:
            curse["boost"] = boost
    if boss_idx is not None and int(special.get("charges", 0) or 0) > 0 and bool(special.get("open_charge", False)):
        open_charge = True
        state["meta"]["log"].append("⚠️ 惩罚生效：Boss 开场蓄力。")
        special["charges"] = max(0, int(special.get("charges", 0) or 0) - 1)
        if special["charges"] <= 0:
            curse.pop("special", None)
        else:
            curse["special"] = special
    state.setdefault("meta", {})["boss_curse"] = curse

    allies: List[Dict[str, Any]] = []
    for m in state.get("party_members", []) or []:
        mm = copy.deepcopy(m)
        _recalc_member_stats(mm, int(state.get("level", mm.get("level", 1)) or 1), state.get("party_armory"), state.get("resources"))
        mm["aid"] = str(mm.get("mid", f"ally_{len(allies)}"))
        # 进入战斗应继承队友当前 HP/MP，而不是强制回满
        hp_now = int(m.get("hp", mm.get("max_hp", 1)) or 0)
        mp_now = int(m.get("mp", mm.get("max_mp", 0)) or 0)
        mm["hp"] = max(0, min(int(mm.get("max_hp", 1) or 1), hp_now))
        mm["mp"] = max(0, min(int(mm.get("max_mp", 0) or 0), mp_now))
        allies.append(mm)

    state["phase"] = "battle"
    state["encounter"] = {"enemy": enemies[0], "enemies": enemies}
    state["battle"] = {
        "enemy": enemies[0],
        "enemies": enemies,
        "allies": allies,
        "player_hp": state["hp"],
        "player_max_hp": state["max_hp"],
        "player_mp": state["mp"],
        "player_max_mp": state["max_mp"],
        "player_atk": state["atk"],
        "player_def": _incoming_def_effective_for_unit(str(state.get("role", "warrior")), int(state.get("def", 1) or 1)),
        "player_mdef": _incoming_mdef_effective_for_unit(str(state.get("role", "warrior")), int(state.get("mdef", 1) or 1)),
        "turn": 1,
        "result": None,
        "next_enemy_damage_mult": 1.0,
        "cover_party_turns": 0,
        "open_charge_boss": open_charge,
        "skill_cd": {"execution": 0, "armor_break": 0},
        "defend_cd": 0,
        "taunt_pending_next_enemy": False,
        "taunt_active_this_enemy_phase": False,
        "shield_counter_active": False,
        "war_cry_turns": 0,
        "player_damage_taken_this_turn": 0,
    }
    state["defend_turn"] = False
    state.setdefault("status_effects", [])
    bl0 = [f"— 战斗开始（敌人数：{len(enemies)}，队伍人数：{_party_size(state)}） —"]
    if any(str(e.get("mid")) == "boss_witherling" for e in enemies if isinstance(e, dict)):
        bl0.append("🌿 枯萎光环：枯萎之王在场时，对其造成的直接伤害降低10%。")
    state["meta"]["battle_log"] = bl0
    return state


def _battle_enemy_move(state: Dict[str, Any], enemy: Dict[str, Any], rng: random.Random, logs: List[str]) -> Dict[str, Any]:
    battle = state["battle"]
    if int(enemy.get("hp", 0) or 0) <= 0:
        return {"type": "none"}
    target = _pick_enemy_target(state, battle, enemy, rng)
    if target.get("kind") == "none":
        return {"type": "none"}
    enemy_mp = int(enemy.get("mp", 0) or 0)
    lv_tag = f"Lv{enemy.get('level', '?')}"
    if _enemy_blind_consume_and_maybe_whiff(enemy, rng, logs):
        return {"type": "miss"}

    if bool(enemy.get("enemy_power_strike_pending", False)):
        enemy["enemy_power_strike_pending"] = False
        style = rng.choice(["蓄力重击", "蓄力爆发"])
        power = 1.28 if style == "蓄力重击" else 1.42
        # defense/evasion by target（Q4 海妖系蓄力按魔法承伤）
        if target["kind"] == "player":
            tdef = _enemy_sea_magic_attack_resist(enemy, battle, target)
            if rng.random() < _player_evasion_chance(state):
                logs.append(f"{enemy['name']}（{lv_tag}）的蓄力一击被你闪开了！")
                _try_warrior_dodge_heal(state, battle, logs)
                return {"type": "miss"}
        else:
            ally = battle["allies"][int(target["idx"])]
            tdef = _enemy_sea_magic_attack_resist(enemy, battle, target)
            if rng.random() < _ally_evasion(ally, state):
                logs.append(f"{enemy['name']}（{lv_tag}）对 {ally.get('name','队友')} 的蓄力一击落空！")
                return {"type": "miss"}
        crit_rate = min(0.12, 0.04 + int(enemy.get("agi", 1)) / 600.0)
        dmg, is_crit = _compute_damage(int(enemy.get("atk", 1)), tdef, power, rng, crit_rate)
        dmg = int(dmg * ENEMY_CHARGE_MULT)
        if target["kind"] == "player":
            dmg = _apply_defend_mult_to_damage(battle, dmg)
        _apply_enemy_hit_target(state, enemy, dmg, target, logs)
        _guard_info = battle.pop("_last_guard_applied", None)
        shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
        tname = "你" if target["kind"] == "player" else battle["allies"][int(target["idx"])].get("name", "队友")
        logs.append(f"{enemy['name']}（{lv_tag}）【{style}】命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}")
        return {"type": "charged_attack", "dmg": dmg}

    # 枯萎之王：低概率【枯萎凋零】群攻 / 【枯萎反噬】反射预备（优先于蓄力掷骰）
    if str(enemy.get("mid")) == "boss_witherling":
        em_w = int(enemy.get("mp", 0) or 0)
        if em_w >= WITHER_BOSS_AOE_MP_COST and rng.random() < WITHER_BOSS_SPECIAL_SKILL_CHANCE:
            enemy["mp"] = em_w - WITHER_BOSS_AOE_MP_COST
            _wither_boss_aoe_attack(state, battle, enemy, rng, logs)
            return {"type": "wither_aoe", "dmg": 0}
        em_w = int(enemy.get("mp", 0) or 0)
        if em_w >= WITHER_BOSS_REFLECT_MP_COST and rng.random() < WITHER_BOSS_SPECIAL_SKILL_CHANCE:
            enemy["mp"] = em_w - WITHER_BOSS_REFLECT_MP_COST
            enemy["wither_reflect_next"] = True
            logs.append(
                f"{enemy['name']}（{lv_tag}）展开【枯萎反噬】：下一次对其造成的直接伤害将被部分反弹！"
            )
            return {"type": "wither_reflect", "dmg": 0}

    mid = str(enemy.get("mid", ""))
    # Q3 Boss（熔岩巨像）：2 主动 + 1 被动（命中时更易附加灼烧）
    if mid == "boss_golem":
        rb = rng.random()
        if rb < GOLEM_SKILL1_CHANCE:
            # 主动1：熔核震地（全体）- 每名目标第1次 GOLEM_QUAKE_BASE_DMG 点，之后每次对该目标伤害×2
            logs.append(f"{enemy['name']}（{lv_tag}）释放【熔核震地】！")
            battle.setdefault("golem_quake_stacks", {"player": 0, "allies": {}})
            gq = battle.get("golem_quake_stacks") or {"player": 0, "allies": {}}
            ally_stack_map = gq.get("allies") if isinstance(gq.get("allies"), dict) else {}
            targets = [{"kind": "player"}]
            for i, al in enumerate(battle.get("allies", []) or []):
                if int(al.get("hp", 0) or 0) > 0:
                    targets.append({"kind": "ally", "idx": i, "aid": al.get("aid")})
            for t in targets:
                if t["kind"] == "player":
                    if rng.random() < _player_evasion_chance(state):
                        logs.append("你躲开了熔核震地。")
                        _try_warrior_dodge_heal(state, battle, logs)
                        continue
                    old_stack = int(gq.get("player", 0) or 0)
                    dmg = max(1, GOLEM_QUAKE_BASE_DMG * (2**old_stack))
                    dmg = _shield_counter_pre_player_incoming(battle, dmg)
                    battle["player_hp"] = max(0, int(battle.get("player_hp", 0) or 0) - dmg)
                    _battle_track_player_damage_taken_this_turn(battle, dmg)
                    _shield_counter_reflect_after_player_hit(battle, enemy, dmg, logs)
                    gq["player"] = old_stack + 1
                    logs.append(f"熔核震地命中你，造成 {dmg} 点伤害（震地叠层：{gq['player']}）。")
                else:
                    alx = battle["allies"][int(t["idx"])]
                    if rng.random() < _ally_evasion(alx, state):
                        logs.append(f"{alx.get('name','队友')} 躲开了熔核震地。")
                        continue
                    aid = str(alx.get("aid") or alx.get("mid") or f"idx_{int(t['idx'])}")
                    old_stack = int(ally_stack_map.get(aid, 0) or 0)
                    dmg = max(1, GOLEM_QUAKE_BASE_DMG * (2**old_stack))
                    alx["hp"] = max(0, int(alx.get("hp", 0) or 0) - dmg)
                    ally_stack_map[aid] = old_stack + 1
                    logs.append(
                        f"熔核震地命中{alx.get('name','队友')}，造成 {dmg} 点伤害（震地叠层：{ally_stack_map[aid]}）。"
                    )
            gq["allies"] = ally_stack_map
            battle["golem_quake_stacks"] = gq
            return {"type": "golem_quake"}
        if rb < GOLEM_SKILL1_CHANCE + GOLEM_SKILL2_CHANCE:
            # 主动2：岩锥穿刺（单体）= 0.95系数伤害 + 固定20%最大生命附伤
            if target["kind"] == "player":
                tdef = int(battle.get("player_def", 1))
                if rng.random() < _player_evasion_chance(state):
                    logs.append(f"{enemy['name']}（{lv_tag}）【岩锥穿刺】被你闪开了！")
                    _try_warrior_dodge_heal(state, battle, logs)
                    return {"type": "miss"}
            else:
                ally = battle["allies"][int(target["idx"])]
                tdef = _incoming_def_effective_for_unit(str(ally.get("role", "")), ally.get("def", 1))
                if rng.random() < _ally_evasion(ally, state):
                    logs.append(f"{enemy['name']}（{lv_tag}）【岩锥穿刺】被 {ally.get('name','队友')} 躲开！")
                    return {"type": "miss"}
            crit_rate = min(0.16, 0.05 + int(enemy.get("agi", 1)) / 620.0)
            dmg, is_crit = _compute_damage(int(enemy.get("atk", 1)), tdef, GOLEM_SKILL2_POWER, rng, crit_rate)
            if target["kind"] == "player":
                dmg = _apply_defend_mult_to_damage(battle, dmg)
            _apply_enemy_hit_target(state, enemy, dmg, target, logs)
            _guard_info = battle.pop("_last_guard_applied", None)
            shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
            fixed = 0
            if target["kind"] == "player":
                fixed = max(1, int(int(battle.get("player_max_hp", 1) or 1) * 0.20))
                fixed = _shield_counter_pre_player_incoming(battle, fixed)
                battle["player_hp"] = max(0, int(battle.get("player_hp", 0) or 0) - fixed)
                _battle_track_player_damage_taken_this_turn(battle, fixed)
                _shield_counter_reflect_after_player_hit(battle, enemy, fixed, logs)
            else:
                ally_t = battle["allies"][int(target["idx"])]
                fixed = max(1, int(int(ally_t.get("max_hp", 1) or 1) * 0.20))
                ally_t["hp"] = max(0, int(ally_t.get("hp", 0) or 0) - fixed)
            tname = "你" if target["kind"] == "player" else battle["allies"][int(target["idx"])].get("name", "队友")
            logs.append(
                f"{enemy['name']}（{lv_tag}）【岩锥穿刺】命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''} + 固定{fixed}（最大生命20%）伤害。"
            )
            return {"type": "golem_spike", "dmg": dmg + fixed}

    # Q4 Boss（潮汐女巫）：2 主动 + 1 被动（每回合小幅回蓝回生）
    if mid == "boss_sea_witch":
        hp_reg = max(0, int(int(enemy.get("max_hp", 1) or 1) * 0.02))
        mp_reg = max(0, int(int(enemy.get("max_mp", 0) or 0) * 0.06))
        if hp_reg > 0:
            enemy["hp"] = min(int(enemy.get("max_hp", 1) or 1), int(enemy.get("hp", 0) or 0) + hp_reg)
        if mp_reg > 0:
            enemy["mp"] = min(int(enemy.get("max_mp", 0) or 0), int(enemy.get("mp", 0) or 0) + mp_reg)
        if hp_reg > 0 or mp_reg > 0:
            logs.append(f"{enemy['name']}（{lv_tag}）【潮汐同调】恢复 HP+{hp_reg} / MP+{mp_reg}。")
        rb = rng.random()
        if enemy_mp >= 10 and rb < SEA_WITCH_SKILL1_CHANCE:
            # 主动1：潮汐乱流（全体）+ 全员当前蓝量流失10%
            enemy["mp"] = max(0, enemy_mp - 10)
            crit_rate = min(0.16, 0.05 + int(enemy.get("agi", 1)) / 650.0)
            logs.append(f"{enemy['name']}（{lv_tag}）释放【潮汐乱流】！")
            targets = [{"kind": "player"}]
            for i, al in enumerate(battle.get("allies", []) or []):
                if int(al.get("hp", 0) or 0) > 0:
                    targets.append({"kind": "ally", "idx": i, "aid": al.get("aid")})
            for t in targets:
                if t["kind"] == "player":
                    tdef = _battle_player_incoming_resist(battle, magical=True)
                    if rng.random() < _player_evasion_chance(state):
                        logs.append("你躲开了潮汐乱流。")
                        _try_warrior_dodge_heal(state, battle, logs)
                        continue
                else:
                    alx = battle["allies"][int(t["idx"])]
                    tdef = _battle_ally_incoming_resist(alx, magical=True)
                    if rng.random() < _ally_evasion(alx, state):
                        logs.append(f"{alx.get('name','队友')} 躲开了潮汐乱流。")
                        continue
                dmg, is_crit = _compute_damage(int(enemy.get("atk", 1)), tdef, SEA_WITCH_SKILL1_POWER, rng, crit_rate)
                if t["kind"] == "player":
                    dmg = _apply_defend_mult_to_damage(battle, dmg)
                _apply_enemy_hit_target(state, enemy, dmg, t, logs)
                _guard_info = battle.pop("_last_guard_applied", None)
                shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
                tname = "你" if t["kind"] == "player" else battle["allies"][int(t["idx"])].get("name", "队友")
                logs.append(f"潮汐乱流命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}。")
            player_mp_now = int(battle.get("player_mp", 0) or 0)
            player_mp_loss = max(0, int(int(battle.get("player_max_mp", 0) or 0) * 0.10))
            if player_mp_loss > 0:
                battle["player_mp"] = max(0, player_mp_now - player_mp_loss)
            logs.append(f"潮汐乱流卷走你的法力，MP -{player_mp_loss}。")
            for al in battle.get("allies", []) or []:
                if int(al.get("hp", 0) or 0) <= 0:
                    continue
                amp_now = int(al.get("mp", 0) or 0)
                amp_loss = max(0, int(int(al.get("max_mp", 0) or 0) * 0.10))
                if amp_loss > 0:
                    al["mp"] = max(0, amp_now - amp_loss)
                logs.append(f"{al.get('name','队友')} 的MP流失 {amp_loss}。")
            return {"type": "sea_tide"}
        if enemy_mp >= 14 and rb < SEA_WITCH_SKILL1_CHANCE + SEA_WITCH_SKILL2_CHANCE:
            # 主动2：溺潮咒缚（单体重伤+中毒）
            if target["kind"] == "player":
                tdef = _battle_player_incoming_resist(battle, magical=True)
                if rng.random() < _player_evasion_chance(state):
                    logs.append(f"{enemy['name']}（{lv_tag}）【溺潮咒缚】被你闪开了！")
                    _try_warrior_dodge_heal(state, battle, logs)
                    return {"type": "miss"}
            else:
                ally = battle["allies"][int(target["idx"])]
                tdef = _battle_ally_incoming_resist(ally, magical=True)
                if rng.random() < _ally_evasion(ally, state):
                    logs.append(f"{enemy['name']}（{lv_tag}）【溺潮咒缚】被 {ally.get('name','队友')} 躲开！")
                    return {"type": "miss"}
            enemy["mp"] = max(0, enemy_mp - 14)
            crit_rate = min(0.18, 0.06 + int(enemy.get("agi", 1)) / 620.0)
            dmg, is_crit = _compute_damage(int(enemy.get("atk", 1)), tdef, SEA_WITCH_SKILL2_POWER, rng, crit_rate)
            if target["kind"] == "player":
                dmg = _apply_defend_mult_to_damage(battle, dmg)
            _apply_enemy_hit_target(state, enemy, dmg, target, logs)
            _guard_info = battle.pop("_last_guard_applied", None)
            shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
            tname = "你" if target["kind"] == "player" else battle["allies"][int(target["idx"])].get("name", "队友")
            logs.append(f"{enemy['name']}（{lv_tag}）【溺潮咒缚】命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}。")
            if target["kind"] == "player":
                state["status_effects"] = [e for e in state.get("status_effects", []) if e.get("kind") != "poison"]
                state["status_effects"].append({"kind": "poison", "turns": 3, "dmg": max(2, int(dmg * 0.24))})
                logs.append("状态：中毒（持续3回合）")
            return {"type": "sea_bind", "dmg": dmg}

    # Q5 Boss（王座守卫）：2 主动 + 1 被动（常驻威压）；血量<20%进入狂暴（一次）
    if mid == "boss_throne_guard":
        def _throne_try_summon_guard() -> None:
            enemies_now = battle.get("enemies") or []
            if len(enemies_now) >= 5:
                logs.append("王座守卫试图召唤援军，但战场已满。")
                return
            hero_lv = max(1, int(state.get("level", 1) or 1))
            guard = _enemy_stats("throne_guard", hero_lv, rng, scale=1.0, enemy_level=30)
            guard["eid"] = f"e_{rng.randint(1000,9999)}"
            guard["is_boss"] = False
            if str(state.get("location", "")) == "throne":
                guard["atk"] = max(1, int(int(guard.get("atk", 1) or 1) * float(THRONE_ENEMY_ATK_MULT)))
                guard["def"] = max(1, int(int(guard.get("def", 1) or 1) * float(THRONE_ENEMY_DEF_MULT)))
            enemies_now.append(guard)
            battle["enemies"] = enemies_now
            _sync_primary_enemy(battle)
            if isinstance(state.get("encounter"), dict):
                state["encounter"]["enemies"] = enemies_now
                state["encounter"]["enemy"] = battle.get("enemy")
            logs.append(f"{enemy['name']}（{lv_tag}）召唤了【王座卫兵】（Lv30）加入战斗！")

        if not bool(enemy.get("throne_enraged", False)):
            hp_now = int(enemy.get("hp", 0) or 0)
            hp_max = max(1, int(enemy.get("max_hp", 1) or 1))
            if hp_now <= int(hp_max * 0.20):
                enemy["throne_enraged"] = True
                enemy["atk"] = max(1, int(int(enemy.get("atk", 1) or 1) * 1.10))
                enemy["def"] = max(1, int(int(enemy.get("def", 1) or 1) * 1.07))
                enemy["agi"] = max(1, int(int(enemy.get("agi", 1) or 1) * 1.10))
                logs.append(f"{enemy['name']}（{lv_tag}）进入【狂暴】！攻防敏小幅提升。")
        rb = rng.random()
        if rb < THRONE_SKILL1_CHANCE:
            # 主动1：王座裁决（单体极重）
            if target["kind"] == "player":
                tdef = int(battle.get("player_def", 1))
                if rng.random() < _player_evasion_chance(state):
                    logs.append(f"{enemy['name']}（{lv_tag}）【王座裁决】被你闪开了！")
                    _try_warrior_dodge_heal(state, battle, logs)
                    _throne_try_summon_guard()
                    return {"type": "miss"}
            else:
                ally = battle["allies"][int(target["idx"])]
                tdef = _incoming_def_effective_for_unit(str(ally.get("role", "")), ally.get("def", 1))
                if rng.random() < _ally_evasion(ally, state):
                    logs.append(f"{enemy['name']}（{lv_tag}）【王座裁决】被 {ally.get('name','队友')} 躲开！")
                    _throne_try_summon_guard()
                    return {"type": "miss"}
            crit_rate = min(0.20, 0.06 + int(enemy.get("agi", 1)) / 580.0)
            # 被动：王者威压（常驻小幅增伤）
            dmg, is_crit = _compute_damage(int(enemy.get("atk", 1)), tdef, THRONE_SKILL1_POWER * 1.08, rng, crit_rate)
            if target["kind"] == "player":
                dmg = _apply_defend_mult_to_damage(battle, dmg)
            _apply_enemy_hit_target(state, enemy, dmg, target, logs)
            _guard_info = battle.pop("_last_guard_applied", None)
            shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
            tname = "你" if target["kind"] == "player" else battle["allies"][int(target["idx"])].get("name", "队友")
            logs.append(f"{enemy['name']}（{lv_tag}）【王座裁决】命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}。")
            _throne_try_summon_guard()
            return {"type": "throne_judge", "dmg": dmg}
        if rb < THRONE_SKILL1_CHANCE + THRONE_SKILL2_CHANCE:
            # 主动2：破阵横扫（全体）
            crit_rate = min(0.18, 0.05 + int(enemy.get("agi", 1)) / 620.0)
            logs.append(f"{enemy['name']}（{lv_tag}）释放【破阵横扫】！")
            targets = [{"kind": "player"}]
            for i, al in enumerate(battle.get("allies", []) or []):
                if int(al.get("hp", 0) or 0) > 0:
                    targets.append({"kind": "ally", "idx": i, "aid": al.get("aid")})
            for t in targets:
                if t["kind"] == "player":
                    tdef = int(battle.get("player_def", 1) or 1)
                    hp_now = int(battle.get("player_hp", 0) or 0)
                    hp_max = max(1, int(battle.get("player_max_hp", 1) or 1))
                    # 斩决：不可闪避；但仍走统一受击结算，可被护盾/免疫等机制抵挡
                    if hp_now > 0 and hp_now <= int(hp_max * 0.20) and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
                        exec_dmg = max(1, hp_max * 10)
                        _apply_enemy_hit_target(state, enemy, exec_dmg, t, logs)
                        if int(battle.get("player_hp", 0) or 0) <= 0:
                            logs.append("破阵横扫触发【斩决】！你被瞬间击倒。")
                        else:
                            logs.append("破阵横扫触发【斩决】！但被护盾/免死效果抵挡。")
                        continue
                    if rng.random() < _player_evasion_chance(state):
                        logs.append("你躲开了破阵横扫。")
                        _try_warrior_dodge_heal(state, battle, logs)
                        continue
                else:
                    alx = battle["allies"][int(t["idx"])]
                    tdef = _incoming_def_effective_for_unit(str(alx.get("role", "")), alx.get("def", 1))
                    hp_now = int(alx.get("hp", 0) or 0)
                    hp_max = max(1, int(alx.get("max_hp", 1) or 1))
                    # 斩决：不可闪避；但仍走统一受击结算，可被护盾/免疫等机制抵挡
                    if hp_now > 0 and hp_now <= int(hp_max * 0.20) and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
                        exec_dmg = max(1, hp_max * 10)
                        _apply_enemy_hit_target(state, enemy, exec_dmg, t, logs)
                        if int(alx.get("hp", 0) or 0) <= 0:
                            logs.append(f"破阵横扫触发【斩决】！{alx.get('name','队友')} 被瞬间击倒。")
                        else:
                            logs.append(f"破阵横扫触发【斩决】！但 {alx.get('name','队友')} 被护盾/免死效果保住。")
                        continue
                    if rng.random() < _ally_evasion(alx, state):
                        logs.append(f"{alx.get('name','队友')} 躲开了破阵横扫。")
                        continue
                dmg, is_crit = _compute_damage(int(enemy.get("atk", 1)), tdef, THRONE_SKILL2_POWER * 1.08, rng, crit_rate)
                if t["kind"] == "player":
                    dmg = _apply_defend_mult_to_damage(battle, dmg)
                _apply_enemy_hit_target(state, enemy, dmg, t, logs)
                _guard_info = battle.pop("_last_guard_applied", None)
                shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
                tname = "你" if t["kind"] == "player" else battle["allies"][int(t["idx"])].get("name", "队友")
                logs.append(f"破阵横扫命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}。")
            return {"type": "throne_sweep"}

    # 小怪专属技能（原通用技能改为怪物技；优先于蓄力与普通攻击）
    if mid == "goblin":
        em = int(enemy.get("mp", 0) or 0)
        if em >= GOBLIN_FIREBALL_MP and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
            enemy["mp"] = em - GOBLIN_FIREBALL_MP
            if target["kind"] == "player":
                tdef = _battle_player_incoming_resist(battle, magical=True)
                if rng.random() < _player_evasion_chance(state):
                    logs.append(f"{enemy['name']}（{lv_tag}）的【火球术】被你闪开了！")
                    _try_warrior_dodge_heal(state, battle, logs)
                    return {"type": "miss"}
            else:
                ally = battle["allies"][int(target["idx"])]
                tdef = _battle_ally_incoming_resist(ally, magical=True)
                if rng.random() < _ally_evasion(ally, state):
                    logs.append(f"{enemy['name']}（{lv_tag}）的【火球术】被 {ally.get('name','队友')} 闪开了！")
                    return {"type": "miss"}
            mag = _enemy_spell_attack(enemy)
            crit_rate = min(0.11, 0.035 + int(enemy.get("agi", 1)) / 750.0)
            dmg, is_crit = _compute_damage(mag, tdef, GOBLIN_FIREBALL_POWER, rng, crit_rate)
            if target["kind"] == "player":
                dmg = _apply_defend_mult_to_damage(battle, dmg)
            _apply_enemy_hit_target(state, enemy, dmg, target, logs)
            _guard_info = battle.pop("_last_guard_applied", None)
            shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
            tname = "你" if target["kind"] == "player" else battle["allies"][int(target["idx"])].get("name", "队友")
            logs.append(f"{enemy['name']}（{lv_tag}）【火球术】命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}。")
            return {"type": "goblin_fireball", "dmg": dmg}
    if mid == "sprite":
        em = int(enemy.get("mp", 0) or 0)
        if em >= SPRITE_LIGHTNING_MP and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
            enemy["mp"] = em - SPRITE_LIGHTNING_MP
            if target["kind"] == "player":
                tdef = _battle_player_incoming_resist(battle, magical=True)
                if rng.random() < _player_evasion_chance(state):
                    logs.append(f"{enemy['name']}（{lv_tag}）的【雷电术】被你闪开了！")
                    _try_warrior_dodge_heal(state, battle, logs)
                    return {"type": "miss"}
            else:
                ally = battle["allies"][int(target["idx"])]
                tdef = _battle_ally_incoming_resist(ally, magical=True)
                if rng.random() < _ally_evasion(ally, state):
                    logs.append(f"{enemy['name']}（{lv_tag}）的【雷电术】被 {ally.get('name','队友')} 闪开了！")
                    return {"type": "miss"}
            mag = _enemy_spell_attack(enemy)
            crit_rate = min(0.12, 0.038 + int(enemy.get("agi", 1)) / 720.0)
            dmg, is_crit = _compute_damage(mag, tdef, SPRITE_LIGHTNING_POWER, rng, crit_rate)
            if target["kind"] == "player":
                dmg = _apply_defend_mult_to_damage(battle, dmg)
            _apply_enemy_hit_target(state, enemy, dmg, target, logs)
            _guard_info = battle.pop("_last_guard_applied", None)
            shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
            tname = "你" if target["kind"] == "player" else battle["allies"][int(target["idx"])].get("name", "队友")
            logs.append(f"{enemy['name']}（{lv_tag}）【雷电术】命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}。")
            return {"type": "sprite_lightning", "dmg": dmg}
    if mid == "miner_golem":
        em = int(enemy.get("mp", 0) or 0)
        if em >= MINER_GUARD_MP and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
            enemy["mp"] = em - MINER_GUARD_MP
            enemy["miner_guard_stance_turns"] = 2
            logs.append(f"{enemy['name']}（{lv_tag}）摆出【守护姿态】：短时间内对其造成的直接伤害降低约 30%！")
            return {"type": "miner_guard"}
    if mid == "sea_curse":
        em = int(enemy.get("mp", 0) or 0)
        hp_now = int(enemy.get("hp", 0) or 0)
        hp_max = max(1, int(enemy.get("max_hp", 1) or 1))
        if em >= SEA_CURSE_HEAL_MP and hp_now < int(hp_max * 0.90) and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
            enemy["mp"] = em - SEA_CURSE_HEAL_MP
            heal = max(10, int(hp_max * 0.15 + int(enemy.get("atk", 1)) * 0.52))
            enemy["hp"] = min(hp_max, hp_now + heal)
            logs.append(f"{enemy['name']}（{lv_tag}）【治愈术】恢复生命 +{heal}。")
            return {"type": "sea_curse_heal", "heal": heal}
    if mid == "throne_guard":
        em = int(enemy.get("mp", 0) or 0)
        if em >= THRONE_GUARD_BRAVE_MP and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
            enemy["mp"] = em - THRONE_GUARD_BRAVE_MP
            if target["kind"] == "player":
                tdef = int(battle.get("player_def", 1))
                if rng.random() < _player_evasion_chance(state):
                    logs.append(f"{enemy['name']}（{lv_tag}）的【勇气斩】被你闪开了！")
                    _try_warrior_dodge_heal(state, battle, logs)
                    return {"type": "miss"}
            else:
                ally = battle["allies"][int(target["idx"])]
                tdef = _incoming_def_effective_for_unit(str(ally.get("role", "")), ally.get("def", 1))
                if rng.random() < _ally_evasion(ally, state):
                    logs.append(f"{enemy['name']}（{lv_tag}）的【勇气斩】被 {ally.get('name','队友')} 闪开了！")
                    return {"type": "miss"}
            crit_rate = min(0.14, 0.045 + int(enemy.get("agi", 1)) / 650.0)
            dmg, is_crit = _compute_damage(int(enemy.get("atk", 1)), tdef, THRONE_GUARD_BRAVE_POWER, rng, crit_rate)
            if target["kind"] == "player":
                dmg = _apply_defend_mult_to_damage(battle, dmg)
            _apply_enemy_hit_target(state, enemy, dmg, target, logs)
            _guard_info = battle.pop("_last_guard_applied", None)
            shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
            tname = "你" if target["kind"] == "player" else battle["allies"][int(target["idx"])].get("name", "队友")
            logs.append(f"{enemy['name']}（{lv_tag}）【勇气斩】命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}。")
            return {"type": "throne_guard_brave", "dmg": dmg}

    r2 = rng.random()
    if r2 < MONSTER_SPECIAL_MOVE_CHANCE:
        enemy["enemy_power_strike_pending"] = True
        logs.append(f"{enemy['name']}（{lv_tag}）【蓄力】下回合首次伤害×{ENEMY_CHARGE_MULT}！")
        return {"type": "charge"}

    # normal hit（Q4 海妖系普攻按魔法承伤）
    if target["kind"] == "player":
        tdef = _enemy_sea_magic_attack_resist(enemy, battle, target)
        if rng.random() < _player_evasion_chance(state):
            logs.append(f"{enemy['name']}（{lv_tag}）的攻击被你闪开了！")
            _try_warrior_dodge_heal(state, battle, logs)
            return {"type": "miss"}
    else:
        ally = battle["allies"][int(target["idx"])]
        tdef = _enemy_sea_magic_attack_resist(enemy, battle, target)
        if rng.random() < _ally_evasion(ally, state):
            logs.append(f"{enemy['name']}（{lv_tag}）的攻击被 {ally.get('name','队友')} 闪开了！")
            return {"type": "miss"}
    power = rng.uniform(0.95, 1.15)
    crit_rate = min(0.12, 0.04 + int(enemy.get("agi", 1)) / 700.0)
    dmg, is_crit = _compute_damage(int(enemy.get("atk", 1)), tdef, power, rng, crit_rate)
    if target["kind"] == "player":
        dmg = _apply_defend_mult_to_damage(battle, dmg)
    _apply_enemy_hit_target(state, enemy, dmg, target, logs)
    _guard_info = battle.pop("_last_guard_applied", None)
    shown_dmg = int(_guard_info.get("shown_dmg", dmg)) if isinstance(_guard_info, dict) else int(dmg)
    # chance to add status only if hit player
    if target["kind"] == "player" and enemy_mp >= 8 and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
        if rng.random() < 0.5:
            _player_apply_burn_stack(state, logs)
        else:
            state["status_effects"] = [e for e in state.get("status_effects", []) if e.get("kind") != "poison"]
            state["status_effects"].append({"kind": "poison", "turns": 3, "dmg": max(2, int(dmg * 0.2))})
            logs.append("状态：中毒（持续3回合）")
        enemy["mp"] = max(0, enemy_mp - 8)
    # Q3 Boss 被动：熔核余烬（命中主角时，额外概率附加灼烧）
    if mid == "boss_golem" and target["kind"] == "player" and rng.random() < MONSTER_SPECIAL_MOVE_CHANCE:
        logs.append("🔥 熔核余烬：")
        _player_apply_burn_stack(state, logs)
    tname = "你" if target["kind"] == "player" else battle["allies"][int(target["idx"])].get("name", "队友")
    logs.append(f"{enemy['name']}（{lv_tag}）命中{tname}，造成{shown_dmg}{'（暴击）' if is_crit else ''}")
    return {"type": "attack", "dmg": dmg}


def _battle_player_move(state: Dict[str, Any], action: Dict[str, Any], rng: random.Random, logs: List[str]) -> None:
    battle = state["battle"]
    if int(battle.get("player_hp", 0) or 0) <= 0:
        return
    kind = action.get("kind")
    target = _pick_player_target(battle, action.get("target_id"))
    if kind in ("attack", "skill") and not target:
        return
    _dq_try_append_player_video_stem(state, battle, action)
    _ensure_attrs(state)
    ea = _effective_attrs(state)
    dex = int(ea.get("dex", 0))
    tb_hit = _talent_combat_flat_bonuses(list(state.get("talents") or []))
    acc_hit = _accessory_extra_bonus(state)
    hit_bonus = float(tb_hit.get("hit_bonus", 0.0)) + float(acc_hit.get("hit_bonus", 0.0) or 0.0)
    hit_rate = min(1.0, _role_hit_rate(str(state.get("role", "warrior")), dex) + hit_bonus)
    talents = set(state.get("talents") or [])
    # 物理类增伤：主要给战士分支用（修复：本函数需显式定义作用域变量）
    phys_mult = 1.0
    if "warrior_t10_a" in talents:
        phys_mult += float(TALENT_CHOICE_DEFS.get("warrior_t10_a", {}).get("effects", {}).get("phys_dmg_bonus", 0.0) or 0.0)
    low_hp_atk_bonus = 0.0
    if "warrior_t30_a" in talents:
        low_hp_atk_bonus += float(TALENT_CHOICE_DEFS.get("warrior_t30_a", {}).get("effects", {}).get("low_hp_atk_bonus", 0.0) or 0.0)
    fury_mult = 1.0
    if low_hp_atk_bonus > 0:
        php = int(battle.get("player_hp", 0) or 0)
        pmh = int(battle.get("player_max_hp", 1) or 1)
        if php > 0 and php <= max(1, int(pmh * 0.20)):
            fury_mult += low_hp_atk_bonus
    crit_rate = _player_crit_rate(state)
    att_phys = _player_battle_physical_att(state)
    # 技能是否视作“魔法类”（不吃战士物理增伤）；原通用火/雷已改为怪物专属
    magic_sids = set()

    if kind == "attack":
        if rng.random() > hit_rate:
            logs.append("你的攻击未命中！")
            return
        dmg, is_crit = _compute_damage(att_phys, int(target["def"]), 1.0, rng, crit_rate)
        dmg = int(dmg * _dmg_vs_enemy_mult(state, target) * phys_mult * fury_mult)
        fd = _apply_wither_boss_incoming_damage(target, dmg, battle, logs, reflect_from="player")
        _try_soul_drink(state, battle, fd, logs)
        _try_execute_amulet(state, target, rng, logs)
        logs.append(f"你攻击 {target.get('name','敌人')}，造成{fd}{'（暴击）' if is_crit else ''}")
        return

    if kind == "skill":
        sid = action.get("sid")
        catalog = _skill_catalog()
        if sid not in catalog:
            return
        sk = catalog[sid]
        if int(battle.get("player_mp", 0) or 0) < sk.mp_cost:
            logs.append("MP不足，无法执行行动")
            return
        battle["player_mp"] = int(battle.get("player_mp", 0) or 0) - sk.mp_cost
        if sk.kind == "heal":
            int_bonus = int(ea.get("int", 0))
            base = int(state["max_hp"] * 0.24) + int_bonus * 2
            heal = int(base * (0.80 + 0.32 * sk.power) * rng.uniform(0.9, 1.05))
            battle["player_hp"] = min(int(battle["player_max_hp"]), int(battle["player_hp"]) + heal)
            logs.append(f"{sk.name}（MP-{sk.mp_cost}）成功！HP 恢复+{heal}")
            return
        if sk.kind == "buff":
            logs.append(f"{sk.name}（MP-{sk.mp_cost}）！本回合敌人对你的直接攻击伤害降低 65%")
            return
        if sk.kind == "cover_party":
            rem = int(battle.get("cover_party_turns", 0) or 0)
            logs.append(
                f"{sk.name}（MP-{sk.mp_cost}）：你与存活队友获得额外约 20% 免伤，持续 {COVER_PARTY_DURATION_TURNS} 回合"
                f"（当前剩余 {rem} 回合）。"
            )
            return
        if sk.kind == "war_cry":
            battle.setdefault("skill_cd", {})[str(sid)] = int(WARRIOR_SPECIAL_SKILL_CD_TURNS)
            battle["war_cry_turns"] = int(WAR_CRY_DURATION_TURNS)
            logs.append(
                f"{sk.name}（MP-{sk.mp_cost}）：全队对敌人造成的直接伤害提高"
                f" {int(round((WAR_CRY_ATK_MULT - 1.0) * 100))}%，持续 {WAR_CRY_DURATION_TURNS} 回合（含本回合）。"
            )
            return
        if sk.kind == "shield_counter":
            battle.setdefault("skill_cd", {})[str(sid)] = int(WARRIOR_SPECIAL_SKILL_CD_TURNS)
            if not bool(battle.pop("_armor_break_pre_enemy", False)):
                battle["shield_counter_active"] = True
                battle["taunt_pending_next_enemy"] = True
            logs.append(
                f"{sk.name}（MP-{sk.mp_cost}）：本回合敌方攻击集中在你身上；"
                f"你受到的敌方直接伤害额外降低约 {int(round((1.0 - SHIELD_COUNTER_PLAYER_INCOMING_MULT) * 100))}%，"
                f"并将实际所受伤害的 {int(round(SHIELD_COUNTER_REFLECT_FRAC * 100))}% 反弹给当次攻击者。"
            )
            return
        if sk.kind == "double_slash":
            # 每段独立 10% 未命中，与 _role_hit_rate（DEX）无关，避免与命中率叠加过低
            att_eff = att_phys
            logs.append(f"你施放「{sk.name}」（MP-{sk.mp_cost}）。")
            for hit in (1, 2):
                if int(target.get("hp", 0) or 0) <= 0:
                    break
                if rng.random() < LIANZHAN_MISS_PER_HIT:
                    logs.append(f"「{sk.name}」第{hit}段未命中！")
                    continue
                dmg, is_crit = _compute_damage(att_eff, int(target["def"]), sk.power, rng, crit_rate)
                dmg = int(dmg * _dmg_vs_enemy_mult(state, target) * phys_mult * fury_mult)
                fd = _apply_wither_boss_incoming_damage(target, dmg, battle, logs, reflect_from="player")
                _try_soul_drink(state, battle, fd, logs)
                _try_execute_amulet(state, target, rng, logs)
                logs.append(f"你使用「{sk.name}」第{hit}段命中 {target.get('name','敌人')}，造成{fd}{'（暴击）' if is_crit else ''}")
            return
        if sk.kind == "quick_stab_chain":
            att_eff = att_phys
            _qs_probs = _quick_stab_chain_probs_for_talents(list(state.get("talents") or []))
            logs.append(f"你施放「{sk.name}」（MP-{sk.mp_cost}）。")
            for hit_i in range(1, 5):
                if hit_i > 1:
                    if rng.random() >= _qs_probs[hit_i - 2]:
                        break
                if int(target.get("hp", 0) or 0) <= 0:
                    break
                if hit_i == 1:
                    if rng.random() > hit_rate:
                        logs.append(f"「{sk.name}」未命中！")
                        return
                dmg, is_crit = _compute_damage(att_eff, int(target["def"]), QUICK_STAB_HIT_POWER, rng, crit_rate)
                dmg = int(dmg * _dmg_vs_enemy_mult(state, target) * phys_mult * fury_mult)
                fd = _apply_wither_boss_incoming_damage(target, dmg, battle, logs, reflect_from="player")
                _try_soul_drink(state, battle, fd, logs)
                _try_execute_amulet(state, target, rng, logs)
                logs.append(
                    f"「{sk.name}」第{hit_i}刀命中 {target.get('name','敌人')}，造成{fd}{'（暴击）' if is_crit else ''}"
                )
            return
        if sid == "whirlwind":
            if rng.random() > hit_rate:
                logs.append(f"{sk.name}（MP-{sk.mp_cost}）失手了！")
                return
            att_eff = att_phys
            dmg, is_crit = _compute_damage(att_eff, int(target["def"]), sk.power, rng, crit_rate)
            dmg = int(dmg * _dmg_vs_enemy_mult(state, target) * phys_mult * fury_mult)
            fd = _apply_wither_boss_incoming_damage(target, dmg, battle, logs, reflect_from="player")
            _try_soul_drink(state, battle, fd, logs)
            _try_execute_amulet(state, target, rng, logs)
            logs.append(
                f"你使用{sk.name}（MP-{sk.mp_cost}）命中 {target.get('name','敌人')}，造成{fd}{'（暴击）' if is_crit else ''}"
            )
            tid = str(target.get("eid") or "")
            alive2 = _alive_enemies(battle)
            others = [e for e in alive2 if str(e.get("eid") or "") != tid]
            if others:
                splash_target = rng.choice(others)
                extra_note = ""
            else:
                splash_target = next((e for e in alive2 if str(e.get("eid") or "") == tid), None)
                extra_note = "（无其他敌人，余威落在同一目标）"
            if splash_target is None:
                return
            dmg2, is_crit2 = _compute_damage(att_eff, int(splash_target["def"]), sk.power * 0.38, rng, crit_rate)
            dmg2 = int(dmg2 * _dmg_vs_enemy_mult(state, splash_target) * phys_mult * fury_mult)
            fd2 = _apply_wither_boss_incoming_damage(splash_target, dmg2, battle, logs, reflect_from="player")
            _try_soul_drink(state, battle, fd2, logs)
            _try_execute_amulet(state, splash_target, rng, logs)
            logs.append(
                f"旋风余威命中 {splash_target.get('name','敌人')}，造成{fd2}{'（暴击）' if is_crit2 else ''}{extra_note}"
            )
            return
        if sid in ("arcane_bolt", "fire_blast", "chain_lightning", "meteor"):
            if str(state.get("role", "")) != "mage":
                logs.append("非法师无法使用该技能")
                return
            att_v = _player_mage_spell_att(state)
            spell_power_mult = 1.0
            if "mage_t20_a" in talents:
                spell_power_mult += float(
                    TALENT_CHOICE_DEFS.get("mage_t20_a", {}).get("effects", {}).get("spell_power_bonus", 0.0) or 0.0
                )
            fire_power_mult = 1.0
            if "mage_t10_a" in talents:
                fire_power_mult += float(
                    TALENT_CHOICE_DEFS.get("mage_t10_a", {}).get("effects", {}).get("fire_power_bonus", 0.0) or 0.0
                )
            meteor_power_mult = 1.0
            if "mage_t30_a" in talents:
                meteor_power_mult += float(
                    TALENT_CHOICE_DEFS.get("mage_t30_a", {}).get("effects", {}).get("meteor_power_bonus", 0.0) or 0.0
                )
            chain_lightning_dmg_mult = 1.0
            chain_lightning_extra_hits = 0
            if "mage_t20_b" in talents:
                _t20b = (TALENT_CHOICE_DEFS.get("mage_t20_b", {}) or {}).get("effects") or {}
                chain_lightning_dmg_mult = float(_t20b.get("chain_lightning_damage_mult", 1.0) or 1.0)
                chain_lightning_extra_hits = int(_t20b.get("chain_lightning_extra_hits", 0) or 0)
            g_agi = int(ea.get("agi", 1) or 1)
            crit_m = min(0.33, 0.04 + g_agi * 0.0018)
            _map_crit_bonus = float((state.get("resources") or {}).get("clue_bonus_crit", 0.0) or 0.0)
            crit_m = min(0.45, crit_m + _map_crit_bonus)
            if rng.random() > hit_rate:
                logs.append(f"{sk.name}（MP-{sk.mp_cost}）未命中。")
                return
            if sid == "meteor":
                es_al = _alive_enemies(battle)
                if not es_al:
                    return
                p = float(sk.power) * meteor_power_mult * spell_power_mult
                total_dmg, is_crit = _compute_damage(att_v, _enemy_resist_for_spell_hit(es_al[0]), p, rng, crit_m)
                total_dmg = int(total_dmg * _dmg_vs_enemy_mult(state, es_al[0]))
                n = len(es_al)
                base = total_dmg // n
                rem = total_dmg % n
                logs.append(
                    f"你释放陨星术（MP-{sk.mp_cost}），星陨总伤 {total_dmg}{'（暴击）' if is_crit else ''}，由 {n} 名敌人均分。"
                )
                for ii, en in enumerate(es_al):
                    if int(en.get("hp", 0) or 0) <= 0:
                        continue
                    portion = base + (1 if ii < rem else 0)
                    if portion <= 0:
                        continue
                    fd = _apply_wither_boss_incoming_damage(en, portion, battle, logs, reflect_from="player")
                    _try_soul_drink(state, battle, fd, logs)
                    _try_execute_amulet(state, en, rng, logs)
                    logs.append(f"  → {en.get('name','敌人')} 受到 {fd}。")
                return
            if sid == "chain_lightning":
                p_hit = float(sk.power) * MAGE_CHAIN_HIT_POWER_FRAC * chain_lightning_dmg_mult * spell_power_mult
                tgt0 = target
                if int(tgt0.get("hp", 0) or 0) <= 0:
                    es0 = _alive_enemies(battle)
                    if not es0:
                        return
                    tgt0 = rng.choice(es0)
                dmg1, is_crit1 = _compute_damage(att_v, _enemy_resist_for_spell_hit(tgt0), p_hit, rng, crit_m)
                dmg1 = int(dmg1 * _dmg_vs_enemy_mult(state, tgt0))
                fd1 = _apply_wither_boss_incoming_damage(tgt0, dmg1, battle, logs, reflect_from="player")
                _try_soul_drink(state, battle, fd1, logs)
                _try_execute_amulet(state, tgt0, rng, logs)
                logs.append(
                    f"你释放连锁闪电（MP-{sk.mp_cost}）主闪命中 {tgt0.get('name','敌人')}，造成 {fd1}{'（暴击）' if is_crit1 else ''}。"
                )
                for _ in range(MAGE_CHAIN_EXTRA_HITS + chain_lightning_extra_hits):
                    es_now = _alive_enemies(battle)
                    if not es_now:
                        break
                    tgt = rng.choice(es_now)
                    dmgh, is_crh = _compute_damage(att_v, _enemy_resist_for_spell_hit(tgt), p_hit, rng, crit_m)
                    dmgh = int(dmgh * _dmg_vs_enemy_mult(state, tgt))
                    fdh = _apply_wither_boss_incoming_damage(tgt, dmgh, battle, logs, reflect_from="player")
                    _try_soul_drink(state, battle, fdh, logs)
                    _try_execute_amulet(state, tgt, rng, logs)
                    logs.append(
                        f"连锁闪电弹射命中 {tgt.get('name','敌人')}，造成 {fdh}{'（暴击）' if is_crh else ''}。"
                    )
                return
            if sid == "fire_blast":
                p = float(sk.power) * fire_power_mult * spell_power_mult
                dmg, is_crit = _compute_damage(att_v, _enemy_resist_for_spell_hit(target), p, rng, crit_m)
                dmg = int(dmg * _dmg_vs_enemy_mult(state, target))
                fd = _apply_wither_boss_incoming_damage(target, dmg, battle, logs, reflect_from="player")
                _try_soul_drink(state, battle, fd, logs)
                _try_execute_amulet(state, target, rng, logs)
                logs.append(
                    f"你释放爆炎术（MP-{sk.mp_cost}），对 {target.get('name','敌人')} 造成 {fd}{'（暴击）' if is_crit else ''}。"
                )
                _mage_apply_fire_blast_burn(target, rng, logs)
                return
            p = float(sk.power) * spell_power_mult
            dmg, is_crit = _compute_damage(att_v, _enemy_resist_for_spell_hit(target), p, rng, crit_m)
            dmg = int(dmg * _dmg_vs_enemy_mult(state, target))
            fd = _apply_wither_boss_incoming_damage(target, dmg, battle, logs, reflect_from="player")
            _try_soul_drink(state, battle, fd, logs)
            _try_execute_amulet(state, target, rng, logs)
            logs.append(
                f"你释放奥术冲击（MP-{sk.mp_cost}），对 {target.get('name','敌人')} 造成 {fd}{'（暴击）' if is_crit else ''}。"
            )
            if "mage_t10_b" in talents:
                adc = float(
                    TALENT_CHOICE_DEFS.get("mage_t10_b", {}).get("effects", {}).get("arcane_double_chance", 0.0) or 0.0
                )
                if adc > 0 and rng.random() < adc:
                    dmg2, is_crit2 = _compute_damage(att_v, _enemy_resist_for_spell_hit(target), p, rng, crit_m)
                    dmg2 = int(dmg2 * _dmg_vs_enemy_mult(state, target))
                    fd2 = _apply_wither_boss_incoming_damage(target, dmg2, battle, logs, reflect_from="player")
                    _try_soul_drink(state, battle, fd2, logs)
                    _try_execute_amulet(state, target, rng, logs)
                    logs.append(
                        f"灵闪！追加奥术冲击，对 {target.get('name','敌人')} 造成 {fd2}{'（暴击）' if is_crit2 else ''}。"
                    )
            return
        if sid == "volley":
            if str(state.get("role", "")) != "hunter":
                logs.append("非猎人无法使用该技能")
                return
            if rng.random() > hit_rate:
                logs.append(f"{sk.name}（MP-{sk.mp_cost}）失手了！")
                return
            volley_hit_crit_bonus = (
                float(TALENT_CHOICE_DEFS.get("hunter_t30_b", {}).get("effects", {}).get("volley_hit_crit_bonus", 0.0) or 0.0)
                if "hunter_t30_b" in talents
                else 0.0
            )
            crit_volley = min(0.85, crit_rate + volley_hit_crit_bonus)
            volley_per = float(HUNTER_VOLLEY_HIT_POWER)
            att_eff = att_phys
            cur = target
            logs.append(f"你施放连射（MP-{sk.mp_cost}）。")
            for hit_i in range(1, HUNTER_VOLLEY_HITS + 1):
                es_live = _alive_enemies(battle)
                if not es_live:
                    break
                if int(cur.get("hp", 0) or 0) <= 0:
                    cur = rng.choice(es_live)
                dmg, is_crit = _compute_damage(att_eff, int(cur.get("def", 0) or 0), volley_per, rng, crit_volley)
                dmg = int(dmg * _dmg_vs_enemy_mult(state, cur) * phys_mult * fury_mult)
                fd = _apply_wither_boss_incoming_damage(cur, dmg, battle, logs, reflect_from="player")
                _try_soul_drink(state, battle, fd, logs)
                _try_execute_amulet(state, cur, rng, logs)
                logs.append(
                    f"连射第{hit_i}箭命中 {cur.get('name','敌人')}，造成{fd}{'（暴击）' if is_crit else ''}。"
                )
            return
        # damage / drain
        if sid != "aim_shot" and rng.random() > hit_rate:
            logs.append(f"{sk.name}（MP-{sk.mp_cost}）失手了！")
            return
        att_eff = att_phys
        eff_power = float(sk.power)
        if sid == "aim_shot" and "hunter_t10_a" in talents:
            eff_power *= 1.0 + float(
                TALENT_CHOICE_DEFS.get("hunter_t10_a", {}).get("effects", {}).get("aim_shot_power_bonus", 0.0) or 0.0
            )
        if sid == "eagle_eye" and "hunter_t30_a" in talents:
            eff_power *= 1.0 + float(
                TALENT_CHOICE_DEFS.get("hunter_t30_a", {}).get("effects", {}).get("eagle_eye_power_bonus", 0.0) or 0.0
            )
        dmg, is_crit = _compute_damage(att_eff, int(target["def"]), eff_power, rng, crit_rate)
        dmg = int(dmg * _dmg_vs_enemy_mult(state, target))
        if sid not in magic_sids:
            dmg = int(dmg * phys_mult * fury_mult)
        fd = _apply_wither_boss_incoming_damage(target, dmg, battle, logs, reflect_from="player")
        _try_soul_drink(state, battle, fd, logs)
        _try_execute_amulet(state, target, rng, logs)
        extra_eagle = ""
        if sid == "eagle_eye":
            _ebp = HUNTER_EAGLE_EYE_BLIND_CHANCE
            if "hunter_t30_a" in talents:
                _ebp += float(
                    TALENT_CHOICE_DEFS.get("hunter_t30_a", {}).get("effects", {}).get("eagle_eye_blind_chance_bonus", 0.0)
                    or 0.0
                )
            if not _enemy_is_boss(target) and rng.random() < min(1.0, _ebp):
                target.setdefault("effects", [])
                target["effects"] = [x for x in (target.get("effects") or []) if str(x.get("kind")) != "blind"]
                target["effects"].append({"kind": "blind", "turns": 1})
                extra_eagle = "（致盲！）"
        extra_deep = ""
        if sid == "deep_cut" and not _enemy_is_boss(target) and rng.random() < 0.30:
            target.setdefault("effects", [])
            target["effects"] = [x for x in (target.get("effects") or []) if str(x.get("kind")) != "bleed"]
            target["effects"].append({"kind": "bleed", "turns": 3, "pct": 0.10})
            extra_deep = "（流血！）"
        logs.append(
            f"你使用{sk.name}（MP-{sk.mp_cost}）命中 {target.get('name','敌人')}，造成{fd}{'（暴击）' if is_crit else ''}{extra_eagle}{extra_deep}"
        )
        if sk.kind == "drain":
            steal = max(1, int(fd * 0.12))
            battle["player_hp"] = min(int(battle["player_max_hp"]), int(battle["player_hp"]) + steal)
            logs.append(f"「{sk.name}」汲取生命 +{steal} HP")
        return

    if kind == "defend":
        _dt = action.get("defend_target")
        if isinstance(_dt, str) and _dt.startswith("ally:"):
            logs.append("你进入防守姿态：守护队友（直击你减伤45%，被守护队友受击时你与其各承担减伤后的一半）")
        else:
            logs.append("你进入防守姿态：守护自己（敌人对你的直接攻击伤害降低 65%）")
        return

    if kind == "item":
        item_id = action.get("item_id")
        item_target = str(action.get("item_target") or "player")
        inv = state["inventory"]
        for it in inv:
            if it.get("item_id") == item_id and int(it.get("qty", 0) or 0) > 0:
                meta = it.get("meta", {}) or {}
                use = meta.get("use")
                if use not in BATTLE_POTION_USES:
                    logs.append("该物品不可用于战斗")
                    return
                nm = it.get("name", "药水")
                dh, dm = _potion_restore_from_meta(battle, meta, str(use))
                tgt_name = "主角"
                tgt_is_player = True
                tgt_ally_idx = -1
                if item_target.startswith("ally:"):
                    _aid = item_target.split(":", 1)[1]
                    for _idx, _al in enumerate(battle.get("allies", []) or []):
                        if str(_al.get("aid") or _al.get("mid") or "") != _aid:
                            continue
                        # 非复活：仅允许仍存活队友作目标；复活药水必须能匹配已倒地者
                        if str(use) != "revive_potion" and int(_al.get("hp", 0) or 0) <= 0:
                            continue
                        tgt_is_player = False
                        tgt_ally_idx = _idx
                        tgt_name = str(_al.get("name", "队友"))
                        break
                if tgt_is_player:
                    tgt_name = str(state.get("name", "主角"))
                if use == "revive_potion":
                    allies = battle.get("allies") or []
                    if tgt_is_player:
                        logs.append("复活药水只能用于已倒地队友。")
                        return
                    if not (0 <= tgt_ally_idx < len(allies)):
                        logs.append("复活目标不存在。")
                        return
                    _a = allies[tgt_ally_idx]
                    if int(_a.get("hp", 0) or 0) > 0:
                        logs.append(f"{tgt_name} 当前未倒地，复活药水未生效。")
                        return
                    hp_rev = max(1, int(int(_a.get("max_hp", 1) or 1) * max(1, int(meta.get("revive_hp_pct", POTION_REVIVE_HP_PCT))) / 100))
                    mp_max = int(_a.get("max_mp", 0) or 0)
                    mp_rev = int(mp_max * max(1, int(meta.get("revive_mp_pct", POTION_REVIVE_MP_PCT))) / 100)
                    if mp_max > 0:
                        mp_rev = max(1, mp_rev)
                    _a["hp"] = min(int(_a.get("max_hp", 1) or 1), hp_rev)
                    _a["mp"] = min(mp_max, max(0, mp_rev))
                    logs.append(f"使用{nm}，{tgt_name} 复活（HP {_a['hp']} / MP {_a['mp']}）。")
                    it["qty"] = int(it.get("qty", 1) or 1) - 1
                    return
                if use == "heal_potion":
                    if tgt_is_player:
                        battle["player_hp"] = min(int(battle["player_max_hp"]), int(battle["player_hp"]) + dh)
                    elif 0 <= tgt_ally_idx < len(battle.get("allies", []) or []):
                        _a = battle["allies"][tgt_ally_idx]
                        _a["hp"] = min(int(_a.get("max_hp", 1) or 1), int(_a.get("hp", 0) or 0) + dh)
                    logs.append(f"使用{nm}，{tgt_name} HP +{dh}")
                elif use == "mp_potion":
                    if tgt_is_player:
                        battle["player_mp"] = min(int(battle["player_max_mp"]), int(battle["player_mp"]) + dm)
                    elif 0 <= tgt_ally_idx < len(battle.get("allies", []) or []):
                        _a = battle["allies"][tgt_ally_idx]
                        _a["mp"] = min(int(_a.get("max_mp", 0) or 0), int(_a.get("mp", 0) or 0) + dm)
                    logs.append(f"使用{nm}，{tgt_name} MP +{dm}")
                else:
                    if tgt_is_player:
                        battle["player_hp"] = min(int(battle["player_max_hp"]), int(battle["player_hp"]) + dh)
                        battle["player_mp"] = min(int(battle["player_max_mp"]), int(battle["player_mp"]) + dm)
                    elif 0 <= tgt_ally_idx < len(battle.get("allies", []) or []):
                        _a = battle["allies"][tgt_ally_idx]
                        _a["hp"] = min(int(_a.get("max_hp", 1) or 1), int(_a.get("hp", 0) or 0) + dh)
                        _a["mp"] = min(int(_a.get("max_mp", 0) or 0), int(_a.get("mp", 0) or 0) + dm)
                    logs.append(f"使用{nm}，{tgt_name} HP +{dh}，MP +{dm}")
                it["qty"] = int(it.get("qty", 1) or 1) - 1
                return
        logs.append("物品不存在")


def _resolve_turn(state: Dict[str, Any], player_action: Dict[str, Any], rng: random.Random, logs: List[str]) -> bool:
    """结算一回合；若因 MP 不足无法释放技能则返回 False（不推进回合、不结算持续效果与敌我行动）。"""
    battle = state["battle"]
    battle["player_damage_taken_this_turn"] = 0
    battle["dq_turn_video_stems"] = []
    battle.pop("_cleric_divine_bless_done_pre_enemy", None)
    _sync_primary_enemy(battle)
    enemies_alive = _alive_enemies(battle)
    if not enemies_alive:
        battle["result"] = "win"
        return True
    player_agi = int(state.get("agi", 1) or 1)
    enemy_agi = max(int(e.get("agi", 1) or 1) for e in enemies_alive)
    player_first = (rng.randint(0, 10) + player_agi) >= (rng.randint(0, 10) + enemy_agi)
    if player_action.get("kind") == "item":
        player_first = True

    if player_action.get("kind") == "flee":
        _fs = _dq_player_video_stem_from_action(state, player_action)
        if _fs:
            _dq_append_turn_video_stem(battle, _fs)
        gap = player_agi - enemy_agi
        base = max(0.08, min(0.85, 0.35 + gap * 0.015))
        if rng.random() < base:
            battle["result"] = "flee"
            logs.append("你成功逃脱了战斗！")
            return True
        logs.append("你没能逃脱！")

    if str(player_action.get("kind")) == "skill":
        sid = player_action.get("sid")
        sk = _skill_catalog().get(sid)
        if sk is not None and int(battle.get("player_mp", 0) or 0) < int(sk.mp_cost):
            logs.append("MP不足，无法执行行动")
            return False
        if sk is not None and sk.kind in ("war_cry", "shield_counter"):
            scd = battle.get("skill_cd") or {}
            rem = int(scd.get(str(sid), 0) or 0)
            if rem > 0:
                logs.append(f"{sk.name} 冷却中（剩余 {rem} 回合），无法使用。")
                return False

    if str(player_action.get("kind")) == "defend":
        rem = int(battle.get("defend_cd", 0) or 0)
        if rem > 0:
            logs.append(f"防守冷却中（剩余 {rem} 回合），无法使用。")
            return False

    _apply_status_tick(state, "player", rng, logs)
    _apply_enemy_effect_ticks(battle, logs)
    _sync_primary_enemy(battle)
    if int(battle.get("player_hp", 0) or 0) <= 0:
        battle["result"] = "lose"
        return True
    if not _alive_enemies(battle):
        battle["result"] = "win"
        return True

    # 本回合防守配置（供敌方命中结算使用）
    battle["guard_cfg"] = {"active": False}
    if player_action.get("kind") == "defend":
        dt = str(player_action.get("defend_target") or "player")
        if dt.startswith("ally:"):
            aid = dt.split(":", 1)[1]
            idx = -1
            for i, a in enumerate(battle.get("allies", []) or []):
                if str(a.get("aid") or a.get("mid") or "") == aid and int(a.get("hp", 0) or 0) > 0:
                    idx = i
                    break
            if idx >= 0:
                battle["guard_cfg"] = {"active": True, "target_kind": "ally", "target_idx": idx, "target_aid": aid}
            else:
                battle["guard_cfg"] = {"active": True, "target_kind": "player", "target_idx": -1}
        else:
            battle["guard_cfg"] = {"active": True, "target_kind": "player", "target_idx": -1}
    elif (
        player_action.get("kind") == "skill"
        and str(player_action.get("sid")) == "heavy_strike"
        and int(battle.get("player_mp", 0) or 0) >= _skill_catalog()["heavy_strike"].mp_cost
    ):
        # 与守护姿态一致：在先后手判定之后、敌方行动之前即生效，敌方先手时本回合也能吃到援护
        battle["cover_party_turns"] = int(COVER_PARTY_DURATION_TURNS)
    elif (
        player_action.get("kind") == "skill"
        and str(player_action.get("sid")) == "armor_break"
        and int(battle.get("player_mp", 0) or 0) >= _skill_catalog()["armor_break"].mp_cost
    ):
        # 盾反：敌方先手时须在敌方行动前生效（强制集火主角 + 免伤/反弹）
        battle["shield_counter_active"] = True
        battle["taunt_pending_next_enemy"] = True
        battle["_armor_break_pre_enemy"] = True

    def _enemy_phase():
        if bool(battle.get("taunt_pending_next_enemy")):
            battle["taunt_active_this_enemy_phase"] = True
            battle["taunt_pending_next_enemy"] = False
        else:
            battle["taunt_active_this_enemy_phase"] = False
        for e in list(_alive_enemies(battle)):
            # 开场Boss蓄力惩罚只触发一次
            if bool(battle.get("open_charge_boss", False)) and _enemy_is_boss(e):
                e["enemy_power_strike_pending"] = True
                battle["open_charge_boss"] = False
            _battle_enemy_move(state, e, rng, logs)
            if int(battle.get("player_hp", 0) or 0) <= 0:
                break
        battle["taunt_active_this_enemy_phase"] = False
        battle["shield_counter_active"] = False

    if player_first:
        _battle_player_move(state, player_action, rng, logs)
        _allies_auto_action(state, rng, logs)
        if not _alive_enemies(battle):
            battle["result"] = "win"
            return True
        _enemy_phase()
    else:
        _cleric_divine_bless_before_enemy_phase(state, rng, logs)
        _enemy_phase()
        if int(battle.get("player_hp", 0) or 0) <= 0:
            battle["result"] = "lose"
            return True
        _battle_player_move(state, player_action, rng, logs)
        _allies_auto_action(state, rng, logs)

    if not _alive_enemies(battle):
        battle["result"] = "win"
    elif int(battle.get("player_hp", 0) or 0) <= 0:
        battle["result"] = "lose"
    return True


def dq_battle_action_was_aborted(state: Dict[str, Any]) -> bool:
    """本回合因 MP 不足、冷却等未真正出手（不应播放技能/普攻动画）。"""
    meta = (state or {}).get("meta") or {}
    if bool(meta.get("dq_last_battle_action_aborted")):
        return True
    logs = meta.get("battle_log") or []
    if not logs:
        return False
    last = str(logs[-1] or "")
    return ("MP不足，无法执行行动" in last) or ("无法使用。" in last)


def dq_battle_action(state: Dict[str, Any], action: Dict[str, Any], rng: random.Random) -> Dict[str, Any]:
    state = copy.deepcopy(state)
    if state.get("phase") != "battle":
        return state
    _ensure_meta_logs(state)
    battle = state["battle"]
    if battle.get("result"):
        return state

    logs: List[str] = []
    turn_done = _resolve_turn(state, action, rng, logs)
    if not turn_done:
        state["meta"]["battle_log"].extend(logs)
        state["meta"]["dq_last_battle_action_aborted"] = True
        return state

    state["meta"]["dq_last_battle_action_aborted"] = False
    state["meta"]["turn"] = int(state.get("meta", {}).get("turn", 0)) + 1
    _battle_log_append_round_separator(logs, battle)
    # 回合结束：结算“1回合伤害免疫”
    battle["player_immune_turns"] = max(0, int(battle.get("player_immune_turns", 0) or 0) - 1)
    for al in (battle.get("allies") or []):
        if isinstance(al, dict):
            al["immune_turns"] = max(0, int(al.get("immune_turns", 0) or 0) - 1)
    _prev_cover = int(battle.get("cover_party_turns", 0) or 0)
    battle["cover_party_turns"] = max(0, _prev_cover - 1)
    _new_cover = int(battle.get("cover_party_turns", 0) or 0)
    if _prev_cover > 0:
        if _new_cover > 0:
            logs.append(f"🛡️ 援护：约 20% 减伤生效中，剩余 {_new_cover} 回合。")
        else:
            logs.append("🛡️ 援护效果已结束。")
    _prev_wc = int(battle.get("war_cry_turns", 0) or 0)
    battle["war_cry_turns"] = max(0, _prev_wc - 1)
    _new_wc = int(battle.get("war_cry_turns", 0) or 0)
    if _prev_wc > 0:
        if _new_wc > 0:
            logs.append(f"📣 战吼：全队对敌伤害 +{int(round((WAR_CRY_ATK_MULT - 1.0) * 100))}% 生效中，剩余 {_new_wc} 回合。")
        else:
            logs.append("📣 战吼攻击力加成已结束。")
    for e in list(battle.get("enemies") or []):
        if not isinstance(e, dict) or str(e.get("mid")) != "miner_golem":
            continue
        t = int(e.get("miner_guard_stance_turns", 0) or 0)
        if t > 0:
            e["miner_guard_stance_turns"] = t - 1
    scd = battle.setdefault("skill_cd", {})
    for _k in ("execution", "armor_break"):
        if int(scd.get(_k, 0) or 0) > 0:
            scd[_k] = max(0, int(scd.get(_k, 0) or 0) - 1)
    if str(action.get("kind") or "") == "defend":
        battle["defend_cd"] = int(PLAYER_DEFEND_COOLDOWN_TURNS)
    battle["defend_cd"] = max(0, int(battle.get("defend_cd", 0) or 0) - 1)
    battle["turn"] = int(battle.get("turn", 1) or 1) + 1
    _sync_primary_enemy(battle)

    if battle.get("result") == "win" or not _alive_enemies(battle):
        battle["result"] = "win"
    if battle.get("result") == "lose" or int(battle.get("player_hp", 0) or 0) <= 0:
        battle["result"] = "lose"

    state["meta"]["battle_log"].extend(logs)
    overworld_lines: List[str] = []
    battle_end_lines: List[str] = []

    def _sync_party_from_battle(all_dead_to_one: bool = False) -> None:
        members = state.get("party_members") or []
        allies = (battle.get("allies") or []) if isinstance(battle, dict) else []
        if not members or not allies:
            return
        ally_map: Dict[str, Dict[str, Any]] = {}
        for a in allies:
            if not isinstance(a, dict):
                continue
            k = str(a.get("aid") or a.get("mid") or "")
            if k:
                ally_map[k] = a
        for mem in members:
            if not isinstance(mem, dict):
                continue
            key = str(mem.get("mid") or "")
            al = ally_map.get(key)
            if not al:
                continue
            if all_dead_to_one:
                mem["hp"] = 1
                mem["mp"] = 1
                continue
            hp_now = int(al.get("hp", 0) or 0)
            mp_now = int(al.get("mp", 0) or 0)
            if hp_now <= 0:
                mem["hp"] = 1
                mem["mp"] = 1
            else:
                mem["hp"] = max(1, min(int(mem.get("max_hp", 1) or 1), hp_now))
                mem["mp"] = max(0, min(int(mem.get("max_mp", 0) or 0), mp_now))

    if battle.get("result") == "win":
        enemies_all = battle.get("enemies") or ([battle.get("enemy")] if battle.get("enemy") else [])
        zone_id = state.get("location", "starter")
        floor = max(1, int((state.get("dungeon") or {}).get("floor", 1) or 1))
        inf_training = bool((state.get("dungeon") or {}).get("training_mode"))
        train_floor = max(1, int((state.get("dungeon") or {}).get("training_floor", floor) or floor))
        hero_lv_now = max(1, int(state.get("level", 1) or 1))
        # 无限地牢训练：若训练层比主角低 >=3 级，则不给经验/金币，也不掉装备和药水
        no_reward_easy_training = bool(
            state.get("location") == "infinite" and inf_training and (hero_lv_now - train_floor) >= 3
        )
        xp_total = 0
        gold_total = 0
        items_all: List[Dict[str, Any]] = []
        mats_all: List[Dict[str, Any]] = []
        q1_tut_meta = (state.get("meta") or {}).get("q1_post_act1_tutorial")
        q1_tut_battle = bool(
            isinstance(q1_tut_meta, dict)
            and bool(q1_tut_meta.get("active"))
            and str(q1_tut_meta.get("focus", "")).startswith("battle_")
        )
        q1_has_slime = any(isinstance(e, dict) and str(e.get("mid", "")) == "slime" for e in enemies_all)
        forced_tutorial_equip: Optional[Dict[str, Any]] = None
        for e in enemies_all:
            if not isinstance(e, dict):
                continue
            xp, gold, items, mats = _enemy_xp_and_drop(state["level"], e, rng, zone_id, floor)
            if not no_reward_easy_training:
                xp_total += int(xp)
                gold_total += int(gold)
                items_all.extend(items)
            mats_all.extend(mats)
        if q1_tut_battle and q1_has_slime and not no_reward_easy_training:
            # 去掉随机掉落的武器（可能带非战士职业署名）；无装备时再补一件非武器
            items_all = [
                it
                for it in items_all
                if not (
                    isinstance(it, dict)
                    and str((it.get("meta") or {}).get("slot", "")) == "weapon"
                )
            ]
            has_equip_drop = any(
                isinstance(it, dict)
                and str((it.get("meta") or {}).get("slot", "")) in EQUIPMENT_SLOTS
                for it in items_all
            )
            if not has_equip_drop:
                forced_tutorial_equip = _build_drop_equipment(
                    zone_id=zone_id,
                    player_level=int(state.get("level", 1) or 1),
                    floor=floor,
                    rng=rng,
                    force_slot=str(rng.choice(Q1_TUTORIAL_NON_WEAPON_SLOTS)),
                )
                items_all.append(forced_tutorial_equip)
        rare_names = _collect_rare_drop_names(items_all)
        if rare_names:
            _queue_unlock_notice(state, "🎁 稀有掉落", [f"获得：{x}" for x in rare_names])
        n_enemy = max(1, len([e for e in enemies_all if isinstance(e, dict)]))
        gain_mult = 1.0 + 0.18 * (n_enemy - 1)  # 多怪叠加系数
        xp = int(xp_total * gain_mult)
        gold = int(gold_total * gain_mult)
        state["exp"] = int(state.get("exp", 0) or 0) + xp
        gold_mult = 1.28 if _party_has_special_id(state, "gold_hoard") else 1.0
        gold_mult += float((state.get("resources") or {}).get("clue_bonus_gold_pct", 0.0) or 0.0)
        g_add = int(gold * gold_mult)
        state["gold"] = int(state.get("gold", 0) or 0) + g_add
        state["hp"] = int(battle.get("player_hp", state.get("hp", 1)) or 1)
        state["mp"] = int(battle.get("player_mp", state.get("mp", 0)) or 0)
        _sync_party_from_battle(all_dead_to_one=False)
        state["status_effects"] = []
        state["defend_turn"] = False

        ok_names, lost = dq_try_add_inventory(state, items_all)
        if forced_tutorial_equip and str(forced_tutorial_equip.get("name", "")) in lost:
            # 教学奖励兜底：即使背包满，也确保该装备进入背包并可继续教学流程
            state.setdefault("inventory", []).append(copy.deepcopy(forced_tutorial_equip))
            lost = [x for x in lost if str(x) != str(forced_tutorial_equip.get("name", ""))]
            ok_names.append(str(forced_tutorial_equip.get("name", "教学装备")))
            state.setdefault("meta", {}).setdefault("log", []).append("🎁 教学奖励：已为你保留一件装备到背包。")
        if lost:
            state.setdefault("meta", {}).setdefault("log", []).append(f"⚠️ 背包已满，未能拾取：{'、'.join(lost)}。")
        mat_display: List[str] = []
        mat_lost: List[str] = []
        for m in mats_all:
            nm = str(m.get("name", "草药"))
            qm = int(m.get("qty", 0) or 0)
            if qm <= 0:
                continue
            ok_m, _ = dq_try_add_material_stack(state, nm, qm, rng)
            if ok_m:
                mat_display.append(f"{nm}×{qm}")
            else:
                mat_lost.append(f"{nm}×{qm}")
        if mat_lost:
            state.setdefault("meta", {}).setdefault("log", []).append(f"⚠️ 背包已满，未能拾取材料：{'、'.join(mat_lost)}。")

        # 主线剧情推进仅看队首敌人（通常是主Boss）
        if state.get("location") != "infinite":
            lead_enemy = (battle.get("enemies") or [battle.get("enemy")])[0]
            if isinstance(lead_enemy, dict):
                _on_battle_win(state, lead_enemy, rng, logs)

        _plv_b = int(state.get("level", 1) or 1)
        _triv_b = _is_player_trivializing_zone(_plv_b, zone_id)
        if no_reward_easy_training:
            overworld_lines.append(
                f"🏆 战斗胜利：训练层级（第{train_floor}层）低于主角≥3级，本次无经验、无金币，且不掉落装备/药水。"
            )
            battle_end_lines.append(
                f"💀 最终结算：训练层第{train_floor}层过低（低于主角≥3级），经验 +0，金币 +0，装备/药水 +0。"
            )
        elif g_add > 0:
            overworld_lines.append(f"🏆 战斗胜利：敌人×{n_enemy}，经验 +{xp}，金币 +{g_add}。")
            battle_end_lines.append(f"💀 最终结算：共击败 {n_enemy} 个敌人，经验 +{xp}，金币 +{g_add}。")
        elif _triv_b:
            overworld_lines.append(f"🏆 战斗胜利：敌人×{n_enemy}，经验 +{xp}（该区域过于轻松，战斗不掉落金币）。")
            battle_end_lines.append(f"💀 最终结算：共击败 {n_enemy} 个敌人，经验 +{xp}（该区域过于轻松，无金币）。")
        else:
            overworld_lines.append(f"🏆 战斗胜利：敌人×{n_enemy}，经验 +{xp}，金币 +{g_add}。")
            battle_end_lines.append(f"💀 最终结算：共击败 {n_enemy} 个敌人，经验 +{xp}，金币 +{g_add}。")
        if ok_names:
            overworld_lines.append("获得道具：" + "、".join(ok_names))
        if mat_display:
            overworld_lines.append("获得材料：" + "、".join(mat_display))
        _maybe_level_up(state, rng, overworld_lines)

        if state.get("location") == "infinite" and not inf_training:
            state.setdefault("dungeon", {})
            state["dungeon"].pop("active_enemy", None)
            state["dungeon"].pop("active_enemy_floor", None)
            state["dungeon"]["wins"] = int(state["dungeon"].get("wins", 0) or 0) + 1
            if any(str(e.get("mid", "")).startswith("boss_") for e in enemies_all if isinstance(e, dict)):
                state["dungeon"]["last_boss_at"] = floor
            state["dungeon"]["floor"] = int(floor) + 1
        elif state.get("location") == "infinite" and inf_training:
            # 训练模式不保存层进度，也不记录 active_enemy。
            state.setdefault("dungeon", {})
            state["dungeon"].pop("active_enemy", None)
            state["dungeon"].pop("active_enemy_floor", None)
        _restore_overworld_location_after_infinite_dungeon(state)
        state["phase"] = "overworld"
        state["battle"] = None
        state["encounter"] = None
        state.setdefault("meta", {})["dq_last_battle_outcome"] = "win"
        if q1_tut_battle:
            qtm = state.setdefault("meta", {}).setdefault("q1_post_act1_tutorial", {})
            qtm["active"] = True
            notice_q = state.setdefault("meta", {}).get("pending_unlock_notice_queue") or []
            # 有掉落弹窗时先停留在 drop_notice：未点确认就切背包会与装备 dialog 叠开
            qtm["focus"] = "drop_notice" if (isinstance(notice_q, list) and notice_q) else "backpack_tab"
            qtm["target_equip_item_id"] = str(
                (forced_tutorial_equip or {}).get("item_id", qtm.get("target_equip_item_id", ""))
            )

    elif battle.get("result") == "lose":
        _lose_ratio = LOSE_GOLD_RATIO_INFINITE if state.get("location") == "infinite" else LOSE_GOLD_RATIO_NORMAL
        lose_gold = min(int(state.get("gold", 0) or 0), int(int(state.get("gold", 0) or 0) * float(_lose_ratio)))
        state["gold"] = int(state.get("gold", 0) or 0) - lose_gold
        state["hp"] = 1
        state["mp"] = 1
        _sync_party_from_battle(all_dead_to_one=True)
        state["stamina"] = max(0, int(int(state.get("max_stamina", 0) or 0) * 0.6))
        state["status_effects"] = []
        if state.get("location") == "infinite" and not bool((state.get("dungeon") or {}).get("training_mode")):
            state.setdefault("dungeon", {})
            ae = _infinite_active_enemy_from_battle(battle)
            if ae is not None:
                state["dungeon"]["active_enemy"] = ae
                state["dungeon"]["active_enemy_floor"] = int((state.get("dungeon") or {}).get("floor", 1) or 1)
        _q2_bump_wither_encounter_chance_on_fail(state, battle, overworld_lines)
        _q3_bump_golem_encounter_chance_on_fail(state, battle, overworld_lines)
        _q4_bump_sea_witch_encounter_chance_on_fail(state, battle, overworld_lines)
        _q5_bump_throne_guard_encounter_chance_on_fail(state, battle, overworld_lines)
        _restore_overworld_location_after_infinite_dungeon(state)
        state["phase"] = "overworld"
        state["battle"] = None
        state["encounter"] = None
        state.setdefault("meta", {})["dq_last_battle_outcome"] = "lose"
        battle_end_lines.append(f"💀 你倒下了。醒来后损失金币{lose_gold}，HP恢复到 {state['hp']}。")
        overworld_lines.append(f"战斗失败：损失金币{lose_gold}，未获得经验掉落。")

    elif battle.get("result") == "flee":
        state["stamina"] = min(int(state.get("max_stamina", 0) or 0), int(state.get("stamina", 0) or 0) + 2)
        state["hp"] = int(battle.get("player_hp", state.get("hp", 1)) or 1)
        state["mp"] = int(battle.get("player_mp", state.get("mp", 0)) or 0)
        _sync_party_from_battle(all_dead_to_one=False)
        state["status_effects"] = []
        if state.get("location") == "infinite" and not bool((state.get("dungeon") or {}).get("training_mode")):
            state.setdefault("dungeon", {})
            ae = _infinite_active_enemy_from_battle(battle)
            if ae is not None:
                state["dungeon"]["active_enemy"] = ae
                state["dungeon"]["active_enemy_floor"] = int((state.get("dungeon") or {}).get("floor", 1) or 1)
        _restore_overworld_location_after_infinite_dungeon(state)
        state["phase"] = "overworld"
        state["battle"] = None
        state["encounter"] = None
        state.setdefault("meta", {})["dq_last_battle_outcome"] = "flee"
        battle_end_lines.append("你带着一丝狼狈离开了战场。")
        overworld_lines.append("战斗结束：逃跑成功。")

    if battle_end_lines:
        state["meta"]["battle_log"].extend(battle_end_lines)
    if overworld_lines:
        state["meta"]["log"].extend(overworld_lines)
    _recalc_player_from_equipment(state)
    _ensure_inventory_integrity(state)
    return state


# ---------------------------------------------------------------------------
# PVP 联机：快照导出 + 与主线相同的「普攻 / 技能」结算（对手为主角+队友，需选目标）
# ---------------------------------------------------------------------------

PVP_BLOCKED_SKILL_IDS = frozenset({"heavy_strike", "execution", "armor_break"})
PVP_HERO_ALLY_MID = "__pvp_hero__"


def _pvp_build_actor_order(host_snap: Dict[str, Any], guest_snap: Dict[str, Any]) -> List[str]:
    order: List[str] = []
    order.append("host:hero")
    order.append("guest:hero")
    nh = len(host_snap.get("party") or [])
    ng = len(guest_snap.get("party") or [])
    for i in range(max(nh, ng)):
        if i < nh:
            order.append(f"host:p{i}")
        if i < ng:
            order.append(f"guest:p{i}")
    return order


def _pvp_actor_alive(battle: Dict[str, Any], actor_key: str) -> bool:
    parts = str(actor_key).strip().split(":")
    if len(parts) != 2:
        return False
    side, slot = parts[0], parts[1]
    if side not in ("host", "guest"):
        return False
    hero = battle.get(f"{side}_hero") or {}
    party = battle.get(f"{side}_party") or []
    if slot == "hero":
        return int(hero.get("hp", 0) or 0) > 0
    if slot.startswith("p") and slot[1:].isdigit():
        idx = int(slot[1:])
        if 0 <= idx < len(party):
            return int(party[idx].get("hp", 0) or 0) > 0
    return False


def _pvp_refresh_current_actor(battle: Dict[str, Any]) -> None:
    order = battle.get("actor_order") or []
    if not order:
        battle["actor"] = ""
        return
    start = int(battle.get("actor_index", 0) or 0) % len(order)
    for step in range(len(order)):
        i = (start + step) % len(order)
        ak = order[i]
        if _pvp_actor_alive(battle, ak):
            battle["actor_index"] = i
            battle["actor"] = ak
            return
    battle["actor"] = order[0] if order else ""


def _pvp_advance_actor_after_action(battle: Dict[str, Any]) -> None:
    order = battle.get("actor_order") or []
    if not order:
        return
    cur_i = int(battle.get("actor_index", 0) or 0) % len(order)
    for step in range(1, len(order) + 1):
        nxt = (cur_i + step) % len(order)
        ak = order[nxt]
        if _pvp_actor_alive(battle, ak):
            battle["actor_index"] = nxt
            battle["actor"] = ak
            return
    _pvp_refresh_current_actor(battle)


def _pvp_parse_actor_key(actor_key: str) -> Tuple[str, str, Optional[int]]:
    """返回 (side, 'hero'|'ally', ally_idx 或 None)。"""
    parts = str(actor_key).strip().split(":")
    if len(parts) != 2:
        return "", "", None
    side, slot = parts[0], parts[1]
    if side not in ("host", "guest"):
        return "", "", None
    if slot == "hero":
        return side, "hero", None
    if slot.startswith("p") and slot[1:].isdigit():
        return side, "ally", int(slot[1:])
    return "", "", None


def _pvp_side_fully_dead(battle: Dict[str, Any], side: str) -> bool:
    hero = battle.get(f"{side}_hero") or {}
    party = battle.get(f"{side}_party") or []
    if int(hero.get("hp", 0) or 0) > 0:
        return False
    for row in party:
        if int(row.get("hp", 0) or 0) > 0:
            return False
    return True


def _pvp_alive_actor_keys_for_side(battle: Dict[str, Any], side: str) -> List[str]:
    out: List[str] = []
    if _pvp_actor_alive(battle, f"{side}:hero"):
        out.append(f"{side}:hero")
    party = battle.get(f"{side}_party") or []
    for i in range(len(party)):
        if _pvp_actor_alive(battle, f"{side}:p{i}"):
            out.append(f"{side}:p{i}")
    return out


def _pvp_actor_effective_agi(battle: Dict[str, Any], actor_key: str) -> int:
    """PVP 先攻用 AGI：主角用快照面板；队友用 _effective_attrs_party_member（与战斗一致）。"""
    aside, akind, aidx = _pvp_parse_actor_key(actor_key)
    if not aside:
        return 1
    snap = battle.get("host_snap") if aside == "host" else battle.get("guest_snap")
    if not isinstance(snap, dict):
        return 1
    if akind == "hero":
        return max(1, int(snap.get("agi", 1) or 1))
    if akind == "ally" and aidx is not None:
        pm = snap.get("party") or []
        if 0 <= aidx < len(pm) and isinstance(pm[aidx], dict):
            ea = _effective_attrs_party_member(pm[aidx], None)
            return max(1, int(ea.get("agi", 1) or 1))
    return 1


def _pvp_actor_display_label(battle: Dict[str, Any], actor_key: str) -> str:
    """战报/先攻列表用短标签。"""
    aside, akind, aidx = _pvp_parse_actor_key(actor_key)
    if not aside:
        return actor_key
    hs = battle.get("host_snap") or {}
    gs = battle.get("guest_snap") or {}
    snap = hs if aside == "host" else gs
    tag = "房主" if aside == "host" else "挑战者"
    hn = str(snap.get("hero_name", "?"))
    if akind == "hero":
        return f"「{tag}」{hn}（主角）"
    if akind == "ally" and aidx is not None:
        pm = snap.get("party") or []
        if 0 <= aidx < len(pm) and isinstance(pm[aidx], dict):
            return f"「{tag}」{hn}·{pm[aidx].get('name', '队友')}"
    return actor_key


def _pvp_opponent_tag_from_prefix(prefix: str) -> str:
    """敌方 eid 前缀 h=guest / g=host 侧：战报里显示为 房主 / 挑战者。"""
    return "挑战者" if str(prefix or "") == "g" else "房主"


def _pvp_normalize_pvp_action_log_lines(
    logs: List[str],
    start_i: int,
    battle: Dict[str, Any],
    actor_req: str,
    my_snap: Dict[str, Any],
    akind: str,
    aidx: Optional[int],
    party_snap: Any,
) -> None:
    """将「柒步使用…」「王曦媛释放…」等裸名主语统一为 `_pvp_actor_display_label` 格式（与先攻列表一致）。"""
    disp = _pvp_actor_display_label(battle, actor_req)
    hn = str(my_snap.get("hero_name", "") or "").strip()
    cands: List[str] = []
    if hn:
        cands.append(hn)
    ps = party_snap if isinstance(party_snap, list) else []
    if akind == "ally" and isinstance(aidx, int) and 0 <= aidx < len(ps):
        pr = ps[aidx]
        if isinstance(pr, dict):
            pn = str(pr.get("name", "") or "").strip()
            if pn:
                cands.append(pn)
            if hn and pn:
                cands.append(f"{hn}·{pn}")
    cands = sorted(set([c for c in cands if c]), key=len, reverse=True)
    if not cands:
        return
    for i in range(start_i, len(logs)):
        s = str(logs[i])
        if s.startswith("▶ ") or s.startswith("  ·") or s.startswith("⚠️"):
            continue
        if s.startswith("「") and "」" in s[:12]:
            continue
        if s.startswith(disp):
            continue
        for bare in cands:
            if not bare or not s.startswith(bare):
                continue
            rest = s[len(bare) :]
            if not rest:
                break
            if not any(rest.startswith(v) for v in ("使用", "释放", "施放")):
                continue
            logs[i] = disp + rest
            break


def _pvp_actor_log_speak_label(battle: Dict[str, Any], actor_key: str) -> str:
    """PVP 战报中替换「你」的称谓：「房主/挑战者」+ 主角或队友名（不用裸名拼接）。"""
    aside, akind, aidx = _pvp_parse_actor_key(actor_key)
    if aside not in ("host", "guest"):
        return "你"
    tag = "房主" if aside == "host" else "挑战者"
    hs = battle.get("host_snap") or {}
    gs = battle.get("guest_snap") or {}
    snap = hs if aside == "host" else gs
    hn = str(snap.get("hero_name", "?"))
    if akind == "hero":
        return f"「{tag}」{hn}（主角）"
    if akind == "ally" and aidx is not None:
        pm = snap.get("party") or []
        if 0 <= aidx < len(pm) and isinstance(pm[aidx], dict):
            return f"「{tag}」{str(pm[aidx].get('name', '队友'))}"
    return _pvp_actor_display_label(battle, actor_key)


def dq_pvp_export_snapshot(state: Dict[str, Any]) -> Dict[str, Any]:
    """供创建/加入房间上传：含技能、属性、主角与队友当前战斗数值。"""
    _ensure_attrs(state)
    _recalc_player_from_equipment(state)
    ea = _effective_attrs(state)
    party_out: List[Dict[str, Any]] = []
    for m in state.get("party_members") or []:
        if not isinstance(m, dict):
            continue
        party_out.append(
            {
                "mid": str(m.get("mid", "")),
                "name": str(m.get("name", "队友")),
                "role": str(m.get("role", "warrior")),
                "level": int(m.get("level", 1) or 1),
                "attrs": dict(m.get("attrs") or {}),
                "talents": [str(t) for t in (m.get("talents") or [])],
                "equipped": copy.deepcopy(m.get("equipped") or {}),
                "hp": int(m.get("hp", 1) or 1),
                "max_hp": int(m.get("max_hp", 1) or 1),
                "mp": int(m.get("mp", 0) or 0),
                "max_mp": int(m.get("max_mp", 0) or 0),
                "atk": int(m.get("atk", 1) or 1),
                "def": int(m.get("def", 1) or 1),
                "mdef": int(m.get("mdef", 1) or 1),
                "agi": int(m.get("agi", 1) or 1),
                "skills": [str(x) for x in (m.get("skills") or []) if x],
            }
        )
    return {
        "hero_name": str(state.get("name", "勇者")),
        "level": int(state.get("level", 1) or 1),
        "role": str(state.get("role", "warrior")),
        "attrs": dict(state.get("attrs") or {}),
        "talents": [str(t) for t in (state.get("talents") or [])],
        "skills": [str(s) for s in (state.get("skills") or []) if s],
        "hp": int(state.get("hp", 1) or 1),
        "max_hp": int(state.get("max_hp", 1) or 1),
        "mp": int(state.get("mp", 0) or 0),
        "max_mp": int(state.get("max_mp", 1) or 1),
        "atk": int(state.get("atk", 1) or 1),
        "def": int(state.get("def", 1) or 1),
        "mdef": int(state.get("mdef", 1) or 1),
        "agi": int(ea.get("agi", 0) or 0),
        "dex": int(ea.get("dex", 0) or 0),
        "luk": int(ea.get("luk", 0) or 0),
        "int": int(ea.get("int", 0) or 0),
        "party": party_out,
        "hero_gender": str(state.get("hero_gender") or "男"),
    }


def _pvp_double_snap_hp_for_arena(snap: Dict[str, Any]) -> None:
    """PVP 入场：主角与队友的当前生命、生命上限翻倍（仅作用于本场快照）。"""
    mh = max(1, int(snap.get("max_hp", 1) or 1))
    h = max(0, int(snap.get("hp", mh) or mh))
    snap["max_hp"] = mh * 2
    snap["hp"] = min(mh * 2, h * 2)
    for p in snap.get("party") or []:
        if not isinstance(p, dict):
            continue
        pmh = max(1, int(p.get("max_hp", 1) or 1))
        ph = max(0, int(p.get("hp", pmh) or pmh))
        p["max_hp"] = pmh * 2
        p["hp"] = min(pmh * 2, ph * 2)


def dq_pvp_battle_init(host_snap: Dict[str, Any], guest_snap: Dict[str, Any]) -> Dict[str, Any]:
    """服务端房间 battle 字段：可变 HP/MP + 快照副本。"""
    hs = copy.deepcopy(host_snap)
    gs = copy.deepcopy(guest_snap)
    _pvp_double_snap_hp_for_arena(hs)
    _pvp_double_snap_hp_for_arena(gs)

    def _party_rows(snap: Dict[str, Any]) -> List[Dict[str, int]]:
        out: List[Dict[str, int]] = []
        for p in snap.get("party") or []:
            if not isinstance(p, dict):
                continue
            out.append(
                {
                    "hp": int(p.get("hp", 1) or 1),
                    "mp": int(p.get("mp", 0) or 0),
                }
            )
        return out

    battle: Dict[str, Any] = {
        "round": 1,
        "host_plan": None,
        "guest_plan": None,
        "last_initiative": [],
        "host_hero": {"hp": int(hs["hp"]), "mp": int(hs["mp"])},
        "guest_hero": {"hp": int(gs["hp"]), "mp": int(gs["mp"])},
        "host_party": _party_rows(hs),
        "guest_party": _party_rows(gs),
        "log": [
            "— 战斗开始 —",
            f"PVP：「{hs.get('hero_name', '?')}」 VS 「{gs.get('hero_name', '?')}」",
            "规则：每回合双方同时为本方所有存活单位选择普攻/技能/防守，双方均提交后按先攻依次结算。",
            "先攻值 = 掷骰 0～10 + 有效 AGI（与单机先手判定同一思路）。",
            "本场生命：双方主角与队友的 HP / MaxHP 已翻倍（竞技场加成）。",
        ],
        "result": None,
        "host_snap": hs,
        "guest_snap": gs,
        "host_defend_cd": 0,
        "guest_defend_cd": 0,
    }
    return battle


def _pvp_opponent_prefix(acting_side: str) -> str:
    return "g" if acting_side == "host" else "h"


def _pvp_make_enemy_row(
    eid: str,
    label_name: str,
    snap_row: Dict[str, Any],
    hp_now: int,
) -> Dict[str, Any]:
    return {
        "eid": eid,
        "mid": "pvp_target",
        "name": label_name,
        "hp": max(0, int(hp_now)),
        "max_hp": max(1, int(snap_row.get("max_hp", 1) or 1)),
        "def": max(0, int(snap_row.get("def", 1) or 1)),
        "mdef": max(0, int(snap_row.get("mdef", snap_row.get("def", 1)) or 1)),
        "agi": max(1, int(snap_row.get("agi", 10) or 10)),
        "level": max(1, int(snap_row.get("level", 1) or 1)),
        "effects": [],
    }


def _pvp_build_enemies(
    opp_snap: Dict[str, Any],
    opp_mut_hero: Dict[str, int],
    opp_mut_party: List[Dict[str, int]],
    prefix: str,
) -> List[Dict[str, Any]]:
    enemies: List[Dict[str, Any]] = []
    _tag = _pvp_opponent_tag_from_prefix(prefix)
    _ohn = str(opp_snap.get("hero_name", "对手"))
    hr = _pvp_make_enemy_row(
        f"{prefix}_hero",
        f"「{_tag}」{_ohn}（主角）",
        {
            "max_hp": opp_snap.get("max_hp"),
            "def": opp_snap.get("def"),
            "mdef": opp_snap.get("mdef", opp_snap.get("def")),
            "agi": opp_snap.get("agi"),
            "level": opp_snap.get("level"),
        },
        int(opp_mut_hero.get("hp", 0) or 0),
    )
    enemies.append(hr)
    party_snap = opp_snap.get("party") or []
    for i, p in enumerate(party_snap):
        if not isinstance(p, dict):
            continue
        if i >= len(opp_mut_party):
            break
        hp_i = int(opp_mut_party[i].get("hp", 0) or 0)
        ally_label = f"「{_tag}」{str(p.get('name', '队友'))}"
        enemies.append(
            _pvp_make_enemy_row(
                f"{prefix}_p{i}",
                ally_label,
                {
                    "max_hp": p.get("max_hp"),
                    "def": p.get("def"),
                    "mdef": p.get("mdef", p.get("def")),
                    "agi": p.get("agi"),
                    "level": p.get("level"),
                },
                hp_i,
            )
        )
    return enemies


def _pvp_build_party_allies(
    my_snap: Dict[str, Any],
    my_mut_party: List[Dict[str, int]],
) -> List[Dict[str, Any]]:
    allies: List[Dict[str, Any]] = []
    party_snap = my_snap.get("party") or []
    for i, p in enumerate(party_snap):
        if not isinstance(p, dict) or i >= len(my_mut_party):
            break
        mhp = int(p.get("max_hp", 1) or 1)
        mm = int(p.get("max_mp", 0) or 0)
        allies.append(
            {
                "mid": str(p.get("mid", f"ally{i}")),
                "name": str(p.get("name", "队友")),
                "role": str(p.get("role", "warrior")),
                "level": int(p.get("level", 1) or 1),
                "hp": int(my_mut_party[i].get("hp", 0) or 0),
                "max_hp": mhp,
                "mp": int(my_mut_party[i].get("mp", 0) or 0),
                "max_mp": mm,
                "atk": int(p.get("atk", 1) or 1),
                "def": int(p.get("def", 1) or 1),
                "mdef": int(p.get("mdef", 1) or 1),
                "agi": int(p.get("agi", 1) or 1),
                "skills": list(p.get("skills") or []),
                "effects": [],
            }
        )
    return allies


def _pvp_state_for_actor(my_snap: Dict[str, Any], hero_hp: int, hero_mp: int) -> Dict[str, Any]:
    attrs_copy = copy.deepcopy(my_snap.get("attrs") or {})
    _migrate_attrs_dict_inplace(attrs_copy)
    st: Dict[str, Any] = {
        "name": str(my_snap.get("hero_name", "勇者")),
        "role": str(my_snap.get("role", "warrior")),
        "level": int(my_snap.get("level", 1) or 1),
        "attrs": attrs_copy,
        "talents": list(my_snap.get("talents") or []),
        "skills": list(my_snap.get("skills") or []),
        "hp": int(hero_hp),
        "max_hp": int(my_snap.get("max_hp", 1) or 1),
        "mp": int(hero_mp),
        "max_mp": int(my_snap.get("max_mp", 1) or 1),
        "atk": int(my_snap.get("atk", 1) or 1),
        "def": int(my_snap.get("def", 1) or 1),
        "mdef": int(my_snap.get("mdef", my_snap.get("def", 1)) or 1),
        "agi": int(my_snap.get("agi", 1) or 1),
        "inventory": [],
        "meta": {},
        "party_members": [],
    }
    ea = st["attrs"]
    ea.setdefault("str", 0)
    ea.setdefault("int", int(my_snap.get("int", 0) or 0))
    ea.setdefault("dex", int(my_snap.get("dex", 0) or 0))
    ea.setdefault("agi", int(my_snap.get("agi", 0) or 0))
    ea.setdefault("luk", int(my_snap.get("luk", 0) or 0))
    ea.setdefault("vit", int(attrs_copy.get("vit", 1) or 1))
    return st


def _pvp_state_for_party_member(
    my_snap: Dict[str, Any], ally_idx: int, my_party: List[Dict[str, int]]
) -> Dict[str, Any]:
    party_snap = my_snap.get("party") or []
    if ally_idx < 0 or ally_idx >= len(party_snap):
        return {}
    p = party_snap[ally_idx]
    if not isinstance(p, dict):
        return {}
    m = my_party[ally_idx]
    raw_attrs = p.get("attrs") or {}
    st: Dict[str, Any] = {
        "name": str(p.get("name", "队友")),
        "role": str(p.get("role", "warrior")),
        "level": int(p.get("level", 1) or 1),
        "attrs": copy.deepcopy(raw_attrs),
        "talents": list(p.get("talents") or []),
        "skills": list(p.get("skills") or []),
        "equipped": copy.deepcopy(p.get("equipped") or {}),
        "hp": int(m.get("hp", 0) or 0),
        "max_hp": int(p.get("max_hp", 1) or 1),
        "mp": int(m.get("mp", 0) or 0),
        "max_mp": int(p.get("max_mp", 0) or 0),
        "atk": int(p.get("atk", 1) or 1),
        "def": int(p.get("def", 1) or 1),
        "mdef": int(p.get("mdef", p.get("def", 1)) or 1),
        "agi": int(p.get("agi", 1) or 1),
        "inventory": [],
        "meta": {},
        "party_members": [],
    }
    _ensure_member_attrs(st)
    return st


def _normalize_pvp_skill_id(raw: Any) -> str:
    """PVP 指令里的技能 id：去空白；支持误传中文技能名时反查 id。"""
    s = str(raw or "").strip()
    if not s:
        return ""
    cat = _skill_catalog()
    if s in cat:
        return s
    for sid, sk in cat.items():
        if getattr(sk, "name", None) == s:
            return sid
    return s


def _pvp_enemy_target_status(battle_syn: Dict[str, Any], target_id: Optional[str]) -> str:
    """当前战场中敌方 eid 状态：alive / dead / missing。"""
    tid = str(target_id or "").strip()
    if not tid:
        return "missing"
    for e in _alive_enemies(battle_syn):
        if str(e.get("eid")) == tid:
            return "alive"
    for e in battle_syn.get("enemies") or []:
        if isinstance(e, dict) and str(e.get("eid")) == tid:
            hp = int(e.get("hp", 0) or 0)
            return "dead" if hp <= 0 else "alive"
    return "missing"


def _pvp_make_pl_action(
    kind: str, action: Dict[str, Any], battle_syn: Dict[str, Any]
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if kind == "attack":
        tid = str(action.get("target_id") or "").strip()
        if not tid:
            return None, "请选择攻击目标"
        return {"kind": "attack", "target_id": tid}, None
    if kind == "defend":
        return {"kind": "defend", "defend_target": action.get("defend_target")}, None
    if kind == "skill":
        sid = _normalize_pvp_skill_id(action.get("sid"))
        if not sid:
            return None, "请选择技能"
        sk = _skill_catalog().get(sid)
        if sk is None:
            return None, f"未知技能：{sid}"
        tid = str(action.get("target_id") or "").strip()
        if sk.kind in ("damage", "double_slash", "quick_stab_chain", "drain"):
            if not tid:
                return None, "请选择目标"
            return {"kind": "skill", "sid": sid, "target_id": tid}, None
        alive = _alive_enemies(battle_syn)
        if not alive:
            return None, "没有可攻击目标"
        if not tid:
            tid = str(alive[0].get("eid") or "")
        return {"kind": "skill", "sid": sid, "target_id": tid}, None
    return None, "未知行动"


def _pvp_allies_for_ally_turn(
    my_snap: Dict[str, Any], my_hero: Dict[str, int], my_party: List[Dict[str, int]], ally_idx: int
) -> List[Dict[str, Any]]:
    hero_ally: Dict[str, Any] = {
        "mid": PVP_HERO_ALLY_MID,
        "name": str(my_snap.get("hero_name", "勇者")),
        "role": str(my_snap.get("role", "warrior")),
        "level": int(my_snap.get("level", 1) or 1),
        "hp": int(my_hero.get("hp", 0) or 0),
        "max_hp": int(my_snap.get("max_hp", 1) or 1),
        "mp": int(my_hero.get("mp", 0) or 0),
        "max_mp": int(my_snap.get("max_mp", 1) or 1),
        "atk": int(my_snap.get("atk", 1) or 1),
        "def": int(my_snap.get("def", 1) or 1),
        "mdef": int(my_snap.get("mdef", my_snap.get("def", 1)) or 1),
        "agi": int(my_snap.get("agi", 1) or 1),
        "skills": list(my_snap.get("skills") or []),
        "effects": [],
    }
    out: List[Dict[str, Any]] = [hero_ally]
    party_snap = my_snap.get("party") or []
    for j, p in enumerate(party_snap):
        if not isinstance(p, dict) or j >= len(my_party) or j == ally_idx:
            continue
        mhp = int(p.get("max_hp", 1) or 1)
        mm = int(p.get("max_mp", 0) or 0)
        out.append(
            {
                "mid": str(p.get("mid", f"ally{j}")),
                "name": str(p.get("name", "队友")),
                "role": str(p.get("role", "warrior")),
                "level": int(p.get("level", 1) or 1),
                "hp": int(my_party[j].get("hp", 0) or 0),
                "max_hp": mhp,
                "mp": int(my_party[j].get("mp", 0) or 0),
                "max_mp": mm,
                "atk": int(p.get("atk", 1) or 1),
                "def": int(p.get("def", 1) or 1),
                "mdef": int(p.get("mdef", p.get("def", 1)) or 1),
                "agi": int(p.get("agi", 1) or 1),
                "skills": list(p.get("skills") or []),
                "effects": [],
            }
        )
    return out


def _pvp_sync_after_hero_move(
    battle_syn: Dict[str, Any], my_hero: Dict[str, int], my_party: List[Dict[str, int]]
) -> None:
    my_hero["hp"] = int(battle_syn.get("player_hp", my_hero.get("hp", 1)) or 1)
    my_hero["mp"] = int(battle_syn.get("player_mp", my_hero.get("mp", 0)) or 0)
    for i, al in enumerate(battle_syn.get("allies") or []):
        if isinstance(al, dict) and i < len(my_party):
            my_party[i]["hp"] = int(al.get("hp", 0) or 0)
            my_party[i]["mp"] = int(al.get("mp", 0) or 0)


def _pvp_sync_after_ally_move(
    battle_syn: Dict[str, Any],
    my_snap: Dict[str, Any],
    ally_idx: int,
    my_hero: Dict[str, int],
    my_party: List[Dict[str, int]],
) -> None:
    if ally_idx < 0 or ally_idx >= len(my_party):
        return
    my_party[ally_idx]["hp"] = int(battle_syn.get("player_hp", 0) or 0)
    my_party[ally_idx]["mp"] = int(battle_syn.get("player_mp", 0) or 0)
    for al in battle_syn.get("allies") or []:
        if not isinstance(al, dict):
            continue
        mid = str(al.get("mid", "") or "")
        if mid == PVP_HERO_ALLY_MID:
            my_hero["hp"] = int(al.get("hp", 0) or 0)
            my_hero["mp"] = int(al.get("mp", 0) or 0)
            continue
        for j, p in enumerate(my_snap.get("party") or []):
            if not isinstance(p, dict) or j == ally_idx:
                continue
            if str(p.get("mid", "")) == mid and j < len(my_party):
                my_party[j]["hp"] = int(al.get("hp", 0) or 0)
                my_party[j]["mp"] = int(al.get("mp", 0) or 0)
                break


def _pvp_sync_enemies_to_mut(
    enemies: List[Dict[str, Any]],
    prefix: str,
    opp_snap: Dict[str, Any],
    opp_hero_mut: Dict[str, int],
    opp_party_mut: List[Dict[str, int]],
) -> None:
    for e in enemies:
        if not isinstance(e, dict):
            continue
        eid = str(e.get("eid") or "")
        hp = max(0, int(e.get("hp", 0) or 0))
        if eid == f"{prefix}_hero":
            opp_hero_mut["hp"] = hp
        elif eid.startswith(f"{prefix}_p"):
            idx_s = eid.split("_p", 1)[-1]
            try:
                idx = int(idx_s)
            except Exception:
                continue
            if 0 <= idx < len(opp_party_mut):
                opp_party_mut[idx]["hp"] = hp


def _pvp_all_opponents_dead(enemies: List[Dict[str, Any]]) -> bool:
    for e in enemies:
        if isinstance(e, dict) and int(e.get("hp", 0) or 0) > 0:
            return False
    return True


def _pvp_run_single_action(
    battle: Dict[str, Any],
    actor_key: str,
    action: Dict[str, Any],
    rng: random.Random,
) -> Tuple[List[str], Optional[str]]:
    """执行单个单位的 PVP 行动（不写入 battle['log']、不推进旧版 actor）。"""
    logs: List[str] = []
    if battle.get("result"):
        return [], "对战已结束"
    actor_req = str(actor_key or "").strip()
    aside, akind, aidx = _pvp_parse_actor_key(actor_req)
    if aside not in ("host", "guest"):
        return [], "无效行动单位"
    side = aside
    kind = str(action.get("kind") or "")
    if kind == "flee":
        return [], "PVP 中无法逃跑"
    if kind == "item":
        return [], "PVP 中无法使用背包物品"

    host_snap = battle.get("host_snap") or {}
    guest_snap = battle.get("guest_snap") or {}
    if not isinstance(host_snap, dict) or not isinstance(guest_snap, dict):
        return [], "数据损坏"

    my_snap = host_snap if side == "host" else guest_snap
    opp_snap = guest_snap if side == "host" else host_snap
    my_hero = battle["host_hero"] if side == "host" else battle["guest_hero"]
    opp_hero = battle["guest_hero"] if side == "host" else battle["host_hero"]
    my_party: List[Dict[str, int]] = battle["host_party"] if side == "host" else battle["guest_party"]
    opp_party: List[Dict[str, int]] = battle["guest_party"] if side == "host" else battle["host_party"]

    prefix = _pvp_opponent_prefix(side)

    if kind == "skill":
        sid0 = _normalize_pvp_skill_id(action.get("sid"))
        if sid0 in PVP_BLOCKED_SKILL_IDS:
            return [], "该技能在 PVP 中不可用（援护/战吼/盾反）"

    party_snap = my_snap.get("party") or []
    if akind == "ally":
        if aidx is None or aidx < 0 or aidx >= len(party_snap):
            return [], "队友位无效"
        if int(my_party[aidx].get("hp", 0) or 0) <= 0:
            return [], "该单位已无法行动"
    elif akind != "hero":
        return [], "无效行动单位"

    enemies = _pvp_build_enemies(opp_snap, opp_hero, opp_party, prefix)

    if akind == "hero":
        allies = _pvp_build_party_allies(my_snap, my_party)
        state = _pvp_state_for_actor(my_snap, int(my_hero.get("hp", 1)), int(my_hero.get("mp", 0)))
        state["party_members"] = allies
        battle_syn: Dict[str, Any] = {
            "enemy": enemies[0] if enemies else {},
            "enemies": enemies,
            "allies": allies,
            "player_hp": int(my_hero.get("hp", 1)),
            "player_max_hp": int(my_snap.get("max_hp", 1) or 1),
            "player_mp": int(my_hero.get("mp", 0)),
            "player_max_mp": int(my_snap.get("max_mp", 1) or 1),
            "player_atk": int(my_snap.get("atk", 1) or 1),
            "player_def": _incoming_def_effective_for_unit(
                str(my_snap.get("role", "warrior")), int(my_snap.get("def", 1) or 1)
            ),
            "player_mdef": _incoming_mdef_effective_for_unit(
                str(my_snap.get("role", "warrior")),
                int(my_snap.get("mdef", my_snap.get("def", 1)) or 1),
            ),
            "turn": 1,
            "result": None,
            "skill_cd": {},
            "cover_party_turns": 0,
            "taunt_pending_next_enemy": False,
            "taunt_active_this_enemy_phase": False,
            "shield_counter_active": False,
            "war_cry_turns": 0,
            "player_damage_taken_this_turn": 0,
            "next_enemy_damage_mult": 1.0,
            "defend_cd": int(battle.get(f"{side}_defend_cd", 0) or 0),
            "_pvp": True,
        }
        state["battle"] = battle_syn
    else:
        if aidx is None:
            return [], "队友位无效"
        state = _pvp_state_for_party_member(my_snap, aidx, my_party)
        if not state:
            return [], "队友数据无效"
        p_row = party_snap[aidx]
        if not isinstance(p_row, dict):
            return [], "队友数据无效"
        allies_bt = _pvp_allies_for_ally_turn(my_snap, my_hero, my_party, aidx)
        battle_syn = {
            "enemy": enemies[0] if enemies else {},
            "enemies": enemies,
            "allies": allies_bt,
            "player_hp": int(my_party[aidx].get("hp", 1)),
            "player_max_hp": int(p_row.get("max_hp", 1) or 1),
            "player_mp": int(my_party[aidx].get("mp", 0)),
            "player_max_mp": int(p_row.get("max_mp", 0) or 0),
            "player_atk": int(p_row.get("atk", 1) or 1),
            "player_def": _incoming_def_effective_for_unit(str(p_row.get("role", "warrior")), int(p_row.get("def", 1) or 1)),
            "player_mdef": _incoming_mdef_effective_for_unit(
                str(p_row.get("role", "warrior")),
                int(p_row.get("mdef", p_row.get("def", 1)) or 1),
            ),
            "turn": 1,
            "result": None,
            "skill_cd": {},
            "cover_party_turns": 0,
            "taunt_pending_next_enemy": False,
            "taunt_active_this_enemy_phase": False,
            "shield_counter_active": False,
            "war_cry_turns": 0,
            "player_damage_taken_this_turn": 0,
            "next_enemy_damage_mult": 1.0,
            "_pvp": True,
        }
        state["battle"] = battle_syn
        state["party_members"] = allies_bt

    def _post_move_sync() -> List[str]:
        """同步本方 HP/MP 与对方受伤表，并返回需追加的胜负提示行。"""
        out: List[str] = []
        battle_syn = state["battle"]
        if akind == "hero":
            _pvp_sync_after_hero_move(battle_syn, my_hero, my_party)
        else:
            _pvp_sync_after_ally_move(
                battle_syn, my_snap, aidx if aidx is not None else 0, my_hero, my_party
            )
        _pvp_sync_enemies_to_mut(
            list(battle_syn.get("enemies") or []),
            prefix,
            opp_snap,
            opp_hero,
            opp_party,
        )
        ens = list(battle_syn.get("enemies") or [])
        if _pvp_all_opponents_dead(ens):
            battle["result"] = "host_win" if side == "host" else "guest_win"
            wtag = "房主" if side == "host" else "挑战者"
            w = str(my_snap.get("hero_name", "勇者"))
            out.append(f"🏆 {wtag}「{w}」获胜！")
        elif _pvp_side_fully_dead(battle, "host"):
            battle["result"] = "guest_win"
            gn = str(guest_snap.get("hero_name", "挑战者"))
            out.append(f"🏆 挑战者「{gn}」获胜！")
        elif _pvp_side_fully_dead(battle, "guest"):
            battle["result"] = "host_win"
            hn = str(host_snap.get("hero_name", "房主"))
            out.append(f"🏆 房主「{hn}」获胜！")
        return out

    actor_label = _pvp_actor_log_speak_label(battle, actor_req)

    pl_action, err = _pvp_make_pl_action(kind, action, state["battle"])
    if err or pl_action is None:
        return [], err or "行动无效"

    pk = str(pl_action.get("kind") or "")
    if pk == "defend" and akind == "hero":
        rem = int(battle.get(f"{side}_defend_cd", 0) or 0)
        if rem > 0:
            return [], f"防守冷却中（剩余 {rem} 回合）"
    tid_chk = str(pl_action.get("target_id") or "").strip()
    if pk == "attack":
        st_t = _pvp_enemy_target_status(state["battle"], tid_chk)
        if st_t != "alive":
            logs.append(f"▶ {_pvp_actor_display_label(battle, actor_req)} 的行动")
            if st_t == "dead":
                logs.append(
                    f"⚠️ {_pvp_actor_display_label(battle, actor_req)}：攻击单位已阵亡，本次普攻未命中。"
                )
            else:
                logs.append(
                    f"⚠️ {_pvp_actor_display_label(battle, actor_req)}：攻击目标无效，本次普攻未命中。"
                )
            return logs, None
    elif pk == "skill":
        sid_pl = str(pl_action.get("sid") or "").strip()
        sk_pl = _skill_catalog().get(sid_pl)
        if sk_pl and sk_pl.kind in ("damage", "double_slash", "quick_stab_chain", "drain"):
            st_t = _pvp_enemy_target_status(state["battle"], tid_chk)
            if st_t != "alive":
                bs = state["battle"]
                pm0 = int(bs.get("player_mp", 0) or 0)
                cost = int(sk_pl.mp_cost or 0)
                if pm0 < cost:
                    return [], "MP不足，无法执行行动"
                bs["player_mp"] = pm0 - cost
                disp = _pvp_actor_display_label(battle, actor_req)
                logs.append(f"▶ {disp} 的行动")
                if st_t == "dead":
                    logs.append(
                        f"⚠️ {disp}：攻击单位已阵亡，「{sk_pl.name}」未命中（MP-{cost}）。"
                    )
                else:
                    logs.append(
                        f"⚠️ {disp}：攻击目标无效，「{sk_pl.name}」未命中（MP-{cost}）。"
                    )
                logs.extend(_post_move_sync())
                return logs, None

    logs.append(f"▶ {_pvp_actor_display_label(battle, actor_req)} 的行动")
    n0 = len(logs)
    _battle_player_move(state, pl_action, rng, logs)
    if akind == "hero" and pk == "defend":
        battle[f"{side}_defend_cd"] = int(PLAYER_DEFEND_COOLDOWN_TURNS)
    for i in range(n0, len(logs)):
        logs[i] = str(logs[i]).replace("你", actor_label)
    _pvp_normalize_pvp_action_log_lines(
        logs, n0, battle, actor_req, my_snap, str(akind), aidx, party_snap
    )

    logs.extend(_post_move_sync())

    return logs, None


def dq_pvp_submit_plans(
    battle: Dict[str, Any], side: str, plans: Dict[str, Any]
) -> Optional[str]:
    """校验并保存单方本回合指令表；键为 host:hero / host:p0 …"""
    if battle.get("result"):
        return "对战已结束"
    side = str(side or "")
    if side not in ("host", "guest"):
        return "无效阵营"
    need = set(_pvp_alive_actor_keys_for_side(battle, side))
    if not need:
        return "没有可行动单位"
    got = set(str(k) for k in (plans or {}).keys())
    if need != got:
        return f"须为每名存活单位各选一条指令（需要 {sorted(need)}）"
    for k, v in (plans or {}).items():
        if not isinstance(v, dict):
            return "指令格式错误"
        kind = str(v.get("kind") or "")
        if kind not in ("attack", "defend", "skill"):
            return f"未知行动：{kind}"
        if kind == "defend":
            ak = str(k)
            aside, akind, _ = _pvp_parse_actor_key(ak)
            if akind == "hero" and aside in ("host", "guest"):
                rem = int(battle.get(f"{aside}_defend_cd", 0) or 0)
                if rem > 0:
                    return f"「{ak}」防守冷却中（剩余 {rem} 回合），请改选其它行动"
    battle[f"{side}_plan"] = copy.deepcopy(plans)
    return None


def dq_pvp_resolve_round(battle: Dict[str, Any], rng: random.Random) -> Optional[str]:
    """双方指令均已提交时：按先攻依次结算。成功返回 None，否则错误说明。"""
    if battle.get("result"):
        return "对战已结束"
    hp = battle.get("host_plan")
    gp = battle.get("guest_plan")
    if not isinstance(hp, dict) or not isinstance(gp, dict):
        return None
    hk = set(_pvp_alive_actor_keys_for_side(battle, "host"))
    gk = set(_pvp_alive_actor_keys_for_side(battle, "guest"))
    if set(hp.keys()) != hk:
        return "房主指令与存活单位不一致"
    if set(gp.keys()) != gk:
        return "挑战者指令与存活单位不一致"

    all_keys = list(hk | gk)
    scored: List[Tuple[str, int, int, int]] = []
    for ak in all_keys:
        agi_v = _pvp_actor_effective_agi(battle, ak)
        roll = int(rng.randint(0, 10))
        sc = roll + agi_v
        scored.append((ak, sc, agi_v, roll))
    scored.sort(key=lambda x: (-x[1], -x[2], x[0]))

    rnd_n = int(battle.get("round", 1) or 1)
    battle.setdefault("log", []).append(f"════════ 第 {rnd_n} 回合 ════════")
    battle.setdefault("log", []).append("先攻顺序（掷骰 0～10 + 有效 AGI，数值高者优先出手）：")
    ini_log: List[Dict[str, Any]] = []
    for ak, sc, agi_v, roll in scored:
        lab = _pvp_actor_display_label(battle, ak)
        battle["log"].append(f"  · {lab}　先攻 {sc}（骰{roll} + AGI{agi_v}）")
        ini_log.append({"actor": ak, "score": sc, "agi": agi_v, "roll": roll})
    battle["last_initiative"] = ini_log

    merged: Dict[str, Dict[str, Any]] = {**copy.deepcopy(hp), **copy.deepcopy(gp)}
    for ak, _, _, _ in scored:
        if battle.get("result"):
            break
        act = merged.get(ak) or {}
        logs, err = _pvp_run_single_action(battle, ak, act, rng)
        if err:
            battle.setdefault("log", []).append(f"⚠️ {_pvp_actor_display_label(battle, ak)}：{err}")
            continue
        battle.setdefault("log", []).extend(logs)

    for _s in ("host", "guest"):
        _dk = f"{_s}_defend_cd"
        battle[_dk] = max(0, int(battle.get(_dk, 0) or 0) - 1)
    battle["host_plan"] = None
    battle["guest_plan"] = None
    battle["round"] = rnd_n + 1
    return None


def dq_pvp_apply_action(
    battle: Dict[str, Any],
    acting_side: str,
    action: Dict[str, Any],
    rng: random.Random,
) -> Tuple[Dict[str, Any], List[str], Optional[str]]:
    """
    单步行动（旧版接口）：与主线 _battle_player_move 共用伤害/技能公式。
    同步回合制下优先使用 submit + resolve_round。
    """
    logs: List[str] = []
    side = str(acting_side or "")
    if side not in ("host", "guest"):
        return battle, [], "无效阵营"
    if battle.get("result"):
        return battle, [], "对战已结束"

    actor_req = str(action.get("actor") or "").strip()
    cur_act = str(battle.get("actor") or "").strip()
    if cur_act and (not actor_req or actor_req != cur_act):
        return battle, [], "行动单位不匹配或已过期"

    aside, _, _ = _pvp_parse_actor_key(actor_req)
    if aside != side or not aside:
        return battle, [], "阵营与行动单位不一致"

    logs, err = _pvp_run_single_action(battle, actor_req, action, rng)
    if err:
        return battle, [], err
    battle.setdefault("log", []).extend(logs)
    if not battle.get("result"):
        _pvp_advance_actor_after_action(battle)
    return battle, [], None

