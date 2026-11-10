# Author: SuChao
# Date: 2026-11-06
# desc: 全项目唯一的配置出口，.env 里定义的变量在此收口为类型安全的 settings 单例。
# 任何模块需要配置，只需要 from app.core.config import settings，
# 绝不在业务代码里直接 os.environ 或散落读取 .env。
# app/core/config.py

from typing import ClassVar, Literal

# 应用配置管理
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    全局配置：字段名小写下划线，自动匹配.env中的同名大写变量（大小写不敏感）.
    """

    # 运行环境：Local（本地开发）/ prod（生产）
    app_env: Literal["local", "prod"] = "local"
    log_level: str = "INFO"

    # 服务器地址
    mongo_uri: str = "mongodb://localhost:27017/ting-baby-memories"  # 本地mongo地址

    # 与汀宝宝共享的 JWT secret（真实值取自 backend .env 的 jwtSecret）
    jwt_secret: str = "change_me"

    # LLM 配置
    deepseek_api_key: str = "change_me"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-flash"
    deepseek_time_out: int = 60000
    deepseek_temperature: float = 0.7

    # 汀宝宝 Node 后端（写工具经此调用，JWT 透传）
    node_api_base_url: str = "http://127.0.0.1:3000"

    # 多模态（M5 用）
    vision_provider: str = "qwen"
    dashscope_api_key: str = "change_me"

    # Agent 护栏（M4 用）
    agent_max_iters: int = 6

    # 前端直连 Agent 属跨域；"*" 表示放行全部（仅 local 用）
    cors_origins: str = "*"

    model_config: ClassVar[SettingsConfigDict] = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # 忽略未知字段
    )


# 模块级单例：import时创建一次，全项目共享
settings = Settings()
