import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.tools.build_selected_metahuman_handoff import build_handoff, verify_handoff

CONFIG = json.loads(Path("character_pipeline/config/metahuman_identity_handoff.json").read_text())


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


class SelectedMetaHumanHandoffTest(unittest.TestCase):
    def fixture(self, root):
        candidate = root / "candidate"; raw = candidate / "raw/mesh.glb"
        raw.parent.mkdir(parents=True); raw.write_bytes(b"glTF-mesh")
        state = candidate / "postprocess-state.json"; state.write_text(json.dumps({"state": "completed"}))
        shortlist = root / "shortlist.json"; shortlist.write_text(json.dumps({"state": "awaiting-human-review"}))
        selection = root / "selection.json"
        selection.write_text(json.dumps({"state": "selection-reviewed", "automatic": False,
            "productionMeshAllowed": False, "shortlist": {"path": str(shortlist), "sha256": sha(shortlist)},
            "selected": {"candidate": str(candidate), "model": "trellis", "seed": 20260813,
                         "postprocessStateSha256": sha(state),
                         "rawMesh": {"path": str(raw), "sha256": sha(raw)},
                         "role": "temporary-shape-estimate-for-metahuman-conform"}}))
        identity = root / "identity.json"; identity.write_text(json.dumps({"schemaVersion": 1, "characterId": "gahyeon"}))
        profile = root / "go.json"; profile.write_text(json.dumps({"profileId": "looking-glass-go",
            "device": {"panelResolution": [1440, 2560]},
            "quilt": {"viewCount": 66, "failClosedWithoutCalibration": True}}))
        return selection, identity, profile, raw, state

    def test_build_and_verify_preserves_shape_only_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); selection, identity, profile, _, _ = self.fixture(root)
            result = build_handoff(CONFIG, selection, identity, profile)
            output = root / "handoff.json"; output.write_text(json.dumps(result))
            verified = verify_handoff(output)
            self.assertEqual((verified["views"], verified["displayProfile"]), (5, "looking-glass-go"))
            self.assertFalse(result["automaticApproval"]); self.assertFalse(result["productionMeshAllowed"])
            self.assertEqual(result["sourceShape"]["format"], "glb")

    def test_selection_or_mesh_tamper_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); selection, identity, profile, raw, _ = self.fixture(root)
            raw.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "mesh checksum"):
                build_handoff(CONFIG, selection, identity, profile)

    def test_automatic_or_production_selection_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); selection, identity, profile, _, _ = self.fixture(root)
            value = json.loads(selection.read_text()); value["automatic"] = True
            selection.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "human-reviewed"):
                build_handoff(CONFIG, selection, identity, profile)

    def test_wrong_display_or_identity_authority_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); selection, identity, profile, _, _ = self.fixture(root)
            value = json.loads(profile.read_text()); value["device"]["panelResolution"] = [1920, 1080]
            profile.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError, "Looking Glass Go"):
                build_handoff(CONFIG, selection, identity, profile)
            profile.write_text(json.dumps({"profileId": "looking-glass-go", "device": {"panelResolution": [1440, 2560]},
                "quilt": {"viewCount": 66, "failClosedWithoutCalibration": True}}))
            identity.write_text(json.dumps({"schemaVersion": 1, "characterId": "other"}))
            with self.assertRaisesRegex(ValueError, "authority differs"):
                build_handoff(CONFIG, selection, identity, profile)

    def test_verifier_rejects_lineage_and_coordinate_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); selection, identity, profile, _, _ = self.fixture(root)
            result = build_handoff(CONFIG, selection, identity, profile)
            output = root / "handoff.json"; output.write_text(json.dumps(result))
            result["coordinateContract"]["unit"] = "meter"; output.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError, "coordinate"):
                verify_handoff(output)


if __name__ == "__main__": unittest.main()
