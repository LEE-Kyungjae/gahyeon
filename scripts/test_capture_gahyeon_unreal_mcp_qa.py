#!/usr/bin/env python3

import importlib.util
import math
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("capture_gahyeon_unreal_mcp_qa.py")
SPEC = importlib.util.spec_from_file_location("capture_gahyeon_unreal_mcp_qa", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class UnrealMcpQaCaptureTest(unittest.TestCase):
    def setUp(self):
        self.bounds = {
            "min": {"x": -50.0, "y": -10.0, "z": 0.0},
            "max": {"x": 50.0, "y": 30.0, "z": 180.0},
            "isValid": True,
        }

    def test_builds_required_unique_views(self):
        views = MODULE.build_views(self.bounds)
        names = [view["name"] for view in views]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(
            names,
            [
                "full_front",
                "full_rear",
                "profile_left",
                "profile_right",
                "three_quarter_left",
                "three_quarter_right",
                "face_front",
            ],
        )

    def test_front_and_rear_look_at_center(self):
        views = {view["name"]: view for view in MODULE.build_views(self.bounds)}
        self.assertAlmostEqual(views["full_front"]["transform"]["rotation"]["yaw"], -90.0)
        self.assertAlmostEqual(views["full_rear"]["transform"]["rotation"]["yaw"], 90.0)

    def test_rotations_are_finite(self):
        for view in MODULE.build_views(self.bounds):
            for value in view["transform"]["rotation"].values():
                self.assertTrue(math.isfinite(value))

    def test_face_camera_is_closer_than_full_body_camera(self):
        views = {view["name"]: view for view in MODULE.build_views(self.bounds)}
        center_y = 10.0
        face_distance = abs(views["face_front"]["transform"]["location"]["y"] - center_y)
        full_distance = abs(views["full_front"]["transform"]["location"]["y"] - center_y)
        self.assertLess(face_distance, full_distance * 0.4)


if __name__ == "__main__":
    unittest.main()
