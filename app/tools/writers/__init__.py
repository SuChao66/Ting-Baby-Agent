# app/tools/writers/__init__.py
# 目标与职责：写工具共享设施——时间适配。纯日期在「今天」时补当前时刻，
# 带时刻的值附加本地时区偏移，与前端 toLocalISOString 同构，服务器任何时区都能正确比较。

# 导入正则表达式模块
import re
from datetime import date, datetime

# 纯日期：YYYY-MM-DD
_DATE_ONLY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _local_iso(dt: datetime) ->str:
    """ naive 本地时间 -> 带时区偏移的 ISO 字符串（2026-11-09T10:30:00+08:00）。 """

    return dt.astimezone().isoformat(timespec="seconds")

# 写时间
def write_time(value: str) -> str:
    """ 把 LLM/调试传来的时间统一成 Node API 能正确校验的 ISO 字符串。

    - 纯日期 YYYY-MM-DD：今天 -> 补成当前时刻（避开早8点前被 Node 拒的坑）；
      过去日期原样透传（Node 按 UTC 零点解析，必然早于当前）；未来日期原样透传
      （Node 自己会拒，错误文案更友好）。
    - 带时刻：解析后若没带时区则附加本地偏移（astimezone），与前端提交格式同构。
    """

    text = value.strip()  # 去掉前后空格
    if _DATE_ONLY.fullmatch(text):  # 纯日期
        if text == date.today().isoformat():  # 今天
            return _local_iso(datetime.now())  # 补当前时刻
            
        return text  # 过去或未来日期，原样透传
    
    parsed = datetime.fromisoformat(text.replace(" ", "T"))  # 带时刻
    if parsed.tzinfo is None:  # 未指定时区
        return parsed.isoformat(timespec="seconds")
        
    return _local_iso(parsed)