# app/crud/agent_session.py
# 目标与职责：Agent 会话记忆的 Mongo 持久化（agent_conversations，_id=sessionCode）。
# 纯 dict 访问，不 import agentscope——AgentState 转换在 adapter。
from datetime import datetime
from typing import Any

from app.core.database import get_db

# 定义集合
COLLECTION = "agent_conversations"


# 加载上下文
async def load_session_state(session_code: str) -> dict[str, Any] | None:
    """按 session_code 取已持久化的 AgentState dict；没有返回 None（新会话）。"""

    # 根据session_code获取对应的文档内容
    # find_one 的文档类型参数是 Any（get_db 返回 AsyncDatabase[Any]），
    # 显式注解在 crud 边界收口，后续 doc.get("state") 才有真实类型
    doc: dict[str, Any] | None = await get_db()[COLLECTION].find_one({"_id": session_code})

    if doc is None:
        return None

    # 将文档内容转换为 AgentState
    # doc.get 返回 Any | None，与 doc 同款显式注解收口，isinstance 收窄后才有干净的 dict[str, Any]
    state: dict[str, Any] | None = doc.get("state")

    return state if isinstance(state, dict) else None


# 保存上下文
async def save_session_state(session_code: str, state: dict[str, Any]) -> None:
    """全量覆盖保存（replace 而非 update：state 内部结构由框架定义，整存整取）。"""

    # upset=True：如果找到匹配文档，就用新文档替换它；如果没找到，就插入一条新文档
    _ = await get_db()[COLLECTION].replace_one(
        {"_id": session_code},
        {
            "_id": session_code,
            "updatedAt": datetime.now().isoformat(timespec="seconds"),
            "state": state,
        },
        upsert=True,
    )
