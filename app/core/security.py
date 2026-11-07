# app/core/security.py
# 目标与职责：校验前端透传的用户 JWT。与 backend 共享 secret（.env 的 JWT_SECRET = backend .env 的 jwtSecret）。Agent 侧只验不发（签发永远在 backend），所以没有 encode 函数。
import jwt
from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

ALGORITHM = "HS256"

# jwt token payload
class TokenPayload(BaseModel):
    """ 与Ting-baby-backend src/types/express.d.ts的TokenPayload保持一致 """
    id: str
    username: str

# 校验token
def decode_token(token: str)-> TokenPayload:
    """ 校验签名与有效期，返回用户信息。三态失败文案与 backend auth 中间件逐字一致。 """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("token 已过期，请重新登录") from None
    except jwt.InvalidTokenError:
        raise UnauthorizedException("token 无效") from None

    user_id = payload.get("id")
    username = payload.get("username")

    # isinstance 窄化：jwt.decode 返回 dict[str, Any]，isinstance 让 basedpyright 收窄 Any；
    # 同时比 str() 强转更严格——非字符串字段直接判无效，对齐 backend 的 TS 类型合同
    if not isinstance(user_id, str) or not isinstance(username, str) or not user_id or not username:
        raise UnauthorizedException("token 无效")

    return TokenPayload(id=user_id, username=username)