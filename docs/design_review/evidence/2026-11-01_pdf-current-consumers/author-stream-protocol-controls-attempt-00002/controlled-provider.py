#!/home/paul/corpus-structure/.venv/bin/python

import base64, json, os, signal, sys, time
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
assert sys.argv[sys.argv.index("--input-format") + 1] == "stream-json"
assert sys.argv[sys.argv.index("--output-format") + 1] == "stream-json"
assert "--verbose" in sys.argv and "--json-schema" in sys.argv
assert "--strict-mcp-config" in sys.argv and "--restricted" in sys.argv
images = [v["source"] for v in message["message"]["content"] if v["type"] == "image"]
assert len(images) == 2
for key, image in zip(("sampling", "normal"), images, strict=True):
    assert image["type"] == "base64" and image["media_type"] == "image/png"
    assert base64.b64decode(image["data"]) == (root / f"source-{key}.png").read_bytes()
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
print(json.dumps({"type": "system", "subtype": "init", "session_id": session}), flush=True)
if mode == "both_refusals" or (mode == "failure" and kind == "A"):
    print(json.dumps({"type": "result", "subtype": "error_during_execution",
                      "session_id": session, "is_error": True,
                      "errors": ["controlled-provider-refusal"]}), flush=True)
elif kind == "B" and mode != "success":
    print("controlled partial B", flush=True)
    while True:
        time.sleep(1)
else:
    print(json.dumps({"type": "assistant", "session_id": session,
                      "message": {"content": [{"type": "text", "text": "control"}]}}))
    print(json.dumps({"type": "result", "subtype": "success", "is_error": False,
                      "stop_reason": "end_turn", "session_id": session, "structured_output": {
        "author": kind, "complete_batches": ["sampling-full", "normal-full"]
    }}), flush=True)
