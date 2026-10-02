import unittest
from pathlib import Path


class TalkingFullBodyV103ContractTest(unittest.TestCase):
    def test_safe_margin_camera_contract(self):
        source = Path(
            "unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v103.py"
        ).read_text(encoding="utf-8")
        self.assertIn("v103/Sequence", source)
        self.assertIn("channel.set_default(-70.0)", source)
        self.assertIn("channel.set_default(125.0)", source)


if __name__ == "__main__":
    unittest.main()
