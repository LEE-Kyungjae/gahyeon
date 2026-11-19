#!/usr/bin/env python3
"""Exercise installed roster selections and inspect the actual Unreal alpha frames."""
import argparse, ctypes, hashlib, json, mmap, os
from pathlib import Path
import struct, subprocess, time, zlib

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'artifacts/land-characters/roster-20261016'
LIB=ctypes.CDLL(None)


def frame():
    fd=LIB.shm_open(b'/gahyeon_rgba_v003',os.O_RDONLY,0)
    if fd<0: return None
    try:
        with mmap.mmap(fd,64+1600*1258*4*2,access=mmap.ACCESS_READ) as view:
            if len(view)<64:return None
            h=struct.unpack('<16I',view[:64])
            if h[0]!=0x47485247 or h[2:5]!=(1600,1258,6400) or h[5]>1 or h[6]<30:return None
            data=view[64+h[5]*h[4]*h[3]:64+(h[5]+1)*h[4]*h[3]]
            if struct.unpack('<16I',view[:64])[5:8]!=h[5:8]:return None
            if h[9]!=255 or h[12]<=h[10] or h[13]<=h[11]:return None
            opaque=colored=clear=0
            for p in range(0,len(data),64):
                b,g,r,a=data[p:p+4]
                if a==0:clear+=1
                if a>240:
                    opaque+=1
                    if max(r,g,b)-min(r,g,b)>25:colored+=1
            if opaque<100 or clear<100:return None
            return h,data,{'sequence':h[6],'alphaMin':h[8],'alphaMax':h[9],
                'bounds':list(h[10:14]),'sampledOpaquePixels':opaque,'sampledColoredPixels':colored,
                'sha256':hashlib.sha256(data).hexdigest()}
    except (OSError,ValueError):return None
    finally:os.close(fd)


def save_frame(path,h,bgra):
    rgba=bytearray(bgra)
    rgba[0::4]=bgra[2::4];rgba[2::4]=bgra[0::4]
    raw=b''.join(b'\0'+rgba[y*h[4]:(y+1)*h[4]] for y in range(h[3]))
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',h[2],h[3],8,6,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b''))


def main():
    p=argparse.ArgumentParser();p.add_argument('--models',nargs='+',default=['zeze','rogue','pirate','fighter','fighter-unmasked','child','hacker','gahyeon']);args=p.parse_args()
    results=[]
    for ident in args.models:
        subprocess.run(['python3',str(ROOT/'scripts/select_canonical_macos_character.py'),ident],check=True,cwd=ROOT)
        deadline=time.monotonic()+180;first=None
        while time.monotonic()<deadline:
            current=frame()
            if current:
                first=current;break
            time.sleep(0.25)
        if not first:raise RuntimeError('No visible frame: '+ident)
        time.sleep(1.2);second=None
        second_deadline=time.monotonic()+5
        while second is None and time.monotonic()<second_deadline:
            second=frame()
            if second is None:time.sleep(0.05)
        if not second:raise RuntimeError('No second stable frame: '+ident)
        if first[2]['sha256']==second[2]['sha256']:raise RuntimeError('Frozen frames: '+ident)
        if second[2]['sampledColoredPixels']==0:raise RuntimeError('Missing source colors: '+ident)
        h=second[0]
        if h[10]==0 or h[11]==0 or h[12]>=h[2]-1 or h[13]>=h[3]-1:raise RuntimeError('Clipped frame: '+ident)
        save_frame(OUT/(ident+'-mac-frame-a.png'),first[0],first[1])
        save_frame(OUT/(ident+'-mac-frame.png'),second[0],second[1])
        results.append({'id':ident,'first':first[2],'second':second[2],'humanVisualApproval':False})
        (OUT/'mac-runtime-verification.json').write_text(json.dumps(results,indent=2)+'\n')
        print('verified '+ident,flush=True)


if __name__=='__main__':main()
