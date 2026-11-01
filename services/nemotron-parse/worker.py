"""Finite DB-free public-parser worker; Python 3.12, deliberately outside the app env."""

from __future__ import annotations

import base64
import dataclasses
import hashlib
import io
import json
import os
import sys
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
    return hashlib.sha256(value).hexdigest()


def encode(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class RecordingBackend:
    """Record actual submitted PNG and complete HTTP body before parser validation/merging."""

    def __init__(self, request: dict[str, Any], directory: Path) -> None:
        self.request = request
        self.directory = directory
        self.rows: list[dict[str, Any]] = []
        self.crop: dict[str, Any] | None = None
        self.client = httpx.Client(timeout=request["timeout_seconds"])

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
            reply = self.client.post(self.request["endpoint"].rstrip("/") + "/chat/completions", json=payload)
            row["http_status"] = reply.status_code
            row["http_response"] = prefix + ".http.json"
            save(self.directory / row["http_response"], reply.content)
            reply.raise_for_status()
            body = reply.json()
            choice = body["choices"][0]
            raw = choice["message"].get("content") or ""
            row.update(
                response_model=body.get("model"), finish_reason=choice.get("finish_reason"),
                usage=body.get("usage"), raw_response=prefix + ".raw.txt",
                raw_digest=save(self.directory / (prefix + ".raw.txt"), raw.encode()),
            )
            row["outcome"] = (
                "succeeded" if row["finish_reason"] in {"stop", "eos"} and raw.strip()
                else "partial"
            )
            save(self.directory / (prefix + ".json"), encode(row))
            return {"raw_out": raw, "finish_reason": row["finish_reason"], "usage": row["usage"] or {}}
        except BaseException as error:
            row.update(outcome="failed", diagnostic=f"{type(error).__name__}: {error}")
            save(self.directory / (prefix + ".json"), encode(row))
            raise


def run(request: dict[str, Any], directory: Path) -> dict[str, Any]:
    from importlib.metadata import version

    import nemotron_parse.inference as inference
    from nemotron_parse.inference import DocumentParser, GenerationSettings

    expected = request["packages"]
    for name, pin in expected.items():
        if version(name) != pin:
            raise ValueError(f"runtime package drift: {name}: {version(name)} != {pin}")
    backend = RecordingBackend(request, directory)
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
    result: dict[str, Any] = {"outcome": "failed"}
    try:
        parser = DocumentParser(
            backend=backend, model=request["model"], max_regions=request["max_regions"],
            fullpage=GenerationSettings(**request["settings"]["fullpage"]),
            detection=GenerationSettings(**request["settings"]["detection"]),
            crop=GenerationSettings(**request["settings"]["crop"]),
            merge_policy="alternatives",
        )
        document = parser.parse_triple(image, triple_regions="union")
        save(directory / "provider-document.json", encode(document))
        result.update(outcome="succeeded", document="provider-document.json")
    except BaseException as error:
        result["diagnostic"] = f"{type(error).__name__}: {error}"
    finally:
        inference.geometry.crop_bbox_pixels = crop_original
        inference.select_union_regions = select_original
        backend.client.close()
        image.close()
    result.update(requests=backend.rows, decisions=journal)
    save(directory / "result.json", encode(result))
    return result


if __name__ == "__main__":
    request_path = Path(sys.argv[1])
    try:
        run(json.loads(request_path.read_text()), request_path.parent)
    except BaseException as error:
        save(request_path.parent / "result.json", encode({
            "outcome": "failed", "diagnostic": f"{type(error).__name__}: {error}",
        }))
        raise
