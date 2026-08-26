import importlib.util
import io
import json
import struct
import sys
import tempfile
import types
import unittest
import wave
from pathlib import Path
from unittest.mock import patch


class FakeFastAPI:
    def __init__(self, **_): pass
    def get(self, *_args, **_kwargs): return lambda function: function
    post = get


class FakeResponse:
    def __init__(self, content=b"", media_type=None, headers=None):
        self.content, self.media_type, self.headers = content, media_type, headers or {}


class FakeStreamingResponse(FakeResponse):
    def __init__(self, content, media_type=None, headers=None):
        super().__init__(content, media_type, headers)


fastapi = types.ModuleType("fastapi")
fastapi.FastAPI = FakeFastAPI
fastapi.Header = lambda default=None: default
fastapi.HTTPException = type("HTTPException", (Exception,), {})
responses = types.ModuleType("fastapi.responses")
responses.Response = FakeResponse
responses.StreamingResponse = FakeStreamingResponse
sys.modules.setdefault("fastapi", fastapi)
sys.modules.setdefault("fastapi.responses", responses)

path = Path(__file__).with_name("c_runtime_bridge.py")
spec = importlib.util.spec_from_file_location("gahyeon_c_runtime_bridge", path)
bridge = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(bridge)


def wav() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1); target.setsampwidth(2); target.setframerate(24_000)
        target.writeframes(b"\0\0" * 240)
    return output.getvalue()


class FakeUrlResponse:
    status = 200
    headers = {"Content-Type": "audio/pcm", "X-Sample-Rate": "24000",
               "X-Sample-Format": "s16le", "X-Channels": "1"}
    def __init__(self, content=None): self.content = wav() if content is None else content
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def close(self): pass
    def read(self, count):
        result, self.content = self.content[:count], self.content[count:]
        return result


class CRuntimeBridgeTest(unittest.TestCase):
    def profile(self):
        return {"backendUrl": "http://127.0.0.1:18771/v1/tts", "language": "Korean",
                "seed": 7, "minimumEmotionStrength": 0.15, "maximumEmotionStrength": 0.35,
                "styles": {"natural": None, "bright": "joy"}}

    def request(self, style="natural", intensity=0.3):
        return bridge.SynthesisRequest(text="안녕", voiceProfile="gahyeon.assistant", style=style,
            intensity=intensity, communicativeIntent="conversation",
            modelId=bridge.MODEL_ID, quantization=bridge.QUANTIZATION, responseFormat="wav")

    def test_profile_requires_loopback_and_explicit_natural_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "profiles.json"
            config.write_text(json.dumps({"gahyeon.assistant": self.profile()}), encoding="utf-8")
            self.assertIn("gahyeon.assistant", bridge.load_profiles(config))
            bad = self.profile(); bad["backendUrl"] = "http://external.example/v1/tts"
            config.write_text(json.dumps({"bad": bad}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "loopback"):
                bridge.load_profiles(config)

    def test_maps_validated_emotion_and_scales_it_with_a_consumed_instruction(self):
        captured = {}
        def open_request(request, timeout):
            captured.update(json.loads(request.data)); self.assertEqual(bridge.TIMEOUT_SECONDS, timeout)
            return FakeUrlResponse()
        with patch.object(bridge.urllib.request, "urlopen", open_request):
            audio = bridge.backend_request(self.request("bright", 0.75), self.profile())
        self.assertEqual(b"RIFF", audio[:4])
        self.assertEqual("joy", captured["emotion"])
        self.assertNotIn("emotion_strength", captured)
        self.assertIn("joy", captured["instruct"])
        self.assertIn("strong and unmistakable", captured["instruct"])

    def test_rejects_unvalidated_fake_cute_instead_of_approximating_it(self):
        with self.assertRaisesRegex(ValueError, "no validated mapping"):
            bridge.backend_request(self.request("fake_cute"), self.profile())

    def test_maps_validated_instruct_style_and_scales_instruction_strength(self):
        profile = self.profile()
        profile["styles"]["fake_cute"] = {
            "instruct": "Speak in a deliberately cute and playful voice.",
            "rate": 0.95,
        }
        captured = {}
        def open_request(request, timeout):
            self.assertEqual(bridge.TIMEOUT_SECONDS, timeout)
            captured.update(json.loads(request.data))
            return FakeUrlResponse()
        with patch.object(bridge.urllib.request, "urlopen", open_request):
            bridge.backend_request(self.request("fake_cute", 0.8), profile)
        self.assertEqual(0.95, captured["rate"])
        self.assertIn("deliberately cute", captured["instruct"])
        self.assertIn("strong and unmistakable", captured["instruct"])
        self.assertNotIn("emotion", captured)

    def test_streams_only_attested_mono_pcm_and_releases_slot(self):
        profile = self.profile()
        profile["styles"]["fake_cute"] = {"instruct": "Speak playfully."}
        raw = b"\0\0" * 7_200
        captured = {}
        def open_request(request, timeout):
            captured["url"] = request.full_url
            captured["payload"] = json.loads(request.data)
            self.assertEqual(bridge.TIMEOUT_SECONDS, timeout)
            return FakeUrlResponse(raw)
        bridge.SYNTHESIS_SLOT.acquire()
        with patch.object(bridge.urllib.request, "urlopen", open_request):
            stream = bridge.backend_stream(self.request("fake_cute", 0.8), profile)
            self.assertEqual(raw, b"".join(stream))
        self.assertTrue(bridge.SYNTHESIS_SLOT.acquire(timeout=0.01))
        bridge.SYNTHESIS_SLOT.release()
        self.assertEqual("http://127.0.0.1:18771/v1/tts/stream", captured["url"])
        self.assertIn("Speak playfully", captured["payload"]["instruct"])

    def test_profile_rejects_unknown_instruct_controls(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "profiles.json"
            profile = self.profile()
            profile["styles"]["bad"] = {"instruct": "Speak brightly.", "shell": "unsafe"}
            config.write_text(json.dumps({"gahyeon.assistant": profile}), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "unsupported"):
                bridge.load_profiles(config)

    def test_applies_style_output_gain_to_wav_without_overflow(self):
        profile = self.profile()
        profile["styles"]["concerned"] = {
            "instruct": "Speak with attentive concern.", "outputGain": 3.72,
        }
        source = io.BytesIO()
        with wave.open(source, "wb") as target:
            target.setnchannels(1); target.setsampwidth(2); target.setframerate(24_000)
            target.writeframes(struct.pack("<3h", 1000, 10_000, -10_000))
        with patch.object(bridge.urllib.request, "urlopen",
                          lambda request, timeout: FakeUrlResponse(source.getvalue())):
            audio = bridge.backend_request(self.request("concerned"), profile)
        with wave.open(io.BytesIO(audio), "rb") as result:
            self.assertEqual((3720, 32767, -32768),
                             struct.unpack("<3h", result.readframes(3)))

    def test_stream_applies_only_the_selected_style_output_gain(self):
        profile = self.profile()
        profile["styles"]["concerned"] = {
            "instruct": "Speak with attentive concern.", "outputGain": 2,
        }
        raw = struct.pack("<2h", 1000, -1000)
        bridge.SYNTHESIS_SLOT.acquire()
        with patch.object(bridge.urllib.request, "urlopen",
                          lambda request, timeout: FakeUrlResponse(raw)):
            stream = bridge.backend_stream(self.request("concerned"), profile)
            self.assertEqual((2000, -2000), struct.unpack("<2h", b"".join(stream)))

    def test_land_v115_profile_exposes_the_full_expression_palette(self):
        config = Path(__file__).parents[3] / "config" / "qwen-c-runtime-profiles-land-v115.json"
        profile = bridge.load_profiles(config)["gahyeon.assistant"]
        self.assertEqual(
            {"natural", "warm", "gentle", "bright", "surprised", "concerned", "serious",
             "playful", "fake_cute", "sarcastic", "sleepy", "whisper", "excited",
             "annoyed", "sad", "suppressed_laugh"},
            set(profile["styles"]),
        )


if __name__ == "__main__": unittest.main()
