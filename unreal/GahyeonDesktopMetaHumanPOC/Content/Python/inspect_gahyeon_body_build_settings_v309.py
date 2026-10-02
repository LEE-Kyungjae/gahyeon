"""Inspect Gahyeon's v244 body SkeletalMesh LOD build settings without mutation."""

import json
from pathlib import Path

import unreal


BODY = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/"
    "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_BodyMesh"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v309-gahyeon-body-build-settings/report.json"
)


def inspect_gahyeon_body_build_settings_v309():
    mesh = unreal.load_asset(BODY)
    if mesh is None:
        raise RuntimeError(f"missing body mesh: {BODY}")
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    if subsystem is None:
        raise RuntimeError("SkeletalMeshEditorSubsystem unavailable")
    candidate_count_methods = [
        name for name in dir(subsystem) if "lod" in name.lower()
    ]
    mesh_lod_methods = [name for name in dir(mesh) if "lod" in name.lower()]
    if hasattr(subsystem, "get_lod_count"):
        lod_count = int(subsystem.get_lod_count(mesh))
    else:
        report = {
            "schemaVersion": 1,
            "iteration": "v309",
            "status": "inspection-api-discovery-required",
            "body": BODY,
            "subsystemLodMethods": candidate_count_methods,
            "meshLodMethods": mesh_lod_methods,
            "mutated": False,
            "humanApproved": False,
            "productionReady": False,
        }
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
        unreal.SystemLibrary.quit_editor()
        return
    lods = []
    for lod_index in range(lod_count):
        settings = subsystem.get_lod_build_settings(mesh, lod_index)
        properties = {}
        for name in (
            "recompute_normals",
            "recompute_tangents",
            "use_mikk_t_space",
            "compute_weighted_normals",
            "remove_degenerates",
            "use_full_precision_uvs",
            "use_high_precision_tangent_basis",
        ):
            try:
                properties[name] = settings.get_editor_property(name)
            except Exception as exc:
                properties[name] = {"unavailable": str(exc)}
        lods.append({"lod": lod_index, "buildSettings": properties})
    report = {
        "schemaVersion": 1,
        "iteration": "v309",
        "status": "inspection-complete",
        "body": BODY,
        "lodCount": lod_count,
        "lods": lods,
        "mutated": False,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, default=str) + "\n")
    unreal.log("GAHYEON_V309_BUILD_SETTINGS=" + json.dumps(report, default=str))
    unreal.SystemLibrary.quit_editor()


inspect_gahyeon_body_build_settings_v309()
