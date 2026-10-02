import ast
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("benchmark_qwen_voice_backbone_land.py")


class BenchmarkQwenVoiceBackboneLandTest(unittest.TestCase):
    def test_records_fail_closed_identity_and_expression_limit(self):
        source = SCRIPT.read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn('"expressionControl": False', source)
        self.assertIn('choices=("float16", "float32"), default="float32"', source)
        self.assertIn('"quantization": f"none-{args.dtype}"', source)
        self.assertIn('"referenceSha256": sha256(args.reference)', source)
        self.assertIn('torch.cuda.max_memory_allocated()', source)
        self.assertIn('dtype=torch.float32 if args.dtype == "float32" else torch.float16', source)
        self.assertNotIn('do_sample=False', source)
        self.assertIn('os.replace(temporary, output)', source)

    def test_keeps_korean_and_github_english_in_the_same_runtime(self):
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('("ko-short", "Korean"', source)
        self.assertIn('("ko-expression-text", "Korean"', source)
        self.assertIn('("en-github", "English"', source)
        self.assertIn("GitHub repository", source)


if __name__ == "__main__":
    unittest.main()
