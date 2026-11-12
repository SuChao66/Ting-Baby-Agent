# app/schemas/records.py
# 目标与职责：记录类读模型。判别字段用 Literal（Swagger 下拉 + LLM 合同 + 脏数据拦截），
# 取值超多的选项列表（臭臭颜色 12 选等）放宽为 str，可选值写进注释。
# 时间字段统一 CnTime：Mongo 存 UTC，模型/用户看北京时间，转述零换算。

from datetime import UTC, datetime
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

# 导入校验
from pydantic import BaseModel, PlainSerializer

# 业务时区唯一权威：用户/宝宝都在中国（与 tools/shared.py 同一约定）
_CN_TZ = ZoneInfo("Asia/Shanghai")


# pymongo 默认读出的 naive datetime 值是 UTC 时刻：标 UTC 转北京时间，给「YYYY-MM-DD HH:MM」字符串
def _to_cn_str(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(_CN_TZ).strftime("%Y-%m-%d %H:%M")


# 读模型时间字段类型：序列化统一转北京时间字符串
CnTime = Annotated[datetime, PlainSerializer(_to_cn_str, return_type=str)]

# 吃喝拉撒睡类型（backend constants.ts DAILY_RECORD_TYPES）
DailyType = Literal["feed", "sleep", "diaper", "food", "bath", "play", "swim", "other"]
# 症状护理类型（SYMPTOM_RECORD_TYPES）
SymptomType = Literal["temperature", "symptom", "medication", "doctor", "memo"]
# 药品使用类型
MedicationUsage = Literal["internal", "external"]
# 时间线可见角色
VisibleRole = Literal["public", "family", "private"]


# 身高-体重记录
class GrowthRecordOut(BaseModel):
    """身高体重（heightWeight，按 date 倒序）。"""

    id: str
    babyId: str  # 宝宝 ID
    height: float  # 身高
    weight: float  # 体重
    head: float | None = None  # 头围
    date: CnTime  # 记录日期


# 症状记录
class SymptomRecordOut(BaseModel):
    """症状记录（symptomRecord，按 startTime 倒序）"""

    id: str
    babyId: str  # 宝宝 ID
    type: SymptomType  # 记录类型
    startTime: CnTime | None = None  # 开始时间
    temperature: float | None = None  # 体温 ℃（34-43）
    symptoms: list[str] | None = (
        None  # 症状多选，见 SYMPTOM_OPTIONS（runnyNose/cough/fever 等 24 项）
    )
    medicineType: MedicationUsage | None = None
    medicineName: str | None = None
    dosage: str | None = None
    hospital: str | None = None  # 医院 以下 5 项为看医生
    department: str | None = None  # 科室
    doctor: str | None = None  # 医生
    diagnosis: str | None = None  # 诊断
    advice: str | None = None  # 指导
    content: str | None = None  # 备忘
    remark: str | None = None  # 备注


# 日常记录-吃喝拉撒睡
class DailyRecordOut(BaseModel):
    """吃喝拉撒睡（dailyRecord，按 startTime 倒序）。字段多但都是 backend 原名。"""

    id: str
    babyId: str
    type: DailyType
    startTime: CnTime | None = None  # 开始时间
    duration: float | None = None  # 持续时间（洗睡玩游）
    eventName: str | None = None  # 其他事件名
    foodName: str | None = None  # 辅食
    foodWeight: str | None = None  # 食物重量
    status: str | None = None  # 尿布状态 poop/pee/both/dry
    poopColor: str | None = None  # yellow/yellowGreen/darkGreen/black/... 12 项
    poopShape: str | None = None  # paste/watery/milkCurds/... 15 项
    peeAmount: str | None = None  # little/medium/much
    hasRash: bool | None = None  # 红屁股
    breastMode: str | None = None  # 亲喂模式 timer/manual
    leftDuration: float | None = None  # 左侧喂 分钟
    rightDuration: float | None = None
    lastUsedSide: str | None = None  # left/right
    estimatedAmount: float | None = None  # 预估奶量 ml
    formulaAmount: float | None = None  # 配方奶 ml
    breastMilkAmount: float | None = None  # 母乳 ml
    remark: str | None = None


# 疫苗记录
class VaccineRecordOut(BaseModel):
    """接种记录（vaccineRecord，按 injectDate 倒序）。"""

    id: str
    babyId: str
    vaccineName: str  # 疫苗名称
    dose: int | None = None  # 第几剂
    doseKey: str | None = None  # 剂次标识（如 hepb-1，自由补录为空）
    injectDate: CnTime  # 注射日期
    hospital: str | None = None
    batchNo: str | None = None
    fee: float | None = None
    note: str | None = None


# 接种计划
class VaccinePlanOut(BaseModel):
    """接种计划（vaccinePlan，每宝宝一份）。keys 的语义表在前端模板，M2 只透出原始 key。"""

    id: str
    babyId: str
    keys: list[str]


# 成长记录-附件
class TimelineFile(BaseModel):
    """时间线附件。type 放宽为 str：backend 自身两处不一致（Schema 校验 IMAGE，常量表是 img）。

    fileName 可选：backend Schema 标了 required，但库里历史数据没有该字段
    （校验后补，管不到旧数据）。
    """

    url: str
    type: str  # 理论上 IMAGE/VIDEO/AUDIO
    fileName: str | None = None


# 大事记
class MilestoneOut(BaseModel):
    """成长时间线（timeline，按 publishTime 倒序）。"""

    id: str
    babyId: str
    content: str
    isMilestone: bool | None = None  # 是否里程碑事件
    publishTime: CnTime
    tags: list[str] | None = None
    files: list[TimelineFile] | None = None
    visibleRoles: VisibleRole | None = None
