from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import threading
import time
import wave
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import soundfile as sf
import torch
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
log = logging.getLogger("gahyeonbot-qwen-tts")

MODEL_PATH = Path(os.getenv("QWEN_MODEL_PATH", "/models/qwen"))
MODEL_ID = os.getenv("QWEN_MODEL_ID", "")
QUANTIZATION = os.getenv("QWEN_QUANTIZATION", "none-float32")
DTYPE = os.getenv("QWEN_DTYPE", "float32")
PROFILES_PATH = Path(os.getenv("QWEN_VOICE_PROFILES", "/config/voice-profiles.json"))
API_KEY = os.getenv("QWEN_API_KEY", "")
MAX_CHARS = int(os.getenv("QWEN_MAX_CHARS", "500"))
ADMISSION_TIMEOUT_SECONDS = float(os.getenv("QWEN_ADMISSION_TIMEOUT_SECONDS", "0.05"))
SYNTHESIS_SLOT = threading.BoundedSemaphore(1)
model: Any | None = None
profiles: dict[str, dict[str, Any]] = {}

SUPPORTED_STYLES = {
    "natural", "warm", "gentle", "bright", "surprised", "concerned", "serious",
    "playful", "fake_cute", "sarcastic", "sleepy", "whisper", "excited", "annoyed",
    "sad", "suppressed_laugh",
}


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1)
    voiceProfile: str = Field(min_length=1, max_length=120)
    style: str = Field(min_length=1, max_length=40)
    intensity: float = Field(ge=0, le=1)
    communicativeIntent: str = Field(min_length=1, max_length=80)
    modelId: str = Field(min_length=1, max_length=200)
    quantization: str = Field(min_length=1, max_length=40)
    responseFormat: str = "wav"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise RuntimeError("at least one Qwen voice profile is required")
    checked: dict[str, dict[str, Any]] = {}
    for profile_id, raw in payload.items():
        if not isinstance(profile_id, str) or not profile_id.strip() or not isinstance(raw, dict):
            raise RuntimeError("invalid Qwen voice profile entry")
        mode = raw.get("mode")
        if mode not in {"voice_clone", "custom_voice", "voice_design"}:
            raise RuntimeError(f"unsupported Qwen profile mode: {mode}")
        expression_control = bool(raw.get("expressionControl", False))
        if mode == "voice_clone":
            reference = Path(str(raw.get("referenceAudio", "")))
            reference_text = raw.get("referenceText")
            if not reference.is_file() or not isinstance(reference_text, str) or not reference_text.strip():
                raise RuntimeError(f"voice clone profile is incomplete: {profile_id}")
            raw = dict(raw)
            raw["referenceSha256"] = sha256(reference)
            if expression_control:
                raise RuntimeError("voice_clone cannot claim instruction expression control")
        elif mode == "custom_voice" and not str(raw.get("speaker", "")).strip():
            raise RuntimeError(f"custom voice speaker is missing: {profile_id}")
        elif mode == "voice_design" and not str(raw.get("baseInstruct", "")).strip():
            raise RuntimeError(f"voice design instruction is missing: {profile_id}")
        checked[profile_id.strip()] = dict(raw)
    return checked


def expression_instruction(style: str, intensity: float, intent: str) -> str:
    if style not in SUPPORTED_STYLES:
        raise ValueError(f"unsupported expression style: {style}")
    return f"Style: {style}. Intensity: {intensity:.2f}. Communicative intent: {intent}."


def synthesize_audio(request: SynthesisRequest, profile: dict[str, Any]) -> bytes:
    if model is None:
        raise RuntimeError("model is not ready")
    language = str(profile.get("language", "Auto"))
    mode = profile["mode"]
    controls_expression = bool(profile.get("expressionControl", False))
    if not controls_expression and request.style != "natural":
        raise ValueError("selected voice profile does not support expression control")
    instruction = expression_instruction(
        request.style, request.intensity, request.communicativeIntent,
    ) if controls_expression else None
    if mode == "voice_clone":
        wavs, sample_rate = model.generate_voice_clone(
            text=request.text,
            language=language,
            ref_audio=profile["referenceAudio"],
            ref_text=profile["referenceText"],
            x_vector_only_mode=False,
        )
    elif mode == "custom_voice":
        wavs, sample_rate = model.generate_custom_voice(
            text=request.text,
            language=language,
            speaker=profile["speaker"],
            instruct=instruction,
        )
    else:
        combined = f"{profile['baseInstruct']} {instruction or ''}".strip()
        wavs, sample_rate = model.generate_voice_design(
            text=request.text, language=language, instruct=combined,
        )
    output = io.BytesIO()
    sf.write(output, wavs[0], sample_rate, format="WAV", subtype="PCM_16")
    payload = output.getvalue()
    with wave.open(io.BytesIO(payload), "rb") as audio:
        if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getnframes() < 1:
            raise RuntimeError("Qwen returned unsupported audio")
    return payload


@asynccontextmanager
async def lifespan(_: FastAPI):
    global model, profiles
    if not MODEL_ID or not MODEL_PATH.is_dir() or not PROFILES_PATH.is_file():
        raise RuntimeError("Qwen model identity or voice profiles are missing")
    if DTYPE not in {"float16", "float32"}:
        raise RuntimeError("unsupported Qwen dtype")
    profiles = load_profiles(PROFILES_PATH)
    from qwen_tts import Qwen3TTSModel
    started = time.perf_counter()
    model = Qwen3TTSModel.from_pretrained(
        str(MODEL_PATH), device_map="cuda",
        dtype=torch.float32 if DTYPE == "float32" else torch.float16,
        attn_implementation="eager",
    )
    log.info("model_loaded id=%s quantization=%s profiles=%d seconds=%.3f",
             MODEL_ID, QUANTIZATION, len(profiles), time.perf_counter() - started)
    yield
    model = None
    profiles = {}


app = FastAPI(title="Gahyeon Qwen TTS", version="1", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "healthy" if model is not None else "loading",
        "ready": model is not None,
        "modelId": MODEL_ID,
        "quantization": QUANTIZATION,
        "dtype": DTYPE,
        "voiceProfiles": sorted(profiles),
        "expressionProfiles": sorted(
            key for key, value in profiles.items() if value.get("expressionControl", False)
        ),
    }


@app.post("/v1/speech")
def speech(request: SynthesisRequest, authorization: str | None = Header(default=None)) -> Response:
    if API_KEY and authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="invalid bearer token")
    if model is None:
        raise HTTPException(status_code=503, detail="model is not ready")
    if request.modelId != MODEL_ID or request.quantization != QUANTIZATION:
        raise HTTPException(status_code=409, detail="model identity mismatch")
    if request.responseFormat.lower() != "wav":
        raise HTTPException(status_code=400, detail="only wav output is supported")
    text = request.text.strip()
    if not text or len(text) > MAX_CHARS:
        raise HTTPException(status_code=413, detail="text length is out of range")
    profile = profiles.get(request.voiceProfile)
    if profile is None:
        raise HTTPException(status_code=404, detail="unknown voice profile")
    if not SYNTHESIS_SLOT.acquire(timeout=max(0.0, ADMISSION_TIMEOUT_SECONDS)):
        raise HTTPException(status_code=429, detail="synthesis is busy")
    try:
        try:
            payload = synthesize_audio(request.model_copy(update={"text": text}), profile)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
    finally:
        SYNTHESIS_SLOT.release()
    return Response(
        content=payload,
        media_type="audio/wav",
        headers={
            "X-Gahyeon-Voice-Profile": request.voiceProfile,
            "X-Gahyeon-Model-Id": MODEL_ID,
            "X-Gahyeon-Quantization": QUANTIZATION,
        },
    )
