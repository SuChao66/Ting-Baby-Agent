# app/crud/ai_record.py
# 目标与职责：AI 问答记录（aiRecord 集合）落库——Python 是该集合唯一写入方，
# 读走 Node 历史接口（getRecordList/getRecordDetail），职责边界：Python 写、Node 读。
# schema 权威 = Ting-Baby-Memories-backend/src/models/AIRecord.ts：
# 字段名/类型/索引两边合同，改一边必改另一边。
from datetime import UTC, datetime
from typing import Literal

# DuplicateKeyError: reqId 唯一索引（Mongoose 建的）命中的信号，幂等去重靠它
from pymongo.errors import DuplicateKeyError

from app.core.database import get_db
from app.crud.common import oid

# 定义集合（Mongoose model 第三参数显式指定的集合名，非默认复数形式）
COLLECTION = "aiRecord"


# 保存会话内容
async def save_aiRecord(
    user_id: str, session_code: str, question: str, answer: str, req_id: str, status: Literal[1, 0]
) -> bool:
    """落库一条问答记录；调用方负责整体 try/except 兜底（旁路操作）。

    返回 False = reqId 重复命中唯一索引，幂等跳过，不算错误。
    """

    # Mongoose timestamps 是应用层行为，pymongo 不自动补——排序/展示都依赖它，必须自己写。
    # 存 UTC 时刻（汀家时区合同：Mongo 存 UTC，展示端转北京时间），tz-aware 编码为 BSON Date。
    now = datetime.now(UTC)

    try:
        _ = await get_db()[COLLECTION].insert_one(
            {
                # userId 必须是 ObjectId：Mongoose schema 类型如此，
                # Node 读接口按 ObjectId 查——写 str 是 BSON 类型不匹配，记录成孤儿查不出
                "userId": oid(user_id),
                "sessionCode": session_code,
                "question": question,
                "answer": answer,
                "reqId": req_id,
                "status": status,
                "createdAt": now,
                "updatedAt": now,
            }
        )
    except DuplicateKeyError:
        # reqId 唯一索引命中：同一次请求重复落库，幂等吞掉（与 Node 落库语义一致）
        return False

    return True
