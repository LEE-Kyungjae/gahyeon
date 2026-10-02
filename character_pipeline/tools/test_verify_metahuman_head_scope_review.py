import hashlib,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
from character_pipeline.tools.verify_metahuman_head_scope_review import validate

CONFIG=json.loads(Path("character_pipeline/config/metahuman_head_scope_review.json").read_text()); NOW=datetime(2026,8,13,3,tzinfo=timezone.utc)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()

class TestScope(unittest.TestCase):
 def fixture(self,root):
  scene=root/"work.blend";scene.write_bytes(b"blend");report=root/"report.json"
  report.write_text(json.dumps({"claim":"review-required-head-scope-working-scene","output":{"sha256":sha(scene)},"objects":[{"name":"Head"},{"name":"Eyes"}]}))
  review={"schemaVersion":1,"scope":CONFIG["requiredScope"],"approved":True,"automatic":False,"productionMeshAllowed":False,
   "reviewer":{"name":"Tech","role":"character-technical-artist"},"reviewedAt":"2026-08-13T02:00:00Z",
   "workingScene":{"path":str(scene),"sha256":sha(scene)},"preparationReport":{"path":str(report),"sha256":sha(report)},"selectedObjects":["Head","Eyes"],
   "views":[{"view":x,"verdict":"acceptable","notes":"checked"} for x in CONFIG["requiredViews"]],
   "checks":[{"check":x,"passed":True,"notes":"checked"} for x in CONFIG["requiredChecks"]]}
  p=root/"review.json";p.write_text(json.dumps(review));return p,scene,report
 def test_valid(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(len(validate(CONFIG,self.fixture(Path(d))[0],NOW)["selectedObjects"]),2)
 def test_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p,s,_=self.fixture(Path(d));s.write_bytes(b"x")
   with self.assertRaisesRegex(ValueError,"scene checksum"):validate(CONFIG,p,NOW)
 def test_missing_or_blocking_review(self):
  with tempfile.TemporaryDirectory() as d:
   p,_,_=self.fixture(Path(d));v=json.loads(p.read_text());v["views"].pop();p.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"all five"):validate(CONFIG,p,NOW)
 def test_unknown_or_duplicate_object(self):
  with tempfile.TemporaryDirectory() as d:
   p,_,_=self.fixture(Path(d));v=json.loads(p.read_text());v["selectedObjects"]=["Head","Head"];p.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"duplicate"):validate(CONFIG,p,NOW)
 def test_automatic_fails(self):
  with tempfile.TemporaryDirectory() as d:
   p,_,_=self.fixture(Path(d));v=json.loads(p.read_text());v["automatic"]=True;p.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"explicit"):validate(CONFIG,p,NOW)

if __name__=="__main__":unittest.main()
