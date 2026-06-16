#!/bin/sh
set -e

# Seed the domain config on first start so a mounted (empty) /config volume gets
# a real, editable file. An existing file is never overwritten.
: "${ZILPZALP_CONFIG:=/config/config.yaml}"
if [ ! -f "$ZILPZALP_CONFIG" ]; then
    mkdir -p "$(dirname "$ZILPZALP_CONFIG")"
    cp /app/backend/config.default.yaml "$ZILPZALP_CONFIG"
fi

exec "$@"
