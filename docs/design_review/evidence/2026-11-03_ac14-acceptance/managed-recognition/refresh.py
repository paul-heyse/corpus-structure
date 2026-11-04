"""Refresh managed-service custody on an owned local service and new receipt directory."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import signal
import socket
import subprocess
import tempfile
import time

import httpx

REPO = Path(__file__).resolve().parents[5]
SERVICE = REPO / "services/nemotron-parse"
PYTHON = SERVICE / ".venv/bin/python"
RUNTIME = SERVICE / ".venv/bin/vllm"


def write(path, value):
    with path.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--export", type=Path, default=Path.home()/".cache/corpus-structure/nemotron-parse-4035ffb")
    parser.add_argument("--port", type=int, default=8135)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    with socket.socket() as check:
        check.bind(("127.0.0.1", args.port))
    base = f"http://127.0.0.1:{args.port}"
    launch = [str(PYTHON), str(SERVICE/"launch.py"), "--export", str(args.export),
              "--runtime", str(RUNTIME), "--receipts", str(output/"generations"), "--port", str(args.port)]
    watched = [SERVICE/"launch.py", SERVICE/"custody.py", SERVICE/"worker.py",
               REPO/"python/corpus-structure/src/corpus_structure/ingest/pdf_recognition.py", Path(__file__).resolve()]
    write(output/"source-context.json", {"head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO,text=True).strip(),
        "argv": launch, "files": {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest() for p in watched}})
    request = json.loads((REPO/"docs/design_review/evidence/2026-11-03_managed-recognition/runtime/request-1.json").read_text())["payload"]
    write(output/"request.json", request)
    process = None
    log = None

    def stop():
        nonlocal process, log
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=120)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=30)
        # Only this probe's newly created process group is eligible for cleanup.
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        log.close()
        process = None

    def start(index):
        nonlocal process, log
        log = (output/f"startup-{index}.log").open("x")
        process = subprocess.Popen(launch, cwd=REPO, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        deadline = time.monotonic()+600
        while time.monotonic()<deadline:
            if process.poll() is not None:
                raise RuntimeError(f"service stopped during startup: {process.returncode}")
            try:
                if httpx.get(base+"/health", timeout=3).status_code==200:
                    record=httpx.get(base+"/corpus/generation", timeout=3).json()
                    write(output/f"generation-{index}.json",record)
                    print(f"generation-{index} ready", flush=True)
                    return record
            except httpx.HTTPError:
                pass
            time.sleep(2)
        raise TimeoutError("owned managed-service startup exceeded600seconds")

    def query(name, generation, expected):
        headers={} if generation is None else {"x-corpus-generation":generation}
        reply=httpx.post(base+"/v1/chat/completions", json=request, headers=headers, timeout=180)
        write(output/(name+".json"), {"status":reply.status_code,"headers":dict(reply.headers),"body":reply.text})
        assert reply.status_code==expected, (name,reply.status_code,reply.text)
        return reply

    try:
        first=start(1)
        for name,generation,status in (("missing-generation",None,409),("wrong-generation","different",409),
                                        ("admitted-generation",first["generation"],200)):
            reply=query(name,generation,status)
            assert reply.headers["x-corpus-generation"]==first["generation"]
        with tempfile.TemporaryDirectory(prefix="corpus-ac14-replaced-") as tmp:
            replaced=Path(tmp)
            (replaced/"model.safetensors").write_bytes(b"same alias replacement")
            (replaced/"tokenizer.json").write_bytes(b"replacement tokenizer")
            command=list(launch)
            command[command.index("--export")+1]=str(replaced)
            command[command.index("--receipts")+1]=str(output/"replaced-generations")
            result=subprocess.run(command,cwd=REPO,text=True,capture_output=True,timeout=60)
            write(output/"replaced-startup.json",{"returncode":result.returncode,"stdout":result.stdout,"stderr":result.stderr})
            assert result.returncode!=0 and not (output/"replaced-generations").exists()
        for action in ("sleep?level=1", "wake_up"):
            reply=httpx.post(base+"/"+action,timeout=90)
            write(output/(action.split("?")[0]+".json"),{"status":reply.status_code,"body":reply.text,"headers":dict(reply.headers)})
            reply.raise_for_status()
            assert reply.headers["x-corpus-generation"]==first["generation"]
        streaming=dict(request,stream=True)
        lines=[]
        interrupted=False
        with httpx.stream("POST",base+"/v1/chat/completions",json=streaming,
                          headers={"x-corpus-generation":first["generation"]},timeout=180) as response:
            response.raise_for_status()
            assert response.headers["x-corpus-generation"]==first["generation"]
            for line in response.iter_lines():
                lines.append(line)
                if line.startswith("data: ") and line!="data: [DONE]":
                    chunk=json.loads(line[6:])
                    if not interrupted and any(choice.get("delta",{}).get("content") for choice in chunk.get("choices",[])):
                        process.terminate()
                        interrupted=True
        (output/"response-crossing.sse").write_text("\n".join(lines)+"\n")
        write(output/"crossing-result.json",{"generation":first["generation"],"shutdown_after_output":interrupted,"finished":"data: [DONE]" in lines})
        assert interrupted and "data: [DONE]" in lines
        stop()
        second=start(2)
        assert second["generation"]!=first["generation"]
        old=query("stale-generation-after-restart",first["generation"],409)
        assert old.headers["x-corpus-generation"]==second["generation"]
        new=query("new-generation-after-restart",second["generation"],200)
        assert new.headers["x-corpus-generation"]==second["generation"]
        from corpus_structure.ingest.pdf_recognition import NemotronRecipe, PreparedRecognitionSource, RecognitionWorker
        builder=runpy.run_path(str(REPO/"fixtures/toy/build_pdf.py"))
        source=output/"controlled.pdf"
        builder["write_pdf"](source,(("Example 1",("A = 2 + 3.",)),))
        prepared=PreparedRecognitionSource.prepare(source.read_bytes())
        recipe=NemotronRecipe(second["artifacts"]["model.safetensors"],second["artifacts"]["tokenizer.json"],
                              identity_assurance="trusted_managed_service",max_tokens=2048,detection_max_tokens=1024,max_regions=8)
        worker=RecognitionWorker(python=PYTHON,script=SERVICE/"worker.py",endpoint=base+"/v1",receipts=output/"application")
        try:
            (page,)=tuple(worker.recognize_pages(prepared,recipe,(1,),reuse=False))
            requests=[{"outcome":row["outcome"],"assurance":row["identity_assurance"],"generation":row["service_generation"],
                       "response_generation":row.get("response_generation")} for row,raw,artifacts in page.requests()]
            write(output/"application-result.json",{"outcome":page.result["outcome"],"requests":requests})
            assert page.succeeded and requests
            assert all(row["assurance"]=="trusted_managed_service" and row["generation"]==second["generation"]==row["response_generation"] for row in requests)
        finally:
            assert worker._process is None, "recognition generator did not release its owned worker"
        assert all(hashlib.sha256(p.read_bytes()).hexdigest()==digest for p,digest in ((REPO/key,value) for key,value in json.loads((output/"source-context.json").read_text())["files"].items()))
        write(output/"result.json",{"outcome":"passed","generation_before":first["generation"],"generation_after":second["generation"]})
        print("actual managed controls and application journey passed",flush=True)
    except BaseException as error:
        write(output/"failure.json",{"type":type(error).__name__,"message":str(error)})
        raise
    finally:
        stop()


if __name__=="__main__":
    main()
