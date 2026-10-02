#!/usr/bin/env python3
"""Exec the isolated land Desktop voice Core without persisting provider secrets."""

from __future__ import annotations

import json
import os
from pathlib import Path


ROOT = Path("/opt/zaeze-ai/gahyeon-desktop-core-v106")
ALLOWED_SECRET_KEYS = {"OPENROUTER_API_KEY", "OPENROUTER_MODEL", "AGENT_BASE_URL"}


def run_core() -> None:
    supplied = json.load(os.sys.stdin)
    if not isinstance(supplied, dict) or set(supplied) - ALLOWED_SECRET_KEYS:
        raise SystemExit("unexpected provider configuration")
    api_key = supplied.get("OPENROUTER_API_KEY")
    if not isinstance(api_key, str) or len(api_key) < 16:
        raise SystemExit("provider API key is unavailable")

    environment = os.environ.copy()
    environment.update({
        "SPRING_PROFILES_ACTIVE": "dev",
        "SERVER_PORT": "8080",
        "BOT_ENABLED": "false",
        "WEATHER_PREFETCH_ENABLED": "false",
        "GAHYEON_HEADLESS_ENABLED": "true",
        "GAHYEON_BEHAVIOR_ENABLED": "true",
        "GAHYEON_UNREAL_WEBSOCKET_ENABLED": "false",
        "GAHYEON_CLIENT_TOKEN": "land-v106-local-desktop-voice-token",
        "GAHYEON_AGENT_PROVIDER": "openai",
        "AGENT_API_KEY": api_key,
        "AGENT_MODEL": str(supplied.get("OPENROUTER_MODEL") or "openrouter/free"),
        "AGENT_BASE_URL": str(supplied.get("AGENT_BASE_URL") or "https://openrouter.ai/api"),
        "ASSISTANT_ENABLED": "true",
        "ASSISTANT_TTS_PROVIDER": "custom",
        "ASSISTANT_STT_ENABLED": "true",
        "ASSISTANT_STT_BASE_URL": "http://127.0.0.1:18766",
        "ASSISTANT_STT_ENDPOINT": "/v1/audio/transcriptions",
        "ASSISTANT_STT_API_KEY_REQUIRED": "false",
        "ASSISTANT_STT_MODEL": "large-v3-turbo",
        "ASSISTANT_STT_TIMEOUT_SECONDS": "20",
        "TTS_ENABLED": "true",
        "TTS_PROVIDER": "custom",
        "CUSTOM_TTS_ENDPOINT": "http://127.0.0.1:18767/synthesize",
        "CUSTOM_TTS_FORMAT": "wav",
        "CUSTOM_TTS_MODEL": "gahyeon-voicebox-diverse5000-step40000-9a016fa24c25",
        "CUSTOM_TTS_SPEAKER_ID": "0",
        "CUSTOM_TTS_TIMEOUT_SECONDS": "60",
        "LOGGING_FILE_NAME": str(ROOT / "core-v106.log"),
        "LOGGING_LEVEL_COM_GAHYEONBOT": "INFO",
        "LOGGING_LEVEL_ORG_HIBERNATE_SQL": "OFF",
        "LOGGING_LEVEL_ORG_SPRINGFRAMEWORK_WEB": "INFO",
    })
    java = ROOT / "jre/bin/java"
    jar = ROOT / "app.jar"
    if not java.is_file() or not jar.is_file():
        raise SystemExit("isolated Java runtime or Core jar is missing")
    os.execve(str(java), [str(java), "-jar", str(jar)], environment)


if __name__ == "__main__":
    run_core()
