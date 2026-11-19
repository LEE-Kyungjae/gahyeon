#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
engine_root="${GAHYEON_UE_ROOT:-/Users/Shared/Epic Games/UE_5.8}"
evidence_root="${GAHYEON_DESKTOP_PACKAGE_ROOT:-$repo_root/artifacts/desktop-looking-glass-runtime-poc-v091/unreal-mac-package}"
project="$repo_root/unreal/GahyeonStage/GahyeonStage.uproject"
run_uat="$engine_root/Engine/Build/BatchFiles/RunUAT.sh"
archive="$evidence_root/package"
map="/Game/Gahyeon/DesktopRuntime/v091/L_GahyeonDesktopRuntime_v091"

[[ "$(uname -s)" == "Darwin" ]] || { echo "Mac package gate requires macOS" >&2; exit 2; }
[[ -x "$run_uat" ]] || { echo "missing UE 5.8 RunUAT.sh: $run_uat" >&2; exit 3; }
[[ -f "$project" ]] || { echo "missing project: $project" >&2; exit 4; }
[[ ! -e "$evidence_root" ]] || { echo "evidence directory already exists: $evidence_root" >&2; exit 5; }
mkdir -p "$evidence_root"

if [[ "${GAHYEON_PROMOTE_STAGED_ONLY:-0}" == "1" ]]; then
  printf '%s\n' "Promoting an existing UE 5.8 staged build; no build/cook was run." > "$evidence_root/package.log"
else
  "$run_uat" BuildCookRun \
    -project="$project" -noP4 -platform=Mac -clientconfig=Development \
    -build -cook -stage -pak -archive -map="$map" \
    -AdditionalCookerOptions="-NoAssetRegistryCache" \
    -archivedirectory="$archive" 2>&1 | tee "$evidence_root/package.log"
fi

# UE 5.8's Mac archive step copies the thin app from Binaries/Mac and omits the
# staged Contents/UE payload. Preserve that output for diagnosis, then promote
# the signed staged app that xcodebuild assembled and validated.
staged_app="$repo_root/unreal/GahyeonStage/Saved/StagedBuilds/Mac/GahyeonStage.app"
archived_app="$archive/Mac/GahyeonStage.app"
[[ -d "$staged_app/Contents/UE" ]] || { echo "staged app is missing Contents/UE: $staged_app" >&2; exit 6; }
[[ -f "$staged_app/Contents/UE/GahyeonStage/Binaries/Mac/libtbb.12.dylib" ]] || {
  echo "staged app is missing libtbb.12.dylib" >&2
  exit 7
}
if [[ -d "$archived_app" ]]; then
  mv "$archived_app" "$evidence_root/uat-thin-archive.app"
fi
mkdir -p "$(dirname "$archived_app")"
ditto "$staged_app" "$archived_app"
codesign --verify --deep --strict "$archived_app"

python3 - "$evidence_root" "$project" "$map" <<'PY'
import datetime, hashlib, json, pathlib, sys
root, project, map_path = pathlib.Path(sys.argv[1]).resolve(), pathlib.Path(sys.argv[2]).resolve(), sys.argv[3]
package = root / "package"
app = package / "Mac" / "GahyeonStage.app"
required = [
    app / "Contents" / "MacOS" / "GahyeonStage",
    app / "Contents" / "UE" / "GahyeonStage" / "Binaries" / "Mac" / "libtbb.12.dylib",
    app / "Contents" / "UE" / "GahyeonStage" / "Content" / "Paks" / "GahyeonStage-Mac.utoc",
    app / "Contents" / "UE" / "GahyeonStage" / "Content" / "Paks" / "GahyeonStage-Mac.ucas",
]
missing = [str(path) for path in required if not path.is_file()]
if missing:
    raise SystemExit("packaged app is incomplete: " + ", ".join(missing))
files = []
for path in sorted(item for item in package.rglob("*") if item.is_file() and not item.is_symlink()):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    files.append({"path": path.relative_to(package).as_posix(), "bytes": path.stat().st_size, "sha256": digest})
if not files:
    raise SystemExit("packaged output contains no regular files")
log = root / "package.log"
manifest = {
    "schemaVersion": 1, "status": "passed", "platform": "Mac", "engineVersion": "5.8",
    "configuration": "Development", "completedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "project": str(project), "map": map_path, "packagedBuild": True,
    "packageLogSha256": hashlib.sha256(log.read_bytes()).hexdigest(), "files": files,
}
(root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
print(f"Mac Unreal package inventory: {len(files)} files")
PY
