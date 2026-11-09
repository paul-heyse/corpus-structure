"""Exercise native startup refusal and in-flight cancellation on the resident GPU."""

import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic

import httpx

from corpus_structure.methods.pm2_worker import Pm2WorkerError, open_pm2_worker
from corpus_structure.settings import Settings

ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "python/corpus-structure/src/corpus_structure/methods/pm2_native.py"


def requests(provider):
    short = ["Ada", "checked", "the", "chart", "."]
    long = ["She", "then", "reported", "the", "figures", "to", "her", "team", "."]
    if provider == "hanlp":
        return (
            {"sentences": [short, long]},
            {"sentences": [short, long * 13] * 4},
        )
    if provider == "maverick":
        return (
            {"sentences": [short, long]},
            {"sentences": [short, long] * 20},
        )
    if provider == "dipo":
        short, long = " ".join(short), " ".join(long)
        return {"text": f"{short} {long}"}, {"text": f"{short} {long} " * 60}
    return (
        {
            "state": {"source": "Ada checked the chart."},
            "questions": {"term": {"type": "text", "instructions": "Copy the name."}},
        },
        {},
    )


def emit(case, **result):
    print(json.dumps({"case": case, **result}, ensure_ascii=False), flush=True)


def run(provider):
    python = (
        Path(sys.executable)
        if provider == "d1"
        else ROOT / f"services/pm2-{provider}/.venv/bin/python"
    )
    settings = Settings()
    endpoint = settings.nemotron.endpoint
    health = endpoint.rstrip("/").removesuffix("/v1") + "/is_sleeping"
    options = dict(python=python, script=SCRIPT, device="cuda", nemotron_endpoint=endpoint)
    short, long = requests(provider)

    def require_awake():
        result = httpx.get(health, timeout=10)
        result.raise_for_status()
        if result.json().get("is_sleeping") is not False:
            raise ValueError("incumbent was not restored")

    require_awake()
    with TemporaryDirectory() as tmp:
        profile = Path(tmp) / "profile.json"

        def configure(assets):
            profile.write_text(json.dumps(
                {"provider": provider, "device": "cuda", "assets": str(assets)}
            ))

        configure(Path(tmp) / "absent-artifacts")
        try:
            with open_pm2_worker(profile=profile, **options):
                raise AssertionError("startup accepted missing artifacts")
        except Pm2WorkerError as error:
            if "native model startup failed" not in str(error):
                raise
            require_awake()
            emit("missing-artifacts", outcome="refused", incumbent_awake=True)

        configure(ROOT / "build/models/pm2")
        with open_pm2_worker(profile=profile, **options) as worker:
            startup = worker.startup
            warm = worker.infer(short)
            if warm["outcome"] != "succeeded":
                raise ValueError(f"representative request was not successful: {warm['outcome']}")
            emit("cold-load-and-warm-work", profile=startup, result=warm)
            if long:
                # Show that the exact cancellation input fits the real provider first.
                control = worker.infer(long)
                if control["outcome"] not in {"succeeded", "empty"}:
                    raise ValueError(f"cancellation input was not admitted: {control}")
                emit("cancellation-input", outcome=control["outcome"])
                child = worker.pid
                deadline = monotonic() + 0.015

                def cancel():
                    if monotonic() >= deadline:
                        raise InterruptedError("native cancellation probe")

                try:
                    worker.infer(long, check_active=cancel)
                except InterruptedError:
                    if Path(f"/proc/{child}").exists():
                        raise ValueError("cancelled native child remained live")
                else:
                    raise ValueError("request settled before cancellation")
        require_awake()
        if long:
            emit("cancellation", outcome="cancelled", child_reaped=True, incumbent_awake=True)
            with open_pm2_worker(profile=profile, **options) as worker:
                recovered = worker.infer(short)
                if worker.startup != startup or recovered != warm:
                    raise ValueError("fresh worker did not recover the exact successful result")
            require_awake()
            emit("recovery", outcome="succeeded", exact_result=True, incumbent_awake=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("provider", choices=("hanlp", "maverick", "dipo", "d1"))
    run(cli.parse_args().provider)
