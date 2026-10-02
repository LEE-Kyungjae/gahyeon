#!/usr/bin/env python3
"""Verify a real presentation profile covers assistant facial semantics without overclaiming."""
import argparse,hashlib,json,math
from pathlib import Path

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
    path=Path(path)
    if not path.is_file() or path.is_symlink(): raise ValueError(f"missing or unsafe file: {path}")
    return json.loads(path.read_text())

def validate(config,cloud_evidence_path,mapping_evidence_path):
    cloud,mapping=load(cloud_evidence_path),load(mapping_evidence_path)
    if mapping.get("cloudAssetEvidence",{}).get("sha256")!=sha(cloud_evidence_path):
        raise ValueError("P33 cloud asset evidence lineage differs")
    if mapping.get("state")!="editor-facial-mapping-observed" or mapping.get("engine")!="5.6" or mapping.get("editorRuntimeVerified") is not True:
        raise ValueError("facial mapping was not observed in UE 5.6 Editor")
    if mapping.get("automaticApproval") is not False or mapping.get("productionReady") is not False or mapping.get("deformationVerified") is not False:
        raise ValueError("facial mapping evidence overclaims approval, deformation or production readiness")
    display=mapping.get("displayProfile",{})
    expected=config["displayProfile"]
    if display.get("id")!=expected["id"] or display.get("resolution")!=expected["resolution"] or display.get("viewCount")!=expected["viewCount"]:
        raise ValueError("facial mapping evidence is not bound to Looking Glass Go")
    morphs=set(cloud.get("assets",{}).get("faceSkeletalMesh",{}).get("morphTargets",[]))
    if not morphs: raise ValueError("P33 morph inventory is empty")
    bindings=mapping.get("bindings",[])
    if not bindings: raise ValueError("facial mapping bindings are empty")
    by_group={"direct":{},"viseme":{},"emotion":{}}
    seen_pairs=set()
    for item in bindings:
        group=item.get("group");semantic=item.get("semantic");curve=item.get("curve");route=item.get("route");scale=item.get("scale")
        if group not in by_group or not isinstance(semantic,str) or not semantic or not isinstance(curve,str) or not curve:
            raise ValueError("facial mapping binding is malformed")
        if route not in config["allowedRoutes"] or not isinstance(scale,(int,float)) or isinstance(scale,bool) or not math.isfinite(scale) or scale<=0 or scale>config["maximumScale"]:
            raise ValueError("facial mapping route or scale is invalid")
        pair=(group,semantic,curve)
        if pair in seen_pairs: raise ValueError("duplicate semantic/curve binding")
        seen_pairs.add(pair);by_group[group].setdefault(semantic,[]).append(item)
        if route=="direct-morph" and curve not in morphs:
            raise ValueError(f"direct morph is absent from P33 inventory: {curve}")
        if route=="control-rig-curve" and item.get("animBridgeAcknowledged") is not True:
            raise ValueError(f"Control Rig curve lacks explicit Anim bridge evidence: {curve}")
    for semantic in config["requiredDirectSemantics"]:
        if semantic not in by_group["direct"]: raise ValueError(f"missing direct semantic: {semantic}")
    for semantic in config["requiredVisemes"]:
        if semantic not in by_group["viseme"]: raise ValueError(f"missing viseme: {semantic}")
    for semantic in config["requiredEmotions"]:
        if semantic not in by_group["emotion"]: raise ValueError(f"missing emotion: {semantic}")
    left={x["curve"] for x in by_group["direct"]["blink-left"]};right={x["curve"] for x in by_group["direct"]["blink-right"]}
    if left & right: raise ValueError("left and right blink must use distinct curves")
    checks=mapping.get("checks",{})
    for key in ("presentationProfileExists","profileValidationPassed","runtimeResolverPresent","animInstanceBridgePresent"):
        if checks.get(key) is not True: raise ValueError(f"Editor facial mapping check failed: {key}")
    return {"valid":True,"mappingCoverageVerified":True,"directSemantics":len(by_group["direct"]),"visemes":len(by_group["viseme"]),"emotions":len(by_group["emotion"]),"productionReady":False,"deformationVerified":False,"displayProfile":"looking-glass-go"}

def main():
    p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=Path("character_pipeline/config/facial_semantic_coverage.json"));p.add_argument("--cloud-evidence",type=Path,required=True);p.add_argument("--mapping-evidence",type=Path,required=True);a=p.parse_args()
    print(json.dumps(validate(load(a.config),a.cloud_evidence.resolve(),a.mapping_evidence.resolve())));return 0
if __name__=="__main__": raise SystemExit(main())
