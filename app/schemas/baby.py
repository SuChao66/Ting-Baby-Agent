# app/schemas/baby.py
# 目标与职责：宝宝档案的字段合同，字段名与 backend src/models/Baby.ts 逐字对齐。
from datetime import datetime
from typing import Literal

# 导入校验
from pydantic import BaseModel


# baby profile
class BabyProfile(BaseModel):
    """内嵌档案（Baby.ts 的 profile 子文档）"""

    bloodType: str | None = None  # 血型（A/B/O/AB/Rh等）
    birthWeight: float | None = None  # 出生体重（kg）
    birthHeight: float | None = None  # 出生身长（cm）
    allergens: str | None = None  # 过敏原
    preferences: str | None = None  # 喜好
    remarks: str | None = None  # 备注


# Baby
class BabyOut(BaseModel):
    """宝宝档案读模型（_id 已在 crud 层归一化为 id）"""

    id: str
    nickname: str  # 宝宝小名
    gender: Literal[0, 1]  # 性别：0-女 1-男
    birthday: datetime  # 出生日期
    birthTime: str | None = None  # 出生时刻（HH:mm:ss）
    avatarUrl: str | None = None  # 头像 URL
    profile: BabyProfile | None = None  # 内嵌档案
