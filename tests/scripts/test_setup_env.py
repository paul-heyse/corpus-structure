"""Checkout preparation cannot target an inherited provider environment."""

import json
import os
import shutil
import subprocess
from pathlib import Path


def test_setup_selects_checkout_environment(tmp_path: Path) -> None:
    checkout = tmp_path / "checkout with spaces"
    scripts = checkout / "scripts"
    scripts.mkdir(parents=True)
    source = Path(__file__).resolve().parents[2] / "scripts/setup-env"
    shutil.copyfile(source, scripts / "setup-env")
    tools = tmp_path / "bin"
    tools.mkdir()
    uv = tools / "uv"
    uv.write_text(
        "#!/usr/bin/python3\nimport json,os,sys\n"
        'print(json.dumps({"args":sys.argv[1:],"cwd":os.getcwd(),'
        '"prefix":os.environ["UV_PROJECT_ENVIRONMENT"],'
        '"foreign":{k:os.environ[k] for k in ("UV_NO_SYNC","UV_PYTHON",'
        '"UV_PROJECT","UV_WORKING_DIR","UV_NO_PROJECT","VIRTUAL_ENV") if k in os.environ}}))\n'
        'sys.exit(int(os.environ.get("SETUP_TEST_EXIT","0")))\n'
    )
    uv.chmod(0o755)
    env = {
        **os.environ,
        "PATH": str(tools) + ":/usr/bin:/bin",
        "VIRTUAL_ENV": "/foreign",
        "UV_PROJECT_ENVIRONMENT": "/foreign",
        "UV_NO_SYNC": "1",
        "UV_PYTHON": "3.9",
        "UV_PROJECT": "/foreign",
        "UV_WORKING_DIR": "/foreign",
        "UV_NO_PROJECT": "1",
    }
    env.pop("BASH_ENV", None)
    for status in (0, 23):
        result = subprocess.run(
            ["bash", str(scripts / "setup-env")],
            cwd=tmp_path,
            env={**env, "SETUP_TEST_EXIT": str(status)},
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == status, result.stderr
        call = json.loads(result.stdout)
        assert call["cwd"] == str(checkout)
        assert call["prefix"] == str(checkout / ".venv")
        assert call["foreign"] == {}
        assert call["args"] == ["sync", "--locked", "--inexact"]
    result = subprocess.run(
        ["bash", str(scripts / "setup-env"), "invalid"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert result.stdout == ""
