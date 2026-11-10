# app/tools/readers/vaccine.py
from typing import Any

from app.core.exceptions import NotFoundException
from app.crud import records as crud_records
from app.schemas.records import VaccinePlanOut, VaccineRecordOut
from app.tools.registry import read_tool
from app.tools.shared import parse_date, resolve_baby_ids


@read_tool("query_vaccine_records")
async def query_vaccine_records(
    user_id: str,
    baby_id: str | None = None,
    start: str | None = None,
    end: str | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """查询疫苗接种记录：名称、剂次、日期、接种单位、费用，按接种日期倒序。

    Args:
        user_id: 用户 id（服务端从 JWT 注入）
        baby_id: 可选，指定宝宝；缺省查该用户全部宝宝
        start: 可选，开始日期 YYYY-MM-DD（含当天）
        end: 可选，结束日期 YYYY-MM-DD（含当天）
        limit: 可选，最多返回条数，默认 20，上限 100
    Returns:
        记录列表
    """
    baby_ids = await resolve_baby_ids(user_id, baby_id)
    docs = await crud_records.query_vaccine_records(
        baby_ids, parse_date(start), parse_date(end, end_of_day=True), limit
    )
    return [VaccineRecordOut.model_validate(doc).model_dump(mode="json") for doc in docs]


@read_tool("get_vaccine_plan")
async def get_vaccine_plan(user_id: str, baby_id: str | None = None) -> dict[str, Any]:
    """查询宝宝的疫苗接种计划（已加入计划的自费疫苗剂次 key 列表）。

    key 的中文名对照在前端疫苗模板里，本工具只透出原始 key（如 hepb-1）。

    Args:
        user_id: 用户 id（服务端从 JWT 注入）
        baby_id: 可选，宝宝 id；缺省取第一个宝宝
    Returns:
        { id, babyId, keys }
    """
    baby_ids = await resolve_baby_ids(user_id, baby_id)
    if not baby_ids:
        raise NotFoundException("该用户还没有关联宝宝")
    plan = await crud_records.get_vaccine_plan(baby_ids[0])
    if plan is None:
        raise NotFoundException("该宝宝还没有接种计划")
    return VaccinePlanOut.model_validate(plan).model_dump(mode="json")
