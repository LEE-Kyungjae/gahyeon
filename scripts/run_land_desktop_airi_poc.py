#!/usr/bin/env python3
"""Build, sync, and launch the current AIRI-style Desktop POC on land Windows."""

from __future__ import annotations

import argparse
import base64
import os
from pathlib import Path
import subprocess


ROOT = Path(__file__).resolve().parents[1]
DESKTOP = ROOT / "desktop"
OUTPUT = DESKTOP / "release-land-x64" / "win-unpacked"
REMOTE_ROOT = "/mnt/c/GahyeonPOC/desktop-airi-current"


def run(command: list[str], *, cwd: Path | None = None, stdin: str | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        input=stdin,
        text=True,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    token = os.environ.get("GAHYEON_CLIENT_TOKEN", "")
    if not token and not args.dry_run:
        raise SystemExit("set GAHYEON_CLIENT_TOKEN in the invoking shell")

    if args.dry_run:
        print("build desktop; package win-x64; sync to land; health-check Core; relaunch Windows app")
        return

    if not args.skip_build:
        print(run(["npm", "run", "build"], cwd=DESKTOP))
        print(run([
            "npx", "electron-builder", "--win", "--x64", "--dir",
            "--config.directories.output=release-land-x64",
        ], cwd=DESKTOP))
    if not (OUTPUT / "Gahyeon.exe").is_file():
        raise SystemExit(f"Windows package is missing: {OUTPUT}")

    run([
        "ssh", "land",
        "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe "
        "-NoProfile -Command \"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "\$Processes = @(Get-Process Gahyeon -ErrorAction SilentlyContinue); "
        "if (\$Processes.Count -gt 0) { \$Processes | Stop-Process -Force }; exit 0\"",
    ])
    run(["ssh", "land", "mkdir", "-p", f"{REMOTE_ROOT}/win-unpacked"])
    print(run([
        "rsync", "-a", "--delete", f"{OUTPUT}/",
        f"land:{REMOTE_ROOT}/win-unpacked/",
    ]))
    run([
        "scp", str(ROOT / "scripts" / "capture_gahyeon_airi_window_v105.ps1"),
        f"land:{REMOTE_ROOT}/launch-and-capture.ps1",
    ])
    land_ip = run(["ssh", "land", "hostname", "-I"]).split()[0]

    encoded_token = base64.b64encode(token.encode()).decode("ascii")
    remote = r'''GAHYEON_CLIENT_TOKEN=$(printf %s 'TOKEN_B64' | base64 -d)
export GAHYEON_CLIENT_TOKEN
export WSLENV="${WSLENV:+$WSLENV:}GAHYEON_CLIENT_TOKEN"
curl -fsS --max-time 5 \
  -H "Authorization: Bearer $GAHYEON_CLIENT_TOKEN" \
  http://127.0.0.1:8080/api/gahyeon/desktop/speech/status
stamp=$(date +%Y%m%d-%H%M%S)
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe \
  -NoProfile -ExecutionPolicy Bypass \
  -File C:\\GahyeonPOC\\desktop-airi-current\\launch-and-capture.ps1 \
  -Executable C:\\GahyeonPOC\\desktop-airi-current\\win-unpacked\\Gahyeon.exe \
  -Screenshot "C:\\GahyeonPOC\\desktop-airi-current\\screen-$stamp.png" \
  -Manifest "C:\\GahyeonPOC\\desktop-airi-current\\manifest-$stamp.json" \
  -CoreApiUrl CORE_URL \
  -UserDataDir "C:\\GahyeonPOC\\desktop-airi-current\\profile-$stamp"
sleep 20
/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -Command \
  'if (-not (Get-Process Gahyeon -ErrorAction SilentlyContinue | Where-Object MainWindowHandle -ne 0)) { exit 1 }'
'''.replace("TOKEN_B64", encoded_token).replace(
        "CORE_URL", f"http://{land_ip}:8080/api",
    )
    print(run(["ssh", "land", "bash", "-s"], stdin=remote))


if __name__ == "__main__":
    main()
