#!/usr/bin/env python3
"""Validate solved-Identity evidence and build a UE 5.6 import_from_identity job."""
from __future__ import annotations
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 p=Path(p)
 if not p.is_file() or p.is_symlink():raise ValueError(f"missing or unsafe file: {p}")
 return json.loads(p.read_text())
def build(config,import_job_path,import_receipt_path,solved_receipt_path,character_asset_path):
 job,imp,solved=load(import_job_path),load(import_receipt_path),load(solved_receipt_path)
 if config.get("engine")!="5.6" or config.get("replaceExisting") is not False or config.get("automaticApproval") is not False:raise ValueError("unsafe conform config")
 if imp.get("job",{}).get("sha256")!=sha(import_job_path) or imp.get("source",{}).get("sha256")!=job.get("source",{}).get("sha256"):raise ValueError("P30 import lineage differs")
 if imp.get("state")!="imported-awaiting-identity-guided-workflow" or imp.get("identitySolved") is not False:raise ValueError("P30 import receipt overclaims Identity")
 if solved.get("state")!="identity-solved-human-reviewed" or solved.get("automatic") is not False or solved.get("productionReady") is not False:raise ValueError("solved Identity evidence is absent or overclaims readiness")
 if solved.get("importReceipt",{}).get("sha256")!=sha(import_receipt_path):raise ValueError("solved Identity and P30 receipt lineage differ")
 reviewer=solved.get("reviewer",{})
 if not reviewer.get("name") or reviewer.get("role") not in config["authorizedReviewerRoles"]:raise ValueError("solved Identity requires authorized named reviewer")
 reviewed=datetime.fromisoformat(solved.get("reviewedAt","").replace("Z","+00:00"))
 if reviewed.tzinfo is None or reviewed.astimezone(timezone.utc)>datetime.now(timezone.utc):raise ValueError("solved Identity review timestamp invalid")
 identity=solved.get("identityAsset",{})
 if identity.get("class")!=config["identityAssetClass"] or not str(identity.get("path","")).startswith("/Game/"):raise ValueError("solved Identity asset evidence differs")
 for key in ("neutralFrameTracked","markersHumanCorrected","identitySolveCompleted","templateOverlayReviewed"):
  if solved.get("checks",{}).get(key) is not True:raise ValueError(f"solved Identity check missing: {key}")
 if not character_asset_path.startswith("/Game/") or character_asset_path==identity["path"]:raise ValueError("target MetaHuman Character asset path invalid")
 return {"schemaVersion":1,"state":"ready-to-conform-from-identity","engine":"5.6","importJob":{"path":str(Path(import_job_path).resolve()),"sha256":sha(import_job_path)},"importReceipt":{"path":str(Path(import_receipt_path).resolve()),"sha256":sha(import_receipt_path)},"solvedIdentityReceipt":{"path":str(Path(solved_receipt_path).resolve()),"sha256":sha(solved_receipt_path)},"identityAsset":identity,"characterAsset":{"path":character_asset_path,"expectedClass":config["characterAssetClass"]},"params":{"useEyeMeshes":True,"useTeethMesh":True,"useMetricScale":True},"operation":"MetaHumanCharacterEditorSubsystem.import_from_identity","requiredResult":"SUCCESS","onIdentityNotConformed":"fail","replaceExisting":False,"automaticApproval":False,"productionReady":False,"nextState":"conformed-head-awaiting-auto-rig-surface-groom-body-and-qa"}
def verify(job_path,receipt_path=None):
 j=load(job_path)
 if j.get("state")!="ready-to-conform-from-identity" or j.get("requiredResult")!="SUCCESS" or j.get("productionReady") is not False:raise ValueError("conform job overclaims state")
 for k in ("importJob","importReceipt","solvedIdentityReceipt"):
  r=j[k];p=Path(r["path"])
  if not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p)!=r["sha256"]:raise ValueError(f"conform lineage differs: {k}")
 if j.get("params")!={"useEyeMeshes":True,"useTeethMesh":True,"useMetricScale":True}:raise ValueError("conform identity preservation params differ")
 if receipt_path:
  r=load(receipt_path)
  if r.get("state")!="conformed-head-awaiting-production-systems" or r.get("job",{}).get("sha256")!=sha(job_path) or r.get("result")!="SUCCESS" or r.get("productionReady") is not False:raise ValueError("conform receipt differs or overclaims readiness")
 return {"valid":True,"state":j["state"],"requiredResult":"SUCCESS","productionReady":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=Path("character_pipeline/config/metahuman_identity_conform.json"));p.add_argument("--import-job",type=Path);p.add_argument("--import-receipt",type=Path);p.add_argument("--solved-receipt",type=Path);p.add_argument("--character-asset");p.add_argument("--output",type=Path,required=True);p.add_argument("--verify",action="store_true");p.add_argument("--receipt",type=Path);a=p.parse_args()
 if a.verify:r=verify(a.output.resolve(),a.receipt.resolve() if a.receipt else None)
 else:
  if not all((a.import_job,a.import_receipt,a.solved_receipt,a.character_asset)):p.error("all build inputs required")
  if a.output.exists():raise SystemExit(f"refusing to overwrite: {a.output}")
  r=build(load(a.config),a.import_job.resolve(),a.import_receipt.resolve(),a.solved_receipt.resolve(),a.character_asset);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps({"valid":True,"state":r["state"],"productionReady":False}));return 0
if __name__=="__main__":raise SystemExit(main())
