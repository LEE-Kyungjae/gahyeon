import hashlib,json,tempfile,unittest
from pathlib import Path
from character_pipeline.tools.build_metahuman_identity_conform_job import build,verify
CONFIG=json.loads(Path("character_pipeline/config/metahuman_identity_conform.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class TestConform(unittest.TestCase):
 def fixture(self,r):
  job=r/"import-job.json";job.write_text(json.dumps({"source":{"sha256":"a"}}));imp=r/"import-receipt.json";imp.write_text(json.dumps({"state":"imported-awaiting-identity-guided-workflow","job":{"sha256":sha(job)},"source":{"sha256":"a"},"identitySolved":False}));sol=r/"solved.json";sol.write_text(json.dumps({"state":"identity-solved-human-reviewed","automatic":False,"productionReady":False,"importReceipt":{"sha256":sha(imp)},"reviewer":{"name":"Tech","role":"character-technical-artist"},"reviewedAt":"2026-08-13T00:00:00Z","identityAsset":{"path":"/Game/Gahyeon/MI_Gahyeon","class":"MetaHumanIdentity"},"checks":{"neutralFrameTracked":True,"markersHumanCorrected":True,"identitySolveCompleted":True,"templateOverlayReviewed":True}}));return job,imp,sol
 def test_valid(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b,c=self.fixture(r);v=build(CONFIG,a,b,c,"/Game/Gahyeon/MHC_Gahyeon");p=r/"j.json";p.write_text(json.dumps(v));self.assertEqual(verify(p)["requiredResult"],"SUCCESS");self.assertFalse(v["productionReady"])
 def test_unsolved(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b,c=self.fixture(r);v=json.loads(c.read_text());v["checks"]["identitySolveCompleted"]=False;c.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"identitySolveCompleted"):build(CONFIG,a,b,c,"/Game/Gahyeon/MHC")
 def test_lineage(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b,c=self.fixture(r);v=json.loads(c.read_text());v["importReceipt"]["sha256"]="x";c.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"lineage"):build(CONFIG,a,b,c,"/Game/Gahyeon/MHC")
 def test_review(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b,c=self.fixture(r);v=json.loads(c.read_text());v["reviewer"]["role"]="bot";c.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"reviewer"):build(CONFIG,a,b,c,"/Game/Gahyeon/MHC")
 def test_receipt_overclaim(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b,c=self.fixture(r);v=build(CONFIG,a,b,c,"/Game/Gahyeon/MHC");p=r/"j.json";p.write_text(json.dumps(v));q=r/"r.json";q.write_text(json.dumps({"state":"conformed-head-awaiting-production-systems","job":{"sha256":sha(p)},"result":"SUCCESS","productionReady":True}))
   with self.assertRaisesRegex(ValueError,"overclaims"):verify(p,q)
if __name__=="__main__":unittest.main()
