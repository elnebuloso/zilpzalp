#!/bin/sh
# Dev server controller for the ZilpZalp backend (uv + uvicorn).
#
# Runs a single uvicorn process on 127.0.0.1:8000 with isolated runtime data under
# .dev/backend/, so an agent can bring the app up for manual or Playwright checks and
# tear it down cleanly. No --reload (single process => portable `kill` stop).
set -eu

HOST=127.0.0.1
PORT=8000

# Repo root, resolved from this script's location (scripts/devserver.sh -> repo root).
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

DEV_DIR="$ROOT/.dev/backend"
CONFIG_DIR="$DEV_DIR/config"
CONFIG_FILE="$CONFIG_DIR/config.yaml"
DATA_DIR="$DEV_DIR/data"
PID_FILE="$DEV_DIR/devserver.pid"
LOG_FILE="$DEV_DIR/devserver.log"
HEALTH_URL="http://$HOST:$PORT/healthz/live"

is_running() {
    [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

cmd_start() {
    if is_running; then
        echo "Dev server already up (PID $(cat "$PID_FILE")) at http://$HOST:$PORT"
        return 0
    fi

    mkdir -p "$CONFIG_DIR"
    if [ ! -f "$CONFIG_FILE" ]; then
        cp "$ROOT/backend/config.default.yaml" "$CONFIG_FILE"
    fi

    export ZILPZALP_CONFIG="$CONFIG_FILE"
    export ZILPZALP_PATH_INBOX="$DATA_DIR/inbox"
    export ZILPZALP_PATH_ERROR="$DATA_DIR/error"
    export ZILPZALP_PATH_TRASH="$DATA_DIR/trash"
    export ZILPZALP_PATH_CACHE="$DATA_DIR/cache"
    export ZILPZALP_PATH_OUTBOX="$DATA_DIR/outbox"

    cd "$ROOT/backend"
    uv run uvicorn zilpzalp.main:app --host "$HOST" --port "$PORT" >"$LOG_FILE" 2>&1 &
    echo $! >"$PID_FILE"

    # Health gate: poll until live or ~15s timeout.
    i=0
    while [ "$i" -lt 15 ]; do
        if curl -fsS "$HEALTH_URL" >/dev/null 2>&1; then
            echo "Dev server up at http://$HOST:$PORT"
            return 0
        fi
        i=$((i + 1))
        sleep 1
    done

    echo "Dev server failed to become healthy within 15s; last log lines:" >&2
    tail -n 20 "$LOG_FILE" >&2
    cmd_stop >/dev/null 2>&1 || true
    return 1
}

cmd_stop() {
    if ! is_running; then
        rm -f "$PID_FILE"
        echo "Dev server not running"
        return 0
    fi
    pid=$(cat "$PID_FILE")
    kill -TERM "$pid" 2>/dev/null || true
    i=0
    while [ "$i" -lt 10 ] && kill -0 "$pid" 2>/dev/null; do
        i=$((i + 1))
        sleep 1
    done
    rm -f "$PID_FILE"
    echo "Dev server stopped"
}

cmd_status() {
    if is_running; then
        echo "up (PID $(cat "$PID_FILE")) at http://$HOST:$PORT"
    else
        echo "down"
    fi
}

cmd_logs() {
    [ -f "$LOG_FILE" ] || { echo "no log file yet"; return 0; }
    tail -f "$LOG_FILE"
}

case "${1:-}" in
    start)  cmd_start ;;
    stop)   cmd_stop ;;
    status) cmd_status ;;
    logs)   cmd_logs ;;
    *)
        echo "usage: $0 {start|stop|status|logs}" >&2
        exit 2
        ;;
esac
