"""Physical participant roles and native joins remain separate from semantic support."""

from dataclasses import replace
from types import SimpleNamespace

import pytest

from corpus_structure.core.method import UnitRef
from corpus_structure.core.vocab import TaskUnitType
from corpus_structure.methods.scoped_relations import (
    ScopedRelationsConfig,
    ScopedRelationsMethod,
    SourceWorkBinding,
    discover_relations,
)
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.proposals import native_source_frame
from corpus_structure.semantic.structural_products import (
    ExternalSourceRef,
    StructuralInput,
    StructuralPassage,
)

from .test_m1_source_preparation import native_table_source, source, table_cell


def complete_native_fields(view):
    nodes = {node["self_ref"]: dict(node) for node in view.items}
    for piece in view.pieces:
        if piece.get("kind") == "native_text" and piece.get("cell_index") is None:
            nodes[piece["item_ref"]]["text"] = view.text[piece["start"] : piece["end"]]
    return replace(view, items=tuple(nodes.values()))


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
    output = discover_relations(
        native_source_frame(complete_native_fields(view), ()), source_work="actual-parent-sha"
    )
    rows = output["contributions"]
    values = {r["contribution_id"]: source_python(r["value"]) for r in rows}
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
    output = discover_relations(native_source_frame(complete_native_fields(view), ()))
    rows = output["contributions"]
    values = {r["contribution_id"]: source_python(r["value"]) for r in rows}
    symbols = [r for r in rows if values[r["contribution_id"]].get("role") == "symbol"]
    assert len(symbols) == 2 and symbols[0]["occurrence_id"] != symbols[1]["occurrence_id"]
    relations = [values[r["contribution_id"]]["relation"] for r in rows if r["kind"] == "relation"]
    assert relations.count("declares") == 2 and relations.count("order") == 0
    assert output["extra_operations"][0]["outcome"] == "not_run"


def test_source_without_authenticated_parent_binding_retains_no_artifact_identity():
    view = source("See Table 5.1.", labels=("text",))
    output = discover_relations(native_source_frame(complete_native_fields(view), ()))
    assert not any(r["semantic_type"] == "structural.artifact" for r in output["contributions"])


@pytest.fixture(scope="module", params=("declared", "missing", "incompatible"))
def qualifier_release(request):
    import yaml
    from semantic.test_record_contracts import release_inputs

    from corpus_structure.semantic import prepare_release

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
    from corpus_structure.methods.source_preparation import prepare_source

    declaration, release = qualifier_release
    labels = ("section_header", "text") if "\n" in text else ("text",)
    view = complete_native_fields(source(text, labels=labels))
    prepared = prepare_source(view, profile=AnnotationProfile(), annotations_only=True)
    result = discover_relations(
        native_source_frame(view, ()),
        annotations=prepared.annotations,
        predicate_version="5",
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

    # Exercise the ordinary Reader projection with the actual released row codec,
    # not a second fixture of the component or an independent interpretation rule.
    from corpus_structure.semantic.contribution_queries import ContributionInventory
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.refusals import SemanticRefusal
    from corpus_structure.serve.contributions import _interpretations

    pin = next(iter(rows.values()))["pin"]
    custody = dict(
        selected_task_id=51,
        origin_task_id=49,
        source_view_id=pin["source_view_id"],
        source=pin["source"],
        cut_member=True,
    )
    retained = tuple(
        release.validate_json("SourceContribution", canonical_bytes(row)).model_dump(mode="python")
        | custody
        for row in rows.values()
    )
    retained_operations = tuple(op | custody for op in operations.values())

    def facets(selected):
        inventory = ContributionInventory((), retained_operations, (), False, selected)
        return {
            row["contribution_id"]: row["composition"]
            for row in _interpretations(inventory, prepared=release)
            if "composition" in row
        }

    composed = facets(retained)
    for frame in (frames[host], frames[competing]):
        assert composed[frame]["operation_outcome"] == "succeeded"
        (predicate,) = [role for role in composed[frame]["roles"] if role["role"] == "predicate"]
        assert predicate["state"] == "source_located"
    (host_reading,) = [
        row
        for row in rows.values()
        if row.get("component", {}).get("kind") == "predicate_reading"
        and row["component"]["frame"] == frames[host]
    ]
    host_facet = composed[host_reading["contribution_id"]]
    assert host_facet["reading"] == reading
    assert host_facet["operation_outcome"] == interpretation["outcome"]
    assert host_facet["standing"] == "retained_private"

    if declaration == "declared":
        (relation,) = condition_relations
        identity = relation["contribution_id"]
        attachment = composed[identity]
        assert [(role["role"], role["state"]) for role in attachment["roles"][:2]] == [
            ("qualifier", "source_located"),
            ("host", "retained"),
        ]
        assert attachment["roles"][1]["reference"]["contribution_id"] == frames[host]
        assert (
            attachment["roles"][1]["reference"]["operation_key"]
            == operations["source_predicate_frames"]["operation_key"]
        )
        assert attachment["condition"]["text"] == text.split(",")[0].splitlines()[-1]
        (relation_row,) = [row for row in retained if row["contribution_id"] == identity]
        assert [role["state"] for role in facets((relation_row,))[identity]["roles"][:2]] == [
            "outside_selection",
            "outside_selection",
        ]
        with pytest.raises(SemanticRefusal, match="directed endpoints"):
            facets((dict(relation_row, endpoints=list(reversed(relation_row["endpoints"]))),))
    else:
        assert not any(
            facet["operation_question"] == "source_predicate_interpretation"
            and facet.get("qualifier_kind") == "condition"
            for facet in composed.values()
        )
        assert any(
            facet.get("qualifier_kind") == "condition"
            and facet["roles"][0]["state"] == "source_located"
            for facet in composed.values()
        )


@pytest.mark.parametrize("predicate_version", ["4", "5"])
def test_selected_action_preserves_wholly_clipped_role_without_an_anchor(predicate_version):
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.source_preparation import prepare_source

    text = "The analyst records the input."
    view = complete_native_fields(source(text, labels=("text",)))
    prepared = prepare_source(view, profile=AnnotationProfile(), annotations_only=True)
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
        native_source_frame(view, ()),
        annotations=prepared.annotations,
        passages=(selected,),
        predicate_version=predicate_version,
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


@pytest.mark.parametrize("named_version", ("2", "3"))
def test_named_procedure_reference_binds_verb_to_caption_under_selected_version(named_version):
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.source_preparation import prepare_source

    view = complete_native_fields(
        native_table_source(
            (table_cell("1", 0, 0),),
            caption="Table 6.1 Results",
            note="The results are shown in Table 6.1.",
        )
    )
    view = replace(
        view,
        items=tuple(
            dict(
                item,
                content_layer="body",
                **({"parent": {"$ref": "#/tables/0"}} if item["label"] == "caption" else {}),
            )
            for item in view.items
        ),
    )
    annotation = prepare_source(view, profile=AnnotationProfile(), annotations_only=True)
    output = discover_relations(
        native_source_frame(view, ()),
        source_work="fixture-parent",
        annotations=annotation.annotations,
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
        predicate_version="4",
        witnessed_links_enabled=True,
        named_link_version=named_version,
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
    from .test_structural_roles import annotation

    text = "Table 5.1 must be reviewed by Manager."
    view = complete_native_fields(source(text, labels=("text",)))
    product = annotation(
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
    )
    output = discover_relations(
        native_source_frame(view, ()), source_work="parent", annotations=(product,)
    )
    rows = output["contributions"]
    by_id = {r["contribution_id"]: source_python(r["value"]) for r in rows}
    relations = [r for r in rows if r["kind"] == "relation"]
    links = {
        source_python(r["value"])["relation"]: (by_id[r["members"][0]], by_id[r["members"][1]])
        for r in relations
    }
    assert links["actor"][0]["text"] == "reviewed" and links["actor"][1]["text"] == "Manager"
    assert links["object"][1]["text"] == "Table 5.1"
    assert links["uses_artifact"][1]["text"] == "Table 5.1"
    from pathlib import Path

    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.contributions import bind_contributions
    from corpus_structure.semantic.observations import observation_inputs

    core = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    prepared = prepare_release(
        observation_inputs(SourceBundle("core", (SourceArtifact("core", core.read_bytes()),)))
    )
    bound_operations, bound_rows = bind_contributions(
        prepared,
        source=view.ref.key,
        operations=(output["operation"], *output["extra_operations"]),
        contributions=rows,
        coordinate_texts=output["coordinates"],
    )
    assert len(bound_rows) == len(rows)
    assert {op["question"]: op["outcome"] for op in bound_operations} == {
        "source_structural_relations": "succeeded",
        "source_procedure_roles": "succeeded",
        "source_predicate_frames": "not_run",
        "source_predicate_interpretation": "not_run",
    }
    operation = output["extra_operations"][0]
    assert operation["outcome"] == "succeeded" and operation["emitted_count"] > 0
    assert all(
        "annotation:independent-fixture" in r["computation_dependencies"]
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
    view = replace(view, items=nodes)
    output = discover_relations(native_source_frame(view, ()))
    rows = output["contributions"]
    values = {r["contribution_id"]: source_python(r["value"]) for r in rows}
    uses = [r for r in rows if values[r["contribution_id"]].get("role") == "formula_symbol"]
    assert len(uses) == 2 and uses[0]["occurrence_id"] != uses[1]["occurrence_id"]
    assert {values[r["contribution_id"]]["text"] for r in uses} == {"x"}
    assert all(values[r["contribution_id"]]["mapping"] == "exact_native_field" for r in uses)
    assert output["formula_diagnostics"][0]["outcome"] == "parsed"


def test_annotation_failure_keeps_independent_native_contributions_and_failed_stage():
    view = complete_native_fields(source("Let x be count.", labels=("text",)))
    output = discover_relations(
        native_source_frame(view, ()), annotation_errors=("retained parser block failed",)
    )
    assert output["contributions"]
    assert output["operation"]["outcome"] == "succeeded"
    assert output["extra_operations"][0]["outcome"] == "failed"
    assert output["extra_operations"][0]["emitted_count"] == 0


def original_inputs(view):
    ref = view.ref
    original = ExternalSourceRef(
        project_id="original",
        run_id=10,
        cut_id=11,
        release_id="r",
        result_revision=1,
        source_view_id=ref.id,
        native_task_id=ref.native_product.task_id,
        native_product_key=ref.native_product.product_key,
        native_content_digest=ref.native_product.content_digest,
        projection_digest=ref.projection_digest,
        recipe_digest=ref.recipe_digest,
        coordinate_version=3,
    )
    return StructuralInput(
        question="Retain original annotations",
        scope="s",
        inventory_id="i",
        policy_id="p",
        sources=(original,),
        passages=(
            StructuralPassage(
                passage_id="original",
                source_ref=original.identity,
                start=0,
                end=len(view.text),
                text=view.text,
                scope="s",
            ),
        ),
        dependencies=("annotation:original",),
    )


def run_scoped(view, cfg, reader):
    unit = SimpleNamespace(ref=UnitRef(TaskUnitType.SOURCE_VIEW, view.ref.id, view.ref.key))
    return ScopedRelationsMethod().run(
        (unit,), cfg, SimpleNamespace(reader=reader, check_active=lambda: None)
    )[0]


@pytest.mark.parametrize("errors", ((), ("retained block failed",)))
def test_original_annotation_port_keeps_roles_when_new_run_has_no_annotation_task(errors):
    from corpus_structure.ingest.annotations import AnnotationProfile

    from .test_structural_roles import annotation

    text = "Manager reviews Table 5.1."
    view = complete_native_fields(source(text, labels=("text",)))
    inputs = original_inputs(view)
    cfg = ScopedRelationsConfig(
        inputs=inputs,
        structural_input_digest=inputs.identity,
        work_bindings=(
            SourceWorkBinding(
                native_content_digest=view.ref.native_product.content_digest,
                source_work="controlled-parent",
                provenance="explicit functional control binding",
            ),
        ),
    )
    product = annotation(
        text,
        [
            ("Manager", "NOUN", "nsubj", 1, "NN"),
            ("reviews", "VERB", "ROOT", 1, "VBZ"),
            ("Table", "NOUN", "dobj", 1, "NN"),
            ("5.1", "NUM", "nummod", 2, "CD"),
        ],
    )
    calls = []

    class Reader:
        def source_view(self, identity):
            assert identity == view.ref.id
            return view

        def source_result(self, *_):
            raise AssertionError("must use original-source annotations, not the new run")

        def structural_source_annotations(self, actual, source_ref, profile):
            calls.append((actual, source_ref, profile))
            return SimpleNamespace(
                source=native_source_frame(view, ()),
                annotations=(product,),
                errors=errors,
            )

    result = run_scoped(view, cfg, Reader())
    assert calls == [(inputs, inputs.sources[0].identity, AnnotationProfile(cfg.sentences))]
    assert result.contributions is not None and result.contribution_operations is not None
    assert {source_python(r["value"]).get("relation") for r in result.contributions} >= {
        "actor",
        "object",
        "uses_artifact",
    }
    assert next(
        o for o in result.contribution_operations if o["question"] == "source_procedure_roles"
    )["outcome"] == ("limited" if errors else "succeeded")
    assert result.parse_detail is not None and result.parse_detail["annotation_errors"] == list(
        errors
    )


def test_original_annotation_inputs_require_exact_digest_and_complete_pair():
    view = complete_native_fields(source("Let x be count.", labels=("text",)))
    inputs = original_inputs(view)
    for partial in (
        dict(inputs=inputs),
        dict(structural_input_digest=inputs.identity),
        dict(inputs=inputs, structural_input_digest="f" * 64),
    ):
        with pytest.raises(ValueError, match="digest"):
            ScopedRelationsConfig.model_validate(partial)
    assert ScopedRelationsConfig().inputs is None


@pytest.mark.parametrize("mismatch", ("absent", "ambiguous", "native", "projection"))
def test_original_annotation_reference_must_select_exactly_current_source_before_read(mismatch):
    view = complete_native_fields(source("Let x be count.", labels=("text",)))
    inputs = original_inputs(view)
    original = inputs.sources[0]
    if mismatch == "absent":
        sources = (original.model_copy(update=dict(source_view_id=view.ref.id + 1)),)
    elif mismatch == "ambiguous":
        sources = (original, original.model_copy(update=dict(run_id=12, cut_id=13)))
    else:
        key = "native_content_digest" if mismatch == "native" else "projection_digest"
        sources = (original.model_copy(update={key: "f" * 64}),)
    inputs = StructuralInput.model_validate(
        {
            **inputs.model_dump(mode="json"),
            "sources": [s.model_dump(mode="json") for s in sources],
            "passages": [
                inputs.passages[0]
                .model_copy(update=dict(source_ref=sources[0].identity))
                .model_dump(mode="json")
            ],
        }
    )

    class Reader:
        def source_view(self, _):
            return view

        def structural_source_annotations(self, *_):
            raise AssertionError("wrong current source must refuse before original annotation read")

    with pytest.raises(ValueError, match=r"selected source reference|current native source"):
        run_scoped(
            view,
            ScopedRelationsConfig(inputs=inputs, structural_input_digest=inputs.identity),
            Reader(),
        )


@pytest.mark.parametrize("field,value", (("projection_digest", "f" * 64), ("text", "wrong source")))
def test_original_annotation_port_cannot_substitute_detached_projection(field, value):
    view = complete_native_fields(source("Let x be count.", labels=("text",)))
    inputs = original_inputs(view)
    frame = native_source_frame(view, ())
    returned = SimpleNamespace(**{**frame.__dict__, field: value})

    class Reader:
        def source_view(self, _):
            return view

        def structural_source_annotations(self, *_):
            return SimpleNamespace(source=returned, annotations=(), errors=())

    with pytest.raises(ValueError, match="current native projection"):
        run_scoped(
            view,
            ScopedRelationsConfig(inputs=inputs, structural_input_digest=inputs.identity),
            Reader(),
        )


def test_same_run_annotation_route_still_preserves_unavailable_upstream_without_reparse():
    view = complete_native_fields(source("Let x be count.", labels=("text",)))
    calls = []

    class Reader:
        def source_view(self, _):
            return view

        def source_result(self, identity, method):
            calls.append((identity, method))
            return None

        def structural_source_annotations(self, *_):
            raise AssertionError("unconfigured original-source path must not run")

    result = run_scoped(view, ScopedRelationsConfig(), Reader())
    assert calls == [(view.ref.id, "extract.m1_annotations")]
    assert result.contribution_operations is not None
    assert (
        next(
            o for o in result.contribution_operations if o["question"] == "source_procedure_roles"
        )["outcome"]
        == "not_run"
    )


def test_retained_predicate_publication_preserves_exact_hosts_and_refuses_swapped_host():
    from pathlib import Path

    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.source_preparation import prepare_source
    from corpus_structure.semantic import SourceArtifact, SourceBundle, prepare_release
    from corpus_structure.semantic.contributions import bind_contributions, contribution_identity
    from corpus_structure.semantic.observations import observation_inputs

    text = (
        "The reviewer must complete the purchase review form if the purchase exceeds the limit, "
        "and the analyst must retain the receipt if the audit remains open."
    )
    view = complete_native_fields(source(text, labels=("text",)))
    annotations = prepare_source(view, profile=AnnotationProfile(), annotations_only=True)
    assert annotations.annotations and not annotations.annotation_errors
    output = discover_relations(native_source_frame(view, ()), annotations=annotations.annotations)
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
            source=view.ref.key,
            operations=(output["operation"], *output["extra_operations"]),
            contributions=population,
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
    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.methods.source_preparation import prepare_source
    from corpus_structure.methods.witnessed_source_links import match_named_source_links

    view = complete_native_fields(
        native_table_source(
            (table_cell("1", 0, 0),), caption="Table 6.1", note="A value is reported."
        )
    )
    items = {item["self_ref"]: dict(item, content_layer="body") for item in view.items}
    product = prepare_source(view, profile=AnnotationProfile(), annotations_only=True)
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
    verified = match_named_source_links(*arguments, product.annotations, version="3")
    assert (verified.inspected_count, verified.outcome()) == (1, "empty")
    absent = match_named_source_links(*arguments, (), version="3")
    assert (absent.inspected_count, absent.outcome()) == (0, "unsupported")
    unselected = match_named_source_links(
        view.text,
        view.pieces,
        items,
        (),
        (),
        annotation_errors=("another block failed",),
        version="3",
    )
    assert (unselected.inspected_count, unselected.outcome()) == (0, "empty")


def _assert_public_condition_projection(view, relation, rows, predicate):
    from copy import deepcopy

    from corpus_structure.methods.structural_products import condition_qualification
    from corpus_structure.semantic.retained_contributions import RetainedContributionRef
    from corpus_structure.semantic.structural_admission import structural_statement
    from corpus_structure.semantic.structural_products import StructuralProductReport

    pin = relation["pin"]
    scope = relation["component"]["scope"]
    ref = RetainedContributionRef(
        contribution_id=relation["contribution_id"],
        project_id="control",
        run_id=1,
        cut_id=2,
        release_id="control-release",
        result_revision=1,
        selected_task_id=3,
        origin_task_id=4,
        runtime_fingerprint="control-runtime",
    )
    selected = ExternalSourceRef(
        project_id=ref.project_id,
        run_id=ref.run_id,
        cut_id=ref.cut_id,
        release_id=ref.release_id,
        result_revision=ref.result_revision,
        source_view_id=pin["source_view_id"],
        native_task_id=pin["native_product_task_id"],
        native_product_key=pin["product_key"],
        native_content_digest=pin["product_digest"],
        projection_digest=pin["projection_digest"],
        recipe_digest=pin["recipe_digest"],
        coordinate_version=2,
    )
    inputs = StructuralInput(
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
    projected = condition_qualification(inputs, ref, payload)
    report = StructuralProductReport(
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
        update={"passage_id": "same-physical-source-other-version", "effective_version": "revision-2"}
    )
    versioned = inputs.model_copy(update={"passages": (original, other_version)})
    assert condition_qualification(versioned, ref, payload) == projected

    changed = deepcopy(payload)
    (cue,) = [
        row
        for row in changed["contributions"]
        if row["contribution_id"] == relation["component"]["qualifier_contribution_id"]
    ]
    cue["component"]["candidate_tokens"] = (*cue["component"]["candidate_tokens"], 1000)
    with pytest.raises(ValueError, match="uniquely located host"):
        condition_qualification(inputs, ref, changed)

    # An assumption in the condition family remains an assumption in public
    # meaning; the cue and relation must declare the same subtype.
    changed = deepcopy(payload)
    for row in changed["contributions"]:
        if row["contribution_id"] == ref.contribution_id:
            row["component"]["qualifier_kind"] = "assumption"
        if row["contribution_id"] == relation["component"]["qualifier_contribution_id"]:
            row["component"]["cue_kind"] = "assumption"
    assumption = condition_qualification(inputs, ref, changed)
    assert assumption.relation == "assumption"
