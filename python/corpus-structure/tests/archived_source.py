"""Retained historical inputs for archive controls; never invokes a retired writer."""

import json
from functools import cache
from hashlib import sha256
from pathlib import Path

from corpus_structure.core.evidence import RenditionContent

_TRACE = Path(__file__).resolve().parents[3] / "fixtures/trace"


@cache
def _archive(filename: str) -> dict:
    return json.loads((_TRACE / filename).read_bytes())


def archived_rendition(page: str, raw: bytes | None = None) -> RenditionContent:
    retained = _archive("archived-renditions.json")["pages"][page]
    if raw is not None and sha256(raw).hexdigest() != retained["source_sha256"]:
        retained = _archive("archived-edit-renditions.json")["variants"][sha256(raw).hexdigest()]
        if retained["page"] != page:
            raise ValueError("retained input belongs to another source page")
    return RenditionContent.model_validate(retained["content"])


def archived_title(page: str) -> str | None:
    return _archive("archived-renditions.json")["pages"][page]["title"]
