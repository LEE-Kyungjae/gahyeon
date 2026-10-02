import hashlib,json,tempfile,unittest
from pathlib import Path
from character_pipeline.tools.verify_metahuman_cloud_asset_evidence import validate
CONFIG=json.loads(Path("character_pipeline/config/metahuman_cloud_asset_evidence.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class T(unittest.TestCase):
 def fixture(self,r):
  j=r/"j.json";j.write_text(json.dumps({"characterAsset":{"path":"/Game/G/MHC"}}));q=r/"q.json";q.write_text(json.dumps({"state":"cloud-requests-completed-awaiting-asset-verification","job":{"sha256":sha(j)}}));e=r/"e.json";e.write_text(json.dumps({"state":"editor-cloud-assets-observed","engine":"5.6","editorRuntimeVerified":True,"automaticApproval":False,"productionReady":False,"cloudReceipt":{"sha256":sha(q)},"rigType":"JOINTS_AND_BLENDSHAPES","assets":{"character":{"path":"/Game/G/MHC","class":"MetaHumanCharacter"},"faceSkeletalMesh":{"exists":True,"class":"SkeletalMesh","morphTargets":["jawOpen","eyeBlinkL"]},"textureSources":[{"exists":True,"class":"Texture2D","dimensions":[4096,4096]}]},"checks":{"faceSkeletalMeshExists":True,"morphTargetsObserved":True,"textureSourcesObserved":True,"rigRequestWasBlendshapeType":True}}));return j,q,e
 def test_valid_but_not_production(self):
  with tempfile.TemporaryDirectory() as d:
   v=validate(CONFIG,*self.fixture(Path(d)));self.assertTrue(v["blendshapesVerified"]);self.assertFalse(v["productionReady"]);self.assertFalse(v["surfaceProductionApproved"])
 def test_no_morph(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,e=self.fixture(Path(d));v=json.loads(e.read_text());v["assets"]["faceSkeletalMesh"]["morphTargets"]=[];e.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"blendshape"):validate(CONFIG,a,b,e)
 def test_lowres(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,e=self.fixture(Path(d));v=json.loads(e.read_text());v["assets"]["textureSources"][0]["dimensions"]=[2048,4096];e.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"below 4K"):validate(CONFIG,a,b,e)
 def test_lineage(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,e=self.fixture(Path(d));b.write_text("{}")
   with self.assertRaisesRegex(ValueError,"lineage"):validate(CONFIG,a,b,e)
 def test_overclaim(self):
  with tempfile.TemporaryDirectory() as d:
   a,b,e=self.fixture(Path(d));v=json.loads(e.read_text());v["productionReady"]=True;e.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,"overclaims"):validate(CONFIG,a,b,e)
if __name__=="__main__":unittest.main()
