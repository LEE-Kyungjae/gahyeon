#!/usr/bin/env python3
"""Generate a resumable, fixed-seed Gahyeon SDXL LoRA comparison on land."""

from __future__ import annotations

import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional


API = "http://127.0.0.1:8188"
OUTPUT_ROOT = Path("/opt/zaeze-ai/training/gahyeon-sdxl-v1/comparison")
COMFY_OUTPUT = Path("/opt/zaeze-ai/comfyui/output")
CHECKPOINT = "sd_xl_base_1.0.safetensors"
VARIANTS = [
    ("base", None),
    ("step0200", "gahyeon-sdxl-v1-step00000200.safetensors"),
    ("step0400", "gahyeon-sdxl-v1-step00000400.safetensors"),
    ("step0600", "gahyeon-sdxl-v1-step00000600.safetensors"),
    ("step0800", "gahyeon-sdxl-v1-step00000800.safetensors"),
    ("total1200", "gahyeon-sdxl-v1-continued-from0800-step00000400.safetensors"),
    ("total1600", "gahyeon-sdxl-v1-continued-from0800-step00000800.safetensors"),
    ("total2000", "gahyeon-sdxl-v1-continued-from0800-step00001200.safetensors"),
    ("total2400", "gahyeon-sdxl-v1-continued-from2000-step00000400.safetensors"),
    ("total2800", "gahyeon-sdxl-v1-continued-from2000-step00000800.safetensors"),
]
SCENARIOS = [
    {
        "slug": "front_portrait",
        "seed": 424201,
        "width": 512,
        "height": 512,
        "prompt": "gahyeonch woman, front-facing close-up portrait, neutral gentle expression, looking at viewer, natural soft light, detailed face, clean background, high quality photograph",
    },
    {
        "slug": "profile_smile",
        "seed": 424202,
        "width": 512,
        "height": 512,
        "prompt": "gahyeonch woman, right side profile portrait, subtle smile, natural soft light, detailed face, clean background, high quality photograph",
    },
    {
        "slug": "casual_fullbody",
        "seed": 424203,
        "width": 448,
        "height": 640,
        "prompt": "gahyeonch woman, full body, walking outdoors, casual white t-shirt and blue jeans, natural relaxed pose, daylight, high quality photograph",
    },
    {
        "slug": "black_dress",
        "seed": 424204,
        "width": 448,
        "height": 640,
        "prompt": "gahyeonch woman, full body studio portrait, elegant simple black dress, standing, neutral background, soft studio lighting, high quality photograph",
    },
]
NEGATIVE = "low quality, worst quality, blurry, deformed, distorted face, asymmetrical eyes, extra fingers, missing fingers, extra limbs, duplicate person, text, logo, watermark, signature"


def request_json(path: str, payload: Optional[dict] = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API + path,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def workflow(variant: str, lora: Optional[str], scenario: dict) -> dict:
    nodes = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": CHECKPOINT}},
        "3": {"class_type": "CLIPTextEncode", "inputs": {"text": scenario["prompt"], "clip": ["1", 1]}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": NEGATIVE, "clip": ["1", 1]}},
        "5": {"class_type": "EmptyLatentImage", "inputs": {"width": scenario["width"], "height": scenario["height"], "batch_size": 1}},
        "6": {"class_type": "KSampler", "inputs": {"seed": scenario["seed"], "steps": 24, "cfg": 6.0, "sampler_name": "dpmpp_2m", "scheduler": "karras", "denoise": 1.0, "model": ["1", 0], "positive": ["3", 0], "negative": ["4", 0], "latent_image": ["5", 0]}},
        "7": {"class_type": "VAEDecode", "inputs": {"samples": ["6", 0], "vae": ["1", 2]}},
        "8": {"class_type": "SaveImage", "inputs": {"filename_prefix": f"gahyeon_lora_compare/{scenario['slug']}_{variant}", "images": ["7", 0]}},
    }
    if lora:
        nodes["2"] = {"class_type": "LoraLoader", "inputs": {"lora_name": lora, "strength_model": 0.8, "strength_clip": 0.0, "model": ["1", 0], "clip": ["1", 1]}}
        nodes["3"]["inputs"]["clip"] = ["2", 1]
        nodes["4"]["inputs"]["clip"] = ["2", 1]
        nodes["6"]["inputs"]["model"] = ["2", 0]
    return nodes


def write_atomic(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def wait_output(prompt_id: str, deadline: float) -> Path:
    while time.time() < deadline:
        history = request_json(f"/history/{prompt_id}")
        record = history.get(prompt_id)
        if record:
            if record.get("status", {}).get("status_str") == "error":
                raise RuntimeError(json.dumps(record.get("status"), ensure_ascii=False))
            images = record.get("outputs", {}).get("8", {}).get("images", [])
            if images:
                image = images[0]
                return COMFY_OUTPUT / image.get("subfolder", "") / image["filename"]
        time.sleep(3)
    raise TimeoutError(f"generation timed out: {prompt_id}")


def main() -> None:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    for variant, lora in VARIANTS:
        for scenario in SCENARIOS:
            result_path = OUTPUT_ROOT / f"{scenario['slug']}_{variant}.json"
            if result_path.exists():
                existing = json.loads(result_path.read_text(encoding="utf-8"))
                if existing.get("status") == "completed" and Path(existing["output"]).exists():
                    results.append(existing)
                    continue
            queue = request_json("/queue")
            if queue.get("queue_running") or queue.get("queue_pending"):
                raise RuntimeError("ComfyUI queue is not empty before comparison generation")
            started = time.time()
            result = {
                "variant": variant,
                "lora": lora,
                "scenario": scenario,
                "status": "generating",
                "started_at": started,
            }
            write_atomic(result_path, result)
            submitted = request_json("/prompt", {"prompt": workflow(variant, lora, scenario)})
            prompt_id = submitted["prompt_id"]
            result["prompt_id"] = prompt_id
            try:
                output = wait_output(prompt_id, time.time() + 1800)
                if not output.exists() or output.stat().st_mtime < started:
                    raise RuntimeError(f"missing or stale output: {output}")
                result.update(
                    status="completed",
                    output=str(output),
                    sha256=sha256(output),
                    elapsed_seconds=round(time.time() - started, 3),
                )
                request_json("/system_stats")
            except Exception as error:
                result.update(status="failed", error_type=type(error).__name__, error=str(error))
                write_atomic(result_path, result)
                raise
            write_atomic(result_path, result)
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    write_atomic(OUTPUT_ROOT / "summary.json", {"results": results})


if __name__ == "__main__":
    main()
