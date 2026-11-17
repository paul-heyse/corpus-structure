"""Serial DB-free recognition slot; Python 3.12, deliberately outside the app env."""

from __future__ import annotations

import base64
import contextlib
import dataclasses
import hashlib
import io
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any

import httpx
from PIL import Image


def save(path: Path, value: bytes) -> str:
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(value)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    descriptor = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return hashlib.sha256(value).hexdigest()


def encode(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class TerminalInputRefusal(ValueError):
    """The admitted provider refused this input; never an adapter retry signal."""


class ServiceGenerationChanged(RuntimeError):
    """The response cannot be attributed to the generation that admitted the request."""


class RecordingBackend:
    """Record actual submitted PNG and complete HTTP body before parser validation/merging."""

    def __init__(self, request: dict[str, Any], directory: Path, *, client: httpx.Client | None = None) -> None:
        self.request = request
        self.directory = directory
        self.rows: list[dict[str, Any]] = []
        self.crop: dict[str, Any] | None = None
        self.binding = request.get("service_binding")
        if request.get("identity_assurance") == "trusted_managed_service" and not self.binding:
            raise ValueError("managed recognition requires an admitted startup generation")
        self.client = client or httpx.Client(timeout=request["timeout_seconds"])

    def __call__(self, image: Image.Image, *, prompt: str, stage: str, settings: Any) -> dict:
        ordinal = len(self.rows)
        prefix = f"request-{ordinal:03d}"
        stream = io.BytesIO()
        image.save(stream, format="PNG")
        submitted = stream.getvalue()
        payload = {
            "model": self.request["model"],
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {
                    "url": "data:image/png;base64," + base64.b64encode(submitted).decode("ascii")
                }},
            ]}],
            **dataclasses.asdict(settings),
            "skip_special_tokens": False,
        }
        row = {
            "ordinal": ordinal, "stage": stage, "prompt": prompt,
            "outcome_class": "execution",
            "requested_model": self.request["model"],
            "identity_assurance": "provider_reported",
            "service_generation": None if self.binding is None else self.binding["generation"],
            "settings": dataclasses.asdict(settings),
            "width": image.width, "height": image.height,
            "submitted_image": prefix + ".png",
            "submitted_digest": save(self.directory / (prefix + ".png"), submitted),
            "crop": self.crop if stage == "crop" else None,
        }
        self.rows.append(row)
        # Durable admission also preserves a request lost to process termination.
        save(self.directory / (prefix + ".json"), encode(row))
        try:
            reply = self.client.post(
                self.request["endpoint"].rstrip("/") + "/chat/completions", json=payload,
                headers={} if self.binding is None else {
                    "x-corpus-generation": self.binding["generation"]},
            )
            row["http_status"] = reply.status_code
            row["http_response"] = prefix + ".http.json"
            save(self.directory / row["http_response"], reply.content)
            row["response_generation"] = reply.headers.get("x-corpus-generation")
            save(self.directory / (prefix + ".json"), encode(row))
            if self.binding is not None:
                if row["response_generation"] != self.binding["generation"]:
                    raise ServiceGenerationChanged("request crossed a service generation boundary")
                row["identity_assurance"] = "trusted_managed_service"
            if reply.status_code in {400, 413, 422}:
                row["outcome_class"] = "terminal"
                raise TerminalInputRefusal(f"provider refused input: HTTP {reply.status_code}")
            reply.raise_for_status()
            body = reply.json()
            choice = body["choices"][0]
            raw = choice["message"].get("content") or ""
            row.update(
                response_model=body.get("model"), finish_reason=choice.get("finish_reason"),
                usage=body.get("usage"), raw_response=prefix + ".raw.txt",
                raw_digest=save(self.directory / (prefix + ".raw.txt"), raw.encode()),
            )
            row["outcome_class"] = "terminal"
            row["outcome"] = (
                "succeeded" if row["finish_reason"] in {"stop", "eos"} and raw.strip()
                else "partial"
            )
            save(self.directory / (prefix + ".json"), encode(row))
            return {"raw_out": raw, "finish_reason": row["finish_reason"], "usage": row["usage"] or {}}
        except BaseException as error:
            if not isinstance(error, TerminalInputRefusal):
                row["outcome_class"] = "execution"
            row.update(outcome="failed", diagnostic=f"{type(error).__name__}: {error}")
            save(self.directory / (prefix + ".json"), encode(row))
            raise


class WorkerRuntime:
    """One slot owns imports, checked package pins and a reusable HTTP connection pool."""

    def __init__(self, request: dict[str, Any]) -> None:
        from importlib.metadata import version

        import nemotron_parse.inference as inference
        from nemotron_parse.inference import DocumentParser, GenerationSettings

        self.packages = dict(request["packages"])
        for name, pin in self.packages.items():
            if version(name) != pin:
                raise ValueError(f"runtime package drift: {name}: {version(name)} != {pin}")
        self.endpoint = request["endpoint"]
        self.timeout = request["timeout_seconds"]
        self.inference = inference
        self.DocumentParser, self.GenerationSettings = DocumentParser, GenerationSettings
        self.client = httpx.Client(timeout=self.timeout)

    def close(self) -> None:
        self.client.close()


def run(request: dict[str, Any], directory: Path, runtime: WorkerRuntime) -> dict[str, Any]:
    if (request["packages"], request["endpoint"], request["timeout_seconds"]) != (
        runtime.packages, runtime.endpoint, runtime.timeout
    ):
        raise ValueError("recognition slot configuration changed within its lifetime")
    inference = runtime.inference
    DocumentParser, GenerationSettings = runtime.DocumentParser, runtime.GenerationSettings
    backend = RecordingBackend(request, directory, client=runtime.client)
    image = Image.open(request["image_path"]).convert("RGB")
    crop_original = inference.geometry.crop_bbox_pixels
    select_original = inference.select_union_regions
    journal: list[dict[str, Any]] = []

    def select(*args: Any, **kwargs: Any) -> Any:
        result = select_original(*args, **kwargs)
        journal.append({"kind": "union_selection", "selected": result})
        save(directory / "decisions.json", encode(journal))
        return result

    def crop(*args: Any, **kwargs: Any) -> Any:
        pixels = crop_original(*args, **kwargs)
        row = {
            "kind": "crop", "bbox_norm": list(args[0]), "pixels": list(pixels),
            "margin_px": kwargs["margin_px"], "margin_ratio": kwargs["margin_ratio"],
            "omitted": pixels[2] - pixels[0] < 8 or pixels[3] - pixels[1] < 8,
        }
        if not row["omitted"]:
            stream = io.BytesIO()
            image.crop(pixels).save(stream, format="JPEG", quality=95)
            row["jpeg_path"] = f"crop-{len(journal):03d}.jpg"
            row["jpeg_digest"] = save(directory / row["jpeg_path"], stream.getvalue())
        backend.crop = row
        journal.append(row)
        save(directory / "decisions.json", encode(journal))
        return pixels

    # The backend seam loses crop coordinates on a later exception. These scoped observers
    # retain upstream decisions unchanged; the isolated process is serial and DB-free.
    inference.geometry.crop_bbox_pixels = crop
    inference.select_union_regions = select
    result: dict[str, Any] = {"outcome": "failed", "outcome_class": "execution"}
    try:
        parser = DocumentParser(
            backend=backend, model=request["model"], max_regions=request["max_regions"],
            fullpage=GenerationSettings(**request["settings"]["fullpage"]),
            detection=GenerationSettings(**request["settings"]["detection"]),
            crop=GenerationSettings(**request["settings"]["crop"]),
            merge_policy="alternatives",
        )
        try:
            document = parser.parse_triple(image, triple_regions="union")
        except BaseException as error:
            result["diagnostic"] = f"{type(error).__name__}: {error}"
            # Classification applies to completed provider parsing, not file
            # writes, runtime construction or cancellation around that parsing.
            if isinstance(error, Exception) and not isinstance(error, OSError) and backend.rows and all(
                row.get("outcome_class") == "terminal" for row in backend.rows
            ):
                result["outcome_class"] = "terminal"
        else:
            save(directory / "provider-document.json", encode(document))
            result.update(outcome="succeeded", outcome_class="terminal", document="provider-document.json")
    finally:
        inference.geometry.crop_bbox_pixels = crop_original
        inference.select_union_regions = select_original
        image.close()
    result.update(requests=backend.rows, decisions=journal, worker_pid=os.getpid())
    save(directory / "result.json", encode(result))
    return result


def serve() -> None:
    """Serial page jobs share one runtime; every reply names its exact input capability."""
    protocol = sys.stdout
    runtime = None
    try:
        for line in sys.stdin:
            job = json.loads(line)
            if job.get("shutdown"):
                return
            request_path = Path(job["request"])
            fatal = False
            with (request_path.parent / "worker.log").open("a") as log:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    try:
                        request = json.loads(request_path.read_bytes())
                        if runtime is None:
                            runtime = WorkerRuntime(request)
                        run(request, request_path.parent, runtime)
                    except BaseException as error:
                        fatal = runtime is None or not isinstance(error, Exception)
                        save(request_path.parent / "result.json", encode({
                            "outcome": "failed", "outcome_class": "execution",
                            "diagnostic": f"{type(error).__name__}: {error}",
                        }))
                        traceback.print_exc()
            protocol.write(json.dumps({"request": str(request_path), "fatal": fatal}) + "\n")
            protocol.flush()
            if fatal:
                return
    finally:
        if runtime is not None:
            runtime.close()


if __name__ == "__main__":
    if sys.argv[1:] != ["--serve"]:
        raise SystemExit("recognition worker requires its owned page-job pipe")
    serve()
