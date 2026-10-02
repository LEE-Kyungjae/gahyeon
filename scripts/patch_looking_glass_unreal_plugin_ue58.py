#!/usr/bin/env python3
"""Apply the minimal UE 5.8 source compatibility patch to Looking Glass 2.1.1."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PATCH_ID = "gahyeon-looking-glass-2.1.1-ue5.8-v1"


def _replace(path: Path, old: str, new: str) -> bool:
    text = path.read_text(encoding="utf-8-sig")
    if new in text:
        return False
    if old not in text:
        raise ValueError(f"unexpected Looking Glass source; refusing to patch {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def apply_patch(plugin: Path) -> dict:
    runtime = plugin / "Source/LookingGlassRuntime"
    changed: list[str] = []

    replacements = [
        (
            runtime / "Private/Render/LookingGlassRendering.cpp",
            '#include "CommonRenderResources.h"\n',
            '#include "CommonRenderResources.h"\n#include "RendererInterface.h"\n',
        ),
        (
            runtime / "Private/Render/LookingGlassViewportClient.cpp",
            '#include "ScreenRendering.h"\n',
            '#include "ScreenRendering.h"\n#include "RendererInterface.h"\n',
        ),
        (
            runtime / "Public/Game/LookingGlassSceneCaptureComponent2D.h",
            "\tvirtual void PostInterpChange(FProperty* PropertyThatChanged) override;\n",
            "#if ENGINE_MAJOR_VERSION < 5 || (ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION < 8)\n"
            "\tvirtual void PostInterpChange(FProperty* PropertyThatChanged) override;\n"
            "#endif\n",
        ),
        (
            runtime / "Private/Game/LookingGlassSceneCaptureComponent2D.cpp",
            "void ULookingGlassSceneCaptureComponent2D::PostInterpChange(FProperty* PropertyThatChanged)\n"
            "{\n",
            "#if ENGINE_MAJOR_VERSION < 5 || (ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION < 8)\n"
            "void ULookingGlassSceneCaptureComponent2D::PostInterpChange(FProperty* PropertyThatChanged)\n"
            "{\n",
        ),
        (
            runtime / "Private/Game/LookingGlassSceneCaptureComponent2D.cpp",
            "\t}\n}\n\n// This function is called when \"Size\" property is changed",
            "\t}\n}\n#endif\n\n// This function is called when \"Size\" property is changed",
        ),
        (
            runtime / "Public/Render/LookingGlassViewportClient.h",
            "\tvirtual bool InputTouch(FViewport* Viewport, const FInputDeviceId DeviceId, uint32 Handle, ETouchType::Type Type, const FVector2D& TouchLocation, float Force, uint32 TouchpadIndex, const uint64 Timestamp) override;\n",
            "#if ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 8\n"
            "\tvirtual bool InputTouch(FViewport* Viewport, const FTouchId TouchId, ETouchType::Type Type, const FVector2D& TouchLocation, float Force, const uint64 Timestamp) override;\n"
            "#else\n"
            "\tvirtual bool InputTouch(FViewport* Viewport, const FInputDeviceId DeviceId, uint32 Handle, ETouchType::Type Type, const FVector2D& TouchLocation, float Force, uint32 TouchpadIndex, const uint64 Timestamp) override;\n"
            "#endif\n",
        ),
        (
            runtime / "Private/Render/LookingGlassViewportClient.cpp",
            "bool FLookingGlassViewportClient::InputTouch(FViewport* InViewport, const FInputDeviceId DeviceId, uint32 Handle, ETouchType::Type Type, const FVector2D& TouchLocation, float Force, uint32 TouchpadIndex, const uint64 Timestamp)\n"
            "{\n",
            "#if ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 8\n"
            "bool FLookingGlassViewportClient::InputTouch(FViewport* InViewport, const FTouchId TouchId, ETouchType::Type Type, const FVector2D& TouchLocation, float Force, const uint64 Timestamp)\n"
            "{\n"
            "\tconst FInputDeviceId DeviceId = TouchId.GetDeviceId();\n"
            "#else\n"
            "bool FLookingGlassViewportClient::InputTouch(FViewport* InViewport, const FInputDeviceId DeviceId, uint32 Handle, ETouchType::Type Type, const FVector2D& TouchLocation, float Force, uint32 TouchpadIndex, const uint64 Timestamp)\n"
            "{\n"
            "#endif\n",
        ),
        (
            runtime / "Private/Render/LookingGlassViewportClient.cpp",
            "\t\tbResult = GEngine->GameViewport->ViewportConsole->InputTouch(DeviceId, Handle, Type, TouchLocation, Force, TouchpadIndex, Timestamp);\n",
            "#if ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 8\n"
            "\t\tbResult = GEngine->GameViewport->ViewportConsole->InputTouch(TouchId, Type, TouchLocation, Force, Timestamp);\n"
            "#else\n"
            "\t\tbResult = GEngine->GameViewport->ViewportConsole->InputTouch(DeviceId, Handle, Type, TouchLocation, Force, TouchpadIndex, Timestamp);\n"
            "#endif\n",
        ),
        (
            runtime / "Private/Render/LookingGlassViewportClient.cpp",
            "\t\t\tbResult = TargetPlayer->PlayerController->InputTouch(DeviceId, Handle, Type, TouchLocation, Force, TouchpadIndex, Timestamp);\n",
            "#if ENGINE_MAJOR_VERSION == 5 && ENGINE_MINOR_VERSION >= 8\n"
            "\t\t\tbResult = TargetPlayer->PlayerController->InputTouch(TouchId, Type, TouchLocation, Force, Timestamp);\n"
            "#else\n"
            "\t\t\tbResult = TargetPlayer->PlayerController->InputTouch(DeviceId, Handle, Type, TouchLocation, Force, TouchpadIndex, Timestamp);\n"
            "#endif\n",
        ),
    ]

    for path, old, new in replacements:
        if _replace(path, old, new):
            changed.append(path.relative_to(plugin).as_posix())

    marker = plugin / ".gahyeon-ue58-compat.json"
    patched_files = sorted({item[0] for item in replacements})
    payload = {
        "patchId": PATCH_ID,
        "files": {
            path.relative_to(plugin).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in patched_files
        },
    }
    marker.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return {"status": "patched" if changed else "already-patched", "patchId": PATCH_ID,
            "changed": sorted(set(changed)), "marker": str(marker)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("plugin", type=Path)
    args = parser.parse_args()
    print(json.dumps(apply_patch(args.plugin.resolve()), ensure_ascii=False))


if __name__ == "__main__":
    main()
