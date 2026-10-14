#!/usr/bin/env bash
# JARVIS — NORMAL mode.
# Real Claude Code brain, your connectors, no scripted answers. This is the
# honest assistant anyone building it should run.
#
# Run from a normal Terminal window (not inside a Claude Code session).
cd "$(dirname "$0")" || exit 1
unset CLAUDECODE CLAUDE_CODE_SESSION_ID CLAUDE_CODE_ENTRYPOINT ANTHROPIC_AUTH_TOKEN ANTHROPIC_API_KEY
PORT="${JARVIS_PORT:-$(grep -s '^JARVIS_PORT=' .env | cut -d= -f2)}"; PORT="${PORT:-8730}"
if lsof -ti tcp:"$PORT" >/dev/null 2>&1; then
  echo "Port $PORT is already in use. Stop that process, or set JARVIS_PORT in .env." >&2
  exit 1
fi
exec python3 server.py
