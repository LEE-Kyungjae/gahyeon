#!/usr/bin/env python3
"""Verify every production subsystem belongs to one exact v002 MetaHuman Hero."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

ROLES=("identity","surface","groom","clothing","runtimeFace","lookingGlass")
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
 path=Path(path)
 if not path.is_file() or path.is_symlink():raise ValueError(f"missing or unsafe evidence: {path}")
 return json.loads(path.read_text())
def verify(manifest_path):
 manifest_path=Path(manifest_path).resolve();value=load(manifest_path)
 if value.get("schemaVersion")!=1 or value.get("chainId")!="gahyeon-metahuman-hero-production-v002":raise ValueError("wrong production chain")
 if value.get("state")!="candidate-awaiting-final-human-approval" or value.get("automaticApproval") is not False or value.get("qualityClaim") is not None:raise ValueError("production chain lifecycle or claims differ")
 hero=value.get("heroAsset",{})
 if not hero.get("path") or hero.get("class")!="BlueprintGeneratedClass" or not hero.get("packageGuid"):raise ValueError("exact Hero package identity missing")
 face=value.get("faceAsset",{})
 if not face.get("path") or face.get("class")!="SkeletalMesh" or not face.get("packageGuid"):raise ValueError("exact MetaHuman face identity missing")
 receipts=value.get("receipts",{})
 if set(receipts)!=set(ROLES):raise ValueError("production subsystem receipts incomplete")
 loaded={}
 for role,item in receipts.items():
  uri=item.get("uri");path=(manifest_path.parent/uri).resolve() if isinstance(uri,str) else Path()
  if path.is_symlink() or not path.is_file() or sha(path)!=item.get("sha256"):raise ValueError(f"production receipt missing or changed: {role}")
  receipt=load(path);loaded[role]=receipt
  if receipt.get("valid") is not True or receipt.get("automaticApproval") is not False:raise ValueError(f"production receipt is not verified: {role}")
  if receipt.get("iteration") not in (None,"v002"):raise ValueError(f"production receipt iteration differs: {role}")
 for role in ("surface","groom","clothing","lookingGlass"):
  asset=loaded[role].get("heroAsset")
  if asset!=hero:raise ValueError(f"production receipt uses a different Hero: {role}")
 if loaded["runtimeFace"].get("faceAsset")!=face:raise ValueError("runtime face receipt uses a different face")
 if loaded["identity"].get("faceAsset")!=face or loaded["identity"].get("heroAsset")!=hero:raise ValueError("identity receipt does not bind Hero and face")
 if loaded["identity"].get("decision")!="keep-and-build-surfaces":raise ValueError("identity was not explicitly kept")
 if loaded["lookingGlass"].get("physicalPresentationPassed") is not True or loaded["lookingGlass"].get("viewCount")!=66:raise ValueError("physical 66-view acceptance missing")
 return {"valid":True,"chainId":value["chainId"],"heroAsset":hero,"faceAsset":face,"receipts":6,"physicalPresentationPassed":True,"automaticApproval":False,"qualityClaim":None}
def main():
 p=argparse.ArgumentParser();p.add_argument("manifest",type=Path);a=p.parse_args();print(json.dumps(verify(a.manifest)));return 0
if __name__=="__main__":raise SystemExit(main())
