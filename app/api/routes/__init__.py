# app/api/routes/__init__.py
# 目标职责：所有业务子路由在此汇总为一个 api_router，main.py 只挂这一个对象。
from fastapi import APIRouter

# 导入路由
from app.api.routes.agent import agent_router
from app.api.routes.health import health_router

# 导入配置
from app.core.config import settings

api_router = APIRouter()

# 挂载子路由
api_router.include_router(health_router)
api_router.include_router(agent_router)

# M2 调试路由仅 local 挂载：Swagger 直调读工具用，prod 不可达
if settings.app_env == "local":
    from app.api.routes import tools

    api_router.include_router(tools.router)
