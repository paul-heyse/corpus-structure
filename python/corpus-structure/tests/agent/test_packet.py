"""Prompt parts and the current pinned PDF packet digest."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.methods.llm import parts as parts_

REPO = Path(__file__).resolve().parents[4]


GUIDELINE = """# Fixture guideline

## 10.1 Definitions
<!-- core -->
<!-- applies: statement_kind=definition -->
Definitions are annotated as such.

## 10.2 Claims
<!-- core -->
<!-- applies: claim_bearing=true -->
Claims carry evidence.

## 10.3 Everything
<!-- core -->
Every unit.

## 10.4 Not core
Never served.
"""


def test_core_sections_and_their_declarations() -> None:
    found = parts_.sections(GUIDELINE)
    assert [(s.id, s.core, s.applies) for s in found] == [
        ("10.1", True, (("statement_kind", "definition"),)),
        ("10.2", True, (("claim_bearing", "true"),)),
        ("10.3", True, ()),
        ("10.4", False, ()),
    ]
    core = parts_.core_guideline(GUIDELINE)
    assert "## 10.3 Everything" in core and "Not core" not in core
    with pytest.raises(parts_.GuidelineError, match="unit_colour"):
        parts_.sections(GUIDELINE.replace("claim_bearing=true", "unit_colour=red"))


def test_parts_page_at_line_ends_within_the_bound() -> None:
    text = "".join(f"line {i:05d} " + "x" * 90 + "\n" for i in range(800))
    paged = parts_.pages(text)
    assert "".join(paged) == text and len(paged) == 4
    assert all(len(p) <= parts_.PAGE_CHARS and p.endswith("\n") for p in paged)


def test_native_digest_uses_readers_archived_release_and_resolved_configuration(monkeypatch):
    from unittest.mock import create_autospec

    from corpus_structure.core.canonical import canonical_json
    from corpus_structure.core.method import Reader, RunView, UnitRef, UnitView
    from corpus_structure.core.vocab import RunKind, TaskUnitType
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.llm.agent_opus import AgentOpus, AgentOpusConfig
    from corpus_structure.methods.math import native
    from corpus_structure.semantic.types import PreparedRelease

    archived = PreparedRelease(
        release_id="archived-source-release",
        manifest=b"{}",
        definitions=(),
        vocabularies=(),
        registry_rows=(),
        queries=(),
        artifacts=(),
        required_capabilities=(),
        diagnostics=(),
        _adapters=(),
    )
    reader = create_autospec(Reader, instance=True, spec_set=True)
    reader.prepared = archived
    run = RunView(
        run_id=17,
        kind=RunKind.FULL,
        phase=0,
        reference_run_id=None,
        model_revision="archived",
        schema_version_id=1,
        guideline_version_id=None,
        policy_version_id=None,
        key_scheme=1,
        options={},
        reader=reader,
    )
    unit = UnitView(UnitRef(TaskUnitType.SOURCE_VIEW, 31, "native-section"), run)
    packet = SimpleNamespace(hash="pinned-packet-hash")
    factory = create_autospec(native.native_proposal_packet, return_value=packet)
    monkeypatch.setattr(native, "native_proposal_packet", factory)
    cfg = AgentOpusConfig(sentences=SentenceConfig())

    digest = AgentOpus().input_digest(unit, cfg)

    factory.assert_called_once_with(reader, 31, archived, cfg.model_dump(mode="json"))
    assert digest.packet_hash == "pinned-packet-hash"
    assert digest.bytes == canonical_json({"packet": "pinned-packet-hash", "model": cfg.model})
    changed = cfg.model_copy(update={"model": "another-model"})
    assert AgentOpus().input_digest(unit, changed).bytes != digest.bytes

    factory.reset_mock()
    missing_row = UnitView(UnitRef(TaskUnitType.SOURCE_VIEW, None, "native-section"), run)
    with pytest.raises(ValueError, match="require a selected PDF SourceView"):
        AgentOpus().input_digest(missing_row, cfg)
    factory.assert_not_called()
