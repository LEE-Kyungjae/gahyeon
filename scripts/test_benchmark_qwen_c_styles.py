import importlib.util
import io
import unittest
import wave
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("benchmark_qwen_c_styles.py")
SPEC = importlib.util.spec_from_file_location("gahyeon_qwen_style_benchmark", MODULE_PATH)
benchmark = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(benchmark)


def make_wav(sample_rate: int = 24_000, channels: int = 1) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\0\0" * sample_rate)
    return output.getvalue()


class BenchmarkQwenCStylesTest(unittest.TestCase):
    def test_accepts_expected_pcm_contract(self) -> None:
        metadata = benchmark.inspect_wav(make_wav())
        self.assertEqual(24_000, metadata["sampleRate"])
        self.assertEqual(1.0, metadata["durationSeconds"])

    def test_rejects_wrong_channel_count(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unsupported WAV"):
            benchmark.inspect_wav(make_wav(channels=2))


if __name__ == "__main__":
    unittest.main()
