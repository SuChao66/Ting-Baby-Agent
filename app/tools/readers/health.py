# app/tools/readers/health.py
from typing import Any

from app.crud import records as crud_records
from app.schemas.records import SymptomRecordOut
from app.tools.readers import parse_date, resolve_baby_ids
from app.tools.registry import read_tool


@read_tool("query_health_data")
async def query_health_data(
    user_id: str,
    baby_id: str | None = None,
    record_type: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """查询症状护理记录：体温、症状、用药、看医生、备忘，按记录时间倒序。

    Args:
        user_id: 用户 id（服务端从 JWT 注入）
        baby_id: 可选，指定宝宝；缺省查该用户全部宝宝
        record_type: 可选，记录类型过滤：temperature/symptom/medication/doctor/memo
        start: 可选，开始日期 YYYY-MM-DD（含当天）
        end: 可选，结束日期 YYYY-MM-DD（含当天）
        limit: 可选，最多返回条数，默认 20，上限 100
    Returns:
        记录列表
    """
    
    baby_ids = await resolve_baby_ids(user_id, baby_id)
    docs = await crud_records.query_health_data(
        baby_ids, parse_date(start), parse_date(end, end_of_day=True), limit
    )

    if record_type is not None:
        docs = [doc for doc in docs if doc.get("type") == record_type]

    return [SymptomRecordOut.model_validate(doc).model_dump(mode="json") for doc in docs]