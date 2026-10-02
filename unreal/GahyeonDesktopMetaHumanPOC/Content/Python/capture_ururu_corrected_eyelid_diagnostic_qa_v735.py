"""Diagnose corrected eyelid winding on the rejected v734 temporary skeleton."""

from __future__ import annotations

from pathlib import Path


SOURCE = Path(__file__).with_name("capture_ururu_ue_settled_face_morph_qa_v701.py")
OLD_MESH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
NEW_MESH = "/Game/LivingCharacterPOC/v734/Characters/UruruFacial/Ururu_HeadMorphs_CorrectedEyelids_v733"
OLD_SKELETON = "/Game/LivingCharacterPOC/v585/Characters/UruruCentimeterNormalized/Ururu_CentimeterNormalized_v584_Skeleton"
NEW_SKELETON = "/Game/LivingCharacterPOC/v734/Characters/UruruFacial/Ururu_HeadMorphs_CorrectedEyelids_v733_Skeleton"
OLD_MATERIAL_MAP = '''        donor_by_name = {
            str(slot.material_slot_name): slot.material_interface
            for slot in donor.get_editor_property("materials")
            if slot.material_interface is not None
        }
'''
COMPLETE_MATERIAL_MAP = '''        donor_by_name = {
            str(slot.material_slot_name): slot.material_interface
            for slot in donor.get_editor_property("materials")
            if slot.material_interface is not None
        }
        for material_path in (
            "/Game/LivingCharacterPOC/v734/Characters/UruruFacial/Ururu_EyelidSkin_v684",
            "/Game/LivingCharacterPOC/v734/Characters/UruruFacial/Ururu_BlinkLash_v684",
        ):
            material = unreal.load_asset(material_path)
            if not isinstance(material, unreal.MaterialInterface):
                raise RuntimeError(f"v735 eyelid material is unavailable: {material_path}")
            donor_by_name[material.get_name()] = material
'''
OLD_APPLY = '''        for name, value in values.items():
            self.component.set_morph_target(name, value, False)
'''
REFRESHED_APPLY = '''        for name, value in values.items():
            self.component.set_morph_target(name, value, False)
        message = unreal.GahyeonMetaHumanQALibrary.force_refresh_skeletal_morphs(self.component)
        if not isinstance(message, str) or "refreshed" not in message:
            raise RuntimeError(f"v735 skeletal morph refresh failed: {message!r}")
'''


def capture_ururu_corrected_eyelid_diagnostic_qa_v735() -> None:
    if not SOURCE.is_file():
        raise FileNotFoundError(SOURCE)
    source = SOURCE.read_text(encoding="utf-8")
    required = (OLD_MESH, OLD_SKELETON, OLD_MATERIAL_MAP, OLD_APPLY)
    if source.count("v701") < 10 or not all(value in source for value in required):
        raise RuntimeError("sealed v701 manual-morph protocol changed unexpectedly")
    source = source.replace(OLD_MESH, NEW_MESH)
    source = source.replace(OLD_SKELETON, NEW_SKELETON)
    source = source.replace(OLD_MATERIAL_MAP, COMPLETE_MATERIAL_MAP)
    source = source.replace(OLD_APPLY, REFRESHED_APPLY)
    source = source.replace("v701", "v735").replace("V701", "V735")
    exec(compile(source, str(SOURCE) + "::v735", "exec"), {"__name__": "__main__"})


capture_ururu_corrected_eyelid_diagnostic_qa_v735()
