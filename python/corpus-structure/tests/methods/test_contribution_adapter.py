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
from corpus_structure.methods.gliner import GlinerRefused
from corpus_structure.methods.m1_source import _retained_report
from corpus_structure.methods.record_assembly import NativeRecordGroup, RoleInput, assemble_records
from corpus_structure.methods.record_packs import family_pack
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.source_contexts import (
    NativeSourceContext,
    SourceSlice,
    SyntheticText,
)
from methods.test_record_assembly import context, release, report, source, span


def definition_pack():
    return family_pack(release(), contract="DefinitionRecordFields", anchor_role="term")


def proposals(batch, semantic_type):
    return [
        row
        for row in batch.contributions
        if row["kind"] == "proposal" and row["semantic_type"] == semantic_type
    ]


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
        items=[dict(self_ref="#/texts/1", text="one"), dict(self_ref="#/texts/2", text="two")],
    )
    ctx = NativeSourceContext(
        primary,
        (),
        (
            SourceSlice(1, 0, 3),
            SyntheticText(" ", "model separator"),
            SourceSlice(1, 3, 6),
        ),
        "definition",
        "test-policy",
        "explicit pieces",
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
        items=[dict(self_ref="#/texts/1", text="one"), dict(self_ref="#/texts/2", text="two")],
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


def test_views_share_physical_occurrence_without_merging_observations():
    ctx, pack = context("term"), definition_pack()
    wider = context(
        "Xterm",
        identity=2,
        pieces=[
            dict(kind="native_text", item_ref="#/texts/2", start=0, end=1, source_field="text"),
            dict(kind="native_text", item_ref="#/texts/1", start=1, end=5, source_field="text"),
        ],
        items=[dict(self_ref="#/texts/2", text="X"), dict(self_ref="#/texts/1", text="term")],
    )
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


def test_captured_recognition_retains_distinct_coordinate_space_and_binding():
    from semantic.test_captured_source_contexts import prepared_context

    ctx, captured = prepared_context(text="term", with_native=False)
    pack = definition_pack()
    batch = adapt_report(
        report(ctx, pack, "definition", [{"term": span(0, 4, "term")}]),
        ctx,
        pack=pack,
        item_key="captured",
    )
    (row,) = proposals(batch, "definition.term")
    (anchor,) = row["anchors"]
    assert anchor["space"] == "captured_recognition"
    assert anchor["recognition"] == dict(captured.recognition)
    assert anchor["binding"]["relationship"] == "primary"
    assert anchor["source_piece"] == "term"
    assert batch.coordinate_texts[0]["text"] == "term"


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


def test_actual_blank_native_cell_retains_inspection_subject_without_text_occurrence():
    from corpus_structure.methods.record_assembly import native_table_groups

    ctx = context(
        "context",
        items=[
            dict(self_ref="#/texts/1", text="context"),
            dict(self_ref="#/tables/0", data=dict(table_cells=[dict(text="")])),
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
