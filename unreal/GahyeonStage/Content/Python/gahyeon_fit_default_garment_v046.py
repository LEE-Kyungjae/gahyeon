"""Reduce garment width/depth for the first fitted desktop silhouette test."""

import unreal


GARMENT_LABEL = "DefaultGarment_BodyShapeC_v045"
GARMENT_SCALE = unreal.Vector(0.82, 0.88, 1.0)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
garment = next(
    (actor for actor in actors.get_all_level_actors() if actor.get_actor_label() == GARMENT_LABEL),
    None,
)
if garment is None:
    raise RuntimeError(f"default garment is unavailable: {GARMENT_LABEL}")
garment.set_actor_scale3d(GARMENT_SCALE)
garment.set_actor_label("DefaultGarment_Fitted_v046")

if not unreal.EditorLevelLibrary.save_current_level():
    raise RuntimeError("failed to save v046 fitted garment POC")
unreal.log("Gahyeon v046 fitted garment saved: scale=(0.82,0.88,1.0)")
