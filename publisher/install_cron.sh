#!/bin/bash
# 在服务器上安装每天 06:00（北京时间）的 cron
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${ROOT}/publisher/.venv/bin/python"
if [[ ! -x "$PY" ]]; then
  PY="$(command -v python3)"
fi
LOG=/var/log/video-parse-daily.log
touch "$LOG"
CRON_LINE="0 6 * * * TZ=Asia/Shanghai $PY $ROOT/publisher/daily_publish.py >> $LOG 2>&1"
tmp="$(mktemp)"
crontab -l 2>/dev/null | grep -v "daily_publish.py" >"$tmp" || true
echo "$CRON_LINE" >>"$tmp"
crontab "$tmp"
rm -f "$tmp"
echo "已安装 cron："
echo "$CRON_LINE"
crontab -l | grep daily_publish.py
