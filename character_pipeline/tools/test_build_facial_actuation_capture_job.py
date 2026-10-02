import json,tempfile,unittest
from pathlib import Path
from character_pipeline.tools.build_facial_actuation_capture_job import build
CONFIG=json.loads(Path("character_pipeline/config/facial_actuation_qa.json").read_text())
class T(unittest.TestCase):
 def fixture(self,root):
  p=root/"mapping.json";p.write_text(json.dumps({"state":"editor-facial-mapping-observed","editorRuntimeVerified":True,"productionReady":False,"deformationVerified":False}));return p
 def test_build_exact_go_job(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);v=build(CONFIG,self.fixture(root),root/"out");self.assertEqual(v["expectedSamples"],57);self.assertEqual(v["displayProfile"]["resolution"],[1440,2560]);self.assertEqual(v["displayProfile"]["viewCount"],66);self.assertTrue(v["sequence"]["neverOverwrite"]);self.assertFalse(v["productionReady"])
 def test_not_editor_observed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=self.fixture(root);v=json.loads(p.read_text());v["editorRuntimeVerified"]=False;p.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"Editor mapping"):build(CONFIG,p,root/"out")
 def test_overclaim(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);p=self.fixture(root);v=json.loads(p.read_text());v["deformationVerified"]=True;p.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"overclaims"):build(CONFIG,p,root/"out")
if __name__=="__main__":unittest.main()
