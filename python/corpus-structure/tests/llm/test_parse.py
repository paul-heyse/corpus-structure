"""Parse: frame resolution, conversion and the report (agent interface §3.1, §6 P0-A-0).

The `fixtures/s0` batches (the v1 reference as authored batches with citation frames) are parsed on
production renditions and compared with the spike's stored v1 reference by segment extent and
locator. Frame outcomes are exercised on edited pages: an edit elsewhere shifts every span; an edit
that makes a frame locator ambiguous gives `relocated` with the new locator and leaves the frame as
it was; a changed sentence text gives `unresolved` with `text_differs`. T1's completeness is checked
against the model's slots through `core/translations.py`'s declaration.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Any

import pytest
from linkml_runtime.utils.schemaview import SchemaView
from pydantic import MISSING

from corpus_structure.core import translations as T
from corpus_structure.core.batch import (
    AuthoredBatch,
    AuthoredOutside,
    CitationFrame,
    FrameEntry,
    StoredOutside,
)
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.vocab import DropReason, FrameFailureReason
from corpus_structure.methods.llm.cascade import CASCADE_VERSION
from corpus_structure.methods.llm.parse import Parsed, UnknownName, parse
from corpus_structure.schema.model import CORE, ci_annotations

INSERTED = "<p>An inserted paragraph that shifts every later offset.</p>\n"


def fixture(env: Any, name: str) -> tuple[AuthoredBatch, CitationFrame, str]:
    raw = json.loads((env.fixtures / f"{name}.json").read_text(encoding="utf-8"))
    page = raw["provenance"]["rendition"]["page"]
    return (
        AuthoredBatch.model_validate(raw["batch"]),
        CitationFrame.model_validate(raw["frame"]),
        page,
    )


def parsed(env: Any, name: str) -> Parsed:
    batch, frame, page = fixture(env, name)
    return parse(env.view(page), batch, frame, env.names)


def edited(env: Any, page: str, html: str, before: str = "<h3") -> Any:
    raw = env.raw(page).decode("utf-8")
    at = raw.index(before)
    return env.view_of(page, (raw[:at] + html + raw[at:]).encode("utf-8"))


NAMES = sorted(
    p.stem
    for p in (__import__("pathlib").Path(__file__).resolve().parents[4] / "fixtures/s0").glob(
        "*.json"
    )
)


# --- The v1 reference ---------------------------------------------------------------------------


def extent(view: Any, key: str) -> list[Any]:
    for s in view.content.document.walk():
        if key == _key(view, s):
            return [s.kind.value, s.start, s.end]
    raise AssertionError(key)


def _key(view: Any, segment: Any) -> str:
    from corpus_structure.core.evidence import segment_key

    return segment_key(view.rendition_key, segment.kind, segment.start, segment.end)


def spans_under(node: Any) -> list[list[int]]:
    out: list[list[int]] = []
    if isinstance(node, dict):
        if isinstance(node.get("start"), int) and isinstance(node.get("end"), int):
            out.append([node["start"], node["end"]])
        for v in node.values():
            out += spans_under(v)
    elif isinstance(node, list):
        for v in node:
            out += spans_under(v)
    return out


def test_the_v1_reference_reproduces_its_stored_form(env: Any) -> None:
    """Every fixture's stored form equals the spike's stored v1 reference: evidence spans, phrase
    spans, unsupported spans, and anchors, entity scope segments and scope qualifiers by extent
    (equal extents on one rendition are equal locators). T1 is two fixtures; U6's outside item was
    a `Statement` entity in the spike (S4 V2) and is compared by its descriptor separately."""
    reference = env.data("reference_v1")
    differ: list[tuple[Any, ...]] = []
    for name in NAMES:
        unit = name.split("-")[0]
        result = parsed(env, name)
        view = env.view(reference[unit]["page"])
        stored = result.stored.model_dump(mode="json")
        expected = reference[unit]
        assert result.report.problems == ()
        for s in stored["statements"]:
            if s["anchor"] == "outside":
                continue
            got = [extent(view, k) for k in s["anchor"]]
            if got != expected["statements"][s["local_ref"]]:
                differ.append((name, s["local_ref"], got))
        for e in stored["entities"]:
            if e["scope"] == "local" and e["local_ref"] in expected["entities"]:
                got = extent(view, e["scope_segment"])
                want = expected["entities"][e["local_ref"]]
                if got != want and name != "T1-dfn1":
                    differ.append((name, e["local_ref"], got, want))
        for c in stored["claims"]:
            want = expected["claims"][c["local_ref"]]
            evidence = [[x["start"], x["end"], x["role"]] for x in c["evidence"]]
            scope = c["qualifiers"].get("core:scope")
            phrases = spans_under({"object": c["object"], "q": c["qualifiers"]})
            got = {
                "evidence": evidence,
                "phrases": phrases,
                "scope": extent(view, scope["segment"]) if scope else None,
            }
            if got != want:
                differ.append((name, c["local_ref"], got, want))
        for u in stored["unsupported"]:
            if [u["start"], u["end"]] != expected["unsupported"][u["local_ref"]]:
                differ.append((name, u["local_ref"]))
    assert differ == []


def test_t1_split_gives_z_the_section_of_each_files_evidence(env: Any) -> None:
    """F3-01, decided by A0: T1 is two fixtures (P0-F-3). The lead-in's `Z` (extent `section`)
    resolves where the spike's T1 put it; the `#dfn1` file redeclares `Z`, whose earliest evidence
    there lies in the definition's subsection, so it resolves to that subsection, inside the spike's
    section."""
    reference = env.data("reference_v1")["T1"]
    view = env.view(reference["page"])
    lead = next(e for e in parsed(env, "T1-leadin").stored.entities if e.local_ref == "Z")
    assert extent(view, str(lead.scope_segment)) == reference["entities"]["Z"]
    dfn = next(e for e in parsed(env, "T1-dfn1").stored.entities if e.local_ref == "Z")
    kind, start, end = extent(view, str(dfn.scope_segment))
    _, outer_start, outer_end = reference["entities"]["Z"]
    assert kind == "section" and outer_start <= start < end <= outer_end


def test_an_outside_descriptor_is_stored_with_its_span(env: Any) -> None:
    result = parsed(env, "U6")
    outside = [s for s in result.stored.statements if isinstance(s, StoredOutside)]
    assert len(outside) == 1
    d = outside[0].descriptor
    text = env.view("special/Normal.html").content.canonical_text
    assert text[d.start : d.end] == "the last result"
    assert d.coarse is MISSING and d.target is MISSING
    paths = [q.path for q in result.report.quotes]
    assert "statements[2].descriptor" in paths


def test_the_report_carries_the_cascade_version_and_every_quote(env: Any) -> None:
    result = parsed(env, "T2")
    assert result.report.cascade_version == CASCADE_VERSION
    assert result.report.unit.segment is not None and result.report.unit.code is None
    assert [o.status for o in result.report.frame] == ["resolved", "resolved"]
    batch, _, _ = fixture(env, "T2")
    assert len(result.report.quotes) == sum(len(c.evidence) for c in batch.claims)
    assert all(q.located.step is not None for q in result.report.quotes)
    assert result.stored.rendition == env.view("special/Normal.html").rendition_key


def test_an_unknown_name_is_a_precondition_failure(env: Any) -> None:
    batch, frame, page = fixture(env, "T2")
    with pytest.raises(UnknownName):
        parse(env.view(page), batch, frame, {})


# --- Renditions with edits ------------------------------------------------------------------------


def test_an_edit_elsewhere_gives_the_same_text_at_shifted_offsets(env: Any) -> None:
    batch, frame, page = fixture(env, "T2")
    before = parse(env.view(page), batch, frame, env.names)
    view = edited(env, page, INSERTED)
    after = parse(view, batch, frame, env.names)
    old = env.view(page).content.canonical_text
    new = view.content.canonical_text
    shifts = set()
    for a, b in zip(before.stored.claims, after.stored.claims, strict=True):
        for x, y in zip(a.evidence, b.evidence, strict=True):
            assert old[x.start : x.end] == new[y.start : y.end]
            shifts.add(y.start - x.start)
    assert len(shifts) == 1 and shifts.pop() > 0
    assert all(o.status == "resolved" for o in after.report.frame)


def test_a_lengthened_locator_is_relocated_and_the_frame_is_not_touched(env: Any) -> None:
    """Revealing case: the re-location is reported with the new locator; the frame stays as it was
    (a consumer that keeps it writes a new frame version)."""
    batch, frame, page = fixture(env, "T2")
    assert frame["s2"].locator == "special/Normal.html@sentence:As the"
    view = edited(env, page, "<p>As the inserted sentence shows, the prefix is shared now.</p>\n")
    snapshot = frame.model_dump()
    result = parse(view, batch, frame, env.names)
    assert frame.model_dump() == snapshot
    s2 = next(o for o in result.report.frame if o.sentence == "s2")
    assert (s2.status, s2.code) == ("relocated", FrameFailureReason.LOCATOR_REFUSED)
    assert s2.locator is not None and s2.locator != frame["s2"].locator
    index = LocatorIndex(view.content, page)
    assert index.resolve(s2.locator) == s2.segment
    assert view.content.text(s2.segment) == frame["s2"].text
    assert result.report.problems == ()


def test_a_changed_sentence_is_unresolved_with_text_differs(env: Any) -> None:
    batch, frame, page = fixture(env, "T2")
    entry = frame["s2"]
    changed = CitationFrame(
        {**frame.root, "s2": FrameEntry(locator=entry.locator, text=entry.text + " Changed.")}
    )
    result = parse(env.view(page), batch, changed, env.names)
    s2 = next(o for o in result.report.frame if o.sentence == "s2")
    assert (s2.status, s2.code, s2.segment) == ("unresolved", FrameFailureReason.TEXT_DIFFERS, None)
    cited_s2 = [q for q in result.report.quotes if q.sentence == "s2"]
    assert cited_s2 and all(q.frame is FrameFailureReason.TEXT_DIFFERS for q in cited_s2)


def test_every_failure_carries_its_code(env: Any) -> None:
    """A frame without one cited entry and with one entry on another page: every failing entry, and
    every item that could not be placed, has its code."""
    batch, frame, page = fixture(env, "U6")
    entries = dict(frame.root)
    del entries["s3"]
    entries["s2"] = FrameEntry(
        locator="special/Gamma.html@sentence:A corollary", text=entries["s2"].text
    )
    result = parse(env.view(page), batch, CitationFrame(entries), env.names)
    outcomes = {o.sentence: o for o in result.report.frame}
    assert outcomes["s3"].code is FrameFailureReason.NOT_IN_FRAME
    assert outcomes["s2"].status == "relocated"  # its text is still on the page, once
    assert outcomes["s2"].code is FrameFailureReason.OTHER_PAGE
    for o in result.report.frame:
        assert (o.status == "resolved") == (o.code is None)
    assert result.report.problems, "the anchor on s3 cannot be placed"
    for p in result.report.problems:
        assert isinstance(p.code, DropReason)
    s3_anchor = [p for p in result.report.problems if p.path == "statements[1].anchor[1]"]
    assert s3_anchor and s3_anchor[0].frame is FrameFailureReason.NOT_IN_FRAME


def test_an_item_without_a_valid_sentence_is_dropped_with_its_code(env: Any) -> None:
    batch, frame, page = fixture(env, "U6")
    entries = {k: v for k, v in frame.root.items() if k != "s2"}
    result = parse(env.view(page), batch, CitationFrame(entries), env.names)
    outside = [s for s in result.stored.statements if isinstance(s, StoredOutside)]
    # "the last result" occurs only in s2, which is not in the frame: the descriptor is dropped
    assert outside == []
    dropped = {p.path: p for p in result.report.problems}
    assert dropped["statements[2].descriptor"].code is DropReason.UNLOCATED_QUOTE
    assert dropped["statements[2].descriptor"].frame is FrameFailureReason.NOT_IN_FRAME


def test_an_unresolved_extent_is_reported_with_its_code(env: Any) -> None:
    """A `scope: statement` qualifier on a claim with no statement is not guessed: it is left out
    and reported as `unresolved_extent`."""
    batch, frame, page = fixture(env, "U6")
    claims = list(batch.claims)
    i = next(k for k, c in enumerate(claims) if c.local_ref == "c_X_mean")
    raw = claims[i].model_dump(mode="json", exclude={"statement", "statement_role"})
    claims[i] = type(claims[i]).model_validate(raw)
    changed = batch.model_copy(update={"claims": tuple(claims)})
    result = parse(env.view(page), changed, frame, env.names)
    problems = {p.path: p.code for p in result.report.problems}
    assert problems[f"claims[{i}].qualifiers.scope"] is DropReason.UNRESOLVED_EXTENT
    claim = next(c for c in result.stored.claims if c.local_ref == "c_X_mean")
    assert claim.qualifiers.scope is MISSING


# --- T1 completeness (DA-005) ---------------------------------------------------------------------


def slot_lister(view: SchemaView):
    def slots(cls: str, form: str) -> Iterator[str]:
        for slot in view.class_induced_slots(cls):
            if ci_annotations(slot).get("ci:form") in (None, form, "consolidated"):
                yield str(slot.name)

    return slots


def _pairs(authored: AuthoredBatch, stored: Any) -> Iterator[tuple[str, Any, Any]]:
    """(model class, authored item, stored item) for every T1 source class in a parsed batch."""
    yield "Batch", authored, stored
    by_ref = {s.local_ref: s for s in stored.statements}
    for st in authored.statements:
        if isinstance(st, AuthoredOutside):
            out = by_ref[st.local_ref]
            yield "OutsideItem", st, out
            yield "ReferenceDescriptor", st.descriptor, out.descriptor
        else:
            yield "StatementItem", st, by_ref[st.local_ref]
    entities = {e.local_ref: e for e in stored.entities}
    for e in authored.entities:
        yield "EntityItem", e, entities[e.local_ref]
    claims = {c.local_ref: c for c in stored.claims}
    for c in authored.claims:
        sc = claims[c.local_ref]
        yield "ClaimItem", c, sc
        for a, s in zip(c.evidence, sc.evidence, strict=True):
            yield "Evidence", a, s
        if getattr(c.object, "t", None) == "phrase":
            yield "PhraseValue", c.object, sc.object
    for a, s in zip(authored.alternatives, stored.alternatives, strict=True):
        yield "AlternativeItem", a, s
    unsupported = {u.local_ref: u for u in stored.unsupported}
    for u in authored.unsupported:
        yield "UnsupportedItem", u, unsupported[u.local_ref]


def test_t1_completeness_on_the_fixtures(env: Any) -> None:
    """For every authored item of every fixture, each model slot of its class that is set reaches
    the stored item through T1's declared image (`core/translations.T1`), and a slot replaced by
    the located span leaves `start` and `end` set. Nothing is lost silently."""
    view = SchemaView(str(CORE))
    slots = slot_lister(view)
    maps = {m.source: m for m in T.T1.classes}
    seen: set[str] = set()
    for name in NAMES:
        batch, frame, page = fixture(env, name)
        result = parse(env.view(page), batch, frame, env.names)
        assert result.report.problems == ()
        for source, authored, stored in _pairs(batch, result.stored):
            seen.add(source)
            declared = maps[source]
            for slot in slots(source, T.T1.source_form):
                image = declared.slots[slot]
                value = getattr(authored, slot, MISSING)
                if value is MISSING or value in ((), {}):
                    continue
                if isinstance(image, T.Omitted):
                    assert isinstance(stored.start, int) and isinstance(stored.end, int), (
                        source,
                        slot,
                    )
                    continue
                for target in (image,) if isinstance(image, str) else image:
                    got = getattr(stored, target)
                    assert got is not MISSING, (name, source, slot, target)
                    renamed = ("type", "predicate", "kind", "text", "anchor")
                    if isinstance(value, str | int) and slot not in renamed:
                        assert got == value, (name, source, slot)
    assert seen >= {m.source for m in T.T1.classes} - {"PhraseValue", "AlternativeItem"}
