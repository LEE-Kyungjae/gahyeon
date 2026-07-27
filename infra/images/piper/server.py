from __future__ import annotations

import io
import logging
import os
import threading
import time
import wave
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from piper import PiperVoice
from pydantic import BaseModel, Field


logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("gahyeonbot-piper")

MODEL_PATH = Path(os.getenv("PIPER_MODEL_PATH", "/models/voice.onnx"))
CONFIG_PATH = Path(os.getenv("PIPER_CONFIG_PATH", f"{MODEL_PATH}.json"))
MODEL_ALIAS = os.getenv("PIPER_MODEL_ALIAS", "ze9-fp32-step5884")
API_KEY = os.getenv("PIPER_API_KEY", "")
MAX_CHARS = int(os.getenv("PIPER_MAX_CHARS", "500"))
SYNTHESIS_LOCK = threading.Lock()
voice: PiperVoice | None = None


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1)
    model: str | None = None
    speakerId: str | None = None
    format: str = "wav"


@asynccontextmanager
async def lifespan(_: FastAPI):
    global voice
    if not MODEL_PATH.is_file() or not CONFIG_PATH.is_file():
        raise RuntimeError(f"Piper model is missing: {MODEL_PATH} / {CONFIG_PATH}")
    started = time.perf_counter()
    voice = PiperVoice.load(MODEL_PATH, CONFIG_PATH, use_cuda=False)
    log.info("model_loaded alias=%s seconds=%.3f", MODEL_ALIAS, time.perf_counter() - started)
    yield
    voice = None


app = FastAPI(title="Gahyeonbot Piper TTS", version="1", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "healthy" if voice is not None else "loading",
        "provider": "piper",
        "model": MODEL_ALIAS,
        "ready": voice is not None,
    }


@app.post("/synthesize")
def synthesize(
    request: SynthesisRequest,
    authorization: str | None = Header(default=None),
) -> Response:
    if API_KEY and authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="invalid bearer token")
    if voice is None:
        raise HTTPException(status_code=503, detail="model is not ready")
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")
    if len(text) > MAX_CHARS:
        raise HTTPException(status_code=413, detail=f"text exceeds {MAX_CHARS} characters")
    if request.format.lower() != "wav":
        raise HTTPException(status_code=400, detail="only wav output is supported")
    if request.model and request.model != MODEL_ALIAS:
        raise HTTPException(status_code=404, detail="unknown model alias")

    started = time.perf_counter()
    output = io.BytesIO()
    with SYNTHESIS_LOCK:
        with wave.open(output, "wb") as wav_file:
            voice.synthesize_wav(text, wav_file)
    elapsed = time.perf_counter() - started
    payload = output.getvalue()
    with wave.open(io.BytesIO(payload), "rb") as wav_file:
        duration = wav_file.getnframes() / wav_file.getframerate()
    rtf = elapsed / duration if duration else 0.0
    log.info(
        "synthesized chars=%d audio_seconds=%.3f generation_seconds=%.3f rtf=%.3f",
        len(text), duration, elapsed, rtf,
    )
    return Response(
        content=payload,
        media_type="audio/wav",
        headers={
            "X-Piper-Model": MODEL_ALIAS,
            "X-Generation-Seconds": f"{elapsed:.4f}",
            "X-Audio-Seconds": f"{duration:.4f}",
            "X-Realtime-Factor": f"{rtf:.4f}",
        },
    )
