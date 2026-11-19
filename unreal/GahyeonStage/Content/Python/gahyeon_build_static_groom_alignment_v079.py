"""Build immutable v079 by aligning the rendered unbound Groom to the head."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v078/Preview/L_Skotukeda_GroomRecovery_v078"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v079/Preview/L_Skotukeda_StaticGroomAligned_v079"
OUTPUT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v079-static-groom-alignment/build-receipt.json")
DELTA_Z_CM = 40.0


if OUTPUT.exists() or unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError("refusing to overwrite immutable v079 output")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load v078 source map: {SOURCE_MAP}")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
character = next((a for a in actors if a.get_actor_label() == "Skotukeda_Medium_v027"), None)
hair = next((c for c in character.get_components_by_class(unreal.GroomComponent) if c.get_name() == "Hair"), None)
if hair is None or hair.get_editor_property("groom_asset") is None:
    raise RuntimeError("v078 rendered Groom component is unavailable")
before = hair.get_editor_property("relative_location")
after = unreal.Vector(before.x, before.y, before.z + DELTA_Z_CM)
hair.set_editor_property("relative_location", after)
if abs(hair.get_editor_property("relative_location").z - after.z) > 0.01:
    raise RuntimeError("Groom alignment did not persist in memory")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError(f"failed to save v079 map: {TARGET_MAP}")
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(json.dumps({
    "schemaVersion": 1, "iteration": "v079", "state": "draft-static-groom-alignment-built",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "hypothesis": "The unbound Groom renders around 40 cm below the head because legacy Groom reference coordinates are not converted by a binding asset.",
    "action": "Raise only the Hair Groom component by 40 cm in a disposable static desktop POC.",
    "expectedResult": "Strand hair surrounds the scalp and face instead of the neck; deformation remains unsupported.",
    "sourceMap": SOURCE_MAP, "targetMap": TARGET_MAP, "deltaZCm": DELTA_Z_CM,
    "before": [before.x, before.y, before.z], "after": [after.x, after.y, after.z],
    "bindingCompatible": False, "automaticApproval": False, "productionReady": False,
}, indent=2) + "\n", encoding="utf-8")
unreal.SystemLibrary.quit_editor()
