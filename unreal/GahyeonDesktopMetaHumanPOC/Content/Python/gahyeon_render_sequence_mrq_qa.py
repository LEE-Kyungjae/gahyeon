"""Deterministic Level Sequence QA rendering through UE's official MRQ PIE executor.

Required environment variables:
  GAHYEON_MRQ_ITERATION, GAHYEON_MRQ_SEQUENCE, GAHYEON_MRQ_MAP,
  GAHYEON_MRQ_OUTPUT

Optional:
  GAHYEON_MRQ_PASS=lit|unlit, GAHYEON_MRQ_EXPOSURE_OFFSET,
  GAHYEON_MRQ_RESOLUTION
"""

import hashlib
import json
import os
from pathlib import Path

import unreal


subsystem = None
executor = None
output_root = None
configuration = None


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"missing required environment variable: {name}")
    return value


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def on_finished(_executor, success):
    frames = sorted((output_root / "frames").glob("*.png"))
    report = {
        "schemaVersion": 1,
        "iteration": configuration["iteration"],
        "status": "captured-draft-mrq" if success and frames else "failed-mrq",
        "sequence": configuration["sequence"],
        "map": configuration["map"],
        "renderPass": configuration["renderPass"],
        "exposureOffset": configuration["exposureOffset"],
        "resolution": configuration["resolution"],
        "frameCount": len(frames),
        "uniqueFrameHashes": len({sha256(path) for path in frames}),
        "firstFrame": str(frames[0]) if frames else None,
        "lastFrame": str(frames[-1]) if frames else None,
        "visualValidationPending": True,
        "humanApproved": False,
        "productionReady": False,
        "automaticApproval": False,
    }
    (output_root / "render-report.json").write_text(json.dumps(report, indent=2) + "\n")
    unreal.log("GAHYEON_MRQ_FINISHED=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


def main():
    global subsystem, executor, output_root, configuration
    iteration = required("GAHYEON_MRQ_ITERATION")
    sequence_path = required("GAHYEON_MRQ_SEQUENCE")
    map_path = required("GAHYEON_MRQ_MAP")
    output_root = Path(required("GAHYEON_MRQ_OUTPUT")).resolve()
    render_pass_name = os.environ.get("GAHYEON_MRQ_PASS", "lit").strip().lower()
    exposure_offset = float(os.environ.get("GAHYEON_MRQ_EXPOSURE_OFFSET", "0"))
    resolution = int(os.environ.get("GAHYEON_MRQ_RESOLUTION", "1024"))
    if render_pass_name not in {"lit", "unlit"}:
        raise RuntimeError(f"unsupported render pass: {render_pass_name}")
    if resolution < 256 or resolution > 4096:
        raise RuntimeError(f"unsafe QA resolution: {resolution}")
    if output_root.exists():
        raise RuntimeError(f"refusing to overwrite immutable iteration: {output_root}")
    (output_root / "frames").mkdir(parents=True)
    if unreal.load_asset(sequence_path) is None or unreal.load_asset(map_path) is None:
        raise RuntimeError("sequence or map is missing")

    configuration = {
        "iteration": iteration,
        "sequence": sequence_path,
        "map": map_path,
        "renderPass": render_pass_name,
        "exposureOffset": exposure_offset,
        "resolution": [resolution, resolution],
    }
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    queue = subsystem.get_queue()
    queue.delete_all_jobs()
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.job_name = f"Gahyeon {iteration} MRQ QA"
    job.author = "Codex"
    job.sequence = unreal.SoftObjectPath(sequence_path)
    job.map = unreal.SoftObjectPath(map_path)
    config = job.get_configuration()
    output = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    output.output_directory = unreal.DirectoryPath(str(output_root / "frames"))
    output.output_resolution = unreal.IntPoint(resolution, resolution)
    output.file_name_format = f"{iteration}.{{frame_number}}"
    output.zero_pad_frame_numbers = 4
    output.flush_disk_writes_per_shot = True
    pass_class = (
        unreal.MoviePipelineDeferredPassBase
        if render_pass_name == "lit"
        else unreal.MoviePipelineDeferredPass_Unlit
    )
    render_pass = config.find_or_add_setting_by_class(pass_class)
    render_pass.disable_multisample_effects = True
    config.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    antialias = config.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    antialias.spatial_sample_count = 1
    antialias.temporal_sample_count = 1
    if exposure_offset:
        cvars = config.find_or_add_setting_by_class(unreal.MoviePipelineConsoleVariableSetting)
        if not cvars.add_or_update_console_variable("r.ExposureOffset", exposure_offset):
            raise RuntimeError("failed to set r.ExposureOffset")
    executor = unreal.MoviePipelinePIEExecutor(subsystem)
    executor.on_executor_finished_delegate.add_callable_unique(on_finished)
    unreal.log("GAHYEON_MRQ_START=" + json.dumps(configuration, sort_keys=True))
    subsystem.render_queue_with_executor_instance(executor)


main()
