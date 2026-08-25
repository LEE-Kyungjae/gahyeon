#!/usr/bin/env python3

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/remote-deploy.sh"


class RemoteDeployKnowledgeMemoryContractTest(unittest.TestCase):
    def test_features_fail_closed_and_every_runtime_value_reaches_the_container(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        for marker in (
            'GAHYEON_ADMIN_ENABLED="${GAHYEON_ADMIN_ENABLED:-false}"',
            'GAHYEON_AUTONOMY_ENABLED="${GAHYEON_AUTONOMY_ENABLED:-false}"',
            'GAHYEON_ADMIN_TOKEN must contain at least 32 characters when admin is enabled',
            'GAHYEON_AUTONOMY_HEARTBEAT_MILLIS must be at least 1000',
            '-e GAHYEON_ADMIN_ENABLED="${GAHYEON_ADMIN_ENABLED}"',
            '-e GAHYEON_ADMIN_TOKEN="${GAHYEON_ADMIN_TOKEN:-}"',
            '-e GAHYEON_AUTONOMY_ENABLED="${GAHYEON_AUTONOMY_ENABLED}"',
            '-e GAHYEON_KNOWLEDGE_EMBEDDING_MODEL="${GAHYEON_KNOWLEDGE_EMBEDDING_MODEL}"',
        ):
            self.assertIn(marker, source)


if __name__ == "__main__":
    unittest.main()
