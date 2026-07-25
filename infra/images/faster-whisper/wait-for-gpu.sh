#!/usr/bin/env bash
set -euo pipefail

NVIDIA_SMI="${NVIDIA_SMI:-/usr/lib/wsl/lib/nvidia-smi}"
MAX_USED_MIB="${WHISPER_START_MAX_GPU_USED_MIB:-2500}"

while true; do
  used="$("$NVIDIA_SMI" --query-gpu=memory.used --format=csv,noheader,nounits | head -1 | tr -d ' ')"
  if [[ "$used" =~ ^[0-9]+$ ]] && (( used <= MAX_USED_MIB )); then
    exit 0
  fi
  sleep 15
done
