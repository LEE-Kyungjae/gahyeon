#!/usr/bin/env python3
"""Apply Gahyeon's pinned 0.6B HTTP emotion fix to qwen3-tts-c."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


PINNED_REVISION = "328ab9cb241774572bb59917af199bdf64a17227"
PATCH_RELATIVE_PATH = Path("patches/qwen3-tts-c/328ab9c-http-emotion-06b.patch")


def run_checked(command: list[str], cwd: Path) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def apply_patch(source: Path, repository: Path, check_only: bool) -> None:
    revision = run_checked(["git", "rev-parse", "HEAD"], source)
    if revision != PINNED_REVISION:
        raise SystemExit(
            f"refusing to patch unpinned qwen3-tts-c revision {revision}; "
            f"expected {PINNED_REVISION}"
        )

    patch_path = (repository / PATCH_RELATIVE_PATH).resolve()
    if not patch_path.is_file():
        raise SystemExit(f"patch not found: {patch_path}")

    reverse_check = subprocess.run(
        ["git", "apply", "--reverse", "--check", str(patch_path)],
        cwd=source,
        capture_output=True,
        text=True,
    )
    if reverse_check.returncode == 0:
        print("patch already applied")
        return

    run_checked(["git", "apply", "--check", str(patch_path)], source)
    if check_only:
        print("patch applies cleanly")
        return
    run_checked(["git", "apply", str(patch_path)], source)
    print("patch applied")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path(__file__).resolve().parents[1],
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    apply_patch(args.source.resolve(), args.repository.resolve(), args.check)


if __name__ == "__main__":
    main()
