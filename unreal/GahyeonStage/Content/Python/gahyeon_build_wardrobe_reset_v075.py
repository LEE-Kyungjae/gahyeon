"""Create an immutable v075 diagnostic with baked basewear and rejected donor pieces hidden."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


SOURCE_MAP = "/Game/Gahyeon/CharacterPipeline/v055/Preview/L_Skotukeda_DonorOutfit_v055"
TARGET_MAP = "/Game/Gahyeon/CharacterPipeline/v075/Preview/L_Skotukeda_WardrobeReset_v075"
SKIN_MATERIAL = "/Game/Gahyeon/CharacterPipeline/v044/Materials/M_Body_SkinLit_v044"
BODY_SOURCE_MATERIAL = (
    "/Game/Gahyeon/CharacterPipeline/v035/Materials/"
    "M_Body_TexturedLit_v035.M_Body_TexturedLit_v035"
)
REJECTED_DONOR_LABELS = {"DonorOutfit_top_v055", "DonorOutfit_bottom_v055"}
INVENTORY = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v075-wardrobe-reset/layer-inventory.json"
)
RECEIPT = INVENTORY.with_name("wardrobe-reset-receipt.json")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


if not INVENTORY.is_file():
    raise RuntimeError(f"missing inspected layer inventory: {INVENTORY}")
if RECEIPT.exists():
    raise RuntimeError(f"refusing to overwrite immutable receipt: {RECEIPT}")
if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MAP):
    raise RuntimeError(f"refusing to overwrite immutable v075 map: {TARGET_MAP}")

skin = unreal.EditorAssetLibrary.load_asset(SKIN_MATERIAL)
if skin is None:
    raise RuntimeError(f"skin-only diagnostic material is unavailable: {SKIN_MATERIAL}")
world = unreal.EditorLoadingAndSavingUtils.load_map(SOURCE_MAP)
if world is None:
    raise RuntimeError(f"failed to load inspected v055 source map: {SOURCE_MAP}")

body_changes = []
donor_changes = []
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
for actor in actors:
    label = actor.get_actor_label()
    if label in REJECTED_DONOR_LABELS:
        mesh_components = actor.get_components_by_class(unreal.MeshComponent)
        if len(mesh_components) != 1:
            raise RuntimeError(f"expected one donor mesh component for {label}, got {len(mesh_components)}")
        component = mesh_components[0]
        component.set_editor_property("visible", False)
        component.set_editor_property("hidden_in_game", True)
        donor_changes.append(label)
        continue
    if label != "Skotukeda_Medium_v027":
        continue
    for component in actor.get_components_by_class(unreal.SkeletalMeshComponent):
        if component.get_name() != "Body":
            continue
        if component.get_num_materials() != 1:
            raise RuntimeError(f"expected one Body material slot, got {component.get_num_materials()}")
        previous = component.get_material(0)
        previous_path = previous.get_path_name() if previous is not None else None
        if previous_path != BODY_SOURCE_MATERIAL:
            raise RuntimeError(f"unexpected v055 Body material: {previous_path}")
        component.set_material(0, skin)
        body_changes.append({"component": component.get_name(), "from": previous_path, "to": SKIN_MATERIAL})

if len(body_changes) != 1:
    raise RuntimeError(f"expected exactly one Body material replacement, got {len(body_changes)}")
if set(donor_changes) != REJECTED_DONOR_LABELS:
    raise RuntimeError(f"failed to hide exact rejected donor pair: {donor_changes}")
if not unreal.EditorLoadingAndSavingUtils.save_map(world, TARGET_MAP):
    raise RuntimeError(f"failed to save immutable v075 map: {TARGET_MAP}")

receipt = {
    "schemaVersion": 1,
    "iteration": "v075",
    "state": "draft-diagnostic-wardrobe-reset",
    "observedAt": datetime.now(timezone.utc).isoformat(),
    "hypothesis": "The visible camisole and underwear are baked into the Body material while the displaced white pieces are rejected donor actors.",
    "action": "Replace only the Body material with the existing skin-only diagnostic material and hide exactly the two rejected donor mesh components.",
    "expectedResult": "No baked camisole, baked underwear, or displaced donor pieces remain visible in the v075 diagnostic map.",
    "sourceMap": SOURCE_MAP,
    "targetMap": TARGET_MAP,
    "inventory": {"path": str(INVENTORY), "sha256": sha256(INVENTORY)},
    "bodyChanges": body_changes,
    "hiddenDonorActors": sorted(donor_changes),
    "productionAsset": False,
    "diagnosticOnly": True,
    "automaticApproval": False,
    "productionReady": False,
}
RECEIPT.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
unreal.log(f"Gahyeon v075 wardrobe reset saved: {TARGET_MAP}")
unreal.SystemLibrary.quit_editor()
