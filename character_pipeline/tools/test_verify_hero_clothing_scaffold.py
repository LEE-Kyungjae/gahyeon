#!/usr/bin/env python3

import json
import unittest
from pathlib import Path

from character_pipeline.tools.verify_hero_clothing_scaffold import verify_clothing_scaffold


class HeroClothingScaffoldTest(unittest.TestCase):
    def test_current_pending_scaffold(self):
        config = json.loads(Path("character_pipeline/config/hero_clothing_qa.json").read_text())
        binding = json.loads(Path("character_pipeline/metahuman/validation/v001/clothing-binding.json").read_text())
        result = verify_clothing_scaffold(config, binding)
        self.assertEqual(result["state"], "awaiting-production-clothing")
        self.assertEqual(result["captures"], 16)


if __name__ == "__main__":
    unittest.main()
