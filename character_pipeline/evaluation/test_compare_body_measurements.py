import unittest

from character_pipeline.evaluation.compare_body_measurements import compare


class BodyMeasurementCompareTest(unittest.TestCase):
    def test_never_emits_body_score(self):
        reference = {"measurements": {"torsoLengthOverSilhouetteHeight": 0.25}}
        candidate = {"measurements": {"torsoLengthOverSilhouetteHeight": 0.275}}
        result = compare(reference, candidate)
        self.assertIsNone(result["bodySimilarityScore"])
        self.assertEqual(10.0, result["deltas"][0]["relativeDeltaPercent"])


if __name__ == "__main__":
    unittest.main()
