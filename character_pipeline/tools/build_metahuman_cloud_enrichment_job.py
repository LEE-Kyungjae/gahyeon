#!/usr/bin/env python3
"""Build a lineage-bound cloud rig and texture-source request after P31 conform."""
import argparse,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
 p=Path(p)
 if not p.is_file() or p.is_symlink():raise ValueError(f"missing or unsafe file: {p}")
 return json.loads(p.read_text())
def build(config,conform_job_path,conform_receipt_path):
 job,receipt=load(conform_job_path),load(conform_receipt_path)
 if config.get("engine")!="5.6" or config.get("rigType")!="JOINTS_AND_BLENDSHAPES" or config.get("blocking") is not True:return (_ for _ in ()).throw(ValueError("unsafe cloud enrichment config"))
 if receipt.get("state")!="conformed-head-awaiting-production-systems" or receipt.get("job",{}).get("sha256")!=sha(conform_job_path) or receipt.get("result")!="SUCCESS":raise ValueError("P31 conform receipt differs")
 if receipt.get("productionReady") is not False or receipt.get("faceRigGenerated") is not False or receipt.get("highResolutionTexturesDownloaded") is not False:raise ValueError("P31 receipt overclaims enrichment")
 character=receipt.get("characterAsset",{})
 if not str(character.get("path","")).startswith("/Game/"):raise ValueError("P31 Character asset path invalid")
 return {"schemaVersion":1,"state":"ready-for-blocking-cloud-enrichment","engine":"5.6","conformJob":{"path":str(Path(conform_job_path).resolve()),"sha256":sha(conform_job_path)},"conformReceipt":{"path":str(Path(conform_receipt_path).resolve()),"sha256":sha(conform_receipt_path)},"characterAsset":character,"requests":[{"operation":"request_auto_rigging","blocking":True,"reportProgress":False,"rigType":"JOINTS_AND_BLENDSHAPES"},{"operation":"request_texture_sources","blocking":True,"reportProgress":False}],"authentication":{"epicCloudAccessRequired":True,"mayPromptInEditor":True},"postRequestVerificationRequired":True,"automaticApproval":False,"productionReady":False,"nextState":"cloud-requests-completed-awaiting-rig-texture-asset-verification"}
def verify(job_path,receipt_path=None):
 j=load(job_path)
 if j.get("state")!="ready-for-blocking-cloud-enrichment" or j.get("productionReady") is not False:raise ValueError("cloud job overclaims state")
 for k in ("conformJob","conformReceipt"):
  r=j[k];p=Path(r["path"])
  if not p.is_absolute() or p.is_symlink() or not p.is_file() or sha(p)!=r["sha256"]:raise ValueError(f"cloud lineage differs: {k}")
 if j.get("requests",[])[0].get("rigType")!="JOINTS_AND_BLENDSHAPES" or not all(x.get("blocking") is True for x in j["requests"]):raise ValueError("cloud request policy differs")
 if receipt_path:
  r=load(receipt_path)
  if r.get("state")!="cloud-requests-completed-awaiting-asset-verification" or r.get("job",{}).get("sha256")!=sha(job_path) or r.get("requestsReturned")!=["auto-rig","texture-sources"] or r.get("productionReady") is not False:raise ValueError("cloud receipt differs or overclaims readiness")
  if any(r.get(x) is not False for x in ("faceRigVerified","blendshapesVerified","textureSourcesVerified")):raise ValueError("cloud receipt fabricates post-request verification")
 return {"valid":True,"state":j["state"],"rigType":"JOINTS_AND_BLENDSHAPES","productionReady":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=Path("character_pipeline/config/metahuman_cloud_enrichment.json"));p.add_argument("--conform-job",type=Path);p.add_argument("--conform-receipt",type=Path);p.add_argument("--output",type=Path,required=True);p.add_argument("--verify",action="store_true");p.add_argument("--receipt",type=Path);a=p.parse_args()
 if a.verify:r=verify(a.output.resolve(),a.receipt.resolve() if a.receipt else None)
 else:
  if not a.conform_job or not a.conform_receipt:p.error("conform job and receipt required")
  if a.output.exists():raise SystemExit(f"refusing to overwrite: {a.output}")
  r=build(load(a.config),a.conform_job.resolve(),a.conform_receipt.resolve());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+"\n")
 print(json.dumps({"valid":True,"state":r["state"],"productionReady":False}));return 0
if __name__=="__main__":raise SystemExit(main())
