#!/usr/bin/env python3
"""Prepare or execute the immutable KeenTools Cloud v175 identity candidate.

Preparation is local-only.  Network execution is deliberately a separate,
explicit command because processing and model download consume Cloud credits.
The API key is read only from ``KEENTOOLS_API_KEY`` and is never persisted.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


WORKSPACE = Path("/Users/ze/work/gahyeonbot")
SOURCE_ROOT = WORKSPACE / "artifacts/gahyeon-ch"
OUTPUT_ROOT = SOURCE_ROOT / "iterations/v175-keentools-cloud-multiview"
ITERATION = "v175"
DEFAULT_API_BASE = "https://api.keentools.workers.dev"
INPUTS = (
    (3, "front", "ChatGPT Image 2026년 8월 10일 오후 10_57_38.png",
     "84855cabf133616975e5699217af54bc00e3804ecdfe5dfb1d22bd6887dfbc99"),
    (6, "three-quarter-left", "ChatGPT Image 2026년 8월 10일 오후 10_59_24.png",
     "ea2438b34cad90ef90fc51f76bbb0311e99a6c13c4533afd91b753815f82ed40"),
    (7, "left-profile", "ChatGPT Image 2026년 8월 10일 오후 11_01_23.png",
     "cf2a0755d0a3d179ce99a5e1124ca1e1de3b1f673eda7c8536eb1f31bb4269ac"),
    (8, "right-profile", "ChatGPT Image 2026년 8월 10일 오후 11_02_27.png",
     "9080943d8611a6efd6c8dcabcf6cb23775892c8c215030c61565882f6e9e3a2e"),
    (11, "three-quarter-right", "ChatGPT Image 2026년 8월 10일 오후 11_09_33.png",
     "4149a9bf35ea69f45161b17b88d1239202ce0f49d3311ef0fb3fc943e6aca50b"),
)


def sha256_v175(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json_v175(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def png_dimensions_v175(path: Path) -> list[int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise RuntimeError(f"expected PNG input: {path}")
    width, height = struct.unpack(">II", header[16:24])
    return [width, height]


def prepare_v175() -> dict[str, Any]:
    manifest_path = OUTPUT_ROOT / "input-manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        for record in payload["inputs"]:
            target = WORKSPACE / record["stagedPath"]
            if not target.is_file() or sha256_v175(target) != record["sha256"]:
                raise RuntimeError(f"sealed {ITERATION} input differs: {target}")
        return payload

    input_dir = OUTPUT_ROOT / "input"
    input_dir.mkdir(parents=True, exist_ok=False)
    records: list[dict[str, Any]] = []
    for sequence, (index, view, filename, expected_sha) in enumerate(INPUTS, start=1):
        source = SOURCE_ROOT / filename
        if not source.is_file() or sha256_v175(source) != expected_sha:
            raise RuntimeError(f"Golden Identity lineage differs: reference {index}")
        suffix = source.suffix.lower()
        staged = input_dir / f"{sequence:02d}-{view}{suffix}"
        shutil.copy2(source, staged)
        if sha256_v175(staged) != expected_sha:
            raise RuntimeError(f"staging checksum failed: {staged}")
        records.append({
            "sequence": sequence,
            "referenceIndex": index,
            "view": view,
            "sourcePath": str(source.relative_to(WORKSPACE)),
            "stagedPath": str(staged.relative_to(WORKSPACE)),
            "sha256": expected_sha,
            "contentType": "image/png",
            "dimensions": png_dimensions_v175(staged),
        })

    shapes = {tuple(record["dimensions"]) for record in records}
    if len(shapes) != 1:
        raise RuntimeError(
            f"estimate_common requires equal image shapes, found {sorted(shapes)}"
        )

    payload = {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "status": "prepared-not-submitted",
        "identityAuthority": "Gahyeon Golden Identity v173",
        "hypothesis": (
            "A true multi-view reconstruction with jointly estimated cameras will preserve "
            "Gahyeon's cross-view facial geometry better than FaceBuilder's unreviewed auto pins."
        ),
        "action": "Submit five sealed canonical neutral views to KeenTools Cloud reconstruction.",
        "expectedResult": (
            "A coherent neutral head sufficiently close to the canonical identity for bounded "
            "MetaHuman PCA refinement."
        ),
        "service": {
            "name": "KeenTools Cloud API",
            "apiBase": DEFAULT_API_BASE,
            "imageCount": len(INPUTS),
            "focalLengthMode": "estimate_common",
            "expressionsEnabled": False,
            "requestedOutput": {
                "meshFormat": "glb",
                "meshLod": "high_poly",
                "texture": "png",
                "blendshapes": [],
            },
            "creditBearing": True,
        },
        "inputs": records,
        "gates": {
            "automaticApproval": False,
            "mayConformToMetaHuman": False,
            "requiredBeforeConform": [
                "downloaded artifact checksum recorded",
                "front/three-quarter/profile fixed-camera renders produced",
                "side-by-side identity review against references 03/06/07/08",
                "geometry and visual identity gates pass",
            ],
        },
    }
    atomic_json_v175(manifest_path, payload)
    return payload


def request_json_v175(
    method: str,
    url: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "GahyeonCharacterFactory/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            content = response.read()
            return json.loads(content.decode("utf-8")) if content else {}
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:1000]
        raise RuntimeError(f"KeenTools HTTP {error.code}: {detail}") from error


def upload_v175(url: str, path: Path, content_type: str) -> None:
    request = urllib.request.Request(
        url,
        data=path.read_bytes(),
        method="PUT",
        headers={"Content-Type": content_type},
    )
    try:
        with urllib.request.urlopen(request, timeout=300) as response:
            if response.status // 100 != 2:
                raise RuntimeError(f"upload failed with HTTP {response.status}")
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"upload failed with HTTP {error.code}") from error


def execute_v175(api_base: str, poll_seconds: float) -> dict[str, Any]:
    manifest = prepare_v175()
    api_key = os.environ.get("KEENTOOLS_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("KEENTOOLS_API_KEY is required for credit-bearing execution")
    state_path = OUTPUT_ROOT / "cloud-state.json"
    if state_path.exists():
        raise RuntimeError("cloud-state.json already exists; refusing duplicate billed submission")

    base = api_base.rstrip("/")
    initialized = request_json_v175(
        "POST", f"{base}/v1/avatar/init", api_key,
        {"image_count": len(manifest["inputs"])},
    )
    avatar_id = initialized.get("avatar_id")
    upload_urls = initialized.get("img_urls")
    if not avatar_id or not isinstance(upload_urls, list) or len(upload_urls) != len(INPUTS):
        raise RuntimeError("KeenTools init response did not contain the expected upload slots")
    atomic_json_v175(state_path, {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "status": "initialized",
        "avatarId": avatar_id,
        "apiBase": base,
        "secretMaterialPersisted": False,
    })

    # The system Python on the UE workstation is 3.9.  The lengths were
    # validated immediately above, so using plain zip is safe and keeps the
    # credit-bearing runner compatible with that interpreter.
    for record, upload_url in zip(manifest["inputs"], upload_urls):
        upload_v175(upload_url, WORKSPACE / record["stagedPath"], record["contentType"])
    request_json_v175(
        "POST", f"{base}/v1/avatar/{urllib.parse.quote(avatar_id)}/process", api_key,
        {
            "focal_length_type": {"focal_length_type": "estimate_common"},
            "expressions_enabled": False,
        },
    )
    atomic_json_v175(state_path, {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "status": "processing",
        "avatarId": avatar_id,
        "apiBase": base,
        "secretMaterialPersisted": False,
    })

    status_url = f"{base}/v1/avatar/{urllib.parse.quote(avatar_id)}/get-status"
    while True:
        status = request_json_v175("GET", status_url, api_key)
        phase = str(status.get("status", "unknown"))
        atomic_json_v175(state_path, {
            "schemaVersion": 1,
            "iteration": ITERATION,
            "status": phase,
            "avatarId": avatar_id,
            "apiBase": base,
            "secretMaterialPersisted": False,
        })
        if phase == "completed":
            break
        if phase in {"failed", "error", "deleted"}:
            raise RuntimeError(f"KeenTools reconstruction ended as {phase}")
        time.sleep(poll_seconds)

    query = urllib.parse.urlencode({
        "mesh_format": "glb",
        "mesh_lod": "high_poly",
        "texture": "png",
    })
    model_url = f"{base}/v1/avatar/{urllib.parse.quote(avatar_id)}/get-3d-model?{query}"
    while True:
        result = request_json_v175("GET", model_url, api_key)
        if result.get("event") == "retry-after":
            time.sleep(max(float(result.get("data", {}).get("time_sec", poll_seconds)), 1.0))
            continue
        if result.get("event") != "redirect" or not result.get("data", {}).get("url"):
            raise RuntimeError("unexpected get-3d-model response")
        download_url = result["data"]["url"]
        break

    model_path = OUTPUT_ROOT / f"gahyeon-keentools-cloud-{ITERATION}.glb"
    if model_path.exists():
        raise RuntimeError(f"refusing to overwrite {model_path}")
    with urllib.request.urlopen(download_url, timeout=600) as response:
        downloaded = response.read()
    if downloaded.startswith(b"\x1f\x8b"):
        transport_path = model_path.with_suffix(model_path.suffix + ".gz")
        transport_path.write_bytes(downloaded)
        model_path.write_bytes(gzip.decompress(downloaded))
    else:
        model_path.write_bytes(downloaded)
    if model_path.read_bytes()[:4] != b"glTF":
        raise RuntimeError("downloaded payload is not a binary glTF after transport decoding")
    if model_path.stat().st_size < 1024:
        raise RuntimeError("downloaded GLB is implausibly small")
    final = {
        "schemaVersion": 1,
        "iteration": ITERATION,
        "status": "downloaded-awaiting-visual-qa",
        "avatarId": avatar_id,
        "model": {
            "path": str(model_path.relative_to(WORKSPACE)),
            "sha256": sha256_v175(model_path),
            "bytes": model_path.stat().st_size,
        },
        "automaticApproval": False,
        "mayConformToMetaHuman": False,
    }
    atomic_json_v175(state_path, final)
    return final


def main_v175(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare", help="stage and hash canonical inputs locally")
    execute = subparsers.add_parser("execute", help="submit the credit-bearing cloud job")
    execute.add_argument("--api-base", default=DEFAULT_API_BASE)
    execute.add_argument("--poll-seconds", type=float, default=5.0)
    args = parser.parse_args(argv)
    payload = prepare_v175() if args.command == "prepare" else execute_v175(
        args.api_base, args.poll_seconds,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main_v175())
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
