# app/crud/baby.py
# 目标与职责：用户↔宝宝关系查询 + 单宝宝档案。一切记录查询都从这里拿 baby_ids。
from typing import Any

from app.core.database import get_db
from app.crud.common import find_many, normalize_doc, oid

# 根据用户 id 查询该用户全部有效宝宝 id
async def get_baby_ids_for_user(user_id: str) -> list[str]:
    """ 查 user_baby_relation 得到该用户全部有效宝宝 id（status=1，已移除的除外）。  """

    relations = await find_many(
        "user_baby_relation",
        {
            "userId": oid(user_id),
            "status": 1,
        },
        sort_field="createdAt",
        limit=50  # 一个用户的宝宝数远小于此，给个安全边界
    )

    baby_ids: list[str] = []
    for relation in relations:
        baby_id: str = relation["babyId"]  # 显式注解：从 dict[str, Any] 取值回到 str 类型世界
        baby_ids.append(baby_id)

    return baby_ids


# 获取单个宝宝档案
async def get_baby_profile(baby_id: str) -> dict[str, Any] | None:
    """ 按 id 查单个宝宝档案 """

    doc = await get_db()["baby"].find_one(
        {
            "_id": oid(baby_id),
        }
    )

    return normalize_doc(doc)