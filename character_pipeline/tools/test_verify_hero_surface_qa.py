#!/usr/bin/env python3

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from character_pipeline.tools.verify_hero_surface_qa import validate_surface_contract


class HeroSurfaceQaTest(unittest.TestCase):
    def fixture(self, root: Path):
        config = json.loads(Path("character_pipeline/config/hero_surface_qa.json").read_text())
        texture_dir = root / "textures"
        texture_dir.mkdir()
        textures = {}
        source = Image.new("L", (4096, 4096), 128)
        for channel in config["skin"]["requiredChannels"]:
            path = texture_dir / f"{channel}.png"
            source.save(path, optimize=True)
            textures[channel] = {"file": str(path.relative_to(root)),
                                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        editor = root / "editor.json"
        capture_dir = root / "captures"
        capture_dir.mkdir()
        captures = []
        capture_image = Image.new("RGB", (1440, 2560), "gray")
        for item in config["captures"]:
            path = capture_dir / f"{item['id']}.png"
            capture_image.save(path, optimize=True)
            captures.append({"id": item["id"], "file": path.name,
                             "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        manifest = capture_dir / "manifest.json"
        manifest.write_text(json.dumps({"resolution": [1440, 2560], "captures": captures}))
        binding = {
            "state": "candidate", "claim": "production-surface-candidate-not-approved",
            "skinMaterialInstance": "/Game/Skin", "eyeMaterialInstances": ["/Game/Eye"],
            "textures": textures,
            "zoneMasks": {zone: "/Game/Mask" for zone in config["skin"]["requiredZones"]},
            "eyeParts": {part: "/Game/EyePart" for part in config["eyes"]["requiredParts"]},
            "editorEvidence": editor.name,
            "captureManifest": str(manifest.relative_to(root)),
        }
        editor.write_text(json.dumps({
            "schemaVersion": 1, "kind": "metahuman-production-surface-editor-evidence",
            "engine": "5.6", "editorRuntimeVerified": True,
            "checks": {"materials": True, "eyes": True},
            "skin": {"materialInstance": "/Game/Skin", "textureChannels": {
                channel: {"path": f"/Game/{channel}", "class": "Texture2D", "dimensions": [4096, 4096]}
                for channel in config["skin"]["requiredChannels"]}},
            "eyes": {"materialInstances": ["/Game/Eye"],
                     "parts": {part: {"path": f"/Game/{part}", "exists": True}
                               for part in config["eyes"]["requiredParts"]}},
            "automaticApproval": False, "qualityClaim": None,
        }))
        return config, binding

    def test_complete_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            config, binding = self.fixture(Path(directory))
            self.assertEqual(validate_surface_contract(config, binding, Path(directory))["captures"], 7)

    def test_rejects_missing_tearline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            del binding["eyeParts"]["tearLine"]
            with self.assertRaisesRegex(ValueError, "eye parts"):
                validate_surface_contract(config, binding, root)

    def test_rejects_texture_below_4k(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            path = root / binding["textures"]["roughness"]["file"]
            Image.new("L", (2048, 2048), 128).save(path)
            binding["textures"]["roughness"]["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaisesRegex(ValueError, "below 4K"):
                validate_surface_contract(config, binding, root)

    def test_rejects_missing_editor_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            (root / "editor.json").unlink()
            with self.assertRaisesRegex(ValueError, "Editor"):
                validate_surface_contract(config, binding, root)

    def test_rejects_unobserved_editor_texture_channel(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config, binding = self.fixture(root)
            evidence = json.loads((root / "editor.json").read_text())
            del evidence["skin"]["textureChannels"]["microNormal"]
            (root / "editor.json").write_text(json.dumps(evidence))
            with self.assertRaisesRegex(ValueError, "texture channels"):
                validate_surface_contract(config, binding, root)


if __name__ == "__main__":
    unittest.main()
