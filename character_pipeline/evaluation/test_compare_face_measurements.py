import unittest

from character_pipeline.evaluation.compare_face_measurements import compare


class MeasurementCompareTest(unittest.TestCase):
    def test_deltas_are_not_a_similarity_score(self):
        base = {"image": {"uri": "a"}, "measurements": {"mouthWidthOverFaceWidth": 0.25}}
        candidate = {"image": {"uri": "b"}, "measurements": {"mouthWidthOverFaceWidth": 0.30}}
        result = compare(base, candidate, prototype_eyes=False)
        self.assertIsNone(result["identitySimilarityScore"])
        self.assertEqual(20.0, result["deltas"][0]["relativeDeltaPercent"])


if __name__ == "__main__":
    unittest.main()
