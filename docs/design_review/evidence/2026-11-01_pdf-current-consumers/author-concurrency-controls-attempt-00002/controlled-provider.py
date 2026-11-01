#!/home/paul/corpus-structure/.venv/bin/python

import json, os, signal, sys, time
from pathlib import Path

root = Path(os.environ["AUTHOR_CONTROL_ROOT"])
mode = os.environ["AUTHOR_CONTROL_MODE"]
message = json.loads(sys.stdin.buffer.read())
text = message["message"]["content"][0]["text"]
kind = "C" if "You are fresh adjudicator C." in text else (
    "A" if "You are independent author A;" in text else "B"
)
payload = json.loads(text.split("\n", 1)[1])
session = sys.argv[sys.argv.index("--session-id") + 1]
assert sys.argv[sys.argv.index("--tools") + 1] == ""
assert "--strict-mcp-config" in sys.argv and "--restricted" in sys.argv
assert len([v for v in message["message"]["content"] if v["type"] == "image"]) == 2
assert not any(key.startswith(("CORPUS_", "PG", "DATABASE")) for key in os.environ)
if kind == "C":
    assert (root / "A.validated").exists() and (root / "B.validated").exists()
    assert set(payload["independent_authors"]) == {"A", "B"}
    assert all(v["complete_batches"] == ["sampling-full", "normal-full"]
               for v in payload["independent_authors"].values())
else:
    assert "independent_authors" not in payload
    if kind == "B" and mode != "success":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
(root / (kind + ".started")).write_text(json.dumps({
    "pid": os.getpid(), "session": session, "cwd": os.getcwd()
}))
if kind in {"A", "B"}:
    deadline = time.monotonic() + 5
    while not all((root / (other + ".started")).exists() for other in ("A", "B")):
        assert time.monotonic() < deadline, "both independent children must start"
        time.sleep(.01)
if mode == "both_refusals" or (mode == "failure" and kind == "A"):
    print(json.dumps({"session_id": session, "is_error": True,
                      "error": "controlled-provider-refusal"}), flush=True)
elif kind == "B" and mode != "success":
    print("controlled partial B", flush=True)
    while True:
        time.sleep(1)
else:
    print(json.dumps({"session_id": session, "structured_output": {
        "author": kind, "complete_batches": ["sampling-full", "normal-full"]
    }}), flush=True)
