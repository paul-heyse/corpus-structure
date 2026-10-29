"""The packet, the stored-scope adapter, the prompt parts and the `by_unit` sections (P0-A-1; agent
interface §3.2-§3.4, §6). No database: renditions and M13's scopes come from I1a's and I2a's
functions in this process, as I2a's own tests build them.

- **Golden mode** reproduces S0-R2's v1 packets (`packet_v1/units/*.md`, unit key in the header) and
  the pack's worked examples `reference/E*/packet.md` byte for byte. H3's expected standing context
  is I2a's corrected one (`tests/math/test_scope.py`'s `CORRECTED`), not the spike's.
- **The adapter**: stored `mention` and `scope` payloads, validated, give the same standing context
  as the in-memory scopes, for every core unit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from corpus_structure.core.payloads import MentionPayload, ScopePayload
from corpus_structure.core.vocab import SegmentKind
from corpus_structure.methods.llm import packet as P
from corpus_structure.methods.llm import parts as parts_
from corpus_structure.methods.math.context import standing_context

REPO = Path(__file__).resolve().parents[4]
SPIKE = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s0r2/inputs/packet_v1"
CONTEXTS = REPO / "python/corpus-structure/tests/math/data/s0r2_contexts.json"
CORRECTED = {"H3": [(9504, 9648), (11267, 11410)]}  # I2a's corrected H3 context (test_scope.py)
VENDORED_PAGES = {
    "special/LocationScale.html",
    "special/Normal.html",
    "special/LogNormal.html",
    "special/Gamma.html",
}


def units() -> dict[str, Any]:
    return json.loads(CONTEXTS.read_text(encoding="utf-8"))["units"]


def parts_of(content: Any, unit: dict[str, Any]) -> list[Any]:
    wanted = {(p["kind"], p["start"], p["end"]) for p in unit["parts"]}
    return [s for s in content.document.walk() if (s.kind.value, s.start, s.end) in wanted]


def golden(agent: SimpleNamespace, uid: str) -> P.Packet:
    unit = units()[uid]
    content = agent.page_content(unit["page"])
    analysis = agent.analyse(content)
    segments = parts_of(content, unit)
    context = standing_context(content, unit["page"], analysis.scopes, segments)
    return P.render(content, unit["page"], uid, segments, context)


def expected(uid: str) -> str:
    path = SPIKE / "units" / f"{uid}.md"
    if not path.exists():
        path = REPO / "domains/statistics/reference" / uid / "packet.md"
    return path.read_text(encoding="utf-8")


def _cases() -> list[Any]:
    names = [*sorted(p.stem for p in (SPIKE / "units").glob("*.md")), "E1", "E2", "E3"]
    pages = units()
    return [
        pytest.param(n, marks=[] if pages[n]["page"] in VENDORED_PAGES else [pytest.mark.corpus])
        for n in names
    ]


@pytest.mark.parametrize("uid", _cases())
def test_golden_packets_reproduce_v1_and_the_worked_examples(
    agent: SimpleNamespace, uid: str
) -> None:
    got = golden(agent, uid)
    want = expected(uid)
    if uid in CORRECTED:
        text = agent.page_content(units()[uid]["page"]).canonical_text
        lines = want.split("\n")
        start = lines.index("") + 4  # the context lines follow the note and a blank line
        fixed = [f"[c{i + 1}] {text[a:b]}" for i, (a, b) in enumerate(CORRECTED[uid])]
        end = start + sum(1 for line in lines[start:] if line.startswith("[c"))
        want = "\n".join([*lines[:start], *fixed, *lines[end:]])
    assert got.parts == (want,)
    assert got.hash == P.packet_hash([want])
    assert [s.id for s in got.sentences if s.id.startswith("s")] == list(got.part_ids[0])


def stored(
    agent: SimpleNamespace, content: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """The page's M09 and M13 payloads in their stored JSON form, validated by their classes."""
    mentions = agent.mention_payloads(content, "ren:test")
    ordinals = {(m.start, m.end): i for i, m in enumerate(mentions)}
    scopes = agent.scope_payloads(content, "ren:test", 7, ordinals)
    as_rows = [MentionPayload.model_validate_json(m.model_dump_json()) for m in mentions]
    scope_rows = [ScopePayload.model_validate_json(s.model_dump_json()) for s in scopes]
    return (
        [m.model_dump(mode="json") for m in as_rows],
        [s.model_dump(mode="json") for s in scope_rows],
    )


def test_the_stored_scope_adapter_gives_the_in_memory_standing_context(
    agent: SimpleNamespace,
) -> None:
    core = {u: v for u, v in units().items() if v["set"] == "core"}
    for uid, unit in core.items():
        content = agent.page_content(unit["page"])
        analysis = agent.analyse(content)
        mentions, scopes = stored(agent, content)
        views = P.stored_scopes(content, mentions, scopes, analysis.macros)
        segments = parts_of(content, unit)
        mine = P.context_from_stored(content, unit["page"], segments, views)
        theirs = standing_context(content, unit["page"], analysis.scopes, segments)
        assert [(c.id, c.locator, c.text) for c in mine] == [
            (c.id, c.locator, c.text) for c in theirs
        ], uid


def test_a_packet_over_the_cap_splits_at_sentences_with_shared_context(
    agent: SimpleNamespace,
) -> None:
    whole = golden(agent, "T2")  # two context sentences, several unit sentences
    cap = len(whole.parts[0]) - 80  # room for each sentence, not for both
    unit = units()["T2"]
    content = agent.page_content(unit["page"])
    segments = parts_of(content, unit)
    context = standing_context(content, unit["page"], agent.analyse(content).scopes, segments)
    split = P.render(content, unit["page"], "T2", segments, context, cap=cap)
    assert len(split.parts) >= 2 and all(len(p) <= cap for p in split.parts)
    assert split.oversize == ()
    for i, part in enumerate(split.parts):
        assert f"part {i + 1} of {len(split.parts)}" in part.split("\n", 1)[0]
        assert "## Standing context" in part and "[c1]" in part and "[c2]" in part
    ids = [i for ids in split.part_ids for i in ids]
    assert ids == [f"s{n}" for n in range(1, len(ids) + 1)]  # continuous through the parts
    assert split.sentences == whole.sentences and split.hash != whole.hash
    with pytest.raises(P.PacketTooLarge):
        P.render(content, unit["page"], "T2", segments, context, cap=200)
    tight = P.render(
        content,
        unit["page"],
        "T2",
        segments,
        context,
        cap=len(split.parts[0].split("## Text")[0]) + 40,
    )
    assert tight.oversize  # a sentence longer than the room is served whole and flagged


def test_the_packet_hash_is_the_same_under_another_hash_seed(agent: SimpleNamespace) -> None:
    here = golden(agent, "T3").hash
    shim = Path(__file__).with_name("conftest.py")
    script = f"""
import importlib.util, json, sys
spec = importlib.util.spec_from_file_location("agent_conftest", {str(shim)!r})
m = importlib.util.module_from_spec(spec); sys.modules["agent_conftest"] = m
spec.loader.exec_module(m)
from corpus_structure.methods.llm import packet as P
from corpus_structure.methods.math.context import standing_context
units = json.loads(open({str(CONTEXTS)!r}).read())["units"]
u = units["T3"]; content = m.page_content(u["page"]); a = m.analyse(content)
want = {{(p["kind"], p["start"], p["end"]) for p in u["parts"]}}
segs = [s for s in content.document.walk() if (s.kind.value, s.start, s.end) in want]
ctx = standing_context(content, u["page"], a.scopes, segs)
print(P.render(content, u["page"], "T3", segs, ctx).hash)
"""
    out = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        env={**__import__("os").environ, "PYTHONHASHSEED": "12345"},
        check=True,
    )
    assert out.stdout.strip() == here


def test_agent_mode_carries_the_bootstrap_list(agent: SimpleNamespace) -> None:
    unit = units()["T1"]
    content = agent.page_content(unit["page"])
    segments = parts_of(content, unit)
    terms = P.bootstrap_terms(content)
    assert terms[0] == P.KnownEntity("Location-Scale Families")
    assert all(t.cls is None for t in terms) and len({t.label for t in terms}) == len(terms)
    packet = P.render(content, unit["page"], "T1", segments, [], terms)
    text = packet.parts[0]
    assert text.index("## Known entities") < text.index("## Text")
    assert '- term "Location-Scale Families"' in text
    entity = P.KnownEntity("normal", "stat:DistributionFamily", ("normal distribution",))
    assert entity.line() == '- stat:DistributionFamily "normal" · aliases: normal distribution'


# --- Parts and sections --------------------------------------------------------------------------


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


def unit_segment(kind: SegmentKind, hint: dict[str, Any]) -> Any:
    from corpus_structure.core.evidence import Segment

    return Segment(kind=kind, start=0, end=1, attrs={"hint": hint} if hint else {})


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


def test_a_section_applies_by_feature_or_when_the_unit_cannot_exclude_it() -> None:
    found = {s.id: s for s in parts_.sections(GUIDELINE)}
    definition = parts_.unit_features(
        unit_segment(SegmentKind.UNIT, {"statement_kind": "definition", "claim_bearing": True})
    )
    theorem = parts_.unit_features(
        unit_segment(SegmentKind.UNIT, {"statement_kind": "theorem", "claim_bearing": True})
    )
    unhinted = parts_.unit_features(unit_segment(SegmentKind.PARAGRAPH, {}))
    assert parts_.applies(found["10.1"], definition)
    assert not parts_.applies(found["10.1"], theorem)
    assert parts_.applies(found["10.1"], unhinted)  # no recorded statement kind: cannot exclude
    assert all(parts_.applies(found["10.3"], f) for f in (definition, theorem, unhinted))


def test_by_unit_guideline_input_moves_only_where_an_edit_applies() -> None:
    definition = unit_segment(
        SegmentKind.UNIT, {"statement_kind": "definition", "claim_bearing": True}
    )
    theorem = unit_segment(SegmentKind.UNIT, {"statement_kind": "theorem", "claim_bearing": True})
    edited = GUIDELINE.replace("annotated as such", "annotated with care")
    assert parts_.by_unit_guideline(edited, theorem) == parts_.by_unit_guideline(GUIDELINE, theorem)
    assert parts_.by_unit_guideline(edited, definition) != parts_.by_unit_guideline(
        GUIDELINE, definition
    )
    everyone = GUIDELINE.replace("Every unit.", "Every single unit.")
    for unit in (definition, theorem):
        assert parts_.by_unit_guideline(everyone, unit) != parts_.by_unit_guideline(GUIDELINE, unit)
    remapped = GUIDELINE.replace("statement_kind=definition", "statement_kind=theorem")
    for unit in (definition, theorem):  # a mapping change asks again for every unit
        assert parts_.by_unit_guideline(remapped, unit) != parts_.by_unit_guideline(GUIDELINE, unit)


def test_parts_page_at_line_ends_within_the_bound() -> None:
    text = "".join(f"line {i:05d} " + "x" * 90 + "\n" for i in range(800))
    paged = parts_.pages(text)
    assert "".join(paged) == text and len(paged) == 4
    assert all(len(p) <= parts_.PAGE_CHARS and p.endswith("\n") for p in paged)


# --- M24's digest ------------------------------------------------------------------------------


class FakeReader:
    """Just what M24's parts read: the guideline and two artifact bodies."""

    def __init__(self, guideline: str) -> None:
        self._guideline = guideline

    def guideline(self) -> str:
        return self._guideline

    def artifact(self, artifact_hash: str) -> bytes:
        body: Any = {"$id": "x", "title": "schema"} if artifact_hash == "b" * 64 else "# Reference"
        return json.dumps(body).encode()


def test_a_prompt_part_change_gives_a_new_digest_and_identical_inputs_the_same(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from corpus_structure.core.method import RunView, UnitRef, UnitView
    from corpus_structure.core.vocab import RunKind, TaskUnitType
    from corpus_structure.methods.llm.agent_opus import AgentOpus, AgentOpusConfig

    cfg = AgentOpusConfig(reference="a" * 64, json_schema="b" * 64, rules="c" * 64)
    packet = P.Packet("u", ("# Unit u\n",), P.packet_hash(["# Unit u\n"]), (), ((),))

    def digest(guideline: str, run_id: int = 1, config: AgentOpusConfig = cfg) -> bytes:
        view = RunView(
            run_id=run_id,
            kind=RunKind.FULL,
            phase=0,
            reference_run_id=None,
            model_revision="m",
            schema_version_id=1,
            guideline_version_id=1,
            policy_version_id=None,
            key_scheme=1,
            options={"agent_reuse": "full"},
            reader=cast(Any, FakeReader(guideline)),
        )  # type: ignore[arg-type]
        unit = UnitView(UnitRef(TaskUnitType.SEGMENT, 1, "u"), view, rendition_id=1)
        from corpus_structure.core.canonical import canonical_json

        return canonical_json(AgentOpus().digest_inputs(unit, config, packet))

    assert digest(GUIDELINE) == digest(GUIDELINE, run_id=2)  # nothing run-specific enters
    assert digest(GUIDELINE.replace("Claims carry", "Claims always carry")) != digest(GUIDELINE)
    assert digest(GUIDELINE.replace("Never served", "Not served")) == digest(GUIDELINE)  # not core
    assert digest(GUIDELINE, config=cfg.model_copy(update={"model": "other"})) != digest(GUIDELINE)
    original = parts_.prompt

    def edited(name: str) -> str:
        return original(name) + ("\nOne more note.\n" if name == "format.md" else "")

    before = digest(GUIDELINE)
    monkeypatch.setattr(parts_, "prompt", edited)
    assert digest(GUIDELINE) != before  # a prompt part's change asks again


def test_packet_cache_preserves_each_configurations_cap(agent: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    from corpus_structure.methods.llm.agent_opus import AgentOpus, AgentOpusConfig

    selected = units()["T2"]
    content = agent.page_content(selected["page"])
    segments = parts_of(content, selected)
    context = standing_context(content, selected["page"], agent.analyse(content).scopes, segments)
    def inputs(self: Any, unit: Any, cfg: Any) -> Any:
        return SimpleNamespace(packet=lambda cap: P.render(content, selected["page"], "T2", segments, context, cap=cap))
    monkeypatch.setattr(AgentOpus, "inputs", inputs)
    method = AgentOpus()
    unit = SimpleNamespace(rendition_id=1, ref=SimpleNamespace(unit_key="T2"), run=SimpleNamespace(run_id=1))
    cfg = AgentOpusConfig()
    method.packet(unit, cfg)
    with pytest.raises(P.PacketTooLarge):
        method.packet(unit, cfg.model_copy(update={"packet_cap_chars": 200}))
