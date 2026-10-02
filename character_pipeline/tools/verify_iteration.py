#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

from iteration_contract import load, validate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("iteration", type=Path)
    parser.add_argument("--verify-files", action="store_true")
    args = parser.parse_args()
    directory = args.iteration.resolve()
    result = validate(load(directory / "iteration.json"), directory,
                      verify_files=args.verify_files)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

