# app/tools/writers/record.py
# 目标与职责：三类写工具（身高体重/症状护理/日常记录）。
# docstring 即 M4 的工具 schema；payload 成形转 backend 原名；错误由 api_client 翻译。
# 值域合同以 backend src/enums/enum/constants.ts + validators 为唯一权威（2026-11-12 全量核对），
# 与 backend 校验不一致的值会被 express-validator / mongoose enum 直接拒绝。
from typing import Any, Literal, cast

from app.core.logger import get_logger
from app.schemas.records import DailyType, MedicationUsage, SymptomType
from app.tools.registry import write_tool
from app.tools.shared import write_time
from app.tools.writers.api_client import post_write

logger = get_logger(__name__)

# —— 值域枚举（backend constants.ts；读端 schemas/records.py 已有前三个，直接复用）——
# 尿布状态（DIAPER_STATUS）
DiaperStatus = Literal["poop", "pee", "both", "dry"]
# 症状选项（SYMPTOM_OPTIONS 25 项，按身体部位平铺，与前端 SYMPTOM_GROUPS 一致）
SymptomOption = Literal[
    "runnyNose",  # 流鼻涕
    "cough",  # 咳嗽
    "spitUpMilk",  # 吐奶
    "occipitalBaldness",  # 枕秃
    "teethGrinding",  # 磨牙
    "nosebleed",  # 鼻出血
    "eyeDischarge",  # 眼屎多
    "drooling",  # 流口水
    "snoring",  # 打鼾
    "badBreath",  # 口臭
    "bellyAche",  # 肚子痛
    "diarrhea",  # 腹泻
    "diaperRash",  # 尿布疹
    "constipation",  # 便秘
    "frequentUrination",  # 尿频
    "fever",  # 发热
    "rash",  # 皮疹
    "sweating",  # 多汗
    "convulsion",  # 抽搐
    "shortStature",  # 身材矮小
    "lethargy",  # 嗜睡
    "emotionalInstability",  # 情绪不稳
    "poorAppetite",  # 食欲不振
    "nightCrying",  # 夜啼
    "drowsiness",  # 昏睡
]
# 臭臭颜色（POOP_COLOR_OPTIONS 12 项）
PoopColor = Literal[
    "yellow",  # 黄色
    "yellowGreen",  # 黄绿色
    "darkGreen",  # 深绿色
    "greenBrown",  # 绿棕色
    "lightYellow",  # 浅黄色
    "darkBrown",  # 深棕色
    "black",  # 黑色
    "green",  # 绿色
    "grayWhite",  # 灰白色
    "darkRed",  # 暗红色
    "red",  # 红色
    "pink",  # 粉色
]
# 臭臭性状（POOP_SHAPE_OPTIONS 15 项）
PoopShape = Literal[
    "paste",  # 糊状
    "dryThick",  # 干硬
    "cream",  # 奶油状
    "milkCurds",  # 奶瓣
    "watery",  # 稀水样
    "foamy",  # 泡沫样
    "muddy",  # 黏土样
    "granular",  # 颗粒状
    "tarry",  # 柏油样
    "jam",  # 果酱样
    "tofuResidue",  # 豆腐渣样
    "eggDropSoup",  # 蛋花汤样
    "mucus",  # 黏液样
    "asphaltLike",  # 沥青样黑便
    "powder",  # 粉末状
]
# 尿量（PEE_AMOUNT_OPTIONS）
PeeAmount = Literal["little", "medium", "much"]
# 喂奶计量方式（BREAST_FEED_MODE：计时 / 手动输入）
BreastMode = Literal["timer", "manual"]
# 亲喂最后使用侧（BREAST_SIDE）
BreastSide = Literal["left", "right"]

# 身高体重接口
WEIGHT_HEIGHT_ADD_PATH = "/api/v1/weight_height/add"
# 症状接口
SYMPTOM_RECORD_ADD_PATH = "/api/v1/symptom_record/add"
# 吃喝拉撒睡接口
DAILY_RECORD_ADD_PATH = "/api/v1/daily_record/add"


@write_tool("add_growth_record")
async def add_growth_record(
    user_id: str,
    token: str,
    baby_id: str,
    date: str,
    height: float,
    weight: float,
    head: float | None = None,
) -> dict[str, Any]:
    """记录宝宝的身高体重测量值。

    Args:
        user_id: 服务端注入的用户 id（调用方勿传）。
        token: 服务端注入的 JWT（调用方勿传）。
        baby_id: 宝宝 id，24 位十六进制字符串。
        date: 测量日期，YYYY-MM-DD；今天可只写日期（自动补当前时刻）。
        height: 身高，厘米，大于 0，例如 75.5。
        weight: 体重，千克，大于 0，例如 9.2。
        head: 头围，厘米，大于 0，可选。
    """

    # 组装 payload
    payload: dict[str, Any] = {
        "babyId": baby_id,
        "date": write_time(date),
        "height": height,
        "weight": weight,
        "head": head,
    }
    body = await post_write(WEIGHT_HEIGHT_ADD_PATH, token=token, payload=payload)
    # Node 合同：data 是新文档 id 的 24 位 hex 字符串；cast 收窄避开 reportAny
    # 从 body 这个字典里取 "data" 这个键对应的值；如果键不存在，就返回默认值
    record_id = cast(str, body.get("data", ""))
    logger.info("身高体重已写入 user=%s baby=%s date=%s id=%s", user_id, baby_id, date, record_id)

    return {"id": record_id, "message": body.get("message", "新增成功")}


@write_tool("add_health_data")
async def add_health_data(
    user_id: str,
    token: str,
    baby_id: str,
    record_type: SymptomType,
    start_time: str,
    temperature: float | None = None,
    symptoms: list[SymptomOption] | None = None,
    medicine_name: str | None = None,
    medicine_type: MedicationUsage | None = None,
    dosage: str | None = None,
    hospital: str | None = None,
    department: str | None = None,
    doctor: str | None = None,
    diagnosis: str | None = None,
    advice: str | None = None,
    content: str | None = None,
    remark: str | None = None,
) -> dict[str, Any]:
    """记录宝宝的医疗护理信息：测体温、症状、用药、看医生、护理备忘。

    吃喝拉撒睡等日常流水（喂奶/睡觉/换尿布/辅食/洗澡）请改用 add_daily_care。

    Args:
        user_id: 服务端注入的用户 id（调用方勿传）。
        token: 服务端注入的 JWT（调用方勿传）。
        baby_id: 宝宝 id，24 位十六进制字符串。
        record_type: 记录类型（枚举）：
            "temperature"(测体温：temperature 必填)
            "symptom"(症状记录：symptoms 必填，从 symptoms 枚举里选)
            "medication"(用药：medicine_name 与 medicine_type 必填，dosage 可选)
            "doctor"(就诊：diagnosis 必填，hospital/department/doctor/advice 可选)
            "memo"(护理备忘：content 必填)
        start_time: 记录发生时间，YYYY-MM-DD HH:MM（24小时制）或 YYYY-MM-DD；不能晚于当前时间。
        temperature: 体温，摄氏度，34~43；type=temperature 时必填。
        symptoms: 症状 key 列表（多选）；type=symptom 时必填。
            对照：runnyNose=流鼻涕、cough=咳嗽、spitUpMilk=吐奶、occipitalBaldness=枕秃、
            teethGrinding=磨牙、nosebleed=鼻出血、eyeDischarge=眼屎多、drooling=流口水、
            snoring=打鼾、badBreath=口臭、bellyAche=肚子痛、diarrhea=腹泻、diaperRash=尿布疹、
            constipation=便秘、frequentUrination=尿频、fever=发热、rash=皮疹、sweating=多汗、
            convulsion=抽搐、shortStature=身材矮小、lethargy=嗜睡、emotionalInstability=情绪不稳、
            poorAppetite=食欲不振、nightCrying=夜啼、drowsiness=昏睡。
        medicine_name: 药品名称；type=medication 时必填。
        medicine_type: 药品使用方式：internal(内服)/external(外用，如退烧贴)；
            type=medication 时必填。
        dosage: 用药剂量描述，可选。
        hospital: 医院名称，type=doctor 时可填。
        department: 就诊科室，type=doctor 时可填。
        doctor: 医生姓名，type=doctor 时可填。
        diagnosis: 诊断结果；type=doctor 时必填。
        advice: 医嘱，type=doctor 时可填。
        content: 备忘内容；type=memo 时必填。
        remark: 备注说明，可选。
    """
    payload: dict[str, Any] = {
        "babyId": baby_id,
        "type": record_type,
        "startTime": write_time(start_time),
        "temperature": temperature,
        "symptoms": symptoms,
        "medicineName": medicine_name,
        "medicineType": medicine_type,
        "dosage": dosage,
        "hospital": hospital,
        "department": department,
        "doctor": doctor,
        "diagnosis": diagnosis,
        "advice": advice,
        "content": content,
        "remark": remark,
    }
    body = await post_write(SYMPTOM_RECORD_ADD_PATH, token=token, payload=payload)
    record_id = cast(str, body.get("data", ""))

    logger.info(
        "症状护理已写入 user=%s baby=%s type=%s id=%s", user_id, baby_id, record_type, record_id
    )

    return {"id": record_id, "message": body.get("message", "新增成功")}


@write_tool("add_daily_care")
async def add_daily_care(
    user_id: str,
    token: str,
    baby_id: str,
    record_type: DailyType,
    start_time: str,
    duration: int | None = None,
    event_name: str | None = None,
    food_name: str | None = None,
    food_weight: str | None = None,
    status: DiaperStatus | None = None,
    poop_color: PoopColor | None = None,
    poop_shape: PoopShape | None = None,
    pee_amount: PeeAmount | None = None,
    has_rash: bool | None = None,
    breast_mode: BreastMode | None = None,
    left_duration: int | None = None,
    right_duration: int | None = None,
    last_used_side: BreastSide | None = None,
    estimated_amount: int | None = None,
    formula_amount: int | None = None,
    breast_milk_amount: int | None = None,
    remark: str | None = None,
) -> dict[str, Any]:
    """记录宝宝的吃喝拉撒睡日常：喂奶、睡觉、换尿布、辅食、洗澡、玩耍、游泳、其他。

    体温、生病症状、用药、就诊等医疗护理信息请改用 add_health_data。

    Args:
        user_id: 服务端注入的用户 id（调用方勿传）。
        token: 服务端注入的 JWT（调用方勿传）。
        baby_id: 宝宝 id，24 位十六进制字符串。
        record_type: 记录类型（枚举）：
            "feed"(喂奶：母乳亲喂填 breast_mode=timer 与 left_duration/right_duration；
                瓶喂母乳填 breast_mode=manual 与 estimated_amount/breast_milk_amount；
                奶粉填 formula_amount，可带 food_name 奶名)
            "sleep"(睡觉：duration 必填，分钟)
            "diaper"(换尿布：status 必填；含大便时 poop_color/poop_shape 必填、
                尿量填 pee_amount；尿布疹用 has_rash)
            "food"(辅食：food_name 必填，food_weight 可选)
            "bath"(洗澡：duration 必填，分钟)
            "play"(玩耍：duration 可选，分钟)
            "swim"(游泳：duration 可选，分钟)
            "other"(其他事件：event_name 必填)
        start_time: 记录发生时间，YYYY-MM-DD HH:MM（24小时制）或 YYYY-MM-DD；不能晚于当前时间。
        duration: 持续时长，分钟，大于 0；sleep 必填，bath/play/swim 可选。
        event_name: 自定义事件名；type=other 时必填。
        food_name: 食物名称；type=food（辅食）时必填，type=feed 喂奶粉时可填（如"a2三段"）。
        food_weight: 辅食重量描述，如"30克"；type=food 时可选。
        status: 尿布状态，type=diaper 时必填：poop(臭臭)/pee(嘘嘘)/both(臭臭+嘘嘘)/dry(干爽)。
        poop_color: 大便颜色，type=diaper 且含大便时必填，从枚举选（yellow=黄色、green=绿色等）。
        poop_shape: 大便性状，type=diaper 且含大便时必填，从枚举选（paste=糊状、watery=稀水样等）。
        pee_amount: 尿量，type=diaper 含小便时填写：little(少量)/medium(中量)/much(大量)。
        has_rash: 是否尿布疹，true/false，type=diaper 时可选。
        breast_mode: 喂奶计量方式，type=feed 且母乳时填：timer(计时)/manual(手动估算)。
        left_duration: 亲喂左侧时长，分钟，type=feed 亲喂计时时填。
        right_duration: 亲喂右侧时长，分钟，type=feed 亲喂计时时填。
        last_used_side: 本次最后喂的一侧，type=feed 亲喂时可选：left/right。
        estimated_amount: 母乳亲喂估算量，毫升，type=feed 亲喂母乳时填。
        formula_amount: 奶粉量，毫升，type=feed 喂奶粉或混合喂养时填。
        breast_milk_amount: 母乳量，毫升，type=feed 瓶喂时填。
        remark: 备注说明，可选，最多 200 字。
    """
    payload: dict[str, Any] = {
        "babyId": baby_id,
        "type": record_type,
        "startTime": write_time(start_time),
        "duration": duration,
        "eventName": event_name,
        "foodName": food_name,
        "foodWeight": food_weight,
        "status": status,
        "poopColor": poop_color,
        "poopShape": poop_shape,
        "peeAmount": pee_amount,
        "hasRash": has_rash,
        "breastMode": breast_mode,
        "leftDuration": left_duration,
        "rightDuration": right_duration,
        "lastUsedSide": last_used_side,
        "estimatedAmount": estimated_amount,
        "formulaAmount": formula_amount,
        "breastMilkAmount": breast_milk_amount,
        "remark": remark,
    }
    body = await post_write(DAILY_RECORD_ADD_PATH, token=token, payload=payload)
    record_id = cast(str, body.get("data", ""))

    logger.info(
        "日常记录已写入 user=%s baby=%s type=%s id=%s", user_id, baby_id, record_type, record_id
    )

    return {"id": record_id, "message": body.get("message", "新增成功")}
