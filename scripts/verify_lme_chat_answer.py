#!/usr/bin/env python3
"""Narrow, offline acceptance check for a captured LME chat answer, not a truth oracle."""
import json
import re
import sys
from pathlib import Path


def validate_answer(answer, expected):
    normalized = answer.replace('‑', '-').replace('–', '-').replace(',', '')
    required = [expected['date'], expected['source'], 'USD', '톤']
    required += [f"{expected[key]:.2f}" for key in ('cash', 'threeMonth', 'cashDelta', 'threeMonthDelta')]
    missing = [value for value in required if value not in normalized]
    if not re.search(r'현금|Cash', normalized, re.I):
        missing.append('cash label')
    if not re.search(r'3개월|3.Month', normalized, re.I):
        missing.append('three-month label')
    return missing


if __name__ == '__main__':
    missing = validate_answer(Path(sys.argv[1]).read_text(), json.loads(Path(sys.argv[2]).read_text()))
    print(json.dumps({'passed': not missing, 'missing': missing}, ensure_ascii=False))
    sys.exit(bool(missing))
