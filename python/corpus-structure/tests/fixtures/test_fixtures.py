"""Independent source and citation witnesses in retained S0 and trace JSON.

The historical authored-batch schema has retired. These controls retain exact local
references, source locators, evidence quotes, region extents and vendored byte custody.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path
from types import ModuleType

import pytest

from corpus_structure.core.locators import parse


def _support() -> ModuleType:
    # The package's tests are imported in importlib mode, so the sibling module is loaded by path.
    name = "fixture_support"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name("support.py"))
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


support = _support()
REPO: Path = support.REPO
V1 = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s0r2/reference_model_v1"
MANIFEST = REPO / "docs/statistics_corpus/MANIFEST.sha256"


def _quotes(batch: dict) -> list[tuple[str, str]]:
    found = [(e["sentence"], e["quote"]) for c in batch.get("claims", ()) for e in c["evidence"]]
    return found + [(u["sentence"], u["quote"]) for u in batch.get("unsupported", ())]


def _citations(value):
    if isinstance(value, dict):
        for name, item in value.items():
            if name == "sentence" and isinstance(item, str):
                yield item
            elif name == "anchor":
                anchors = item if isinstance(item, list) else [item]
                yield from (
                    anchor
                    for anchor in anchors
                    if isinstance(anchor, str) and anchor[:1] in {"s", "c"} and anchor[1:].isdigit()
                )
            else:
                yield from _citations(item)
    elif isinstance(value, list):
        for item in value:
            yield from _citations(item)


def _local_refs(batch):
    return [
        (kind, item["local_ref"])
        for kind in ("entities", "statements", "claims", "unsupported")
        for item in batch.get(kind, ())
    ]


def _check_frame(frame: dict, page: str, batch: dict) -> None:
    assert set(frame) == set(_citations(batch))
    for entry in frame.values():
        locator = parse(entry["locator"])
        assert locator.page == page
        assert str(locator) == entry["locator"]
        assert locator.form in {"id", "prefix"}
    for sentence, quote in _quotes(batch):
        assert quote in frame[sentence]["text"], (sentence, quote)


# --- fixtures/s0 -------------------------------------------------------------------------------


def test_s0_file_set() -> None:
    files = {p.stem for p in support.S0_DIR.glob("*.json")}
    assert files == set(support.S0_UNITS)


@pytest.mark.parametrize("name", support.S0_UNITS)
def test_s0_fixture_preserves_source_citations(name: str) -> None:
    fixture = support.load_s0(name)
    page = str(fixture["provenance"]["rendition"]["page"])
    assert parse(fixture["unit_key"]).page == page
    _check_frame(fixture["frame"], page, fixture["batch"])  # descriptor sentences are citations
    for item in fixture["batch"]["statements"]:
        if item.get("kind") == "outside":  # an ExternalReference: its quote is in its sentence
            assert (
                item["descriptor"]["quote"]
                in fixture["frame"][item["descriptor"]["sentence"]]["text"]
            )


def _v1_items(unit: str) -> Counter[tuple[str, str]]:
    raw = json.loads((V1 / f"{unit}.json").read_text(encoding="utf-8"))
    items: Counter[tuple[str, str]] = Counter()
    for kind in ("entities", "statements", "claims", "unsupported"):
        for item in raw[kind]:
            # S4's V2: a `Statement` entity is a statement item
            moved = kind == "entities" and item["type"] == "Statement"
            items["statements" if moved else kind, item["local_ref"]] += 1
    items["alternatives", str(len(raw["alternatives"]))] += 1
    return items


def _fixture_items(*names: str) -> Counter[tuple[str, str]]:
    items: Counter[tuple[str, str]] = Counter()
    alternatives = 0
    for name in names:
        batch = support.load_s0(name)["batch"]
        items.update(_local_refs(batch))
        alternatives += len(batch.get("alternatives", ()))
    items["alternatives", str(alternatives)] += 1
    return items


@pytest.mark.parametrize("unit", [u for u in support.S0_UNITS if not u.startswith("T1")])
def test_s0_keeps_the_v1_items(unit: str) -> None:
    assert _fixture_items(unit) == _v1_items(unit)


def test_s0_standing_context_is_u12s() -> None:
    cited = {
        u for u in support.S0_UNITS if any(s.startswith("c") for s in support.load_s0(u)["frame"])
    }
    assert cited == {"U12"}


def test_s0_t1_split() -> None:
    lead, dfn = support.load_s0("T1-leadin"), support.load_s0("T1-dfn1")
    expected = _v1_items("T1")
    expected["entities", "Z"] += 1  # the #dfn1 file redeclares Z
    assert _fixture_items("T1-leadin", "T1-dfn1") == expected
    (z_lead,) = [e for e in lead["batch"]["entities"] if e["local_ref"] == "Z"]
    (z_dfn,) = [e for e in dfn["batch"]["entities"] if e["local_ref"] == "Z"]
    assert z_lead == z_dfn
    assert set(lead["frame"].keys()) == {"s1", "s2", "s3"}
    assert set(dfn["frame"].keys()) == {"s4", "s5", "s6"}
    assert lead["unit_key"] != dfn["unit_key"]


# --- fixtures/trace ----------------------------------------------------------------------------


def test_trace_file_set() -> None:
    segments = {
        p.name.removesuffix(".segments.json") for p in support.TRACE_DIR.glob("*.segments.json")
    }
    targets = {p.name.removesuffix(".target.json") for p in support.TRACE_DIR.glob("*.target.json")}
    assert segments == set(support.TRACE_ANNOTATION_UNITS)
    assert targets == set(support.TRACE_UNITS)


@pytest.mark.parametrize("name", support.TRACE_ANNOTATION_UNITS)
def test_trace_segments_validate(name: str) -> None:
    record = support.load_segments(name)
    unit = record.segments[0]
    assert unit.locator == record.unit_key
    for row in (*record.ancestors, *record.segments):
        locator = parse(row.locator)
        assert locator.page == record.page
        assert str(locator) == row.locator
    for row in record.segments:
        assert unit.start <= row.start <= row.end <= unit.end
    assert dict(Counter(row.kind for row in record.segments)) == record.counts
    stated = record.trace_md["counts"]
    assert isinstance(stated, dict)
    assert all(record.counts[kind] == n for kind, n in stated.items())
    assert record.trace_md["kind"] == unit.kind.value
    assert record.source_uri == f"{support.CORPUS_ROOT}/{record.page}"


@pytest.mark.parametrize("name", support.TRACE_UNITS)
def test_trace_target_preserves_citations_and_references(name: str) -> None:
    target = support.load_target(name)
    assert target["trace_unit"] == name
    _check_frame(target["frame"], target["page"], target["batch"])
    keys = {support.load_segments(u).unit_key for u in support.TRACE_ANNOTATION_UNITS}
    assert set(target["units"]) <= keys
    assert target["batch"]["unit_ref"] in target["units"]
    refs = {ref for _, ref in _local_refs(target["batch"])}
    deferred = target.get("deferred") or {}
    refs |= {item["local_ref"] for item in deferred.get("claims", ())}
    for question in target["questions"]:
        assert set(question.get("returns", ())) <= refs
        assert set(question.get("returns_with_suppositions", ())) <= refs
        assert set(question.get("returns", ())) <= set(
            question.get("returns_with_suppositions", ())
        )
        if "locator" in question.get("params", {}):
            assert parse(question["params"]["locator"]).page == target["page"]
    assert set(target["phases"].get("items", {})) <= refs


def test_trace_t1_cites_both_annotation_units() -> None:
    target = support.load_target("T1")
    keys = [support.load_segments(u).unit_key for u in ("T1-leadin", "T1-dfn1")]
    assert list(target["units"]) == keys
    assert {parse(e["locator"]).form for e in target["frame"].values()} == {"prefix"}
    assert set(target["frame"].keys()) == {"s1", "s2", "s3", "s4", "s5", "s6"}


# --- vendored pages ----------------------------------------------------------------------------


def _index_rows() -> list[dict[str, str]]:
    with support.INDEX_FILE.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def test_vendored_pages_and_index() -> None:
    rows = {row["path"]: row for row in _index_rows()}
    assert set(rows) == set(support.VENDORED_PAGES)
    for page in support.VENDORED_PAGES:
        path = support.CORPUS_DIR / support.CORPUS_ROOT / page
        assert path.stat().st_size == int(rows[page]["bytes"])
    assert "CC BY 2.0" in (support.CORPUS_DIR / "NOTICE").read_text(encoding="utf-8")
    pages = {support.load_segments(u).page for u in support.TRACE_ANNOTATION_UNITS}
    pages |= {str(support.load_s0(u)["provenance"]["rendition"]["page"]) for u in support.S0_UNITS}
    assert pages <= set(support.VENDORED_PAGES)


@pytest.mark.corpus
def test_vendored_pages_match_the_corpus_manifest() -> None:
    listed = {}
    for line in MANIFEST.read_text(encoding="utf-8").splitlines():
        digest, _, path = line.partition("  ")
        listed[path] = digest
    for page in support.VENDORED_PAGES:
        relative = f"corpus/{support.CORPUS_ROOT}/{page}"
        data = (support.CORPUS_DIR / support.CORPUS_ROOT / page).read_bytes()
        assert hashlib.sha256(data).hexdigest() == listed[relative], page
