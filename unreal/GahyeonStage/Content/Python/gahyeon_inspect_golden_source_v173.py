"""Read-only forensic inspection of the imported Fab MetaHuman source."""

import hashlib
import json
from pathlib import Path

import unreal


SOURCE = "/Game/Fab/MetaHuman/Skotukeda"
SOURCE_FILE = Path(
    "/Users/ze/work/gahyeonbot/unreal/GahyeonStage/Content/Fab/MetaHuman/Skotukeda.uasset"
)
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/forensics/"
    "v173-golden-source/skotukeda-source-inspection.json"
)


def _path(value):
    return value.get_path_name() if value is not None else None


def inspect_golden_source_v173():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable v173 inspection: {OUTPUT}")
    if not SOURCE_FILE.is_file():
        raise RuntimeError(f"source package file is missing: {SOURCE_FILE}")
    character = unreal.load_asset(SOURCE)
    if character is None or character.get_class().get_name() != "MetaHumanCharacter":
        raise RuntimeError(f"source is not a MetaHumanCharacter: {SOURCE}")

    collection = character.internal_collection
    instance = collection.default_instance if collection is not None else None
    subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
    if not subsystem.try_add_object_to_edit(character):
        raise RuntimeError("could not open source MetaHuman for read-only inspection")
    try:
        coefficients = list(subsystem.get_face_model_coefficients(character))
        can_build = bool(subsystem.can_build_meta_human(character, False))
    finally:
        if subsystem.is_object_added_for_editing(character):
            subsystem.remove_object_to_edit(character)

    referencers = sorted(
        unreal.EditorAssetLibrary.find_package_referencers_for_asset(SOURCE, False)
    )
    payload = {
        "schemaVersion": 1,
        "iteration": "v173",
        "state": "read-only-source-inspected-awaiting-golden-selection",
        "engineVersion": unreal.SystemLibrary.get_engine_version(),
        "source": {
            "asset": SOURCE,
            "class": character.get_class().get_name(),
            "objectPath": character.get_path_name(),
            "packageFile": str(SOURCE_FILE),
            "sizeBytes": SOURCE_FILE.stat().st_size,
            "sha256": hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest(),
        },
        "internalCollection": {
            "path": _path(collection),
            "class": collection.get_class().get_name() if collection is not None else None,
            "defaultInstance": _path(instance),
            "defaultInstanceClass": instance.get_class().get_name() if instance is not None else None,
        },
        "faceModel": {
            "coefficientCount": len(coefficients),
            "coefficientSha256": hashlib.sha256(
                json.dumps(coefficients, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
            "coefficientsPersistedOrModified": False,
        },
        "canBuildWithoutHighResolutionTextures": can_build,
        "packageReferencers": referencers,
        "packageReferencerCount": len(referencers),
        "inspectionPolicy": {
            "assetSaved": False,
            "assetDuplicated": False,
            "conformCalled": False,
            "assemblyCalled": False,
            "automaticGoldenSelection": False,
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon v173 read-only source inspection written: {OUTPUT}")
    unreal.SystemLibrary.quit_editor()


inspect_golden_source_v173()
