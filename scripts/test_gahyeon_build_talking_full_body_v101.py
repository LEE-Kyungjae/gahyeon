import unittest
from pathlib import Path


class TalkingFullBodyV101ContractTest(unittest.TestCase):
    def test_final_camera_contract(self):
        source = Path(
            "unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v101.py"
        ).read_text(encoding="utf-8")
        self.assertIn("v101/Sequence", source)
        self.assertIn("channel.set_default(3.2)", source)
        self.assertIn("channel.set_default(125.0)", source)
        self.assertIn("refusing to overwrite v101 sequence", source)


if __name__ == "__main__":
    unittest.main()
