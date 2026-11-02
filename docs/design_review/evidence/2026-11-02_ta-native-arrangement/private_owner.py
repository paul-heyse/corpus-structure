"""Contained native pilot and identity-checked settlement, not production recovery code."""

from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RUNS = REPO / "build/tmp/ta-native"
RUNS.mkdir(parents=True, exist_ok=True)


def wait_for(predicate, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        value = predicate()
        if value:
            return value
        time.sleep(0.05)
    raise TimeoutError("pilot readiness timed out")


def recover(parent: Path, root: Path) -> dict:
    assert parent.owner() == root.owner() and parent.stat().st_uid == os.getuid()
    assert root.parent == parent and not parent.is_symlink() and not root.is_symlink()
    conf = root / "postgresql/18/regress"
    marker = conf / ".by_pg_virtualenv"
    assert marker.read_text().strip() == "This is a temporary throw-away cluster"
    env = {**os.environ, "PG_CLUSTER_CONF_ROOT": str(root / "postgresql"), "PGSYSCONFDIR": str(root / "postgresql-common")}
    data = root / "data/18/regress"
    pidfile = data / "postmaster.pid"
    running = pidfile.exists()
    identity = None
    if running:
        pid = int(pidfile.read_text().splitlines()[0])
        cmd = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        assert str(data).encode() in cmd and b"-D" in cmd
        identity = {"pid": pid, "data": str(data), "private_config": str(conf)}
        stop = subprocess.run(["pg_ctlcluster", "--mode", "immediate", "18", "regress", "stop"], env=env, text=True, capture_output=True)
        assert stop.returncode == 0, stop.stderr
        wait_for(lambda: not pidfile.exists())
    drop = subprocess.run(["pg_dropcluster", "18", "regress"], env=env, text=True, capture_output=True)
    assert drop.returncode == 0, drop.stderr
    shutil.rmtree(parent)
    return {"server_was_running": running, "identity": identity, "owned_parent_removed": not parent.exists()}


def run(mode):
    parent = Path(tempfile.mkdtemp(prefix="owned-", dir=RUNS))
    socket = parent / "socket"
    socket.mkdir(mode=0o700)
    env = {**os.environ, "TMPDIR": str(parent), "TA_SOCKET": str(socket)}
    argv = ["pg_virtualenv", "-v", "18", "-o", "fsync=on", "-o", "synchronous_commit=off", "-o", "listen_addresses=", "-o", "unix_socket_directories=" + str(socket), "-o", "shared_preload_libraries=pg_textsearch,pg_stat_statements,auto_explain"]
    gate = None
    if mode == "partial-kill":
        binpath = parent / "bin"
        binpath.mkdir()
        wrapper = binpath / "pg_ctlcluster"
        gate = parent / "start-gate"
        wrapper.write_text("#!/bin/sh\ncase \" $* \" in *' start '*) touch \"$TA_GATE\"; sleep 120;; esac\nexec /usr/bin/pg_ctlcluster \"$@\"\n")
        wrapper.chmod(0o700)
        env.update(PATH=str(binpath) + ":" + env["PATH"], TA_GATE=str(gate))
    if mode in {"normal", "pgtap"}:
        argv.extend([sys.executable, str(HERE / "native_controls.py"), "private-pgtap" if mode == "pgtap" else "private"])
    else:
        argv.extend([sys.executable, "-c", "import pathlib,time,os; pathlib.Path(os.environ['TMPDIR'],'child-ready').write_text('ready'); time.sleep(120)"])
    output = HERE / "raw" / (mode + ".log")
    with output.open("w") as stream:
        child = subprocess.Popen(argv, cwd=REPO, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            if mode in {"normal", "pgtap"}:
                code = child.wait(timeout=240)
                result = {"mode": mode, "returncode": code, "owned_parent": str(parent)}
                if code != 0:
                    raise RuntimeError(f"native private controls failed: {output}")
                assert not list(parent.glob("pg_virtualenv.*"))
                shutil.rmtree(parent)
                result["owned_parent_removed"] = True
                return result
            if gate is not None:
                wait_for(gate.exists)
            else:
                wait_for(lambda: (parent / "child-ready").exists())
            roots = list(parent.glob("pg_virtualenv.*"))
            assert len(roots) == 1
            root = roots[0]
            child.kill()
            child.wait(timeout=10)
            # The still-owned, unreused process-group identity is known from this live pilot.
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            result = {"mode": mode, "outer_returncode": child.returncode, "root_contained_before_child_start": gate is not None, "recovery": recover(parent, root)}
            return result
        finally:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait()
            if parent.exists():
                roots = list(parent.glob("pg_virtualenv.*"))
                if len(roots) == 1 and (roots[0] / "postgresql/18/regress/.by_pg_virtualenv").exists():
                    recover(parent, roots[0])
                elif not roots:
                    shutil.rmtree(parent)


if __name__ == "__main__":
    (HERE / "raw").mkdir(exist_ok=True)
    results = [run(mode) for mode in (sys.argv[1:] or ("normal", "partial-kill", "running-kill"))]
    name = "private-results.json" if not sys.argv[1:] else "-".join(sys.argv[1:]) + "-results.json"
    (HERE / "raw" / name).write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))
