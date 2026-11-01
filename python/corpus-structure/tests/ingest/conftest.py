"""Retained HTML inputs test archive consumers without a current HTML producer."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from archived_source import archived_rendition

from corpus_structure.core.evidence import RenditionContent


@dataclass(frozen=True)
class RetainedInput:
    content: RenditionContent
    page: str


def ingest_page(page: str, corpus: Path | None = None) -> RetainedInput:
    return RetainedInput(archived_rendition(page), page)


@pytest.fixture(scope="session")
def ingest() -> Callable[..., RetainedInput]:
    return ingest_page
