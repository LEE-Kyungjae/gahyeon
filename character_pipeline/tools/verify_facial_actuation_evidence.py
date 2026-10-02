#!/usr/bin/env python3
"""Verify exact semantic actuation traces and immutable Looking Glass Go captures."""
import argparse,hashlib,json,math,struct
from pathlib import Path

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):
 path=Path(path)
 if not path.is_file() or path.is_symlink():raise ValueError(f"missing or unsafe file: {path}")
 return json.loads(path.read_text())
def png_size(path):
 data=Path(path).read_bytes()[:24]
 if len(data)!=24 or data[:8]!=b"\x89PNG\r\n\x1a\n" or data[12:16]!=b"IHDR":raise ValueError(f"not a PNG capture: {path}")
 return list(struct.unpack(">II",data[16:24]))
def validate(config,mapping_path,report_path,job_path=None):
 mapping,report=load(mapping_path),load(report_path);root=Path(report_path).resolve().parent
 if job_path is not None:
  job=load(job_path)
  if report.get("job",{}).get("sha256")!=sha(job_path) or job.get("mappingEvidence",{}).get("sha256")!=sha(mapping_path):raise ValueError("P36 capture job lineage differs")
  if job.get("expectedSamples")!=57 or job.get("displayProfile",{}).get("resolution")!=config["resolution"]:raise ValueError("P36 capture job contract differs")
 if report.get("mappingEvidence",{}).get("sha256")!=sha(mapping_path):raise ValueError("P34 mapping evidence lineage differs")
 if mapping.get("state")!="editor-facial-mapping-observed" or mapping.get("editorRuntimeVerified") is not True:raise ValueError("P34 mapping evidence is not Editor-observed")
 if report.get("state")!="candidate" or report.get("editorRuntimeVerified") is not True:raise ValueError("facial actuation evidence is not an Editor runtime candidate")
 if report.get("automaticApproval") is not False or report.get("deformationVerified") is not False or report.get("productionReady") is not False:raise ValueError("facial actuation evidence overclaims quality")
 display=report.get("displayProfile",{})
 if display.get("id")!="looking-glass-go" or display.get("resolution")!=config["resolution"] or display.get("viewCount")!=66:raise ValueError("actuation evidence is not bound to Looking Glass Go")
 bindings={}
 control_curves=set()
 all_curves=set()
 for item in mapping.get("bindings",[]):
  bindings.setdefault((item["group"],item["semantic"]),set()).add(item["curve"]);all_curves.add(item["curve"])
  if item.get("route")=="control-rig-curve":control_curves.add(item["curve"])
 expected={(case["id"],weight) for case in config["requiredCases"] for weight in config["sampleWeights"]}
 samples=report.get("samples",[]);actual={(x.get("case"),x.get("requestedWeight")) for x in samples}
 if len(actual)!=len(samples):raise ValueError("duplicate facial actuation sample")
 if actual!=expected:raise ValueError(f"facial actuation sample coverage mismatch: expected={len(expected)} actual={len(actual)}")
 cases={x["id"]:x for x in config["requiredCases"]};thresholds=config["thresholds"];failures=[];captures=set()
 for sample in samples:
  case=cases[sample["case"]];weight=sample["requestedWeight"];curves=sample.get("curveWeights",{})
  if set(curves)!=all_curves:raise ValueError(f"curve inventory mismatch: {sample['case']}:{weight}")
  consumption=sample.get("controlRigConsumption")
  if control_curves:
   if not isinstance(consumption,dict) or not isinstance(consumption.get("token"),int) or isinstance(consumption.get("token"),bool) or consumption["token"]<=0 or not isinstance(consumption.get("digest"),str) or len(consumption["digest"])!=32:raise ValueError("Control Rig consumption acknowledgement missing or malformed")
  elif consumption is not None:raise ValueError("morph-only sample fabricates Control Rig consumption")
  if any(not isinstance(v,(int,float)) or isinstance(v,bool) or not math.isfinite(v) or v<0 or v>1 for v in curves.values()):raise ValueError("curve weight is non-finite or outside 0..1")
  capture=sample.get("capture",{});relative=capture.get("path")
  if not isinstance(relative,str) or Path(relative).is_absolute() or ".." in Path(relative).parts:raise ValueError("capture path is unsafe")
  image=(root/relative).resolve()
  if not image.is_file() or image.is_symlink() or sha(image)!=capture.get("sha256") or png_size(image)!=config["resolution"]:raise ValueError("capture missing, changed or wrong resolution")
  if relative in captures:raise ValueError("capture reused across samples")
  captures.add(relative)
  trace=sample.get("trace",{});trace_relative=trace.get("path")
  if not isinstance(trace_relative,str) or Path(trace_relative).is_absolute() or ".." in Path(trace_relative).parts:raise ValueError("trace path is unsafe")
  trace_path=(root/trace_relative).resolve()
  if not trace_path.is_file() or trace_path.is_symlink() or sha(trace_path)!=trace.get("sha256"):raise ValueError("curve trace missing or changed")
  trace_value=load(trace_path)
  if trace_value.get("case")!=sample["case"] or trace_value.get("requestedWeight")!=weight or trace_value.get("curveWeights")!=curves:raise ValueError("curve trace disagrees with evidence sample")
  target=set() if case["group"]=="baseline" else bindings.get((case["group"],case["semantic"]),set())
  if case["group"]!="baseline" and not target:raise ValueError(f"case lacks P34 binding: {case['id']}")
  if weight==0.0 and max(curves.values(),default=0)>thresholds["maximumNeutralAbsoluteWeight"]:failures.append({"case":case["id"],"weight":weight,"defect":"neutral-leak"})
  if weight==0.5 and target and min(curves[x] for x in target)<thresholds["minimumHalfResponse"]:failures.append({"case":case["id"],"weight":weight,"defect":"weak-half-response"})
  if weight==1.0 and target:
   if min(curves[x] for x in target)<thresholds["minimumPeakResponse"]:failures.append({"case":case["id"],"weight":weight,"defect":"weak-peak-response"})
   if max((v for k,v in curves.items() if k not in target),default=0)>thresholds["maximumUnmappedPeakWeight"]:failures.append({"case":case["id"],"weight":weight,"defect":"curve-crosstalk"})
   opposite="blink-right" if case["id"]=="blink-left" else "blink-left" if case["id"]=="blink-right" else None
   if opposite:
    other=bindings[("direct",opposite)]
    if max(curves[x] for x in other)>thresholds["maximumOppositeBlinkWeight"]:failures.append({"case":case["id"],"weight":weight,"defect":"opposite-blink-leak"})
 declared=report.get("summary",{})
 if declared.get("sampleCount")!=len(samples):raise ValueError("declared actuation sample count disagrees with samples")
 if failures:raise ValueError(f"facial actuation thresholds exceeded: {len(failures)}")
 if declared.get("failureCount")!=0:raise ValueError("declared actuation failure count disagrees with passing samples")
 return {"valid":True,"cases":len(cases),"samples":len(samples),"captures":len(captures),"mappingActuationVerified":True,"deformationVerified":False,"productionReady":False,"displayProfile":"looking-glass-go"}
def main():
 p=argparse.ArgumentParser();p.add_argument("--config",type=Path,default=Path("character_pipeline/config/facial_actuation_qa.json"));p.add_argument("--mapping-evidence",type=Path,required=True);p.add_argument("--report",type=Path,required=True);p.add_argument("--job",type=Path);a=p.parse_args();print(json.dumps(validate(load(a.config),a.mapping_evidence.resolve(),a.report.resolve(),a.job.resolve() if a.job else None)));return 0
if __name__=="__main__":raise SystemExit(main())
