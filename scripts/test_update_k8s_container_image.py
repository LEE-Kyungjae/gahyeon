#!/usr/bin/env python3

import unittest

from update_k8s_container_image import ImageUpdateError, update_container_image


class UpdateK8sContainerImageTest(unittest.TestCase):
    def test_updates_core_by_name_without_touching_first_sidecar(self) -> None:
        manifest = """containers:
  - name: edge-tts
    image: ghcr.io/example/gahyeonbot:old-sidecar
  - name: gahyeonbot
    image: ghcr.io/example/gahyeonbot@sha256:old-core
"""

        updated = update_container_image(
            manifest, "gahyeonbot", "ghcr.io/example/gahyeonbot:sha-new"
        )

        self.assertIn("image: ghcr.io/example/gahyeonbot:old-sidecar", updated)
        self.assertIn("image: ghcr.io/example/gahyeonbot:sha-new", updated)
        self.assertNotIn("sha256:old-core", updated)

    def test_fails_closed_for_missing_or_duplicate_named_container(self) -> None:
        with self.assertRaises(ImageUpdateError):
            update_container_image("containers: []\n", "gahyeonbot", "example:new")
        duplicate = """containers:
  - name: gahyeonbot
    image: example:one
  - name: gahyeonbot
    image: example:two
"""
        with self.assertRaises(ImageUpdateError):
            update_container_image(duplicate, "gahyeonbot", "example:new")


if __name__ == "__main__":
    unittest.main()
