#app/api/routes/__init__.py
# 目标职责：所有业务子路由在此汇总为一个 api_router，main.py 只挂这一个对象。
from fastapi import APIRouter
# 导入健康检查子路由
from app.api.routes import health

api_router = APIRouter()

# 挂载子路由
api_router.include_router(health.router)
