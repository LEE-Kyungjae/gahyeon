"""Apply a conservative garment scale that should retain body clearance."""

import unreal


GARMENT_LABEL = "DefaultGarment_BodyShapeC_v045"
GARMENT_SCALE = unreal.Vector(0.92, 0.94, 1.0)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
garment = next(
    (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == GARMENT_LABEL),
    None,
)
if garment is None:
    raise RuntimeError(f"default garment is unavailable: {GARMENT_LABEL}")
garment.set_actor_scale3d(GARMENT_SCALE)
garment.set_actor_label("DefaultGarment_SafeFitted_v047")

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v047 safe-fitted garment POC")
unreal.log("Gahyeon v047 fitted garment saved: scale=(0.92,0.94,1.0)")
