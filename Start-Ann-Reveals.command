#!/bin/bash
set -eu
cd "$(dirname "$0")"
exec python3 scripts/start_local.py
