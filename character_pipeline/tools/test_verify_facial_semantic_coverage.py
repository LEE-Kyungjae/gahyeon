import hashlib,json,tempfile,unittest
from pathlib import Path
from character_pipeline.tools.verify_facial_semantic_coverage import validate
CONFIG=json.loads(Path("character_pipeline/config/facial_semantic_coverage.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class T(unittest.TestCase):
 def fixture(self,root):
  morphs=["blink_l","blink_r","jaw"]+[f"v_{x}" for x in CONFIG["requiredVisemes"]]+[f"e_{x}" for x in CONFIG["requiredEmotions"]]
  cloud=root/"cloud.json";cloud.write_text(json.dumps({"assets":{"faceSkeletalMesh":{"morphTargets":morphs}}}))
  bindings=[{"group":"direct","semantic":s,"curve":c,"route":"direct-morph","scale":1.0} for s,c in (("blink-left","blink_l"),("blink-right","blink_r"),("jaw-open","jaw"))]
  bindings += [{"group":"viseme","semantic":x,"curve":f"v_{x}","route":"direct-morph","scale":1.0} for x in CONFIG["requiredVisemes"]]
  bindings += [{"group":"emotion","semantic":x,"curve":f"e_{x}","route":"control-rig-curve","scale":1.0,"animBridgeAcknowledged":True} for x in CONFIG["requiredEmotions"]]
  evidence=root/"mapping.json";evidence.write_text(json.dumps({"state":"editor-facial-mapping-observed","engine":"5.6","editorRuntimeVerified":True,"automaticApproval":False,"productionReady":False,"deformationVerified":False,"cloudAssetEvidence":{"sha256":sha(cloud)},"displayProfile":{"id":"looking-glass-go","resolution":[1440,2560],"viewCount":66},"bindings":bindings,"checks":{"presentationProfileExists":True,"profileValidationPassed":True,"runtimeResolverPresent":True,"animInstanceBridgePresent":True}}));return cloud,evidence
 def test_valid_not_production(self):
  with tempfile.TemporaryDirectory() as d:
   v=validate(CONFIG,*self.fixture(Path(d)));self.assertTrue(v["mappingCoverageVerified"]);self.assertFalse(v["deformationVerified"]);self.assertFalse(v["productionReady"])
 def mutate(self,fn,pattern):
  with tempfile.TemporaryDirectory() as d:
   c,e=self.fixture(Path(d));v=json.loads(e.read_text());fn(v);e.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,pattern):validate(CONFIG,c,e)
 def test_missing_viseme(self):self.mutate(lambda v:v["bindings"].__setitem__(slice(None),[x for x in v["bindings"] if not(x["group"]=="viseme" and x["semantic"]=="aa")]),"missing viseme")
 def test_same_blink_curve(self):self.mutate(lambda v:[x.update(curve="blink_l") for x in v["bindings"] if x["semantic"]=="blink-right"],"distinct")
 def test_duplicate_pair(self):self.mutate(lambda v:v["bindings"].append(dict(v["bindings"][0])),"duplicate")
 def test_direct_curve_absent(self):self.mutate(lambda v:[x.update(curve="missing") for x in v["bindings"] if x["semantic"]=="jaw-open"],"absent")
 def test_control_rig_unacknowledged(self):self.mutate(lambda v:[x.update(animBridgeAcknowledged=False) for x in v["bindings"] if x["group"]=="emotion"],"lacks explicit")
 def test_overclaim(self):self.mutate(lambda v:v.update(productionReady=True),"overclaims")
 def test_wrong_display(self):self.mutate(lambda v:v["displayProfile"].update(resolution=[1920,1080]),"Looking Glass Go")
if __name__=="__main__":unittest.main()
