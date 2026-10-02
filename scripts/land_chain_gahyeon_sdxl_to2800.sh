#!/usr/bin/env bash
set -euo pipefail

root=/opt/zaeze-ai/training/gahyeon-sdxl-v1
source_pid_file="$root/continued-from0800.pid"
source_log="$root/logs/continued-from0800-run.log"
source_weights="$root/outputs/gahyeon-sdxl-v1-continued-from0800.safetensors"
next_log="$root/logs/continued-from2000-run.log"

source_pid=$(tr -d '[:space:]' <"$source_pid_file")
[[ "$source_pid" =~ ^[0-9]+$ ]]
if [[ -r "/proc/$source_pid/cmdline" ]]; then
  source_command=$(tr '\0' ' ' <"/proc/$source_pid/cmdline")
  [[ "$source_command" == *"sdxl_train_network.py"* ]]
  [[ "$source_command" == *"--output_name gahyeon-sdxl-v1-continued-from0800"* ]]
fi

while kill -0 "$source_pid" 2>/dev/null; do
  sleep 30
done

[[ -s "$source_weights" ]]
if grep -Eiq "nan|out of memory|cuda error|traceback|failed|killed" "$source_log"; then
  printf 'source training log contains a terminal error; refusing chained training\n' >&2
  exit 1
fi
[[ -z "$(pgrep -f '[s]dxl_train_network.py' || true)" ]]
[[ "$(systemctl is-active zaeze-comfyui.service || true)" == "inactive" ]]
[[ "$(free -g | awk '/^Mem:/ {print $7}')" -ge 8 ]]
[[ "$(df --output=avail -BG /opt/zaeze-ai | tail -1 | tr -dc '0-9')" -ge 100 ]]
gpu_free=$(nvidia-smi --query-gpu=memory.free --format=csv,noheader,nounits | tr -d '[:space:]')
[[ "$gpu_free" =~ ^[0-9]+$ ]]
[[ "$gpu_free" -ge 4096 ]]

nohup "$root/land_continue_gahyeon_sdxl_lora_from2000.sh" >"$next_log" 2>&1 </dev/null &
next_pid=$!
printf '%s\n' "$next_pid" >"$root/continued-from2000.pid"
printf 'started continuation from total step 2000: pid=%s\n' "$next_pid"
