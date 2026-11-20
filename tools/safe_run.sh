#!/bin/bash
# USAGE: tools/safe_run.sh [-m MAX_GB] [-t MAX_MINUTES] -- command args...
# Runs one command at low priority with thread caps, and kills it (and its children) if its total
# resident memory passes MAX_GB (default 6) or it runs longer than MAX_MINUTES (default 20).
# Refuses to start if another safe_run job is already running (one heavy job at a time).
MAX_GB=6; MAX_MIN=20
while [ "$1" != "--" ] && [ $# -gt 0 ]; do case "$1" in -m) MAX_GB=$2; shift 2;; -t) MAX_MIN=$2; shift 2;; *) echo "bad arg $1"; exit 2;; esac; done
shift
LOCK=/tmp/rocker_safe_run.lock
if [ -f "$LOCK" ] && kill -0 "$(cat $LOCK)" 2>/dev/null; then echo "safe_run: another job (pid $(cat $LOCK)) is running; refusing"; exit 3; fi
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 VECLIB_MAXIMUM_THREADS=2 NUMEXPR_NUM_THREADS=2 OPENCV_FOR_THREADS_NUM=2
nice -n 15 "$@" &
PID=$!; echo $PID > $LOCK; START=$(date +%s); PEAK=0
rss_kb() { local t=0 p; for p in $1 $(pgrep -P $1 2>/dev/null); do t=$((t + $(ps -o rss= -p $p 2>/dev/null | tr -d ' ' || echo 0))); for c in $(pgrep -P $p 2>/dev/null); do [ "$p" != "$1" ] && t=$((t + $(ps -o rss= -p $c 2>/dev/null | tr -d ' ' || echo 0))); done; done; echo $t; }
while kill -0 $PID 2>/dev/null; do
  R=$(rss_kb $PID); [ "$R" -gt "$PEAK" ] && PEAK=$R
  if [ "$R" -gt $((MAX_GB*1024*1024)) ]; then echo "safe_run: KILLED, memory $((R/1024)) MB over ${MAX_GB} GB cap"; pkill -P $PID; kill -9 $PID; rm -f $LOCK; exit 137; fi
  if [ $(( $(date +%s) - START )) -gt $((MAX_MIN*60)) ]; then echo "safe_run: KILLED, over ${MAX_MIN} min"; pkill -P $PID; kill -9 $PID; rm -f $LOCK; exit 124; fi
  sleep 1
done
wait $PID; RC=$?; rm -f $LOCK
echo "safe_run: exit $RC, peak memory $((PEAK/1024)) MB, $(( $(date +%s) - START )) s"; exit $RC
