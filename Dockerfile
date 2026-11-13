# ============================================
# 汀家 Agent（ting-baby-agent）镜像
# ============================================
# 构建在汀宝宝仓库根目录执行：docker compose build agent
# 配置全部来自环境变量（compose env_file: .env.agent 注入），容器内不需要 .env 文件
# ============================================

FROM python:3.13-slim

# TZ：业务代码显式用 Asia/Shanghai（app/tools/shared.py 的 ZoneInfo("Asia/Shanghai")），
# slim 镜像不保证自带 tzdata，缺了会在 import 时直接抛 ZoneInfoNotFoundError
ENV TZ=Asia/Shanghai \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

# 先装依赖再拷代码：依赖没变时，改代码不触发重新下载
COPY requirements.lock.txt ./
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir -r requirements.lock.txt

COPY app ./app

# 进程存活探针：/healthz 不碰外部依赖，永远 200（slim 无 curl，用 Python 内置库）
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"]

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
