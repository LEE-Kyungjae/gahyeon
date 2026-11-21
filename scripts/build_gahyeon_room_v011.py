"""Build or validate the shallow-depth Looking Glass room in a commandlet."""
import argparse
from pathlib import Path
import subprocess
import launch_canonical_macos_runtime as canonical

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--validate', action='store_true')
args = parser.parse_args()
manifest = canonical.load_manifest()['macos']
project = canonical.ROOT / manifest['project']
script = project.parent / 'Content/Python' / (
    'validate_gahyeon_room_v011.py' if args.validate else 'build_gahyeon_room_v011.py')
subprocess.run([
    str(Path(manifest['engineRoot']) / 'Engine/Binaries/Mac/UnrealEditor-Cmd'),
    str(project), '-run=pythonscript', '-script=' + str(script),
    '-unattended', '-nullrhi', '-nosplash', '-nosourcecontrol', '-nop4', '-stdout',
], check=True)
