import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).with_name("report_metahuman_disk_recovery.py")
SPEC = importlib.util.spec_from_file_location("disk_recovery", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class DiskRecoveryTest(unittest.TestCase):
    def test_decimal_docker_sizes_convert_to_gib(self):
        self.assertAlmostEqual(MODULE.parse_decimal_size("10.36GB (63%)"), 10.36)
        self.assertAlmostEqual(MODULE.parse_decimal_size("1024MB"), 1.0)
        self.assertEqual(MODULE.parse_decimal_size("0B"), 0.0)


if __name__ == "__main__":
    unittest.main()
