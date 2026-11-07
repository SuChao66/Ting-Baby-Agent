# app/schemas/response.py
from enum import IntEnum
from typing import Generic, TypeVar
# 引入校验
from pydantic import BaseModel

T = TypeVar('T')

# 定义响应码
class ResponseCode(IntEnum):
    """ 与Ting-baby-backend src/enums/enum/constants.ts的RESPONSE_CODE保持一致 """
    SUCCESS = 0
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    RATE_LIMIT = 429
    PARAM_ERROR = 430
    SERVER_ERROR = 500

# 定义响应体
class ApiResponse(BaseModel, Generic[T]):
    """ 统一响应体：与backend ApiResponse<T> 保持一致 """
    code: int = ResponseCode.SUCCESS
    data: T | None = None
    message: str = "success"

# 定义成功响应
def ok(data: T | None = None, message: str = "success") -> ApiResponse[T]:
    """ 成功响应 """
    return ApiResponse[T](code=ResponseCode.SUCCESS, data=data, message=message)

# 定义失败响应
def fail(code: int = ResponseCode.SERVER_ERROR, message: str = "error") -> ApiResponse[T]:
    """ 失败响应 """
    return ApiResponse[T](code=code, data=None, message=message)