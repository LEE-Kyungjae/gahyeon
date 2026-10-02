"""Record the UE 5.8 Python surface that can refresh skeletal morph rendering."""

from __future__ import annotations

import json
from pathlib import Path

import unreal


REPORT = Path(
    "/Users/ze/work/gahyeonbot/artifacts/"
    "living-character-poc-v726-skeletal-refresh-api/report.json"
)


def inspect_skeletal_mesh_component_refresh_api_v726() -> None:
    component = unreal.SkeletalMeshComponent()
    tokens = ("tick", "refresh", "render", "morph", "animation", "bone", "update")
    exposed = sorted(
        name for name in dir(component)
        if any(token in name.lower() for token in tokens)
    )
    class_methods = sorted(
        name for name in dir(unreal.SkeletalMeshComponent)
        if any(token in name.lower() for token in tokens)
    )
    report = {
        "schemaVersion": 1,
        "iteration": "v726",
        "status": "inspection-only",
        "componentClass": component.get_class().get_path_name(),
        "instanceMethods": exposed,
        "classMethods": class_methods,
        "requiredCandidates": {
            name: hasattr(component, name)
            for name in (
                "tick_animation",
                "tick_component",
                "refresh_bone_transforms",
                "mark_render_dynamic_data_dirty",
                "mark_render_state_dirty",
                "recreate_render_state_concurrent",
                "force_update_transform",
            )
        },
    }
    REPORT.parent.mkdir(parents=True, exist_ok=False)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    unreal.log(f"V726_REPORT={REPORT}")
    unreal.SystemLibrary.quit_editor()


inspect_skeletal_mesh_component_refresh_api_v726()
