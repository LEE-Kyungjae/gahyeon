from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "unreal-runtime.yml"


class UnrealRuntimeWorkflowV091Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.text = WORKFLOW.read_text(encoding="utf-8")

    def test_windows_proof_is_manual_and_self_hosted(self) -> None:
        self.assertIn("run_native_windows:", self.text)
        self.assertIn("github.event_name == 'workflow_dispatch' && inputs.run_native_windows", self.text)
        self.assertIn("runs-on: [self-hosted, Windows, X64, unreal-5.8]", self.text)

    def test_windows_proof_runs_packaged_gate(self) -> None:
        self.assertIn("scripts\\run_desktop_runtime_poc_v091_windows.ps1", self.text)
        self.assertIn("-UnrealRoot", self.text)
        self.assertIn("-EvidenceRoot", self.text)
        self.assertIn("-RunRealtimeAcceptance", self.text)

    def test_windows_evidence_is_always_uploaded(self) -> None:
        self.assertIn("uses: actions/upload-artifact@v4", self.text)
        self.assertIn("if-no-files-found: error", self.text)
        self.assertIn("windows-native-${{ github.run_id }}-${{ github.run_attempt }}", self.text)

    def test_static_contract_job_includes_v091_gate_test(self) -> None:
        self.assertIn("python3 ./scripts/test_run_desktop_runtime_poc_v091_windows.py", self.text)
        self.assertIn("Validate UE 5.8 source scaffold", self.text)


if __name__ == "__main__":
    unittest.main()
