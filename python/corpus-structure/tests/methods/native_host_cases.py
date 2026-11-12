"""Controlled JSONL peer for real process/IPC tests; no provider or GPU execution."""
import json
import os
import sys
import time
from threading import Event, Lock, Thread


def main():
    if sys.argv[1:] == ["startup-hang"]:
        time.sleep(60)
        return
    initialize = json.loads(sys.stdin.buffer.readline())
    generation = initialize["generation"]
    writing, pending = Lock(), {}

    def send(value):
        content = json.dumps(value, separators=(",", ":")).encode() + b"\n"
        with writing:
            sys.stdout.buffer.write(content)
            sys.stdout.buffer.flush()

    metadata = {}
    for declared in initialize["residents"]:
        profile = declared["profile"]
        metadata[declared["fingerprint"]] = dict(provider=profile["provider"], profile=declared["fingerprint"], runtime_identity=profile["runtime_identity"], assets=profile["artifacts"], device="cuda:0", dtype="torch."+profile["dtype"], backend=profile["backend"], matmul_precision=profile["matmul_precision"], cudnn_allow_tf32=profile["cudnn_allow_tf32"], native_threads=dict(intra_op=profile["threads"], inter_op=profile["interop_threads"]))
    send(dict(kind="ready", generation=generation, residents=metadata))

    def infer(request, cancelled):
        payload = request["payload"]
        mode = payload.get("mode")
        if mode == "descendant":
            import subprocess
            child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
            send(dict(kind="result", generation=generation, request_id=request["request_id"], provider=request["provider"], profile=request["profile"], payload={"child": child.pid}))
            os._exit(0)
        if mode == "crash":
            os._exit(7)
        if mode == "hang":
            time.sleep(60)
        if mode == "wait":
            time.sleep(0.2)
        kind, body = "result", {"payload": payload}
        if mode == "oversized":
            body = {"payload": {"oversized": "x"*8192}}
        if mode == "refused":
            kind, body = "refused", {"message": "controlled member refusal"}
        if cancelled.is_set():
            kind, body = "cancelled", {"message": "controlled member cancellation"}
        send(dict(kind=kind, generation=generation if mode != "foreign" else "wrong", request_id=request["request_id"], provider=request["provider"], profile=request["profile"], **body))

    for line in sys.stdin.buffer:
        request = json.loads(line)
        if request["kind"] == "shutdown":
            break
        if request["kind"] == "cancel":
            pending.get(request["request_id"], Event()).set()
            continue
        cancelled = Event()
        pending[request["request_id"]] = cancelled
        Thread(target=infer, args=(request, cancelled), daemon=True).start()


if __name__ == "__main__":
    main()
