#!/usr/bin/env python3

import subprocess
import unittest


class HeroSurfaceScaffoldTest(unittest.TestCase):
    def test_current_pending_scaffold(self):
        result = subprocess.run(
            ["python3", "character_pipeline/tools/verify_hero_surface_scaffold.py"],
            check=True, capture_output=True, text=True,
        )
        self.assertIn('"skinChannels": 8', result.stdout)
        self.assertIn('"state": "awaiting-metahuman-candidate"', result.stdout)


if __name__ == "__main__":
    unittest.main()
