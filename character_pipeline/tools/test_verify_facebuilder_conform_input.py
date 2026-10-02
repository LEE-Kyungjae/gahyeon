from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from character_pipeline.tools.verify_facebuilder_conform_input import (
    verify_facebuilder_conform_input,
)


class VerifyFaceBuilderConformInputTest(unittest.TestCase):
    def build_package(self, root: Path) -> Path:
        files = []
        for name, data in (
            ("gahyeon-facebuilder-v159.obj", b"o head\nv 0 0 0\n"),
            ("gahyeon-facebuilder-v159.fbx", b"Kaydara FBX Binary"),
        ):
            path = root / name
            path.write_bytes(data)
            files.append({
                "uri": name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            })
        manifest = {
            "schemaVersion": 1,
            "iteration": "v159",
            "purpose": "ue58-metahuman-from-custom-mesh-input",
            "topology": {
                "vertices": 5_000,
                "polygons": 5_000,
                "nonManifoldEdgesOverTwoFaces": 0,
                "looseEdges": 0,
            },
            "canonicalCameras": [
                {"imagePath": f"canonical-{index}.png", "pinCount": 20}
                for index in range(4)
            ],
            "files": files,
            "claims": {
                "identityApproved": False,
                "metaHumanConformed": False,
                "productionReady": False,
            },
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return root

    def test_valid_package_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = verify_facebuilder_conform_input(self.build_package(Path(directory)))
            self.assertTrue(result["valid"])
            self.assertEqual(result["cameraCount"], 4)

    def test_tampered_mesh_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = self.build_package(Path(directory))
            (package / "gahyeon-facebuilder-v159.obj").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "lineage mismatch"):
                verify_facebuilder_conform_input(package)

    def test_self_approval_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            package = self.build_package(Path(directory))
            path = package / "manifest.json"
            manifest = json.loads(path.read_text(encoding="utf-8"))
            manifest["claims"]["identityApproved"] = True
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not self-approve"):
                verify_facebuilder_conform_input(package)


if __name__ == "__main__":
    unittest.main()
