# app/tools/registry.py
# 目标与职责：读工具白名单，唯一注册入口；M3 会有平行的 WRITE_TOOLS（写工具显式标注）。

# 抽象基类：Awaitable，表示“可以被 await 的对象”。
# Callable: 表示“可被调用的对象”。Callable[[int], str] 表示“接受一个 int 参数，返回一个 str 对象的函数”。
from collections.abc import Awaitable, Callable
from typing import Any

# 工具函数统一形态：异步、参数全是JSON可序列化的简单值
ToolFunc = Callable[..., Awaitable[Any]]

# 读工具白名单：name -> 函数
READ_TOOLS: dict[str, ToolFunc] = {}


def read_tool(name: str) -> Callable[[ToolFunc], ToolFunc]:
    """ 注册装饰器：把函数挂进白名单。重名直接报错——宁可启动炸也不静默覆盖。 """

    def decorator(fn: ToolFunc) -> ToolFunc:
        if name in READ_TOOLS:
            raise ValueError(f"read tool'{name}' already exists")
        READ_TOOLS[name] = fn
    
        return fn

    return decorator