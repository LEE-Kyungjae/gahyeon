import os
from pathlib import Path
import subprocess
import unittest

class MacosChatTimeoutTest(unittest.TestCase):
    def test_research_wait_budget_does_not_change_health_checks(self):
        source = Path('native/macos/GahyeonUnrealOverlay/main.swift').read_text()
        start = source.index('        var request = URLRequest(', source.index('private func request<T: Decodable>'))
        end = source.index('        if body != nil', start)
        actual = source[start:end]
        code = '''import Foundation
let root = URL(string: "http://127.0.0.1:18080/api")!
let body: Data? = nil
for (path, method, expected) in [("/gahyeon/desktop/conversations/session/messages", "POST", 180.0),
("/gahyeon/desktop/speech/status", "GET", 20.0)] {
''' + actual + '''
precondition(request.timeoutInterval == expected)
precondition(request.url!.path.hasPrefix("/api/gahyeon/desktop/"))
precondition(request.value(forHTTPHeaderField:"Authorization") == "Bearer fixture-only")
}
'''
        subprocess.run(['swift','-e',code],env=dict(os.environ,GAHYEON_CLIENT_TOKEN='fixture-only'),check=True,capture_output=True)

if __name__ == '__main__': unittest.main()
