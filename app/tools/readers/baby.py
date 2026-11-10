# app/tools/readers/baby.py
from typing import Any

from app.core.exceptions import NotFoundException
from app.crud import baby as crud_baby
from app.schemas.baby import BabyOut
from app.tools.registry import read_tool
from app.tools.shared import resolve_baby_ids


@read_tool("get_baby_profile")
async def get_baby_profile(user_id: str, baby_id: str | None = None) -> dict[str, Any]:
    """查询宝宝档案：小名、性别、生日、出生身高体重、血型、过敏原等。

    baby_id 缺省时返回该用户的第一个宝宝。

    Args:
        user_id: 用户 id（服务端从 JWT 注入，工具绝不接收前端传来的用户身份）
        baby_id: 可选，宝宝 id；缺省取第一个宝宝
    Returns:
        宝宝档案 dict（含内嵌 profile）
    """

    baby_ids = await resolve_baby_ids(user_id, baby_id)
    if not baby_ids:
        raise NotFoundException("该用户还没有关联宝宝")

    profile = await crud_baby.get_baby_profile(baby_ids[0])
    if profile is None:
        raise NotFoundException("宝宝档案不存在")

    # model_validate 作用是把外部数据（比如字典、ORM 对象、JSON 解析后的结构）验证并转换成模型实例
    return BabyOut.model_validate(profile).model_dump(mode="json")
