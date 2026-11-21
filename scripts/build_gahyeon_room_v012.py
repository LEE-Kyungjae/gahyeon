"""Build the detailed room candidate using the canonical local Unreal project."""
import argparse
from pathlib import Path
import subprocess
import launch_canonical_macos_runtime as canonical
from generate_room_detail_textures import generate

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--validate', action='store_true')
args = parser.parse_args()
manifest = canonical.load_manifest()['macos']
project = canonical.ROOT / manifest['project']
if not args.validate:
    generate(canonical.ROOT / 'artifacts/looking-glass-room-v012/textures')
script = project.parent / 'Content/Python' / ('validate_gahyeon_room_v012.py' if args.validate else 'build_gahyeon_room_v012.py')
subprocess.run([
    str(Path(manifest['engineRoot']) / 'Engine/Binaries/Mac/UnrealEditor-Cmd'),
    str(project), '-run=pythonscript', '-script=' + str(script),
    '-unattended', '-nullrhi', '-nosplash', '-nosourcecontrol', '-nop4', '-stdout',
], check=True)
