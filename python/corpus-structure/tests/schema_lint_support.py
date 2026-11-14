"""The pinned LinkML CLI's process and JSON-report contract."""

import json
import shutil
import subprocess
from pathlib import Path


def report_errors(
    result: subprocess.CompletedProcess[str], *, expected_returncode: int = 0
) -> list[str]:
    assert result.returncode == expected_returncode, (
        result.returncode,
        result.stdout,
        result.stderr,
    )
    problems = json.loads(result.stdout)
    assert isinstance(problems, list), problems
    assert all(
        isinstance(p, dict)
        and p.get("level") in {"warning", "error"}
        and isinstance(p.get("message"), str)
        for p in problems
    ), problems
    errors = [p["message"] for p in problems if p["level"] == "error"]
    assert bool(errors) == (expected_returncode == 2), problems
    return errors


def lint_errors(path: Path, config: Path, *, expected_returncode: int = 0) -> list[str]:
    executable = shutil.which("linkml-lint")
    assert executable is not None, "blocked: linkml-lint missing"
    result = subprocess.run(
        [executable, "--ignore-warnings", "--format", "json", "--config", str(config), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return report_errors(result, expected_returncode=expected_returncode)
