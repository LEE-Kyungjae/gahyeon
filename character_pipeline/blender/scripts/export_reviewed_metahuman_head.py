"""Export only human-reviewed objects from a P29 working scene."""

from __future__ import annotations

import argparse, hashlib, json, sys
from pathlib import Path
import bpy


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse():
    v=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []; p=argparse.ArgumentParser()
    p.add_argument("--review",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--manifest",type=Path,required=True); return p.parse_args(v)


def main():
    a=parse(); review_path=a.review.resolve(); out=a.output.resolve(); manifest=a.manifest.resolve()
    for p in (out,manifest):
        if p.exists(): raise SystemExit(f"refusing to overwrite: {p}")
        p.parent.mkdir(parents=True,exist_ok=True)
    review=json.loads(review_path.read_text()); scene_record=review["workingScene"]
    if digest(bpy.data.filepath)!=scene_record["sha256"] or str(Path(bpy.data.filepath).resolve())!=str(Path(scene_record["path"]).resolve()):
        raise SystemExit("open working scene differs from approved review")
    selected=[]
    for name in review["selectedObjects"]:
        obj=bpy.data.objects.get(name)
        if obj is None or obj.type!="MESH": raise SystemExit(f"approved mesh object missing: {name}")
        selected.append(obj)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in selected: obj.select_set(True)
    bpy.context.view_layer.objects.active=max(selected,key=lambda o:len(o.data.vertices))
    ext=out.suffix.lower()
    if ext==".obj": bpy.ops.wm.obj_export(filepath=str(out),export_selected_objects=True,export_materials=True,forward_axis="X",up_axis="Z",apply_modifiers=True)
    elif ext==".fbx": bpy.ops.export_scene.fbx(filepath=str(out),use_selection=True,axis_forward="X",axis_up="Z",apply_unit_scale=True,bake_space_transform=True)
    else: raise SystemExit("MetaHuman reviewed export must be OBJ or FBX")
    if not out.is_file() or out.stat().st_size==0: raise SystemExit("export produced no mesh")
    value={"schemaVersion":1,"scope":"neutral-head-neck-and-eyes-only","claim":"metahuman-identity-static-input-not-production-topology",
      "review":{"path":str(review_path),"sha256":digest(review_path)},"workingScene":scene_record,"selectedObjects":review["selectedObjects"],
      "coordinateContract":{"unit":"centimeter","upAxis":"+Z","forwardAxis":"+X","handedness":"left"},
      "output":{"path":str(out),"format":ext[1:],"bytes":out.stat().st_size,"sha256":digest(out)},"productionMeshAllowed":False}
    manifest.write_text(json.dumps(value,indent=2)+"\n"); print(json.dumps(value)); return 0


if __name__=="__main__": raise SystemExit(main())
