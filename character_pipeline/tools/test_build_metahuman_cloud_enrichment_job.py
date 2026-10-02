import hashlib,json,tempfile,unittest
from pathlib import Path
from character_pipeline.tools.build_metahuman_cloud_enrichment_job import build,verify
CONFIG=json.loads(Path("character_pipeline/config/metahuman_cloud_enrichment.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class T(unittest.TestCase):
 def fixture(self,r):
  j=r/"cjob.json";j.write_text("{}");q=r/"creceipt.json";q.write_text(json.dumps({"state":"conformed-head-awaiting-production-systems","job":{"sha256":sha(j)},"result":"SUCCESS","productionReady":False,"faceRigGenerated":False,"highResolutionTexturesDownloaded":False,"characterAsset":{"path":"/Game/G/MHC","expectedClass":"MetaHumanCharacter"}}));return j,q
 def test_valid(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b=self.fixture(r);v=build(CONFIG,a,b);p=r/"j.json";p.write_text(json.dumps(v));self.assertEqual(verify(p)["rigType"],"JOINTS_AND_BLENDSHAPES")
 def test_lineage(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b=self.fixture(r);v=json.loads(b.read_text());v["job"]["sha256"]="x";b.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"differs"):build(CONFIG,a,b)
 def test_partial_overclaim(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b=self.fixture(r);v=json.loads(b.read_text());v["faceRigGenerated"]=True;b.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"overclaims"):build(CONFIG,a,b)
 def test_bad_rig_config(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b=self.fixture(r);c=dict(CONFIG);c["rigType"]="JOINTS_ONLY"
   with self.assertRaisesRegex(ValueError,"unsafe"):build(c,a,b)
 def test_cloud_receipt_cannot_verify_assets(self):
  with tempfile.TemporaryDirectory() as d:
   r=Path(d);a,b=self.fixture(r);v=build(CONFIG,a,b);p=r/"j.json";p.write_text(json.dumps(v));q=r/"r.json";q.write_text(json.dumps({"state":"cloud-requests-completed-awaiting-asset-verification","job":{"sha256":sha(p)},"requestsReturned":["auto-rig","texture-sources"],"faceRigVerified":True,"blendshapesVerified":False,"textureSourcesVerified":False,"productionReady":False}))
   with self.assertRaisesRegex(ValueError,"fabricates"):verify(p,q)
if __name__=="__main__":unittest.main()
