#!/usr/bin/env python3
import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from character_pipeline.tools.verify_metahuman_runtime_face_quality import verify,sha

class T(unittest.TestCase):
 def fixture(self,root):
  ac=root/"ac.json";ac.write_text("{}")
  dc=root/"dc.json";dc.write_text(json.dumps({"samplePolicy":{"automaticApproval":False},"diagnostics":{}}))
  cases=root/"cases.json";cases.write_text(json.dumps({"requiredCases":[]}))
  mapping=root/"mapping.json";mapping.write_text("{}")
  face={"path":"/Game/Face","class":"SkeletalMesh","packageGuid":"1234"}
  act=root/"act.json";act.write_text(json.dumps({"faceAsset":face,"mappingEvidence":{"sha256":sha(mapping)}}))
  diag=root/"diag.json";diag.write_text(json.dumps({"state":"candidate","editorRuntimeVerified":True,"faceAsset":face,"actuationEvidence":{"sha256":sha(act)},"displayProfile":{"id":"looking-glass-go","resolution":[1440,2560],"viewCount":66},"samples":[],"summary":{"sampleCount":0,"failedSampleCount":0},"automaticApproval":False,"qualityClaim":None}))
  return ac,mapping,act,dc,cases,diag
 @patch("character_pipeline.tools.verify_metahuman_runtime_face_quality.validate_actuation",return_value={"samples":57})
 def test_same_asset_evidence_is_bound(self,_):
  with tempfile.TemporaryDirectory() as d:self.assertTrue(verify(*self.fixture(Path(d)))["runtimeFaceQualityVerified"])
 @patch("character_pipeline.tools.verify_metahuman_runtime_face_quality.validate_actuation",return_value={"samples":57})
 def test_different_face_asset_rejected(self,_):
  with tempfile.TemporaryDirectory() as d:
   values=list(self.fixture(Path(d)));diag=json.loads(values[-1].read_text());diag["faceAsset"]["packageGuid"]="other";values[-1].write_text(json.dumps(diag))
   with self.assertRaisesRegex(ValueError,"different face"):verify(*values)
 @patch("character_pipeline.tools.verify_metahuman_runtime_face_quality.validate_actuation",return_value={"samples":57})
 def test_unbound_diagnostics_rejected(self,_):
  with tempfile.TemporaryDirectory() as d:
   values=list(self.fixture(Path(d)));diag=json.loads(values[-1].read_text());diag["actuationEvidence"]["sha256"]="0"*64;values[-1].write_text(json.dumps(diag))
   with self.assertRaisesRegex(ValueError,"not bound"):verify(*values)
if __name__=="__main__":unittest.main()
