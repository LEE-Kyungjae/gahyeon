"""Audit connected components and boundary loops of a MetaHuman Identity OBJ in Blender."""
import argparse,json,sys
from pathlib import Path
import bmesh,bpy
def args():
 p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);return p.parse_args(sys.argv[sys.argv.index("--")+1:])
def components(bm):
 remaining=set(bm.verts);result=[]
 while remaining:
  seed=remaining.pop();seen={seed};stack=[seed]
  while stack:
   v=stack.pop()
   for e in v.link_edges:
    n=e.other_vert(v)
    if n in remaining:remaining.remove(n);seen.add(n);stack.append(n)
  result.append(seen)
 return result
def loops(edges):
 remaining=set(edges);result=[]
 while remaining:
  seed=remaining.pop();seen={seed};stack=[seed]
  while stack:
   e=stack.pop()
   for v in e.verts:
    for n in v.link_edges:
     if n in remaining and len(n.link_faces)==1:remaining.remove(n);seen.add(n);stack.append(n)
  result.append(seen)
 return result
def main():
 a=args();bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.wm.obj_import(filepath=str(a.input.resolve()));meshes=[x for x in bpy.context.selected_objects if x.type=="MESH"]
 if not meshes:raise RuntimeError("OBJ import produced no mesh")
 records=[]
 for obj in meshes:
  bm=bmesh.new();bm.from_mesh(obj.data);bm.verts.ensure_lookup_table();boundary=[e for e in bm.edges if len(e.link_faces)==1];nonmanifold=[e for e in bm.edges if len(e.link_faces)!=2]
  comp=components(bm);boundary_loops=loops(boundary);record={"object":obj.name,"vertices":len(bm.verts),"polygons":len(bm.faces),"connectedComponents":len(comp),"componentVertexCounts":sorted((len(x) for x in comp),reverse=True),"boundaryEdges":len(boundary),"nonManifoldEdges":len(nonmanifold),"boundaryLoops":[]}
  for group in boundary_loops:
   verts={v for e in group for v in e.verts};coords=[obj.matrix_world@v.co for v in verts];record["boundaryLoops"].append({"edges":len(group),"vertices":len(verts),"zRange":[min(v.z for v in coords),max(v.z for v in coords)],"radialRange":[min((v.x*v.x+v.y*v.y)**.5 for v in coords),max((v.x*v.x+v.y*v.y)**.5 for v in coords)]})
  record["boundaryLoops"].sort(key=lambda x:x["edges"],reverse=True);records.append(record);bm.free()
 value={"schemaVersion":1,"claim":"topology-measurement-not-solve-approval","input":str(a.input.resolve()),"objects":records,"totals":{"objects":len(records),"vertices":sum(x["vertices"] for x in records),"polygons":sum(x["polygons"] for x in records),"connectedComponents":sum(x["connectedComponents"] for x in records),"boundaryEdges":sum(x["boundaryEdges"] for x in records),"nonManifoldEdges":sum(x["nonManifoldEdges"] for x in records),"boundaryLoops":sum(len(x["boundaryLoops"]) for x in records)}}
 if a.output.exists():raise RuntimeError(f"refusing to overwrite topology audit: {a.output}")
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(value,indent=2)+"\n");print(json.dumps(value));return 0
if __name__=="__main__":raise SystemExit(main())
