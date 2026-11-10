# app/crud/common.py
# 目标与职责：crud层公共设施，clamp_limit + find_many 是 limit 硬上限的唯一执行点，
# 全项目谁都绕不过去。

from typing import Any

# 处理 BSON（Binary JSON） 格式的库，BSON 是 MongoDB 使用的二进制文档格式，
# 比 JSON 多了日期、ObjectId、二进制数据、正则、Decimal128 等类型，也更适合高效存储和解析
from bson import ObjectId

from app.core.database import get_db
from app.core.exceptions import BizException

DEFAULT_LIMIT = 20  # 不传 limit 时的默认条数
MAX_LIMIT = 100  # 硬上限


# 限制 limit 的值，避免恶意请求。
def clamp_limit(limit: int | None) -> int:
    """限制 limit 的值，避免恶意请求。把外部传来的 limit 钳制在 [1, MAX_LIMIT]。"""

    if limit is None:
        return DEFAULT_LIMIT

    return max(1, min(MAX_LIMIT, limit))


# 将字符串转为 ObjectId。
def oid(value: str) -> ObjectId:
    """把字符串转为 ObjectId。"""

    try:
        return ObjectId(value)
    except Exception as e:
        #  f-string（格式化字符串）：自动把 {} 里的内容替换成实际值，
        #  类似于："无效的 id: " + str(value)
        raise BizException(f"无效的 id: {value}") from e


# 递归转换 ObjectId -> str。
def _to_plain(value: Any) -> Any:
    """递归转换 ObjectId -> str。datetime 不用动，Pydantic 原生处理。"""

    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, dict):
        return {key: _to_plain(item) for key, item in value.items()}

    if isinstance(value, list):
        return [_to_plain(item) for item in value]

    return value


# 归一化
def normalize_doc(doc: dict[str, Any] | None) -> dict[str, Any] | None:
    """
    Mongo 文档 -> JSON 友好 dict：ObjectId 全转 str，顶层 _id 改名 id。

    backend 的 JSON 输出里主键就叫 id（mongoose 的 toJSON 转换），
    我们在 crud 层对齐这个约定，schema 里就可以直接写 id: str。
    """

    if doc is None:
        return None
    plain: Any = _to_plain(doc)

    if "_id" in plain:
        plain["id"] = plain.pop("_id")

    return plain


# 查找
# coll: 集合名
# query: 查询条件
# sort_field: 排序字段
# limit: 条数限制
async def find_many(
    coll: str,
    query: dict[str, Any],
    sort_field: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """全项目唯一的批量查询出口：倒序 + 强制 limit + 归一化。

    to_list(length=n) 是真正的闸门：游标只取 n 条，查询命中再多也只回 n 条。
    """
    n = clamp_limit(limit)
    cursor = get_db()[coll].find(query).sort(sort_field, -1).limit(n)
    docs = await cursor.to_list(length=n)

    # 游标产出的永远是 dict；is not None 只为类型收窄
    # （normalize_doc 的 None 分支服务 find_one 路径）
    return [d for doc in docs if (d := normalize_doc(doc)) is not None]  # pyright: ignore[reportAny]
