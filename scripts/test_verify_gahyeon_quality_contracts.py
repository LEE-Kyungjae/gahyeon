#!/usr/bin/env python3

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import verify_gahyeon_quality_contracts as contract


class QualityContractConsistencyTest(unittest.TestCase):
    def test_current_contracts_are_consistent(self):
        result = contract.verify()
        self.assertEqual([15, 21, 23, 27, 21],
                         [item["requiredViews"] for item in result["gates"]])
        self.assertEqual(2, result["gates"][-1]["optionalViews"])

    def test_schema_verifier_view_drift_is_rejected(self):
        original = json.loads(
            (contract.ROOT / "docs/contracts/gahyeon-g1-review.schema.json").read_text())
        changed = copy.deepcopy(original)
        changed["properties"]["evidence"]["items"]["properties"]["view"]["enum"].pop()
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            path = root / "docs/contracts"
            path.mkdir(parents=True)
            for gate in range(1, 6):
                source = contract.ROOT / f"docs/contracts/gahyeon-g{gate}-review.schema.json"
                payload = changed if gate == 1 else json.loads(source.read_text())
                (path / source.name).write_text(json.dumps(payload))
            hero = contract.ROOT / "docs/contracts/gahyeon-hero-asset.schema.json"
            (path / hero.name).write_bytes(hero.read_bytes())
            with mock.patch.object(contract, "ROOT", root):
                with self.assertRaisesRegex(ValueError, "schema/verifier evidence drift"):
                    contract.verify()


if __name__ == "__main__":
    unittest.main()
