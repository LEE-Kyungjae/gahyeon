import importlib.util
import io
import json
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("server.py")


class FakeFastAPI:
    def __init__(self, **_):
        pass

    def get(self, *_args, **_kwargs):
        return lambda function: function

    post = get


class FakeResponse:
    def __init__(self, content=b"", media_type=None, headers=None):
        self.content = content
        self.media_type = media_type
        self.headers = headers or {}


fastapi = types.ModuleType("fastapi")
fastapi.FastAPI = FakeFastAPI
fastapi.Header = lambda default=None: default
fastapi.HTTPException = type("HTTPException", (Exception,), {})
responses = types.ModuleType("fastapi.responses")
responses.Response = FakeResponse
soundfile = types.ModuleType("soundfile")


def write_wav(target, samples, sample_rate, format=None, subtype=None):
    del format, subtype
    with wave.open(target, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(b"\0\0" * len(samples))


soundfile.write = write_wav
torch = types.ModuleType("torch")
torch.float16 = "float16"
torch.float32 = "float32"
sys.modules.setdefault("fastapi", fastapi)
sys.modules.setdefault("fastapi.responses", responses)
sys.modules.setdefault("soundfile", soundfile)
sys.modules.setdefault("torch", torch)
SPEC = importlib.util.spec_from_file_location("gahyeon_qwen_server", MODULE_PATH)
server = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(server)


class FakeModel:
    def generate_voice_clone(self, **kwargs):
        import numpy as np
        self.kwargs = kwargs
        return [np.zeros(240, dtype=np.float32)], 24_000


class QwenServerTest(unittest.TestCase):
    def request(self, style="natural"):
        return server.SynthesisRequest(
            text="안녕", voiceProfile="gahyeon.assistant", style=style,
            intensity=0.3, communicativeIntent="conversation",
            modelId="Qwen/base", quantization="none-float32", responseFormat="wav",
        )

    def test_voice_clone_profile_is_identity_attested_and_cannot_claim_expression(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            audio = root / "reference.wav"
            audio.write_bytes(b"reference")
            config = root / "profiles.json"
            config.write_text(json.dumps({"gahyeon.assistant": {
                "mode": "voice_clone", "referenceAudio": str(audio),
                "referenceText": "안녕하세요.", "language": "Korean",
                "expressionControl": False,
            }}), encoding="utf-8")
            loaded = server.load_profiles(config)
            self.assertEqual(64, len(loaded["gahyeon.assistant"]["referenceSha256"]))

            payload = json.loads(config.read_text(encoding="utf-8"))
            payload["gahyeon.assistant"]["expressionControl"] = True
            config.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "cannot claim"):
                server.load_profiles(config)

    def test_natural_voice_clone_generates_pcm_wav(self):
        fake = FakeModel()
        profile = {
            "mode": "voice_clone", "referenceAudio": "/reference.wav",
            "referenceText": "안녕하세요.", "language": "Korean",
            "expressionControl": False,
        }
        with patch.object(server, "model", fake):
            payload = server.synthesize_audio(self.request(), profile)
        self.assertEqual(b"RIFF", payload[:4])
        self.assertEqual("안녕", fake.kwargs["text"])

    def test_voice_clone_rejects_fake_expression_instead_of_ignoring_it(self):
        profile = {"mode": "voice_clone", "expressionControl": False}
        with patch.object(server, "model", FakeModel()):
            with self.assertRaisesRegex(ValueError, "does not support"):
                server.synthesize_audio(self.request("fake_cute"), profile)

    def test_expression_instruction_is_bounded_to_known_styles(self):
        self.assertIn("Intensity: 0.75", server.expression_instruction("playful", 0.75, "teasing"))
        with self.assertRaisesRegex(ValueError, "unsupported"):
            server.expression_instruction("arbitrary_prompt", 1.0, "unsafe")


if __name__ == "__main__":
    unittest.main()
