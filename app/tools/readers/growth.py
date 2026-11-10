# app/tools/readers/growth.py
from typing import Any

from app.core.exceptions import NotFoundException
from app.crud import records as crud_records
from app.schemas.records import GrowthRecordOut
from app.tools.registry import read_tool
from app.tools.shared import parse_date, resolve_baby_ids


@read_tool("query_growth_records")
async def query_growth_records(
    user_id: str,
    baby_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """查询身高体重测量记录（含头围），按测量日期倒序。

    Args:
        user_id: 用户 id（服务端从 JWT 注入）
        baby_id: 可选，指定宝宝；缺省查该用户全部宝宝
        start: 可选，开始日期 YYYY-MM-DD（含当天）
        end: 可选，结束日期 YYYY-MM-DD（含当天）
        limit: 可选，最多返回条数，默认 20，上限 100
    Returns:
        记录列表，每条含 height/weight/head/date
    """

    baby_ids = await resolve_baby_ids(user_id, baby_id)
    if not baby_ids:
        raise NotFoundException("该用户还没有关联宝宝")

    docs = await crud_records.query_growth_records(
        baby_ids, parse_date(start), parse_date(end, end_of_day=True), limit
    )
    return [GrowthRecordOut.model_validate(doc).model_dump(mode="json") for doc in docs]
