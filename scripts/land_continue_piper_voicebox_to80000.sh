#!/usr/bin/env bash
set -Eeuo pipefail

root=/home/ubuntu/piper-voice
source_root="$root/voicebox-diverse5000-final-sim090/training-stages4800"
run_root="$root/voicebox-diverse5000-final-sim090/training-long-80000"
dataset="$source_root/speaker-consistency/metadata-speaker-accepted.csv"
audio_dir="$root/voicebox-diverse5000-final-sim090/piper_dataset/wav"
config="$root/ze-studio387-fp32-2026-07-28/config-step300.yaml"
model_config="$root/ze-studio387-fp32-2026-07-28/step300/model.onnx.json"
evaluator="$root/evaluate_tts_suite.py"
reference="$root/real-v3-dataset-2026-07-28/reference9.wav"
previous="$source_root/step4800/step4800.ckpt"
dataset_sha256=$(tr -d '[:space:]' <"$root/voicebox-diverse5000-final-sim090/.dataset-ready")

mkdir -p "$run_root"
exec 9>"$root/.gahyeon-piper-training.lock"
if ! flock -n 9; then
  echo "Another Gahyeon Piper pipeline owns the worker lock" >&2
  exit 75
fi

for required in "$dataset" "$config" "$model_config" "$evaluator" "$reference" "$previous"; do
  [[ -s "$required" ]] || { echo "Missing required input: $required" >&2; exit 2; }
done

write_state() {
  local status=$1 stage=$2
  local temporary="$run_root/STATE.json.tmp.$$"
  printf '{\n  "schema": "gahyeon-piper-long-training-v1",\n  "status": "%s",\n  "stage": "%s",\n  "datasetSha256": "%s",\n  "sourceCheckpoint": "%s",\n  "targets": [10000, 20000, 40000, 80000],\n  "updatedAt": "%s"\n}\n' \
    "$status" "$stage" "$dataset_sha256" "$source_root/step4800/step4800.ckpt" \
    "$(date --iso-8601=seconds)" >"$temporary"
  mv "$temporary" "$run_root/STATE.json"
}

current_stage=preflight
on_error() {
  local exit_code=$?
  trap - ERR
  write_state failed "$current_stage"
  exit "$exit_code"
}
trap on_error ERR

eval_texts=(
  '안녕하세요. 오늘 서버 상태와 프로젝트 진행 상황을 정확하게 알려드리겠습니다.'
  'GPU 사용률은 72퍼센트이고, API 응답 시간은 183밀리초입니다.'
  '정말 잘됐네요! 생각보다 훨씬 자연스럽게 완성됐어요.'
  '지금 바로 실행할까요, 아니면 설정을 한 번 더 확인할까요?'
  '오류가 다시 발생하더라도 당황하지 말고 로그를 확인한 다음 안전하게 복구하면 됩니다.'
)

evaluate_model() {
  local stage=$1 model=$2
  local suite="$stage/evaluation-suite-input.jsonl"
  : >"$suite"
  for index in "${!eval_texts[@]}"; do
    local number=$((index + 1))
    local wav="$stage/eval-$number.wav"
    printf '%s\n' "${eval_texts[$index]}" | "$root/.venv-cu126/bin/piper" \
      --model "$model" --config "$model_config" \
      --length-scale 0.92 --noise-scale 0.55 --noise-w-scale 0.65 \
      --output-file "$wav"
    printf '{"id":%d,"audio":"%s","text":"%s"}\n' \
      "$number" "$wav" "${eval_texts[$index]}" >>"$suite"
  done
  "$root/.venv-cu126/bin/python" "$evaluator" \
    --suite "$suite" --reference "$reference" --output "$stage/evaluation-suite.json"
}

write_state running preflight
for target in 10000 20000 40000 80000; do
  stage="$run_root/step$target"
  final_ckpt="$stage/step$target.ckpt"
  mkdir -p "$stage"
  current_stage="training_step_$target"
  write_state running "$current_stage"

  if [[ ! -s "$final_ckpt" ]]; then
    cd "$root"
    env PATH="/usr/lib/wsl/lib:$PATH" PIPER_FINAL_CKPT="$final_ckpt" \
      "$root/.venv/bin/python" -m piper.train fit \
      --config "$config" \
      --trainer.max_steps="$target" \
      --trainer.default_root_dir="$stage/run" \
      --trainer.precision=32-true \
      --model.learning_rate=2e-5 \
      --model.learning_rate_d=1e-5 \
      --data.csv_path="$dataset" \
      --data.audio_dir="$audio_dir" \
      --data.cache_dir="$source_root/cache" \
      --data.voice_name=gahyeon_voicebox_diverse5000_long \
      --ckpt_path="$previous" >"$stage/train.log" 2>&1
  fi

  [[ -s "$final_ckpt" ]]
  if grep -Eqi 'CUDA out of memory|I/O error|Input/output error|Xid|nan|inf loss' "$stage/train.log"; then
    echo "Unsafe training signature detected at target=$target" >&2
    exit 3
  fi

  current_stage="export_step_$target"
  write_state running "$current_stage"
  cd "$root"
  "$root/.venv/bin/python" -m piper.train.export_onnx \
    --checkpoint "$final_ckpt" --output-file "$stage/model.onnx" \
    >"$stage/export.log" 2>&1
  cp "$model_config" "$stage/model.onnx.json"
  "$root/.venv-cu126/bin/python" -c \
    'import onnx,sys; onnx.checker.check_model(onnx.load(sys.argv[1]))' "$stage/model.onnx"

  current_stage="evaluation_step_$target"
  write_state running "$current_stage"
  evaluate_model "$stage" "$stage/model.onnx"
  (
    cd "$stage"
    sha256sum step"$target".ckpt model.onnx model.onnx.json \
      evaluation-suite.json eval-*.wav >SHA256SUMS
  )
  previous="$final_ckpt"
done

write_state complete step80000
trap - ERR
