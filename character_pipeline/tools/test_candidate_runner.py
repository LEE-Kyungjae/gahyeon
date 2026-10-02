import copy
from datetime import datetime, timezone, timedelta
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from character_pipeline.tools.candidate_runner import execute_candidate, sha256, validate_runner_request


CONTRACT = json.loads(Path("character_pipeline/config/runner_contract.json").read_text())


class CandidateRunnerTest(unittest.TestCase):
    def fixture(self, root: Path, model="trellis", seed=20260813):
        image = root / "masked.png"
        pixels = Image.new("RGBA", (512, 512), (120, 100, 90, 255))
        pixels.putpixel((0, 0), (0, 0, 0, 0))
        pixels.save(image)
        matte_manifest = root / "matte.json"
        matte_manifest.write_text(json.dumps({"canonicalIndex": 3, "derivative": {"sha256": sha256(image)}}))
        approval = root / "approval.json"
        now = datetime.now(timezone.utc)
        approval.write_text(json.dumps({
            "schemaVersion": 1, "canonicalIndex": 3, "scope": "face-shape-only",
            "exclusions": ["hair-strand-fidelity", "earring-geometry", "skin-texture", "final-topology"],
            "purpose": "temporary-shape-estimate-for-metahuman-conform", "productionMeshAllowed": False,
            "approved": True, "automatic": False,
            "reviewer": {"name": "fixture-owner", "role": "character-owner"},
            "approvedAt": now.isoformat(), "expiresAt": (now + timedelta(days=30)).isoformat(),
            "derivative": {"path": str(image.resolve()), "sha256": sha256(image)},
            "matteManifest": {"path": str(matte_manifest.resolve()), "sha256": sha256(matte_manifest)}
        }))
        candidate = root / "generation" / model / "candidate_001"
        (candidate / "raw").mkdir(parents=True)
        for name in ("inputs", "renders", "measurements", "logs"):
            (candidate / name).mkdir()
        (candidate / "candidate.json").write_text(json.dumps({
            "status": "planned", "model": model, "seed": seed
        }))
        return {"schemaVersion": 1, "model": model, "seed": seed,
                "claim": CONTRACT["claim"], "productionMeshAllowed": False,
                "input": {"path": str(image.resolve()), "sha256": sha256(image),
                          "approval": str(approval.resolve()),
                          "approvalConfig": str(Path("character_pipeline/config/shape_input_approval.json").resolve())},
                "snapshot": {"revision": "a" * 40, "inventorySha256": "b" * 64},
                "candidate": str(candidate.resolve())}

    def good_backend(self, request, output):
        (output / "mesh.glb").write_bytes(b"glTF" + b"x" * 2048)
        return {"model": request["model"], "seed": request["seed"], "exitCode": 0}

    def test_atomic_success_promotes_mesh_and_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.fixture(Path(directory))
            receipt = execute_candidate(CONTRACT, request, self.good_backend)
            raw = Path(request["candidate"]) / "raw"
            self.assertEqual(receipt["seed"], 20260813)
            self.assertTrue((raw / "mesh.glb").is_file())
            self.assertTrue((raw / "result.json").is_file())
            manifest = json.loads((Path(request["candidate"]) / "candidate.json").read_text())
            self.assertEqual(manifest["status"], "generated")
            self.assertEqual({item["role"] for item in manifest["outputs"]}, {"raw-mesh", "runner-receipt"})

    def test_partial_or_multiple_output_never_promotes(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.fixture(Path(directory))
            def broken(req, output):
                (output / "one.glb").write_bytes(b"x" * 2048)
                (output / "two.obj").write_bytes(b"x" * 2048)
                return {"model": req["model"], "seed": req["seed"]}
            with self.assertRaisesRegex(ValueError, "exactly one"):
                execute_candidate(CONTRACT, request, broken)
            self.assertEqual(list((Path(request["candidate"]) / "raw").iterdir()), [])

    def test_backend_exception_never_promotes(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.fixture(Path(directory))
            def broken(req, output):
                (output / "mesh.glb").write_bytes(b"x" * 2048)
                raise RuntimeError("GPU OOM")
            with self.assertRaisesRegex(RuntimeError, "GPU OOM"):
                execute_candidate(CONTRACT, request, broken)
            self.assertEqual(list((Path(request["candidate"]) / "raw").iterdir()), [])

    def test_seed_checksum_and_transparency_are_enforced(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.fixture(Path(directory))
            bad = copy.deepcopy(request); bad["seed"] = 1
            with self.assertRaisesRegex(ValueError, "seed"):
                validate_runner_request(CONTRACT, bad)
            bad = copy.deepcopy(request); bad["input"]["sha256"] = "0" * 64
            with self.assertRaisesRegex(ValueError, "checksum"):
                validate_runner_request(CONTRACT, bad)
            image = Path(request["input"]["path"])
            Image.new("RGBA", (512, 512), (1, 2, 3, 255)).save(image)
            request["input"]["sha256"] = sha256(image)
            with self.assertRaisesRegex(ValueError, "transparent"):
                validate_runner_request(CONTRACT, request)

    def test_missing_or_forged_approval_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.fixture(Path(directory))
            bad = copy.deepcopy(request); bad["input"].pop("approval")
            with self.assertRaisesRegex(ValueError, "approval package missing"):
                validate_runner_request(CONTRACT, bad)
            approval_path = Path(request["input"]["approval"])
            approval = json.loads(approval_path.read_text()); approval["automatic"] = True
            approval_path.write_text(json.dumps(approval))
            with self.assertRaisesRegex(ValueError, "explicit human approval"):
                validate_runner_request(CONTRACT, request)

    def test_second_execution_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            request = self.fixture(Path(directory))
            execute_candidate(CONTRACT, request, self.good_backend)
            with self.assertRaisesRegex(ValueError, "already contains"):
                execute_candidate(CONTRACT, request, self.good_backend)


if __name__ == "__main__":
    unittest.main()
