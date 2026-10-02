#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from reconstruction_contract import load, validate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()
    directory = args.candidate.resolve()
    print(json.dumps(validate(load(directory / "candidate.json"), directory, args.verify_files)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

