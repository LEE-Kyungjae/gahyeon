#!/usr/bin/env python3

import binascii
import json
import subprocess
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path

from package_gahyeon_g1_handoff import DEFAULT_INPUT, package as package_handoff
from package_gahyeon_g1_submission import package as package_submission
from verify_gahyeon_g1_submission import verify_archive


def png(width: int = 64, height: int = 64) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF))
    pixels = b"".join(b"\x00" + b"\x00\x00\x00" * width for _ in range(height))
    return (b"\x89PNG\r\n\x1a\n"
            + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


class G1SubmissionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        archive = self.root / "handoff.zip"
        package_handoff(DEFAULT_INPUT, archive)
        self.handoff = self.root / "handoff"
        with zipfile.ZipFile(archive) as source:
            source.extractall(self.handoff)
        self.model = self.root / "gahyeon-g1.blend"
        self.model.write_bytes(b"BLENDER-v300-candidate")
        self.evidence = self.root / "evidence"
        self.evidence.mkdir()
        order = json.loads((self.handoff / "g1-authoring-work-order.json").read_text())
        for item in order["requiredEvidence"]:
            (self.evidence / f"{item['view']}.png").write_bytes(png())
        self.output = self.root / "submission.zip"

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_candidate_is_sealed_and_verified(self):
        result = package_submission(
            self.handoff, self.model, "blend", self.evidence, self.output)
        verified = verify_archive(self.output)
        self.assertEqual(15, result["evidenceCount"])
        self.assertEqual("candidate", verified["status"])
        with zipfile.ZipFile(self.output) as archive:
            review = json.loads(archive.read("g1-review.json"))
        self.assertEqual([], review["approvals"])
        self.assertEqual(
            {"rear-body", "rear-hair", "top-hair", "rear-outfit"},
            set(review["artistAuthoredRegions"]),
        )

    def test_missing_view_fails_closed_without_output(self):
        (self.evidence / "hair-top.png").unlink()
        with self.assertRaisesRegex(ValueError, "required G1 evidence is missing"):
            package_submission(self.handoff, self.model, "blend", self.evidence, self.output)
        self.assertFalse(self.output.exists())

    def test_packaged_submission_tool_runs_without_repository_imports(self):
        output = self.root / "standalone-submission.zip"
        completed = subprocess.run(
            [
                sys.executable,
                str(self.handoff / "tools/package-g1-submission.py"),
                "--handoff-dir", str(self.handoff),
                "--model", str(self.model),
                "--format", "blend",
                "--evidence-dir", str(self.evidence),
                "--output", str(output),
            ],
            cwd=self.handoff,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(15, json.loads(completed.stdout)["evidenceCount"])
        self.assertTrue(verify_archive(output)["valid"])

    def test_fake_png_is_rejected(self):
        (self.evidence / "hair-top.png").write_bytes(b"not-an-image")
        with self.assertRaisesRegex(ValueError, "not a PNG"):
            package_submission(self.handoff, self.model, "blend", self.evidence, self.output)

    def test_changed_archive_entry_is_rejected(self):
        package_submission(self.handoff, self.model, "blend", self.evidence, self.output)
        changed = self.root / "changed.zip"
        with zipfile.ZipFile(self.output) as source, zipfile.ZipFile(changed, "w") as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "model/gahyeon-g1.blend":
                    data += b"tamper"
                target.writestr(info, data)
        with self.assertRaisesRegex(ValueError, "byte size mismatch"):
            verify_archive(changed)


if __name__ == "__main__":
    unittest.main()
