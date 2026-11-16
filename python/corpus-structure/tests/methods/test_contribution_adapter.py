"""Local recovery expectations independent of whole-record acceptance and scores."""

import json
from dataclasses import replace
from hashlib import sha256

import pytest

from corpus_structure.methods.contribution_adapter import (
    ContributionBatch,
    adapt_native_groups,
    adapt_report,
    restore_report,
)
from corpus_structure.methods.gliner import GlinerPack, GlinerRefused
from corpus_structure.methods.m1_source import _retained_report
from corpus_structure.methods.record_assembly import NativeRecordGroup, RoleInput, assemble_records
from corpus_structure.methods.record_packs import family_pack
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    PreparedNativeSources,
    SyntheticText,
    source_slice,
)
from methods.record_assembly_support import context, release, report, source, span
from methods.record_assembly_support import model as record_model


def definition_pack():
    return family_pack(release(), contract="DefinitionRecordFields", anchor_role="term")


def test_current_binding_preserves_typed_population_and_separate_limited_operation():
    from corpus_structure.semantic.contributions import (
        bind_contributions,
        contribution_identity,
        operation_identity,
    )
    from corpus_structure.semantic.observations import source_value

    ctx = context("term")
    pack = GlinerPack.from_declaration(
        "release:test", {"entities": ["term"]}, version="native-local-v1"
    )
    native = replace(
        report(ctx, pack, "unused", []),
        raw_json=json.dumps({"entities": {"term": [span(0, 4, "term")]}}),
    )
    batch = adapt_report(native, ctx, pack=pack, item_key="local")
    base = next(row for row in batch.contributions if row["kind"] == "proposal")
    extra = []
    for semantic_type in ("attribute.role", "source_rule.fixture", "math.syntax"):
        row = dict(
            base,
            semantic_type=semantic_type,
            item_key=semantic_type,
            value=source_value(
                {"category": semantic_type, "nested": [{"tokens": ["term"], "positions": [0, 4]}]}
            ),
        )
        row["contribution_id"] = contribution_identity(row)
        extra.append(row)
    operation = dict(batch.operations[0], emitted_count=len(batch.contributions) + len(extra))
    limited = dict(
        question="unexecuted scoped question",
        operation_version="1",
        outcome="limited",
        inspected_count=0,
        emitted_count=0,
        reason="fixture source request limit",
        inputs=(),
        computation_dependencies=("source:fixture",),
    )
    limited["operation_key"] = operation_identity(limited)
    combined = ContributionBatch.combine(
        (
            ContributionBatch((operation,), (*batch.contributions, *extra), batch.coordinate_texts),
            ContributionBatch((limited,), (), ()),
        )
    )
    operations, contributions = bind_contributions(
        release(),
        source=ctx.primary.unit_ref,
        operations=combined.operations,
        contributions=combined.contributions,
        coordinate_texts=combined.coordinate_texts,
    )
    assert len(contributions) == len(batch.contributions) + 3
    assert {row["semantic_type"] for row in contributions} >= {
        "attribute.role",
        "source_rule.fixture",
        "math.syntax",
    }
    assert contributions[-1]["value"] == extra[-1]["value"]
    assert isinstance(contributions[-1]["value"]["fields"], tuple)
    assert [row["outcome"] for row in operations] == ["succeeded", "limited"]
    assert operations[-1]["inspected_count"] == operations[-1]["emitted_count"] == 0
    assert operations[-1]["reason"] == "fixture source request limit"
    assert not any(row["operation_key"] == limited["operation_key"] for row in contributions)


@pytest.mark.parametrize("primary", ["unique", "ambiguous", "unlocated"])
def test_latent_group_associations_require_unique_located_primary_and_retain_mode(primary):
    ctx = context("term word alias")
    declaration = json.loads(definition_pack().declaration_json)
    declaration["structures"]["definition"].update(mode="latent", anchor=None)
    pack = GlinerPack.from_declaration("release:test", declaration, version="native-combined-v2")
    term = (
        span(0, 4, "term")
        if primary == "unique"
        else [span(0, 4, "term"), span(5, 9, "word")]
        if primary == "ambiguous"
        else span(99, 100, "x")
    )
    batch = adapt_report(
        report(ctx, pack, "definition", [{"term": term, "alias": span(10, 15, "alias")}]),
        ctx,
        pack=pack,
        item_key="latent",
    )
    relations = [row for row in batch.contributions if row["kind"] == "relation"]
    assert len(relations) == (1 if primary == "unique" else 0)
    assert any(row["kind"] == "composite" for row in batch.contributions)
    if relations:
        assert relations[0]["semantic_type"] == "definition.alias_attachment"
        assert "grouping-mode:latent" in relations[0]["computation_dependencies"]
        assert relations[0]["score_state"] == "missing" and "score" not in relations[0]


def test_substituted_schema_declaration_cannot_authorize_attachments_under_original_pack_key():
    from corpus_structure.methods.contribution_adapter import _with_group_attachments

    ctx = context("term alias")
    pack = definition_pack()
    adapted = adapt_report(
        report(
            ctx, pack, "definition", [{"term": span(0, 4, "term"), "alias": span(5, 10, "alias")}]
        ),
        ctx,
        pack=pack,
        item_key="source",
    )
    original_ops = tuple(
        op for op in adapted.operations if op["question"] != "propose_returned_role_attachments"
    )
    keys = {op["operation_key"] for op in original_ops}
    original = ContributionBatch(
        original_ops,
        tuple(row for row in adapted.contributions if row["operation_key"] in keys),
        adapted.coordinate_texts,
    )
    changed = json.loads(pack.declaration_json)
    changed["structures"]["definition"].update(mode="latent", anchor=None)
    substituted = GlinerPack.from_declaration(pack.release, changed, version="native-combined-v2")
    assert substituted.fingerprint != pack.fingerprint
    refused = _with_group_attachments(original, schema_packs={pack.fingerprint: substituted})
    assert refused.contributions == original.contributions
    assert refused.operations[: len(original_ops)] == original_ops
    (operation,) = refused.operations[len(original_ops) :]
    assert operation["outcome"] == "unsupported" and operation["emitted_count"] == 0
    assert "fingerprint" in operation["reason"]
    accepted = _with_group_attachments(original, schema_packs={pack.fingerprint: pack})
    assert sum(row["kind"] == "relation" for row in accepted.contributions) == 1


@pytest.mark.parametrize("blank", [False, True])
def test_captured_native_header_association_is_independent_of_value_presence(blank):
    from corpus_structure.methods.record_assembly import native_table_groups
    from corpus_structure.semantic.contributions import bind_contributions

    value = "" if blank else "0"
    pieces = [
        dict(
            kind="native_text",
            item_ref="#/tables/0",
            start=len(value),
            end=len(value) + 4,
            source_field="cell_text",
            cell_index=1,
        )
    ]
    if value:
        pieces.insert(
            0,
            dict(
                kind="native_text",
                item_ref="#/tables/0",
                start=0,
                end=1,
                source_field="cell_text",
                cell_index=0,
            ),
        )
    ctx = context(
        value + "mean",
        pieces=pieces,
        items=[
            dict(
                label="table",
                self_ref="#/tables/0",
                data=dict(table_cells=[dict(text=value), dict(text="mean")]),
            )
        ],
    )
    groups = native_table_groups(
        ctx, table_pointer="#/tables/0", cells=(0,), row_paths={}, header_paths={0: (1,)}
    )
    batch = adapt_native_groups(ctx, family="table", groups=groups, item_key="native-header")
    (relation,) = [row for row in batch.contributions if row["kind"] == "relation"]
    assert relation["semantic_type"] == "table.header_path_attachment"
    assert "grouping-mode:native_geometry" in relation["computation_dependencies"]
    assert "producer:derived_from_native_group" in relation["computation_dependencies"]
    primary = next(
        row
        for row in batch.contributions
        if row["contribution_id"] == relation["endpoints"][0]["contribution_id"]
    )
    assert primary["source_field_state"] == ("unstated" if blank else "present")
    assert primary["anchors"][0]["precision"] == ("item" if blank else "exact")
    assert not any(
        row["semantic_type"]
        in {"table.unit_attachment", "table.note_attachment", "table.caption_attachment"}
        for row in batch.contributions
    )
    bind_contributions(
        release(),
        source=ctx.primary.unit_ref,
        operations=batch.operations,
        contributions=batch.contributions,
        coordinate_texts=batch.coordinate_texts,
    )


def proposals(batch, semantic_type):
    return [
        row
        for row in batch.contributions
        if row["kind"] == "proposal" and row["semantic_type"] == semantic_type
    ]


def test_local_mentions_attributes_and_directed_endpoints_preserve_repeated_occurrences():
    ctx = context("X names X")
    pack = GlinerPack.from_declaration(
        "release:test",
        {
            "entities": ["term"],
            "entity_attributes": {
                "role": {"labels": ["alias", "definition"], "applies_to": ["term"]}
            },
            "relations": ["names"],
        },
        version="native-local-v1",
    )
    raw = {
        "entities": {
            "term": [
                dict(span(0, 1, "X"), role={"label": "definition", "confidence": 0.7}),
                span(8, 9, "X"),
            ]
        },
        "relation_extraction": {
            "names": [{"head": span(8, 9, "X"), "tail": span(0, 1, "X"), "confidence": 0.8}]
        },
    }
    native = replace(report(ctx, pack, "unused", []), raw_json=json.dumps(raw))
    batch = adapt_report(native, ctx, pack=pack, item_key="local")
    terms = proposals(batch, "entity.term")
    attrs = proposals(batch, "attribute.role")
    assert len(terms) == 2 and terms[0]["occurrence_id"] != terms[1]["occurrence_id"]
    assert (
        len(attrs) == 1
        and attrs[0]["endpoints"][0]["contribution_id"] == terms[0]["contribution_id"]
    )
    assert attrs[0]["value"] == {"kind": "text", "text": "definition"}
    assert attrs[0]["score_state"] == "native"
    assert attrs[0]["score"] == {"kind": "float", "hexadecimal": (0.7).hex()}
    (relation,) = [r for r in batch.contributions if r["kind"] == "relation"]
    assert [e["contribution_id"] for e in relation["endpoints"]] == [
        terms[1]["contribution_id"],
        terms[0]["contribution_id"],
    ]
    assert relation["score_state"] == "native" and relation["standing"] == "retained_private"
    assert batch.operations[0]["operation_version"] == "native-local-contributions-2"
    prepared = release()
    from corpus_structure.semantic.contributions import bind_contributions

    bind_contributions(
        prepared,
        source=batch.contributions[0]["pin"]["source"],
        operations=batch.operations,
        contributions=batch.contributions,
        coordinate_texts=batch.coordinate_texts,
    )


@pytest.mark.parametrize(
    "multi_label,returned,expected",
    [
        (False, "definition", [("definition", None)]),
        (False, {"label": "definition"}, [("definition", None)]),
        (False, {"label": "definition", "confidence": 0.0}, [("definition", 0.0)]),
        (
            True,
            [{"label": "definition", "confidence": 0.7}, "alias"],
            [("definition", 0.7), ("alias", None)],
        ),
    ],
)
def test_attribute_semantics_exclude_native_scores_and_accept_independent_label_expectations(
    multi_label, returned, expected
):
    from corpus_structure.semantic.contributions import bind_contributions

    ctx = context("X")
    pack = GlinerPack.from_declaration(
        "release:test",
        dict(
            entities=["term"],
            entity_attributes={
                "role": dict(
                    labels=["definition", "alias"], applies_to=["term"], multi_label=multi_label
                )
            },
        ),
        version="native-local-v1",
    )
    raw = {"entities": {"term": [dict(span(0, 1, "X"), role=returned)]}}
    native = replace(report(ctx, pack, "unused", []), raw_json=json.dumps(raw))
    batch = adapt_report(native, ctx, pack=pack, item_key="local")
    attrs = proposals(batch, "attribute.role")
    assert len(attrs) == len(expected)
    for attribute, (label, confidence) in zip(attrs, expected, strict=True):
        assert attribute["value"] == {"kind": "text", "text": label}
        assert attribute["score_state"] == ("missing" if confidence is None else "native")
        if confidence is None:
            assert "score" not in attribute
        else:
            assert attribute["score"] == {"kind": "float", "hexadecimal": float(confidence).hex()}
    bind_contributions(
        release(),
        source=batch.contributions[0]["pin"]["source"],
        operations=batch.operations,
        contributions=batch.contributions,
        coordinate_texts=batch.coordinate_texts,
    )
    assert json.loads(native.raw_json) == raw


def test_local_text_only_relation_endpoints_are_unresolved_not_first_equal_string():
    ctx = context("X names X")
    pack = GlinerPack.from_declaration(
        "release:test", {"entities": ["term"], "relations": ["names"]}, version="native-local-v1"
    )
    raw = {
        "entities": {"term": [span(0, 1, "X"), span(8, 9, "X")]},
        "relation_extraction": {"names": [{"head": {"text": "X"}, "tail": span(8, 9, "X")}]},
    }
    native = replace(report(ctx, pack, "unused", []), raw_json=json.dumps(raw))
    batch = adapt_report(native, ctx, pack=pack, item_key="local")
    (relation,) = [r for r in batch.contributions if r["kind"] == "relation"]
    assert relation["disposition"] == "unresolved"
    assert relation["endpoints"][0]["contribution_id"] not in {
        p["contribution_id"] for p in proposals(batch, "entity.term")
    }


def test_failed_whole_group_preserves_located_term_and_unlocated_alias():
    ctx = context("term means value")
    pack = definition_pack()
    native = report(
        ctx,
        pack,
        "definition",
        [
            {
                "term": span(0, 4, "term"),
                "alias": span(999, 1002, "bad"),
            }
        ],
    )
    # Requiring both fields as canonical occurrence deliberately fails this group.
    assembled = assemble_records(
        release(),
        ctx,
        pack,
        native,
        contract="DefinitionRecordFields",
        anchor_role="term",
        policy_version="test",
        occurrence_roles=("term", "alias"),
        model=record_model(),
    )
    assert not assembled.records
    assert any(row.code == "unlocated_occurrence" for row in assembled.diagnostics)
    batch = adapt_report(native, ctx, pack=pack, item_key="report:0")
    (term,) = proposals(batch, "definition.term")
    (alias,) = proposals(batch, "definition.alias")
    assert term["anchors"][0]["source_piece"] == "term"
    assert term["anchors"][0]["space"] == "native"
    assert term["score_state"] == "missing" and "score" not in term
    assert not alias["anchors"] and "occurrence_id" not in alias
    assert source_python(alias["value"])["text"] == "bad"
    assert any(row["semantic_type"] == "unlocated_returned_proposal" for row in batch.contributions)
    (group,) = [row for row in batch.contributions if row["kind"] == "composite"]
    assert group["members"] == (term["contribution_id"], alias["contribution_id"])


def test_score_shape_changes_no_location_or_role_inventory():
    ctx, pack = context("term"), definition_pack()
    batches = [
        adapt_report(
            report(ctx, pack, "definition", [{"term": {**span(0, 4, "term"), **score}}]),
            ctx,
            pack=pack,
            item_key=str(index),
        )
        for index, score in enumerate(({}, {"confidence": 0.0}, {"confidence": [0.8]}))
    ]
    rows = [proposals(batch, "definition.term")[0] for batch in batches]
    assert [row["score_state"] for row in rows] == ["missing", "native", "unsupported"]
    assert [row["anchors"] for row in rows] == [rows[0]["anchors"]] * 3
    assert len({row["occurrence_id"] for row in rows}) == 1
    assert "score" not in rows[0] and source_python(rows[1]["score"]) == 0.0
    assert "score" not in rows[2] and source_python(rows[2]["value"])["confidence"] == [0.8]


def test_returned_fragment_order_classifications_and_unsupported_fields_survive():
    ctx, pack = context("term one two"), definition_pack()
    native = report(
        ctx,
        pack,
        "definition",
        [
            {
                "defining_text": [span(9, 12, "two"), span(5, 8, "one")],
                "relation_type": dict(text="alias", start=0, end=4),
                "unexpected": {"nested": ["retained"]},
            }
        ],
    )
    batch = adapt_report(native, ctx, pack=pack, item_key="raw")
    pieces = proposals(batch, "definition.defining_text")
    assert [row["anchors"][0]["source_piece"] for row in pieces] == ["two", "one"]
    assert pieces[0]["item_key"].endswith("[0]") and pieces[1]["item_key"].endswith("[1]")
    (classified,) = proposals(batch, "definition.relation_type")
    assert classified["anchors"] == ()
    (diagnostic,) = [
        row for row in batch.contributions if row["semantic_type"] == "unsupported_returned_shape"
    ]
    assert source_python(diagnostic["value"]) == {"nested": ["retained"]}
    assert batch.operations[0]["outcome"] == "limited"


def test_synthetic_gap_never_becomes_continuous_quote():
    primary = source(
        "onetwo",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/1", start=0, end=3, source_field="text"),
            dict(kind="native_text", item_ref="#/texts/2", start=3, end=6, source_field="text"),
        ],
        items=[
            dict(label="text", self_ref="#/texts/1", text="one"),
            dict(label="text", self_ref="#/texts/2", text="two"),
        ],
    )
    ctx = NativeSourceContext(
        primary,
        (),
        (
            source_slice(primary, 0, 3),
            SyntheticText(" ", "model separator"),
            source_slice(primary, 3, 6),
        ),
        "definition",
        "test-policy",
        "explicit pieces",
        version=2,
        preparation=PreparedNativeSources((primary,)),
    )
    pack = definition_pack()
    native = report(ctx, pack, "definition", [{"term": span(0, 7, "one two")}])
    (row,) = proposals(adapt_report(native, ctx, pack=pack, item_key="raw"), "definition.term")
    assert row["anchors"] == () and "synthetic" in row["reason"]


def test_multi_piece_native_evidence_preserves_real_order():
    ctx = context(
        "onetwo",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/1", start=0, end=3, source_field="text"),
            dict(kind="native_text", item_ref="#/texts/2", start=3, end=6, source_field="text"),
        ],
        items=[
            dict(label="text", self_ref="#/texts/1", text="one"),
            dict(label="text", self_ref="#/texts/2", text="two"),
        ],
    )
    pack = definition_pack()
    batch = adapt_report(
        report(ctx, pack, "definition", [{"term": span(0, 6, "onetwo")}]),
        ctx,
        pack=pack,
        item_key="raw",
    )
    (row,) = proposals(batch, "definition.term")
    assert [
        (anchor["pointer"], anchor["start"], anchor["end"], anchor["source_piece"])
        for anchor in row["anchors"]
    ] == [
        ("#/texts/1", 0, 3, "one"),
        ("#/texts/2", 0, 3, "two"),
    ]


def test_contexts_share_governed_source_occurrence_without_merging_observations():
    pack = definition_pack()
    primary = source(
        "Xterm",
        identity=2,
        pieces=[
            dict(kind="native_text", item_ref="#/texts/2", start=0, end=1, source_field="text"),
            dict(kind="native_text", item_ref="#/texts/1", start=1, end=5, source_field="text"),
        ],
        items=[
            dict(label="text", self_ref="#/texts/2", text="X"),
            dict(label="text", self_ref="#/texts/1", text="term"),
        ],
    )

    def selected(start):
        return NativeSourceContext(
            primary,
            (),
            (source_slice(primary, start, 5),),
            "independent reading",
            "test-policy",
            "explicit source selection",
            version=2,
            preparation=PreparedNativeSources((primary,)),
        )

    ctx, wider = selected(1), selected(0)
    a = adapt_report(
        report(ctx, pack, "definition", [{"term": span(0, 4, "term")}]),
        ctx,
        pack=pack,
        item_key="a",
    )
    b = adapt_report(
        report(wider, pack, "definition", [{"term": span(1, 5, "term")}]),
        wider,
        pack=pack,
        item_key="b",
    )
    left, right = proposals(a, "definition.term")[0], proposals(b, "definition.term")[0]
    assert left["occurrence_id"] == right["occurrence_id"]
    assert left["contribution_id"] != right["contribution_id"]
    assert (
        sum(
            op["question"] == "recover_returned_local_contributions"
            for op in ContributionBatch.combine((a, b)).operations
        )
        == 2
    )


def test_native_structural_proposals_are_independently_attributed():
    ctx = context("term")
    batch = adapt_native_groups(
        ctx,
        family="definition",
        groups=(
            NativeRecordGroup((RoleInput("scope", native_pointer="#/groups/1"),), "native section"),
        ),
        item_key="native",
    )
    (row,) = proposals(batch, "definition.scope")
    assert row["score_state"] == "missing" and row["anchors"][0]["precision"] == "item"
    assert "producer:native_structure" in row["computation_dependencies"]
    assert all(
        "producer:gliner_returned" not in row["computation_dependencies"]
        for row in batch.contributions
    )


def test_frozen_report_restoration_verifies_profile_and_preparation_without_mutation():
    ctx, pack = context("term"), definition_pack()
    native = report(ctx, pack, "definition", [{"term": span(0, 4, "term")}])
    profiles = {}
    retained = _retained_report(native, profiles)
    before = json.dumps(retained)
    restored = restore_report(retained, ctx, profiles)
    assert restored == native and restored.raw_json == native.raw_json
    assert json.dumps(retained) == before
    damaged = {
        **retained,
        "preparation": {**retained["preparation"], "consumed_text_sha256": "0" * 64},
    }
    with pytest.raises(GlinerRefused, match="preparation text digest"):
        restore_report(damaged, ctx, profiles)
    with pytest.raises(GlinerRefused, match="effective profile"):
        restore_report(retained, ctx, {})


def test_zero_output_and_unsupported_top_level_shape_have_population_rows():
    ctx, pack = context("term"), definition_pack()
    empty = adapt_report(report(ctx, pack, "definition", []), ctx, pack=pack, item_key="empty")
    assert empty.operations[0]["outcome"] == "empty" and empty.contributions == ()
    native = replace(
        report(ctx, pack, "definition", []), raw_json='{"definition":{"not":"groups"}}'
    )
    bad = adapt_report(native, ctx, pack=pack, item_key="bad")
    assert bad.operations[0]["outcome"] == "limited"
    assert bad.operations[0]["inspected_count"] == 0 and len(bad.contributions) == 1
    assert bad.operations[0]["report_digest"] == sha256(native.raw_json.encode()).hexdigest()


def test_adapter_batch_uses_released_binding_and_authentic_source_coordinates():
    from corpus_structure.semantic.contributions import bind_contributions

    ctx, pack = context("term"), definition_pack()
    batch = adapt_report(
        report(ctx, pack, "definition", [{"term": span(0, 4, "term")}]),
        ctx,
        pack=pack,
        item_key="binding",
    )
    operations, rows = bind_contributions(
        release(),
        source=ctx.primary.unit_ref,
        operations=batch.operations,
        contributions=batch.contributions,
        coordinate_texts=batch.coordinate_texts,
    )
    assert len(rows) == len(batch.contributions) and len(operations) == len(batch.operations)


def test_table_attachment_is_separate_candidate_with_exact_closed_endpoints():
    ctx = context(
        "0mean",
        pieces=[
            dict(
                kind="native_text",
                item_ref="#/tables/0",
                start=0,
                end=1,
                source_field="cell_text",
                cell_index=0,
            ),
            dict(
                kind="native_text",
                item_ref="#/tables/0",
                start=1,
                end=5,
                source_field="cell_text",
                cell_index=1,
            ),
        ],
        items=[
            dict(
                label="table",
                self_ref="#/tables/0",
                data=dict(
                    table_cells=[
                        dict(text="0"),
                        dict(text="mean"),
                    ]
                ),
            )
        ],
    )
    pack = family_pack(release(), contract="TableRecordFields", anchor_role="cell_value")
    batch = adapt_report(
        report(
            ctx,
            pack,
            "table",
            [
                {
                    "cell_value": span(0, 1, "0"),
                    "header_path": span(1, 5, "mean"),
                    "unit": None,
                }
            ],
        ),
        ctx,
        pack=pack,
        item_key="table",
    )
    (cell,) = proposals(batch, "table.cell_value")
    (header,) = proposals(batch, "table.header_path")
    (relation,) = [row for row in batch.contributions if row["kind"] == "relation"]
    assert relation["semantic_type"] == "table.header_path_attachment"
    assert relation["operation_key"] != cell["operation_key"]
    assert relation["endpoints"] == (
        dict(role="cell_value", contribution_id=cell["contribution_id"]),
        dict(role="header_path", contribution_id=header["contribution_id"]),
    )
    assert relation["score_state"] == "missing" and "score" not in relation
    assert any(op["question"] == "propose_returned_role_attachments" for op in batch.operations)
    assert "producer:derived_from_returned_group" in relation["computation_dependencies"]
    # Rejecting this attachment cannot change the independently addressed value occurrence.
    assert cell["anchors"][0]["source_piece"] == "0"
    assert cell["anchors"][0]["pointer"] == "#/tables/0/data/table_cells/0"


def test_missing_primary_never_invents_alias_attachment_from_group_cooccurrence():
    ctx, pack = context("alias"), definition_pack()
    batch = adapt_report(
        report(
            ctx,
            pack,
            "definition",
            [
                {
                    "term": span(99, 100, "x"),
                    "alias": span(0, 5, "alias"),
                }
            ],
        ),
        ctx,
        pack=pack,
        item_key="missing-primary",
    )
    (alias,) = proposals(batch, "definition.alias")
    assert alias["anchors"]
    assert not any(row["kind"] == "relation" for row in batch.contributions)
    assert any(row["kind"] == "composite" for row in batch.contributions)


@pytest.mark.parametrize("located_predicate", [True, False])
def test_partial_assertion_keeps_exact_attributed_roles_without_inventing_a_record(
    located_predicate,
):
    from corpus_structure.semantic.contributions import bind_contributions

    ctx = context("Operators wait if busy")
    pack = family_pack(release(), contract="AssertionRecordFields", anchor_role="predicate")
    batch = adapt_report(
        report(
            ctx,
            pack,
            "assertion",
            [
                {
                    "subject": span(0, 9, "Operators"),
                    "predicate": span(10, 14, "wait")
                    if located_predicate
                    else span(80, 84, "wait"),
                    "condition": span(15, 22, "if busy"),
                }
            ],
        ),
        ctx,
        pack=pack,
        item_key="partial-assertion",
    )
    (predicate,) = proposals(batch, "assertion.predicate")
    (condition,) = proposals(batch, "assertion.condition")
    (subject,) = proposals(batch, "assertion.subject")
    (group,) = [row for row in batch.contributions if row["kind"] == "composite"]
    relations = [row for row in batch.contributions if row["kind"] == "relation"]
    assert condition["anchors"][0]["source_piece"] == "if busy"
    assert not proposals(batch, "assertion.object")
    if not located_predicate:
        assert not relations
        return
    assert {row["semantic_type"] for row in relations} == {
        "assertion.condition_attachment",
        "assertion.subject_attachment",
    }
    _, bound = bind_contributions(
        release(),
        source=ctx.primary.unit_ref,
        operations=batch.operations,
        contributions=batch.contributions,
        coordinate_texts=batch.coordinate_texts,
    )
    assert {row["contribution_id"] for row in bound if row["kind"] == "relation"} == {
        row["contribution_id"] for row in relations
    }
    for row in relations:
        role = row["semantic_type"].removeprefix("assertion.").removesuffix("_attachment")
        assert row["endpoints"] == (
            dict(role="predicate", contribution_id=predicate["contribution_id"]),
            dict(
                role=role,
                contribution_id={"condition": condition, "subject": subject}[role][
                    "contribution_id"
                ],
            ),
        )
        assert row["standing"] == "retained_private" and row["score_state"] == "missing"
        assert "returned-group:" + group["contribution_id"] in row["computation_dependencies"]


def test_actual_blank_native_cell_retains_inspection_subject_without_text_occurrence():
    from corpus_structure.methods.record_assembly import native_table_groups

    ctx = context(
        "context",
        items=[
            dict(label="text", self_ref="#/texts/1", text="context"),
            dict(label="table", self_ref="#/tables/0", data=dict(table_cells=[dict(text="")])),
        ],
    )
    groups = native_table_groups(
        ctx, table_pointer="#/tables/0", cells=(0,), row_paths={}, header_paths={}
    )
    batch = adapt_native_groups(ctx, family="table", groups=groups, item_key="blank-cell")
    (cell,) = proposals(batch, "table.cell_value")
    assert cell["source_field_state"] == "unstated"
    assert cell["anchor_role"] == "inspection_subject"
    assert cell["anchors"][0]["pointer"] == "#/tables/0/data/table_cells/0"
    assert cell["anchors"][0]["precision"] == "item"
    assert all(name not in cell["anchors"][0] for name in ("start", "end", "source_piece"))
    assert cell["endpoints"] == ()
    # The group also exposes the actual native cell object. Its structural
    # occurrence is valid, while no located textual value is manufactured.
    assert all(
        anchor["precision"] == "item" and "source_piece" not in anchor
        for row in batch.contributions
        if row["kind"] == "occurrence"
        for anchor in row["anchors"]
    )
