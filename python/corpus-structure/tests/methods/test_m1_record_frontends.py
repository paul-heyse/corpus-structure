"""Native frontend ABI controls; exact independent expectations, no model or database."""

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from corpus_structure.methods import m1_source
from corpus_structure.methods import source_preparation as prep
from corpus_structure.methods.gliner import GlinerPack, GlinerRefused
from corpus_structure.methods.record_assembly import (
    OCCURRENCE_POLICY,
    NativeRecordGroup,
    RoleInput,
    _decoder_literal_spans,
    assemble_records,
)
from corpus_structure.methods.record_packs import family_pack
from corpus_structure.methods.record_readings import native_model_observations
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    SourceSlice,
    SyntheticText,
)
from methods.test_m1_source_preparation import source as view_source
from methods.test_m1_source_profile import config
from methods.test_record_assembly import context, fields, release, report, span

ROOT = Path(__file__).resolve().parents[4]


def pack(*, contract="DefinitionRecordFields", anchor="term", inspection=False):
    return family_pack(
        release(),
        contract=contract,
        anchor_role=anchor,
        source_inspection=inspection,
        pack_version="native-combined-v2",
    )


def assemble(
    ctx,
    selected,
    group,
    *,
    contract="DefinitionRecordFields",
    anchor="term",
    occurrence_policy=OCCURRENCE_POLICY,
):
    return assemble_records(
        release(),
        ctx,
        selected,
        report(ctx, selected, "definition" if anchor == "term" else "assertion", [group]),
        contract=contract,
        anchor_role=anchor,
        policy_version="test",
        occurrence_policy=occurrence_policy,
        supplements={
            0: NativeRecordGroup(
                (RoleInput("scope", native_pointer="#/groups/1"),),
                "owned section scope",
            )
        }
        if anchor == "term"
        else {},
    )


def definition_group():
    return {
        "term": span(0, 1, "T"),
        "defining_text": [
            dict(span(15, 18, "two"), confidence=0.9),
            dict(span(2, 5, "one"), confidence=0.2),
        ],
    }


def test_v1_pack_identity_and_policy5_profiles_remain_released(tmp_path):
    old = family_pack(release(), contract="DefinitionRecordFields", anchor_role="term")
    assert old.version == "native-combined-v1"
    assert (
        GlinerPack.from_declaration(release().release_id, json.loads(old.declaration_json)) == old
    )
    for policy in (prep.POLICY, prep.POLICY_V5):
        cfg = config(tmp_path, policy=policy)
        configured = m1_source.configured_packs(release(), cfg)
        assert configured["definition"].fingerprint == old.fingerprint
        assert all(p.version == "native-combined-v1" for p in configured.values())
        assert (
            json.loads(configured["assertion"].declaration_json)["structures"]["assertion"]["mode"]
            == "natural"
        )
    cfg = config(tmp_path, policy=prep.POLICY_V6, formula_prose=True)
    configured = m1_source.configured_pack_variants(release(), cfg)
    assert all(
        p.version == "native-combined-v2"
        for variants in configured.values()
        for _, _, p in variants
    )
    assert configured["assertion"][0][:2] == ("default", "predicate")
    spec = json.loads(configured["assertion"][0][2].declaration_json)["structures"]["assertion"]
    assert spec["mode"] == "latent" and "anchor" not in spec
    assert [(variant, anchor) for variant, anchor, _ in configured["formula_context"]] == [
        ("symbol_binding", "symbol"),
        ("formula_reading", "formula"),
    ]


@pytest.mark.parametrize(
    "version,mode,anchor",
    [
        ("native-combined-v1", "latent", None),
        ("native-combined-v1", "anchorless", None),
        ("native-combined-v2", "anchorless", None),
        ("native-combined-v2", "natural", None),
        ("native-combined-v2", "latent", "predicate"),
    ],
)
def test_pack_frontends_refuse_unsupported_formation(version, mode, anchor):
    selected = pack(contract="AssertionRecordFields", anchor="predicate")
    declaration = json.loads(selected.declaration_json)
    spec = declaration["structures"]["assertion"]
    spec["mode"] = mode
    if anchor is not None:
        spec["anchor"] = anchor
    with pytest.raises(GlinerRefused):
        GlinerPack.from_declaration(release().release_id, declaration, version=version)


def test_fragment_bridge_preserves_real_pieces_without_intervening_text():
    ctx = context(
        "T one GENUINE! two",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/1", start=0, end=5, source_field="text"),
            dict(kind="native_text", item_ref="#/texts/2", start=5, end=15, source_field="orig"),
            dict(kind="native_text", item_ref="#/texts/3", start=15, end=18, source_field="text"),
        ],
        items=[
            dict(self_ref="#/texts/1", text="T one"),
            dict(self_ref="#/texts/2", orig=" GENUINE! "),
            dict(self_ref="#/texts/3", text="two"),
        ],
    )
    group = definition_group()
    result = assemble(ctx, pack(), group)
    assert len(result.records) == 1
    row = result.records[0].model_dump(mode="python")
    field = fields(result.records[0])["defining_text"]
    assert field["original_pieces"] == ("one", "two")
    assert field["value"] == {"kind": "text_sequence", "items": ("one", "two")}
    anchors = {a["anchor_id"]: a for a in row["anchors"]}
    evidence = next(e for e in row["evidence_sets"] if e["set_id"] in field["evidence_sets"])
    assert [
        (anchors[a]["pointer"], anchors[a]["start"], anchors[a]["end"], anchors[a]["source_piece"])
        for a in evidence["anchors"]
    ] == [("#/texts/1", 2, 5, "one"), ("#/texts/3", 15, 18, "two")]
    assert group["defining_text"][0]["confidence"] == 0.9  # raw confidence order unchanged
    assert result.raw_report is not None
    assert result.raw_report.raw["definition"] == [group]


@pytest.mark.parametrize(
    "bad",
    [
        [span(2, 5, "one"), span(2, 5, "one")],
        [span(2, 5, "one"), span(4, 6, "e ")],
        [span(2, 5, "ONE")],
        [span(15, 19, "two.")],
        [dict(start=True, end=5, text="one")],
        ["one"],
        span(2, 5, "one"),
    ],
)
def test_malformed_fragments_remain_unresolved_without_partial_value(bad):
    # Isolate field refusal with the retained legacy term occurrence adapter; the
    # selected occurrence-v2 profile additionally refuses this incomplete definition.
    result = assemble(
        context("T one GENUINE! two"),
        pack(),
        dict(definition_group(), defining_text=bad),
        occurrence_policy=None,
    )
    assert result.records
    field = fields(result.records[0])["defining_text"]
    assert field["state"] == "unresolved" and "value" not in field
    assert any(
        d.role == "defining_text" and d.code == "unsupported_field" for d in result.diagnostics
    )


@pytest.mark.parametrize("state", [None, "unstated", "unresolved", "present"])
def test_empty_list_never_infers_absence_and_independent_inspection_survives(state):
    group = dict(term=span(0, 1, "T"), defining_text=[])
    if state is not None:
        group["defining_text__state"] = state
    result = assemble(
        context("T one GENUINE! two"), pack(inspection=True), group, occurrence_policy=None
    )
    field = fields(result.records[0])["defining_text"]
    assert field["state"] == ("unstated" if state == "unstated" else "unresolved")
    assert "value" not in field


def test_state_conflict_keeps_fragment_value_branch_and_shared_score_provenance():
    ctx, selected = context("T one GENUINE! two"), pack(inspection=True)
    group = dict(definition_group(), defining_text__state="unstated", confidence=0.7)
    result = assemble(ctx, selected, group)
    candidates = [fields(r)["defining_text"] for r in result.records]
    assert {f["state"] for f in candidates} == {"unresolved", "present"}
    valued = next(f for f in candidates if f["state"] == "present")
    assert valued["original_pieces"] == ("one", "two")
    raw = report(ctx, selected, "definition", [group])
    observations = native_model_observations(raw, context=ctx, family="definition", context_index=3)
    fragments = [row for row in observations if row["field"] == "defining_text"]
    assert [
        (r["fragment_index"], r["confidence"], r["raw_output"]["start"]) for r in fragments
    ] == [
        (0, 0.9, 15),
        (1, 0.2, 2),
    ]
    assert len({r["group_dependency"] for r in fragments}) == 1
    assert len({r["dependence_group"] for r in fragments}) == 1
    assert all(r["context_index"] == 3 and r["pack"] == selected.fingerprint for r in fragments)
    assert all("fragment_index" not in r for r in observations if r["field"] != "defining_text")
    assert len(fragments) == 2 and all(
        r["score_standing"] == "uncalibrated_decoder_output" for r in fragments
    )


def test_fragment_list_single_item_keeps_existing_logical_text_shape():
    group = dict(definition_group(), defining_text=[span(2, 5, "one")])
    field = fields(assemble(context("T one GENUINE! two"), pack(), group).records[0])[
        "defining_text"
    ]
    assert field["value"] == {"kind": "text", "text": "one"}
    assert field["original"] == "one" and "original_pieces" not in field


def test_fragment_order_refuses_reversed_source_serialization_and_synthetic_crossing():
    base = context("T one GENUINE! two")
    ctx = NativeSourceContext(
        base.primary,
        (),
        (SourceSlice(1, 15, 18), SourceSlice(1, 0, 5)),
        "reversed fixture",
        "fixture",
        "explicit order refusal control",
    )
    # Model order is valid; the source coordinate order is unsupported.
    group = dict(term=span(3, 4, "T"), defining_text=[span(0, 3, "two"), span(5, 8, "one")])
    result = assemble(ctx, pack(), group, occurrence_policy=None)
    assert fields(result.records[0])["defining_text"]["state"] == "unresolved"
    assert any("source-monotone" in d.reason for d in result.diagnostics)
    ctx = NativeSourceContext(
        base.primary,
        (),
        (SourceSlice(1, 0, 5), SyntheticText(" ", "explicit boundary"), SourceSlice(1, 15, 18)),
        "synthetic fixture",
        "fixture",
        "explicit crossing refusal control",
    )
    result = assemble(
        ctx,
        pack(),
        dict(term=span(0, 1, "T"), defining_text=[span(2, 9, "one two")]),
        occurrence_policy=None,
    )
    assert fields(result.records[0])["defining_text"]["state"] == "unresolved"
    assert any("synthetic" in d.reason for d in result.diagnostics)


def test_fragment_report_refuses_foreign_context_and_schema():
    ctx, selected = context("T one GENUINE! two"), pack()
    raw = report(ctx, selected, "definition", [definition_group()])
    for changed in (replace(raw, context_digest="a" * 64), replace(raw, pack="foreign")):
        with pytest.raises(GlinerRefused, match=r"another source context|report/pack"):
            assemble_records(
                release(),
                ctx,
                selected,
                changed,
                contract="DefinitionRecordFields",
                anchor_role="term",
                policy_version="test",
            )


def test_fragment_observation_dedup_keeps_positions_but_never_invents_missing_confidence():
    ctx, selected = context("T one GENUINE! two"), pack()
    group = definition_group()
    group["defining_text"][1].pop("confidence")
    raw = report(ctx, selected, "definition", [group, group])
    observations = native_model_observations(raw, context=ctx, family="definition", context_index=0)
    assert len(observations) == 1
    assert observations[0]["fragment_index"] == 0
    assert observations[0]["group_indices"] == [0, 1]
    assert observations[0]["raw_output"] == group["defining_text"][0]


def test_latent_assertions_keep_existing_spo_occurrence_identity():
    ctx = context("A is B; C is D")
    selected = pack(contract="AssertionRecordFields", anchor="predicate")
    groups = [
        dict(subject=span(0, 1, "A"), predicate=span(2, 4, "is"), object=span(5, 6, "B")),
        dict(subject=span(8, 9, "C"), predicate=span(2, 4, "is"), object=span(13, 14, "D")),
    ]
    result = assemble_records(
        release(),
        ctx,
        selected,
        report(ctx, selected, "assertion", groups),
        contract="AssertionRecordFields",
        anchor_role="predicate",
        policy_version="test",
        occurrence_policy=OCCURRENCE_POLICY,
    )
    assert len(result.records) == 2
    assert len({r.model_dump()["record_id"] for r in result.records}) == 2
    assert [fields(r)["predicate"]["original"] for r in result.records] == ["is", "is"]


@pytest.mark.parametrize("pieces", [5, 13])
def test_actual_frozen_definition_fragment_bridge(pieces):
    controls = json.loads(
        (
            ROOT
            / "docs/design_review/evidence/2026-11-04_m1-native-record-challengers"
            / "controls-002.json"
        ).read_text()
    )
    case = next(
        c
        for c in controls
        if c["many"]
        and any(
            sum(r["record_id"] == rid and r["field"] == "defining_text" for r in c["roundtrips"])
            == pieces
            for rid in c["target_record_ids"]
        )
    )
    rid = next(
        rid
        for rid in case["target_record_ids"]
        if sum(r["record_id"] == rid and r["field"] == "defining_text" for r in case["roundtrips"])
        == pieces
    )
    expected = [
        r for r in case["roundtrips"] if r["record_id"] == rid and r["field"] == "defining_text"
    ]
    output = [dict(r["span"], confidence=(i + 1) / (pieces + 1)) for i, r in enumerate(expected)]
    output.reverse()
    bridged = _decoder_literal_spans(output, fragments=True)
    assert [(s.start, s.end, s.text) for s in bridged] == [
        (r["span"]["start"], r["span"]["end"], r["span"]["original_anchor"]["source_piece"])
        for r in expected
    ]
    assert [r["source_reread"][0][4] for r in expected] == [s.text for s in bridged]


def test_policy6_prose_reuses_whole_neighborhoods_and_links_both_formula_regions():
    view = view_source(
        "definition one\nF\nassertion two\nG", labels=("text", "formula", "text", "formula")
    )
    # Deliberately controlled block metadata: this test makes no annotation-provider claim.
    annotations: tuple[Any, ...] = tuple(
        SimpleNamespace(
            block_id=p["item_ref"],
            kind="paragraph",
            block_start=p["start"],
            block_end=p["end"],
        )
        for p in view.pieces
        if p["kind"] == "native_text"
    )
    selected = prep.prepare_source(
        view, persisted_annotations=annotations, policy=prep.POLICY_V6, max_chars=4096
    )
    full = [
        (i, s)
        for i, s in enumerate(selected.selections)
        if s.families == prep.PROSE_FAMILIES and s.pieces
    ]
    full = [
        (i, s)
        for i, s in full
        if s.context(
            selected.source,
            max_chars=4096,
            max_pieces=64,
            preparation=selected.preparation,
        ).text
        == view.text
    ]
    assert len(full) == 1  # both formula primaries consume the identical complete window
    index, request = full[0]
    ctx = request.context(
        selected.source, max_chars=4096, max_pieces=64, preparation=selected.preparation
    )
    assert ctx.text == view.text and ctx.policy == prep.POLICY_V6
    formulas = [r for r in selected.regions if r.label == "formula"]
    assert len(formulas) == 2 and all(index in r.selections for r in formulas)
    assert all(set(prep.PROSE_FAMILIES) <= set(r.families) for r in formulas)
    assert all(s.policy == prep.POLICY_V6 for s in selected.selections)
    old = prep.prepare_source(
        view, persisted_annotations=annotations, policy=prep.POLICY_V5, max_chars=4096
    )
    assert all(not s.pieces for s in old.selections if s.families == prep.PROSE_FAMILIES)


def test_prose_dedup_preserves_failures_and_keeps_distinct_dependencies():
    base = prep.ContextSelection(
        "#/texts/1",
        1,
        2,
        ("formula_context",),
        "formula",
        pieces=(prep.SourceSlice(7, 0, 10),),
        policy=prep.POLICY_V6,
        local_dispositions=(("#/missing", "resource_limit", "first failure"),),
    )
    other = replace(
        base,
        region="#/texts/2",
        start=3,
        end=4,
        local_dispositions=(("#/other", "unsupported", "second failure"),),
    )
    regions = [
        prep.RegionDisposition(s.region, "formula", (), s.families, "selected", "test", (i,))
        for i, s in enumerate((base, other))
    ]
    out, linked = prep._prose_formula_neighborhoods([base, other], regions, first_window=0)
    assert len(out) == 3 and linked[0].selections[-1] == linked[1].selections[-1] == 2
    assert out[2].local_dispositions == (*base.local_dispositions, *other.local_dispositions)
    changed = replace(other, missing_roles=("different_dependency",))
    out, _ = prep._prose_formula_neighborhoods([base, changed], regions, first_window=0)
    assert len(out) == 4
