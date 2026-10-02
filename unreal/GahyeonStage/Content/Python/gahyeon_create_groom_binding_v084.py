"""Create v084 direct Face section-6 Groom binding and wait for editor ticks."""

import json
from datetime import datetime, timezone
from pathlib import Path

import unreal


GROOM_PATH = "/MetaHumanCharacter/Optional/Grooms/GroomAssets/Hair/Hair_L_StraightBangs/Hair_L_StraightBangs"
TARGET_PATH = "/Game/Gahyeon/CharacterPipeline/v027/AssembledMedium/Skotukeda_Medium_v027/Face/SKM_MHC_Skotukeda_Baseline_v026_FaceMesh"
BINDING_PATH = "/Game/Gahyeon/CharacterPipeline/v084/Groom/Hair_L_StraightBangs_Skotukeda_v084_Binding"
RECEIPT = Path("/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/v084-groom-binding/binding-receipt.json")
_driver = None


class BindingDriver:
    def __init__(self):
        if RECEIPT.exists() or unreal.EditorAssetLibrary.does_asset_exist(BINDING_PATH):
            raise RuntimeError("refusing to overwrite immutable v084 binding")
        groom = unreal.EditorAssetLibrary.load_asset(GROOM_PATH)
        target = unreal.EditorAssetLibrary.load_asset(TARGET_PATH)
        if groom is None or target is None:
            raise RuntimeError("v084 binding input unavailable")
        self.binding = unreal.GroomLibrary.create_new_groom_binding_asset_with_path(
            BINDING_PATH, groom, target, 100, None, 6
        )
        if self.binding is None:
            raise RuntimeError("GroomLibrary returned no v084 binding")
        self.remaining_ticks = 300
        self.handle = unreal.register_slate_post_tick_callback(self.tick)

    def tick(self, _delta):
        if self.remaining_ticks > 0:
            self.remaining_ticks -= 1
            return
        group_infos = self.binding.get_editor_property("group_infos")
        if not group_infos:
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
            raise RuntimeError("v084 section-6 direct binding produced no hair groups")
        if not unreal.EditorAssetLibrary.save_loaded_asset(self.binding, False):
            raise RuntimeError(f"failed to save compiled v084 binding: {BINDING_PATH}")
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        RECEIPT.write_text(json.dumps({
            "schemaVersion": 1, "iteration": "v084", "state": "draft-direct-binding-created",
            "observedAt": datetime.now(timezone.utc).isoformat(),
            "bindingAsset": self.binding.get_path_name(),
            "groomAsset": self.binding.get_editor_property("groom").get_path_name(),
            "targetSkeletalMesh": self.binding.get_editor_property("target_skeletal_mesh").get_path_name(),
            "sourceSkeletalMesh": None, "matchingSection": 6,
            "hairGroupCount": len(group_infos), "waitedEditorTicks": 300,
            "automaticApproval": False, "productionReady": False,
        }, indent=2) + "\n", encoding="utf-8")
        unreal.unregister_slate_post_tick_callback(self.handle)
        self.handle = None
        unreal.SystemLibrary.quit_editor()


def main():
    global _driver
    _driver = BindingDriver()


main()
