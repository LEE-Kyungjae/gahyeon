#!/usr/bin/env python3
"""Build an immutable UE 5.6 facial actuation capture work order from P34 evidence."""
import argparse,hashlib,json
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text())
def build(config,mapping_path,output_root):
 mapping=load(mapping_path)
 if mapping.get("state")!="editor-facial-mapping-observed" or mapping.get("editorRuntimeVerified") is not True:raise ValueError("P34 Editor mapping evidence is required")
 if mapping.get("productionReady") is not False or mapping.get("deformationVerified") is not False:raise ValueError("P34 evidence overclaims quality")
 cases=[]
 for index,case in enumerate(config["requiredCases"]):
  samples=[]
  for offset,weight in enumerate(config["sampleWeights"]):
   stem=f"{index:02d}-{case['id']}-{int(weight*100):03d}"
   samples.append({"requestedWeight":weight,"frame":index*10+offset,"capture":f"captures/{stem}.png","trace":f"traces/{stem}.json"})
  cases.append({**case,"samples":samples})
 return {"schemaVersion":1,"state":"ready-for-ue56-editor-capture","engine":"5.6","mappingEvidence":{"path":str(Path(mapping_path).resolve()),"sha256":sha(mapping_path)},"displayProfile":{"id":"looking-glass-go","resolution":[1440,2560],"viewCount":66,"camera":config["camera"]},"sequence":{"path":"/Game/GahyeonGenerated/QA/LS_GahyeonFacialActuation_v001","moviePipelinePreset":"/Game/GahyeonGenerated/QA/MRQ_LookingGlassGo_Face_v001","neverOverwrite":True,"warmupFrames":32,"settleFrames":8},"outputRoot":str(Path(output_root).resolve()),"cases":cases,"expectedSamples":len(cases)*len(config["sampleWeights"]),"automaticApproval":False,"deformationVerified":False,"productionReady":False}
def main():
 p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=Path("character_pipeline/config/facial_actuation_qa.json"));p.add_argument("--mapping-evidence",type=Path,required=True);p.add_argument("--output-root",type=Path,required=True);p.add_argument("--output",type=Path,required=True);a=p.parse_args()
 if a.output.exists():raise ValueError(f"refusing to overwrite immutable capture job: {a.output}")
 value=build(load(a.config),a.mapping_evidence.resolve(),a.output_root.resolve());a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2)+"\n");print(json.dumps({"valid":True,"cases":len(value["cases"]),"samples":value["expectedSamples"],"output":str(a.output)}));return 0
if __name__=="__main__":raise SystemExit(main())
