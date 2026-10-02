#!/usr/bin/env python3
"""Record Core-contract Qwen C runtime style samples and latency evidence."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import time
import urllib.error
import urllib.request
import wave
from pathlib import Path


DEFAULT_STYLES = ("natural", "bright", "surprised", "annoyed", "sad")


def inspect_wav(audio: bytes) -> dict[str, float | int]:
    with wave.open(io.BytesIO(audio), "rb") as wav:
        channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        frames = wav.getnframes()
    if channels != 1 or sample_width != 2 or sample_rate != 24_000 or frames < 1:
        raise RuntimeError("worker returned an unsupported WAV")
    return {
        "channels": channels,
        "sampleWidthBytes": sample_width,
        "sampleRate": sample_rate,
        "frames": frames,
        "durationSeconds": round(frames / sample_rate, 3),
    }


def request_style(
    endpoint: str,
    text: str,
    style: str,
    intensity: float,
    timeout: float,
) -> tuple[bytes, dict[str, str], float]:
    payload = {
        "text": text,
        "voiceProfile": "gahyeon.assistant",
        "style": style,
        "intensity": intensity,
        "communicativeIntent": "benchmark",
        "modelId": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "quantization": "c-int4-avx2",
        "responseFormat": "wav",
    }
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        audio = response.read(16 * 1024 * 1024 + 1)
        headers = {name.lower(): value for name, value in response.headers.items()}
    elapsed = time.perf_counter() - started
    if len(audio) > 16 * 1024 * 1024:
        raise RuntimeError("worker response exceeded 16 MiB")
    expected = {
        "x-gahyeon-voice-profile": "gahyeon.assistant",
        "x-gahyeon-model-id": payload["modelId"],
        "x-gahyeon-quantization": payload["quantization"],
    }
    for name, value in expected.items():
        if headers.get(name) != value:
            raise RuntimeError(f"response attestation mismatch for {name}")
    return audio, headers, elapsed


def benchmark_styles(endpoint: str, output: Path, text: str, timeout: float) -> dict[str, object]:
    output.mkdir(parents=True, exist_ok=True)
    samples: dict[str, object] = {}
    hashes: set[str] = set()
    for index, style in enumerate(DEFAULT_STYLES, start=1):
        intensity = 0.3 if style == "natural" else 0.65
        audio, _, elapsed = request_style(endpoint, text, style, intensity, timeout)
        metadata = inspect_wav(audio)
        digest = hashlib.sha256(audio).hexdigest()
        if digest in hashes:
            raise RuntimeError(f"style {style} produced a duplicate waveform")
        hashes.add(digest)
        filename = f"{index:02d}-{style}.wav"
        (output / filename).write_bytes(audio)
        duration = float(metadata["durationSeconds"])
        samples[style] = {
            "file": filename,
            "sha256": digest,
            "requestSeconds": round(elapsed, 3),
            "rtf": round(elapsed / duration, 3),
            **metadata,
        }
    report: dict[str, object] = {
        "schemaVersion": 1,
        "status": "candidate-not-production",
        "endpointContract": "/v1/speech",
        "modelId": "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice",
        "quantization": "c-int4-avx2",
        "voiceProfile": "gahyeon.assistant",
        "text": text,
        "samples": samples,
    }
    (output / "benchmark.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:18770/v1/speech")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--text", default="잠깐만, 지금 확인해 볼게.")
    parser.add_argument("--timeout", type=float, default=120.0)
    args = parser.parse_args()
    report = benchmark_styles(args.endpoint, args.output, args.text, args.timeout)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
