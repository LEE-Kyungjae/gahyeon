import hashlib,json,tempfile,unittest
from pathlib import Path
from character_pipeline.tools.build_unreal_identity_import_job import build,verify
CONFIG=json.loads(Path("character_pipeline/config/unreal_metahuman_identity_import.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class TestJob(unittest.TestCase):
 def fixture(self,r):
  src=r/"head.obj";src.write_bytes(b"obj");hand=r/"handoff.json";hand.write_text(json.dumps({"stage":"metahuman-identity-conform-input","productionMeshAllowed":False}));m=r/"export.json";m.write_text(json.dumps({"scope":"neutral-head-neck-and-eyes-only","productionMeshAllowed":False,"coordinateContract":{"unit":"centimeter","upAxis":"+Z","forwardAxis":"+X","handedness":"left"},"output":{"path":str(src),"format":"obj","sha256":sha(src)}}));return hand,m,src
 def test_build_verify(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);h,m,_=self.fixture(r);v=build(CONFIG,h,m);p=r/"job.json";p.write_text(json.dumps(v));self.assertTrue(verify(p)["manualIdentityGate"]);self.assertFalse(v["productionMeshAllowed"])
 def test_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);h,m,s=self.fixture(r);s.write_bytes(b"x")
   with self.assertRaisesRegex(ValueError,"file differs"):build(CONFIG,h,m)
 def test_wrong_coordinate(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);h,m,_=self.fixture(r);v=json.loads(m.read_text());v["coordinateContract"]["unit"]="meter";m.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"coordinate"):build(CONFIG,h,m)
 def test_receipt_overclaim(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);h,m,_=self.fixture(r);v=build(CONFIG,h,m);p=r/"job.json";p.write_text(json.dumps(v));receipt=r/"receipt.json";receipt.write_text(json.dumps({"state":"imported-awaiting-identity-guided-workflow","job":{"sha256":sha(p)},"source":{"sha256":v["source"]["sha256"]},"asset":{"path":v["expectedAssetPath"]},"identitySolved":True,"productionMeshAllowed":False}))
   with self.assertRaisesRegex(ValueError,"overclaims"):verify(p,receipt)
 def test_existing_job_lineage_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);h,m,_=self.fixture(r);v=build(CONFIG,h,m);p=r/"job.json";p.write_text(json.dumps(v));h.write_text("{}")
   with self.assertRaisesRegex(ValueError,"handoff"):verify(p)
if __name__=="__main__":unittest.main()
