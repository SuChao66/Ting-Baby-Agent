# app/agent/prompt.py
# 目标与职责：ReActAgent 的系统提示词——基调/时间感知/月龄/写操作确认规范/免责话术。
# 纯字符串函数，不 import agentscope（agentscope 唯一收口在 adapter.py）。

# 场景话术：前端 scene 参数 -> 提示词角色微调（M5 的周报流程会扩展 weekly）
from datetime import datetime
from zoneinfo import ZoneInfo

# 业务时区唯一权威：用户/宝宝都在中国，提示词时间基准固定北京时间（不信服务器时区）
_CN_TZ = ZoneInfo("Asia/Shanghai")

# 静态文案段：基调
_BASE_TONE = (
    "你是「汀宝宝」育儿助手的对话大脑，服务一个家庭的婴幼儿养育场景。"
    "用温暖、简洁的简体中文口语回答，避免长篇大论；"
    "查数据靠工具，切记不要随意编造数据。"
)
# 写操作确认规范
_WRITE_CONFIRM_RULE = (
    "新增记录（身高体重/症状护理/吃喝拉撒睡）前，必须先用一句话向用户复述"
    "要写的内容（类型+关键数值+时间），得到确认（如「好的」「对」「是的」）后再调用写工具；"
    "一次只写一条，写完简短告知结果。查询类操作无需确认，直接执行。"
)
# 免责话术
_HEALTH_DISCLAIMER = (
    "涉及健康判断（发热、用药、异常大便等）时，只做信息整理与一般护理常识，"
    "并提醒用户必要时咨询医生；不做诊断，不推荐具体药物剂量。"
)
# 场景提示词
_SCENE_HINTS: dict[str, str] = {
    "record": "当前处于「记录」场景，用户可能想记一笔，主动确认要写的类型与内容。",
    "weekly": "当前处于「成长周报」场景，回答偏汇总分析，给出可执行的养育建议。",
    "insight": "当前处于「数据解读」场景，回答偏数据趋势解释，避免过度诊断。",
}


# 构建系统提示词
# baby_age: baby的年龄
# scene: 当前场景
def build_system_prompt(baby_age: str | None = None, scene: str | None = None) -> str:
    """组装系统提示词：固定基调 + 动态时间/月龄/场景。"""

    # 当前北京时间（含 +08:00 偏移，模型换算相对时间有明确锚点），精确到秒
    now = datetime.now(_CN_TZ).isoformat(timespec="seconds")
    parts: list[str] = [
        # 固定基调
        _BASE_TONE,
        f"当前时间是 {now}。「今天」「昨天」等相对时间以它为基准换算成绝对时间后再传给工具。",
    ]

    # 动态月龄
    if baby_age:
        parts.append(f"宝宝当前月龄：{baby_age}。育儿知识回答要贴合这个阶段。")
    # 动态场景
    if scene and scene in _SCENE_HINTS:
        parts.append(_SCENE_HINTS[scene])
    # 写操作规范
    parts.append(_WRITE_CONFIRM_RULE)
    # 健康声明
    parts.append(_HEALTH_DISCLAIMER)

    return "\n".join(parts)
