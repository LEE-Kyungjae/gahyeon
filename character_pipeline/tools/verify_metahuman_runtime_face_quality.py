#!/usr/bin/env python3
"""Bind actuation and geometric deformation evidence to one MetaHuman face asset."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from character_pipeline.evaluation.evaluate_deformation_diagnostics import evaluate_deformation_diagnostics
from character_pipeline.tools.verify_facial_actuation_evidence import validate as validate_actuation

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
 path=Path(path)
 if not path.is_file() or path.is_symlink(): raise ValueError(f"missing or unsafe evidence: {path}")
 return json.loads(path.read_text())
def verify(actuation_config_path,mapping_path,actuation_path,diagnostic_config_path,cases_path,diagnostics_path):
 ac,dc,cases=load(actuation_config_path),load(diagnostic_config_path),load(cases_path)
 mapping,actuation,diagnostics=load(mapping_path),load(actuation_path),load(diagnostics_path)
 actuation_result=validate_actuation(ac,Path(mapping_path).resolve(),Path(actuation_path).resolve())
 diagnostic_result=evaluate_deformation_diagnostics(dc,cases,diagnostics)
 face=actuation.get("faceAsset",{});diagnostic_face=diagnostics.get("faceAsset",{})
 if not face.get("path") or face.get("class")!="SkeletalMesh" or not face.get("packageGuid"):
  raise ValueError("actuation lacks exact MetaHuman face asset identity")
 if diagnostic_face!=face: raise ValueError("actuation and diagnostics use different face assets")
 if actuation.get("mappingEvidence",{}).get("sha256")!=sha(mapping_path): raise ValueError("mapping lineage differs")
 if diagnostics.get("actuationEvidence",{}).get("sha256")!=sha(actuation_path): raise ValueError("diagnostics are not bound to actuation evidence")
 display=diagnostics.get("displayProfile",{})
 if display!={"id":"looking-glass-go","resolution":[1440,2560],"viewCount":66}: raise ValueError("diagnostics are not bound to Looking Glass Go")
 if diagnostics.get("automaticApproval") is not False or diagnostics.get("qualityClaim") is not None: raise ValueError("runtime face evidence overclaims approval")
 return {"valid":True,"faceAsset":face,"actuationSamples":actuation_result["samples"],"deformationSamples":diagnostic_result["samples"],"diagnostics":diagnostic_result["diagnostics"],"runtimeFaceQualityVerified":True,"automaticApproval":False,"qualityClaim":None}
def main():
 p=argparse.ArgumentParser();p.add_argument("--actuation-config",type=Path,default=Path("character_pipeline/config/facial_actuation_qa.json"));p.add_argument("--mapping",type=Path,required=True);p.add_argument("--actuation",type=Path,required=True);p.add_argument("--diagnostic-config",type=Path,default=Path("character_pipeline/config/deformation_diagnostics.json"));p.add_argument("--cases",type=Path,default=Path("character_pipeline/config/deformation_qa.json"));p.add_argument("--diagnostics",type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.actuation_config,a.mapping,a.actuation,a.diagnostic_config,a.cases,a.diagnostics)));return 0
if __name__=="__main__":raise SystemExit(main())
