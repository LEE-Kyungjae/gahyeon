#!/usr/bin/env python3
"""Run the v175 Cloud client with four equal-size Golden Identity views."""

from __future__ import annotations

import keentools_cloud_candidate_v175 as client


client.ITERATION = "v178"
client.OUTPUT_ROOT = (
    client.SOURCE_ROOT / "iterations/v178-keentools-cloud-equal-shape"
)
client.INPUTS = client.INPUTS[:4]


if __name__ == "__main__":
    try:
        raise SystemExit(client.main_v175())
    except RuntimeError as error:
        print(f"ERROR: {error}", file=client.sys.stderr)
        raise SystemExit(2)
