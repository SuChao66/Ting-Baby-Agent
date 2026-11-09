# app/tools/__init__.py
# 目标与职责：读工具模块装载点——装饰器注册靠 import 副作用，六个 reader 必须在此显式导入，
# READ_TOOLS 白名单才会填充（阶段四自查与调试路由都依赖这一点）。
from app.tools.readers import baby, care, growth, health, milestone, vaccine  # noqa: F401
