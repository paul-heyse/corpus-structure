"""Independent contract examples: declarations, finite states and refusal boundaries."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from typing import Any

import pytest
import yaml

from corpus_structure.semantic.contracts import (
    ExecutionModelInputs,
    approved_implementations,
    compile_execution_model,
    trusted_execution_inputs,
)
from corpus_structure.semantic.types import PreparationError, SourceArtifact


@pytest.fixture(scope="module")
def inputs():
    return trusted_execution_inputs()


@pytest.fixture(scope="module")
def products(inputs):
    return compile_execution_model(inputs)


def changed(inputs: ExecutionModelInputs, data: dict[str, Any]) -> ExecutionModelInputs:
    return replace(inputs, catalog=replace(inputs.catalog, content=yaml.safe_dump(data).encode()))


def body(inputs: ExecutionModelInputs) -> dict[str, Any]:
    return yaml.safe_load(inputs.catalog.content)


def test_all_transitioned_families_and_measurement_context(products):
    assert {c.family for c in products.concepts} == {
        "interpretation",
        "execution",
        "source",
        "measurement",
        "result",
        "knowledge",
        "decision",
        "read",
        "analytics",
    }
    concepts = {c.id: c for c in products.concepts}
    assert {
        "Measurement",
        "MetricDefinition",
        "MeasurementSubject",
        "MeasurementDetail",
    } <= concepts.keys()
    measurement = next(r for r in products.relationships if r.id == "measurement_context")
    assert {e.role: e.concept for e in measurement.endpoints} == {
        "measurement": "Measurement",
        "metric": "MetricDefinition",
        "subject": "MeasurementSubject",
        "producer": "TaskInvocation",
        "method": "MethodDefinition",
        "input": "ObservationInput",
    }
    assert {a.name: a.range for a in concepts["Measurement"].attributes}["value"] == "TypedValue"
    assert {c.id for c in products.lifecycles} == {
        "run",
        "task",
        "submission",
        "cut",
        "realization",
        "evaluation_result",
        "analysis",
    }
    assert products.required_capabilities == (
        "execution.lifecycle.v1",
        "execution.identity_exclusions.v1",
    )
    assert {op.implementation for op in products.operations} == set(approved_implementations())
    for binding in products.implementations:
        implementation = approved_implementations()[binding.id]
        assert binding.owner == implementation.__module__.removeprefix("corpus_structure.")
        assert binding.symbol == implementation.__qualname__


def test_qualified_repeated_nary_and_alternative_identity(products):
    relations = {r.id: r for r in products.relationships}
    fact = relations["fact_denotes"]
    assert fact.direction == "nary"
    assert {e.role for e in fact.endpoints} == {"subject", "fact", "object", "qualification"}
    assert fact.qualifications == ("Qualification",)
    assert fact.identity_context == ("release", "realization")
    occurrence = relations["occurrence_reports"]
    assert occurrence.identity_kind == "occurrence"
    assert "report" in occurrence.identity_roles
    group = relations["group_alternatives"]
    assert group.identity_kind == "unordered_distinct"
    assert group.multiplicity == "set"
    assert "reason" not in group.identity_roles
    assert next(e for e in group.endpoints if e.role == "fact").minimum == 2
    lineage = relations["fact_input"]
    assert lineage.reference_scope == "authorized_lineage"
    assert set(lineage.identity_context) == {
        "input_release",
        "input_realization",
        "output_release",
        "output_realization",
    }
    assert relations["value_member"].multiplicity == "sequence"
    assert "RoleBinding" in relations["value_member"].qualifications


def run_state(status, final_cut="absent", result="absent", receipts="absent"):
    return dict(status=status, final_cut=final_cut, completed_result=result, receipts=receipts)


def test_run_states_require_atomic_completed_output_and_never_reopen(products):
    run = products.lifecycle("run")
    assert run.state(run_state("running")).id == "running"
    assert run.state(run_state("consolidating", "present")).id == "consolidating"
    assert run.state(run_state("finished", "present", "present", "present")).terminal
    products.validate_edge(
        "run_final_cut", run_state("running"), run_state("consolidating", "present")
    )
    with pytest.raises(PreparationError, match="unsupported combination"):
        run.state(run_state("finished", "present", "absent", "present"))
    with pytest.raises(PreparationError, match="unsupported combination"):
        run.state(run_state("running", "present"))
    with pytest.raises(PreparationError, match="unsupported edge"):
        products.validate_edge(
            "run_start_source",
            run_state("finished", "present", "present", "present"),
            run_state("running"),
        )


def test_held_progress_is_independent_of_task_ownership(products):
    task = products.lifecycle("task")
    held = dict(
        status="running",
        attempt_owner="current",
        submission_progress="held",
        terminal_result="none",
        reuse_origin="none",
    )
    assert task.state(held).id == "running_held"
    products.validate_edge("task_reclaim_held", held, held)
    completed = {**held, "status": "done", "attempt_owner": "absent", "terminal_result": "content"}
    products.validate_edge("task_complete_held", held, completed)
    with pytest.raises(PreparationError):
        task.state({**held, "attempt_owner": "absent"})
    with pytest.raises(PreparationError):
        task.state({**completed, "reuse_origin": "completed"})
    # Held is a submission disposition, never a task status or source-read outcome.
    domains = {d.id: d.values for d in products.outcome_domains}
    assert "held" in domains["submission"]
    assert "held" not in domains["protocol"]
    assert "source_ready" in domains["read"]
    assert "source_ready" not in domains["protocol"]


def test_cut_result_and_analytical_lifetime_dimensions(products):
    with pytest.raises(PreparationError):
        products.lifecycle("cut").state({"kind": "final", "source_tasks": "live"})
    with pytest.raises(PreparationError):
        products.lifecycle("realization").state(
            {"completed_result": "present", "writability": "writable"}
        )
    with pytest.raises(PreparationError):
        products.lifecycle("evaluation_result").state(
            {"visibility": "completed", "receipt_set": "incomplete"}
        )
    scope = dict(input_kind="captured", scope_lifetime="open")
    closed = {**scope, "scope_lifetime": "closed"}
    products.validate_edge("analysis_close_captured", scope, closed)
    assert products.lifecycle("analysis").state(closed).terminal
    assert {d.id for d in products.lifecycle("analysis").dimensions} == {
        "input_kind",
        "scope_lifetime",
    }
    # A scope does not assign one exclusive lifetime to its many independent results.
    with pytest.raises(PreparationError):
        products.lifecycle("analysis").state({**scope, "result_lifetime": "detached"})


def test_outcome_translation_preserves_unknown_and_unsupported(products):
    translations = {(t.source, t.target) for t in products.outcome_translations}
    assert translations == {
        ("complete", "complete"),
        ("partial", "partial"),
        ("unknown", "unanalysed"),
        ("unsupported", "unanalysed"),
        ("failed", "failed"),
    }
    assert all(
        t.retained_meaning and t.invariant == "coverage_lowering"
        for t in products.outcome_translations
    )
    assert next(d for d in products.outcome_domains if d.id == "domain_policy").values == ()


@pytest.mark.parametrize(
    "section,index,field,value,code",
    [
        ("concepts", 0, "family", "made_up", "contract_catalog"),
        ("relationships", 0, "identity_roles", ["missing"], "unresolved_contract_reference"),
        ("relationships", 19, "reference_scope", "execution", "unqualified_reference"),
        ("lifecycles", 0, "initial_states", ["missing"], "unresolved_contract_reference"),
        ("transitions", 0, "operation", "missing", "unresolved_contract_reference"),
        ("transitions", 0, "from_states", ["finished"], "terminal_transition"),
        ("operations", 0, "implementation", "missing", "unresolved_contract_reference"),
        ("operations", 0, "outcomes", ["silently_accepted"], "operation_outcome"),
        ("implementations", 0, "symbol", "arbitrary_function", "unapproved_implementation"),
        ("implementations", 0, "owner", "os", "unapproved_implementation"),
        ("implementations", 0, "input_concepts", ["SourceBundle"], "implementation_contract"),
        ("invariants", 0, "implementation", "missing", "unresolved_contract_reference"),
        ("projections", 0, "sources", ["Missing"], "unresolved_contract_reference"),
        ("outcome_domains", 13, "values", ["invented"], "outcome_authority"),
        ("outcome_translations", 0, "target", "missing", "translation_outcome"),
    ],
)
def test_invalid_connected_definitions_refuse(inputs, section, index, field, value, code):
    data = body(inputs)
    data[section][index][field] = value
    with pytest.raises(PreparationError) as error:
        compile_execution_model(changed(inputs, data))
    assert error.value.diagnostics[0].code == code


def test_missing_local_shape_and_wrong_scalar_types_refuse(inputs):
    for value in (None, "1", True):
        data = body(inputs)
        data["relationships"][0]["endpoints"][0]["minimum"] = value
        with pytest.raises(PreparationError) as error:
            compile_execution_model(changed(inputs, data))
        assert error.value.diagnostics[0].code == "contract_catalog"
    data = body(inputs)
    del data["relationships"][0]["endpoints"][0]["minimum"]
    with pytest.raises(PreparationError):
        compile_execution_model(changed(inputs, data))


def test_duplicate_keys_and_definition_identities_refuse(inputs):
    duplicate_key = replace(
        inputs.catalog, content=inputs.catalog.content + b"\nversion: execution-1\n"
    )
    with pytest.raises(PreparationError) as error:
        compile_execution_model(replace(inputs, catalog=duplicate_key))
    assert error.value.diagnostics[0].code == "contract_catalog"
    data = body(inputs)
    data["concepts"].append(data["concepts"][0])
    with pytest.raises(PreparationError) as error:
        compile_execution_model(changed(inputs, data))
    assert error.value.diagnostics[0].code == "duplicate_definition"


def test_endpoint_cardinality_reference_and_state_links_are_checked(inputs):
    cases = []
    data = body(inputs)
    data["relationships"][0]["endpoints"][0]["concept"] = "Missing"
    cases.append((data, "unresolved_contract_reference"))
    data = body(inputs)
    data["relationships"][0]["endpoints"][0]["maximum"] = 0
    cases.append((data, "cardinality"))
    data = body(inputs)
    data["lifecycles"][0]["states"][0]["values"][0]["value"] = "invented"
    cases.append((data, "state_value"))
    data = body(inputs)
    data["lifecycles"][0]["transitions"].remove("run_start_source")
    cases.append((data, "unlinked_transition"))
    data = body(inputs)
    data["concepts"][0]["attributes"][0]["range"] = "Missing"
    cases.append((data, "attribute_range"))
    for data, code in cases:
        with pytest.raises(PreparationError) as error:
            compile_execution_model(changed(inputs, data))
        assert error.value.diagnostics[0].code == code


def test_exact_explicit_bytes_identity_and_immutable_products(inputs, products, monkeypatch):
    assert compile_execution_model(inputs) is products
    catalog_changed = replace(
        inputs,
        catalog=replace(
            inputs.catalog, content=inputs.catalog.content + b"\n# identity-sensitive comment\n"
        ),
    )
    schema_source = inputs.schema.sources[0]
    schema_changed = replace(
        inputs,
        schema=replace(
            inputs.schema,
            sources=(
                replace(
                    schema_source,
                    content=schema_source.content + b"\n# identity-sensitive comment\n",
                ),
            ),
        ),
    )
    assert compile_execution_model(catalog_changed).model_id != products.model_id
    assert compile_execution_model(schema_changed).model_id != products.model_id
    assert products.model_id.startswith("execution:")
    assert json.loads(products.content)["model_id"] == products.model_id
    assert (
        compile_execution_model(
            ExecutionModelInputs(
                inputs.schema, SourceArtifact(inputs.catalog.name, inputs.catalog.content)
            )
        ).content
        == products.content
    )
    with pytest.raises(FrozenInstanceError):
        products.concepts[0].meaning = "changed"
    with pytest.raises(FrozenInstanceError):
        products.concepts[0].attributes[0].range = "changed"
    # Compile uses the supplied bytes, without rereading installed bundled definitions.
    monkeypatch.setattr(
        "corpus_structure.semantic.contracts.trusted_execution_inputs",
        lambda: pytest.fail("ambient read"),
    )
    explicit = replace(
        catalog_changed,
        catalog=replace(catalog_changed.catalog, content=catalog_changed.catalog.content + b"\n"),
    )
    assert compile_execution_model(explicit).model_id != products.model_id


def test_product_conversion_preserves_declared_collections_and_optional_endpoints():
    from corpus_structure.semantic.contracts import (
        _PRODUCT_CONVERTER,
        EndpointRole,
        StateDimension,
    )

    dimension = _PRODUCT_CONVERTER.structure(
        {"id": "owner", "values": ["absent", "current"]}, StateDimension
    )
    assert dimension == StateDimension("owner", ("absent", "current"))
    endpoint = _PRODUCT_CONVERTER.structure(
        {"role": "subject", "concept": "Fact", "minimum": 1, "ordered": False, "unresolved": False},
        EndpointRole,
    )
    assert endpoint.maximum is None
    assert endpoint.unresolved_concept is None
    assert _PRODUCT_CONVERTER.unstructure(dimension) == {
        "id": "owner",
        "values": ["absent", "current"],
    }


@pytest.mark.parametrize("value", ["1", True, 1.0])
def test_product_conversion_never_coerces_integer_fields(value):
    from corpus_structure.semantic.contracts import _PRODUCT_CONVERTER, EndpointRole

    with pytest.raises(ExceptionGroup):
        _PRODUCT_CONVERTER.structure(
            {
                "role": "subject",
                "concept": "Fact",
                "minimum": value,
                "ordered": False,
                "unresolved": False,
            },
            EndpointRole,
        )


def test_native_kernel_bindings_require_complete_exact_signatures(inputs):
    for mutation, code in [
        ("missing", "native_guard_coverage"),
        ("signature", "unapproved_native_guard"),
    ]:
        data = body(inputs)
        if mutation == "missing":
            data["native_guards"].pop()
        else:
            data["native_guards"][0]["symbol"] = "ops.execution_edge(text,text)"
        with pytest.raises(PreparationError) as error:
            compile_execution_model(changed(inputs, data))
        assert error.value.diagnostics[0].code == code


def test_named_graph_operations_are_resolved_and_qualified(products):
    projections = {p.id: p for p in products.projections}
    graph = projections["graph_validation"]
    assert graph.implementation == "graph_project"
    assert graph.lifetime == "snapshot"
    assert "bare_triple_entailment" in graph.omissions
    operations = {o.id: o for o in products.operations}
    assert operations["graph_validate"].inputs == (
        "QualifiedGraphProjection",
        "QualifiedGraphShapes",
    )
    assert operations["graph_validate"].outcomes == ("conformant", "nonconformant", "invalid")
    assert approved_implementations()["graph_project"].__name__ == "qualified_validation_graph"
    assert approved_implementations()["graph_validate"].__name__ == "validate_projected_graph"
