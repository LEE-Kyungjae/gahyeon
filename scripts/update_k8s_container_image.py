#!/usr/bin/env python3
"""Update exactly one named container image in a Kubernetes workload manifest."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


class ImageUpdateError(ValueError):
    pass


def update_container_image(manifest: str, container_name: str, image: str) -> str:
    lines = manifest.splitlines(keepends=True)
    name_pattern = re.compile(r"^(?P<indent>\s*)-\s+name:\s*" + re.escape(container_name) + r"\s*$")
    image_pattern = re.compile(r"^(?P<indent>\s*)image:\s*\S+\s*$")
    matches: list[int] = []

    for index, line in enumerate(lines):
        name_match = name_pattern.match(line.rstrip("\r\n"))
        if not name_match:
            continue
        item_indent = len(name_match.group("indent"))
        for candidate in range(index + 1, len(lines)):
            stripped = lines[candidate].rstrip("\r\n")
            if stripped.strip() and len(stripped) - len(stripped.lstrip()) <= item_indent:
                break
            image_match = image_pattern.match(stripped)
            if image_match:
                matches.append(candidate)
                break

    if len(matches) != 1:
        raise ImageUpdateError(
            f"expected exactly one image for container {container_name!r}, found {len(matches)}"
        )

    index = matches[0]
    newline = "\r\n" if lines[index].endswith("\r\n") else "\n" if lines[index].endswith("\n") else ""
    indent = re.match(r"^\s*", lines[index]).group(0)
    lines[index] = f"{indent}image: {image}{newline}"
    return "".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--container", required=True)
    parser.add_argument("--image", required=True)
    args = parser.parse_args()

    original = args.file.read_text(encoding="utf-8")
    updated = update_container_image(original, args.container, args.image)
    args.file.write_text(updated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
