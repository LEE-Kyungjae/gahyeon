"""Render five fixed clay views of the Ururu v669 MetaHuman draft."""

from pathlib import Path


BASE_SCRIPT = Path(
    "/Users/ze/work/gahyeonbot/unreal/GahyeonStage/Content/Python/"
    "gahyeon_capture_v196_conformed_surface_v199.py"
)


def run_ururu_conformed_surface_qa_v670():
    source = BASE_SCRIPT.read_text(encoding="utf-8")
    invocation = "start_conformed_surface_capture_v199()"
    if not source.rstrip().endswith(invocation):
        raise RuntimeError("validated conformed-surface renderer entry point changed")
    namespace = {"__name__": "ururu_surface_qa_v670", "__file__": str(BASE_SCRIPT)}
    exec(compile(source.rsplit(invocation, 1)[0], str(BASE_SCRIPT), "exec"), namespace)
    namespace.update(
        {
            "ITERATION": "v670",
            "CHARACTER": (
                "/Game/LivingCharacterPOC/v669/Character/MHC_Ururu_Draft_v669"
            ),
            "SOURCE_CONFORM_RECEIPT": (
                "/Users/ze/work/gahyeonbot/artifacts/"
                "living-character-poc-v669-ururu-reference-metahuman-conform/"
                "conform-receipt.json"
            ),
            "MAP": (
                "/Game/LivingCharacterPOC/v670/Preview/"
                "L_UruruConformedSurfaceQA_v670"
            ),
            "OUTPUT": Path(
                "/Users/ze/work/gahyeonbot/artifacts/"
                "living-character-poc-v670-ururu-metahuman-surface-qa"
            ),
        }
    )
    namespace["_driver_v199"] = namespace["ConformedSurfaceCaptureDriverV199"]()


run_ururu_conformed_surface_qa_v670()
