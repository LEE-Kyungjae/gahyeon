#!/usr/bin/env python3
"""Split Korean text into speakable sentences.

- Primary splitter: kss.split_sentences
- Fallback: naive punctuation/newline split

Input: stdin (utf-8)
Output: JSON array of strings (utf-8)
"""

import json
import re
import sys


def naive_split(text: str):
    # Keep it simple and predictable.
    parts = re.split(r"(?<=[\.\!\?\u3002\uFF01\uFF1F])\s+|\n+", text)
    out = []
    for p in parts:
        s = (p or "").strip()
        if s:
            out.append(s)
    return out


def main():
    text = sys.stdin.read()
    text = (text or "").strip()

    if not text:
        print("[]")
        return

    try:
        import kss  # type: ignore

        # kss can return list[str]
        parts = kss.split_sentences(text)
        out = [p.strip() for p in parts if p and str(p).strip()]
    except Exception:
        out = naive_split(text)

    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
