import unittest
from pathlib import Path


class TalkingFullBodyV102ContractTest(unittest.TestCase):
    def test_dolly_camera_contract(self):
        source = Path(
            "unreal/GahyeonStage/Content/Python/gahyeon_build_talking_full_body_v102.py"
        ).read_text(encoding="utf-8")
        self.assertIn("v102/Sequence", source)
        self.assertIn("channel.set_default(5.0)", source)
        self.assertIn("channel.set_default(-45.0)", source)
        self.assertIn("channel.set_default(125.0)", source)


if __name__ == "__main__":
    unittest.main()
