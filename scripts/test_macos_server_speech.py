import http.server
import json
import os
from pathlib import Path
import subprocess
import threading
import unittest

ROOT = Path(__file__).resolve().parents[1]

class MacosServerSpeechTest(unittest.TestCase):
    def test_native_client_posts_wav_and_synthesis_with_auth(self):
        calls = []
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers['Content-Length']))
                calls.append((self.path, self.headers.get('Authorization'), self.headers.get('Content-Type'), body))
                response = b'{"transcript":"fixture"}' if self.path.endswith('transcriptions') else b'RIFF-fixture'
                self.send_response(200); self.end_headers(); self.wfile.write(response)
            def log_message(self, *args): pass
        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        worker = threading.Thread(target=server.serve_forever, daemon=True); worker.start()
        source = (ROOT / 'native/macos/GahyeonUnrealOverlay/main.swift').read_text()
        client = source[source.index('final class DesktopCoreClient'):source.index('final class NativeSpeechInput')]
        code = 'import Foundation\n' + client + '''
let client = DesktopCoreClient()
var complete = false
client.speechData(path: "transcriptions", data: Data("RIFF-input".utf8), mediaType: "audio/wav") { result in
    precondition((try? result.get()) == Data("{\\"transcript\\":\\"fixture\\"}".utf8))
    complete = true
}
while !complete { RunLoop.current.run(until: Date().addingTimeInterval(0.01)) }
complete = false
client.speechData(path: "synthesis", data: Data("{\\"text\\":\\"fixture\\"}".utf8), mediaType: "application/json") { result in
    precondition((try? result.get()) == Data("RIFF-fixture".utf8))
    complete = true
}
while !complete { RunLoop.current.run(until: Date().addingTimeInterval(0.01)) }
'''
        try:
            env = dict(os.environ, GAHYEON_CORE_URL=f'http://127.0.0.1:{server.server_port}/api', GAHYEON_CLIENT_TOKEN='fixture-only')
            subprocess.run(['swift', '-e', code], env=env, check=True, timeout=30, capture_output=True)
            self.assertEqual([x[0] for x in calls], ['/api/gahyeon/desktop/speech/transcriptions','/api/gahyeon/desktop/speech/synthesis'])
            self.assertTrue(all(x[1] == 'Bearer fixture-only' for x in calls))
            self.assertEqual(calls[0][2:], ('audio/wav',b'RIFF-input'))
            self.assertEqual(calls[1][2], 'application/json')
            self.assertEqual(json.loads(calls[1][3]), {'text':'fixture'})
        finally: server.shutdown(); server.server_close()

if __name__ == '__main__': unittest.main()
