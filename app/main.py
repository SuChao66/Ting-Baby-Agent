#!/usr/bin/env python3
# -*- coding:utf-8 -*-
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.routes import api_router
from app.core.config import settings
from app.core.database import init_mongo, close_mongo
from app.core.exceptions import register_exception_handlers
from app.core.logger import get_logger, setup_logging

# 必须先于其他模块的get_logger使用
setup_logging()
logger = get_logger(__name__)

class ReuqestLogMiddleware(BaseHTTPMiddleware):
    """ 请求日志：只记method/path/status/耗时，不记任何请求头（Authorization 是凭据） """

    async def dispatch(self, request: Request, call_next):
        # 开始时间
        start = time.perf_counter()
        response = await call_next(request)
        # 花费时间
        cost_ms = (time.perf_counter() - start) * 1000
        # 打印日志
        logger.info("%s %s -> %s (%.1fms)",
                    request.method, request.url.path, response.status_code, cost_ms)

        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：建 Motor 客户端（惰性，不联网）
    init_mongo()
    logger.info("汀家 Agent 启动完成 env=%s", settings.app_env)
    yield
    # 关闭：释放连接池
    await close_mongo()
    logger.info("汀家 Agent 已关闭")

app = FastAPI(
    title="Ting Baby Agent",
    description="汀宝宝 AI 对话主入口服务",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS：cors_origins 支持 “*” 或者逗号分隔列表
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 请求日志（注意：add_middleware 是「后加的在外层」，先加 CORS 再加日志）
app.add_middleware(ReuqestLogMiddleware)
# 异常处理器
register_exception_handlers(app)
# 路由
app.include_router(api_router)


