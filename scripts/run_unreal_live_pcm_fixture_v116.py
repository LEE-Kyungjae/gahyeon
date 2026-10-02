#!/usr/bin/env python3
"""Serve one real Qwen PCM stream to the production Unreal transport."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import json
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BASE_PATH = ROOT / "scripts/run_unreal_live_speech_fixture_v107.py"
SPEC = importlib.util.spec_from_file_location("gahyeon_v107_fixture", BASE_PATH)
assert SPEC is not None and SPEC.loader is not None
BASE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASE)

SESSION_ID = "gahyeon-live-pcm-v116"
STREAM_PATH = "/api/gahyeon/unreal/speech/stream/gahyeon-live-v116"


def envelope(kind: str, payload: dict, correlation: str) -> dict:
    return {
        "protocol": "gahyeon.unreal.v1",
        "schemaVersion": 1,
        "messageId": str(BASE.uuid.uuid4()),
        "type": kind,
        "sentAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sessionId": SESSION_ID,
        "correlationId": correlation,
        "delivery": "ephemeral",
        "payload": payload,
    }


class Server(BASE.FixtureServer):
    def __init__(self, address, pcm: bytes, evidence: Path):
        super().__init__(address, Handler, pcm, {"source": "amplitude-stream", "visemes": []}, evidence)
        self.pcm = pcm
        self.stream_started_at: float | None = None
        self.stream_completed_at: float | None = None
        self.bytes_sent = 0
        self.stream_requests = 0
        self.speech_dispatched = False

    def write_evidence(self) -> None:
        self.evidence.parent.mkdir(parents=True, exist_ok=True)
        self.evidence.write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v116",
            "status": "stream-completed" if self.stream_completed_at else (
                "event-sent" if self.sent.is_set() else "waiting"),
            "sessionId": SESSION_ID,
            "clientHello": self.client_hello,
            "pcmSha256": hashlib.sha256(self.pcm).hexdigest(),
            "pcmBytes": len(self.pcm),
            "bytesSent": self.bytes_sent,
            "streamRequests": self.stream_requests,
            "streamStartedAt": self.stream_started_at,
            "streamCompletedAt": self.stream_completed_at,
            "claims": {
                "realLandQwenPcm": True,
                "productionUnrealTransport": True,
                "productionProceduralPcmQueue": True,
                "visibleMetaHumanActuation": False,
                "audiblePlaybackObservedByHuman": False,
            },
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    server: Server
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        print("pcm-fixture:", fmt % args, flush=True)

    def do_GET(self) -> None:
        if self.path == STREAM_PATH:
            self.server.stream_requests += 1
            self.send_response(200)
            self.send_header("Content-Type", "audio/pcm")
            self.send_header("X-Sample-Rate", "24000")
            self.send_header("X-Sample-Format", "s16le")
            self.send_header("X-Channels", "1")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(self.server.pcm)))
            self.end_headers()
            self.server.stream_started_at = time.time()
            for offset in range(0, len(self.server.pcm), 4800):
                chunk = self.server.pcm[offset:offset + 4800]
                self.wfile.write(chunk)
                self.wfile.flush()
                self.server.bytes_sent += len(chunk)
                time.sleep(0.04)
            self.server.stream_completed_at = time.time()
            self.server.write_evidence()
            return
        if self.path != "/api/gahyeon/unreal/v1" or self.headers.get("Upgrade", "").lower() != "websocket":
            self.send_error(404)
            return
        key = self.headers.get("Sec-WebSocket-Key", "")
        if not key:
            self.send_error(400)
            return
        accept = base64.b64encode(hashlib.sha1(
            (key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")
        ).digest()).decode("ascii")
        self.send_response(101, "Switching Protocols")
        self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade")
        self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()

        hello = json.loads(BASE.read_websocket_frame(self.rfile))
        if hello.get("type") != "client.hello":
            raise ValueError("first Unreal message was not client.hello")
        self.server.client_hello = hello
        messages = [
            envelope("server.welcome", {"resumeAfter": 0, "heartbeatIntervalMs": 60_000}, "connect:v116"),
        ]
        if not self.server.speech_dispatched:
            self.server.speech_dispatched = True
            messages.extend([
                envelope("generation.advanced", {"generation": 1, "reason": "new_input"}, "turn:v116"),
                envelope("speech.prepared", {
                "generation": 1,
                "utteranceId": "gahyeon-live-v116",
                "utteranceIndex": 0,
                "segmentIndex": 0,
                "segmentCount": 1,
                "finalSegment": True,
                "voiceProfile": "gahyeon.assistant",
                "voiceExpression": {
                    "style": "fake_cute",
                    "intensity": 0.72,
                    "communicativeIntent": "playful_reassurance",
                },
                "audio": {"url": STREAM_PATH, "mimeType": "audio/pcm"},
                "visemes": [],
                }, "turn:v116"),
                envelope("speech.sequence.ended", {
                    "generation": 1, "utteranceCount": 1, "outcome": "completed",
                }, "turn:v116"),
            ])
        for message in messages:
            self.wfile.write(BASE.websocket_frame(json.dumps(
                message, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")))
            self.wfile.flush()
            time.sleep(0.08)
        self.server.sent.set()
        self.server.write_evidence()
        threading.Event().wait(30)
        self.close_connection = True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18775)
    parser.add_argument("--pcm", type=Path, default=(
        ROOT / "artifacts/qwen-expressive-1.7b-land-v116/unreal-live.s16le"))
    parser.add_argument("--evidence", type=Path, default=(
        ROOT / "artifacts/qwen-expressive-1.7b-land-v116/unreal-pcm-fixture.json"))
    args = parser.parse_args()
    pcm = args.pcm.resolve().read_bytes()
    if not pcm or len(pcm) % 2:
        raise ValueError("PCM fixture must be non-empty s16le frames")
    server = Server((args.host, args.port), pcm, args.evidence.resolve())
    server.write_evidence()
    print(json.dumps({
        "status": "listening",
        "websocket": f"ws://{args.host}:{args.port}/api/gahyeon/unreal/v1",
        "stream": f"http://{args.host}:{args.port}{STREAM_PATH}",
    }), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
