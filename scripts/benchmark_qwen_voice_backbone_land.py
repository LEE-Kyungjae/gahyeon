#!/usr/bin/env python3
"""Bounded one-process benchmark for the cached Qwen voice-clone backbone on land."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

import soundfile as sf
import torch
from qwen_tts import Qwen3TTSModel


CASES = (
    ("ko-short", "Korean", "잠깐만, 지금 확인해 볼게."),
    ("ko-expression-text", "Korean", "진짜? 정말 온 거야?"),
    ("en-github", "English", "I checked the GitHub repository before answering."),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--reference-text", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dtype", choices=("float16", "float32"), default="float32")
    args = parser.parse_args()

    if not args.model_path.is_dir() or not args.reference.is_file():
        raise SystemExit("model path and reference audio must already exist")
    args.output.mkdir(parents=True, exist_ok=True)
    result_path = args.output / "result.json"
    started_wall = time.time()
    result = {
        "schemaVersion": 1,
        "status": "running",
        "modelId": args.model_id,
        "modelPath": str(args.model_path),
        "dtype": args.dtype,
        "quantization": f"none-{args.dtype}",
        "referenceSha256": sha256(args.reference),
        "expressionControl": False,
        "note": "Base voice-clone baseline; text may sound expressive but no instruction control is claimed.",
        "startedAtEpochSeconds": started_wall,
        "cases": [],
    }
    atomic_json(result_path, result)

    try:
        os.environ.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        torch.cuda.reset_peak_memory_stats()
        load_started = time.perf_counter()
        model = Qwen3TTSModel.from_pretrained(
            str(args.model_path),
            device_map="cuda",
            dtype=torch.float32 if args.dtype == "float32" else torch.float16,
            attn_implementation="eager",
        )
        result["loadSeconds"] = round(time.perf_counter() - load_started, 3)
        prompt_started = time.perf_counter()
        prompt = model.create_voice_clone_prompt(
            ref_audio=str(args.reference),
            ref_text=args.reference_text,
            x_vector_only_mode=False,
        )
        result["promptSeconds"] = round(time.perf_counter() - prompt_started, 3)

        for index, (case_id, language, text) in enumerate(CASES):
            torch.manual_seed(20260819 + index)
            inference_started = time.perf_counter()
            wavs, sample_rate = model.generate_voice_clone(
                text=text,
                language=language,
                voice_clone_prompt=prompt,
            )
            elapsed = time.perf_counter() - inference_started
            output = args.output / f"{index + 1:02d}-{case_id}.wav"
            temporary = output.with_suffix(".tmp.wav")
            sf.write(temporary, wavs[0], sample_rate, subtype="PCM_16")
            os.replace(temporary, output)
            duration = len(wavs[0]) / sample_rate
            result["cases"].append({
                "id": case_id,
                "language": language,
                "text": text,
                "output": str(output),
                "sha256": sha256(output),
                "audioSeconds": round(duration, 3),
                "inferenceSeconds": round(elapsed, 3),
                "rtf": round(elapsed / duration, 3) if duration > 0 else None,
            })
            atomic_json(result_path, result)

        result["status"] = "completed"
        result["peakGpuAllocatedBytes"] = int(torch.cuda.max_memory_allocated())
        result["completedAtEpochSeconds"] = time.time()
        atomic_json(result_path, result)
    except BaseException as failure:
        result["status"] = "failed"
        result["errorType"] = type(failure).__name__
        result["error"] = str(failure)[:500]
        result["completedAtEpochSeconds"] = time.time()
        atomic_json(result_path, result)
        raise


if __name__ == "__main__":
    main()
