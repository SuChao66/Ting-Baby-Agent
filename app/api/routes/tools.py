# app/api/routes/tools.py
# 目标与职责：白名单分发的读工具调试入口，仅 local 环境挂载。

from inspect import signature
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends

from app.api.deps import RawTokenDep, get_current_user
from app.core.exceptions import BizException, NotFoundException
from app.core.logger import get_logger
from app.core.security import TokenPayload
from app.schemas.response import ApiResponse, ok
from app.tools.registry import READ_TOOLS, WRITE_TOOLS

logger = get_logger(__name__)
router = APIRouter(prefix="/tools", tags=["tools-debug"])


@router.get(
    "/read/{tool_name}",
    response_model=ApiResponse[list[dict[str, Any]] | dict[str, Any]],
)
async def call_read_tool(
    tool_name: str,
    user: Annotated[TokenPayload, Depends(get_current_user)],
    baby_id: str | None = None,
    record_type: str | None = None,
    milestone_only: bool = False,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> ApiResponse[list[dict[str, Any]] | dict[str, Any]]:
    """白名单分发：只执行 READ_TOOLS 里注册过的工具。

    参数按工具函数的实际签名过滤后传入——这正是 M4 AgentScope Toolkit
    注册工具时做的事：看签名决定能传什么。
    """

    fn = READ_TOOLS.get(tool_name)
    if fn is None:
        raise NotFoundException(f"找不到名为 {tool_name} 的读工具")

    # 候选参数的精确类型：字符串/布尔/整数/None，避免值类型退化为 Any
    candidates: dict[str, str | bool | int | None] = {
        "user_id": user.id,
        "baby_id": baby_id,
        "record_type": record_type,
        "milestone_only": milestone_only,
        "start": start,
        "end": end,
        "limit": limit,
    }
    # 工具要什么才传什么：按工具函数的形参名过滤候选参数
    params = signature(fn).parameters
    kwargs: dict[str, str | bool | int | None] = {}
    for k, v in candidates.items():
        if k in params:
            kwargs[k] = v
    # ToolFunc 的返回类型声明为 Awaitable[Any]，此处按读工具的真实合同显式断言收窄
    data = cast(list[dict[str, Any]] | dict[str, Any], await fn(**kwargs))

    return ok(data)


@router.post(
    "/write/{tool_name}",
    response_model=ApiResponse[dict[str, Any]],
    summary="写工具调试：按白名单分发（仅 local 环境）",
)
async def debug_write_tool(
    tool_name: str,
    payload: dict[str, Any],
    user: Annotated[TokenPayload, Depends(get_current_user)],
    token: RawTokenDep,
) -> ApiResponse[dict[str, Any]]:
    """写工具冒烟入口：body 为工具参数的 JSON 对象（snake_case），结果包 envelope。"""
    fn = WRITE_TOOLS.get(tool_name)
    if fn is None:
        raise NotFoundException(f"write tool '{tool_name}' not found")

    # 保留参数服务端注入：body 里同名的 user_id/token 一律忽略，防身份伪造
    injected = {"user_id": user.id, "token": token}
    kwargs = {k: v for k, v in payload.items() if k not in injected}
    unknown = [k for k in kwargs if k not in signature(fn).parameters]
    if unknown:
        raise BizException(message=f"未知参数: {', '.join(unknown)}")

    try:
        data = await fn(**kwargs, **injected)
    except TypeError as exc:
        raise BizException(message=f"工具参数错误: {exc}") from exc

    logger.info("写工具调试 %s baby相关写入完成", tool_name)
    return ApiResponse(data=data)
