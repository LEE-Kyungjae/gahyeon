#!/usr/bin/env python3

import unittest
from pathlib import Path

from character_pipeline.tools.verify_metahuman_post_conform_scaffold import verify_metahuman_post_conform_scaffold


class MetaHumanPostConformScaffoldTest(unittest.TestCase):
    def test_current_scaffold(self):
        result = verify_metahuman_post_conform_scaffold(Path.cwd())
        self.assertTrue(result["valid"])
        self.assertEqual(result["views"], 5)
        self.assertEqual(result["state"], "awaiting-editor-evidence")


if __name__ == "__main__":
    unittest.main()
