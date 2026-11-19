#!/bin/bash
cd "$(dirname "$0")/.."
for pid in /proc/[0-9]*; do
  p=${pid#/proc/}
  c=$(tr '\0' ' ' < "$pid/cmdline" 2>/dev/null)
  case "$c" in *"run_cra"wl.py*) kill -TERM "$p" 2>/dev/null && echo "stopped $p";; esac
done
