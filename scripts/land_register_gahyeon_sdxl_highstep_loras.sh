#!/usr/bin/env bash
set -euo pipefail

root=/opt/zaeze-ai/training/gahyeon-sdxl-v1/outputs
loras=/opt/zaeze-ai/comfyui/models/loras
files=(
  gahyeon-sdxl-v1-continued-from0800-step00000400.safetensors
  gahyeon-sdxl-v1-continued-from0800-step00000800.safetensors
  gahyeon-sdxl-v1-continued-from0800-step00001200.safetensors
  gahyeon-sdxl-v1-continued-from2000-step00000400.safetensors
  gahyeon-sdxl-v1-continued-from2000-step00000800.safetensors
)

mkdir -p "$loras"
for name in "${files[@]}"; do
  source="$root/$name"
  target="$loras/$name"
  [[ -s "$source" ]]
  sha256sum "$source"
  if [[ -L "$target" ]]; then
    [[ "$(readlink -f "$target")" == "$source" ]]
  elif [[ -e "$target" ]]; then
    printf 'refusing to replace non-symlink: %s\n' "$target" >&2
    exit 1
  else
    ln -s "$source" "$target"
  fi
done
