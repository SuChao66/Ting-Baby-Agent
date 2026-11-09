# app/tools/readers/milestone.py
from typing import Any

from app.crud import records as crud_records
from app.schemas.records import MilestoneOut
from app.tools.readers import parse_date, resolve_baby_ids
from app.tools.registry import read_tool


@read_tool("query_milestones")
async def query_milestones(
    user_id: str,
    baby_id: str | None = None,
    milestone_only: bool = False,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """查询成长时间线动态（文字 + 图片/视频/音频附件），按发布时间倒序。

    Args:
        user_id: 用户 id（服务端从 JWT 注入）
        baby_id: 可选，指定宝宝；缺省查该用户全部宝宝
        milestone_only: 可选，True 时只看里程碑事件，默认全部
        start: 可选，开始日期 YYYY-MM-DD（含当天）
        end: 可选，结束日期 YYYY-MM-DD（含当天）
        limit: 可选，最多返回条数，默认 20，上限 100
    Returns:
        动态列表（含 files 附件）
    """
    baby_ids = await resolve_baby_ids(user_id, baby_id)
    docs = await crud_records.query_milestones(
        baby_ids, parse_date(start), parse_date(end, end_of_day=True), limit
    )
    if milestone_only:
        docs = [doc for doc in docs if doc.get("isMilestone") is True]
    return [MilestoneOut.model_validate(doc).model_dump(mode="json") for doc in docs]
