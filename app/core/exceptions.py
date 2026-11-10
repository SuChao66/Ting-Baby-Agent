# app/core/exceptions.py
# 目标与职责：定义两个业务异常 + 注册四类全局处理器。核心规则照搬 backend 的两种返回模式
# （见总览 0.3）：业务错误 HTTP 200 + body.code；鉴权错误 HTTP 401

from typing import Literal

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# 导入日志
from app.core.logger import get_logger

# 导入响应
from app.schemas.response import ResponseCode, fail

# __name__ 会被替换成当前文件的模块路径，意思是：用当前模块名创建一个日志记录器
logger = get_logger(__name__)


class BizException(Exception):
    """业务异常基类,参数错误：HTTP 200 + body.code(对齐 backend res.json(Response.error(...))）"""

    message: str
    code: int

    def __init__(self, message: str = "业务处理失败", code: int = ResponseCode.BAD_REQUEST):
        self.message = message
        self.code = code
        super().__init__(message)


# 未登录异常
class UnauthorizedException(BizException):
    """鉴权错误：HTTP 401 + body.code=401（对齐 backend res.status(401).json(...)）。"""

    def __init__(self, message: str = "未授权，请先登录"):
        super().__init__(message=message, code=ResponseCode.UNAUTHORIZED)


# 禁止越权异常
class ForbiddenException(BizException):
    """权限不足：业务层拒绝（如访问非自己宝宝的记录）。HTTP 200 + body.code=403"""

    def __init__(self, message: str = "无权访问"):
        super().__init__(message=message, code=ResponseCode.FORBIDDEN)


# 未发现异常404
class NotFoundException(BizException):
    """未找到资源：HTTP 200 + body.code=404（对齐 backend res.status(404).json(...)）。"""

    def __init__(self, message: str = "资源不存在"):
        super().__init__(message=message, code=ResponseCode.NOT_FOUND)


# 自定义HTTP响应
def _envelope(code: int, message: str, http_status: int) -> JSONResponse:
    """封装响应体。"""
    return JSONResponse(
        status_code=http_status,  # 设置http的状态码
        content=fail(
            code=code, message=message
        ).model_dump(),  # model_dump:把模型实例转成普通字典，方便序列化成 JSON
    )


# 注册全局异常处理器
def register_exception_handlers(app: FastAPI) -> None:
    """注册全局异常处理器。 在 main.py 里调用一次, 统一把各类异常包成 envelope。"""

    @app.exception_handler(BizException)
    async def biz_handler(request: Request, exc: BizException) -> JSONResponse:
        # 子类 UnauthorizedException 也走这里，靠 isinstance 区分 HTTP 状态
        http_status: Literal[200, 401] = (
            status.HTTP_401_UNAUTHORIZED
            if isinstance(exc, UnauthorizedException)
            else status.HTTP_200_OK
        )
        logger.info(
            "业务异常 %s %s -> code=%s %s", request.method, request.url.path, exc.code, exc.message
        )
        return _envelope(code=exc.code, message=exc.message, http_status=http_status)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        # FastAPI 参数校验失败默认 422；对齐 backend：body.code=PARAM_ERROR(430)
        # 校验详情进日志（哪个字段/什么错），排查调试路由 422 不用猜
        logger.warning("参数校验失败 %s %s -> %s", request.method, request.url.path, exc.errors())
        return _envelope(ResponseCode.PARAM_ERROR, "参数校验失败", status.HTTP_200_OK)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # 框架级错误（路由不存在 404、方法不允许 405 等）：状态码镜像
        logger.warning("HTTP 异常 %s %s -> %s", request.method, request.url.path, exc.status_code)
        return _envelope(exc.status_code, str(exc.detail), exc.status_code)

    @app.exception_handler(Exception)
    async def fallback_handler(request: Request, exc: Exception) -> JSONResponse:
        # 兜底 500：完整堆栈进日志，响应只给通用文案，不外泄内部细节
        logger.exception("未处理异常 %s %s", request.method, request.url.path)
        return _envelope(ResponseCode.SERVER_ERROR, "error", status.HTTP_500_INTERNAL_SERVER_ERROR)
