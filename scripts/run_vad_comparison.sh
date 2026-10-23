#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fixture_dir="${1:?Usage: run_vad_comparison.sh FIXTURE_DIRECTORY}"
export VAD_BENCHMARK_DIR="$(cd "$fixture_dir" && pwd)"
if [[ "$(uname -s)" != Linux && -z "${TEN_VAD_LIBRARY_PATH:-}" ]]; then
  echo 'Set TEN_VAD_LIBRARY_PATH to the official native library for this platform.' >&2
  exit 1
fi
cd "$repo_root"
# Gradle does not track the external fixture directory/environment as task inputs.
./gradlew test --rerun-tasks --tests 'com.gahyeonbot.adapters.speech.VadComparisonTest'
