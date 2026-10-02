#!/usr/bin/env python3

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from character_pipeline.tools.verify_post_conform_metahuman import validate_post_conform_contract


class PostConformMetaHumanTest(unittest.TestCase):
    def fixture(self, root: Path) -> Path:
        assets = {name: f"/Game/Fixture/{name}" for name in (
            "metahumanIdentity", "heroBlueprint", "faceSkeletalMesh", "bodySkeletalMesh",
            "faceControlRig", "bodyControlRig",
        )}
        assets["grooms"] = ["/Game/Fixture/HairGroom"]
        binding = {"state": "candidate", "claim": "metahuman-candidate-not-approved", "assets": assets}
        (root / "binding.json").write_text(json.dumps(binding))
        checks = {name: True for name in ("identity", "hero", "face", "body", "faceRig", "bodyRig", "groom")}
        editor = {"editorRuntimeVerified": True, "readyForPostConformRender": True,
                  "dnaOrRigLogicBound": True, "checks": checks}
        (root / "editor.json").write_text(json.dumps(editor))
        renders = root / "renders"
        renders.mkdir()
        views = []
        for name in ("face-front", "face-left-45", "face-right-45", "face-left-profile", "face-right-profile"):
            path = renders / f"{name}.png"
            Image.new("RGB", (1440, 2560), "gray").save(path)
            views.append({"view": name, "file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        (renders / "render-manifest.json").write_text(json.dumps({"resolution": [1440, 2560], "views": views}))
        contract = {
            "iteration": "v001", "state": "candidate", "binding": "binding.json",
            "editorEvidence": "editor.json",
            "renderEvidence": {"profile": "looking-glass-go", "resolution": [1440, 2560],
                               "directory": "renders", "manifest": "renders/render-manifest.json",
                               "views": [item["view"] for item in views]},
            "comparison": {"identityScoreMayBeEmitted": False, "automaticApproval": False},
        }
        path = root / "contract.json"
        path.write_text(json.dumps(contract))
        return path

    def test_valid_candidate_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(validate_post_conform_contract(self.fixture(Path(directory)))["valid"])

    def test_rejects_missing_dna_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self.fixture(Path(directory))
            editor = Path(directory) / "editor.json"
            value = json.loads(editor.read_text())
            value["dnaOrRigLogicBound"] = None
            editor.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "DNA/RigLogic"):
                validate_post_conform_contract(contract)

    def test_rejects_wrong_go_resolution(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = self.fixture(Path(directory))
            value = json.loads(contract.read_text())
            value["renderEvidence"]["resolution"] = [1920, 1080]
            contract.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "Looking Glass Go"):
                validate_post_conform_contract(contract)


if __name__ == "__main__":
    unittest.main()
