#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from character_pipeline.tools.verify_hero_groom_scaffold import verify_groom_scaffold


class HeroGroomScaffoldTest(unittest.TestCase):
    def test_current_pending_scaffold(self):
        config = json.loads(Path("character_pipeline/config/hero_groom_qa.json").read_text())
        binding = json.loads(Path("character_pipeline/metahuman/validation/v001/groom-binding.json").read_text())
        result = verify_groom_scaffold(config, binding)
        self.assertEqual(result["state"], "awaiting-production-groom")
        self.assertEqual(result["captures"], 14)


if __name__ == "__main__":
    unittest.main()
