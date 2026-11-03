"""Trusted local startup manifest and request-bound service generation, without model authentication."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

GENERATION_HEADER = b"x-corpus-generation"


def verify_export(root: Path, pins: dict[str, str]) -> dict[str, str]:
    """Verify selected immutable bytes once at controlled startup, before vLLM reads them."""
    manifest = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if "__pycache__" in path.parts:
            continue
        with path.open("rb") as stream:
            manifest[path.relative_to(root).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    for name, expected in pins.items():
        if manifest.get(name) != expected:
            raise ValueError(f"immutable export digest differs: {name}")
    return manifest


def generation_record(root: Path, manifest: dict[str, str], command: list[str]) -> dict:
    return {
        "protocol": "corpus-managed-recognition-1",
        "generation": uuid4().hex,
        "created_at": datetime.now(UTC).isoformat(),
        "artifact_root": str(root),
        "artifacts": manifest,
        "command": command,
        "assurance": "trusted_managed_service",
    }


class GenerationMiddleware:
    """The generation is process-bound; it cannot switch between health and inference.

    The controlled launcher supplies the manifest in process environment, rather than a
    mutable alias/file consulted per request. Responses on an old in-flight connection retain
    the old generation. Requests reaching a replacement refuse before entering inference.
    """

    def __init__(self, app):
        self.app = app
        self.record = json.loads(os.environ["CORPUS_RECOGNITION_GENERATION"])
        self.generation = self.record["generation"].encode("ascii")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = dict(scope.get("headers", ()))
        if scope["path"] == "/corpus/generation":
            body = json.dumps(self.record, sort_keys=True).encode()
            await send({"type": "http.response.start", "status": 200,
                        "headers": [(b"content-type", b"application/json"),
                                    (GENERATION_HEADER, self.generation)]})
            await send({"type": "http.response.body", "body": body})
            return
        if scope["path"].endswith("/chat/completions") and headers.get(GENERATION_HEADER) != self.generation:
            await send({"type": "http.response.start", "status": 409,
                        "headers": [(GENERATION_HEADER, self.generation)]})
            await send({"type": "http.response.body", "body": b"service generation differs"})
            return

        async def bound_send(message):
            if message["type"] == "http.response.start":
                message["headers"] = [
                    (key, value) for key, value in message.get("headers", ())
                    if key.lower() != GENERATION_HEADER
                ] + [(GENERATION_HEADER, self.generation)]
            await send(message)

        await self.app(scope, receive, bound_send)
