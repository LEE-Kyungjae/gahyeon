#!/usr/bin/env python3
"""Serve one real Core-shaped speech event to a UE runtime over HTTP/WebSocket.

This is a visual acceptance fixture, not a replacement Core. It exercises the
production UE transport, audio cache download, device playback, viseme runtime,
and MetaHuman presentation path with a real generated Gahyeon WAV.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import socketserver
import struct
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WAV = ROOT / "artifacts/autonomy/conversation-expression-live-v001/gahyeon-bright.wav"
DEFAULT_TIMELINE = ROOT / "artifacts/autonomy/unreal-metahuman-live-speech-v107/viseme-fixture.json"
SESSION_ID = "gahyeon-live-speech-v107"
AUDIO_PATH = "/api/gahyeon/unreal/speech/audio/gahyeon-live-v107"


def envelope(kind: str, payload: dict, correlation: str) -> dict:
    return {
        "protocol": "gahyeon.unreal.v1",
        "schemaVersion": 1,
        "messageId": str(uuid.uuid4()),
        "type": kind,
        "sentAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sessionId": SESSION_ID,
        "correlationId": correlation,
        "delivery": "ephemeral",
        "payload": payload,
    }


def websocket_frame(payload: bytes) -> bytes:
    header = bytearray([0x81])
    length = len(payload)
    if length < 126:
        header.append(length)
    elif length <= 0xFFFF:
        header.append(126)
        header.extend(struct.pack("!H", length))
    else:
        header.append(127)
        header.extend(struct.pack("!Q", length))
    return bytes(header) + payload


def read_websocket_frame(stream) -> bytes:
    first = stream.read(2)
    if len(first) != 2:
        raise ConnectionError("websocket closed before client.hello")
    opcode = first[0] & 0x0F
    if opcode == 0x8:
        raise ConnectionError("websocket closed")
    masked = bool(first[1] & 0x80)
    length = first[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", stream.read(2))[0]
    elif length == 127:
        length = struct.unpack("!Q", stream.read(8))[0]
    mask = stream.read(4) if masked else b""
    payload = bytearray(stream.read(length))
    if len(payload) != length:
        raise ConnectionError("truncated websocket frame")
    if masked:
        for index in range(length):
            payload[index] ^= mask[index % 4]
    return bytes(payload)


class FixtureServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address, handler, wav: bytes, timeline: dict, evidence: Path):
        super().__init__(address, handler)
        self.wav = wav
        self.timeline = timeline
        self.evidence = evidence
        self.sent = threading.Event()
        self.client_hello: dict | None = None

    def write_evidence(self) -> None:
        self.evidence.parent.mkdir(parents=True, exist_ok=True)
        self.evidence.write_text(json.dumps({
            "schemaVersion": 1,
            "iteration": "v107",
            "status": "fixture-event-sent" if self.sent.is_set() else "waiting",
            "sessionId": SESSION_ID,
            "clientHello": self.client_hello,
            "wavSha256": hashlib.sha256(self.wav).hexdigest(),
            "wavBytes": len(self.wav),
            "visemeSource": self.timeline.get("source"),
            "visemeCount": len(self.timeline["visemes"]),
            "audioDurationMs": self.timeline.get("audioDurationMs"),
            "claims": {
                "realGeneratedWav": True,
                "productionUnrealTransport": True,
                "physicalAudioPlayback": False,
                "visibleMetaHumanActuation": False,
            },
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class Handler(BaseHTTPRequestHandler):
    server: FixtureServer
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args) -> None:
        print("fixture:", fmt % args, flush=True)

    def do_GET(self) -> None:
        if self.path == AUDIO_PATH:
            self.send_response(200)
            self.send_header("Content-Type", "audio/wav")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(self.server.wav)))
            self.end_headers()
            self.wfile.write(self.server.wav)
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

        hello = json.loads(read_websocket_frame(self.rfile))
        if hello.get("type") != "client.hello":
            raise ValueError("first Unreal message was not client.hello")
        self.server.client_hello = hello
        messages = [
            envelope("server.welcome", {
                "resumeAfter": 0,
                "heartbeatIntervalMs": 10_000,
            }, hello.get("correlationId", "connection:v107")),
            envelope("world.snapshot", {
                "worldId": "gahyeon-home",
                "revision": 1,
                "currentRoom": "workspace",
                "position": {"x": 0, "y": 0, "z": 0},
                "activity": "conversation",
                "activityStartedAt": "2026-08-20T00:00:00Z",
                "outfit": "casual",
                "worldTime": "2026-08-20T00:00:00Z",
                "emotion": {"name": "bright", "intensity": 0.58},
                "interactionTarget": "local-user",
                "updatedAt": "2026-08-20T00:00:00Z",
                "capturedAt": "2026-08-20T00:00:00Z",
            }, "snapshot:v107"),
            envelope("generation.advanced", {
                "generation": 1,
                "reason": "new_input",
            }, "turn:v107"),
            envelope("emotion.target", {
                "generation": 1,
                "dimensions": {"happy": 0.58},
                "blendSeconds": 0.25,
                "holdSeconds": 4.0,
            }, "life:gahyeon:114"),
            envelope("attention.target", {
                "generation": 1,
                "kind": "user",
                "priority": 50,
                "expiresAfterMs": 4_000,
            }, "life:gahyeon:114"),
            envelope("gesture.intent", {
                "generation": 1,
                "semantic": "small_wave",
                "intensity": 0.58,
                "priority": 50,
                "expiresAfterMs": 4_000,
            }, "life:gahyeon:114"),
            envelope("speech.prepared", {
                "generation": 1,
                "utteranceId": "gahyeon-live-v107",
                "utteranceIndex": 0,
                "segmentIndex": 0,
                "segmentCount": 1,
                "finalSegment": True,
                "voiceProfile": "gahyeon.assistant",
                "voiceExpression": {
                    "style": "bright",
                    "intensity": 0.58,
                    "communicativeIntent": "share_positive_affect",
                },
                "audio": {"url": AUDIO_PATH, "mimeType": "audio/wav"},
                "visemes": self.server.timeline["visemes"],
            }, "turn:v107"),
            envelope("speech.sequence.ended", {
                "generation": 1,
                "utteranceCount": 1,
                "outcome": "completed",
            }, "turn:v107"),
        ]
        for message in messages:
            self.wfile.write(websocket_frame(json.dumps(
                message, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")))
            self.wfile.flush()
            time.sleep(0.08)
        self.server.sent.set()
        self.server.write_evidence()
        # Keep the acceptance connection alive long enough to inspect/capture;
        # closing immediately would intentionally trigger the production retry loop.
        time.sleep(60)
        self.close_connection = True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18773)
    parser.add_argument("--wav", type=Path, default=DEFAULT_WAV)
    parser.add_argument("--timeline", type=Path, default=DEFAULT_TIMELINE)
    parser.add_argument("--evidence", type=Path, default=(
        ROOT / "artifacts/autonomy/unreal-metahuman-live-speech-v107/fixture-server.json"))
    args = parser.parse_args()
    wav = args.wav.resolve().read_bytes()
    timeline = json.loads(args.timeline.resolve().read_text(encoding="utf-8"))
    server = FixtureServer((args.host, args.port), Handler, wav, timeline, args.evidence.resolve())
    server.write_evidence()
    print(json.dumps({
        "status": "listening",
        "websocket": f"ws://{args.host}:{args.port}/api/gahyeon/unreal/v1",
        "audio": f"http://{args.host}:{args.port}{AUDIO_PATH}",
    }, ensure_ascii=False), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
