# app/tools/writers/record.py
# 目标与职责：三类写工具（身高体重/症状护理/日常记录）。
# docstring 即 M4 的工具 schema；payload 成形转 backend 原名；错误由 api_client 翻译。
from typing import Any, cast

from app.core.logger import get_logger
from app.tools.registry import write_tool
from app.tools.writers import write_time
from app.tools.writers.api_client import post_write

logger = get_logger(__name__)

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
)-> dict[str, Any]:
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

    # 组装paload
    payload: dict[str, Any] = {
        "babyId": baby_id,
        "date": write_time(date),
        "height": height,
        "weight": weight,
        "head": head
    }
    body = await post_write(
        WEIGHT_HEIGHT_ADD_PATH,
        token=token,
        payload=payload
    )
    # Node 合同：data 是新文档 id 的 24 位 hex 字符串；cast 收窄避开 reportAny
    # 从 body 这个字典里取 "data" 这个键对应的值；如果键不存在，就返回默认值
    record_id = cast(str, body.get("data", ""))
    logger.info("身高体重已写入 user=%s baby=%s date=%s id=%s", user_id, baby_id, date, record_id)

    return {
        "id": record_id,
        "message": body.get("message", "新增成功")
    }


@write_tool("add_health_data")
async def add_health_data(
    user_id: str,
    token: str,
    baby_id: str,
    record_type: str,
    start_time: str,
    temperature: float | None = None,
    symptoms: list[str] | None = None,
    medicine_name: str | None = None,
    medicine_type: str | None = None,
    dosage: str | None = None,
    hospital: str | None = None,
    department: str | None = None,
    doctor: str | None = None,
    diagnosis: str | None = None,
    advice: str | None = None,
    content: str | None = None,
    remark: str | None = None,
)-> dict[str, Any]:
    """记录宝宝的医疗护理信息：测量体温、生病症状、用药、就诊、日常护理。

    Args:
        user_id: 服务端注入的用户 id（调用方勿传）。
        token: 服务端注入的 JWT（调用方勿传）。
        baby_id: 宝宝 id，24 位十六进制字符串。
        record_type: 记录类型，只能取 5 个值之一：
            "temperature"(测量体温，此时 temperature 必填，34~43 之间)
            "symptom"(症状记录，此时 symptoms 必填，从固定选项里选)
            "medicine"(用药记录，此时 medicine_name 与 medicine_type 必填，dosage 可选)
            "visit"(就诊记录，此时 diagnosis 或 content 至少填一个)
            "care"(日常护理记录，此时 content 必填)
        start_time: 记录发生时间，YYYY-MM-DD HH:MM（24小时制）或 YYYY-MM-DD。
        temperature: 体温，摄氏度，34~43，仅 type=temperature 时必填。
        symptoms: 症状列表，仅 type=symptom 时必填，取值仅限：发热、咳嗽、流鼻涕、鼻塞、
            咳痰、呕吐、腹泻、便秘、湿疹、皮疹、红臀、食欲不振、睡眠异常、其他。
        medicine_name: 药品名称，仅 type=medicine 时必填。
        medicine_type: 药品类型，仅 type=medicine 时必填，取值仅限：中药、西药、中成药。
        dosage: 用药剂量描述，可选。
        hospital: 医院名称，type=visit 时可填。
        department: 就诊科室，type=visit 时可填。
        doctor: 医生姓名，type=visit 时可填。
        diagnosis: 诊断结果，type=visit 时可填。
        advice: 医嘱，type=visit 时可填。
        content: 护理内容描述，type=care 时必填，type=visit 时可与 diagnosis 二选一。
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
    body = await post_write(
        SYMPTOM_RECORD_ADD_PATH, 
        token=token, 
        payload=payload
    )
    record_id = cast(str, body.get("data", ""))

    logger.info("症状护理已写入 user=%s baby=%s type=%s id=%s", user_id, baby_id, record_type, record_id)

    return {
        "id": record_id, 
        "message": body.get("message", "新增成功")
    }


@write_tool("add_daily_care")
async def add_daily_care(
    user_id: str,
    token: str,
    baby_id: str,
    record_type: str,
    start_time: str,
    duration: int | None = None,
    event_name: str | None = None,
    food_name: str | None = None,
    food_weight: float | None = None,
    status: int | None = None,
    poop_color: str | None = None,
    poop_shape: str | None = None,
    pee_amount: str | None = None,
    has_rash: bool | None = None,
    breast_mode: str | None = None,
    left_duration: int | None = None,
    right_duration: int | None = None,
    last_used_side: str | None = None,
    estimated_amount: int | None = None,
    formula_amount: int | None = None,
    breast_milk_amount: int | None = None,
    remark: str | None = None,
) -> dict[str, Any]:
    """记录宝宝的吃喝拉撒睡日常。

    Args:
        user_id: 服务端注入的用户 id（调用方勿传）。
        token: 服务端注入的 JWT（调用方勿传）。
        baby_id: 宝宝 id，24 位十六进制字符串。
        record_type: 记录类型，只能取 7 个值之一：
            "sleep"(睡觉，duration 必填单位分钟，status 可选 1-5 表示睡眠质量)
            "change"(换尿布，status 必填：1=尿 2=屎 3=尿+屎；status=2 或 3 时
                poop_color/poop_shape 必填；pee_amount 按 status 见上)
            "feed"(喂食，按喂养方式必填不同字段，详见下列字段说明)
            "pump"(吸奶，estimated_amount 毫升必填)
            "bath"(洗澡，duration 分钟必填)
            "sun"(晒太阳，duration 分钟必填)
        start_time: 记录发生时间，YYYY-MM-DD HH:MM（24小时制）或 YYYY-MM-DD。
        duration: 时长，分钟，sleep/bath/sun 时必填，大于 0。
        event_name: 自定义事件名，可选。
        food_name: 食物名称，type=feed 且喂奶粉（如"a2三段"）或辅食时必填。
        food_weight: 辅食重量，克，type=feed 且喂辅食时必填。
        status: 睡眠质量 1-5（sleep 可选）；换尿布内容 1=尿 2=屎 3=尿+屎（change 必填）。
        poop_color: 大便颜色，换尿布含大便时必填，取值仅限：黄色、绿色、黑色、
            红色、白色、陶土色、其他。
        poop_shape: 大便性状，换尿布含大便时必填，取值仅限：糊状、成形、稀水、
            泡沫、粘液、干硬、血便、其他。
        pee_amount: 小便量描述，如"少量""大量"；换尿布 type=1 时必填、type=3 时可填。
        has_rash: 尿布疹，true/false，换尿布时可选。
        breast_mode: 母乳喂养方式，"亲喂"或"瓶喂"；type=feed 且母乳时必填。
        left_duration: 亲喂左侧时长，分钟，亲喂时必填。
        right_duration: 亲喂右侧时长，分钟，亲喂时必填。
        last_used_side: 本次最后喂的一侧，"左"或"右"，亲喂时可选。
        estimated_amount: 母乳瓶喂/吸奶量，毫升，瓶喂与 pump 时必填。
        formula_amount: 奶粉量，毫升，type=feed 且喂奶粉或混合喂养时必填。
        breast_milk_amount: 混合喂养中母乳量，毫升，混合喂养时必填。
        remark: 备注说明，可选。
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

    logger.info("日常记录已写入 user=%s baby=%s type=%s id=%s", user_id, baby_id, record_type, record_id)
    
    return {
        "id": record_id, 
        "message": 
        body.get("message", "新增成功")
    }