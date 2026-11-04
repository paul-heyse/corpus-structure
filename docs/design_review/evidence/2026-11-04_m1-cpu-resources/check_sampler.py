"""Bounded real-process sampler sanity; no model, source or provider execution."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


def main():
    root = Path(__file__).parent
    child = "import time; data=bytearray(8*1024*1024); end=time.monotonic()+.8\nwhile time.monotonic()<end: pass"
    parent = (
        "import subprocess,sys,time; data=bytearray(8*1024*1024); "
        f"child=subprocess.Popen([sys.executable,'-c',{child!r}]); "
        "time.sleep(.9); child.wait()"
    )
    with tempfile.TemporaryDirectory(prefix="m1-resource-sampler-") as temporary:
        output = Path(temporary) / "tree.jsonl"
        result = subprocess.run([
            sys.executable, str(root / "sample_tree.py"), "--interval", ".1",
            "--out", str(output), "--", sys.executable, "-c", parent,
        ], check=False)
        assert result.returncode == 0
        events = [json.loads(line) for line in output.read_text().splitlines()]
        samples = [event for event in events if event["kind"] == "sample"]
        assert any(event["process_count"] >= 2 for event in samples)
        assert any(event["pss_complete"] and event["pss_kib"] > 0 for event in samples)
        assert any(event["cpu_delta_seconds"] > 0 for event in samples)
        assert all(event["threads"] >= event["process_count"] for event in samples)
        assert events[-2]["kind"] == "summary"
        assert events[-2]["reason"] == "root_exited"
        assert events[-2]["resource_qualification"] == "not_established"
        assert events[-1] == dict(kind="command_exit", returncode=0)
        refused = subprocess.run([
            sys.executable, str(root / "sample_tree.py"), "--out", str(output),
            "--", sys.executable, "-c", "raise SystemExit(99)",
        ], capture_output=True, check=False)
        assert refused.returncode != 0
        assert "FileExistsError" in refused.stderr.decode()
        print(json.dumps(dict(outcome="passed", samples=len(samples),
                              descendant_observed=True, cpu_delta_observed=True,
                              proportional_memory_observed=True, overwrite_refused=True)))


if __name__ == "__main__":
    main()
