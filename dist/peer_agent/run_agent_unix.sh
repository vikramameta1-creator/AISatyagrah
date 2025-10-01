#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
INBOX="$ROOT/inbox"
OUTBOX="$ROOT/out"
STATE="$ROOT/agent_state.db"
CFG="$ROOT/agent_config.json"
SDHOST=""

if [[ -z "${SATYAGRAH_SECRET:-}" ]]; then
  echo "[ERROR] SATYAGRAH_SECRET is not set. See README.txt" >&2
  exit 1
fi

mkdir -p "$INBOX" "$OUTBOX"
python -m satyagrah.peer.agent run --inbox "$INBOX" --outbox "$OUTBOX" --state "$STATE" --config "$CFG" --panel-port 8090 $SDHOST
