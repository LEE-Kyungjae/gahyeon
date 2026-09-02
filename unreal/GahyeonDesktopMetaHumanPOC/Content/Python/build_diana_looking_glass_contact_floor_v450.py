"""Build an immutable Looking Glass floor candidate with explicit foot contact."""

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE_MAP = "/Game/Gahyeon/Character2/Diana/v449/Runtime/L_DianaLookingGlassFloor_v449"
OUTPUT_MAP = "/Game/Gahyeon/Character2/Diana/v450/Runtime/L_DianaLookingGlassContactFloor_v450"
REPORT = ROOT / "artifacts/gahyeon-ch/iterations/v450-diana-looking-glass-contact-floor/report.json"
FLOOR_RAISE_CM = 1.8


if unreal.EditorAssetLibrary.does_asset_exist(OUTPUT_MAP) or REPORT.exists():
    raise RuntimeError("refusing to overwrite immutable Diana v450 Looking Glass runtime")

unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
floors = [actor for actor in actors if actor.get_actor_label() == "FLOOR_Diana_LookingGlass_v449"]
characters = [actor for actor in actors if isinstance(actor, unreal.SkeletalMeshActor)]
if world is None or len(floors) != 1 or len(characters) != 1:
    raise RuntimeError("v449 Looking Glass composition changed unexpectedly")

floor = floors[0]
floor_location = floor.get_actor_location()
floor.set_actor_location(
    unreal.Vector(floor_location.x, floor_location.y, floor_location.z + FLOOR_RAISE_CM),
    False,
    False,
)
floor.set_actor_label("FLOOR_Diana_LookingGlassContact_v450")

shadow_components = []
for component in characters[0].get_components_by_class(unreal.SkeletalMeshComponent):
    component.set_editor_property("cast_shadow", True)
    try:
        component.set_editor_property("cast_contact_shadow", True)
    except Exception:
        pass
    shadow_components.append(component.get_name())

contact_lights = []
for actor in actors:
    component = actor.get_component_by_class(unreal.RectLightComponent)
    if component is None:
        continue
    component.set_editor_property("cast_shadows", True)
    try:
        component.set_editor_property("contact_shadow_length", 0.08)
    except Exception:
        pass
    contact_lights.append(actor.get_actor_label())

if not unreal.EditorLoadingAndSavingUtils.save_map(world, OUTPUT_MAP):
    raise RuntimeError("failed to save Diana v450 Looking Glass contact-floor map")

report = {
    "schemaVersion": 1,
    "iteration": "v450-diana-looking-glass-contact-floor",
    "status": "candidate",
    "sourceMap": SOURCE_MAP,
    "map": OUTPUT_MAP,
    "hypothesis": "the floating impression comes from missing sole intersection and tight contact shadows",
    "action": "raise the floor 1.8cm and enable skeletal/contact shadows on the character and rect lights",
    "expectedResult": "visible foot-floor contact without obvious shoe clipping",
    "actualResult": "structurally authored; physical-display review pending",
    "decision": "candidate; v449 and v398 retained as fallbacks",
    "floorRaiseCm": FLOOR_RAISE_CM,
    "shadowComponents": shadow_components,
    "contactLights": contact_lights,
}
REPORT.parent.mkdir(parents=True, exist_ok=False)
REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
unreal.log("DIANA_LOOKING_GLASS_CONTACT_FLOOR_V450=" + json.dumps(report, sort_keys=True))
unreal.SystemLibrary.quit_editor()
