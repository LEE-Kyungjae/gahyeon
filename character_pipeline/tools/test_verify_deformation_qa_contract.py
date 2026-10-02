import json
import tempfile
import unittest
from pathlib import Path

from character_pipeline.tools.verify_deformation_qa_contract import verify


class DeformationQaContractTest(unittest.TestCase):
    def test_current_contract(self):
        result = verify(
            Path("character_pipeline/config/deformation_qa.json"),
            Path("unreal/GahyeonStage/GahyeonStageCharacterQA.uproject"),
            Path("unreal/GahyeonStage/Content/Python/gahyeon_character_qa_preflight.py"),
        )
        self.assertTrue(result["valid"])
        self.assertFalse(result["editorRuntimeVerified"])

    def test_automatic_approval_is_rejected(self):
        config = json.loads(Path("character_pipeline/config/deformation_qa.json").read_text())
        config["approvalPolicy"]["automaticApproval"] = True
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(json.dumps(config))
            with self.assertRaisesRegex(ValueError, "never automatically approve"):
                verify(path, Path("unreal/GahyeonStage/GahyeonStageCharacterQA.uproject"),
                       Path("unreal/GahyeonStage/Content/Python/gahyeon_character_qa_preflight.py"))


if __name__ == "__main__":
    unittest.main()
