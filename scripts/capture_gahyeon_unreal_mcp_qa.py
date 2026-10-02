#!/usr/bin/env python3
"""Capture deterministic Gahyeon character QA views through Unreal MCP."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = "2025-03-26"
EDITOR_TOOLSET = "EditorToolset.EditorAppToolset"
ACTOR_TOOLSET = "editor_toolset.toolsets.actor.ActorTools"


class UnrealMcpClient:
    def __init__(self, endpoint: str, timeout: float = 120.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        self.session_id: str | None = None
        self.request_id = 0

    def _post(self, payload: dict[str, Any], include_session: bool = True) -> dict[str, Any]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if include_session and self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            if not self.session_id:
                self.session_id = response.headers.get("Mcp-Session-Id")
            body = response.read()
        return json.loads(body) if body else {}

    def initialize(self) -> None:
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "gahyeon-unreal-qa", "version": "1.0"},
                },
            },
            include_session=False,
        )
        self._raise_rpc_error(response)
        if not self.session_id:
            raise RuntimeError("Unreal MCP did not return an Mcp-Session-Id header")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})

    def call_tool(self, toolset: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        response = self._post(
            {
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "tools/call",
                "params": {
                    "name": "call_tool",
                    "arguments": {
                        "toolset_name": toolset,
                        "tool_name": tool,
                        "arguments": arguments,
                    },
                },
            }
        )
        self._raise_rpc_error(response)
        result = response.get("result", {})
        if result.get("isError"):
            message = "\n".join(
                str(item.get("text", "")) for item in result.get("content", [])
            )
            raise RuntimeError(f"Unreal MCP tool failed: {toolset}.{tool}: {message}")
        text_blocks = [
            item.get("text")
            for item in result.get("content", [])
            if item.get("type") == "text" and item.get("text")
        ]
        if not text_blocks:
            raise RuntimeError(f"Unreal MCP tool returned no JSON text: {toolset}.{tool}")
        return json.loads(text_blocks[0])

    def _next_id(self) -> int:
        self.request_id += 1
        return self.request_id

    @staticmethod
    def _raise_rpc_error(response: dict[str, Any]) -> None:
        if "error" in response:
            raise RuntimeError(f"Unreal MCP RPC error: {response['error']}")


def look_at_rotation(location: dict[str, float], target: dict[str, float]) -> dict[str, float]:
    dx = target["x"] - location["x"]
    dy = target["y"] - location["y"]
    dz = target["z"] - location["z"]
    horizontal = math.hypot(dx, dy)
    return {
        "pitch": math.degrees(math.atan2(dz, horizontal)),
        "yaw": math.degrees(math.atan2(dy, dx)),
        "roll": 0.0,
    }


def build_views(bounds: dict[str, Any]) -> list[dict[str, Any]]:
    minimum = bounds["min"]
    maximum = bounds["max"]
    center = {axis: (minimum[axis] + maximum[axis]) / 2.0 for axis in "xyz"}
    height = maximum["z"] - minimum["z"]
    full_distance = max(260.0, height * 1.48)
    face_target = {"x": center["x"], "y": center["y"], "z": minimum["z"] + height * 0.86}
    body_target = {"x": center["x"], "y": center["y"], "z": minimum["z"] + height * 0.52}
    diagonal = full_distance / math.sqrt(2.0)
    raw_views = [
        ("full_front", {"x": center["x"], "y": center["y"] + full_distance, "z": body_target["z"]}, body_target),
        ("full_rear", {"x": center["x"], "y": center["y"] - full_distance, "z": body_target["z"]}, body_target),
        ("profile_left", {"x": center["x"] - full_distance, "y": center["y"], "z": body_target["z"]}, body_target),
        ("profile_right", {"x": center["x"] + full_distance, "y": center["y"], "z": body_target["z"]}, body_target),
        ("three_quarter_left", {"x": center["x"] - diagonal, "y": center["y"] + diagonal, "z": body_target["z"]}, body_target),
        ("three_quarter_right", {"x": center["x"] + diagonal, "y": center["y"] + diagonal, "z": body_target["z"]}, body_target),
        ("face_front", {"x": face_target["x"], "y": face_target["y"] + max(48.0, height * 0.30), "z": face_target["z"]}, face_target),
    ]
    views = []
    for name, location, target in raw_views:
        views.append(
            {
                "name": name,
                "target": target,
                "transform": {
                    "location": location,
                    "rotation": look_at_rotation(location, target),
                    "scale": {"x": 1.0, "y": 1.0, "z": 1.0},
                },
            }
        )
    return views


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def capture_iteration(args: argparse.Namespace) -> dict[str, Any]:
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    client = UnrealMcpClient(args.endpoint, args.timeout)
    client.initialize()
    actor = {"refPath": args.actor}
    bounds = client.call_tool(ACTOR_TOOLSET, "get_actor_bounds", {"actor": actor})["returnValue"]
    if not bounds.get("isValid"):
        raise RuntimeError(f"Actor has invalid bounds: {args.actor}")

    annotations = {
        "gridSpacing": 0.0,
        "gridExtent": 0.0,
        "gridHeight": 0.0,
        "maxLabelDistance": 0.0,
        "classFilter": {"refPath": "/Script/Engine.Actor"},
        "maxLabels": 0,
    }
    client.call_tool(EDITOR_TOOLSET, "SelectActors", {"actors": []})
    records = []
    for view in build_views(bounds):
        capture = client.call_tool(
            EDITOR_TOOLSET,
            "CaptureViewport",
            {
                "captureTransform": view["transform"],
                "annotations": annotations,
                "bShowUI": False,
            },
        )["returnValue"]
        image = capture["image"]
        if image["mimeType"] != "image/png":
            raise RuntimeError(f"Unexpected image type for {view['name']}: {image['mimeType']}")
        destination = output_dir / f"{view['name']}.png"
        destination.write_bytes(base64.b64decode(image["data"], validate=True))
        records.append(
            {
                "view": view["name"],
                "file": destination.name,
                "sha256": sha256(destination),
                "bytes": destination.stat().st_size,
                "cameraLocation": capture["cameraLocation"],
                "cameraRotation": capture["cameraRotation"],
                "cameraFOV": capture["cameraFOV"],
                "target": view["target"],
            }
        )

    manifest = {
        "schemaVersion": 1,
        "status": "draft",
        "capturedAt": datetime.now(timezone.utc).isoformat(),
        "endpoint": args.endpoint,
        "actor": args.actor,
        "actorBounds": bounds,
        "hypothesis": args.hypothesis,
        "captures": records,
        "promotion": {"automated": False, "humanApprovalRequired": True},
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--actor", required=True, help="Unreal actor refPath")
    parser.add_argument("--output", required=True, type=Path, help="New iteration directory")
    parser.add_argument("--endpoint", default="http://127.0.0.1:8000/mcp")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument(
        "--hypothesis",
        default="Fixed cameras expose identity, proportion, lighting, and clothing defects reproducibly.",
    )
    return parser.parse_args()


def main() -> int:
    try:
        manifest = capture_iteration(parse_args())
    except Exception as error:  # fail closed at the CLI boundary
        print(json.dumps({"ready": False, "error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"ready": True, "captures": len(manifest["captures"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
