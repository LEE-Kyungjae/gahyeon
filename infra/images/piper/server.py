from __future__ import annotations

import io
import hashlib
import logging
import os
import re
import subprocess
import threading
import time
import wave
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from piper import PiperVoice, SynthesisConfig
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
USE_CUDA = os.getenv("PIPER_USE_CUDA", "false").lower() in {"1", "true", "yes"}
ADMISSION_TIMEOUT_SECONDS = float(os.getenv("PIPER_ADMISSION_TIMEOUT_SECONDS", "0.05"))
SENTENCE_SILENCE_SECONDS = float(os.getenv("PIPER_SENTENCE_SILENCE_SECONDS", "0.28"))
HIGHPASS_HZ = int(os.getenv("PIPER_HIGHPASS_HZ", "80"))
DENOISE_REDUCTION_DB = float(os.getenv("PIPER_DENOISE_REDUCTION_DB", "10"))
DENOISE_NOISE_FLOOR_DB = float(os.getenv("PIPER_DENOISE_NOISE_FLOOR_DB", "-32"))
TARGET_LUFS = float(os.getenv("PIPER_TARGET_LUFS", "-12"))
LENGTH_SCALE = float(os.getenv("PIPER_LENGTH_SCALE", "1.03"))
NOISE_SCALE = float(os.getenv("PIPER_NOISE_SCALE", "0.85"))
NOISE_W_SCALE = float(os.getenv("PIPER_NOISE_W_SCALE", "0.95"))
MODEL_SHA256 = os.getenv("PIPER_MODEL_SHA256", "")
CONFIG_SHA256 = os.getenv("PIPER_CONFIG_SHA256", "")
SYNTHESIS_SLOT = threading.BoundedSemaphore(1)
voice: PiperVoice | None = None
LATIN_TEXT = re.compile(r"[A-Za-z]")
MARKUP_TAG = re.compile(r"<[^>]*>")
UNSPEAKABLE_TEXT = re.compile(r"[^0-9A-Za-z가-힣\s.,?!'’-]")
TECH_PRONUNCIATIONS = {
    "lme": "엘엠이",
    "usd": "유에스디",
    "openai": "오픈에이아이",
    "github": "깃허브",
    "api": "에이피아이",
    "tts": "티티에스",
    "stt": "에스티티",
    "ai": "에이아이",
}


def file_sha256(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def verify_runtime_identity() -> None:
    if len(MODEL_SHA256) != 64 or file_sha256(MODEL_PATH) != MODEL_SHA256:
        raise RuntimeError("Piper model digest does not match the deployment identity")
    if len(CONFIG_SHA256) != 64 or file_sha256(CONFIG_PATH) != CONFIG_SHA256:
        raise RuntimeError("Piper config digest does not match the deployment identity")


class SynthesisRequest(BaseModel):
    text: str = Field(min_length=1)
    model: str | None = None
    speakerId: str | None = None
    format: str = "wav"


# This is speech-only text normalization, not a replacement Korean G2P.
_SINO_DIGITS = "영일이삼사오육칠팔구"
_AMOUNT = r"(?<![\w.,])([+-]?(?:[1-9]\d{0,2}(?:,\d{3})+|0|[1-9]\d*)(?:\.\d+)?)"
_SPOKEN_UNITS = {"USD/ton": "달러 퍼 톤", "USD/t": "달러 퍼 톤", "USD": "달러",
                 "kg": "킬로그램", "km": "킬로미터", "%": "퍼센트", "달러": "달러", "원": "원", "톤": "톤"}


def korean_sino_number(value: str) -> str:
    sign = "마이너스 " if value.startswith("-") else "플러스 " if value.startswith("+") else ""
    unsigned = value.lstrip("+-").replace(",", "")
    integer, dot, fraction = unsigned.partition(".")
    if len(integer) > 15:
        raise ValueError("Numeric reading exceeds supported range")
    number = int(integer)
    groups = []
    for large in ("", "만", "억", "조"):
        group = number % 10000; number //= 10000
        if not group:
            continue
        syllables = []
        for power, unit in ((3, "천"), (2, "백"), (1, "십"), (0, "")):
            digit = group // (10 ** power) % 10
            if digit:
                syllables.append(("" if digit == 1 and power else _SINO_DIGITS[digit]) + unit)
        groups.insert(0, "".join(syllables) + large)
    spoken = " ".join(groups) or "영"
    if dot:
        spoken += " 점 " + "".join(_SINO_DIGITS[int(d)] for d in fraction)
    return sign + spoken


def normalize_korean_speech_text(text: str) -> str:
    """Normalize only unambiguous dates and quantities; leave ordinary Korean and IDs intact."""
    def date_reading(match):
        import datetime
        year, month, day = map(int, match.groups())
        try:
            datetime.date(year, month, day)
        except ValueError:
            return match.group(0)
        month_reading = {6: "유", 10: "시"}.get(month, korean_sino_number(str(month)))
        return f"{korean_sino_number(str(year))}년 {month_reading}월 {korean_sino_number(str(day))}일"
    text = re.sub(r"(?<![\w-])(\d{4})-(\d{2})-(\d{2})(?![\w-])", date_reading, text)
    text = re.sub(r"(?<!\w)(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일", date_reading, text)
    units = "|".join(re.escape(unit) for unit in sorted(_SPOKEN_UNITS, key=len, reverse=True))
    def quantity_reading(match):
        try:
            return korean_sino_number(match.group(1)) + " " + _SPOKEN_UNITS[match.group(2)]
        except ValueError:
            return match.group(0)
    return re.sub(_AMOUNT + r"\s*(" + units + r")(?![A-Za-z])", quantity_reading, text)


KOREAN_PRONUNCIATION_PROFILE = os.getenv("PIPER_KOREAN_PRONUNCIATION_PROFILE", "standard")
# Explicit opt-in candidate: same eSpeak inventory; do not rewrite arbitrary Korean.
_KOREAN_READING_CANDIDATE = {"국물이": "궁무리", "읽는": "잉는", "신라": "실라"}


def apply_korean_pronunciation_profile(text: str, profile: str) -> str:
    if profile == "standard":
        return text
    if profile != "candidate-v1":
        raise ValueError("Unknown Korean pronunciation profile")
    return re.sub(r"(?<![가-힣A-Za-z])(?:국물이|읽는|신라)(?![가-힣A-Za-z])",
                  lambda match: _KOREAN_READING_CANDIDATE[match.group(0)], text)


def prepare_synthesis_text(text: str) -> tuple[str, str]:
    text = re.sub(r"\s+", " ", MARKUP_TAG.sub(" ", text)).strip()
    if not text:
        return "", "markup-stripped"
    original_text = text
    text = apply_korean_pronunciation_profile(normalize_korean_speech_text(text), KOREAN_PRONUNCIATION_PROFILE)
    if not LATIN_TEXT.search(text):
        return text, "korean-normalized" if text != original_text else "original"
    prepared = text
    for source, pronunciation in TECH_PRONUNCIATIONS.items():
        prepared = re.sub(rf"(?i)\b{re.escape(source)}\b", pronunciation, prepared)
    try:
        from hunmin import transcribe_auto
        converted = transcribe_auto(prepared, primary_lang="en")
        text_mode = "english-transliterated"
    except Exception as error:
        log.warning("english_transliteration_failed type=%s", type(error).__name__)
        converted = prepared
        text_mode = "pronunciation-dictionary-fallback"
    converted = converted or text
    return converted, text_mode


def validate_wav(payload: bytes) -> tuple[int, int, int]:
    try:
        with wave.open(io.BytesIO(payload), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            frames = wav_file.getnframes()
            sample_width = wav_file.getsampwidth()
    except (EOFError, wave.Error) as error:
        raise ValueError("Piper returned an invalid WAV") from error
    if channels != 1 or sample_width != 2 or sample_rate <= 0 or frames <= 0:
        raise ValueError("Piper returned an empty or unsupported WAV")
    return sample_rate, frames, channels


def normalize_loudness(payload: bytes, sample_rate: int) -> bytes:
    audio_filter = (
        f"highpass=f={HIGHPASS_HZ},"
        f"afftdn=nr={DENOISE_REDUCTION_DB:g}:nf={DENOISE_NOISE_FLOOR_DB:g}:tn=1,"
        f"loudnorm=I={TARGET_LUFS:g}:TP=-1:LRA=7"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", "pipe:0",
        "-af", audio_filter,
        "-ar", str(sample_rate), "-ac", "1",
        "-f", "s16le", "pipe:1",
    ]
    try:
        result = subprocess.run(
            command, input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            check=True, timeout=20,
        )
    except (OSError, subprocess.SubprocessError) as error:
        log.warning("loudness_normalization_failed type=%s", type(error).__name__)
        return payload
    if not result.stdout:
        log.warning("loudness_normalization_failed type=empty_output")
        return payload
    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(result.stdout)
    normalized = output.getvalue()
    validate_wav(normalized)
    return normalized


def synthesize_payload(text: str) -> bytes:
    if voice is None:
        raise ValueError("model is not ready")
    output = io.BytesIO()
    try:
        with wave.open(output, "wb") as wav_file:
            previous_chunk = None
            synthesis_config = SynthesisConfig(
                length_scale=LENGTH_SCALE,
                noise_scale=NOISE_SCALE,
                noise_w_scale=NOISE_W_SCALE,
            )
            for audio_chunk in voice.synthesize(text, syn_config=synthesis_config):
                chunk_format = (
                    audio_chunk.sample_channels,
                    audio_chunk.sample_width,
                    audio_chunk.sample_rate,
                )
                if previous_chunk is None:
                    wav_file.setnchannels(audio_chunk.sample_channels)
                    wav_file.setsampwidth(audio_chunk.sample_width)
                    wav_file.setframerate(audio_chunk.sample_rate)
                elif chunk_format != previous_chunk:
                    raise ValueError("Piper returned inconsistent sentence audio formats")
                else:
                    silence_frames = round(
                        audio_chunk.sample_rate * max(0.0, SENTENCE_SILENCE_SECONDS)
                    )
                    wav_file.writeframes(
                        b"\0" * silence_frames
                        * audio_chunk.sample_width
                        * audio_chunk.sample_channels
                    )
                wav_file.writeframes(audio_chunk.audio_int16_bytes)
                previous_chunk = chunk_format
    except (EOFError, wave.Error) as error:
        raise ValueError("Piper could not synthesize a valid WAV") from error
    payload = output.getvalue()
    validate_wav(payload)
    return payload


@asynccontextmanager
async def lifespan(_: FastAPI):
    global voice
    if not MODEL_PATH.is_file() or not CONFIG_PATH.is_file():
        raise RuntimeError(f"Piper model is missing: {MODEL_PATH} / {CONFIG_PATH}")
    verify_runtime_identity()
    started = time.perf_counter()
    voice = PiperVoice.load(MODEL_PATH, CONFIG_PATH, use_cuda=USE_CUDA)
    log.info("model_loaded alias=%s cuda=%s seconds=%.3f", MODEL_ALIAS, USE_CUDA,
             time.perf_counter() - started)
    yield
    voice = None


app = FastAPI(title="Gahyeonbot Piper TTS", version="1", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "healthy" if voice is not None else "loading",
        "provider": "piper",
        "model": MODEL_ALIAS,
        "modelSha256": MODEL_SHA256,
        "configSha256": CONFIG_SHA256,
        "cuda": USE_CUDA,
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

    prepared_text, text_mode = prepare_synthesis_text(text)
    if not prepared_text:
        raise HTTPException(status_code=422, detail="text did not contain speakable content")
    started = time.perf_counter()
    admitted = SYNTHESIS_SLOT.acquire(timeout=max(0.0, ADMISSION_TIMEOUT_SECONDS))
    if not admitted:
        raise HTTPException(status_code=429, detail="synthesis is busy")
    try:
        try:
            payload = synthesize_payload(prepared_text)
        except ValueError as first_error:
            retry_text = UNSPEAKABLE_TEXT.sub(" ", prepared_text)
            retry_text = re.sub(r"\s+", " ", retry_text).strip()
            if not retry_text or retry_text == prepared_text:
                raise HTTPException(
                    status_code=422, detail="text did not produce valid speech audio",
                ) from first_error
            log.warning("synthesis_retry chars=%d", len(prepared_text))
            try:
                payload = synthesize_payload(retry_text)
            except ValueError as retry_error:
                raise HTTPException(
                    status_code=422, detail="text did not produce valid speech audio",
                ) from retry_error
    finally:
        SYNTHESIS_SLOT.release()
    elapsed = time.perf_counter() - started
    sample_rate, frames, _ = validate_wav(payload)
    payload = normalize_loudness(payload, sample_rate)
    sample_rate, frames, _ = validate_wav(payload)
    duration = frames / sample_rate
    rtf = elapsed / duration if duration else 0.0
    log.info(
        "synthesized chars=%d prepared_chars=%d text_mode=%s audio_seconds=%.3f generation_seconds=%.3f rtf=%.3f",
        len(text), len(prepared_text), text_mode, duration, elapsed, rtf,
    )
    return Response(
        content=payload,
        media_type="audio/wav",
        headers={
            "X-Piper-Model": MODEL_ALIAS,
            "X-Piper-Model-SHA256": MODEL_SHA256,
            "X-Piper-Config-SHA256": CONFIG_SHA256,
            "X-Sentence-Silence-Seconds": f"{SENTENCE_SILENCE_SECONDS:.3f}",
            "X-Audio-Denoised": "true",
            "X-Generation-Seconds": f"{elapsed:.4f}",
            "X-Audio-Seconds": f"{duration:.4f}",
            "X-Realtime-Factor": f"{rtf:.4f}",
            "X-Synthesis-Text-Mode": text_mode,
            "X-Loudness-Normalized": "true",
        },
    )
