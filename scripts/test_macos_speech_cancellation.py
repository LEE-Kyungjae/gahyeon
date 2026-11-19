import subprocess
import tempfile
import unittest
from pathlib import Path

class SpeechCancellationTest(unittest.TestCase):
    def test_late_synthesis_after_cancellation_cannot_start_audio_or_report_error(self):
        source=Path('native/macos/GahyeonUnrealOverlay/main.swift').read_text()
        helper=source.split('// MARK: - Bounded speech segments')[1].split('// MARK: - End bounded speech segments')[0]
        stub='''import Foundation
import AVFoundation
final class DesktopCoreClient {
 var callback: ((Result<Data, Error>) -> Void)?
 var requests=0
 func speechData(path:String,data:Data,mediaType:String,completion:@escaping(Result<Data,Error>)->Void) {
  requests += 1; callback=completion
 }
}
'''
        checks='''
let core=DesktopCoreClient()
var active=true, delivered=false, failed=false
let speech=DesktopSegmentedSpeech(core:core,current:{active},deliver:{_ in delivered=true},failure:{_ in failed=true})
speech.start(String(repeating:"테스트 문장입니다. ",count:100))
precondition(core.requests==1)
active=false
core.callback?(.success(Data([0])))
core.callback?(.failure(NSError(domain:"test",code:1)))
precondition(!delivered && !failed && core.requests==1)
'''
        with tempfile.TemporaryDirectory() as temp:
            p=Path(temp)/'test.swift';p.write_text(stub+helper+checks)
            subprocess.run(['swift',str(p)],check=True,capture_output=True)

if __name__=='__main__':unittest.main()
