"""Prepare a non-destructive review scene from a P28 work order; never exports."""

from __future__ import annotations

import argparse, hashlib, json, sys
from pathlib import Path
import bpy
from mathutils import Vector

VIEWS={"face-front":(0,-1,0),"face-left-45":(-1,-1,0),"face-right-45":(1,-1,0),"face-left-profile":(-1,0,0),"face-right-profile":(1,0,0)}


def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def args():
    values=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    p=argparse.ArgumentParser(); p.add_argument("--handoff",type=Path,required=True); p.add_argument("--output",type=Path,required=True); p.add_argument("--report",type=Path,required=True); return p.parse_args(values)


def bounds(objects):
    pts=[o.matrix_world@Vector(c) for o in objects for c in o.bound_box]
    return Vector(tuple(min(p[i] for p in pts) for i in range(3))),Vector(tuple(max(p[i] for p in pts) for i in range(3)))


def main():
    a=args(); handoff=a.handoff.resolve(); output=a.output.resolve(); report_path=a.report.resolve()
    for p in (output,report_path):
        if p.exists(): raise SystemExit(f"refusing to overwrite: {p}")
        p.parent.mkdir(parents=True,exist_ok=True)
    h=json.loads(handoff.read_text()); source=Path(h["sourceShape"]["path"])
    if digest(source)!=h["sourceShape"]["sha256"]: raise SystemExit("P28 source shape checksum differs")
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    ext=source.suffix.lower()
    if ext==".obj": bpy.ops.wm.obj_import(filepath=str(source))
    elif ext in {".glb",".gltf"}: bpy.ops.import_scene.gltf(filepath=str(source))
    elif ext==".fbx": bpy.ops.import_scene.fbx(filepath=str(source))
    elif ext==".ply": bpy.ops.wm.ply_import(filepath=str(source))
    elif ext==".blend": bpy.ops.wm.open_mainfile(filepath=str(source))
    else: raise SystemExit(f"unsupported source format: {ext}")
    objects=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    if not objects: raise SystemExit("selected source has no mesh")
    lo,hi=bounds(objects); dims=hi-lo
    if min(dims)<=1e-6: raise SystemExit("selected source has degenerate bounds")
    scene=bpy.context.scene; scene["gahyeon_p28_handoff_sha256"]=digest(handoff); scene["gahyeon_source_shape_sha256"]=digest(source)
    scene["gahyeon_scope_state"]="review-required"; scene["gahyeon_production_mesh_allowed"]=False
    scene.render.resolution_x=1440; scene.render.resolution_y=2560; scene.render.resolution_percentage=100
    center=(lo+hi)*0.5; face_z=hi.z-dims.z*0.095; target=Vector((center.x,center.y,face_z))
    cameras=[]
    for view,direction in VIEWS.items():
        data=bpy.data.cameras.new(f"P29_{view}"); camera=bpy.data.objects.new(f"P29_{view}",data); scene.collection.objects.link(camera)
        direction=Vector(direction).normalized(); camera.location=target+direction*320.0; camera.rotation_euler=(target-camera.location).to_track_quat("-Z","Y").to_euler()
        data.type="ORTHO"; data.ortho_scale=dims.z*0.27; camera["evidence_view"]=view; camera["qa_protocol"]="looking-glass-go-single-view-v1"; cameras.append(view)
    bpy.ops.wm.save_as_mainfile(filepath=str(output),check_existing=False)
    report={"schemaVersion":1,"claim":"review-required-head-scope-working-scene","handoff":{"path":str(handoff),"sha256":digest(handoff)},
      "source":{"path":str(source),"sha256":digest(source)},"bounds":{"minimum":list(lo),"maximum":list(hi),"dimensions":list(dims)},
      "objects":[{"name":o.name,"vertices":len(o.data.vertices),"polygons":len(o.data.polygons)} for o in objects],
      "reviewCameras":cameras,
      "requiredReview":"select only neutral head-neck-and-eyes objects; do not export before approval","productionMeshAllowed":False,
      "output":{"path":str(output),"bytes":output.stat().st_size,"sha256":digest(output)}}
    report_path.write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report))
    return 0


if __name__=="__main__": raise SystemExit(main())
