"""Inspect UE's reflected payload for the immutable v693 Ururu morph targets."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
MESH = "/Game/LivingCharacterPOC/v693/Characters/UruruFacial/Ururu_StaticHeadMorphs_v691"
REPORT = ROOT / "artifacts/living-character-poc-v704-ururu-ue-morph-payload/report.json"


def inspect_ururu_ue_morph_payload_v704():
    if REPORT.exists():
        raise RuntimeError("refusing to overwrite immutable v704 report")
    mesh = unreal.load_asset(MESH)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError(f"missing v693 mesh: {MESH}")
    targets = list(mesh.get_editor_property("morph_targets"))
    payload = []
    for target in targets:
        item = {
            "name": target.get_name(),
            "path": target.get_path_name(),
            "reflectedMorphMethods": sorted(name for name in dir(target) if "data" in name.lower() or "delta" in name.lower() or "lod" in name.lower()),
        }
        for method_name, args in (
            ("has_valid_data", ()),
            ("has_data_for_lod", (0,)),
            ("get_num_deltas_for_lod", (0,)),
            ("get_resource_size_bytes", ()),
        ):
            method = getattr(target, method_name, None)
            if callable(method):
                try:
                    item[method_name] = method(*args)
                except Exception as exc:
                    item[method_name + "Error"] = repr(exc)
        payload.append(item)
    report = {
        "schemaVersion": 1,
        "iteration": "v704",
        "status": "inspected-ue-morph-payload",
        "mesh": MESH,
        "morphTargetNames": list(mesh.get_all_morph_target_names()),
        "morphTargets": payload,
        "automaticApproval": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("URURU_UE_MORPH_PAYLOAD_V704=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


inspect_ururu_ue_morph_payload_v704()
