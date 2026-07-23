#!/usr/bin/env python3
import asyncio
import json
import os
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import edge_tts


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            self.send_error(404)
            return
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def do_POST(self):
        if self.path != "/synthesize":
            self.send_error(404)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            request = json.loads(self.rfile.read(size))
            text = str(request["text"]).strip()
            if not text or len(text) > 1000:
                raise ValueError("invalid text")
            fd, path = tempfile.mkstemp(suffix=".mp3")
            os.close(fd)
            try:
                communicate = edge_tts.Communicate(
                    text,
                    request.get("voice", "ko-KR-SunHiNeural"),
                    rate=request.get("rate", "+0%"),
                    pitch=request.get("pitch", "+0Hz"),
                )
                asyncio.run(communicate.save(path))
                with open(path, "rb") as audio:
                    payload = audio.read()
            finally:
                os.unlink(path)
            self.send_response(200)
            self.send_header("Content-Type", "audio/mpeg")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:
            self.send_error(500, str(exc))

    def log_message(self, fmt, *args):
        print(fmt % args, flush=True)


ThreadingHTTPServer(("0.0.0.0", 8765), Handler).serve_forever()
