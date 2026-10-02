#!/usr/bin/env python3
import json,tempfile,unittest
from pathlib import Path
from character_pipeline.tools.verify_metahuman_hero_production_chain_v002 import verify,sha,ROLES
class T(unittest.TestCase):
 def fixture(self,root):
  hero={"path":"/Game/Hero.Hero_C","class":"BlueprintGeneratedClass","packageGuid":"hero-guid"};face={"path":"/Game/Face.Face","class":"SkeletalMesh","packageGuid":"face-guid"};receipts={}
  for role in ROLES:
   value={"valid":True,"automaticApproval":False,"iteration":"v002"}
   if role in ("surface","groom","clothing","lookingGlass"):value["heroAsset"]=hero
   if role=="runtimeFace":value["faceAsset"]=face
   if role=="identity":value.update(heroAsset=hero,faceAsset=face,decision="keep-and-build-surfaces")
   if role=="lookingGlass":value.update(physicalPresentationPassed=True,viewCount=66)
   path=root/f"{role}.json";path.write_text(json.dumps(value));receipts[role]={"uri":path.name,"sha256":sha(path)}
  manifest=root/"chain.json";manifest.write_text(json.dumps({"schemaVersion":1,"chainId":"gahyeon-metahuman-hero-production-v002","state":"candidate-awaiting-final-human-approval","heroAsset":hero,"faceAsset":face,"receipts":receipts,"automaticApproval":False,"qualityClaim":None}));return manifest
 def test_one_exact_hero_chain_passes(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(verify(self.fixture(Path(d)))["receipts"],6)
 def test_surface_from_other_hero_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);manifest=self.fixture(root);value=json.loads((root/"surface.json").read_text());value["heroAsset"]["packageGuid"]="other";(root/"surface.json").write_text(json.dumps(value));m=json.loads(manifest.read_text());m["receipts"]["surface"]["sha256"]=sha(root/"surface.json");manifest.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,"different Hero"):verify(manifest)
 def test_face_from_other_character_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);manifest=self.fixture(root);value=json.loads((root/"runtimeFace.json").read_text());value["faceAsset"]["packageGuid"]="other";(root/"runtimeFace.json").write_text(json.dumps(value));m=json.loads(manifest.read_text());m["receipts"]["runtimeFace"]["sha256"]=sha(root/"runtimeFace.json");manifest.write_text(json.dumps(m))
   with self.assertRaisesRegex(ValueError,"different face"):verify(manifest)
if __name__=="__main__":unittest.main()
