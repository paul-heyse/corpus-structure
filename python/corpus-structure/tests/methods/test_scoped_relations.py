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


def test_native_table_roles_notes_and_units_keep_exact_cell_participants():
    view = native_table_source(
        (
            table_cell("Probability %", 0, 1, column_header=True),
            table_cell("Heads", 1, 0, row_header=True),
            table_cell("50", 1, 1),
            table_cell("50", 2, 1),
        ),
        caption="Table 5.1 Coin",
        note="Values are percentages.",
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
        "note",
        "value_role",
    }
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
    assert len(bound_rows) == len(rows) and len(bound_operations) == 2
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
