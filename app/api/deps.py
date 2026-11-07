# app/api/deps.py
# 目标与职责：依赖注入，为 app.api.api_v1.api 路由提供依赖项。
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.exceptions import UnauthorizedException
from app.core.security import TokenPayload, decode_token

# auto_error=False：没带 Authorization 头时不让库直接抛 403，
# 而是 cred=None 交给我们，返回与 backend 一致的 401 envelope
_bearer = HTTPBearer(auto_error=False)

# Annotated 依赖写法：DI 元数据挂在类型上而非参数默认值，
# 既避开 basedpyright「默认值不允许函数调用」的检查，多个路由还能复用同一个别名
CredDep = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]

# 解析token，获取用户信息（id， username）
async def get_current_user(cred: CredDep) -> TokenPayload:
    """ 校验 JWT，返回用户信息。 """
    if cred is None:
        raise UnauthorizedException("请先登录")
    payload = decode_token(cred.credentials)
    return payload