#!/usr/bin/env python3
"""Install and validate Looking Glass Bridge on the canonical macOS host."""

from __future__ import annotations

import argparse
import plistlib
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_URL = "https://lookingglassfactory.com/software/looking-glass-bridge"
APPLICATIONS = Path("/Applications")
BRIDGE_PATTERNS = ("Looking Glass Bridge*.app", "LookingGlassBridge*.app")
INSTALLER_PATTERNS = (
    "*Looking*Glass*Bridge*.dmg",
    "*LookingGlassBridge*.dmg",
    "*Looking*Glass*Bridge*.pkg",
    "*LookingGlassBridge*.pkg",
)


class SetupError(RuntimeError):
    pass


def find_bridge_app(applications: Path = APPLICATIONS) -> Path | None:
    matches = [path for pattern in BRIDGE_PATTERNS for path in applications.glob(pattern)]
    return sorted(matches)[-1] if matches else None


def find_installer(download_dir: Path) -> Path | None:
    matches = [path for pattern in INSTALLER_PATTERNS for path in download_dir.glob(pattern)]
    files = [path for path in matches if path.is_file() and not path.name.endswith(".download")]
    return max(files, key=lambda path: path.stat().st_mtime) if files else None


def wait_for_installer(download_dir: Path, timeout: int, poll_interval: float = 2.0) -> Path:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        installer = find_installer(download_dir)
        if installer:
            return installer
        time.sleep(poll_interval)
    raise SetupError(
        f"Bridge installer was not downloaded within {timeout}s; download it from {DOWNLOAD_URL}"
    )


def install_dmg(installer: Path, applications: Path = APPLICATIONS) -> Path:
    attached = subprocess.run(
        ["hdiutil", "attach", "-nobrowse", "-readonly", "-plist", str(installer)],
        check=True,
        capture_output=True,
    )
    payload = plistlib.loads(attached.stdout)
    mount_points = [
        Path(entity["mount-point"])
        for entity in payload.get("system-entities", [])
        if entity.get("mount-point")
    ]
    if not mount_points:
        raise SetupError("Bridge disk image mounted without a volume")
    mount = mount_points[-1]
    try:
        candidates = [path for pattern in BRIDGE_PATTERNS for path in mount.glob(pattern)]
        if not candidates:
            raise SetupError("Bridge application is missing from the downloaded disk image")
        source = sorted(candidates)[-1]
        destination = applications / source.name
        subprocess.run(["ditto", str(source), str(destination)], check=True)
        return destination
    finally:
        subprocess.run(["hdiutil", "detach", str(mount)], check=False)


def install_pkg(installer: Path) -> None:
    command = ["/usr/sbin/installer", "-pkg", str(installer), "-target", "/"]
    if hasattr(__import__("os"), "geteuid") and __import__("os").geteuid() != 0:
        command.insert(0, "sudo")
    subprocess.run(command, check=True)


def install_bridge(installer: Path, applications: Path = APPLICATIONS) -> Path:
    if installer.suffix.lower() == ".dmg":
        return install_dmg(installer, applications)
    if installer.suffix.lower() == ".pkg":
        install_pkg(installer)
        app = find_bridge_app(applications)
        if app:
            return app
        raise SetupError("Bridge package completed but its application was not found")
    raise SetupError(f"unsupported Bridge installer: {installer}")


def launch_bridge(app: Path, timeout: int = 30) -> None:
    subprocess.run(["open", str(app)], check=True)
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = subprocess.run(
            ["pgrep", "-if", "Looking Glass Bridge|LookingGlassBridge"],
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            return
        time.sleep(1)
    raise SetupError("Looking Glass Bridge did not stay running after launch")


def display_report() -> str:
    result = subprocess.run(
        ["system_profiler", "SPDisplaysDataType"], text=True, capture_output=True, check=True
    )
    return result.stdout


def validate_go_display(report: str) -> None:
    if "1440 x 2560" not in report and "2560 x 1440" not in report:
        raise SetupError(
            "Looking Glass Go is not exposed at its 1440x2560 desktop resolution. "
            "Use Desktop Mode and connect both display and USB data paths."
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, help="existing official Bridge .dmg or .pkg")
    parser.add_argument("--download-dir", type=Path, default=Path.home() / "Downloads")
    parser.add_argument("--download-timeout", type=int, default=1800)
    parser.add_argument("--no-open-download", action="store_true")
    parser.add_argument("--skip-display-check", action="store_true")
    parser.add_argument("--launch-gahyeon", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if platform.system() != "Darwin":
        raise SetupError("this one-stop installer supports macOS only")

    app = find_bridge_app()
    if not app:
        installer = args.installer or find_installer(args.download_dir)
        if not installer:
            if not args.no_open_download:
                print("Opening the official Bridge download. Complete the vendor login once.")
                subprocess.run(["open", DOWNLOAD_URL], check=True)
            installer = wait_for_installer(args.download_dir, args.download_timeout)
        print(f"Installing official Bridge from {installer}")
        app = install_bridge(installer)

    launch_bridge(app)
    if not args.skip_display_check:
        validate_go_display(display_report())
    print(f"Looking Glass Bridge ready: {app}")

    if args.launch_gahyeon:
        subprocess.run([sys.executable, str(ROOT / "scripts/launch_canonical_macos_runtime.py")], check=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (SetupError, subprocess.CalledProcessError) as error:
        print(f"LOOKING_GLASS_SETUP_FAILED: {error}", file=sys.stderr)
        raise SystemExit(2)
