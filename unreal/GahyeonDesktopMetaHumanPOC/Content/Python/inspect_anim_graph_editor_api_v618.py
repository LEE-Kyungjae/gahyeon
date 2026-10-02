"""Inspect editor subsystems that may author AnimGraph nodes in UE 5.8."""

import json
from pathlib import Path

import unreal


OUTPUT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v618-anim-graph-editor-api/report.json"
)
NAMES = (
    "GraphEditorSubsystem",
    "BlueprintEditorSubsystem",
    "AnimationBlueprintFactory",
    "AnimBlueprintFactory",
    "K2Node",
    "EdGraph",
    "EdGraphNode",
    "AnimGraphNode_Root",
    "AnimGraphNode_SequencePlayer",
    "AnimGraphNode_LocalToComponentSpace",
    "AnimGraphNode_ComponentToLocalSpace",
)


def inspect_anim_graph_editor_api_v618():
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to overwrite immutable output: {OUTPUT}")
    records = {}
    for name in NAMES:
        value = getattr(unreal, name, None)
        records[name] = {
            "available": value is not None,
            "methods": sorted(item for item in dir(value) if not item.startswith("_")) if value else [],
        }
    report = {
        "schemaVersion": 1,
        "iteration": "v618",
        "status": "read-only-anim-graph-editor-api-inspection",
        "classes": records,
        "humanApproved": False,
        "releaseEligible": False,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.SystemLibrary.quit_editor()


inspect_anim_graph_editor_api_v618()
