#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.tools.build_metahuman_identity_launch_plan import build, verify


class LaunchPlanTest(unittest.TestCase):
    def fixtures(self, root: Path, ready: bool = True):
        editor = root / "UE_5.6/Engine/Binaries/Mac/UnrealEditor.app"
        executable = editor / "Contents/MacOS/UnrealEditor"
        executable.parent.mkdir(parents=True)
        executable.write_text("binary")
        project = root / "Stage.uproject"
        project.write_text("{}")
        importer = root / "import.py"
        importer.write_text("pass\n")
        session = root / "session.json"
        session.write_text(json.dumps({
            "sessionId": "gahyeon-metahuman-identity-v002",
            "state": "ready-to-launch" if ready else "blocked-before-launch",
            "blockedChecks": [] if ready else ["engineInstalled"],
            "unreal": {"editor": str(editor), "project": str(project)},
        }))
        return session, importer

    def test_ready_plan_is_import_only_and_verifiable(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session, importer = self.fixtures(root)
            plan = build(session, importer)
            output = root / "plan.json"
            output.write_text(json.dumps(plan))
            self.assertEqual(verify(output)["state"], "ready-to-launch-import-only")
            self.assertIn("identity-solve", plan["stopsBefore"])

    def test_blocked_session_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            session, importer = self.fixtures(Path(temp), ready=False)
            with self.assertRaisesRegex(ValueError, "not ready"):
                build(session, importer)

    def test_lineage_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            session, importer = self.fixtures(root)
            output = root / "plan.json"
            output.write_text(json.dumps(build(session, importer)))
            importer.write_text("changed\n")
            with self.assertRaisesRegex(ValueError, "lineage"):
                verify(output)


if __name__ == "__main__":
    unittest.main()
