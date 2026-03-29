#!/usr/bin/env bash
set -euo pipefail

if pgrep -af "vllm.*Voxtral-4B-TTS-2603" >/dev/null 2>&1; then
  pkill -f "vllm.*Voxtral-4B-TTS-2603"
  echo "[voxtral-wsl] Voxtral server stop signal sent."
else
  echo "[voxtral-wsl] No matching Voxtral server process found."
fi

