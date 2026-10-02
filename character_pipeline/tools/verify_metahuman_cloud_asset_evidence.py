#!/usr/bin/env python3
"""Verify immutable Editor-observed rig/morph/texture evidence after P32."""
import argparse,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 p=Path(p)
 if not p.is_file() or p.is_symlink():raise ValueError(f"missing or unsafe file: {p}")
 return json.loads(p.read_text())
def validate(config,cloud_job_path,cloud_receipt_path,evidence_path):
 job,receipt,e=load(cloud_job_path),load(cloud_receipt_path),load(evidence_path)
 if receipt.get("job",{}).get("sha256")!=sha(cloud_job_path) or receipt.get("state")!="cloud-requests-completed-awaiting-asset-verification":raise ValueError("P32 receipt lineage differs")
 if e.get("cloudReceipt",{}).get("sha256")!=sha(cloud_receipt_path) or e.get("state")!="editor-cloud-assets-observed":raise ValueError("Editor evidence lineage differs")
 if e.get("editorRuntimeVerified") is not True or e.get("engine")!="5.6" or e.get("automaticApproval") is not False or e.get("productionReady") is not False:raise ValueError("Editor evidence overclaims or lacks runtime verification")
 assets=e.get("assets",{});classes=config["requiredClasses"]
 if assets.get("character",{}).get("class")!=classes["character"] or assets.get("character",{}).get("path")!=job.get("characterAsset",{}).get("path"):raise ValueError("MetaHuman Character evidence differs")
 face=assets.get("faceSkeletalMesh",{})
 if face.get("class")!=classes["faceSkeletalMesh"] or face.get("exists") is not True:raise ValueError("face SkeletalMesh evidence missing")
 morphs=face.get("morphTargets",[])
 if len(morphs)<config["minimumMorphTargets"] or len(morphs)!=len(set(morphs)):raise ValueError("blendshape evidence missing or duplicate")
 textures=assets.get("textureSources",[])
 if len(textures)<config["minimumTextureSources"]:raise ValueError("texture source evidence missing")
 for t in textures:
  if t.get("class")!=classes["textureSource"] or t.get("exists") is not True or min(t.get("dimensions",[0,0]))<config["minimumTextureDimension"]:raise ValueError("texture source is missing, wrong-class or below 4K")
 checks=e.get("checks",{})
 required=("faceSkeletalMeshExists","morphTargetsObserved","textureSourcesObserved","rigRequestWasBlendshapeType")
 if any(checks.get(k) is not True for k in required):raise ValueError("Editor cloud asset checks incomplete")
 if e.get("rigType")!="JOINTS_AND_BLENDSHAPES":raise ValueError("Editor evidence rig type differs")
 return {"valid":True,"faceRigVerified":True,"blendshapesVerified":True,"textureSourcesVerified":True,"morphTargets":len(morphs),"textureSources":len(textures),"productionReady":False,"surfaceProductionApproved":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=Path("character_pipeline/config/metahuman_cloud_asset_evidence.json"));p.add_argument("--cloud-job",type=Path,required=True);p.add_argument("--cloud-receipt",type=Path,required=True);p.add_argument("--evidence",type=Path,required=True);a=p.parse_args();print(json.dumps(validate(load(a.config),a.cloud_job.resolve(),a.cloud_receipt.resolve(),a.evidence.resolve())));return 0
if __name__=="__main__":raise SystemExit(main())
