"""Run v183's proven adaptive conform against the corrected v194 cm mesh."""

from pathlib import Path
import os

import unreal


BASE_SCRIPT = Path(__file__).with_name("gahyeon_keentools_metahuman_conform_v183.py")
CORRECTED_MESH = "/Game/Gahyeon/CharacterPipeline/v194/Input/SM_Gahyeon_KeenTools_Cm_v194"


def run_corrected_conform_v195():
    iteration = os.environ.get("GAHYEON_CORRECTED_ITERATION", "v195")
    source = BASE_SCRIPT.read_text(encoding="utf-8")
    invocation = "start_adaptive_custom_head_conform_v183()"
    if not source.rstrip().endswith(invocation):
        raise RuntimeError("v183 conform source entry point contract changed")
    namespace = {"__name__": "gahyeon_v183_reusable", "__file__": str(BASE_SCRIPT)}
    exec(compile(source.rsplit(invocation, 1)[0], str(BASE_SCRIPT), "exec"), namespace)
    namespace.update({
        "ITERATION": iteration,
        "OUTPUT": Path(
            "/Users/ze/work/gahyeonbot/artifacts/gahyeon-ch/iterations/"
            f"{iteration}-ue58-keentools-centimetre-conform"
        ),
        "ASSET_ROOT": f"/Game/Gahyeon/CharacterPipeline/{iteration}",
        "TARGET_MAP": (
            f"/Game/Gahyeon/CharacterPipeline/{iteration}/Preview/"
            f"L_KeenToolsConform_{iteration}"
        ),
        "TARGET_MESH": CORRECTED_MESH,
        "TARGET_CHARACTER": (
            f"/Game/Gahyeon/CharacterPipeline/{iteration}/Character/"
            f"MHC_Gahyeon_KeenTools_Cm_{iteration}"
        ),
    })
    base = namespace["AdaptiveCustomHeadConformDriverV183"]

    class CorrectedCentimetreConformDriverV195(base):
        def __init__(self):
            self.manifest = self._validate_input()
            output = namespace["OUTPUT"]
            if output.exists():
                raise RuntimeError(f"refusing to overwrite immutable output: {output}")
            for asset in (namespace["TARGET_MAP"], namespace["TARGET_CHARACTER"]):
                if unreal.EditorAssetLibrary.does_asset_exist(asset):
                    raise RuntimeError(f"refusing to overwrite immutable asset: {asset}")
            if not unreal.EditorAssetLibrary.does_asset_exist(CORRECTED_MESH):
                raise RuntimeError(f"validated v194 target missing: {CORRECTED_MESH}")
            output.mkdir(parents=True, exist_ok=False)
            self.capture_index = 0
            self.target_offset_z_cm = float(
                os.environ.get("GAHYEON_HEAD_TARGET_OFFSET_Z_CM", "0")
            )
            self.rotate_target_yaw_180 = (
                os.environ.get("GAHYEON_ROTATE_TARGET_YAW_180") == "1"
            )
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
            mesh = unreal.load_asset(CORRECTED_MESH)
            dimensions = mesh.get_bounds().box_extent * 2.0
            if not 35.0 <= max(dimensions.x, dimensions.y, dimensions.z) <= 45.0:
                raise RuntimeError(f"v194 centimetre contract regressed: {dimensions}")
            return mesh

    namespace["_driver_v183"] = CorrectedCentimetreConformDriverV195()


run_corrected_conform_v195()
