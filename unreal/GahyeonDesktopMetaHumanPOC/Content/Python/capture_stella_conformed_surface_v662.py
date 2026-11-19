"""Render five fixed clay views of the Stella/Lily v661 MetaHuman draft."""

from pathlib import Path


BASE_SCRIPT = Path(
    "/Users/ze/work/gahyeonbot/unreal/GahyeonStage/Content/Python/"
    "gahyeon_capture_v196_conformed_surface_v199.py"
)


def run_stella_conformed_surface_qa_v662():
    source = BASE_SCRIPT.read_text(encoding="utf-8")
    invocation = "start_conformed_surface_capture_v199()"
    if not source.rstrip().endswith(invocation):
        raise RuntimeError("validated conformed-surface renderer entry point changed")
    namespace = {"__name__": "stella_surface_qa_v662", "__file__": str(BASE_SCRIPT)}
    exec(compile(source.rsplit(invocation, 1)[0], str(BASE_SCRIPT), "exec"), namespace)
    namespace.update(
        {
            "ITERATION": "v662",
            "CHARACTER": (
                "/Game/LivingCharacterPOC/v661/Character/"
                "MHC_StellaLily_Draft_v661"
            ),
            "SOURCE_CONFORM_RECEIPT": (
                "/Users/ze/work/gahyeonbot/artifacts/"
                "living-character-poc-v661-stella-metahuman-conform/"
                "conform-receipt.json"
            ),
            "MAP": (
                "/Game/LivingCharacterPOC/v662/Preview/"
                "L_StellaConformedSurfaceQA_v662"
            ),
            "OUTPUT": Path(
                "/Users/ze/work/gahyeonbot/artifacts/"
                "living-character-poc-v662-stella-metahuman-surface-qa"
            ),
        }
    )
    namespace["_driver_v199"] = namespace["ConformedSurfaceCaptureDriverV199"]()


run_stella_conformed_surface_qa_v662()

