import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


PATCHER_PATH = Path(__file__).with_name("apply_qwen_c_http_emotion_patch.py")
PATCHER_SPEC = importlib.util.spec_from_file_location("gahyeon_qwen_c_patcher", PATCHER_PATH)
patcher = importlib.util.module_from_spec(PATCHER_SPEC)
assert PATCHER_SPEC.loader is not None
PATCHER_SPEC.loader.exec_module(patcher)


class ApplyQwenCHttpEmotionPatchTest(unittest.TestCase):
    def test_rejects_unpinned_revision(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            repository = source / "repository"
            repository.mkdir()
            with patch.object(patcher, "run_checked", return_value="wrong"):
                with self.assertRaisesRegex(SystemExit, "refusing to patch unpinned"):
                    patcher.apply_patch(source, repository, False)

    def test_check_only_does_not_apply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            repository = root / "repository"
            source.mkdir()
            patch_path = repository / patcher.PATCH_RELATIVE_PATH
            patch_path.parent.mkdir(parents=True)
            patch_path.write_text("patch", encoding="utf-8")
            results = [
                patcher.PINNED_REVISION,
                subprocess.CompletedProcess([], 1, "", "not applied"),
                "",
            ]
            with patch.object(patcher, "run_checked", side_effect=[results[0], results[2]]) as run:
                with patch.object(subprocess, "run", return_value=results[1]):
                    patcher.apply_patch(source, repository, True)
            self.assertEqual(run.call_count, 2)


if __name__ == "__main__":
    unittest.main()
