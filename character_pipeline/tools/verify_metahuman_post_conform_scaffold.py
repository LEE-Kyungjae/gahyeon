#!/usr/bin/env python3
"""Static verifier for the editor collector and pending post-conform contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REQUIRED_PLUGINS = {
    "PythonScriptPlugin", "EditorScriptingUtilities", "MovieRenderPipeline",
    "ControlRig", "MetaHumanCreator", "MetaHumanAnimator",
    "MetaHumanAnimatorDepthProcessing", "RigLogic", "HairStrands",
}


def verify_metahuman_post_conform_scaffold(root: Path) -> dict:
    project = json.loads((root / "unreal/GahyeonStage/GahyeonStageCharacterQA.uproject").read_text())
    enabled = {item["Name"] for item in project.get("Plugins", []) if item.get("Enabled") is True}
    if project.get("EngineAssociation") != "5.6" or not REQUIRED_PLUGINS.issubset(enabled):
        raise ValueError("MetaHuman QA project is missing its UE 5.6 plugin contract")
    binding = json.loads((root / "character_pipeline/metahuman/conform/v001/candidate-binding.json").read_text())
    if binding.get("state") != "awaiting-identity-solve" or binding.get("claim") != "no-metahuman-candidate-yet":
        raise ValueError("pending binding must not claim a MetaHuman candidate")
    if any(value for value in binding.get("assets", {}).values()):
        raise ValueError("pending binding contains fabricated asset paths")
    contract = json.loads((root / "character_pipeline/metahuman/validation/v001/post-conform-contract.json").read_text())
    render = contract.get("renderEvidence", {})
    if contract.get("state") != "awaiting-editor-evidence":
        raise ValueError("post-conform contract must remain pending before Editor evidence")
    if render.get("profile") != "looking-glass-go" or render.get("resolution") != [1440, 2560]:
        raise ValueError("post-conform contract is not bound to Looking Glass Go")
    if len(render.get("views", [])) != 5 or len(set(render["views"])) != 5:
        raise ValueError("post-conform contract must require five unique views")
    source = (root / "unreal/GahyeonStage/Content/Python/gahyeon_collect_metahuman_evidence.py").read_text()
    for token in (
        "EditorAssetLibrary.does_asset_exist", "heroInheritsGahyeonCharacterPawn",
        '"dnaOrRigLogicBound": None', "refusing to overwrite immutable evidence",
        "readyForPostConformRender", "verify_input_handoff", "candidate input handoff checksum differs",
    ):
        if token not in source:
            raise ValueError(f"Editor collector is missing fail-closed token: {token}")
    importer = (root / "unreal/GahyeonStage/Content/Python/gahyeon_import_metahuman_identity_input.py").read_text()
    for token in (
        "AssetImportTask", "combine_meshes", 'replace_existing",False',
        "identity import source checksum differs", "imported-awaiting-identity-guided-workflow",
        "guided Components From Mesh, neutral tracking and Identity Solve remain required",
    ):
        if token not in importer:
            raise ValueError(f"Identity importer is missing fail-closed token: {token}")
    conformer = (root / "unreal/GahyeonStage/Content/Python/gahyeon_conform_metahuman_from_identity.py").read_text()
    for token in (
        "MetaHumanCharacterEditorSubsystem", "try_add_object_to_edit",
        "ImportFromIdentityParams", "use_eye_meshes=True", "use_teeth_mesh=True",
        "use_metric_scale=True", "import_from_identity", "ImportErrorCode.SUCCESS",
        "commit_face_state", "conformed-head-awaiting-production-systems",
        "auto-rig, surfaces, groom, body, deformation and Go QA remain required",
    ):
        if token not in conformer:
            raise ValueError(f"Identity conformer is missing fail-closed token: {token}")
    cloud = (root / "unreal/GahyeonStage/Content/Python/gahyeon_request_metahuman_rig_textures.py").read_text()
    for token in (
        "MetaHumanCharacterAutoRiggingRequestParams", "JOINTS_AND_BLENDSHAPES",
        "request_auto_rigging", "MetaHumanCharacterTextureRequestParams",
        "request_texture_sources", "blocking=True", "report_progress=False",
        "cloud-requests-completed-awaiting-asset-verification",
        '"faceRigVerified":False', '"blendshapesVerified":False',
        '"textureSourcesVerified":False',
    ):
        if token not in cloud:
            raise ValueError(f"MetaHuman cloud requester is missing fail-closed token: {token}")
    cloud_collector = (root / "unreal/GahyeonStage/Content/Python/gahyeon_collect_metahuman_cloud_assets.py").read_text()
    for token in (
        'get_editor_property("morph_targets")', "blueprint_get_size_x",
        "blueprint_get_size_y", "JOINTS_AND_BLENDSHAPES",
        "editor-cloud-assets-observed", '"automaticApproval":False',
        '"productionReady":False', "not final AAA surface, deformation or runtime approval",
    ):
        if token not in cloud_collector:
            raise ValueError(f"MetaHuman cloud asset collector is missing token: {token}")
    facial_collector = (root / "unreal/GahyeonStage/Content/Python/gahyeon_collect_facial_mapping_evidence.py").read_text()
    for token in (
        "presentation profile asset is required", "profile.validate()",
        '"control-rig-curve"', '"direct-morph"', "ResolveFacialCurveWeights",
        '"looking-glass-go"', '"resolution":[1440,2560]', '"viewCount":66',
        '"automaticApproval":False', '"deformationVerified":False',
        '"productionReady":False', "refusing to overwrite immutable facial mapping evidence",
    ):
        if token not in facial_collector:
            raise ValueError(f"facial mapping collector is missing token: {token}")
    return {"valid": True, "engine": "5.6", "plugins": len(REQUIRED_PLUGINS),
            "views": 5, "identityImporter": True, "identityConformer": True,
            "cloudRigTextureRequester": True, "cloudAssetCollector": True,
            "facialMappingCollector": True,
            "state": contract["state"]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    print(json.dumps(verify_metahuman_post_conform_scaffold(args.root.resolve())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
