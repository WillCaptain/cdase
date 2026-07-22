#!/usr/bin/env python3
"""Packaging contract for the cross-platform `cdase` command."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))


class PackageEntrypointTests(unittest.TestCase):
    def test_console_entrypoint_targets_client_main(self):
        config = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('cdase = "cdase.scripts.cdase_client:main"', config)
        from cdase.scripts.cdase_client import main

        self.assertTrue(callable(main))

    def test_wheel_installs_console_script_and_packaged_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            source = tmp_path / "source"
            source.mkdir()
            shutil.copy2(REPO_ROOT / "pyproject.toml", source / "pyproject.toml")
            shutil.copy2(REPO_ROOT / "README.md", source / "README.md")
            shutil.copytree(REPO_ROOT / "cdase", source / "cdase")
            wheel_dir = tmp_path / "wheel"
            wheel_dir.mkdir()
            subprocess.run(
                [
                    sys.executable, "-m", "pip", "wheel", "--no-deps",
                    "--no-build-isolation", "--wheel-dir", str(wheel_dir), str(source),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            venv = tmp_path / "venv"
            subprocess.run([sys.executable, "-m", "venv", str(venv)], check=True)
            python = venv / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            wheel = next(wheel_dir.glob("cdase-*.whl"))
            subprocess.run(
                [str(python), "-m", "pip", "install", "--no-deps", str(wheel)],
                check=True,
                capture_output=True,
                text=True,
            )
            command = venv / ("Scripts/cdase.exe" if os.name == "nt" else "bin/cdase")
            app = tmp_path / "app"
            (app / ".git").mkdir(parents=True)
            global_dir = tmp_path / "global"
            env = {
                **os.environ,
                "CDASE_ROOT": str(app / "cdase"),
                "CDASE_GLOBAL": str(global_dir),
            }
            help_result = subprocess.run(
                [str(command), "--help"], cwd=tmp_path, env=env,
                capture_output=True, text=True,
            )
            self.assertEqual(help_result.returncode, 0, help_result.stderr)
            init_result = subprocess.run(
                [str(command), "init-global-setting"], cwd=tmp_path, env=env,
                capture_output=True, text=True,
            )
            self.assertEqual(init_result.returncode, 0, init_result.stderr)
            self.assertTrue((global_dir / "setting.context.md").is_file())


if __name__ == "__main__":
    unittest.main()
