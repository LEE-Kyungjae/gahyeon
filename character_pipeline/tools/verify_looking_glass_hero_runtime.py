#!/usr/bin/env python3
"""Bind physical Looking Glass acceptance to the exact approved Hero package."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
 path=Path(path)
 if not path.is_file() or path.is_symlink():raise ValueError(f"missing or unsafe evidence: {path}")
 return json.loads(path.read_text())
def verify(acceptance_path,hero_receipt_path,binding_path):
 acceptance,hero,binding=load(acceptance_path),load(hero_receipt_path),load(binding_path)
 if acceptance.get("status")!="passed" or acceptance.get("latencyBoundary")!="physical-presentation-v1":raise ValueError("passed physical Looking Glass acceptance required")
 if acceptance.get("display",{}).get("model")!="Looking Glass Go" or acceptance.get("software",{}).get("unreal")!="5.6":raise ValueError("Looking Glass Go UE 5.6 acceptance required")
 modes={p.get("mode") for p in acceptance.get("profiles",[])}
 if modes!={"Realtime","RealtimeAdaptive","NonRealtime"}:raise ValueError("all Looking Glass modes required")
 if not any(p.get("mode") in {"Realtime","RealtimeAdaptive"} and p.get("views")==66 for p in acceptance["profiles"]):raise ValueError("passing 66-view realtime profile required")
 if hero.get("state")!="approved-hero-runtime-evidence" or hero.get("editorRuntimeVerified") is not True or hero.get("automaticApproval") is not False:raise ValueError("approved Editor Hero runtime evidence required")
 if hero.get("measurementRunId")!=acceptance.get("measurementRunId"):raise ValueError("Hero and acceptance belong to different runs")
 if hero.get("acceptanceSha256")!=sha(acceptance_path):raise ValueError("Hero runtime does not bind acceptance checksum")
 asset=hero.get("heroAsset",{})
 if not asset.get("path") or not asset.get("packageGuid") or asset.get("class")!="BlueprintGeneratedClass":raise ValueError("exact Hero Blueprint package identity missing")
 if binding.get("heroBlueprint")!=asset["path"] or binding.get("heroPackageGuid")!=asset["packageGuid"]:raise ValueError("runtime Hero differs from approved binding")
 systems=hero.get("productionSystems",{})
 required={"metaHumanFace","rigLogic","layeredSkin","physicalEyes","strandGroom","modularClothing","bodyRig","facialActuation"}
 if set(systems)!=required or not all(systems.values()):raise ValueError("runtime Hero production systems incomplete")
 return {"valid":True,"measurementRunId":acceptance["measurementRunId"],"heroAsset":asset,"viewCount":66,"physicalPresentationPassed":True,"automaticApproval":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--acceptance",type=Path,required=True);p.add_argument("--hero-receipt",type=Path,required=True);p.add_argument("--binding",type=Path,required=True);a=p.parse_args();print(json.dumps(verify(a.acceptance.resolve(),a.hero_receipt.resolve(),a.binding.resolve())));return 0
if __name__=="__main__":raise SystemExit(main())
