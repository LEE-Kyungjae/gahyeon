import importlib.util
import json
import tempfile
import struct
import unittest
from pathlib import Path
from unittest import mock


MODULE_PATH = Path(__file__).with_name("keentools_cloud_candidate_v175.py")
SPEC = importlib.util.spec_from_file_location("keentools_cloud_candidate_v175", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class KeenToolsCloudCandidateV175Test(unittest.TestCase):
    def test_empty_success_response_is_valid(self):
        response = mock.MagicMock()
        response.read.return_value = b""
        response.__enter__.return_value = response
        with mock.patch.object(MODULE.urllib.request, "urlopen", return_value=response):
            self.assertEqual(
                MODULE.request_json_v175("POST", "https://example.invalid", "secret", {}),
                {},
            )

    def test_prepare_seals_five_golden_views_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            output = root / "output"
            source.mkdir()
            inputs = []
            for index, view in enumerate(("front", "three-quarter-left", "left-profile",
                                          "right-profile", "three-quarter-right"), start=1):
                filename = f"source-{index}.png"
                path = source / filename
                path.write_bytes(
                    b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" +
                    struct.pack(">II", 1254, 1254)
                )
                inputs.append((index, view, filename, MODULE.sha256_v175(path)))
            with mock.patch.object(MODULE, "WORKSPACE", root), \
                 mock.patch.object(MODULE, "SOURCE_ROOT", source), \
                 mock.patch.object(MODULE, "OUTPUT_ROOT", output), \
                 mock.patch.object(MODULE, "INPUTS", tuple(inputs)):
                first = MODULE.prepare_v175()
                second = MODULE.prepare_v175()
            self.assertEqual(first, second)
            self.assertEqual(len(first["inputs"]), 5)
            self.assertEqual(first["status"], "prepared-not-submitted")
            self.assertFalse(first["gates"]["automaticApproval"])
            persisted = json.loads((output / "input-manifest.json").read_text())
            self.assertEqual(persisted["inputs"], first["inputs"])

    def test_execute_fails_before_network_without_api_key(self):
        with mock.patch.object(MODULE, "prepare_v175", return_value={"inputs": []}), \
             mock.patch.dict("os.environ", {}, clear=True), \
             mock.patch.object(MODULE, "request_json_v175") as request:
            with self.assertRaisesRegex(RuntimeError, "KEENTOOLS_API_KEY"):
                MODULE.execute_v175(MODULE.DEFAULT_API_BASE, 0.01)
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
