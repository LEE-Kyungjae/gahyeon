"""Render all v641 Stella/Ururu action sequences through one deterministic MRQ queue."""

import hashlib
import json
from pathlib import Path

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve().parents[1]
SOURCE = ROOT / "artifacts/living-character-poc-v641-desktop-action-sequences/report.json"
OUTPUT = ROOT / "artifacts/living-character-poc-v642-desktop-action-renders"
executor = None
subsystem = None
expected = []


def sha256_v642(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def configure_v642_job(queue, character_id, map_path, action):
    motion = action["motion"]
    action_root = OUTPUT / character_id / motion
    (action_root / "frames").mkdir(parents=True, exist_ok=False)
    job = queue.allocate_new_job(unreal.MoviePipelineExecutorJob)
    job.job_name = f"v642:{character_id}:{motion}"
    job.author = "Codex"
    job.sequence = unreal.SoftObjectPath(action["sequence"])
    job.map = unreal.SoftObjectPath(map_path)
    config = job.get_configuration()
    output = config.find_or_add_setting_by_class(unreal.MoviePipelineOutputSetting)
    output.output_directory = unreal.DirectoryPath(str(action_root / "frames"))
    output.output_resolution = unreal.IntPoint(512, 512)
    output.file_name_format = f"{motion}.{{frame_number}}"
    output.zero_pad_frame_numbers = 4
    output.flush_disk_writes_per_shot = True
    render_pass = config.find_or_add_setting_by_class(unreal.MoviePipelineDeferredPassBase)
    render_pass.disable_multisample_effects = True
    config.find_or_add_setting_by_class(unreal.MoviePipelineImageSequenceOutput_PNG)
    antialias = config.find_or_add_setting_by_class(unreal.MoviePipelineAntiAliasingSetting)
    antialias.spatial_sample_count = 1
    antialias.temporal_sample_count = 1
    expected.append(
        {
            "character": character_id,
            "motion": motion,
            "sequence": action["sequence"],
            "durationSeconds": action["durationSeconds"],
            "output": action_root,
        }
    )


def on_v642_finished(_executor, success):
    records = []
    failures = []
    for item in expected:
        frames = sorted((item["output"] / "frames").glob("*.png"))
        record = {
            "character": item["character"],
            "motion": item["motion"],
            "sequence": item["sequence"],
            "durationSeconds": item["durationSeconds"],
            "frameCount": len(frames),
            "uniqueFrameHashes": len({sha256_v642(path) for path in frames}),
            "firstFrame": str(frames[0].relative_to(ROOT)) if frames else None,
            "lastFrame": str(frames[-1].relative_to(ROOT)) if frames else None,
        }
        records.append(record)
        if not frames or record["uniqueFrameHashes"] < min(2, len(frames)):
            failures.append(record)
    report = {
        "schemaVersion": 1,
        "iteration": "v642",
        "status": "captured-draft-mrq" if success and not failures else "failed-mrq",
        "source": str(SOURCE.relative_to(ROOT)),
        "resolution": [512, 512],
        "jobCount": len(records),
        "totalFrameCount": sum(item["frameCount"] for item in records),
        "failures": failures,
        "renders": records,
        "visualValidationPending": True,
        "humanApproved": False,
        "releaseEligible": False,
    }
    (OUTPUT / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log("LIVING_CHARACTER_V642=" + json.dumps(report, sort_keys=True))
    unreal.SystemLibrary.quit_editor()


def render_desktop_actions_v642():
    global executor, subsystem
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable iteration: {OUTPUT}")
    if not SOURCE.exists():
        raise RuntimeError(f"missing v641 source report: {SOURCE}")
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    OUTPUT.mkdir(parents=True, exist_ok=False)
    subsystem = unreal.get_editor_subsystem(unreal.MoviePipelineQueueSubsystem)
    queue = subsystem.get_queue()
    queue.delete_all_jobs()
    for character_id, character in payload["characters"].items():
        for action in character["actions"]:
            configure_v642_job(queue, character_id, character["map"], action)
    if len(expected) != 14:
        raise RuntimeError(f"expected 14 action jobs, got {len(expected)}")
    executor = unreal.MoviePipelinePIEExecutor(subsystem)
    executor.on_executor_finished_delegate.add_callable_unique(on_v642_finished)
    subsystem.render_queue_with_executor_instance(executor)


render_desktop_actions_v642()
