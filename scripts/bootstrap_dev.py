"""Install the project's pinned uv version and sync the development environment."""

from pathlib import Path
import subprocess
import sys
import tomllib


root = Path(__file__).resolve().parents[1]
settings = tomllib.loads((root / "pyproject.toml").read_text())
subprocess.run([sys.executable, "-m", "pip", "install",
                "uv" + settings["tool"]["uv"]["required-version"]], check=True)
subprocess.run(["uv", "sync", "--locked"], cwd=root, check=True)
