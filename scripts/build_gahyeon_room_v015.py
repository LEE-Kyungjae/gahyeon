"""Build a background-parallax candidate in the canonical Unreal project."""
import argparse
from pathlib import Path
import subprocess
import launch_canonical_macos_runtime as canonical

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--validate', action='store_true')
args = parser.parse_args()
manifest = canonical.load_manifest()
assert manifest['status'] == 'ready'
macos = manifest['macos']
project = canonical.ROOT/macos['project']
script = project.parent/'Content/Python'/('validate_gahyeon_room_v015.py' if args.validate else 'build_gahyeon_room_v015.py')
subprocess.run([
    str(Path(macos['engineRoot'])/'Engine/Binaries/Mac/UnrealEditor-Cmd'), str(project),
    '-run=pythonscript', '-script='+str(script), '-unattended', '-nullrhi',
    '-nosplash', '-nosourcecontrol', '-nop4', '-stdout',
], check=True)
