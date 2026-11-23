"""Physical participant roles and native joins remain separate from semantic support."""

from dataclasses import replace
from typing import Any

import pytest

from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import (
    DeclaredStructuralInput,
    StructuralPassage,
)
from methods.m1_source_preparation_support import (
    native_table_source,
    projection,
    source,
    table_cell,
)
from methods.scoped_relations_support import (
    discover_relations as discover_relations,
)
from methods.scoped_relations_support import (
    original_inputs as original_inputs,
)


def _direct_profile():
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import pipeline

    nlp: Any = pipeline(AnnotationProfile().configuration)
    return nlp.selection().native


@pytest.mark.parametrize("explicit_scope", [True, False])
def test_native_table_roles_notes_and_units_keep_exact_cell_participants(explicit_scope):
    view = native_table_source(
        (
            table_cell("Probability %", 0, 1, column_header=True),
            table_cell("Heads", 1, 0, row_header=True),
            table_cell("50", 1, 1),
            table_cell("50", 2, 1),
        ),
        caption="Table 5.1 Coin",
        note="Only the Heads row uses percentages."
        if explicit_scope
        else "Values are percentages.",
    )
    output = discover_relations(view, source_work="actual-parent-sha")
    rows = output["contributions"]
    values = {
        r["contribution_id"]: (source_python(r["value"]) if "value" in r else {}) for r in rows
    }
    cells = [r for r in rows if values[r["contribution_id"]].get("text") == "50"]
    assert len(cells) == 2 and cells[0]["occurrence_id"] != cells[1]["occurrence_id"]
    relations = [r for r in rows if r["kind"] == "relation"]
    assert {values[r["contribution_id"]]["relation"] for r in relations} >= {
        "header",
        "row_label",
        "unit",
        "value_role",
    }
    note_links = [
        values[r["contribution_id"]]
        for r in relations
        if values[r["contribution_id"]]["relation"] == "note"
    ]
    assert len(note_links) == int(explicit_scope)
    if note_links:
        assert values[note_links[0]["subject_id"]]["start_row_offset_idx"] == 1
    (note,) = [value for value in values.values() if value.get("role") == "note"]
    assert note["table_association"] == "#/tables/0"
    assert all(
        r["standing"] == "retained_private" and r["component"]["interpretation"] == "unassessed"
        for r in relations
    )
    assert all(len(r["members"]) == 2 for r in relations)
    artifact = [
        values[r["contribution_id"]] for r in rows if r["semantic_type"] == "structural.artifact"
    ]
    assert artifact[0]["controlled_code"] == "5.1" and artifact[0]["title"] == "Coin"


def test_symbol_declarations_keep_occurrences_and_do_not_invent_unparsed_order():
    view = source(
        "Let x be a value. Let x be another value. prepare sample before calculate mean.",
        labels=("text",),
    )
    output = discover_relations(view, annotations=())
    rows = output["contributions"]
    values = {
        r["contribution_id"]: (source_python(r["value"]) if "value" in r else {}) for r in rows
    }
    symbols = [r for r in rows if values[r["contribution_id"]].get("role") == "symbol"]
    assert len(symbols) == 2 and symbols[0]["occurrence_id"] != symbols[1]["occurrence_id"]
    relations = [values[r["contribution_id"]]["relation"] for r in rows if r["kind"] == "relation"]
    assert relations.count("declares") == 2 and relations.count("order") == 0
    assert output["extra_operations"][0]["outcome"] == "not_run"


def test_source_without_authenticated_parent_binding_retains_no_artifact_identity():
    view = source("See Table 5.1.", labels=("text",))
    output = discover_relations(view)
    assert not any(r["semantic_type"] == "structural.artifact" for r in output["contributions"])


@pytest.fixture(scope="module", params=("declared", "missing", "incompatible"))
def qualifier_release(request):
    import yaml
    from semantic.record_contracts_support import release_inputs

    from corpus_structure.semantic.prepare import prepare_release

    bundle, profile, prepared = release_inputs()
    if request.param == "declared":
        return request.param, prepared
    updated = []
    for artifact in bundle.sources:
        if artifact.name == "observations":
            module = yaml.safe_load(artifact.content)
            if request.param == "missing":
                del module["classes"]["PredicateQualifierComponent"]
            else:
                slot = module["classes"]["PredicateQualifierComponent"]["attributes"]
                slot["qualifier_kind"]["pattern"] = "^attribution$"
            artifact = replace(artifact, content=yaml.safe_dump(module).encode())
        updated.append(artifact)
    return request.param, prepare_release(replace(bundle, sources=tuple(updated)), profile=profile)


@pytest.mark.parametrize(
    ("text", "host", "competing", "reading"),
    (
        (
            "If the sample includes duplicates, the algorithm computes the mean.",
            "computes",
            "includes",
            "described_process",
        ),
        (
            "Instructions\n"
            "If the manager approves the invoice, the clerk must release the payment.",
            "release",
            "approves",
            "prescribed_action",
        ),
    ),
)
def test_condition_host_preserves_located_parts_after_declaration_refusal(
    qualifier_release, text, host, competing, reading
):
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.predicate_contributions import predicate_qualifier_refusal
    from methods.m1_source_preparation_support import prepare_declared_source

    declaration, release = qualifier_release
    labels = ("section_header", "text") if "\n" in text else ("text",)
    view = source(text, labels=labels)
    prepared = prepare_declared_source(view, profile=AnnotationProfile(), annotations_only=True)
    result = discover_relations(
        view,
        annotations=prepared.annotations,
        annotation_native_profile=_direct_profile(),
        qualifier_preflight=lambda component: predicate_qualifier_refusal(release, component),
    )
    rows = {row["contribution_id"]: row for row in result["contributions"]}
    frames = {}
    for row in rows.values():
        component = row.get("component", {})
        if component.get("kind") == "predicate_frame":
            (member,) = (role for role in component["frame_members"] if role["role"] == "predicate")
            (anchor,) = rows[member["contribution"]]["anchors"]
            frames[anchor["source_piece"]] = row["contribution_id"]
    assert {host, competing} <= frames.keys()
    components = [row.get("component", {}) for row in rows.values()]
    assert any(
        component.get("kind") == "predicate_reading"
        and component["frame"] == frames[host]
        and component["reading"] == reading
        for component in components
    )
    operations = {operation["question"]: operation for operation in result["extra_operations"]}
    assert operations["source_predicate_frames"]["outcome"] == "succeeded"
    interpretation = operations["source_predicate_interpretation"]
    condition_relations = [
        row
        for row in rows.values()
        if row.get("component", {}).get("qualifier_kind") == "condition"
    ]
    emitted_count = interpretation["emitted_count"]
    assert isinstance(emitted_count, int)
    assert emitted_count == sum(
        row["operation_key"] == interpretation["operation_key"] for row in rows.values()
    )
    if declaration == "declared":
        (relation,) = condition_relations
        cue, target = relation["endpoints"]
        assert target == {"role": "host", "contribution_id": frames[host]}
        assert rows[cue["contribution_id"]]["component"]["cue_kind"] == "condition"
        condition = source_python(relation["component"]["condition"])
        assert condition["kind"] == "escape" and condition["text"] in text
        if reading == "prescribed_action":
            assert "qualification" not in relation["component"]
        assert interpretation["outcome"] == "succeeded"
        _assert_public_condition_projection(view, relation, rows, host)
    else:
        assert not condition_relations
        assert interpretation["outcome"] == "limited" and emitted_count > 0
        reason = "is missing" if declaration == "missing" else "differs from"
        detail = interpretation["reason"]
        assert isinstance(detail, str) and reason in detail


def test_selected_action_preserves_wholly_clipped_role_without_an_anchor():
    from corpus_structure.ingest.annotations import AnnotationProfile
    from methods.m1_source_preparation_support import prepare_declared_source

    text = "The analyst records the input."
    view = source(text, labels=("text",))
    prepared = prepare_declared_source(view, profile=AnnotationProfile(), annotations_only=True)
    start = text.index("records")
    selected = StructuralPassage(
        passage_id="action",
        scope="action",
        source_ref="fixture",
        start=start,
        end=start + len("records"),
        text="records",
    )
    output = discover_relations(
        view,
        annotations=prepared.annotations,
        annotation_native_profile=_direct_profile(),
        passages=(selected,),
    )
    (frame,) = [
        row["component"]
        for row in output["contributions"]
        if row.get("component", {}).get("kind") == "predicate_frame"
    ]
    assert not any(role["role"] in {"actor", "object"} for role in frame["frame_members"])
    assert {(role["role"], role["reason"]) for role in frame["unlocated_roles"]} == {
        ("actor", "outside_selection"),
        ("object", "outside_selection"),
    }


def test_named_procedure_reference_binds_verb_to_caption_under_selected_version():
    from corpus_structure.ingest.annotations import AnnotationProfile
    from methods.m1_source_preparation_support import prepare_declared_source

    view = native_table_source(
        (table_cell("1", 0, 0),),
        caption="Table 6.1 Results",
        note="The results are shown in Table 6.1.",
    )
    view = projection(
        view.text,
        pieces=view.pieces,
        items=tuple(
            dict(
                item,
                content_layer="body",
                **({"parent": {"$ref": "#/tables/0"}} if item["label"] == "caption" else {}),
            )
            for item in view.items
        ),
    )
    annotation = prepare_declared_source(view, profile=AnnotationProfile(), annotations_only=True)
    output = discover_relations(
        view,
        source_work="fixture-parent",
        annotations=annotation.annotations,
        annotation_native_profile=_direct_profile(),
        passages=(
            StructuralPassage(
                passage_id="procedure",
                source_ref="fixture",
                scope="procedure",
                effective_version="R1",
                start=0,
                end=len(view.text),
                text=view.text,
            ),
        ),
        witnessed_links_enabled=True,
    )
    rows = {row["contribution_id"]: row for row in output["contributions"]}
    (edge,) = [
        row
        for row in rows.values()
        if row.get("component", {}).get("attachment_kind") == "procedure_reference"
    ]
    action, caption = (source_python(rows[key]["value"]) for key in edge["members"])
    assert (action["role"], action["text"], caption["source_pointer"], caption["text"]) == (
        "procedure_action",
        "shown",
        "#/texts/captions",
        "Table 6.1",
    )
    assert edge["component"]["effective_version"] == "R1"
    assert any(
        rows.get(key, {}).get("component", {}).get("attachment_kind") == "artifact_reference_target"
        for key in edge["computation_dependencies"]
    )


def test_retained_linguistic_roles_join_action_to_its_real_scoped_artifact():
    from methods.structural_roles_support import annotation

    text = "Table 5.1 must be reviewed by Manager."
    view = source(text, labels=("text",))
    frame = view
    product, _construction = annotation(
        text,
        [
            ("Table", "NOUN", "nsubjpass", 4, "NN"),
            ("5.1", "NUM", "nummod", 0, "CD"),
            ("must", "AUX", "aux", 4, "MD"),
            ("be", "AUX", "auxpass", 4, "VB"),
            ("reviewed", "VERB", "ROOT", 4, "VBN"),
            ("by", "ADP", "agent", 4, "IN"),
            ("Manager", "NOUN", "pobj", 5, "NN"),
        ],
        frame=frame,
    )
    from corpus_structure.ingest.annotations import AnnotationProfile

    output = discover_relations(
        frame,
        source_work="parent",
        annotations=(product,),
        annotation_profile=AnnotationProfile(execution_profile="unadmitted:controlled-columns"),
    )
    rows = output["contributions"]
    by_id = {
        r["contribution_id"]: (source_python(r["value"]) if "value" in r else {}) for r in rows
    }
    relations = [r for r in rows if r["kind"] == "relation"]
    links = {
        (source_python(r["value"]) if "value" in r else {}).get("relation"): (
            by_id[r["members"][0]],
            by_id[r["members"][1]],
        )
        for r in relations
    }
    assert links["actor"][0]["text"] == "reviewed" and links["actor"][1]["text"] == "Manager"
    assert links["object"][1]["text"] == "Table 5.1"
    assert links["uses_artifact"][1]["text"] == "Table 5.1"
    from pathlib import Path

    from corpus_structure.semantic.contributions import (
        bind_contributions,
        split_contribution_evidence,
    )
    from corpus_structure.semantic.observations import observation_inputs
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(
        observation_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    bound_operations, bound_rows = bind_contributions(
        prepared,
        source=view.unit_ref,
        operations=(output["operation"], *output["extra_operations"]),
        contributions=tuple(split_contribution_evidence(row)[0] for row in rows),
        coordinate_texts=output["coordinates"],
    )
    assert len(bound_rows) == len(rows)
    assert {op["question"]: op["outcome"] for op in bound_operations} == {
        "source_structural_relations": "succeeded",
        "source_procedure_roles": "succeeded",
        "source_predicate_frames": "succeeded",
        "source_predicate_interpretation": "succeeded",
    }
    operation = output["extra_operations"][0]
    assert operation["outcome"] == "succeeded" and operation["emitted_count"] > 0
    assert all(
        any(dependency.startswith("annotation:") for dependency in r["computation_dependencies"])
        for r in rows
        if r["operation_key"] == operation["operation_key"]
    )


def test_formula_syntax_links_repeated_uses_to_adjacent_local_declaration():
    text = "Let x be count.\nx+x=2"
    view = source(text, labels=("text", "formula"))
    nodes = (
        dict(
            self_ref="#/texts/0",
            label="text",
            text="Let x be count.",
            parent={"$ref": "#/groups/1"},
        ),
        dict(self_ref="#/texts/1", label="formula", text="x+x=2", parent={"$ref": "#/groups/1"}),
    )
    view = projection(view.text, pieces=view.pieces, items=nodes)
    output = discover_relations(view)
    rows = output["contributions"]
    values = {
        r["contribution_id"]: (source_python(r["value"]) if "value" in r else {}) for r in rows
    }
    uses = [r for r in rows if values[r["contribution_id"]].get("role") == "formula_symbol"]
    assert len(uses) == 2 and uses[0]["occurrence_id"] != uses[1]["occurrence_id"]
    assert {values[r["contribution_id"]]["text"] for r in uses} == {"x"}
    assert all(values[r["contribution_id"]]["mapping"] == "exact_native_field" for r in uses)
    assert output["formula_diagnostics"][0]["outcome"] == "parsed"


def test_missing_native_roles_keeps_lexical_contributions_and_failed_stage():
    view = source("Let x be count.", labels=("text",))
    output = discover_relations(
        view,
        annotations=(),
        annotation_errors=("retained parser block failed",),
    )
    assert output["contributions"]
    assert output["operation"]["outcome"] == "succeeded"
    assert output["extra_operations"][0]["outcome"] == "failed"
    assert output["extra_operations"][0]["emitted_count"] == 0


@pytest.mark.parametrize("errors", ((), ("retained block failed",)))
def test_original_annotation_products_keep_roles_without_an_annotation_task(errors):
    from corpus_structure.ingest.annotations import AnnotationProfile
    from methods.structural_roles_support import annotation

    text = "Manager reviews Table 5.1."
    frame = source(text, labels=("text",))
    product, _construction = annotation(
        text,
        [
            ("Manager", "NOUN", "nsubj", 1, "NN"),
            ("reviews", "VERB", "ROOT", 1, "VBZ"),
            ("Table", "NOUN", "dobj", 1, "NN"),
            ("5.1", "NUM", "nummod", 2, "CD"),
        ],
        frame=frame,
    )
    output = discover_relations(
        frame,
        annotations=(product,),
        annotation_errors=errors,
        annotation_profile=AnnotationProfile(execution_profile="unadmitted:controlled-columns"),
        source_work="controlled-parent",
    )
    assert {
        source_python(row["value"]).get("relation")
        for row in output["contributions"]
        if "value" in row
    } >= {"actor", "object", "uses_artifact"}
    assert next(
        operation
        for operation in output["extra_operations"]
        if operation["question"] == "source_procedure_roles"
    )["outcome"] == ("limited" if errors else "succeeded")


@pytest.mark.parametrize("mismatch", ("source-member", "projection"))
def test_original_annotations_refuse_a_changed_selected_source(mismatch):
    from corpus_structure.ingest.annotations import AnnotationProfile
    from methods.structural_roles_support import annotation

    text = "Manager reviews Table."
    frame = source(text, labels=("text",))
    product, _construction = annotation(
        text,
        [
            ("Manager", "NOUN", "nsubj", 1, "NN"),
            ("reviews", "VERB", "ROOT", 1, "VBZ"),
            ("Table", "NOUN", "dobj", 1, "NN"),
        ],
        frame=frame,
    )
    changed = source(
        text if mismatch == "source-member" else text + " changed",
        labels=("text",),
        identity=2 if mismatch == "source-member" else 1,
    )
    with pytest.raises(ValueError, match="selected source carrier"):
        discover_relations(
            changed,
            annotations=(product,),
            annotation_profile=AnnotationProfile(execution_profile="unadmitted:controlled-columns"),
        )


def test_missing_navigation_refuses_without_reparse(monkeypatch):
    from corpus_structure.ingest import annotations
    from corpus_structure.semantic.constructions.navigation import NativeNavigationIndex
    from methods.navigation_fixture import source_primary_products

    frame = source("Let x be count.", labels=("text",))
    primary = source_primary_products(frame, annotations=())
    monkeypatch.setattr(annotations, "pipeline", lambda *_: pytest.fail("consumer reparsed source"))
    primary = replace(primary, navigation=NativeNavigationIndex((), primary.source))
    with pytest.raises(ValueError, match="required primary navigation"):
        discover_relations(frame, primary=primary)


def test_retained_predicate_publication_preserves_exact_hosts_and_refuses_swapped_host():
    from pathlib import Path

    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.semantic.contributions import (
        bind_contributions,
        contribution_identity,
        split_contribution_evidence,
    )
    from corpus_structure.semantic.observations import observation_inputs
    from corpus_structure.semantic.prepare import prepare_release
    from corpus_structure.semantic.types import SourceArtifact, SourceBundle
    from methods.m1_source_preparation_support import prepare_declared_source

    text = (
        "The reviewer must complete the purchase review form if the purchase exceeds the limit, "
        "and the analyst must retain the receipt if the audit remains open."
    )
    view = source(text, labels=("text",))
    annotations = prepare_declared_source(view, profile=AnnotationProfile(), annotations_only=True)
    assert annotations.annotations and not annotations.annotation_errors
    output = discover_relations(
        view,
        annotations=annotations.annotations,
        annotation_native_profile=_direct_profile(),
    )
    rows = output["contributions"]
    by_id = {row["contribution_id"]: row for row in rows}
    conditions = [
        row for row in rows if row.get("component", {}).get("qualifier_kind") == "condition"
    ]

    def predicate(row):
        host = by_id[row["component"]["host_contribution_id"]]
        member = next(m for m in host["component"]["frame_members"] if m["role"] == "predicate")
        assert host["component"]["focus_state"] == "exact"
        return by_id[member["contribution"]]["anchors"][0]["source_piece"]

    assert {
        predicate(row): source_python(row["component"]["condition"])["text"] for row in conditions
    } == {"complete": "if the purchase exceeds the limit", "retain": "if the audit remains open"}
    first, second = conditions
    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(
        observation_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )

    def bind(population):
        return bind_contributions(
            prepared,
            source=view.unit_ref,
            operations=(output["operation"], *output["extra_operations"]),
            contributions=tuple(split_contribution_evidence(row)[0] for row in population),
            coordinate_texts=output["coordinates"],
        )

    bind(rows)
    old_host, new_host = (row["component"]["host_contribution_id"] for row in conditions)

    def change_host(values):
        return tuple(new_host if value == old_host else value for value in values)

    forged = {
        **first,
        "members": change_host(first["members"]),
        "endpoints": (first["endpoints"][0], second["endpoints"][1]),
        "computation_dependencies": change_host(first["computation_dependencies"]),
        "component": {
            **first["component"],
            "host_contribution_id": new_host,
            "dependencies": change_host(first["component"]["dependencies"]),
        },
    }
    forged["contribution_id"] = contribution_identity(forged)
    with pytest.raises(ValueError, match="exact proposed predicate host"):
        bind(tuple(forged if row is first else row for row in rows))


def test_named_coverage_counts_selected_blocks_once_and_does_not_assume_absence():
    from corpus_structure.methods.witnessed_source_links import match_named_source_links
    from methods.navigation_fixture import source_primary_products

    view = native_table_source(
        (table_cell("1", 0, 0),), caption="Table 6.1", note="A value is reported."
    )
    view = projection(
        view.text,
        pieces=view.pieces,
        items=tuple(dict(item, content_layer="body") for item in view.items),
    )
    items = {item["self_ref"]: item for item in view.items}
    primary = source_primary_products(view)
    unavailable = source_primary_products(view, annotations=())
    passages = tuple(
        StructuralPassage(
            passage_id=f"p-{i}",
            source_ref="fixture",
            scope="chapter",
            start=0,
            end=len(view.text),
            text=view.text,
        )
        for i in range(2)
    )
    arguments = (view.text, view.pieces, items, passages)
    verified = match_named_source_links(*arguments, navigation=primary.navigation)
    assert (verified.inspected_count, verified.outcome()) == (1, "empty")
    absent = match_named_source_links(*arguments, navigation=unavailable.navigation)
    assert (absent.inspected_count, absent.outcome()) == (0, "unsupported")
    unselected = match_named_source_links(
        view.text,
        view.pieces,
        items,
        (),
        navigation=unavailable.navigation,
        annotation_errors=("another block failed",),
    )
    assert (unselected.inspected_count, unselected.outcome()) == (0, "empty")


def _assert_public_condition_projection(view, relation, rows, predicate):
    from corpus_structure.methods.structural_products import condition_qualification
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.structural_admission import structural_statement
    from corpus_structure.semantic.structural_products import DeclaredStructuralProductReport

    pin = relation["pin"]
    scope = relation["component"]["scope"]
    selected = DeclaredStructuralSource.model_validate(pin)
    attachment = relation["contribution_id"]
    project_id = pin["project_id"]
    inputs = DeclaredStructuralInput(
        question="Which condition limits this predicate?",
        scope=scope,
        inventory_id="frozen",
        policy_id="source-only",
        sources=(selected,),
        dependencies=("source",),
        passages=(
            StructuralPassage(
                passage_id=scope,
                source_ref=selected.identity,
                start=0,
                end=len(view.text),
                text=view.text,
                scope=scope,
            ),
        ),
    )
    payload = {
        "contributions": tuple(rows.values()),
        "sources": [{"pin": pin, "projection": {"text": view.text, "pieces": view.pieces}}],
    }

    def changed_components(changes):
        return {
            **payload,
            "contributions": [
                {**row, "component": {**row["component"], **changes[row["contribution_id"]]}}
                if row["contribution_id"] in changes
                else row
                for row in payload["contributions"]
            ],
        }

    projected = condition_qualification(inputs, attachment, payload, project_id=project_id)
    assert projected.attachment == {
        "variant": "member",
        "role": "report",
        "member_id": "contribution:" + attachment,
    }
    report = DeclaredStructuralProductReport(
        kind="condition_qualification",
        inputs=inputs,
        condition_qualification=projected,
    )
    statement = structural_statement(report)["condition_qualification"]
    assert statement["relation"] == "condition"
    assert statement["qualifier"][0]["passage"]["text"].startswith("If ")
    assert statement["host_predicate"][0]["passage"]["text"] == predicate
    assert "attachment" not in statement
    original = inputs.passages[0]
    other_version = original.model_copy(
        update={"passage_id": "other-source-version", "effective_version": "revision-2"}
    )
    versioned = inputs.model_copy(update={"passages": (original, other_version)})
    assert (
        condition_qualification(versioned, attachment, payload, project_id=project_id) == projected
    )

    qualifier_id = relation["component"]["qualifier_contribution_id"]
    cue = next(row for row in payload["contributions"] if row["contribution_id"] == qualifier_id)
    changed = changed_components(
        {qualifier_id: {"candidate_tokens": (*cue["component"]["candidate_tokens"], 1000)}}
    )
    with pytest.raises(ValueError, match="uniquely located host"):
        condition_qualification(inputs, attachment, changed, project_id=project_id)

    # An assumption in the condition family remains an assumption in public
    # meaning; the cue and relation must declare the same subtype.
    changed = changed_components(
        {
            attachment: {"qualifier_kind": "assumption"},
            qualifier_id: {"cue_kind": "assumption"},
        }
    )
    assumption = condition_qualification(inputs, attachment, changed, project_id=project_id)
    assert assumption.relation == "assumption"


def test_sentence_to_scoped_relations_reuses_derived_views(monkeypatch):
    from collections import Counter
    from functools import cached_property

    from corpus_structure import caches
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.semantic import formal_readings, source_products
    from corpus_structure.semantic.constructions import navigation
    from corpus_structure.semantic.data_operation_population import AcquiredPopulation
    from methods.navigation_fixture import source_primary_products
    from methods.structural_roles_support import annotation

    text = "Table 5.1 must be reviewed by Manager."
    frame = source(text, labels=("text",))
    columns, _ = annotation(
        text,
        [
            ("Table", "NOUN", "nsubjpass", 4, "NN"),
            ("5.1", "NUM", "nummod", 0, "CD"),
            ("must", "AUX", "aux", 4, "MD"),
            ("be", "AUX", "auxpass", 4, "VB"),
            ("reviewed", "VERB", "ROOT", 4, "VBN"),
            ("by", "ADP", "agent", 4, "IN"),
            ("Manager", "NOUN", "pobj", 5, "NN"),
        ],
        frame=frame,
    )
    caches.clear("runtime_bytes")
    builds = {}

    def count_loader(owner):
        counts = Counter()
        builds[owner.name] = counts
        original = owner.loader

        def load(*args, **kwargs):
            counts[owner.key(*args, **kwargs)] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(owner, "loader", load)

    for owner in (
        source_products._native_source_view,
        source_products._native_source_selectors,
        formal_readings._retained_index,
        navigation._navigation_index,
    ):
        count_loader(owner)
    rows_built = Counter()
    original_rows = AcquiredPopulation._rows.func

    def decoded_rows(population):
        rows_built[id(population)] += 1
        return original_rows(population)

    rows = cached_property(decoded_rows)
    rows.__set_name__(AcquiredPopulation, "_rows")
    monkeypatch.setattr(AcquiredPopulation, "_rows", rows)
    primary = source_primary_products(
        frame,
        annotations=(columns,),
        profile=AnnotationProfile(execution_profile="unadmitted:controlled-columns"),
    )
    expected = discover_relations(frame, primary=primary, source_work="parent")
    from corpus_structure.semantic.sentence_partitions import produce_sentence_populations
    from corpus_structure.semantic.sentence_products import SourceAnnotations
    from methods.declared_primary_fixture import profiles

    native = primary.native
    assert native is not None
    kind = next(kind for kind in native.model.kinds if kind.name == "DdoSourceAnnotations")
    populations = produce_sentence_populations(native.partition_blocks, native.prepared, kind)
    typed = SourceAnnotations(
        native.content,
        native.prepared,
        native.model,
        (),
        subject_context=native.subject_context,
        populations=populations,
    )
    _, construction_profile = profiles()
    built = construction_profile.run(
        primary.source, (primary.formal,), sentences=typed, subject_context=primary.context
    )
    primary = replace(
        primary,
        native=typed,
        construction=built,
        navigation=navigation.NativeNavigationIndex((built,), primary.source),
    )
    first = discover_relations(frame, primary=primary, source_work="parent")
    second = discover_relations(frame, primary=primary, source_work="parent")
    assert first == second == expected
    values = [source_python(row["value"]) for row in first["contributions"] if "value" in row]
    assert any(value.get("relation") == "uses_artifact" for value in values)
    assert rows_built and set(rows_built.values()) == {1}
    for counts in builds.values():
        assert counts and set(counts.values()) == {1}
