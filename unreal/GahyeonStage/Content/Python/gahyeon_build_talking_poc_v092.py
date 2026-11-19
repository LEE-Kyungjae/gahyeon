"""Build a non-destructive audio-driven MetaHuman talking POC for v088."""

import hashlib
import importlib.util
import json
import os
import sys
import traceback
from pathlib import Path

import unreal


ITERATION = "v092"
ASSET_ROOT = "/Game/Gahyeon/TalkingPOC/v092"
BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v088/AssembledMedium/"
    "Skotukeda_WardrobeGroomQA_v088/BP_Skotukeda_WardrobeGroomQA_v088"
)
DEFAULT_AUDIO = "artifacts/tts-noise-review-2026-08-16/candidate-C.wav"
FACE_SKELETON = "/Game/Gahyeon/CharacterPipeline/v088/CommonMedium/Face/Face_Archetype_Skeleton"


def _load_epic_module(module_name, script_path):
    spec = importlib.util.spec_from_file_location(module_name, str(script_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _asset_exists(path):
    return unreal.EditorAssetLibrary.does_asset_exist(path)


def _save(asset):
    if not unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False):
        raise RuntimeError(f"failed to save asset: {asset.get_path_name()}")


def _import_audio(source):
    destination = f"{ASSET_ROOT}/Audio"
    object_path = f"{destination}/GahyeonTalkingSource_v092"
    if _asset_exists(object_path):
        raise RuntimeError(f"refusing to overwrite existing audio asset: {object_path}")
    task = unreal.AssetImportTask()
    task.filename = str(source)
    task.destination_path = destination
    task.destination_name = "GahyeonTalkingSource_v092"
    task.automated = True
    task.replace_existing = False
    task.save = True
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    imported = list(task.imported_object_paths)
    if len(imported) != 1:
        raise RuntimeError(f"expected one imported audio asset, got {imported}")
    return imported[0].split(".", 1)[0]


def _export_face_animation(performance):
    settings = unreal.MetaHumanPerformanceExportAnimationSettings()
    settings.show_export_dialog = False
    settings.package_path = f"{ASSET_ROOT}/Animation"
    settings.asset_name = "AS_GahyeonTalkingFace_v092"
    target_skeleton = unreal.load_asset(FACE_SKELETON)
    if target_skeleton is None:
        raise RuntimeError(f"v088 face skeleton unavailable: {FACE_SKELETON}")
    settings.target_skeleton_or_skeletal_mesh = target_skeleton
    settings.enable_head_movement = True
    settings.export_range = unreal.PerformanceExportRange.PROCESSING_RANGE
    animation = unreal.MetaHumanPerformanceExportUtils.export_animation_sequence(performance, settings)
    if animation is None:
        raise RuntimeError("MetaHuman face AnimSequence export failed")
    _save(animation)
    return animation


def build_talking_poc_v092():
    project_dir = Path(unreal.Paths.project_dir()).resolve()
    repo = project_dir.parents[1]
    source = Path(os.environ.get("GAHYEON_TALKING_AUDIO", DEFAULT_AUDIO))
    if not source.is_absolute():
        source = repo / source
    source = source.resolve()
    if not source.is_file() or source.suffix.lower() != ".wav":
        raise RuntimeError(f"talking POC source must be an existing WAV: {source}")
    if unreal.load_asset(BLUEPRINT) is None:
        raise RuntimeError(f"v088 Blueprint unavailable: {BLUEPRINT}")

    performance_path = f"{ASSET_ROOT}/Performance/GahyeonTalkingPerformance_v092"
    animation_path = f"{ASSET_ROOT}/Animation/AS_GahyeonTalkingFace_v092"
    if _asset_exists(animation_path):
        raise RuntimeError(f"refusing to overwrite existing POC asset: {animation_path}")

    plugin_python = Path(unreal.Paths.engine_plugins_dir()) / "MetaHuman/MetaHumanAnimator/Content/Python"
    process_audio = _load_epic_module("gahyeon_epic_process_audio", plugin_python / "process_audio_performance.py")
    process_performance = _load_epic_module("process_performance", plugin_python / "process_performance.py")
    if _asset_exists(performance_path):
        performance = unreal.load_asset(performance_path)
        soundwave_path = f"{ASSET_ROOT}/Audio/GahyeonTalkingSource_v092"
        if performance is None or not _asset_exists(soundwave_path):
            raise RuntimeError("incomplete v092 resume assets")
    else:
        soundwave_path = _import_audio(source)
        performance = process_audio.create_performance_asset(
            soundwave_path,
            f"{ASSET_ROOT}/Performance",
            asset_name="GahyeonTalkingPerformance_v092",
            mood="Neutral",
            mood_intensity=0.0,
            process_mask="FullFace",
            head_movement_mode="ControlRig",
        )
        if performance is None:
            raise RuntimeError("MetaHuman Performance asset creation failed")
        process_performance.process_shot(performance)
        _save(performance)
    animation = _export_face_animation(performance)

    receipt = {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "status": "animation-assets-generated",
        "sourceAudio": str(source.relative_to(repo)),
        "sourceSha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "characterBlueprint": BLUEPRINT,
        "soundWave": soundwave_path,
        "performance": performance_path,
        "faceSkeleton": FACE_SKELETON,
        "faceAnimation": animation_path,
        "levelSequence": None,
        "solve": {"output": "FullFace", "mood": "Neutral", "headMovement": "ControlRig"},
        "visualPlaybackVerified": False,
        "productionReady": False,
        "automaticApproval": False,
    }
    output = repo / "artifacts/desktop-looking-glass-runtime-poc-v092/build-receipt.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon talking POC v092 built: {output}")
    return receipt


try:
    build_talking_poc_v092()
except Exception:
    unreal.log_error(traceback.format_exc())
    raise
