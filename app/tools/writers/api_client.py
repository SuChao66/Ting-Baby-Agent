# app/tools/writers/api_client.py
# 目标与职责：汀宝宝 Node REST 客户端——全项目唯一的 HTTP 写出口。
# JWT 头注入、超时、三种失败形态（HTTP 401 / HTTP 400 / HTTP 200+code!=0）翻译成现有异常体系。

from typing import Any, cast

import httpx

from app.core.config import settings
from app.core.exceptions import BizException, ForbiddenException, UnauthorizedException
from app.core.logger import get_logger
from app.schemas.response import ResponseCode

logger = get_logger(__name__)

# 写操作是用户在对话里等结果，总超时 10 秒、连接 5 秒——超了就翻译成「服务暂不可用」
TIMEOUT = httpx.Timeout(10.0, connect=5.0)

# 进程内唯一的 HTTP 客户端：None 表示未初始化（异步任务，防止高并发下同步阻塞）
_client: httpx.AsyncClient | None = None

# 初始化node api client
def init_node_api_client() -> httpx.AsyncClient:
    """ 创建 httpx 客户端（幂等，与 init_mongo 同模式）。 """
    global _client

    if _client is not None:
        return _client

    _client = httpx.AsyncClient(
        base_url=settings.node_api_base_url,
        timeout=TIMEOUT 
    )
    logger.info("Node API 客户端已初始化 base_url=%s", settings.node_api_base_url)

    return _client


# 关闭 node api client
async def close_node_api_client() -> None:
    """ 关闭 httpx 客户端，释放连接池。 """
    global _client
    
    if _client is not None:
        # AsyncClient 的关闭方法是 aclose：close() 只属于同步的 httpx.Client
        await _client.aclose()
        _client = None
        logger.info("Node API 客户端已关闭")


# 提取message
def _message_of(body: dict[str, Any]) -> str:
    """ 从 Node 响应体提取 message，取不到给兜底文案（不让空串冒充错误说明）。 """

    message = body.get("message")

    if isinstance(message, str) and message.strip():
        return message.strip()
    
    return '操作失败，请稍后再试'


# 翻译 HTTP 状态码
def _translate_status(status_code: int, body: dict[str, Any]) -> None:
    """ 非 HTTP 200 的两种形态：401 鉴权、其余（400 参数校验等）按 code 映射业务异常。 """

    if status_code == ResponseCode.UNAUTHORIZED:
        # token 过期/无效：UnauthorizedException 走 HTTP 401 envelope，
        raise UnauthorizedException(message=_message_of(body))
    
    raise BizException(message=_message_of(body), code=status_code)


async def post_write(path: str, *, token: str, payload: dict[str, object]) -> dict[str, Any]:
    """ 统一写请求出口：JWT 头注入 -> POST -> 响应翻译。

    payload 里值为 None 的键一律剔除：express-validator 的 .optional() 只跳过 undefined，
    显式 null 会被当非法值拒掉（如 head=null 报「头围必须大于0」）。
    成功时返回完整响应体（data 是新文档 id 字符串）。
    """

    # 初始化客户端
    client = init_node_api_client()
    body: dict[str, Any]

    """
    payload = {
        "name": "Alice",
        "age": 30,
        "email": None,
        "phone": None,
        "city": "Hangzhou",
    }

    # 过滤掉值为 None 的字段
    clean = {k: v for k, v in payload.items() if v is not None}

    print(clean)
    # {'name': 'Alice', 'age': 30, 'city': 'Hangzhou'}
    """

    try:
        resp = await client.post(
            path,
            json={ k: v for k, v in payload.items() if v is not None }, # 过滤掉value为None的值
            headers={
                "Authorization": f"Bearer {token}",
            }
        )
    except httpx.RequestError as exc:
        # 网络层失败（Node 未启动/超时/隧道断开）：统一友好文案，原始错误进日志
        logger.warning("Node API 请求失败 %s: %s", path, exc)

        raise BizException(message='汀宝宝服务暂时不可用，请稍后再试') from exc

    try:
        # resp.json() 返回 Any，光声明变量类型压不住 reportAny，cast 显式收窄（与 M2 tools.py 同款）
        body = cast(dict[str, Any], resp.json())
    except ValueError as exc:
        logger.warning("Node API 响应非 JSON %s -> %s", path, resp.status_code)
        
        raise BizException(message="汀宝宝服务响应异常，请稍后再试") from exc
    
    if resp.status_code != 200:  # 非 200：先按状态码翻译（Node 成功恒为 HTTP 200）
        _translate_status(resp.status_code, body)
    
    code = body.get("code")
    if code == ResponseCode.SUCCESS:
        return body
    if code == ResponseCode.UNAUTHORIZED:
        raise UnauthorizedException(_message_of(body))
    if code == ResponseCode.FORBIDDEN:
        raise ForbiddenException(_message_of(body))
    
    # 其余业务失败（HTTP 200 + code!=0）：原样透传 code 与文案
    raise BizException(
        message=_message_of(body), 
        code=code if isinstance(code, int) else ResponseCode.SERVER_ERROR
    )