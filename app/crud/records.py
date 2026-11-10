# app/crud/records.py
# 目标与职责：五类记录查询。collection 名见指南 0.5——camelCase 为主，猜错不报错。
from datetime import datetime
from typing import Any

from app.core.database import get_db
from app.crud.common import find_many, normalize_doc, oid


# 判断babyId是否在 baby_ids 里
def _baby_filter(baby_ids: list[str]) -> dict[str, Any]:
    """公共过滤：babyId $in。baby_ids 已经过 readers 层越权校验。"""

    return {"babyId": {"$in": [oid(b) for b in baby_ids]}}


# 限制时间窗：[start, end]
def _with_range(
    query: dict[str, Any], field: str, start: datetime | None, end: datetime | None
) -> None:
    """把可选时间窗并进 query(原地修改)。两个边界都给就是闭区间 [start, end]。"""

    if start is not None or end is not None:
        query[field] = {"$gte": start, "$lte": end}


# 获取成长记录
async def query_growth_records(
    baby_ids: list[str],
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """身高体重（heightWeight，按 date 倒序）。"""

    query = _baby_filter(baby_ids)
    _with_range(query, "date", start, end)

    return await find_many("heightWeight", query, "date", limit)


# 获取健康数据
async def query_health_data(
    baby_ids: list[str],
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """症状护理（symptomRecord，按 startTime 倒序）。type 过滤在 readers 层做内存过滤。"""

    query = _baby_filter(baby_ids)
    _with_range(query, "startTime", start, end)

    return await find_many("symptomRecord", query, "startTime", limit)


# 获取吃喝拉撒睡
async def query_daily_care(
    baby_ids: list[str],
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """吃喝拉撒睡（dailyRecord，按 startTime 倒序）。type 过滤同上。"""
    query = _baby_filter(baby_ids)
    _with_range(query, "startTime", start, end)

    return await find_many("dailyRecord", query, "startTime", limit)


# 获取疫苗接种记录
async def query_vaccine_records(
    baby_ids: list[str],
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """接种记录（vaccineRecord，按 injectDate 倒序）。"""
    query = _baby_filter(baby_ids)
    _with_range(query, "injectDate", start, end)

    return await find_many("vaccineRecord", query, "injectDate", limit)


# 获取大事记记录
async def query_milestones(
    baby_ids: list[str],
    start: datetime | None = None,
    end: datetime | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """成长时间线（timeline，按 publishTime 倒序）。"""
    query = _baby_filter(baby_ids)
    _with_range(query, "publishTime", start, end)

    return await find_many("timeline", query, "publishTime", limit)


# 获取接种计划
async def get_vaccine_plan(baby_id: str) -> dict[str, Any] | None:
    """接种计划（vaccinePlan，每宝宝一份，find_one 单条）。"""

    doc = await get_db()["vaccinePlan"].find_one({"babyId": oid(baby_id)})

    return normalize_doc(doc)
