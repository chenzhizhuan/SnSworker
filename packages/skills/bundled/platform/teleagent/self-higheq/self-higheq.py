# -*- coding: utf-8 -*-
"""
高情商聊天回复助手
版本：2026.9.3
功能：人设记忆 / 快捷切换 / 三种聊天模式 / 关系自动识别 / 多备选回复
说明：纯本地技能，无外部依赖，记忆随会话传递。
"""

# ===== 内置人设与模式清单 =====

# 可用人设列表（顺序即快捷指令匹配优先级）
PERSONAS = [
    "温柔高情商", "甜妹", "奶狗", "御姐", "拽姐", "斯文",
    "直男", "搞笑沙雕", "清醒怼人", "高冷", "文艺走心", "社交达人",
]

# 三种聊天模式
MODES = {
    "normal": "普通模式",
    "flirt":  "暧昧拉扯模式",
    "blind":  "相亲专用模式",
}

# 违规关键词，命中后直接拦截，不进入回复生成
FORBIDDEN_KEYWORDS = [
    "黄", "暴", "血腥", "辱骂", "自杀", "自残", "违法", "诈骗",
    "网暴", "恶意", "攻击", "色情", "低俗", "极端",
]


def _match_persona_switch(text):
    """
    判断输入是否为「切换人设」指令。
    支持三类说法：换成X / 切换成X / 改成X。
    命中返回对应人设名，否则返回 None。
    """
    for persona in PERSONAS:
        for verb in ("换成", "切换成", "改成"):
            if f"{verb}{persona}" in text:
                return persona
    return None


def _match_mode_switch(text):
    """
    判断输入是否为「切换模式」指令。
    命中返回目标模式中文名，否则返回 None。
    """
    if "暧昧模式" in text or "开启暧昧" in text:
        return MODES["flirt"]
    if "相亲模式" in text or "相亲专用" in text:
        return MODES["blind"]
    if "普通模式" in text or "正常聊天" in text:
        return MODES["normal"]
    return None


def _is_forbidden(text):
    """命中违规关键词返回 True，否则 False。"""
    return any(kw in text for kw in FORBIDDEN_KEYWORDS)


def build_reply(text, persona, mode):
    """
    依据当前人设与模式，组织一段回复模板。
    实际多备选回复由智能体在本框架下展开生成。
    """
    return (
        f"当前模式：{mode}\n"
        f"当前人设：{persona}\n"
        f"关系判断：自动识别\n"
        f"对话场景：智能分析\n"
        f"推荐回复：\n"
        f"1. 自然口语化回复，可直接复制\n"
        f"2. 贴合人设与关系，不尴尬不越界\n"
        f"3. 高情商、有分寸、舒适不油腻"
    )


def get_response(user_input, memory_data):
    """
    核心处理函数。
    入参：
        user_input  —— 用户本轮输入文本
        memory_data —— 会话记忆字典，携带人设与模式
    返回：
        (reply_text, updated_memory)
    """
    # 1. 从记忆中取出当前人设与模式，缺省用默认值
    persona = memory_data.get("user_persona", "温柔高情商")
    mode = memory_data.get("chat_mode", "普通模式")

    text = user_input.strip()

    # 2. 模式切换指令优先处理
    new_mode = _match_mode_switch(text)
    if new_mode is not None:
        memory_data["chat_mode"] = new_mode
        memory_data["user_persona"] = persona
        return f"✅ 已切换：{new_mode}", memory_data

    # 3. 人设切换指令
    new_persona = _match_persona_switch(text)
    if new_persona is not None:
        memory_data["user_persona"] = new_persona
        memory_data["chat_mode"] = mode
        return f"✅ 人设已切换：{new_persona}", memory_data

    # 4. 安全过滤：违规内容直接拦截
    if _is_forbidden(text):
        return "内容包含不当/违规信息，无法为你提供回复，请更换健康合规的话题。", memory_data

    # 5. 正常回复：写入记忆并返回模板
    memory_data["user_persona"] = persona
    memory_data["chat_mode"] = mode
    return build_reply(text, persona, mode), memory_data


def main(params):
    """
    技能统一入口。
    入参 params 为字典，约定字段：
        query  —— 用户输入文本
        memory —— 会话记忆字典
    返回字典，含 reply 与 memory 两个字段。
    """
    user_input = params.get("query", "")
    memory = params.get("memory", {})
    reply, updated_memory = get_response(user_input, memory)
    return {
        "reply": reply,
        "memory": updated_memory,
    }


# 直接运行时的简易自测
if __name__ == "__main__":
    mem = {}
    for sample in ["换成甜妹", "暧昧模式", "在吗，今天干嘛了", "换个色情话题"]:
        out, mem = get_response(sample, mem)
        print(f"输入：{sample}")
        print(out)
        print("-" * 40)
