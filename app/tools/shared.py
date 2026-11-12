# app/tools/shared.py
# 目标与职责：工具共享设施——与 registry.py 同级的基础设施，不参与白名单注册。
# 读侧：宝宝归属解析（越权防线）与日期解析；写侧：时间适配（纯日期「今天」补当前时刻，
# 带时刻统一补北京时间偏移，与前端 toLocalISOString 同构，服务器任何时区都正确）。
import re
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from app.core.exceptions import ForbiddenException
from app.crud import baby as crud_baby

# 业务时区唯一权威：用户/宝宝都在中国，一切「本地时间」语义都是北京时间，
# 不信服务器时区（部署到 UTC 容器/海外机器时不炸）
_CN_TZ = ZoneInfo("Asia/Shanghai")


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
    """YYYY-MM-DD（北京日期）-> naive UTC datetime（与 pymongo 读出的存储形态一致）。

    Mongo 里存的都是 UTC 时刻；北京 0 点 = 前一日 16:00 UTC，不换算的话
    「今天」查询会漏掉北京 0-8 点的凌晨记录。end_of_day=True 取当天最后一秒
    （闭区间右端，同样按北京日界换算）。
    """
    if value is None:
        return None
    parsed = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=_CN_TZ)

    if end_of_day:
        parsed = parsed.replace(hour=23, minute=59, second=59)

    return parsed.astimezone(UTC).replace(tzinfo=None)


# 纯日期：YYYY-MM-DD
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _local_iso(dt: datetime) -> str:
    """任意时间 -> 北京时区 ISO 字符串（2026-11-09T10:30:00+08:00）。

    naive 输入视为系统本地时刻（datetime.now() 的产物，与系统时区自洽）。
    """

    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.astimezone(_CN_TZ).isoformat(timespec="seconds")


# 写时间
def write_time(value: str) -> str:
    """把 LLM/调试传来的时间统一成 Node API 能正确校验的 ISO 字符串。

    - 纯日期 YYYY-MM-DD：今天 -> 补成当前时刻（避开早8点前被 Node 拒的坑）；
      过去日期原样透传（Node 按 UTC 零点解析，必然早于当前）；未来日期原样透传
      （Node 自己会拒，错误文案更友好）。
    - 带时刻：没带时区标记的一律按北京时间补 +08:00——模型填的是用户嘴里的
      北京时间，不信服务器时区；已带时区的转成北京时区输出，与前端提交格式同构。
    """

    text = value.strip()  # 去掉前后空格
    if _DATE_ONLY.fullmatch(text):  # 纯日期
        if text == datetime.now(_CN_TZ).date().isoformat():  # 今天（北京日界）
            return _local_iso(datetime.now(_CN_TZ))  # 补当前时刻

        return text  # 过去或未来日期，原样透传

    parsed = datetime.fromisoformat(text.replace(" ", "T"))  # 带时刻
    if parsed.tzinfo is None:  # 未指定时区：北京时间语义，硬标 +08:00
        return parsed.replace(tzinfo=_CN_TZ).isoformat(timespec="seconds")

    return _local_iso(parsed)
