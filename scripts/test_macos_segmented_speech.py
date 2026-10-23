import subprocess
import tempfile
import unittest
from pathlib import Path

class SegmentedSpeechTest(unittest.TestCase):
    def test_long_answer_is_bounded_without_reading_urls_or_splitting_decimal(self):
        source=Path('native/macos/GahyeonUnrealOverlay/main.swift').read_text()
        function=source.split('// MARK: - Bounded speech segments')[1].split('final class DesktopSegmentedSpeech')[0]
        checks=r'''
let text = "현금결제 14,595.00 달러, 3개월물 14,485.00 달러입니다.\n" + String(repeating: "근거를 확인한 문장입니다. ", count: 100) + "[출처](https://example.test/a)"
let parts=desktopSpeechSegments(text)
precondition(parts.count > 5)
precondition(parts.allSatisfy { $0.count <= 180 })
precondition(parts.first!.contains("14,595.00"))
precondition(parts.first!.contains("14,485.00"))
precondition(!parts.joined().contains("https://"))
precondition(parts.joined().contains("출처"))
precondition(desktopSpeechSegments("   ").isEmpty)
'''
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'test.swift';p.write_text('import Foundation\n'+function+checks)
            subprocess.run(['swift',str(p)],check=True,capture_output=True)

if __name__ == '__main__': unittest.main()
