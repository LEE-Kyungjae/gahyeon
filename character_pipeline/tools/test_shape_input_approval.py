import copy, json, tempfile, unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from character_pipeline.tools.shape_input_approval import digest, validate_approval_request, validate_shape_input_approval

CONFIG=json.loads(Path("character_pipeline/config/shape_input_approval.json").read_text())

class ShapeInputApprovalTest(unittest.TestCase):
    def fixture(self,root):
        derivative=root/"input.png"; derivative.write_bytes(b"rgba")
        matte=root/"matte.json"; matte.write_text(json.dumps({"canonicalIndex":3,"derivative":{"sha256":digest(derivative)}}))
        now=datetime(2026,8,13,tzinfo=timezone.utc)
        return {"schemaVersion":1,"canonicalIndex":3,"scope":"face-shape-only",
                "exclusions":["hair-strand-fidelity","earring-geometry","skin-texture","final-topology"],
                "purpose":"temporary-shape-estimate-for-metahuman-conform","productionMeshAllowed":False,
                "approved":True,"automatic":False,"reviewer":{"name":"owner","role":"character-owner"},
                "approvedAt":now.isoformat(),"expiresAt":(now+timedelta(days=30)).isoformat(),
                "derivative":{"path":str(derivative.resolve()),"sha256":digest(derivative)},
                "matteManifest":{"path":str(matte.resolve()),"sha256":digest(matte)}},now
    def test_valid_scope_bound_fixture(self):
        with tempfile.TemporaryDirectory() as d:
            approval,now=self.fixture(Path(d)); self.assertTrue(validate_shape_input_approval(CONFIG,approval,now)["valid"])
    def test_scope_expansion_and_missing_exclusion_fail(self):
        with tempfile.TemporaryDirectory() as d:
            approval,now=self.fixture(Path(d)); approval["scope"]="body-silhouette-only"
            with self.assertRaisesRegex(ValueError,"scope"): validate_shape_input_approval(CONFIG,approval,now)
            approval,now=self.fixture(Path(d)); approval["exclusions"].pop()
            with self.assertRaisesRegex(ValueError,"exclusions"): validate_shape_input_approval(CONFIG,approval,now)
    def test_expired_automatic_or_tampered_fail(self):
        with tempfile.TemporaryDirectory() as d:
            approval,now=self.fixture(Path(d)); approval["automatic"]=True
            with self.assertRaisesRegex(ValueError,"human approval"): validate_shape_input_approval(CONFIG,approval,now)
            approval,now=self.fixture(Path(d))
            with self.assertRaisesRegex(ValueError,"expired"): validate_shape_input_approval(CONFIG,approval,now+timedelta(days=31))
            approval,now=self.fixture(Path(d)); Path(approval["derivative"]["path"]).write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError,"checksum"): validate_shape_input_approval(CONFIG,approval,now)
    def test_expiry_cannot_exceed_policy(self):
        with tempfile.TemporaryDirectory() as d:
            approval,now=self.fixture(Path(d)); approval["expiresAt"]=(now+timedelta(days=31)).isoformat()
            with self.assertRaisesRegex(ValueError,"expired"): validate_shape_input_approval(CONFIG,approval,now)
    def test_real_unsigned_requests_have_valid_lineage(self):
        for index in (3,16):
            path=Path(f"character_pipeline/reference/canonical/derived/canonical-{index:02d}-shape-approval-request.json")
            result=validate_approval_request(CONFIG,json.loads(path.read_text()))
            self.assertFalse(result["approved"])

if __name__=="__main__": unittest.main()
