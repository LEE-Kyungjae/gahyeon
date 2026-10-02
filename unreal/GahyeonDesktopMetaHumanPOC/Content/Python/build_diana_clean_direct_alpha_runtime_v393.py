"""Build an immutable Diana runtime map with scene backdrops removed for direct alpha."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v388/Runtime/L_DianaMacRuntimeIdle_v388"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v393/Runtime/L_DianaMacRuntimeIdleDirectAlpha_v393"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v393-diana-clean-direct-alpha-runtime/report.json"


def actor_uses_green_material(actor):
    for component in actor.get_components_by_class(unreal.MeshComponent):
        for material in component.get_materials():
            if material and "desktopgreenscreen" in material.get_path_name().lower():
                return True
    return False


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v393 runtime")

unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
if world is None:
    raise RuntimeError("failed to load the v388 source world")

removed_labels = []
for actor in list(actor_subsystem.get_all_level_actors()):
    label = actor.get_actor_label()
    if label.lower().startswith("backdrop_desktopgreen") or actor_uses_green_material(actor):
        removed_labels.append(label)
        if not actor_subsystem.destroy_actor(actor):
            raise RuntimeError("failed to remove green backdrop actor: " + label)

remaining = list(actor_subsystem.get_all_level_actors())
characters = [actor for actor in remaining if isinstance(actor, unreal.SkeletalMeshActor)]
cameras = [actor for actor in remaining if isinstance(actor, unreal.CineCameraActor)]
remaining_green = [actor.get_actor_label() for actor in remaining if actor_uses_green_material(actor)]
if len(characters) != 1 or len(cameras) != 1:
    raise RuntimeError(
        f"unexpected runtime composition: characters={len(characters)} cameras={len(cameras)}"
    )
if remaining_green:
    raise RuntimeError("green material actors remain: " + ", ".join(remaining_green))
if not removed_labels:
    raise RuntimeError("expected at least one contaminated green backdrop actor")

if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save clean v393 runtime map")

source_file = Path(unreal.Paths.convert_relative_path_to_full(
    unreal.Paths.project_content_dir() + "Gahyeon/Character2/Diana/v388/Runtime/L_DianaMacRuntimeIdle_v388.umap"
))
report = {
    "schemaVersion": 1,
    "iteration": "v393-diana-clean-direct-alpha-runtime",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "sourceSha256": hashlib.sha256(source_file.read_bytes()).hexdigest(),
    "map": OUTPUT_MAP,
    "hypothesis": "The visible green screen is scene geometry saved into v388, not a requirement of 3D alpha compositing.",
    "action": "Remove actors labeled as desktop-green backdrops or using DesktopGreenScreen materials, then save a new immutable map.",
    "expectedResult": "Only Diana renders with native propagated alpha; the desktop background remains transparent.",
    "actualResult": f"Removed {len(removed_labels)} green backdrop actor(s); retained one skeletal character and one cine camera.",
    "decision": "candidate pending fixed-window visual and alpha validation; v388 retained as fallback",
    "removedActors": removed_labels,
    "remainingGreenMaterialActors": remaining_green,
    "runtimeVisualValidationPending": True,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_CLEAN_DIRECT_ALPHA_RUNTIME_V393=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
