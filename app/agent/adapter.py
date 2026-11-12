# app/agent/adapter.py
# 目标与职责：AgentScope 2.0 唯一 import 收口层——模型/工具/Agent 组装 + 流式事件翻译。
# 对外只暴露框架无关接口：create_agent 返回 Agent，stream_chat 产出 SSE 载荷 dict。

# inspect: 内省函数签名（按签名决定注入哪些身份参数）
import inspect

# AsyncIterator: 异步迭代器抽象基类
from collections.abc import AsyncIterator

# partial: 偏函数, 用来固定函数的一部分参数 / 关键字参数，生成新函数
from functools import partial
from typing import Any

from agentscope.agent import Agent, ReActConfig
from agentscope.credential import DeepSeekCredential
from agentscope.event import (
    ReplyEndEvent,
    ReplyFinishedReason,
    TextBlockDeltaEvent,
)
from agentscope.message import (
    AssistantMsg,  # pyright: ignore[reportUnknownVariableType]
    TextBlock,
    ToolCallState,
    ToolResultBlock,
    ToolResultState,
    UserMsg,  # pyright: ignore[reportUnknownVariableType]
)
from agentscope.model import DeepSeekChatModel
from agentscope.permission import PermissionBehavior, PermissionDecision
from agentscope.state import AgentState
from agentscope.tool import FunctionTool, ToolBase, Toolkit

from app.agent.prompts import build_system_prompt
from app.core.config import settings
from app.core.logger import get_logger
from app.crud.agent_session import load_session_state, save_session_state
from app.tools.registry import READ_TOOLS, WRITE_TOOLS, ToolFunc

logger = get_logger(__name__)

# 读 + 写工具全集：一个白名单视图，注册顺序即给模型的工具顺序
ALL_TOOLS: dict[str, ToolFunc] = {**READ_TOOLS, **WRITE_TOOLS}

# ReAct 超限降级文案（总计划 6.2：超限不报错，给台阶）
FALLBACK_TEXT = "这个问题有点绕，我捋一下思路，请换个问法再试试～"
# Agent error文案
ERROR_TEXT = "汀宝宝大脑开小差了，请稍后再试"

# Agent 名字：写入 context 消息的 name，恢复会话时按它识别自家消息
AGENT_NAME = "汀宝宝助手"

# 工具权限决策：AgentScope 的 FunctionTool 默认 check_permissions 返回 ASK
# （等外部 UserConfirmResultEvent 人工确认），SSE 服务端没有确认回路，
# 工具调用会永久挂在 asking 状态不执行——必须显式放行。
# 白名单注册即信任（越权防线在工具内 resolve_baby_ids + writers 出口），放行到此为止；
# 写操作的确认规范由系统提示词在对话层负责（复述 -> 用户确认 -> 才调写工具）。
_TOOL_PERMISSION = PermissionDecision(
    behavior=PermissionBehavior.ALLOW,
    message="汀宝宝服务端白名单工具，注册即放行",
)


# 注册工具
def _build_toolkit(user_id: str, token: str) -> Toolkit:
    """业务工具 -> FunctionTool 包装，身份凭证按位置注入，LLM 只见业务参数。"""

    # list 是不变容器：list[FunctionTool] 塞不进形参 list[ToolBase]，
    # 先声明 list[ToolBase] 再逐个 append（Toolkit.add_tool 是 async 的，同步函数里用不了）
    tools: list[ToolBase] = []

    def _wrap(name: str, fn: ToolFunc, *, read_only: bool) -> None:
        # 位置绑定注入身份：positional 绑定的参数会从签名移除（schema 干净），
        # keyword 绑定只会挂默认值、参数残留进 LLM schema。
        # 约定 user_id 恒为第一形参，writers 的 token 恒为第二，校验防新增工具排错位
        params = list(inspect.signature(fn).parameters)
        if params[0] != "user_id":
            raise ValueError(f"工具 {name} 第一形参必须是 user_id，实际是 {params[0]}")
        if "token" in params and params[1] != "token":
            raise ValueError(f"工具 {name} 第二形参必须是 token，实际是 {params[1]}")
        bound: tuple[str, ...] = (user_id, token) if "token" in params else (user_id,)
        # is_read_only：读工具并发安全，调度器可并行执行多个读调用
        tools.append(
            FunctionTool(
                func=partial(fn, *bound),
                name=name,
                is_read_only=read_only,
                permission=_TOOL_PERMISSION,
            )
        )

    for name, fn in READ_TOOLS.items():
        _wrap(name, fn, read_only=True)
    for name, fn in WRITE_TOOLS.items():
        _wrap(name, fn, read_only=False)

    return Toolkit(tools=tools)


# 模型客户端
def _build_model() -> DeepSeekChatModel:
    """每请求构造模型客户端（轻对象）；默认 stream=True + DeepSeekChatFormatter。"""

    return DeepSeekChatModel(
        credential=DeepSeekCredential(api_key=settings.deepseek_api_key),
        model=settings.deepseek_model,
    )


# 处理history历史信息（上下文）
def _seed_context(history: list[dict[str, str]]) -> list[Any]:
    """前端带来的历史轮次 -> 上下文消息（服务端无此会话记忆时播种，覆盖历史回填场景）。"""

    msgs: list[Any] = []

    for item in history:
        question: str = item.get("question", "")
        answer: str = item.get("answer", "")

        if question:
            msgs.append(UserMsg(name="user", content=question))
        if answer:
            msgs.append(
                AssistantMsg(name="assistant", content=[TextBlock(type="text", text=answer)])
            )

    return msgs


# 修复旧会话悬空工具调用
def _heal_awaiting_tool_calls(state: AgentState, agent_name: str) -> None:
    """给恢复会话尾部悬空的工具调用补收尾结果。

    历史会话可能因断流/权限挂起留下没有 tool_result 的 tool_call——
    AgentScope 恢复后检测到 awaiting 调用会直接拒绝续聊（要求先喂确认事件），
    直接发给模型也会违反「tool_call 后必有 tool_result」的消息序列。
    这里原地补一条 INTERRUPTED 结果：序列合法化，模型也知道该调用没执行。
    """

    if not state.context:
        return
    last = state.context[-1]
    if last.role != "assistant" or last.name != agent_name:
        return

    result_ids = {b.id for b in last.get_content_blocks("tool_result")}
    for call in last.get_content_blocks("tool_call"):
        if call.id in result_ids:
            continue
        call.state = ToolCallState.FINISHED
        last.content.append(
            ToolResultBlock(
                id=call.id,  # formatter 以此回填 tool_call_id
                name=call.name,
                output="该工具调用因会话中断未执行，结果未知；如用户问及相关数据请重新调用工具查询。",
                state=ToolResultState.INTERRUPTED,
            )
        )


# 创建agent
async def create_agent(
    user_id: str,
    token: str,
    session_code: str,
    baby_age: str | None = None,
    scene: str | None = None,
    history: list[dict[str, str]] | None = None,
) -> Agent:
    """每请求组装一个 ReActAgent：记忆加载/播种 + 凭证注入 + 系统提示词。"""

    # 加载 session state
    saved = await load_session_state(session_code)
    if saved is not None:
        state = AgentState.model_validate(saved)  # 老会话：整存整取恢复
        _heal_awaiting_tool_calls(state, agent_name=AGENT_NAME)
    else:
        state = AgentState(session_id=session_code, context=_seed_context(history or []))

    _agent = Agent(
        name=AGENT_NAME,
        system_prompt=build_system_prompt(baby_age=baby_age, scene=scene),
        model=_build_model(),
        toolkit=_build_toolkit(user_id=user_id, token=token),
        state=state,
        react_config=ReActConfig(max_iters=settings.agent_max_iters),
    )

    return _agent


# 错误的payload
def _error_payload(message: str, code: int = 500) -> dict[str, Any]:
    """前端 envelope 的错误帧形态：code!=0 -> parseSSEMessage 转 errorMessage。"""

    return {"code": code, "message": message, "data": None}


# 正常的payload
def _delta_payload(text: str) -> dict[str, Any]:
    """前端 envelope 的增量帧形态：data.content 为文本增量。"""

    return {"code": 0, "message": "success", "data": {"content": text}}


# 流式问答接口
async def stream_chat(agent: Agent, question: str) -> AsyncIterator[dict[str, Any]]:
    """跑一轮 ReAct 并翻译事件流：产出 SSE 载荷 dict（增量帧/错误帧）。

    职责边界：本函数结束前把 agent.state 持久化；SSE 帧封装（data: 前缀、[DONE]）在路由层。
    """

    try:
        async for evt in agent.reply_stream(inputs=UserMsg(name="user", content=question)):
            if isinstance(evt, TextBlockDeltaEvent):
                delta: str = evt.delta
                if delta:
                    yield _delta_payload(delta)
            elif isinstance(evt, ReplyEndEvent):
                if evt.finished_reason == ReplyFinishedReason.EXCEED_MAX_ITERS:
                    # 护栏超限：给降级文案，正常收尾
                    logger.warning("ReAct 超限 session=%s", agent.state.session_id)
                    yield _delta_payload(FALLBACK_TEXT)
                elif evt.finished_reason == ReplyFinishedReason.ERROR:
                    # 服务端错误：给错误码，正常收尾
                    logger.error("ReAct 错误 session=%s", agent.state.session_id)
                    yield _error_payload(ERROR_TEXT)
                    return
        # 正常收尾：全量持久化（含本轮用户消息 + 回复 + 工具痕迹）
        # mode="json"：枚举/UUID/datetime 转 JSON 原生类型，BSON 才能编码（python 模式保留
        # PermissionMode 枚举实例，replace_one 直接抛 InvalidDocument——每轮收尾必炸）
        await save_session_state(
            agent.state.session_id,
            agent.state.model_dump(mode="json"),
        )
    except Exception:
        # 模型断流/网络异常等：兜成业务错误帧，不让 SSE 以 500 堆栈断掉
        logger.exception("Agent 回复异常 session=%s", agent.state.session_id)
        yield _error_payload(ERROR_TEXT)


# 非流式问答
async def chat_once(agent: Agent, question: str) -> str:
    """非流式：复用同一事件流，聚合全部文本（POST /api/v1/ai/chat 的 answer）。"""

    text: str = ""

    try:
        async for evt in agent.reply_stream(inputs=UserMsg(name="user", content=question)):
            if isinstance(evt, TextBlockDeltaEvent) and evt.delta:
                text += evt.delta
            elif isinstance(evt, ReplyEndEvent):
                if evt.finished_reason == ReplyFinishedReason.EXCEED_MAX_ITERS:
                    text += FALLBACK_TEXT
                elif evt.finished_reason == ReplyFinishedReason.ERROR:
                    # 服务端错误：与 stream_chat 同语义，raise 交给全局异常处理器转错误 envelope
                    logger.error("ReAct 错误 session=%s", agent.state.session_id)
                    raise RuntimeError(ERROR_TEXT)
        # 正常收尾：全量持久化（含本轮用户消息 + 回复 + 工具痕迹）
        await save_session_state(
            agent.state.session_id,
            agent.state.model_dump(mode="json"),
        )
    except Exception:
        # 模型断流/网络异常等：兜成业务错误帧，不让 SSE 以 500 堆栈断掉
        logger.exception("Agent 回复异常 session=%s", agent.state.session_id)
        raise

    return text
