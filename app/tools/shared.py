# app/tools/shared.py
# 目标与职责：工具共享设施——与 registry.py 同级的基础设施，不参与白名单注册。
# 读侧：宝宝归属解析（越权防线）与日期解析；写侧：时间适配（纯日期「今天」补当前时刻，
# 带时刻附加本地时区偏移，与前端 toLocalISOString 同构，服务器任何时区都能正确比较）。
import re
from datetime import date, datetime

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


# 纯日期：YYYY-MM-DD
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _local_iso(dt: datetime) -> str:
    """naive 本地时间 -> 带时区偏移的 ISO 字符串（2026-11-09T10:30:00+08:00）。"""

    return dt.astimezone().isoformat(timespec="seconds")


# 写时间
def write_time(value: str) -> str:
    """把 LLM/调试传来的时间统一成 Node API 能正确校验的 ISO 字符串。

    - 纯日期 YYYY-MM-DD：今天 -> 补成当前时刻（避开早8点前被 Node 拒的坑）；
      过去日期原样透传（Node 按 UTC 零点解析，必然早于当前）；未来日期原样透传
      （Node 自己会拒，错误文案更友好）。
    - 带时刻：解析后若没带时区则附加本地偏移（astimezone），与前端提交格式同构。
    """

    text = value.strip()  # 去掉前后空格
    if _DATE_ONLY.fullmatch(text):  # 纯日期
        if text == date.today().isoformat():  # 今天
            return _local_iso(datetime.now())  # 补当前时刻

        return text  # 过去或未来日期，原样透传

    parsed = datetime.fromisoformat(text.replace(" ", "T"))  # 带时刻
    if parsed.tzinfo is None:  # 未指定时区
        return parsed.isoformat(timespec="seconds")

    return _local_iso(parsed)
