"""Create an immutable Gahyeon body derivative with coherent normals/tangents."""

import json
from pathlib import Path

import unreal


SOURCE = (
    "/Game/Gahyeon/CharacterPipeline/v244/AssembledMedium/"
    "Gahyeon_AnimationPOC_v244/Body/"
    "SKM_MHC_Skotukeda_SweaterJeansHightop_v243_BodyMesh"
)
DESTINATION = (
    "/Game/Gahyeon/CharacterPipeline/v310/Body/"
    "SKM_Gahyeon_Body_RecomputedNormals_v310"
)
REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v310-gahyeon-recomputed-body-build/report.json"
)


def build_gahyeon_recomputed_body_v310():
    if unreal.EditorAssetLibrary.does_asset_exist(DESTINATION):
        raise RuntimeError(f"refusing to overwrite immutable asset: {DESTINATION}")
    source = unreal.load_asset(SOURCE)
    if source is None:
        raise RuntimeError(f"missing source body: {SOURCE}")
    if not unreal.EditorAssetLibrary.duplicate_asset(SOURCE, DESTINATION):
        raise RuntimeError("failed to duplicate Gahyeon body")
    body = unreal.load_asset(DESTINATION)
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    lod_count = int(subsystem.get_lod_count(body))
    before = []
    after = []
    for lod_index in range(lod_count):
        settings = subsystem.get_lod_build_settings(body, lod_index)
        before.append(
            {
                "lod": lod_index,
                "recomputeNormals": settings.get_editor_property("recompute_normals"),
                "recomputeTangents": settings.get_editor_property("recompute_tangents"),
                "weightedNormals": settings.get_editor_property("compute_weighted_normals"),
                "mikkTSpace": settings.get_editor_property("use_mikk_t_space"),
            }
        )
        settings.set_editor_property("recompute_normals", True)
        settings.set_editor_property("recompute_tangents", True)
        settings.set_editor_property("compute_weighted_normals", True)
        settings.set_editor_property("use_mikk_t_space", True)
        subsystem.set_lod_build_settings(body, lod_index, settings)
        verified = subsystem.get_lod_build_settings(body, lod_index)
        after.append(
            {
                "lod": lod_index,
                "recomputeNormals": verified.get_editor_property("recompute_normals"),
                "recomputeTangents": verified.get_editor_property("recompute_tangents"),
                "weightedNormals": verified.get_editor_property("compute_weighted_normals"),
                "mikkTSpace": verified.get_editor_property("use_mikk_t_space"),
            }
        )
    if not all(
        row["recomputeNormals"] and row["recomputeTangents"] for row in after
    ):
        raise RuntimeError(f"normal/tangent settings did not persist: {after}")
    if not unreal.EditorAssetLibrary.save_loaded_asset(body, only_if_is_dirty=False):
        raise RuntimeError("failed to save recomputed body")
    report = {
        "schemaVersion": 1,
        "iteration": "v310",
        "status": "draft-recomputed-body-built",
        "source": SOURCE,
        "asset": DESTINATION,
        "lodCount": lod_count,
        "before": before,
        "after": after,
        "identityChanged": False,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_V310_BODY=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


build_gahyeon_recomputed_body_v310()
