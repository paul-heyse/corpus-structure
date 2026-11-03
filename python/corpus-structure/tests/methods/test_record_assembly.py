"""Independent source readings for private composition; no accuracy/publication claim."""

import json
from dataclasses import replace
from functools import cache
from hashlib import sha256
from pathlib import Path

import pytest

from corpus_structure.methods.gliner import GlinerPreparation, GlinerRefused, GlinerReport
from corpus_structure.methods.math.pdf import FormulaOccurrence
from corpus_structure.methods.record_assembly import (
    LiteralSpan,
    NativeRecordGroup,
    RoleInput,
    assemble_native_records,
    assemble_records,
    native_formula_group,
    native_table_groups,
    reconcile_record_candidates,
)
from corpus_structure.methods.record_packs import family_pack
from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import observation_inputs
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.proposals import NativeFrameSource
from corpus_structure.semantic.source_contexts import (
    ContextRelationship,
    NativeSourceContext,
    RelatedNativeSource,
    SourceSlice,
    SyntheticText,
)

ROOT = Path(__file__).resolve().parents[4]


@cache
def release():
    return prepare_release(
        observation_inputs(
            SourceBundle(
                "statistics_semantic",
                (
                    SourceArtifact(
                        "statistics_semantic",
                        (ROOT / "domains/statistics/semantic.yaml").read_bytes(),
                    ),
                    SourceArtifact(
                        "semantic_core",
                        (
                            ROOT
                            / "python/corpus-structure/src/corpus_structure"
                            / "model/semantic/core.yaml"
                        ).read_bytes(),
                    ),
                ),
            )
        )
    )


def source(text, *, identity=1, pieces=None, items=None, ancestors=("#/groups/1",)):
    pieces = pieces or [
        dict(
            kind="native_text",
            item_ref=f"#/texts/{identity}",
            start=0,
            end=len(text),
            source_field="text",
        )
    ]
    items = items or [dict(self_ref=f"#/texts/{identity}", text=text)]
    native = dict(
        pieces=pieces,
        items=items,
        ancestors=[dict(self_ref=pointer) for pointer in ancestors],
        health={"inline_coverage": "unknown"},
    )
    projection = dict(
        text=text,
        pieces=pieces,
        items=[item["self_ref"] for item in items],
        ancestors=list(ancestors),
        health=native["health"],
    )
    return NativeFrameSource(
        f"unit:{identity}",
        text,
        (),
        identity,
        ProductReference(17, "integrated", "a" * 64),
        "#/groups/1",
        "direct",
        sha256(canonical_bytes(projection)).hexdigest(),
        "c" * 64,
        canonical_bytes(native).decode(),
        version=3,
    )


def context(text, **kwargs):
    primary = source(text, **kwargs)
    return NativeSourceContext(
        primary,
        (),
        (SourceSlice(primary.source_view_id, 0, len(text)),),
        "independent reading",
        "test-policy",
        "explicit source selection",
    )


def report(ctx, pack, family, groups):
    return GlinerReport(
        ctx.dependency_digest,
        ctx.dependency_digest,
        "compute:fixture",
        "profile:fixture",
        pack.fingerprint,
        GlinerPreparation(ctx.text, "", 1, 1, len(ctx.text.encode())),
        json.dumps({family: groups}),
        "{}",
        0.0,
        False,
    )


def fields(record):
    return {field["role"]: field for field in record.model_dump(mode="python")["fields"]}


def span(start, end, text):
    return dict(start=start, end=end, text=text)


def test_native_table_adapter_reads_actual_structure_and_declared_inheritance():
    text = "Amean0note"
    pieces = [
        dict(
            kind="native_text",
            item_ref="#/tables/0",
            start=start,
            end=end,
            source_field="cell_text",
            cell_index=index,
        )
        for index, (start, end) in enumerate(((0, 1), (1, 5), (5, 6)))
    ]
    pieces.append(
        dict(kind="native_text", item_ref="#/texts/2", start=6, end=10, source_field="text")
    )
    ctx = context(
        text,
        pieces=pieces,
        items=[
            dict(
                self_ref="#/tables/0",
                data=dict(
                    table_cells=[dict(text="A"), dict(text="mean"), dict(text="0"), dict(text="")]
                ),
            ),
            dict(self_ref="#/texts/2", text="note"),
        ],
    )
    groups = native_table_groups(
        ctx,
        table_pointer="#/tables/0",
        cells=(2, 3, 4),
        row_paths={2: (0,), 3: (0,)},
        header_paths={2: (1,)},
        inherited={
            2: (
                RoleInput(
                    "note", spans=(LiteralSpan(6, 10, "note"),), dependencies=("note:declared",)
                ),
            )
        },
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="TableRecordFields",
        occurrence_roles=("cell",),
        policy_version="reading-1",
        groups=groups,
    )
    assert len(result.records) == 2
    zero, blank = map(fields, result.records)
    assert zero["cell_value"]["original"] == "0"
    assert zero["note"]["original"] == "note"
    assert blank["cell_value"]["state"] == "unstated"
    assert blank["header_path"]["state"] == "unresolved"
    assert blank["note"]["state"] == "unresolved"
    assert result.native_groups == groups
    assert "note:declared" in result.dependencies


def test_native_formula_adapter_uses_existing_occurrence_and_separate_declaration():
    ctx = context(
        "x=1x is mean",
        pieces=[
            dict(kind="native_text", item_ref="#/texts/1", start=0, end=3, source_field="orig"),
            dict(kind="native_text", item_ref="#/texts/2", start=3, end=12, source_field="text"),
        ],
        items=[
            dict(self_ref="#/texts/1", orig="x=1", text="x = 1"),
            dict(self_ref="#/texts/2", text="x is mean"),
        ],
    )
    occurrence = FormulaOccurrence("a" * 64, "#/texts/1", "x = 1", "x=1", "succeeded")
    group = native_formula_group(
        ctx,
        occurrence,
        scope_pointer="#/groups/1",
        declarations=(
            RoleInput("symbol", spans=(LiteralSpan(3, 4, "x"),)),
            RoleInput("meaning", spans=(LiteralSpan(8, 12, "mean"),)),
        ),
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="FormulaRecordFields",
        occurrence_roles=("formula", "symbol"),
        policy_version="reading-1",
        groups=(group,),
    )
    assert len(result.records) == 1
    assert fields(result.records[0])["formula"]["original"] == "x=1"
    assert fields(result.records[0])["meaning"]["original"] == "mean"
    unsupported = native_formula_group(
        ctx, replace(occurrence, original_text="x = 1"), scope_pointer="#/groups/1"
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="FormulaRecordFields",
        occurrence_roles=("formula",),
        policy_version="reading-1",
        groups=(unsupported,),
    )
    assert not result.records
    assert result.native_groups == (unsupported,)
    assert any(item.code == "unlocated_occurrence" for item in result.diagnostics)


def test_pack_uses_released_roles_enums_and_optional_native_cardinality():
    prepared = release()
    pack = family_pack(prepared, contract="MeasurementRecordFields", anchor_role="original_value")
    structure = json.loads(pack.declaration_json)["structures"]["measurement"]
    by_name = {field["name"]: field for field in structure["fields"]}
    assert set(by_name) == {
        "referent",
        "property",
        "original_value",
        "value_role",
        "unit",
        "comparator",
        "uncertainty",
        "reference_quantity",
        "condition",
    }
    assert "normalized_value" not in by_name
    assert all(field["cardinality"] == "optional_one" for field in by_name.values())
    assert "mean" in by_name["value_role"]["choices"]
    assert "dispersion" in by_name["value_role"]["choices"]
    with pytest.raises(GlinerRefused, match="literal anchor"):
        family_pack(prepared, contract="MeasurementRecordFields", anchor_role="value_role")


def test_definition_native_scope_and_missing_roles_remain_unresolved():
    ctx = context("mean is an average")
    pack = family_pack(release(), contract="DefinitionRecordFields", anchor_role="term")
    raw = report(
        ctx,
        pack,
        "definition",
        [{"term": span(0, 4, "mean"), "defining_text": span(8, 18, "an average")}],
    )
    result = assemble_records(
        release(),
        ctx,
        pack,
        raw,
        contract="DefinitionRecordFields",
        anchor_role="term",
        policy_version="reading-1",
        supplements={
            0: NativeRecordGroup(
                (RoleInput("scope", native_pointer="#/groups/1"),), "source declaration scope"
            )
        },
    )
    assert len(result.records) == 1
    row = result.records[0].model_dump(mode="python")
    assert row["standing"] == "candidate"
    assert row["pin"]["source"] == "unit:1"
    actual = fields(result.records[0])
    assert actual["term"]["original"] == "mean"
    assert actual["defining_text"]["original"] == "an average"
    assert actual["scope"]["value"]["pointer"] == "#/groups/1"
    assert actual["alias"]["state"] == "unresolved"
    assert actual["alias"]["reason"]
    assert result.raw_report is raw
    assert any(value.startswith("raw-report:") for value in row["computation_dependencies"])
    assert row["anchors"][0]["pointer"] == "#/texts/1"


def test_assertion_preserves_modal_condition_and_independent_classification_cue():
    ctx = context("Pump may cavitate below pressure")
    pack = family_pack(release(), contract="AssertionRecordFields", anchor_role="predicate")
    raw = report(
        ctx,
        pack,
        "assertion",
        [
            {
                "subject": span(0, 4, "Pump"),
                "predicate": span(9, 17, "cavitate"),
                "object": span(24, 32, "pressure"),
                "condition": span(18, 32, "below pressure"),
                "modality": {"text": "possible", "start": 0, "end": 4},
                "polarity": {"text": "positive", "start": 0, "end": 4},
            }
        ],
    )
    result = assemble_records(
        release(),
        ctx,
        pack,
        raw,
        contract="AssertionRecordFields",
        anchor_role="predicate",
        policy_version="reading-1",
        supplements={
            0: NativeRecordGroup(
                (
                    RoleInput(
                        "modality",
                        label="possible",
                        cues=(LiteralSpan(5, 8, "may"),),
                        reason="may governs the local cavitate predicate",
                        dependencies=("scope:modal-attachment",),
                    ),
                ),
                "explicit local modality attachment",
            )
        },
    )
    actual = fields(result.records[0])
    assert actual["condition"]["original"] == "below pressure"
    assert actual["modality"]["value"] == {"kind": "assertion_modality", "label": "possible"}
    assert actual["polarity"]["evidence_status"] == "unavailable"
    row = result.records[0].model_dump(mode="python")
    cue_set = next(item for item in row["evidence_sets"] if item["role"] == "modality")
    cue = next(item for item in row["anchors"] if item["anchor_id"] == cue_set["anchors"][0])
    assert (cue["start"], cue["end"], cue["source_piece"]) == (5, 8, "may")
    assert cue_set["usage"] == "classification_cue"
    assert "scope:modal-attachment" in row["computation_dependencies"]


def test_measurement_repeated_values_exact_decimals_and_inspected_absence():
    ctx = context("A mean 12.00 SD 3; B mean 12.00 SD 2")
    groups = (
        NativeRecordGroup(
            (
                RoleInput("referent", spans=(LiteralSpan(0, 1, "A"),)),
                RoleInput("property", spans=(LiteralSpan(2, 6, "mean"),)),
                RoleInput("original_value", spans=(LiteralSpan(7, 12, "12.00"),), decimal=True),
                RoleInput(
                    "value_role",
                    label="mean",
                    cues=(LiteralSpan(2, 6, "mean"),),
                    reason="explicit mean value role",
                ),
                RoleInput(
                    "reference_quantity",
                    state="unstated",
                    inspected_pointer="#/texts/1",
                    reason="no sample size in the inspected group statement",
                ),
            ),
            "Group A mean",
            ("rejected-alternative:SD3",),
        ),
        NativeRecordGroup(
            (
                RoleInput("referent", spans=(LiteralSpan(19, 20, "B"),)),
                RoleInput("property", spans=(LiteralSpan(21, 25, "mean"),)),
                RoleInput("original_value", spans=(LiteralSpan(26, 31, "12.00"),), decimal=True),
                RoleInput(
                    "value_role",
                    label="mean",
                    cues=(LiteralSpan(21, 25, "mean"),),
                    reason="explicit mean value role",
                ),
            ),
            "Group B mean",
        ),
        NativeRecordGroup(
            (
                RoleInput("referent", spans=(LiteralSpan(0, 1, "A"),)),
                RoleInput("property", spans=(LiteralSpan(13, 15, "SD"),)),
                RoleInput("original_value", spans=(LiteralSpan(16, 17, "3"),), decimal=True),
                RoleInput(
                    "value_role",
                    label="dispersion",
                    cues=(LiteralSpan(13, 15, "SD"),),
                    reason="source explicitly labels this value SD",
                ),
            ),
            "Group A dispersion",
        ),
        NativeRecordGroup(
            (
                RoleInput("referent", spans=(LiteralSpan(19, 20, "B"),)),
                RoleInput("property", spans=(LiteralSpan(32, 34, "SD"),)),
                RoleInput("original_value", spans=(LiteralSpan(35, 36, "2"),), decimal=True),
                RoleInput(
                    "value_role",
                    label="dispersion",
                    cues=(LiteralSpan(32, 34, "SD"),),
                    reason="source explicitly labels this value SD",
                ),
            ),
            "Group B dispersion",
        ),
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="MeasurementRecordFields",
        occurrence_roles=("original_value",),
        policy_version="reading-1",
        groups=groups,
    )
    assert len(result.records) == 4
    assert (
        result.records[0].model_dump()["record_id"] != result.records[1].model_dump()["record_id"]
    )
    for record in result.records[:2]:
        assert fields(record)["original_value"]["value"] == {"kind": "decimal", "lexical": "12.00"}
        assert fields(record)["normalized_value"]["state"] == "unresolved"
    assert fields(result.records[0])["reference_quantity"]["state"] == "unstated"
    assert fields(result.records[1])["reference_quantity"]["state"] == "unresolved"
    assert "rejected-alternative:SD3" in result.records[0].model_dump()["computation_dependencies"]
    assert [fields(record)["value_role"]["value"]["label"] for record in result.records] == [
        "mean",
        "mean",
        "dispersion",
        "dispersion",
    ]
    assert [fields(record)["original_value"]["original"] for record in result.records[2:]] == [
        "3",
        "2",
    ]


def test_native_table_full_header_note_shared_and_blank_is_neither_zero_nor_missing():
    # Native cell 4 is explicitly blank; cell 5 does not exist. Projection omits blank text.
    text = "Group APopulationmean0hypothetical"
    lengths = [(0, 7), (7, 17), (17, 21), (21, 22), (22, 34)]
    pieces = [
        dict(
            kind="native_text",
            item_ref="#/tables/0" if i < 4 else "#/texts/2",
            start=start,
            end=end,
            **(
                dict(source_field="cell_text", cell_index=i) if i < 4 else dict(source_field="text")
            ),
        )
        for i, (start, end) in enumerate(lengths)
    ]
    items = [
        dict(
            self_ref="#/tables/0",
            data=dict(
                table_cells=[
                    dict(text="Group A"),
                    dict(text="Population"),
                    dict(text="mean"),
                    dict(text="0"),
                    dict(text=""),
                ]
            ),
        ),
        dict(self_ref="#/texts/2", text="hypothetical"),
    ]
    ctx = context(text, pieces=pieces, items=items)
    common = (
        RoleInput("table", native_pointer="#/tables/0"),
        RoleInput("row_identity", spans=(LiteralSpan(0, 7, "Group A"),)),
        RoleInput(
            "header_path", spans=(LiteralSpan(7, 17, "Population"), LiteralSpan(17, 21, "mean"))
        ),
        RoleInput(
            "note",
            spans=(LiteralSpan(22, 34, "hypothetical"),),
            dependencies=("inheritance:declared-population-note",),
        ),
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="TableRecordFields",
        occurrence_roles=("cell",),
        policy_version="reading-1",
        groups=(
            NativeRecordGroup(
                (
                    *common,
                    RoleInput("cell", native_pointer="#/tables/0/data/table_cells/3"),
                    RoleInput("cell_value", spans=(LiteralSpan(21, 22, "0"),), decimal=True),
                ),
                "native cell/header membership",
            ),
            NativeRecordGroup(
                (
                    *common,
                    RoleInput("cell", native_pointer="#/tables/0/data/table_cells/4"),
                    RoleInput(
                        "cell_value",
                        state="unstated",
                        inspected_pointer="#/tables/0/data/table_cells/4",
                        reason="native cell text is explicitly blank",
                    ),
                ),
                "explicit native blank",
            ),
        ),
    )
    assert len(result.records) == 2
    first, blank = map(fields, result.records)
    assert first["header_path"]["original_pieces"] == ("Population", "mean")
    assert first["cell_value"]["value"] == {"kind": "decimal", "lexical": "0"}
    assert blank["cell_value"]["state"] == "unstated"
    assert "value" not in blank["cell_value"]
    assert blank["note"]["original"] == first["note"]["original"] == "hypothetical"
    assert result.raw_report is None


def test_formula_scope_and_declaration_positions_distinguish_equal_symbol_spelling():
    ctx = context("x=1 x is mean; x=1 x is variance", ancestors=("#/groups/1", "#/groups/2"))
    result = assemble_native_records(
        release(),
        ctx,
        contract="FormulaRecordFields",
        occurrence_roles=("formula", "symbol"),
        policy_version="reading-1",
        groups=(
            NativeRecordGroup(
                (
                    RoleInput("formula", spans=(LiteralSpan(0, 3, "x=1"),)),
                    RoleInput("symbol", spans=(LiteralSpan(4, 5, "x"),)),
                    RoleInput("meaning", spans=(LiteralSpan(9, 13, "mean"),)),
                    RoleInput("scope", native_pointer="#/groups/1"),
                ),
                "separately addressed first local declaration",
                ("declaration:first",),
            ),
            NativeRecordGroup(
                (
                    RoleInput("formula", spans=(LiteralSpan(15, 18, "x=1"),)),
                    RoleInput("symbol", spans=(LiteralSpan(19, 20, "x"),)),
                    RoleInput("meaning", spans=(LiteralSpan(24, 32, "variance"),)),
                    RoleInput("scope", native_pointer="#/groups/2"),
                ),
                "separately addressed second local declaration",
                ("declaration:second",),
            ),
        ),
    )
    assert len(result.records) == 2
    assert (
        result.records[0].model_dump()["record_id"] != result.records[1].model_dump()["record_id"]
    )
    assert [fields(record)["meaning"]["original"] for record in result.records] == [
        "mean",
        "variance",
    ]
    assert all(record.model_dump()["standing"] == "candidate" for record in result.records)
    assert {fields(record)["scope"]["value"]["pointer"] for record in result.records} == {
        "#/groups/1",
        "#/groups/2",
    }


def test_window_reconciliation_retains_dependencies_and_different_qualifications():
    ctx = context("mean mean")
    pack = family_pack(release(), contract="DefinitionRecordFields", anchor_role="term")
    raw = report(ctx, pack, "definition", [{"term": span(0, 4, "mean")}])
    left = assemble_records(
        release(),
        ctx,
        pack,
        raw,
        contract="DefinitionRecordFields",
        anchor_role="term",
        policy_version="reading-1",
    )
    right = assemble_records(
        release(),
        ctx,
        pack,
        replace(raw, computation="compute:second-window"),
        contract="DefinitionRecordFields",
        anchor_role="term",
        policy_version="reading-1",
    )
    merged = reconcile_record_candidates(release(), (left, right))
    assert len(merged) == 1
    dependencies = merged[0].model_dump()["computation_dependencies"]
    assert "computation:compute:fixture" in dependencies
    assert "computation:compute:second-window" in dependencies
    changed = assemble_records(
        release(),
        ctx,
        pack,
        raw,
        contract="DefinitionRecordFields",
        anchor_role="term",
        policy_version="reading-1",
        supplements={
            0: NativeRecordGroup(
                (RoleInput("alias", spans=(LiteralSpan(5, 9, "mean"),)),),
                "independently supplied alias alternative",
            )
        },
    )
    alternatives = reconcile_record_candidates(release(), (left, right, changed))
    assert len(alternatives) == 2
    assert len({record.model_dump()["record_id"] for record in alternatives}) == 1


def test_invalid_classification_cue_and_decimal_preserve_partial_candidate():
    ctx = context("A mean dash")
    result = assemble_native_records(
        release(),
        ctx,
        contract="MeasurementRecordFields",
        occurrence_roles=("referent",),
        policy_version="reading-1",
        groups=(
            NativeRecordGroup(
                (
                    RoleInput("referent", spans=(LiteralSpan(0, 1, "A"),)),
                    RoleInput("original_value", spans=(LiteralSpan(7, 11, "dash"),), decimal=True),
                    RoleInput("value_role", label="invented"),
                ),
                "invalid classified/numeric alternatives retained in structural dependencies",
            ),
        ),
    )
    assert len(result.records) == 1
    actual = fields(result.records[0])
    assert actual["original_value"]["state"] == actual["value_role"]["state"] == "unresolved"
    assert any(
        item.role == "value_role" and item.code == "unsupported_field"
        for item in result.diagnostics
    )


def test_missing_native_cell_is_unlocated_and_dash_remains_literal():
    ctx = context(
        "-",
        pieces=[
            dict(
                kind="native_text",
                item_ref="#/tables/0",
                start=0,
                end=1,
                source_field="cell_text",
                cell_index=0,
            )
        ],
        items=[dict(self_ref="#/tables/0", data=dict(table_cells=[dict(text="-")]))],
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="TableRecordFields",
        occurrence_roles=("cell",),
        policy_version="reading-1",
        groups=(
            NativeRecordGroup(
                (
                    RoleInput("cell", native_pointer="#/tables/0/data/table_cells/0"),
                    RoleInput("cell_value", spans=(LiteralSpan(0, 1, "-"),)),
                ),
                "native dash has no inferred numeric/absence meaning",
            ),
            NativeRecordGroup(
                (RoleInput("cell", native_pointer="#/tables/0/data/table_cells/1"),), "missing cell"
            ),
        ),
    )
    assert len(result.records) == 1
    assert fields(result.records[0])["cell_value"]["value"] == {"kind": "text", "text": "-"}
    assert any(
        item.group == 1 and item.code == "unlocated_occurrence" for item in result.diagnostics
    )


def test_discontinuous_literal_retains_exact_pieces_and_nested_evidence():
    ctx = context("normal and gamma")
    result = assemble_native_records(
        release(),
        ctx,
        contract="DefinitionRecordFields",
        occurrence_roles=("term",),
        policy_version="reading-1",
        groups=(
            NativeRecordGroup(
                (
                    RoleInput("term", spans=(LiteralSpan(0, 6, "normal"),)),
                    RoleInput(
                        "defining_text",
                        spans=(LiteralSpan(0, 6, "normal"), LiteralSpan(11, 16, "gamma")),
                    ),
                ),
                "independent discontinuous reading",
            ),
        ),
    )
    actual = fields(result.records[0])
    assert actual["defining_text"]["value"] == {
        "kind": "text_sequence",
        "items": ("normal", "gamma"),
    }
    assert actual["defining_text"]["original_pieces"] == ("normal", "gamma")


def test_report_pack_release_context_and_unlocated_occurrence_controls():
    ctx = context("mean")
    pack = family_pack(release(), contract="DefinitionRecordFields", anchor_role="term")
    raw = report(ctx, pack, "definition", [{"defining_text": span(0, 4, "mean")}])
    result = assemble_records(
        release(),
        ctx,
        pack,
        raw,
        contract="DefinitionRecordFields",
        anchor_role="term",
        policy_version="reading-1",
    )
    assert not result.records and result.raw_report is raw
    assert any(item.code == "unlocated_occurrence" for item in result.diagnostics)
    for changed in (
        replace(raw, pack="foreign"),
        replace(raw, context_id="foreign"),
        replace(raw, context_digest="a" * 64),
    ):
        with pytest.raises(GlinerRefused):
            assemble_records(
                release(),
                ctx,
                pack,
                changed,
                contract="DefinitionRecordFields",
                anchor_role="term",
                policy_version="reading-1",
            )


def test_synthetic_crossing_and_nonpresent_without_inspection_remain_unresolved():
    primary = source("mean 12")
    ctx = NativeSourceContext(
        primary,
        (),
        (SourceSlice(1, 0, 4), SyntheticText("|", "separator"), SourceSlice(1, 5, 7)),
        "reading",
        "policy",
        "explicit",
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="DefinitionRecordFields",
        occurrence_roles=("term",),
        policy_version="reading-1",
        groups=(
            NativeRecordGroup(
                (
                    RoleInput("term", spans=(LiteralSpan(0, 4, "mean"),)),
                    RoleInput("defining_text", spans=(LiteralSpan(0, 7, "mean|12"),)),
                    RoleInput("alias", state="unstated", reason="decoder omitted it"),
                ),
                "unsupported crossing",
            ),
        ),
    )
    actual = fields(result.records[0])
    assert actual["defining_text"]["state"] == actual["alias"]["state"] == "unresolved"
    assert any("synthetic" in item.reason for item in result.diagnostics)


def test_related_source_mapping_is_explicitly_unsupported_without_fake_primary_pin():
    primary, related = source("mean"), source("average", identity=2)
    ctx = NativeSourceContext(
        primary,
        (RelatedNativeSource(related, ContextRelationship.DECLARATION, "independent declaration"),),
        (SourceSlice(1, 0, 4), SourceSlice(2, 0, 7)),
        "reading",
        "policy",
        "explicit",
    )
    result = assemble_native_records(
        release(),
        ctx,
        contract="DefinitionRecordFields",
        occurrence_roles=("term",),
        policy_version="reading-1",
        groups=(
            NativeRecordGroup(
                (
                    RoleInput("term", spans=(LiteralSpan(0, 4, "mean"),)),
                    RoleInput("defining_text", spans=(LiteralSpan(4, 11, "average"),)),
                ),
                "related declaration",
            ),
        ),
    )
    assert fields(result.records[0])["defining_text"]["state"] == "unresolved"
    assert any("cross-view" in item.reason for item in result.diagnostics)
    assert all(
        anchor["pin"]["source_view_id"] == 1 for anchor in result.records[0].model_dump()["anchors"]
    )


def test_exact_duplicate_native_groups_are_not_independent_votes():
    ctx = context("mean mean")
    pack = family_pack(release(), contract="DefinitionRecordFields", anchor_role="term")
    first = {"term": span(0, 4, "mean")}
    raw = report(ctx, pack, "definition", [first, first, {"term": span(5, 9, "mean")}])
    result = assemble_records(
        release(),
        ctx,
        pack,
        raw,
        contract="DefinitionRecordFields",
        anchor_role="term",
        policy_version="reading-1",
    )
    assert len(result.records) == 2
    assert (
        result.records[0].model_dump()["record_id"] != result.records[1].model_dump()["record_id"]
    )
