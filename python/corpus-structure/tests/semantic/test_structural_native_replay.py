"""Native deterministic replay checks, separate from source-custody qualification."""

import json
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.structural_products import compare_clauses
from corpus_structure.semantic.structural_admission import structural_statement
from semantic.native_record_fixtures import RecordSourceRecipe
from semantic.native_record_fixtures import private_source as private_source
from semantic.typed_structural_composition_support import revision_inputs, threshold_inputs

_COMPARISON_LITERALS = (
    ("Date: 2024-02-29", {"kind": "date", "value": "2024-02-29"}),
    ("Date: 2026-02-29", None),
    ("Identifier: Rule.R3", {"kind": "identifier", "value": "Rule.R3"}),
    ("Quantity: +2.50e1 kg", {"kind": "quantity", "value": "25", "unit": "kg"}),
    (
        "Range: [1, 2) kg",
        dict(kind="range", lower="1", upper="2", lower_closed=True, upper_closed=False, unit="kg"),
    ),
    (
        "Range: (1, 2] kg",
        dict(kind="range", lower="1", upper="2", lower_closed=False, upper_closed=True, unit="kg"),
    ),
    ("Range: (1, 1] kg", None),
    ("Report dated 2024-02-29", None),
    ("Quantity: 1e1000 kg", None),
    ("Quantity: 1e1000000 kg", None),
    ("Quantity: 1e100 kg", dict(kind="quantity", value="1" + "0" * 100, unit="kg")),
    ("Quantity: 1e101 kg", None),
    ("Quantity: 1e-100 kg", dict(kind="quantity", value="0." + "0" * 99 + "1", unit="kg")),
    ("Quantity: 1e-101 kg", None),
    ("Quantity: 1e-1000000 kg", None),
    ("Quantity: -0e1000 kg", dict(kind="quantity", value="0", unit="kg")),
    (
        "Range: [1e-100, 1e100] kg",
        dict(
            kind="range",
            lower="0." + "0" * 99 + "1",
            upper="1" + "0" * 100,
            lower_closed=True,
            upper_closed=True,
            unit="kg",
        ),
    ),
    ("Range: [1e-101, 1] kg", None),
    ("Range: [0, 1e101] kg", None),
    ("Identifier: " + "A" * 244, dict(kind="identifier", value="A" * 244)),
    ("Identifier: " + "A" * 245, None),
)


def _captured_comparison_inputs(case, inputs):
    from corpus_structure.semantic.source_views import load_source_view

    with case.writer.connect() as conn:
        view = load_source_view(conn, case.other_view, analysis=False)
    source = inputs.sources[0].model_copy(
        update=dict(
            project_id=case.project_id,
            run_id=case.run,
            release_id=case.prepared.release_id,
            source_view_id=view.ref.id,
            native_task_id=view.ref.native_product.task_id,
            native_product_key=view.ref.native_product.product_key,
            native_content_digest=view.ref.native_product.content_digest,
            projection_digest=view.ref.projection_digest,
            recipe_digest=view.ref.recipe_digest,
        )
    )
    passages = tuple(
        p.model_copy(
            update=dict(
                source_ref=source.identity,
                start=view.text.index(p.text),
                end=view.text.index(p.text) + len(p.text),
            )
        )
        for p in inputs.passages
    )
    return inputs.model_copy(update=dict(sources=(source,), passages=passages)), view


def _captured_formal_layers(view):
    from corpus_structure.semantic.formal_evidence import build_formal_layer, grammar_identity
    from semantic.primary_formal_fixture import release

    layer = build_formal_layer(
        view,
        release(),
        dict(
            key="text.formal_evidence",
            version="1",
            runtime="fixture",
            model="none",
            grammar=grammar_identity(),
            configuration="fixture",
            input="fixture",
            context="source-only",
        ),
    )
    return {layer.reference(1000 + view.ref.id): layer}


def _primary_wire(layers):
    from corpus_structure.semantic.identity import canonical_bytes

    return {canonical_bytes(pin.values()).decode(): layer.payload for pin, layer in layers.items()}


def _captured_clause(passage, source, layers):
    from corpus_structure.methods.structural_products import threshold_readings
    from corpus_structure.semantic.structural_products import ClauseField, ClauseReading

    fields = [
        ClauseField(dimension=dimension, lexical_value=value, evidence=(passage.passage_id,))
        for dimension, value in (("parent", passage.parent), ("version", passage.effective_version))
        if value
    ]
    thresholds = threshold_readings(passage, source=source, primary_layers=layers)
    if len(thresholds) == 1:
        fields.extend(thresholds)
    return ClauseReading(passage_id=passage.passage_id, fields=tuple(fields))


@pytest.mark.parametrize(
    "left,right,private_source",
    [
        (*pair, RecordSourceRecipe(sibling_references=pair))
        for pair in [
            ("revenue > 25000 USD", "revenue > 50000 USD"),
            (
                "revenue > 25000 USD\nComparison basis: annual gross revenue.",
                "revenue > 50000 USD\nComparison basis: annual gross revenue.",
            ),
            ("x > 2 kg", "x > 5 kg\nRevision R2 supersedes revision R1."),
            (
                "Clause rule.\nRevision R1.\nx > 2 kg",
                "Clause rule.\nRevision R2 supersedes revision R1.\nx > 5 kg",
            ),
            ("revenue >= 25000 USD", "revenue > 25000 USD"),
            ("revenue < 50000 USD", "revenue <= 25000 USD"),
            ("x > 2", "x > 5"),
            ("x > 2 kg and y > 3 kg", "x > 5 kg"),
            ("prefix. x ≥ +2.00e2 kg", "x >= 200 kg"),
            ("x > 2. kg", "x > 2 kg"),
            (
                "Manager must approve Table 5.1 if revenue > 25000 USD unless account is closed.",
                "Manager must approve Table 5.1 if revenue > 50000 USD unless account is closed.",
            ),
            (
                "Table 5.1 must be approved by Manager if revenue > 25000 USD.",
                "Table 5.1 must be approved by Analyst if revenue > 25000 USD.",
            ),
            (
                "If revenue > 25000 USD, Manager must approve Table 5.1 before signing.",
                "Nothing is prescribed.",
            ),
            ("Manager must approve Table; Analyst may reject Form.", "Manager may review Table."),
        ]
    ],
    indirect=("private_source",),
)
def test_native_comparison_replays_same_source_route(
    record_source_admin, private_source, left, right
):
    inputs = threshold_inputs(left, right)
    if "supersedes" in right:
        inputs = revision_inputs(left, right)
    inputs, view = _captured_comparison_inputs(private_source, inputs)
    primary = _captured_formal_layers(view)
    source = inputs.sources[0]
    a, b = (_captured_clause(passage, source, primary) for passage in inputs.passages)
    expected = compare_clauses(inputs, left=a, right=b, primary_layers=primary)
    with record_source_admin.connect() as conn, conn.begin():
        actual = conn.scalar(
            text("""SELECT ops.structural_compare_lexical(
                CAST(:inputs AS jsonb),:left,:right,
                CAST(:left_fields AS jsonb),CAST(:right_fields AS jsonb),CAST(:primary AS jsonb))
            """),
            dict(
                inputs=inputs.model_dump_json(),
                primary=json.dumps({source.identity: _primary_wire(primary)}),
                left=inputs.passages[0].passage_id,
                right=inputs.passages[1].passage_id,
                left_fields=json.dumps(
                    {f.dimension: f.model_dump(mode="json", exclude_none=True) for f in a.fields}
                ),
                right_fields=json.dumps(
                    {f.dimension: f.model_dump(mode="json", exclude_none=True) for f in b.fields}
                ),
            ),
        )
        comparison = expected.model_dump(mode="json", exclude_none=True)["comparison"]
        assert actual == comparison
        public = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:report AS jsonb),NULL)"),
            dict(report=expected.model_dump_json(exclude_none=True)),
        )
        assert public == structural_statement(expected)


def test_native_dossier_replays_membership_after_reader_boundary(commit_db_engine):
    """Isolate composition after the reader; this is not reader/provider qualification."""
    from corpus_structure.methods.structural_products import derive_dossier_members, select_dossier
    from corpus_structure.semantic.structural_products import (
        DefinitionComponentsProduct,
        LocatedDefinitionSpan,
        RetainedComponentRef,
        RetainedStructuralRef,
        StructuralProductReport,
        definition_component,
    )

    inputs = threshold_inputs("term is defining content", "unrelated candidate context")
    p = inputs.passages[0]
    term = LocatedDefinitionSpan(passage_id=p.passage_id, start=0, end=4, text="term")
    content = LocatedDefinitionSpan(
        passage_id=p.passage_id, start=8, end=24, text="defining content"
    )
    component = definition_component(
        term=term,
        content=content,
        interpretation="definition",
        basis="matched_cue",
        scope=p.scope,
        evidence=(p.passage_id,),
        reason="Explicit source cue.",
    )
    unrelated = definition_component(
        term=LocatedDefinitionSpan(passage_id="b", start=0, end=9, text="unrelated"),
        content=LocatedDefinitionSpan(passage_id="b", start=10, end=27, text="candidate context"),
        interpretation="definition",
        basis="matched_cue",
        scope=inputs.passages[1].scope,
        evidence=("b",),
        reason="Separate source and sense.",
    )
    predecessor = StructuralProductReport(
        kind="definition_components",
        inputs=inputs,
        definition_components=DefinitionComponentsProduct(
            components=(component, unrelated), stages=()
        ),
    )
    ref = RetainedStructuralRef(
        product_id=predecessor.product_id,
        project_id="p",
        run_id=1,
        cut_id=1,
        release_id="r",
        result_revision=1,
        selected_task_id=1,
        origin_task_id=1,
        runtime_fingerprint="runtime",
    )
    inputs = inputs.model_copy(
        update=dict(dependencies=(*inputs.dependencies, predecessor.product_id))
    )
    root = RetainedComponentRef(
        **ref.model_dump(),
        component_id=component.component_id,
        operation_id="structure.definition_components",
        operation_version="5",
        dependencies=predecessor.inputs.dependencies,
    )
    payload = dict(
        report=predecessor.model_dump(mode="json", exclude_none=True),
        public_assertions=[
            dict(
                assessment_id="protected-reader-fixture",
                statement=structural_statement(predecessor, component.component_id),
            )
        ],
    )
    members, facets = derive_dossier_members(inputs, ((ref, payload),), root=component)
    report = select_dossier(
        inputs,
        root_id=root.component_id,
        root_component=root,
        members=members,
        supported_facets=facets,
        predecessors=(ref,),
        member_budget=1,
    )
    config = dict(
        root_component=root.model_dump(mode="json"),
        predecessors=[ref.model_dump(mode="json")],
        member_budget=1,
        policy="supported-facet-greedy-1",
    )
    sql = Path(__file__).parents[2] / "src/corpus_structure/semantic/sql"
    with commit_db_engine.connect() as conn, conn.begin():
        for file in (
            "dossier_contributions.sql",
            "structural_products.sql",
            "structural_publication.sql",
        ):
            conn.exec_driver_sql(
                (sql / file).read_text(), execution_options={"no_parameters": True}
            )
        conn.execute(
            text("SELECT set_config('test.structural_payload',:payload,true)"),
            dict(payload=json.dumps(payload)),
        )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.resolve_retained_structural_report(ref jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $$ "
            "SELECT current_setting('test.structural_payload')::jsonb $$"
        )
        conn.execute(
            text("SELECT set_config('test.dossier_root',:component,true)"),
            dict(component=component.model_dump_json(exclude_none=True)),
        )
        conn.exec_driver_sql(
            "CREATE OR REPLACE FUNCTION ops.resolve_retained_component(ref jsonb) "
            "RETURNS jsonb LANGUAGE sql STABLE AS $$ "
            "SELECT jsonb_build_object('component',current_setting('test.dossier_root')::jsonb) $$"
        )
        actual = conn.scalar(
            text("SELECT ops.structural_dossier(CAST(:inputs AS jsonb),CAST(:config AS jsonb))"),
            dict(inputs=inputs.model_dump_json(exclude_none=True), config=json.dumps(config)),
        )
        assert report.dossier is not None
        assert actual == report.dossier.model_dump(mode="json", exclude_none=True)
        public = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:report AS jsonb),NULL)"),
            dict(report=report.model_dump_json(exclude_none=True)),
        )
        assert public == structural_statement(report)
        assert len(actual["members"]) == 2 and {m["passage_id"] for m in actual["members"]} == {"a"}


def test_native_representation_projects_only_selected_member_closure(commit_db_engine):
    from corpus_structure.methods.structural_products import select_dossier
    from corpus_structure.semantic.structural_products import DossierMember, LocatedDefinitionSpan
    from corpus_structure.serve.structural_products import _DOSSIER_SLICE_SQL

    inputs = threshold_inputs("retained source", "uncited source")
    p = inputs.passages[0]
    citation = LocatedDefinitionSpan(passage_id=p.passage_id, start=p.start, end=p.end, text=p.text)
    members = tuple(
        DossierMember(
            member_id=str(i),
            passage_id=p.passage_id,
            citation=citation,
            role="exception",
            scope=p.scope,
            sense="unresolved",
            relation_product_id="upstream",
        )
        for i in range(3)
    )
    report = select_dossier(inputs, root_id="root", members=members, member_budget=1)
    sql = _DOSSIER_SLICE_SQL.replace(
        "SELECT body->'structural_product' report FROM ops.task_result WHERE task_id=:origin_id",
        "SELECT CAST(:report AS jsonb) report",
    ).replace("{projection}", "body")
    with commit_db_engine.connect() as conn:
        result = conn.scalar(
            text(sql),
            dict(report=report.model_dump_json(exclude_none=True), offset=1, end_offset=2),
        )
    assert [m["member_id"] for m in result["members"]] == ["1"]
    assert (
        len(result["citations"]) == 1
        and result["citations"][0]["citation"]["text"] == "retained source"
    )
    assert result["citations"][0]["source"] == inputs.sources[0].model_dump(mode="json")
    assert result["supported_facets"] == []


def test_native_note_scope_checks_the_whole_original_note(commit_db_engine):
    from methods.m1_source_preparation_support import native_table_source, table_cell
    from methods.scoped_relations_support import complete_native_fields, discover_relations

    from corpus_structure.semantic.observations import source_python
    from corpus_structure.semantic.proposals import native_source_frame

    note_text = "Only the Heads row uses percentages."
    view = complete_native_fields(
        native_table_source(
            (
                table_cell("Probability %", 0, 1, column_header=True),
                table_cell("Heads", 1, 0, row_header=True),
                table_cell("50", 1, 1),
                table_cell("50", 2, 1),
            ),
            note=note_text,
        )
    )
    from corpus_structure.semantic.identity import canonical_bytes

    output = discover_relations(native_source_frame(view, ()))
    rows = output["contributions"]
    layers = {
        canonical_bytes(pin.values()).decode(): layer.payload
        for pin, layer in output["_primary_layers"].items()
    }
    physical = dict(
        id=view.ref.id,
        key=view.ref.key,
        native_task_id=view.ref.native_product.task_id,
        native_product_key=view.ref.native_product.product_key,
        native_content_digest=view.ref.native_product.content_digest,
        projection_digest=view.ref.projection_digest,
        recipe_digest=view.ref.recipe_digest,
        projection=dict(text=view.text, pieces=view.pieces),
    )
    note = next(r for r in rows if source_python(r["value"]).get("role") == "note")
    (anchor,) = note["anchors"]
    original = {item["self_ref"]: dict(item) for item in view.items}

    def bind(conn, items):
        conn.execute(
            text("SELECT set_config('test.note_native_items',:items,true)"),
            {"items": json.dumps(items)},
        )

    replay = text(
        "SELECT ops.validate_source_table_note_scope("
        "jsonb_populate_record(NULL::kb.source_view,CAST(:physical AS jsonb)),"
        "CAST(:rows AS jsonb),CAST(:layers AS jsonb))"
    )
    with commit_db_engine.connect() as conn, conn.begin():
        # Isolate the installed scope guard after the owned raw-item boundary.
        conn.exec_driver_sql("""
            CREATE OR REPLACE FUNCTION ops.read_pdf_published_items(
                p_task bigint,p_product text,p_digest text,p_pointers text[])
            RETURNS TABLE(product_id text,revision_id text,pointer text,ordinal bigint,
                label text,parent_pointer text,section_pointer text,content_layer text,
                text text,native_json jsonb) LANGUAGE sql STABLE AS $$
                SELECT NULL::text,NULL::text,p,NULL::bigint,NULL::text,NULL::text,
                    NULL::text,NULL::text,item->>'text',item
                FROM unnest(p_pointers) p
                CROSS JOIN LATERAL (
                    SELECT current_setting('test.note_native_items')::jsonb->p AS item
                ) value
            $$
        """)
        bind(conn, original)
        conn.execute(
            replay,
            {
                "rows": json.dumps(rows),
                "layers": json.dumps(layers),
                "physical": json.dumps(physical),
            },
        )

        prefix = "Do not apply the following statement. "
        original[anchor["pointer"]]["text"] = prefix + note_text
        anchor["start"], anchor["end"] = len(prefix), len(prefix) + len(note_text)
        bind(conn, original)
        with (
            pytest.raises(DBAPIError, match="requires the whole original note"),
            conn.begin_nested(),
        ):
            conn.execute(
                replay,
                {
                    "rows": json.dumps(rows),
                    "layers": json.dumps(layers),
                    "physical": json.dumps(physical),
                },
            )


@pytest.mark.parametrize(
    "connector,expected_group,expected_typed,private_source",
    [
        (
            *case,
            RecordSourceRecipe(
                sibling_references=(
                    f"Clerk must file Form {case[0]} Form if X > 5 kg. No exceptions.",
                    "Reviewer may file Form and Report if X > 7 kg.",
                )
            ),
        )
        for case in [
            ("and", "conjunction", "unknown"),
            ("or", "disjunction", "unknown"),
            ("as well as", "unresolved", "ambiguous"),
        ]
    ],
    indirect=("private_source",),
)
def test_retained_comparison_groups_exact_occurrences(
    record_source_admin, private_source, connector, expected_group, expected_typed
):
    from corpus_structure.methods.structural_products import read_retained_clause
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef

    inputs = threshold_inputs(
        f"Clerk must file Form {connector} Form if X > 5 kg. No exceptions.",
        "Reviewer may file Form and Report if X > 7 kg.",
    )

    inputs, view = _captured_comparison_inputs(private_source, inputs)

    def retained_side(passage, source):
        reference = RetainedContributionRef(
            contribution_id="source-contribution:" + "a" * 64,
            project_id=source.project_id,
            run_id=1,
            cut_id=1,
            release_id=source.release_id,
            result_revision=0,
            selected_task_id=1,
            origin_task_id=1,
            runtime_fingerprint="runtime",
        )
        pin = {
            "source_view_id": source.source_view_id,
            "native_product_task_id": source.native_task_id,
            "product_digest": source.native_content_digest,
            "projection_digest": source.projection_digest,
            "recipe_digest": source.recipe_digest,
        }

        def extent(spelling, at=0):
            start = passage.start + passage.text.index(spelling, max(0, at - passage.start))
            return {"start": start, "end": start + len(spelling)}

        first = extent("Form")
        second = extent("Form" if "Clerk" in passage.text else "Report", first["end"])
        actor, modal = ("Clerk", "must") if "Clerk" in passage.text else ("Reviewer", "may")
        component = {"scope": passage.passage_id}
        rows = [
            {
                "contribution_id": reference.contribution_id,
                "pin": pin,
                "component": {**component, "kind": "predicate_reading", "frame": "frame"},
            },
            {
                "contribution_id": "frame",
                "pin": pin,
                "component": {
                    **component,
                    "kind": "predicate_frame",
                    "frame_members": [
                        dict(
                            role="actor",
                            contribution="actor",
                            outcome="complete",
                            extents=[extent(actor)],
                        ),
                        dict(
                            role="predicate",
                            contribution="predicate",
                            outcome="complete",
                            extents=[extent("file")],
                        ),
                        dict(
                            role="object", contribution="first", outcome="complete", extents=[first]
                        ),
                        dict(
                            role="object",
                            contribution="second",
                            outcome="complete",
                            extents=[second],
                        ),
                    ],
                },
            },
            {
                "contribution_id": "modal",
                "component": dict(
                    kind="predicate_qualifier",
                    host_contribution_id="frame",
                    qualifier_contribution_id="modal-cue",
                    qualifier_kind="modality",
                ),
            },
            {
                "contribution_id": "modal-cue",
                "pin": pin,
                "component": {"extents": [extent(modal)]},
            },
        ]
        if "No exceptions." in passage.text:
            rows.extend(
                (
                    {
                        "contribution_id": "exception",
                        "component": dict(
                            kind="predicate_qualifier",
                            host_contribution_id="frame",
                            qualifier_contribution_id="exception-cue",
                            qualifier_kind="exception",
                        ),
                    },
                    {
                        "contribution_id": "exception-cue",
                        "pin": pin,
                        "component": {"extents": [extent("No exceptions.")]},
                    },
                )
            )
        return reference, rows

    left, right = inputs.passages
    sources = {source.identity: source for source in inputs.sources}
    ls, rs = sources[left.source_ref], sources[right.source_ref]
    lr, lrows = retained_side(left, ls)
    rr, rrows = retained_side(right, rs)
    # Each comparison side has its own retained producer and original view.
    rr = rr.model_copy(update={"selected_task_id": 2, "origin_task_id": 2})
    primary = _captured_formal_layers(view)
    a = read_retained_clause(left, ls, lr, {"contributions": lrows}, primary_layers=primary)
    b = read_retained_clause(right, rs, rr, {"contributions": rrows}, primary_layers=primary)
    report = compare_clauses(
        inputs, left=a, right=b, left_reading=lr, right_reading=rr, primary_layers=primary
    )
    comparison = report.comparison
    assert comparison is not None
    object_ = comparison.dimensions[2]
    group = object_.left_group
    assert group is not None
    assert group.grouping == expected_group
    assert object_.typed_outcome == expected_typed
    assert [m.lexical_value for m in group.members] == ["Form", "Form"]
    assert [m.spans[0].start for m in group.members if m.spans] == [
        left.text.index("Form"),
        left.text.rindex("Form"),
    ]
    assert comparison.dimensions[0].outcome == "different_lexical_value"
    assert comparison.dimensions[3].outcome == "different_lexical_value"
    for index in (4, 5):
        missing = comparison.dimensions[index].left_group
        assert missing is not None and missing.state == "absent"
    exception = comparison.dimensions[6]
    assert exception.left_group is not None and exception.left_group.state == "empty"
    # The primary fact witnesses the phrase; the original sentence terminator
    # remains in the retained clause rather than enlarging the lexical marker.
    (empty_span,) = exception.left_group.witnesses
    empty_start = left.start + left.text.index("No exceptions")
    assert (empty_span.start, empty_span.end, empty_span.text) == (
        empty_start,
        empty_start + len("No exceptions"),
        "No exceptions",
    )
    (empty_ref,) = exception.left_group.primary_witnesses
    empty_fact = next(
        row
        for row in primary[empty_ref.layer].payload["annotations"]
        if row["local_id"] == empty_ref.local_id
    )
    assert empty_fact["kind"] == "formal.exception_empty" and empty_fact["native_label"] == "empty"
    assert exception.right_group is not None and exception.right_group.state == "absent"

    with record_source_admin.connect() as conn, conn.begin():
        actual = conn.scalar(
            text("""SELECT ops.comparison_groups(
                CAST(:passage AS jsonb),CAST(:source AS jsonb),
                CAST(:ref AS jsonb),CAST(:rows AS jsonb),CAST(:primary AS jsonb))
            """),
            dict(
                passage=left.model_dump_json(),
                source=ls.model_dump_json(),
                ref=lr.model_dump_json(),
                rows=json.dumps(lrows),
                primary=json.dumps(_primary_wire(primary)),
            ),
        )
        assert actual == a.model_dump(mode="json", exclude_none=True)["groups"]
        public = conn.scalar(
            text("SELECT data.structural_public_statement(CAST(:report AS jsonb),NULL)"),
            dict(report=report.model_dump_json(exclude_none=True)),
        )
        assert public == structural_statement(report)


@pytest.mark.parametrize(
    "private_source",
    [
        RecordSourceRecipe(
            sibling_references=tuple(spelling for spelling, _expected in _COMPARISON_LITERALS)
        )
    ],
    indirect=True,
    ids=("comparison-literals",),
)
def test_comparison_literals_are_bounded_and_agree_with_native(record_source_admin, private_source):
    from corpus_structure.methods.structural_products import _literal_reading

    value = threshold_inputs(_COMPARISON_LITERALS[0][0], _COMPARISON_LITERALS[0][0])
    value = value.model_copy(update=dict(passages=(value.passages[0],)))
    inputs, view = _captured_comparison_inputs(private_source, value)
    primary = _captured_formal_layers(view)
    source = inputs.sources[0]
    with record_source_admin.connect() as conn, conn.begin():
        for spelling, expected in _COMPARISON_LITERALS:
            start = view.text.index(spelling)
            passage = inputs.passages[0].model_copy(
                update=dict(text=spelling, start=start, end=start + len(spelling))
            )
            literal, reference = _literal_reading(passage, source, primary)
            assert (
                literal.model_dump(mode="json", exclude_none=True) if literal else None
            ) == expected
            actual = conn.scalar(
                text(
                    "SELECT ops.comparison_literal(CAST(:passage AS jsonb),"
                    "CAST(:source AS jsonb),CAST(:primary AS jsonb))"
                ),
                dict(
                    passage=passage.model_dump_json(),
                    source=source.model_dump_json(),
                    primary=json.dumps(_primary_wire(primary)),
                ),
            )
            assert actual.get("literal") == expected
            if reference is not None:
                assert actual["primary_formal"] == reference.values()
