"""Export the processed audio performance as a v088 Control Rig Level Sequence."""

import json
import os
import traceback
from pathlib import Path

import unreal


PERFORMANCE = "/Game/Gahyeon/TalkingPOC/v092/Performance/GahyeonTalkingPerformance_v092"
BLUEPRINT = (
    "/Game/Gahyeon/CharacterPipeline/v088/AssembledMedium/"
    "Skotukeda_WardrobeGroomQA_v088/BP_Skotukeda_WardrobeGroomQA_v088"
)
OUTPUT_PATH = "/Game/Gahyeon/TalkingPOC/v094/Sequence"
OUTPUT_NAME = "LS_GahyeonTalkingControlRig_v094"


def export_talking_sequence_v094():
    output_asset = f"{OUTPUT_PATH}/{OUTPUT_NAME}"
    if unreal.EditorAssetLibrary.does_asset_exist(output_asset):
        raise RuntimeError(f"refusing to overwrite v094 sequence: {output_asset}")
    performance = unreal.load_asset(PERFORMANCE)
    blueprint = unreal.load_asset(BLUEPRINT)
    if performance is None or blueprint is None:
        raise RuntimeError("v092 performance or v088 Blueprint is unavailable")
    settings = unreal.MetaHumanPerformanceExportLevelSequenceSettings()
    settings.show_export_dialog = False
    settings.package_path = OUTPUT_PATH
    settings.asset_name = OUTPUT_NAME
    settings.export_video_track = False
    settings.export_depth_track = False
    settings.export_audio_track = True
    settings.export_image_plane = False
    settings.export_identity = False
    settings.export_camera = True
    settings.apply_lens_distortion = False
    settings.export_depth_mesh = False
    settings.export_control_rig_track = True
    settings.export_transform_track = False
    settings.keep_frame_range = True
    settings.target_meta_human_class = blueprint
    settings.enable_meta_human_head_movement = True
    settings.export_range = unreal.PerformanceExportRange.WHOLE_SEQUENCE
    settings.curve_interpolation = unreal.RichCurveInterpMode.RCIM_CUBIC
    sequence = unreal.MetaHumanPerformanceExportUtils.export_level_sequence(performance, settings)
    if sequence is None:
        raise RuntimeError("Control Rig Level Sequence export returned no asset")
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, only_if_is_dirty=False):
        raise RuntimeError("failed to save v094 sequence")
    receipt = {
        "schemaVersion": 1,
        "iteration": "v094",
        "state": "control-rig-sequence-exported",
        "performance": PERFORMANCE,
        "characterBlueprint": BLUEPRINT,
        "levelSequence": output_asset,
        "videoTrack": False,
        "audioTrack": True,
        "controlRigTrack": True,
        "runtimePlaybackVerified": False,
        "humanApproved": False,
        "productionReady": False,
        "automaticApproval": False,
    }
    receipt_path = Path(os.environ["GAHYEON_V094_EXPORT_RECEIPT"])
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"Gahyeon talking Control Rig sequence v094 exported: {output_asset}")


try:
    export_talking_sequence_v094()
except Exception:
    unreal.log_error(traceback.format_exc())
    raise

