# app/core/logger.py
import logging
import sys

from app.core.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging() -> None:
    """
    初始化根 logger。应用入口 main.py 调用一次即可。
    """
    # 第三方库噪音：pymongo 拓扑/心跳/命令 DEBUG 压到 WARNING（幂等，reload 二次加载也生效）
    logging.getLogger("pymongo").setLevel(logging.WARNING)
    root = logging.getLogger()
    if root.handlers:
        # 已有handler，当uvicorn --reload 二次加载等场景时，不再重复添加
        root.setLevel(settings.log_level.upper())
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, _DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())


# 获取各模块对应的logger
def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的子 logger。
    """
    return logging.getLogger(name)
