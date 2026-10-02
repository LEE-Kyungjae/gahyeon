#!/usr/bin/env python3

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
import uuid
from pathlib import Path

from verify_gahyeon_sdxl_artifacts import (
    CHECKPOINTS,
    SCENARIOS,
    VALIDATION_INDICES,
    VARIANTS,
    sync_summary,
    verify,
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class GahyeonSdxlArtifactTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.identity_root = self.root / "gahyeon-ch"
        self.dataset_root = self.root / "gahyeon-sdxl-v1"
        self.continuation_root = self.root / "gahyeon-sdxl-v1-continuation"
        self.comparison_root = self.root / "gahyeon-sdxl-v1-comparison"
        for path in (self.identity_root, self.dataset_root, self.continuation_root,
                     self.comparison_root / "results", self.comparison_root / "images"):
            path.mkdir(parents=True, exist_ok=True)
        self.identity = self.identity_root / "identity-reference.json"
        self.dataset = self.dataset_root / "manifest.json"
        self.continuation = self.continuation_root / "manifest.json"
        self.selection = self.comparison_root / "selection.json"
        self.write_fixture()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def write_json(self, path: Path, value: dict) -> None:
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def write_fixture(self) -> None:
        references = []
        supporting = []
        dataset = {"trigger": "gahyeonch", "train": [], "validation": []}
        for index in range(1, 30):
            source_name = f"source-{index:02d}.png"
            source_data = f"source:{index}".encode()
            (self.identity_root / source_name).write_bytes(source_data)
            checksum = sha(source_data)
            reference = {"index": index, "file": source_name, "sha256": checksum}
            (references if index <= 18 else supporting).append(reference)
            split = "validation" if index in VALIDATION_INDICES else "train"
            relative = (f"validation/gahyeon_{index:02d}.png" if split == "validation"
                        else f"train/1_gahyeonch/gahyeon_{index:02d}.png")
            image = self.dataset_root / relative
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(source_data)
            caption = f"gahyeonch fixture image {index}"
            image.with_suffix(".txt").write_text(caption + "\n", encoding="utf-8")
            dataset[split].append({
                "index": index, "source": source_name, "file": relative,
                "sha256": checksum, "caption": caption,
            })

        checkpoint_rows = []
        for step, filename in CHECKPOINTS.items():
            checkpoint_rows.append({
                "total_step": step, "status": "completed", "file": filename,
                "sha256": sha(f"checkpoint:{step}".encode()),
            })
        self.write_json(self.identity, {
            "canonicalSource": "user-provided-originals",
            "references": references, "supportingReferences": supporting,
            "auxiliaryModels": [
                {"name": f"gahyeon-sdxl-v1-total{step}", "totalSteps": step,
                 "sha256": next(
                    row["sha256"] for row in checkpoint_rows if row["total_step"] == step),
                 "role": "general-concept" if step == 2000 else "front-face-helper",
                 "heroReferenceAllowed": False}
                for step in (2000, 2800)
            ],
        })
        self.write_json(self.dataset, dataset)
        self.write_json(self.continuation, {
            "status": "completed", "base_total_steps": 800, "additional_steps": 2000,
            "final_total_steps": 2800, "learning_rate": 5e-05,
            "source_weights": "/opt/zaeze-ai/training/gahyeon-sdxl-v1/outputs/gahyeon-sdxl-v1.safetensors",
            "source_sha256": sha(b"source-weight"), "training_errors_detected": False,
            "checkpoints": checkpoint_rows, "registered_in_comfyui": True,
            "comparison_status": "completed",
            "comparison": {"records": 40, "completed": 40, "failed": 0,
                           "missing_outputs": 0, "default_total_step": 2000,
                           "closeup_specialist_total_step": 2800},
        })
        checkpoint_by_step = {row["total_step"]: row for row in checkpoint_rows}
        self.write_json(self.selection, {
            "status": "auxiliary-only", "comparisonStrength": 0.8,
            "default": {**checkpoint_by_step[2000], "totalSteps": 2000,
                        "heroReferenceAllowed": False},
            "specialists": [{**checkpoint_by_step[2800], "totalSteps": 2800,
                             "heroReferenceAllowed": False}],
            "approval": {"generationUse": True, "g0IdentityReference": False,
                         "final3DHeroReference": False},
            "canonicalIdentityManifest": "../gahyeon-ch/identity-reference.json",
        })

        results = []
        for variant, lora in VARIANTS.items():
            for scenario, scenario_payload in SCENARIOS.items():
                filename = f"{scenario}_{variant}_00001_.png"
                image_data = f"image:{scenario}:{variant}".encode()
                (self.comparison_root / "images" / filename).write_bytes(image_data)
                record = {
                    "variant": variant, "lora": lora, "scenario": scenario_payload,
                    "status": "completed", "started_at": 1.0,
                    "prompt_id": str(uuid.uuid4()),
                    "output": f"/opt/zaeze-ai/comfyui/output/gahyeon_lora_compare/{filename}",
                    "sha256": sha(image_data), "elapsed_seconds": 2.0,
                }
                self.write_json(
                    self.comparison_root / "results" / f"{scenario}_{variant}.json", record)
                results.append(record)
        self.write_json(self.comparison_root / "results/summary.json", {"results": results})

    def verify_fixture(self, *, require_summary: bool = True) -> dict:
        return verify(self.dataset, self.continuation, self.comparison_root,
                      self.selection, self.identity, require_summary=require_summary)

    def mutate_json(self, path: Path, callback) -> None:
        value = json.loads(path.read_text(encoding="utf-8"))
        callback(value)
        self.write_json(path, value)

    def test_complete_fixture_passes_exact_matrix(self) -> None:
        result = self.verify_fixture()
        self.assertEqual(40, result["comparison"]["records"])
        self.assertEqual({"train": 24, "validation": 5, "sourceImages": 29},
                         result["dataset"])
        self.assertFalse(result["selection"]["heroReferenceAllowed"])

    def test_stale_summary_cannot_support_completed_claim(self) -> None:
        summary = self.comparison_root / "results/summary.json"
        self.mutate_json(summary, lambda value: value["results"].pop())
        with self.assertRaisesRegex(ValueError, "does not exactly match"):
            self.verify_fixture()

    def test_tampered_comparison_image_is_rejected(self) -> None:
        image = self.comparison_root / "images/front_portrait_total2800_00001_.png"
        image.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "image checksum mismatch"):
            self.verify_fixture()

    def test_selection_must_match_continuation_and_identity(self) -> None:
        def change(value):
            value["default"]["sha256"] = "f" * 64
        self.mutate_json(self.selection, change)
        with self.assertRaisesRegex(ValueError, "disagrees with checkpoint"):
            self.verify_fixture()

    def test_identity_cannot_relabel_selected_checkpoint_role(self) -> None:
        def change(value):
            value["auxiliaryModels"][1]["role"] = "hero-master"
        self.mutate_json(self.identity, change)
        with self.assertRaisesRegex(ValueError, "role mismatch"):
            self.verify_fixture()

    def test_validation_leakage_is_rejected(self) -> None:
        def change(value):
            value["train"][0]["index"] = 3
        self.mutate_json(self.dataset, change)
        with self.assertRaisesRegex(ValueError, "source identity mismatch|validation leakage"):
            self.verify_fixture()

    def test_exact_authoritative_summary_repairs_stale_local_copy(self) -> None:
        local = self.comparison_root / "results/summary.json"
        authoritative = self.root / "authoritative-summary.json"
        authoritative.write_bytes(local.read_bytes())
        self.mutate_json(local, lambda value: value["results"].pop())
        self.verify_fixture(require_summary=False)
        rows = json.loads(authoritative.read_text(encoding="utf-8"))["results"]
        sync_summary(authoritative, local, rows)
        self.assertEqual(40, self.verify_fixture()["comparison"]["records"])

    def test_mismatched_authoritative_summary_does_not_replace_local(self) -> None:
        local = self.comparison_root / "results/summary.json"
        before = local.read_bytes()
        authoritative = self.root / "authoritative-summary.json"
        authoritative.write_text('{"results": []}\n', encoding="utf-8")
        individual = json.loads(local.read_text(encoding="utf-8"))["results"]
        with self.assertRaisesRegex(ValueError, "does not exactly match"):
            sync_summary(authoritative, local, individual)
        self.assertEqual(before, local.read_bytes())


if __name__ == "__main__":
    unittest.main()
