import os
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class MacosCoreConnectionTest(unittest.TestCase):
    def test_request_preserves_api_prefix_and_authenticates(self):
        source = (ROOT / 'native/macos/GahyeonUnrealOverlay/main.swift').read_text()
        start = source.index('        var request = URLRequest(', source.index('private func request<T: Decodable>'))
        end = source.index('        if body != nil', start)
        actual = source[start:end]
        code = '''import Foundation
let root = URL(string: "http://127.0.0.1:18080/api")!
let path = "/gahyeon/desktop/speech/status"
let method = "GET"
let body: Data? = nil
''' + actual + '''
precondition(request.url!.absoluteString == "http://127.0.0.1:18080/api/gahyeon/desktop/speech/status")
precondition(request.value(forHTTPHeaderField: "Authorization") == "Bearer fixture-only")
'''
        env = dict(os.environ, GAHYEON_CLIENT_TOKEN='fixture-only')
        subprocess.run(['swift', '-e', code], check=True, env=env, capture_output=True)

if __name__ == '__main__': unittest.main()
