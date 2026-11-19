#!/bin/bash
cd "$(dirname "$0")/.."
for pid in /proc/[0-9]*; do
  p=${pid#/proc/}
  c=$(tr '\0' ' ' < "$pid/cmdline" 2>/dev/null)
  case "$c" in *"run_pan"el.py*|*"pan"el.py*) kill -TERM "$p" 2>/dev/null;; esac
done
sleep 1
setsid nohup python3 -u run_panel.py > data/panel.log 2>&1 < /dev/null &
sleep 2
echo "panel: http://127.0.0.1:8790"
