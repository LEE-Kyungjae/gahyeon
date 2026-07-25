from __future__ import annotations

import io
import os
import re
import threading
import time
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile


MODEL_DIR = Path(os.environ.get("SENSEVOICE_MODEL_DIR", "/models/sensevoice"))
MODEL_PATH = MODEL_DIR / "model.int8.onnx"
TOKENS_PATH = MODEL_DIR / "tokens.txt"
NUM_THREADS = int(os.environ.get("SENSEVOICE_NUM_THREADS", max(1, (os.cpu_count() or 4) // 2)))
TARGET_SAMPLE_RATE = 16_000

app = FastAPI(title="SenseVoice STT", version="1.0.0")
recognizer: sherpa_onnx.OfflineRecognizer | None = None
recognizer_lock = threading.Lock()


def load_recognizer() -> sherpa_onnx.OfflineRecognizer:
    if not MODEL_PATH.is_file() or not TOKENS_PATH.is_file():
        raise RuntimeError(f"SenseVoice model files are missing under {MODEL_DIR}")
    return sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(MODEL_PATH),
        tokens=str(TOKENS_PATH),
        num_threads=NUM_THREADS,
        sample_rate=TARGET_SAMPLE_RATE,
        language="ko",
        use_itn=True,
        provider="cpu",
    )


@app.on_event("startup")
def startup() -> None:
    global recognizer
    recognizer = load_recognizer()


def decode_wav(content: bytes) -> np.ndarray:
    try:
        with wave.open(io.BytesIO(content), "rb") as audio:
            channels = audio.getnchannels()
            sample_width = audio.getsampwidth()
            source_rate = audio.getframerate()
            frames = audio.readframes(audio.getnframes())
    except (wave.Error, EOFError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid WAV audio: {exc}") from exc

    if sample_width != 2:
        raise HTTPException(status_code=400, detail="Only 16-bit PCM WAV is supported")
    samples = np.frombuffer(frames, dtype="<i2").astype(np.float32)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    samples /= 32768.0
    if source_rate != TARGET_SAMPLE_RATE and samples.size:
        output_size = max(1, round(samples.size * TARGET_SAMPLE_RATE / source_rate))
        source_positions = np.arange(samples.size, dtype=np.float64)
        target_positions = np.linspace(0, samples.size - 1, output_size)
        samples = np.interp(target_positions, source_positions, samples).astype(np.float32)
    return samples


def clean_result(text: str) -> str:
    # SenseVoice can prefix language/emotion/event control tokens.
    return re.sub(r"<\|[^|>]+\|>", "", text).strip()


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy" if recognizer is not None else "starting",
        "model": "SenseVoiceSmall-int8",
        "language": "ko",
        "threads": NUM_THREADS,
    }


@app.post("/transcribe")
@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("ko"),
    model: str = Form("sensevoice-small-int8"),
    response_format: str = Form("json"),
) -> dict:
    del language, model, response_format
    if recognizer is None:
        raise HTTPException(status_code=503, detail="SenseVoice model is not loaded")

    content = await file.read()
    samples = decode_wav(content)
    if samples.size < TARGET_SAMPLE_RATE // 10:
        return {"text": "", "duration": samples.size / TARGET_SAMPLE_RATE, "inference_seconds": 0.0}

    started = time.perf_counter()
    with recognizer_lock:
        stream = recognizer.create_stream()
        stream.accept_waveform(TARGET_SAMPLE_RATE, samples)
        recognizer.decode_stream(stream)
        text = clean_result(stream.result.text)
    elapsed = time.perf_counter() - started
    return {
        "text": text,
        "duration": round(samples.size / TARGET_SAMPLE_RATE, 3),
        "inference_seconds": round(elapsed, 4),
    }
