"""Build the detailed room candidate using the canonical local Unreal project."""
import argparse
import os
from pathlib import Path
import subprocess
import launch_canonical_macos_runtime as canonical
from generate_room_detail_textures import generate

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--validate', action='store_true')
parser.add_argument('--iteration', choices=('v012', 'v013'), default='v013')
args = parser.parse_args()
os.environ['GAHYEON_ROOM_DETAIL_ITERATION'] = args.iteration
manifest = canonical.load_manifest()['macos']
project = canonical.ROOT / manifest['project']
if not args.validate:
    generate(canonical.ROOT / ('artifacts/looking-glass-room-' + args.iteration) / 'textures', fine_grain=args.iteration == 'v012')
script = project.parent / 'Content/Python' / ('validate_gahyeon_room_v012.py' if args.validate else 'build_gahyeon_room_v012.py')
subprocess.run([
    str(Path(manifest['engineRoot']) / 'Engine/Binaries/Mac/UnrealEditor-Cmd'),
    str(project), '-run=pythonscript', '-script=' + str(script),
    '-unattended', '-nullrhi', '-nosplash', '-nosourcecontrol', '-nop4', '-stdout',
], check=True)
