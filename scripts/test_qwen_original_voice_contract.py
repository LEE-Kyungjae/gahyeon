#!/usr/bin/env python3
"""Deterministic regression contract for the approved original-voice rollout."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/qwen-original-voice-v116-production.json"


class QwenOriginalVoiceContractTest(unittest.TestCase):
    def test_approved_original_voice_cannot_regress_to_named_female_or_short_output(self) -> None:
        payload = json.loads(CONTRACT.read_text(encoding="utf-8"))
        identity = payload["speakerIdentity"]
        generation = payload["generation"]

        self.assertEqual(payload["voiceProfile"], "gahyeon.assistant")
        self.assertEqual(payload["modelId"], "Qwen/Qwen3-TTS-12Hz-1.7B-Base")
        self.assertEqual(payload["productionHost"], "land")
        self.assertEqual(payload["coreHost"], "zeze")
        self.assertEqual(payload["endpoint"], "http://10.42.0.1:18773/v1/speech")
        self.assertEqual(payload["quantization"], "c-int4-cuda-sm75-mixed")
        self.assertEqual(identity["mode"], "x-vector-only")
        self.assertTrue(identity["usesOriginalRecordingsOnly"])
        self.assertEqual(identity["dimensions"], 2048)
        self.assertRegex(identity["canonicalJsonSha256"], r"^[0-9a-f]{64}$")
        self.assertGreaterEqual(generation["maximumMaxTokens"], 192)
        self.assertGreaterEqual(generation["completeSentenceFixtureMinimumSeconds"], 5.0)
        self.assertEqual(payload["forbidden"]["namedSpeaker"], "Sohee")
        self.assertEqual(payload["forbidden"]["endpoint"],
                         "http://10.42.0.1:18771/v1/speech")
        self.assertEqual(payload["forbidden"]["quantization"],
                         "Q4_K_M-vulkan-radv-xvector-v116")


if __name__ == "__main__":
    unittest.main()
