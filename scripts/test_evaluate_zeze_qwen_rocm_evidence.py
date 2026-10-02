#!/usr/bin/env python3

import unittest

from evaluate_zeze_qwen_rocm_evidence import evaluate_zeze_qwen_rocm_evidence


class EvaluateZezeQwenRocmEvidenceTest(unittest.TestCase):
    def test_blocks_unspecified_launch_failure_and_gpu_reset(self) -> None:
        findings = evaluate_zeze_qwen_rocm_evidence(
            "ROCm error: unspecified launch failure\nCUDA error: unspecified launch failure",
            "GPU reset begin! Source: 3\ndevice wedged, but recovered through reset\n"
            "SystemOOM\nOut of memory: Killed process 423452 (java)",
        )

        self.assertEqual(
            findings,
            [
                "ROCm error: unspecified launch failure",
                "CUDA error: unspecified launch failure",
                "GPU reset begin!",
                "device wedged, but recovered through reset",
                "SystemOOM",
                "Out of memory: Killed process",
            ],
        )

    def test_accepts_clean_success_evidence(self) -> None:
        self.assertEqual(
            evaluate_zeze_qwen_rocm_evidence(
                "Native active backend: ROCm0\nWrote 24000 samples",
                "qualifying requests: 1\ngpu reset count: 0",
            ),
            [],
        )


if __name__ == "__main__":
    unittest.main()
