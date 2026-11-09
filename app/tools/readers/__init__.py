# app/tools/readers/__init__.py
# 目标与职责：读工具共享设施——宝宝归属解析（越权防线）与日期解析。
from datetime import datetime

from app.core.exceptions import ForbiddenException
from app.crud import baby as crud_baby


# 解析 baby_id，越权校验。
async def resolve_baby_ids(user_id: str, baby_id: str | None) -> list[str]:
    """把「可选的 baby_id」解析成可查询的宝宝列表，顺手做越权校验。

    baby_id 为空 -> 该用户全部宝宝；给了 baby_id -> 必须属于该用户，否则 403。
    """

    owned = await crud_baby.get_baby_ids_for_user(user_id)
    if baby_id is None:
        return owned
    
    if baby_id not in owned:
        raise ForbiddenException("无权访问该宝宝")
    
    return [baby_id]

# 解析日期，方便前端使用。
def parse_date(value: str | None, *, end_of_day: bool = False) -> datetime | None:
    """YYYY-MM-DD -> datetime；end_of_day=True 取当天最后一秒（闭区间右端）。"""
    if value is None:
        return None
    parsed = datetime.strptime(value, "%Y-%m-%d")

    if end_of_day:
        return parsed.replace(hour=23, minute=59, second=59)
        
    return parsed
