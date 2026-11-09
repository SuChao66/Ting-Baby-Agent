#!/usr/bin/env bash
# scripts/tunnel.sh —— 本地 -> VPS MongoDB 的 SSH 隧道
# 用法:
#   ./scripts/tunnel.sh <SSH别名或user@host> [远程端口] [本地端口]   # 前台建隧道，Ctrl+C 断开
#   ./scripts/tunnel.sh status                                       # 查看隧道监听状态
#   ./scripts/tunnel.sh ping                                         # 经隧道 ping MongoDB（验证可达）
# 效果: 本地 127.0.0.1:27018 的流量被转发到 VPS 的 127.0.0.1:27017
set -euo pipefail

REMOTE_PORT_DEFAULT=27017
LOCAL_PORT_DEFAULT=27018

port_listeners() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN 2>/dev/null || true
}

cmd="${1:-}"
case "$cmd" in
  status)
    if [ -n "$(port_listeners "$LOCAL_PORT_DEFAULT")" ]; then
      echo "隧道在线：本地 ${LOCAL_PORT_DEFAULT} 端口监听中"
      port_listeners "$LOCAL_PORT_DEFAULT"
    else
      echo "隧道离线：本地 ${LOCAL_PORT_DEFAULT} 无监听"
    fi
    ;;
  ping)
    if [ -z "$(port_listeners "$LOCAL_PORT_DEFAULT")" ]; then
      echo "隧道不在线，先运行: ./scripts/tunnel.sh <SSH别名>" >&2
      exit 1
    fi
    ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
    PYTHON="$ROOT_DIR/.venv/bin/python"
    if [ ! -x "$PYTHON" ]; then
      echo "未找到 .venv/bin/python，请先在项目根目录建虚拟环境" >&2
      exit 1
    fi
    "$PYTHON" - <<PYEOF
from pymongo import MongoClient

client = MongoClient("mongodb://127.0.0.1:${LOCAL_PORT_DEFAULT}/?serverSelectionTimeoutMS=3000")
print("ping:", client.admin.command("ping"))
print("mongo 版本:", client.server_info().get("version"))
PYEOF
    ;;
  -h|--help|"")
    grep '^#' "$0" | grep -v '^#!' | sed 's/^# \{0,1\}//'
    ;;
  *)
    SSH_TARGET="$cmd"
    REMOTE_PORT="${2:-$REMOTE_PORT_DEFAULT}"
    LOCAL_PORT="${3:-$LOCAL_PORT_DEFAULT}"
    if [ -n "$(port_listeners "$LOCAL_PORT")" ]; then
      echo "本地 ${LOCAL_PORT} 已有监听（隧道可能已在运行）。查看: ./scripts/tunnel.sh status" >&2
      exit 1
    fi
    echo "隧道建立中: 本地 127.0.0.1:${LOCAL_PORT} -> 远端 127.0.0.1:${REMOTE_PORT}（Ctrl+C 断开）"
    exec ssh -N \
      -L "127.0.0.1:${LOCAL_PORT}:127.0.0.1:${REMOTE_PORT}" \
      -o ExitOnForwardFailure=yes \
      -o ServerAliveInterval=30 \
      -o ServerAliveCountMax=3 \
      -o ConnectTimeout=10 \
      "${SSH_TARGET}"
    ;;
esac
