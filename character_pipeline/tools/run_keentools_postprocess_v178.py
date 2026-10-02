#!/usr/bin/env python3
"""Run the sealed v178 KeenTools result through the common QA pipeline."""

from __future__ import annotations

import run_keentools_postprocess_v175 as runner


runner.ITERATION_LABEL = "v178"
runner.ITERATION = (
    runner.WORKSPACE / "artifacts/gahyeon-ch/iterations/v178-keentools-cloud-equal-shape"
)
runner.MODEL = runner.ITERATION / "gahyeon-keentools-cloud-v178.glb"


if __name__ == "__main__":
    try:
        raise SystemExit(runner.main_v175())
    except (RuntimeError, runner.subprocess.CalledProcessError) as error:
        raise SystemExit(f"ERROR: {error}")
