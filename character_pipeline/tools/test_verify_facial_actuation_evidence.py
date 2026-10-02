import hashlib,json,struct,tempfile,unittest,zlib
from pathlib import Path
from character_pipeline.tools.verify_facial_actuation_evidence import validate
CONFIG=json.loads(Path("character_pipeline/config/facial_actuation_qa.json").read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def png(path,w=1440,h=2560):
 def chunk(kind,data):return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
 raw=b"".join(b"\0"+b"\0"*(w*3) for _ in range(h));path.write_bytes(b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw,9))+chunk(b"IEND",b""))
class T(unittest.TestCase):
 def fixture(self,root):
  bindings=[]
  for case in CONFIG["requiredCases"]:
   if case["group"]=="baseline":continue
   bindings.append({"group":case["group"],"semantic":case["semantic"],"curve":case["id"]+"-curve","route":"direct-morph","scale":1.0})
  mapping=root/"mapping.json";mapping.write_text(json.dumps({"state":"editor-facial-mapping-observed","editorRuntimeVerified":True,"bindings":bindings}))
  curves={x["curve"]:0.0 for x in bindings};samples=[]
  for case in CONFIG["requiredCases"]:
   target=None if case["group"]=="baseline" else case["id"]+"-curve"
   for weight in CONFIG["sampleWeights"]:
    values=dict(curves)
    if target:values[target]=weight
    name=f"{case['id']}-{str(weight).replace('.','_')}.png";image=root/name;png(image)
    trace_name=name.replace(".png",".json");trace=root/trace_name;trace.write_text(json.dumps({"case":case["id"],"requestedWeight":weight,"curveWeights":values}))
    samples.append({"case":case["id"],"requestedWeight":weight,"curveWeights":values,"capture":{"path":name,"sha256":sha(image)},"trace":{"path":trace_name,"sha256":sha(trace)}})
  report=root/"report.json";report.write_text(json.dumps({"state":"candidate","editorRuntimeVerified":True,"mappingEvidence":{"sha256":sha(mapping)},"displayProfile":{"id":"looking-glass-go","resolution":[1440,2560],"viewCount":66},"samples":samples,"summary":{"sampleCount":len(samples),"failureCount":0},"automaticApproval":False,"deformationVerified":False,"productionReady":False}));return mapping,report
 def test_valid_is_actuation_only(self):
  with tempfile.TemporaryDirectory() as d:
   v=validate(CONFIG,*self.fixture(Path(d)));self.assertEqual(v["samples"],57);self.assertFalse(v["deformationVerified"]);self.assertFalse(v["productionReady"])
 def mutate(self,fn,pattern,sync_traces=True):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);m,r=self.fixture(root);v=json.loads(r.read_text());fn(v)
   if sync_traces:
    for sample in v["samples"]:
     trace=root/sample["trace"]["path"]
     if trace.is_file():
      trace.write_text(json.dumps({"case":sample["case"],"requestedWeight":sample["requestedWeight"],"curveWeights":sample["curveWeights"]}));sample["trace"]["sha256"]=sha(trace)
   r.write_text(json.dumps(v))
   with self.assertRaisesRegex(ValueError,pattern):validate(CONFIG,m,r)
 def test_missing_sample(self):self.mutate(lambda v:v["samples"].pop(),"coverage")
 def test_duplicate_sample(self):self.mutate(lambda v:v["samples"].append(dict(v["samples"][0])),"duplicate")
 def test_weak_peak(self):self.mutate(lambda v:[x["curveWeights"].update({"viseme-aa-curve":0.4}) for x in v["samples"] if x["case"]=="viseme-aa" and x["requestedWeight"]==1.0],"thresholds")
 def test_crosstalk(self):self.mutate(lambda v:[x["curveWeights"].update({"viseme-ee-curve":0.7}) for x in v["samples"] if x["case"]=="viseme-aa" and x["requestedWeight"]==1.0],"thresholds")
 def test_opposite_blink(self):self.mutate(lambda v:[x["curveWeights"].update({"blink-right-curve":0.5}) for x in v["samples"] if x["case"]=="blink-left" and x["requestedWeight"]==1.0],"thresholds")
 def test_capture_checksum(self):self.mutate(lambda v:v["samples"][0]["capture"].update(sha256="0"*64),"capture")
 def test_trace_checksum(self):self.mutate(lambda v:v["samples"][0]["trace"].update(sha256="0"*64),"trace",False)
 def test_overclaim(self):self.mutate(lambda v:v.update(deformationVerified=True),"overclaims")
 def test_wrong_go_resolution(self):self.mutate(lambda v:v["displayProfile"].update(resolution=[1920,1080]),"Looking Glass Go")
 def test_morph_only_cannot_fabricate_control_rig_consumption(self):self.mutate(lambda v:v["samples"][0].update(controlRigConsumption={"token":1,"digest":"a"*32}),"fabricates")
if __name__=="__main__":unittest.main()
