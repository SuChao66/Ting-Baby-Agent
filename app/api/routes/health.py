# app/api/routes/health.py
# 目标与职责：两个探针
# /healthz 进程存活（liveness，永远 200）；
# /readyz 就绪检查（readiness，探 MongoDB 连通性）

from typing import Any

from fastapi import APIRouter

from app.core.database import get_db
from app.core.logger import get_logger
from app.schemas.response import ApiResponse, ok

# 实例化日志
logger = get_logger(__name__)

# 实例化路由
health_router = APIRouter(tags=["health"])


@health_router.get("/healthz", response_model=ApiResponse[dict[str, Any]])
async def healthz() -> ApiResponse[dict[str, Any]]:
    """存活探针：进程活着就200， 不碰外部依赖。"""
    return ok(data={"status": "ok"})


@health_router.get("/readyz", response_model=ApiResponse[dict[str, Any]])
async def readyz() -> ApiResponse[dict[str, Any]]:
    """就绪探针：ping MongoDB（只读操作）。连不上仍返回 200，
    由 data.mongo 表达状态，方便前端/脚本肉眼判断。"""
    try:
        _ = await get_db().command("ping")  # 返回体用不上，_ 显式丢弃
        mongo = "connected"
    except Exception:
        # 本地没开 Mongo / 隧道断开：不让探针 500，标记 disconnected 即可
        mongo = "disconnected"
    return ok(data={"status": "ready" if mongo == "connected" else "degraded", "mongo": mongo})
