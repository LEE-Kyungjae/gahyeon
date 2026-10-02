#!/usr/bin/env python3

import unittest
from pathlib import Path


class TalkingRuntimeInspectionContractTest(unittest.TestCase):
    def test_inspector_is_read_only_and_targets_retained_blueprint(self):
        source = (Path(__file__).parents[1] / "unreal/GahyeonStage/Content/Python/"
                  "gahyeon_inspect_talking_runtime_v092.py").read_text(encoding="utf-8")
        self.assertIn("BP_Skotukeda_WardrobeGroomQA_v088", source)
        self.assertIn('"assetModified": False', source)
        self.assertNotIn("save_loaded_asset", source)
        self.assertNotIn("save_map", source)
        self.assertNotIn("delete_asset", source)


if __name__ == "__main__":
    unittest.main()
