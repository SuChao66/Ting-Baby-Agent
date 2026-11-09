# app/tools/readers/care.py
from typing import Any

from app.crud import records as crud_records
from app.schemas.records import DailyRecordOut
from app.tools.readers import parse_date, resolve_baby_ids
from app.tools.registry import read_tool


@read_tool("query_daily_care")
async def query_daily_care(
    user_id: str,
    baby_id: str | None = None,
    record_type: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """查询日常记录：喂奶、睡眠、换尿布、辅食、洗澡、玩耍、游泳等吃喝拉撒睡流水，按开始时间倒序。

    Args:
        user_id: 用户 id（服务端从 JWT 注入）
        baby_id: 可选，指定宝宝；缺省查该用户全部宝宝
        record_type: 可选，记录类型过滤：feed/sleep/diaper/food/bath/play/swim/other
        start: 可选，开始日期 YYYY-MM-DD（含当天）
        end: 可选，结束日期 YYYY-MM-DD（含当天）
        limit: 可选，最多返回条数，默认 20，上限 100
    Returns:
        记录列表（喂奶含 leftDuration/rightDuration/formulaAmount 等字段）
    """
    baby_ids = await resolve_baby_ids(user_id, baby_id)
    docs = await crud_records.query_daily_care(
        baby_ids, parse_date(start), parse_date(end, end_of_day=True), limit
    )
    if record_type is not None:
        docs = [doc for doc in docs if doc.get("type") == record_type]
    return [DailyRecordOut.model_validate(doc).model_dump(mode="json") for doc in docs]
