#!/usr/bin/env python3
"""Render fixed source/checker/alpha ROI strips for correction review."""

from __future__ import annotations

import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw


def build_roi_board(config, canonical_index, source_path, rgba_path, output_dir):
    rois=config["roiProfiles"].get(str(canonical_index),[])
    if not rois: raise ValueError("unknown ROI profile")
    output_dir.mkdir(parents=True,exist_ok=True)
    if any(output_dir.iterdir()): raise ValueError("ROI output directory must be empty")
    with Image.open(source_path) as source, Image.open(rgba_path) as rgba:
        source=source.convert("RGB"); rgba=rgba.convert("RGBA")
        if source.size!=rgba.size: raise ValueError("source and RGBA dimensions differ")
        outputs=[]
        for roi in rois:
            box=tuple(roi["box"]); src=source.crop(box); cut=rgba.crop(box); w,h=src.size
            checker=Image.new("RGB",(w,h),"white"); draw=ImageDraw.Draw(checker); tile=max(8,min(w,h)//12)
            for y in range(0,h,tile):
                for x in range(0,w,tile):
                    if (x//tile+y//tile)%2: draw.rectangle((x,y,x+tile-1,y+tile-1),fill=(145,145,145))
            checker.paste(cut,mask=cut.getchannel("A")); alpha=cut.getchannel("A").convert("RGB")
            target_h=420; scale=target_h/h; target_w=round(w*scale)
            panels=[im.resize((target_w,target_h),Image.Resampling.NEAREST if i==2 else Image.Resampling.LANCZOS) for i,im in enumerate((src,checker,alpha))]
            label=34; board=Image.new("RGB",(target_w*3,target_h+label),(20,20,20)); labels=("SOURCE","CHECKER","ALPHA")
            for i,(name,panel) in enumerate(zip(labels,panels)): board.paste(panel,(i*target_w,label)); ImageDraw.Draw(board).text((i*target_w+8,10),name,fill="white")
            path=output_dir/f"{roi['id']}.png"; board.save(path); outputs.append(str(path))
    return outputs


def main():
    p=argparse.ArgumentParser(); p.add_argument("--config",type=Path,default=Path("character_pipeline/config/matte_correction.json")); p.add_argument("--canonical-index",type=int,required=True); p.add_argument("--source",type=Path,required=True); p.add_argument("--rgba",type=Path,required=True); p.add_argument("--output-dir",type=Path,required=True); a=p.parse_args(); print(json.dumps(build_roi_board(json.loads(a.config.read_text()),a.canonical_index,a.source,a.rgba,a.output_dir))); return 0
if __name__=="__main__": raise SystemExit(main())
