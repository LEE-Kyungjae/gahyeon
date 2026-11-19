"""Render and score v217 tracker portraits without running MetaHuman conform."""

from pathlib import Path
import json
import os

import unreal


BASE_SCRIPT = Path(__file__).with_name("gahyeon_keentools_metahuman_conform_v183.py")
ITERATION = "v218"
OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
    "v218-keentools-tracker-portrait-qa"
)
TARGET_MESH = "/Game/Gahyeon/CharacterPipeline/v217/Input/SM_Gahyeon_KeenTools_SmoothHead_Cm_v217"


def run_tracker_portrait_qa_v218():
    source = BASE_SCRIPT.read_text(encoding="utf-8")
    invocation = "start_adaptive_custom_head_conform_v183()"
    if not source.rstrip().endswith(invocation):
        raise RuntimeError("v183 reusable driver contract changed")
    namespace = {"__name__": "gahyeon_v183_portrait_qa", "__file__": str(BASE_SCRIPT)}
    exec(compile(source.rsplit(invocation, 1)[0], str(BASE_SCRIPT), "exec"), namespace)
    namespace.update({
        "ITERATION": ITERATION,
        "OUTPUT": OUTPUT,
        "ASSET_ROOT": "/Game/Gahyeon/CharacterPipeline/v218",
        "TARGET_MAP": "/Game/Gahyeon/CharacterPipeline/v218/Preview/L_TrackerPortraitQA_v218",
        "TARGET_MESH": TARGET_MESH,
        "TARGET_CHARACTER": "/Game/Gahyeon/CharacterPipeline/v218/Unused/MHC_NotCreated_v218",
    })
    base = namespace["AdaptiveCustomHeadConformDriverV183"]

    class TrackerPortraitQADriverV218(base):
        def __init__(self):
            self.manifest = self._validate_input()
            if OUTPUT.exists():
                raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
            target_map = namespace["TARGET_MAP"]
            if unreal.EditorAssetLibrary.does_asset_exist(target_map):
                raise RuntimeError(f"refusing to overwrite immutable map: {target_map}")
            if not unreal.EditorAssetLibrary.does_asset_exist(TARGET_MESH):
                raise RuntimeError(f"validated v217 target missing: {TARGET_MESH}")
            OUTPUT.mkdir(parents=True, exist_ok=False)
            self.capture_index = 0
            self.target_offset_z_cm = 0.0
            self.rotate_target_yaw_180 = True
            self.capture_started = None
            self.warmup = 180
            self.portraits = []
            self.failure = None
            try:
                self._build_scene()
            except Exception as error:
                self._write_failure(error)
                raise
            unreal.EditorPythonScripting.set_keep_python_script_alive(True)
            self.handle = unreal.register_slate_post_tick_callback(self.tick)

        def _import_source(self):
            mesh = unreal.load_asset(TARGET_MESH)
            dimensions = mesh.get_bounds().box_extent * 2.0
            if not 35.0 <= max(dimensions.x, dimensions.y, dimensions.z) <= 45.0:
                raise RuntimeError(f"v217 centimetre contract regressed: {dimensions}")
            return mesh

        def _finish(self):
            self._shutdown()
            subsystem = unreal.get_editor_subsystem(unreal.MetaHumanCharacterEditorSubsystem)
            scored = self._track_portraits(subsystem)
            records = [
                {
                    "axis": axis,
                    "trackedCurveCount": count,
                    "path": str(path),
                    "sha256": namespace["sha256_v183"](path),
                }
                for count, axis, _camera, path, _image_size, _tracked in scored
            ]
            payload = {
                "schemaVersion": 1,
                "iteration": ITERATION,
                "state": "tracker-portraits-awaiting-visual-gate",
                "targetMesh": TARGET_MESH,
                "targetYawRotationDegrees": 180.0,
                "portraits": records,
                "bestAxis": records[0]["axis"],
                "bestTrackedCurveCount": records[0]["trackedCurveCount"],
                "conformExecuted": False,
                "identityApproved": False,
                "automaticApproval": False,
                "productionReady": False,
            }
            (OUTPUT / "report.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
            unreal.SystemLibrary.quit_editor()

    namespace["_driver_v183"] = TrackerPortraitQADriverV218()


run_tracker_portrait_qa_v218()
