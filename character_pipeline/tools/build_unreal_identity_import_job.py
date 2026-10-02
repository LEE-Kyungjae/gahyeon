#!/usr/bin/env python3
"""Build and verify the immutable UE 5.6 import job for a reviewed P29 export."""

from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 p=Path(p)
 if not p.is_file() or p.is_symlink(): raise ValueError(f"missing or unsafe file: {p}")
 return json.loads(p.read_text())

def build(config,handoff_path,export_manifest_path):
 handoff=load(handoff_path); manifest=load(export_manifest_path)
 if config.get("schemaVersion")!=1 or config.get("engine")!="5.6" or config.get("replaceExisting") is not False: raise ValueError("unsafe UE import contract")
 if handoff.get("stage")!="metahuman-identity-conform-input" or handoff.get("productionMeshAllowed") is not False: raise ValueError("P28 handoff differs")
 if manifest.get("scope")!="neutral-head-neck-and-eyes-only" or manifest.get("productionMeshAllowed") is not False: raise ValueError("P29 export overclaims scope")
 source=Path(manifest.get("output",{}).get("path","")); fmt=manifest.get("output",{}).get("format")
 if fmt not in config["allowedFormats"] or source.suffix.lower()!=f".{fmt}" or not source.is_absolute() or source.is_symlink() or not source.is_file() or digest(source)!=manifest["output"].get("sha256"): raise ValueError("P29 export file differs")
 if manifest.get("coordinateContract")!={"unit":"centimeter","upAxis":"+Z","forwardAxis":"+X","handedness":"left"}: raise ValueError("P29 coordinate contract differs")
 return {"schemaVersion":1,"state":"ready-for-unreal-editor-import","engine":"5.6","project":config["project"],
  "handoff":{"path":str(Path(handoff_path).resolve()),"sha256":digest(handoff_path)},"exportManifest":{"path":str(Path(export_manifest_path).resolve()),"sha256":digest(export_manifest_path)},
  "source":{"path":str(source),"sha256":digest(source),"format":fmt,"scope":manifest["scope"]},
  "import":{"destinationPath":config["destinationPath"],"assetName":config["assetName"],"combineMeshes":True,"replaceExisting":False,"automated":True,"save":True},
  "expectedAssetPath":f"{config['destinationPath']}/{config['assetName']}","nextState":config["nextState"],
  "manualGate":{"required":True,"steps":["create MetaHuman Identity asset","Configure Components From Mesh using imported Static Mesh","promote and lock neutral front frame","track markers and visually correct eyelids, lips, nasolabial folds, nose and ears","run Identity Solve and inspect template A/B overlay"],"automaticApproval":False},
  "productionMeshAllowed":False}

def verify(job_path,receipt_path=None):
 job=load(job_path)
 if job.get("state")!="ready-for-unreal-editor-import" or job.get("engine")!="5.6" or job.get("productionMeshAllowed") is not False: raise ValueError("UE import job overclaims state")
 for key in ("handoff","exportManifest","source"):
  r=job[key];p=Path(r["path"])
  if not p.is_absolute() or p.is_symlink() or not p.is_file() or digest(p)!=r["sha256"]: raise ValueError(f"UE import lineage differs: {key}")
 imp=job["import"]
 if imp.get("replaceExisting") is not False or imp.get("combineMeshes") is not True or not job.get("manualGate",{}).get("required"): raise ValueError("UE import safety policy differs")
 if receipt_path:
  receipt=load(receipt_path)
  if receipt.get("state")!="imported-awaiting-identity-guided-workflow" or receipt.get("job",{}).get("sha256")!=digest(job_path) or receipt.get("source",{}).get("sha256")!=job["source"]["sha256"]: raise ValueError("UE import receipt lineage differs")
  if receipt.get("asset",{}).get("path")!=job["expectedAssetPath"] or receipt.get("identitySolved") is not False or receipt.get("productionMeshAllowed") is not False: raise ValueError("UE import receipt overclaims Identity state")
 return {"valid":True,"state":job["state"],"manualIdentityGate":True,"productionMeshAllowed":False}

def main():
 p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=Path("character_pipeline/config/unreal_metahuman_identity_import.json"));p.add_argument("--handoff",type=Path);p.add_argument("--export-manifest",type=Path);p.add_argument("--output",type=Path,required=True);p.add_argument("--verify",action="store_true");p.add_argument("--receipt",type=Path);a=p.parse_args()
 if a.verify:r=verify(a.output.resolve(),a.receipt.resolve() if a.receipt else None)
 else:
  if not a.handoff or not a.export_manifest:p.error("--handoff and --export-manifest required")
  if a.output.exists():raise SystemExit(f"refusing to overwrite: {a.output}")
  r=build(load(a.config),a.handoff.resolve(),a.export_manifest.resolve());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps({"valid":True,"state":r["state"],"productionMeshAllowed":False}));return 0
if __name__=="__main__":raise SystemExit(main())
