#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a standalone sit CLI binary with PyInstaller.")
    parser.add_argument("--dry-run", action="store_true", help="Print the PyInstaller command without running it")
    parser.add_argument("--name", default="sit", help="Binary name")
    parser.add_argument("--dist-dir", default="dist/binary", help="Output directory")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    launcher = root / "build" / "pyinstaller" / "sit_launcher.py"
    command = _pyinstaller_command(root, launcher, name=args.name, dist_dir=args.dist_dir)

    if args.dry_run:
        print(" ".join(command))
        return 0

    if shutil.which("pyinstaller") is None:
        try:
            subprocess.run([sys.executable, "-m", "PyInstaller", "--version"], check=True, capture_output=True, text=True)
        except (FileNotFoundError, subprocess.CalledProcessError) as exc:
            raise SystemExit("PyInstaller is not installed. Run `python3 -m pip install .[binary]` first.") from exc

    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text("from sit.cli import main\nraise SystemExit(main())\n", encoding="utf-8")
    subprocess.run(command, cwd=root, check=True)

    binary = root / args.dist_dir / args.name
    subprocess.run([str(binary), "--version"], cwd=root, check=True)
    print(f"Built binary: {binary}")
    return 0


def _pyinstaller_command(root: Path, launcher: Path, *, name: str, dist_dir: str) -> list[str]:
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--onefile",
        "--clean",
        "--name",
        name,
        "--distpath",
        str(root / dist_dir),
        "--workpath",
        str(root / "build" / "pyinstaller-work"),
        "--specpath",
        str(root / "build" / "pyinstaller"),
        "--hidden-import",
        "yaml",
        "--collect-all",
        "jsonschema",
        str(launcher),
    ]


if __name__ == "__main__":
    raise SystemExit(main())
