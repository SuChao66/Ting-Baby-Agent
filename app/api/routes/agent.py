# app/api/routes/agent.py
# 目标与职责：AI 对话端点——POST /api/v1/ai/chat/stream（SSE，对齐前端现有路径）

import json
from typing import Any, ClassVar

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from app.agent.adapter import chat_once, create_agent, stream_chat
from app.api.deps import RawTokenDep, UserDep
from app.core.logger import get_logger
from app.schemas.response import ApiResponse

logger = get_logger(__name__)

# 实例化路由
agent_router = APIRouter(tags=["agent"])


# 入参类型
class AIChatIn(BaseModel):
    """前端 IAiChatParams 的 Python 镜像：camelCase 别名对齐 JSON 契约。"""

    # `populate_by_name=True`：支持同时用【字段本名】和【alias 别名】来给模型赋值
    # ClassVar 注解：类级配置不随实例变（M1 config.py 同款惯例）
    model_config: ClassVar[ConfigDict] = ConfigDict(populate_by_name=True)

    question: str = Field(min_length=1, max_length=2000)
    session_code: str = Field(alias="sessionCode", min_length=1, max_length=100)
    req_id: str = Field(alias="reqId", min_length=1, max_length=100)
    scene: str | None = None
    baby_age: str | None = Field(alias="babyAge", default=None, max_length=20)
    history: list[dict[str, str]] = []


# SSE 帧
def _sse_frame(payload: dict[str, Any]) -> str:
    """一条 SSE 帧：data: <json>\n\n（与前端 parseSSEMessage 的按行解析对齐）。"""

    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# 流式问答接口
@agent_router.post("/api-ai/v1/ai/chat/stream", summary="AI 对话流式")
async def chat_stream(body: AIChatIn, user: UserDep, token: RawTokenDep) -> StreamingResponse:
    """流式问答：事件翻译后的载荷 dict -> SSE 帧，结束发 [DONE]。"""

    agent = await create_agent(
        user_id=user.id,
        token=token,
        session_code=body.session_code,
        baby_age=body.baby_age,
        scene=body.scene,
        history=body.history,
    )

    # 生成器
    async def gen():
        async for payload in stream_chat(agent, body.question, user_id=user.id, req_id=body.req_id):
            # 发送流式帧
            yield _sse_frame(payload)
        # 发送结束帧
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        # X-Accel-Buffering: no：告诉 nginx 别缓冲这个响应——SSE 部署（M6）时没有这个头，
        # 增量会被 nginx 攒成一坨一次性吐出，前端看起来「不流式」。
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# 非流式问答
@agent_router.post(
    "/api-ai/v1/ai/chat", response_model=ApiResponse[dict[str, Any]], summary="AI 对话非流式"
)
async def chat(body: AIChatIn, user: UserDep, token: RawTokenDep) -> ApiResponse[dict[str, Any]]:
    """非流式问答：同一 adapter 核心，聚合文本返回 {answer}。"""

    agent = await create_agent(
        user_id=user.id,
        token=token,
        session_code=body.session_code,
        baby_age=body.baby_age,
        scene=body.scene,
        history=body.history,
    )

    answer: str = await chat_once(
        agent,
        body.question,
        user_id=user.id,
        req_id=body.req_id,
    )

    return ApiResponse(data={"answer": answer})
