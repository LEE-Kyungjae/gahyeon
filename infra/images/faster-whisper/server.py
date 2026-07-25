from __future__ import annotations

import io
import os
import threading
import time
import wave

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from faster_whisper import WhisperModel


MODEL_NAME = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
DEVICE = os.environ.get("WHISPER_DEVICE", "cuda")
COMPUTE_TYPE = os.environ.get("WHISPER_COMPUTE_TYPE", "int8_float16")
CPU_THREADS = int(os.environ.get("WHISPER_CPU_THREADS", "4"))
TARGET_SAMPLE_RATE = 16_000

app = FastAPI(title="GahyeonBot faster-whisper STT", version="1.0.0")
model: WhisperModel | None = None
model_lock = threading.Lock()


@app.on_event("startup")
def startup() -> None:
    global model
    model = WhisperModel(
        MODEL_NAME,
        device=DEVICE,
        compute_type=COMPUTE_TYPE,
        cpu_threads=CPU_THREADS,
    )


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
        samples = np.interp(
            np.linspace(0, samples.size - 1, output_size),
            np.arange(samples.size),
            samples,
        ).astype(np.float32)
    return samples


@app.get("/health")
def health() -> dict:
    return {
        "status": "healthy" if model is not None else "starting",
        "model": MODEL_NAME,
        "device": DEVICE,
        "compute_type": COMPUTE_TYPE,
    }


@app.post("/transcribe")
@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("ko"),
    requested_model: str = Form("", alias="model"),
    response_format: str = Form("json"),
    prompt: str = Form(""),
) -> dict:
    del requested_model, response_format
    if model is None:
        raise HTTPException(status_code=503, detail="Whisper model is not loaded")
    samples = decode_wav(await file.read())
    if samples.size < TARGET_SAMPLE_RATE // 10:
        return {"text": "", "duration": samples.size / TARGET_SAMPLE_RATE}

    started = time.perf_counter()
    with model_lock:
        segments, info = model.transcribe(
            samples,
            language=language or "ko",
            task="transcribe",
            beam_size=5,
            best_of=5,
            temperature=0,
            initial_prompt=prompt or None,
            condition_on_previous_text=False,
            vad_filter=False,
        )
        text = " ".join(segment.text.strip() for segment in segments).strip()
    return {
        "text": text,
        "duration": round(samples.size / TARGET_SAMPLE_RATE, 3),
        "inference_seconds": round(time.perf_counter() - started, 4),
        "language": info.language,
        "language_probability": round(info.language_probability, 4),
    }
