#!/usr/bin/env python3
import json,tempfile,unittest
from pathlib import Path
from character_pipeline.tools.verify_looking_glass_hero_runtime import verify,sha
class T(unittest.TestCase):
 def fixture(self,root):
  run="run_12345678";accept=root/"accept.json";accept.write_text(json.dumps({"status":"passed","latencyBoundary":"physical-presentation-v1","measurementRunId":run,"display":{"model":"Looking Glass Go"},"software":{"unreal":"5.6"},"profiles":[{"mode":"Realtime","views":66},{"mode":"RealtimeAdaptive","views":66},{"mode":"NonRealtime","views":66}]}))
  asset={"path":"/Game/Gahyeon.Gahyeon_C","packageGuid":"abcd","class":"BlueprintGeneratedClass"};systems={x:True for x in ("metaHumanFace","rigLogic","layeredSkin","physicalEyes","strandGroom","modularClothing","bodyRig","facialActuation")}
  hero=root/"hero.json";hero.write_text(json.dumps({"state":"approved-hero-runtime-evidence","editorRuntimeVerified":True,"automaticApproval":False,"measurementRunId":run,"acceptanceSha256":sha(accept),"heroAsset":asset,"productionSystems":systems}))
  binding=root/"binding.json";binding.write_text(json.dumps({"heroBlueprint":asset["path"],"heroPackageGuid":asset["packageGuid"]}));return accept,hero,binding
 def test_exact_hero_and_run_pass(self):
  with tempfile.TemporaryDirectory() as d:self.assertTrue(verify(*self.fixture(Path(d)))["physicalPresentationPassed"])
 def test_placeholder_swap_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   values=list(self.fixture(Path(d)));b=json.loads(values[-1].read_text());b["heroPackageGuid"]="other";values[-1].write_text(json.dumps(b))
   with self.assertRaisesRegex(ValueError,"differs"):verify(*values)
 def test_different_run_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   values=list(self.fixture(Path(d)));h=json.loads(values[1].read_text());h["measurementRunId"]="run_other123";values[1].write_text(json.dumps(h))
   with self.assertRaisesRegex(ValueError,"different runs"):verify(*values)
if __name__=="__main__":unittest.main()
