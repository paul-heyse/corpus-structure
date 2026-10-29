"""pytest 9.2.0 / Hypothesis 6.170.12 route-classification probe; no database, no network.

Questions:
  1. Does built-in JUnit XML record per-test outcomes with skip reasons and Hypothesis
     failure detail (reproduction blob) faithfully enough for outcome accounting?
  2. Does `--hypothesis-profile=ci` override a conftest that loads a profile from an
     environment default at import?
  3. With only built-in `faulthandler_timeout` + `faulthandler_exit_on_timeout`, what does
     a hung test leave behind (exit code, traceback, JUnit file)?

Run from the repository root:
  uv run --no-sync python docs/design_review/evidence/2026-10-29_library-leverage-postgres-migrations/pytest_route_probe.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import xml.etree.ElementTree as ET
from importlib.metadata import version
from pathlib import Path

HERE = Path(__file__).resolve().parent
CASES = HERE / "pytest_cases"
RAW = HERE / "raw"


def run(name: str, args: list[str]) -> int:
    env = {k: v for k, v in os.environ.items() if k != "HYPOTHESIS_PROFILE"}
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", *args],
        cwd=CASES,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    (RAW / f"{name}.stdout.txt").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr)
    print(f"[{name}] exit code {proc.returncode}")
    return proc.returncode


def junit(path: Path) -> None:
    if not path.exists():
        print(f"  junit file {path.name}: absent")
        return
    root = ET.parse(path).getroot()
    for case in root.iter("testcase"):
        kinds = [c.tag for c in case if c.tag in {"failure", "error", "skipped"}]
        detail = ""
        for c in case:
            if c.tag in {"failure", "skipped"}:
                text = (c.get("message") or "") + " " + (c.text or "")
                detail = " | ".join(
                    s.strip() for s in text.splitlines() if "reproduce_failure" in s or "blocked" in s
                )[:160]
        print(f"  {case.get('name')}: {kinds or ['passed']} {detail}")
    props = [p.get("name") for p in root.iter("property")]
    print(f"  global properties: {len(props)} (first: {props[:1]})")


def main() -> int:
    print("pytest", version("pytest"), "hypothesis", version("hypothesis"), sys.version.split()[0])
    RAW.mkdir(exist_ok=True)
    for stale in RAW.glob("junit_*.xml"):
        stale.unlink()
    j1 = RAW / "junit_profile_ci.xml"
    run(
        "profile_ci",
        ["-c", "probe.ini", "outcomes", "-rA", "--hypothesis-profile=ci", f"--junitxml={j1}"],
    )
    junit(j1)
    j2 = RAW / "junit_profile_default.xml"
    run("profile_default", ["-c", "probe.ini", "outcomes", "-rs", f"--junitxml={j2}"])
    junit(j2)
    j3 = RAW / "junit_hang.xml"
    run("hang_faulthandler_exit", ["-c", "hang.ini", "hang", "-v", f"--junitxml={j3}"])
    junit(j3)
    out = (RAW / "hang_faulthandler_exit.stdout.txt").read_text()
    print("  hang traceback names test_hangs:", "test_hangs" in out)
    print("  test_after reported:", "test_after" in out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
