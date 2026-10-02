"""Inspect current Face mesh and UE 5.8 Groom binding APIs without mutation."""

import json
from pathlib import Path

import unreal


MAP = "/Game/Gahyeon/CharacterPipeline/v077/Preview/L_Skotukeda_HairCardAligned_v077"
OFFICIAL_BINDING = "/MetaHumanCharacter/Optional/Grooms/Bindings/Hair/Hair_L_StraightBangs_Binding"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v080-groom-binding/inspection.json")


def path(value):
    return value.get_path_name() if value is not None else None


if OUTPUT.exists():
    raise RuntimeError(f"refusing to overwrite v080 inspection: {OUTPUT}")
if unreal.EditorLoadingAndSavingUtils.load_map(MAP) is None:
    raise RuntimeError(f"failed to load source map: {MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((a for a in actors if a.get_actor_label() == "Skotukeda_Medium_v027"), None)
face = next((c for c in character.get_components_by_class(unreal.SkeletalMeshComponent) if c.get_name() == "Face"), None)
if face is None:
    raise RuntimeError("current Face component is unavailable")
face_mesh = face.get_editor_property("skeletal_mesh_asset")
binding = unreal.EditorAssetLibrary.load_asset(OFFICIAL_BINDING)
if binding is None:
    raise RuntimeError(f"official binding is unavailable: {OFFICIAL_BINDING}")

groom_types = {}
for name in dir(unreal):
    if "groom" not in name.lower():
        continue
    member = getattr(unreal, name)
    groom_types[name] = getattr(member, "__doc__", None)

record = {
    "schemaVersion": 1,
    "iteration": "v080",
    "state": "read-only-binding-api-inspection",
    "currentFaceMesh": path(face_mesh),
    "currentFaceSkeleton": path(face_mesh.get_editor_property("skeleton")) if face_mesh else None,
    "officialBinding": path(binding),
    "officialGroom": path(binding.get_editor_property("groom")),
    "officialSourceMesh": path(binding.get_editor_property("source_skeletal_mesh")),
    "officialTargetMesh": path(binding.get_editor_property("target_skeletal_mesh")),
    "officialMatchingSection": binding.get_editor_property("matching_section"),
    "officialInterpolationPoints": binding.get_editor_property("num_interpolation_points"),
    "availableGroomTypes": groom_types,
    "automaticApproval": False,
    "productionReady": False,
}
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
