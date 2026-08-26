from __future__ import annotations

import io
import json
import os
import struct
import threading
import urllib.error
import urllib.request
import wave
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field


MODEL_ID = os.getenv("QWEN_MODEL_ID", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
QUANTIZATION = os.getenv("QWEN_QUANTIZATION", "c-int4-avx2")
PROFILES_PATH = Path(os.getenv("QWEN_C_RUNTIME_PROFILES", "/config/c-runtime-profiles.json"))
API_KEY = os.getenv("QWEN_API_KEY", "")
MAX_CHARS = int(os.getenv("QWEN_MAX_CHARS", "500"))
MAX_AUDIO_BYTES = int(os.getenv("QWEN_MAX_AUDIO_BYTES", str(16 * 1024 * 1024)))
TIMEOUT_SECONDS = float(os.getenv("QWEN_BACKEND_TIMEOUT_SECONDS", "120"))
SYNTHESIS_SLOT = threading.BoundedSemaphore(1)


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1)
    voiceProfile: str = Field(min_length=1, max_length=120)
    style: str = Field(min_length=1, max_length=40)
    intensity: float = Field(ge=0, le=1)
    communicativeIntent: str = Field(min_length=1, max_length=80)
    modelId: str = Field(min_length=1, max_length=200)
    quantization: str = Field(min_length=1, max_length=40)
    responseFormat: str = "wav"


def load_profiles(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not payload:
        raise RuntimeError("at least one C runtime voice profile is required")
    result: dict[str, dict[str, Any]] = {}
    for profile_id, raw in payload.items():
        if not isinstance(profile_id, str) or not profile_id.strip() or not isinstance(raw, dict):
            raise RuntimeError("invalid C runtime voice profile")
        backend = str(raw.get("backendUrl", "")).strip()
        styles = raw.get("styles")
        if not backend.startswith("http://127.0.0.1:") or not isinstance(styles, dict):
            raise RuntimeError("C runtime backend must be loopback with an explicit style map")
        if "natural" not in styles or styles["natural"] is not None:
            raise RuntimeError("natural style must map to null emotion")
        for style, mapping in styles.items():
            if not isinstance(style, str) or not style.strip():
                raise RuntimeError("invalid C runtime style mapping")
            if mapping is None or isinstance(mapping, str):
                continue
            if not isinstance(mapping, dict) or not mapping:
                raise RuntimeError("invalid C runtime style mapping")
            unsupported = set(mapping) - {"emotion", "instruct", "rate", "volume", "outputGain"}
            if unsupported:
                raise RuntimeError("unsupported C runtime style controls")
            emotion = mapping.get("emotion")
            instruct = mapping.get("instruct")
            if emotion is None and instruct is None:
                raise RuntimeError("style mapping needs emotion or instruct")
            if emotion is not None and (not isinstance(emotion, str) or not emotion.strip()):
                raise RuntimeError("invalid C runtime emotion mapping")
            if instruct is not None and (not isinstance(instruct, str) or not instruct.strip()
                                         or len(instruct) > 500):
                raise RuntimeError("invalid C runtime instruct mapping")
            for control in ("rate", "volume"):
                value = mapping.get(control)
                if value is not None and (not isinstance(value, (int, float))
                                          or isinstance(value, bool) or value <= 0 or value > 2):
                    raise RuntimeError(f"invalid C runtime {control} mapping")
            output_gain = mapping.get("outputGain")
            if output_gain is not None and (not isinstance(output_gain, (int, float))
                                            or isinstance(output_gain, bool)
                                            or output_gain < 1 or output_gain > 4):
                raise RuntimeError("invalid C runtime outputGain mapping")
        result[profile_id.strip()] = {**raw, "backendUrl": backend, "styles": styles}
    return result


profiles = load_profiles(PROFILES_PATH) if PROFILES_PATH.is_file() else {}
app = FastAPI(title="Gahyeon Qwen C Runtime Bridge", version="1")


def backend_payload(request: SynthesisRequest, profile: dict[str, Any]) -> dict[str, Any]:
    if request.style not in profile["styles"]:
        raise ValueError("selected voice profile has no validated mapping for this style")
    mapping = profile["styles"][request.style]
    payload: dict[str, Any] = {
        "text": request.text,
        "language": profile.get("language", "Korean"),
        "seed": int(profile.get("seed", 20260819)),
    }
    if isinstance(mapping, str):
        mapping = {"emotion": mapping}
    if isinstance(mapping, dict):
        for control in ("emotion", "rate", "volume"):
            if control in mapping:
                payload[control] = mapping[control]
        if "instruct" in mapping:
            payload["instruct"] = mapping["instruct"].strip()
    strength = ("Keep the expression subtle and restrained." if request.intensity < 0.34
                else "Make the expression clear but controlled." if request.intensity < 0.67
                else "Make the expression strong and unmistakable.")
    if "emotion" in payload and "instruct" not in payload:
        payload["instruct"] = f"Speak with {payload['emotion']} in the voice, without becoming theatrical."
    if "instruct" in payload:
        payload["instruct"] = f"{payload['instruct']} {strength}"
    return payload


def scale_pcm_s16le(audio: bytes, gain: float) -> bytes:
    if gain == 1 or not audio:
        return audio
    if len(audio) % 2:
        raise RuntimeError("C runtime returned unaligned PCM")
    samples = struct.unpack(f"<{len(audio) // 2}h", audio)
    scaled = (max(-32768, min(32767, round(sample * gain))) for sample in samples)
    return struct.pack(f"<{len(samples)}h", *scaled)


def output_gain(request: SynthesisRequest, profile: dict[str, Any]) -> float:
    mapping = profile["styles"].get(request.style)
    return float(mapping.get("outputGain", 1)) if isinstance(mapping, dict) else 1.0


def backend_request(request: SynthesisRequest, profile: dict[str, Any]) -> bytes:
    body = json.dumps(backend_payload(request, profile), ensure_ascii=False).encode("utf-8")
    backend = urllib.request.Request(
        profile["backendUrl"], data=body, headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(backend, timeout=TIMEOUT_SECONDS) as response:
            if response.status != 200:
                raise RuntimeError(f"C runtime returned HTTP {response.status}")
            audio = response.read(MAX_AUDIO_BYTES + 1)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError("C runtime is unavailable") from error
    if len(audio) > MAX_AUDIO_BYTES:
        raise RuntimeError("C runtime audio exceeds size limit")
    try:
        with wave.open(io.BytesIO(audio), "rb") as wav:
            valid = (wav.getnchannels() == 1 and wav.getsampwidth() == 2
                     and wav.getframerate() == 24_000 and wav.getnframes() > 0)
    except (EOFError, wave.Error) as error:
        raise RuntimeError("C runtime returned invalid WAV") from error
    if not valid:
        raise RuntimeError("C runtime returned unsupported WAV")
    gain = output_gain(request, profile)
    if gain == 1:
        return audio
    source = io.BytesIO(audio)
    target = io.BytesIO()
    with wave.open(source, "rb") as wav, wave.open(target, "wb") as result:
        result.setparams(wav.getparams())
        result.writeframes(scale_pcm_s16le(wav.readframes(wav.getnframes()), gain))
    return target.getvalue()


def backend_stream(request: SynthesisRequest, profile: dict[str, Any]):
    backend_url = profile["backendUrl"]
    if not backend_url.endswith("/v1/tts"):
        raise RuntimeError("C runtime backend has no validated streaming route")
    body = json.dumps(backend_payload(request, profile), ensure_ascii=False).encode("utf-8")
    backend = urllib.request.Request(
        backend_url + "/stream", data=body,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        response = urllib.request.urlopen(backend, timeout=TIMEOUT_SECONDS)
    except (urllib.error.URLError, TimeoutError) as error:
        raise RuntimeError("C runtime streaming route is unavailable") from error
    if response.status != 200:
        response.close()
        raise RuntimeError(f"C runtime returned HTTP {response.status}")
    expected = {
        "Content-Type": "audio/pcm",
        "X-Sample-Rate": "24000",
        "X-Sample-Format": "s16le",
        "X-Channels": "1",
    }
    if any(response.headers.get(key, "").split(";", 1)[0].strip().lower()
           != value.lower() for key, value in expected.items()):
        response.close()
        raise RuntimeError("C runtime returned unsupported streaming audio")
    first = response.read(4_800)
    if not first or len(first) % 2:
        response.close()
        raise RuntimeError("C runtime returned an invalid first PCM chunk")

    gain = output_gain(request, profile)

    def chunks():
        total = 0
        try:
            chunk = first
            while chunk:
                total += len(chunk)
                if total > MAX_AUDIO_BYTES or len(chunk) % 2:
                    raise RuntimeError("C runtime PCM stream exceeded its contract")
                yield scale_pcm_s16le(chunk, gain)
                chunk = response.read(32_768)
        finally:
            response.close()
            SYNTHESIS_SLOT.release()
    return chunks()


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "configured" if profiles else "unconfigured",
        "ready": bool(profiles),
        "modelId": MODEL_ID,
        "quantization": QUANTIZATION,
        "voiceProfiles": sorted(profiles),
        "validatedStyles": {key: sorted(value["styles"]) for key, value in profiles.items()},
    }


@app.post("/v1/speech")
def speech(request: SynthesisRequest, authorization: str | None = Header(default=None)) -> Response:
    if API_KEY and authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="invalid bearer token")
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
    if not SYNTHESIS_SLOT.acquire(timeout=0.05):
        raise HTTPException(status_code=429, detail="synthesis is busy")
    try:
        try:
            audio = backend_request(request.model_copy(update={"text": text}), profile)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except RuntimeError as error:
            raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        SYNTHESIS_SLOT.release()
    return Response(content=audio, media_type="audio/wav", headers={
        "X-Gahyeon-Voice-Profile": request.voiceProfile,
        "X-Gahyeon-Model-Id": MODEL_ID,
        "X-Gahyeon-Quantization": QUANTIZATION,
    })


@app.post("/v1/speech/stream")
def speech_stream(
        request: SynthesisRequest,
        authorization: str | None = Header(default=None)) -> StreamingResponse:
    if API_KEY and authorization != f"Bearer {API_KEY}":
        raise HTTPException(status_code=401, detail="invalid bearer token")
    if request.modelId != MODEL_ID or request.quantization != QUANTIZATION:
        raise HTTPException(status_code=409, detail="model identity mismatch")
    if request.responseFormat.lower() not in {"pcm", "s16le"}:
        raise HTTPException(status_code=400, detail="streaming requires raw PCM output")
    text = request.text.strip()
    if not text or len(text) > MAX_CHARS:
        raise HTTPException(status_code=413, detail="text length is out of range")
    profile = profiles.get(request.voiceProfile)
    if profile is None:
        raise HTTPException(status_code=404, detail="unknown voice profile")
    if not SYNTHESIS_SLOT.acquire(timeout=0.05):
        raise HTTPException(status_code=429, detail="synthesis is busy")
    try:
        chunks = backend_stream(request.model_copy(update={"text": text}), profile)
    except ValueError as error:
        SYNTHESIS_SLOT.release()
        raise HTTPException(status_code=422, detail=str(error)) from error
    except RuntimeError as error:
        SYNTHESIS_SLOT.release()
        raise HTTPException(status_code=502, detail=str(error)) from error
    return StreamingResponse(chunks, media_type="audio/pcm", headers={
        "X-Gahyeon-Voice-Profile": request.voiceProfile,
        "X-Gahyeon-Model-Id": MODEL_ID,
        "X-Gahyeon-Quantization": QUANTIZATION,
        "X-Sample-Rate": "24000",
        "X-Sample-Format": "s16le",
        "X-Channels": "1",
    })
