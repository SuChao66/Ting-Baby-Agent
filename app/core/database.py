# app/core/database.py
from typing import Any

from pymongo import AsyncMongoClient
from pymongo.asynchronous.database import AsyncDatabase
# 引入自定义配置
from app.core.config import settings
# 引入日志
from app.core.logger import get_logger

logger = get_logger(__name__)

# 进程内唯一的客户端：None表示未初始化
_client: AsyncMongoClient[Any] | None = None

def init_mongo() -> AsyncMongoClient[Any]:
    """ 创建 Mongo 客户端（幂等：重复调用返回已有实例）。 """
    global _client

    if _client is not None:
        return _client

    _client = AsyncMongoClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=3000,  # 连不上 3 秒即报错，避免 /readyz 长阻塞
        maxPoolSize=80,
        minPoolSize=5,
    )
    logger.info("MongoDB 客户端已初始化 env=%s", settings.app_env)
    return _client

async def close_mongo() -> None:
    """ 关闭 Mongo 客户端。 """
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("MongoDB 客户端已关闭")

def get_db() -> AsyncDatabase[Any]:
    """ 取默认数据库，库名取自 MONGO_URI 中的 / ting-baby-memories，不在代码里写死。"""
    if _client is None:
        raise RuntimeError("MongoDB 客户端未初始化，请先调用init_mongo()")
    return _client.get_default_database()
