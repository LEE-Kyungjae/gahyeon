import copy
import json
import subprocess
import unittest
from pathlib import Path

from character_pipeline.tools.run_character_pipeline import run_pipeline, validate_pipeline_run


CONFIG = json.loads(Path("character_pipeline/config/orchestration.json").read_text())


class PipelineRunnerTest(unittest.TestCase):
    def runner(self, responses):
        values = iter(responses)
        def invoke(command, **kwargs):
            code, stdout, stderr = next(values)
            return subprocess.CompletedProcess(command, code, stdout, stderr)
        return invoke

    def test_all_stages_complete_in_order(self):
        config = copy.deepcopy(CONFIG)
        report = run_pipeline(config, Path.cwd(), self.runner([
            (0, "{}", ""), (0, "{}", ""),
            (0, '{"state":"ready"}', ""),
            (0, '{"state":"validated"}', ""),
        ]))
        self.assertEqual(report["state"], "completed")
        self.assertEqual(validate_pipeline_run(config, report)["executedStages"], 4)

    def test_blocked_stage_stops_pipeline(self):
        report = run_pipeline(CONFIG, Path.cwd(), self.runner([
            (0, "{}", ""), (0, "{}", ""),
            (0, '{"state":"blocked"}', ""),
        ]))
        self.assertEqual(report["state"], "blocked")
        self.assertEqual(len(report["stages"]), 3)

    def test_failure_stops_before_later_stages(self):
        report = run_pipeline(CONFIG, Path.cwd(), self.runner([(5, "", "broken")]))
        self.assertEqual(report["state"], "failed")
        self.assertEqual(len(report["stages"]), 1)

    def test_unknown_model_state_fails_closed(self):
        report = run_pipeline(CONFIG, Path.cwd(), self.runner([
            (0, "{}", ""), (0, "{}", ""), (0, '{"state":"magic"}', ""),
        ]))
        self.assertEqual(report["state"], "failed")

    def test_invalid_ordered_report_rejected(self):
        report = {"state": "completed", "displayProfile": "looking-glass-go", "stages": []}
        with self.assertRaisesRegex(ValueError, "omitted"):
            validate_pipeline_run(CONFIG, report)


if __name__ == "__main__":
    unittest.main()
