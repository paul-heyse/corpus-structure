"""Independent authored judgment expectations, including source and alternative boundaries."""

from copy import deepcopy

import pytest
from evaluate.declared_record_grading_support import cut

from corpus_structure.semantic.authored_interpretations import (
    attach_authored_judgment,
    judgment_reading,
)
from corpus_structure.semantic.grouped_record_interpretations import (
    InterpretationRoot,
    grouped_candidate_product,
)
from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember
from semantic.test_grouped_record_interpretations import universe


def judgment_fixture():
    prepared, model, selected, first, _ = universe()
    (group,) = grouped_candidate_product(
        prepared, model, selected, (InterpretationRoot(product_id="product:one"),)
    )
    reading = next(
        row for row in group.readings if row.interpretation_id == first["interpretation_id"]
    )
    field = next(
        field
        for field in first["fields"]
        if field["state"] == "present" and field["kind"] == "literal"
    )
    evidence = next(
        item for item in first["evidence_sets"] if item["set_id"] == field["evidence_sets"][0]
    )
    anchor = next(item for item in first["anchors"] if item["anchor_id"] == evidence["anchors"][0])
    source = {
        **{
            name: cut().record[name]
            for name in ("project_id", "demand_id", "read_id", "release_id", "runtime_id")
        },
        "cut_id": cut().identity,
        "read_scope_json": "{}",
        "product_id": "product:one",
        "member_id": reading.reference.member_id,
        "kind_contract": reading.reference.kind_contract,
        "family_contract": group.family_contract,
        "record_id": first["record_id"],
        "interpretation_id": first["interpretation_id"],
        "source_pin": first["pin"],
    }
    body = dict(
        standing="private_authored_judgment",
        judgment_type="measurement.interpretation",
        source_record=source,
        focus={
            "role": field["role"],
            **{key: anchor[key] for key in ("anchor_id", "start", "end", "source_piece")},
        },
        vocabulary_release=prepared.release_id,
        metadata_digest="metadata:checked",
        outcome="selected",
        unit="SECOND",
        quantity_kind="TIME",
        basis_status="identified",
        basis="one trial",
        assessment="Source describes this duration per trial.",
        reviewer="reviewer:actual",
        numerical_equivalence="unassessed",
    )
    return prepared, model, selected, group, body


def test_source_reading_link_keeps_complete_alternatives_and_authored_unit_basis_distinctions():
    _, _, _, group, body = judgment_fixture()
    actual_group, reading = judgment_reading(body, (group,), cut())
    assert (
        actual_group is group
        and reading.interpretation_id == body["source_record"]["interpretation_id"]
    )
    reference = DdoRichSelectedMember(
        product_id="authored:seconds",
        member_id=None,
        kind_contract="kind:measurement-judgment",
        support_references=(
            {
                "kind": "authored",
                "admission_id": "admission:actual",
                "source_reference": "ref:actual",
            },
        ),
    )
    (result,) = attach_authored_judgment(
        (group,),
        body,
        reference=reference,
        author="author:actual",
        selection_id="selection:seconds",
        source_reference="ref:actual",
    )
    hours = deepcopy(body)
    hours.update(unit="HOUR", basis="one batch", assessment="Independent alternative assessment.")
    (result,) = attach_authored_judgment(
        (result,),
        hours,
        reference=reference.model_copy(update={"product_id": "authored:hours"}),
        author="author:other",
        selection_id="selection:hours",
        source_reference="ref:hours",
    )
    assert len(result.readings) == 2 and result.readings == group.readings
    assert [(row.body["unit"], row.body["basis"]) for row in result.authored_judgments] == [
        ("SECOND", "one trial"),
        ("HOUR", "one batch"),
    ]
    assert all(
        row.body["numerical_equivalence"] == "unassessed" for row in result.authored_judgments
    )
    assert all(
        row.reference.support_references[0].kind == "authored" for row in result.authored_judgments
    )
    assert result.standing == "private_uncalibrated_candidates"
    assert attach_authored_judgment(
        (result,),
        body,
        reference=reference,
        author="author:actual",
        selection_id="selection:seconds",
        source_reference="ref:actual",
    ) == (result,)


@pytest.mark.parametrize(
    "mutation",
    [
        "product",
        "member",
        "kind",
        "family",
        "record",
        "reading",
        "pin",
        "cut",
        "release",
        "role",
        "anchor",
        "span",
        "quote",
    ],
)
def test_foreign_reading_source_cut_field_and_quote_refuse(mutation):
    _, _, _, group, body = judgment_fixture()
    source = body["source_record"]
    fields = {
        "product": "product_id",
        "member": "member_id",
        "kind": "kind_contract",
        "family": "family_contract",
        "record": "record_id",
        "reading": "interpretation_id",
        "cut": "cut_id",
        "release": "release_id",
    }
    if mutation in fields:
        source[fields[mutation]] = "foreign"
    elif mutation == "pin":
        source_pin = source["source_pin"]
        assert isinstance(source_pin, dict)
        source["source_pin"] = {**source_pin, "subject": "foreign"}
    elif mutation == "span":
        body["focus"]["end"] += 1
    else:
        body["focus"][
            {"role": "role", "anchor": "anchor_id", "quote": "source_piece"}[mutation]
        ] = "foreign"
    with pytest.raises(ValueError):
        judgment_reading(body, (group,), cut())


def test_exact_judgment_nominal_and_actual_captured_schema_required():
    from corpus_structure.semantic.authored_interpretations import checked_judgment

    prepared, _, _, _, body = judgment_fixture()
    definition = next(
        item for item in prepared.definitions if item.name == "DdoAuthoredMeasurementJudgment"
    )
    from corpus_structure.semantic.interpretations import metadata_binding

    body["metadata_digest"] = metadata_binding(prepared)[0]
    assert checked_judgment(prepared, definition.iri, body) == body
    stale = deepcopy(body)
    stale["metadata_digest"] = "0" * 64
    with pytest.raises(ValueError, match="vocabulary"):
        checked_judgment(prepared, definition.iri, stale)
    with pytest.raises(ValueError, match="captured"):
        checked_judgment(prepared, "wrong:kind", body)
    bad = deepcopy(body)
    bad["numerical_equivalence"] = "converted"
    with pytest.raises(ValueError):
        prepared.validate_json(definition.name, __import__("json").dumps(bad).encode())


def test_selected_original_admission_exposes_authorship_without_computational_receipt(monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.semantic.data_operation_support import authored_fact_selection
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.serve import interpretation_authoring

    _, _, selected, group, body = judgment_fixture()
    context = selected.context
    authored = authored_fact_selection(
        "judgment",
        body,
        kind_contract="kind:authored-measurement",
        context=context,
        author="reviewer:actual",
        selection_id="selection:actual",
    ).record()["reference"]
    product = dict(
        id="product:judgment",
        project_id=context.project_id,
        kind_contract="kind:authored-measurement",
        canonical_body=semantic_value(body),
        **group.context.model_dump(mode="python"),
    )
    admission = dict(
        id="admission:actual",
        product_id=product["id"],
        demand_id=cut().record["demand_id"],
        project_id=context.project_id,
        reference=authored,
        source_reference="source-ref:actual",
        evidence={"standing": "authored"},
        selection_name="judgment",
        trust_snapshot={},
        subject=context.subject,
        original_source=context.original_source,
        analyzed_scope=group.context.analyzed_scope,
    )
    frontier = dict(
        **{
            key: value
            for key, value in admission.items()
            if key not in {"id", "demand_id", "project_id", "reference"}
        },
        admission_id=admission["id"],
        kind_contract=product["kind_contract"],
        subject_definition=product["subject_definition"],
    )
    rows = {
        "kb.data_product": {product["id"]: product},
        "ops.original_source_admission": {admission["id"]: admission},
        "sem.data_kind_contract": {"kind:authored-measurement": {"kind": "nominal:actual"}},
    }
    index = SimpleNamespace(
        mapping=lambda name, keys: rows[name],
        rows=lambda name: iter((admission,)),
        frontier_rows=lambda name: iter((frontier,)),
    )
    scope = SimpleNamespace(index=index, cut=cut(), prepared="prepared:actual")
    calls = []

    def authenticate(connection, prepared, nominal, actual, *, expected_project):
        assert expected_project == "project:one"
        calls.append((connection, prepared, nominal, actual))
        return actual, group.context

    monkeypatch.setattr(interpretation_authoring, "authenticate_judgment_source", authenticate)
    ((actual, provenance),) = interpretation_authoring.selected_authored_judgments(
        "connection:actual", scope, ("product:judgment",)
    )
    assert actual == body and calls == [
        ("connection:actual", "prepared:actual", "nominal:actual", body)
    ]
    assert provenance["author"] == "reviewer:actual"
    assert provenance["selection_id"] == "selection:actual"
    assert provenance["reference"].support_references[0].model_dump() == {
        "kind": "authored",
        "admission_id": "admission:actual",
        "source_reference": "source-ref:actual",
    }
    admission["evidence"]["standing"] = "computed"
    with pytest.raises(ValueError, match="actual authored"):
        tuple(
            interpretation_authoring.selected_authored_judgments(None, scope, ("product:judgment",))
        )
    admission["evidence"]["standing"] = "authored"
    index.frontier_rows = lambda name: iter(())
    with pytest.raises(ValueError, match="exact selected authored admissions"):
        tuple(
            interpretation_authoring.selected_authored_judgments(None, scope, ("product:judgment",))
        )
    index.frontier_rows = lambda name: iter((frontier,))
    product["subject"] = "subject:foreign"
    with pytest.raises(ValueError, match="original body or context"):
        tuple(
            interpretation_authoring.selected_authored_judgments(None, scope, ("product:judgment",))
        )


def test_judgment_source_reopens_exact_original_cut_scope_before_linking(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from corpus_structure.semantic.interpretations import metadata_binding
    from corpus_structure.serve import interpretation_authoring, selected_contributions

    prepared, model, product, group, body = judgment_fixture()
    body["metadata_digest"] = metadata_binding(prepared)[0]
    nominal = next(
        item.iri for item in prepared.definitions if item.name == "DdoAuthoredMeasurementJudgment"
    )
    seen = []

    @contextmanager
    def acquire(connection, demand_id, **kwargs):
        seen.append((connection, demand_id, kwargs))
        yield cut(), "index:actual"

    monkeypatch.setattr("corpus_structure.semantic.demand_results.selected_record_index", acquire)
    monkeypatch.setattr("corpus_structure.semantic.releases.open_release", lambda *args: prepared)
    monkeypatch.setattr(
        "corpus_structure.semantic.data_operation_admission.bound_data_operation_model",
        lambda value: model,
    )
    monkeypatch.setattr(
        selected_contributions,
        "SelectedContributionScope",
        lambda *args: SimpleNamespace(
            prepared=prepared, model=model, cut=cut(), products=lambda **kwargs: iter((product,))
        ),
    )
    actual, context = interpretation_authoring.authenticate_judgment_source(
        "connection:actual", prepared, nominal, body
    )
    assert actual == body and context == group.context
    assert seen[0][0:2] == ("connection:actual", "demand:source")
    assert seen[0][2]["scope"] == {}
    assert seen[0][2]["read_id"] == "read:source"
    assert seen[0][2]["expected_cut"] == cut().identity
    assert seen[0][2]["capture_frontier"] is True
    body["source_record"]["cut_id"] = "cut:foreign"
    with pytest.raises(ValueError, match="source cut"):
        interpretation_authoring.authenticate_judgment_source(None, prepared, nominal, body)


def test_independent_authored_read_is_explicit_pinned_and_same_project(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from corpus_structure.semantic.grouped_record_interpretations import (
        AuthoredJudgmentRead,
        GroupedInterpretationRequest,
    )
    from corpus_structure.serve import interpretation_authoring, selected_contributions

    prepared, model, _, _, _ = judgment_fixture()
    request = GroupedInterpretationRequest(
        project_id="project:one",
        demand_id="demand:source",
        roots=(InterpretationRoot(product_id="product:one"),),
    )
    independent = AuthoredJudgmentRead(
        demand_id="demand:authored",
        read_id="read:authored",
        expected_cut="cut:authored",
        scope={"product_ids": ["product:judgment"]},
        product_ids=("product:judgment",),
    )
    seen = []

    @contextmanager
    def acquire(connection, demand_id, **kwargs):
        seen.append((demand_id, kwargs))
        yield cut(), "index:authored"

    monkeypatch.setattr("corpus_structure.semantic.demand_results.selected_record_index", acquire)
    monkeypatch.setattr("corpus_structure.semantic.releases.open_release", lambda *args: prepared)
    monkeypatch.setattr(
        "corpus_structure.semantic.data_operation_admission.bound_data_operation_model",
        lambda value: model,
    )
    monkeypatch.setattr(
        selected_contributions,
        "SelectedContributionScope",
        lambda *args: SimpleNamespace(index=args[1]),
    )
    monkeypatch.setattr(
        interpretation_authoring,
        "selected_authored_judgments",
        lambda connection, selected, products: iter(((products, selected.index),)),
    )
    assert tuple(
        interpretation_authoring.read_authored_judgment_selection(None, request, independent)
    ) == ((("product:judgment",), "index:authored"),)
    assert seen == [
        (
            "demand:authored",
            {
                "project_id": "project:one",
                "scope": {"product_ids": ["product:judgment"]},
                "read_id": "read:authored",
                "expected_cut": "cut:authored",
                "max_bytes": request.max_graph_bytes,
                "max_total_bytes": request.max_graph_bytes,
                "max_total_records": request.max_graph_records,
                "capture_frontier": True,
            },
        )
    ]


def test_current_terminology_judgment_keeps_released_candidates_and_source_focus():
    from corpus_structure.semantic.authored_interpretations import checked_judgment
    from corpus_structure.semantic.interpretations import lookup_terms

    prepared, _, _, group, measurement = judgment_fixture()
    lookup = lookup_terms(prepared, "distribution_family", "normal")
    body = dict(
        source_record=measurement["source_record"],
        vocabulary_release=prepared.release_id,
        metadata_digest=lookup["metadata_digest"],
        lookup_policy="released-lexical-1",
        standing="private_authored_judgment",
        judgment_type="terminology.interpretation",
        decisions=[
            dict(
                field="distribution_family",
                focus=measurement["focus"],
                candidates=lookup["candidates"],
                outcome="unresolved",
                assessment="The lexical candidate does not settle this source context.",
                reviewer="reviewer:actual",
            )
        ],
    )
    nominal = next(
        item.iri for item in prepared.definitions if item.name == "DdoAuthoredTerminologyJudgment"
    )
    from corpus_structure.semantic.data_operation_json import json_bytes

    assert json_bytes(checked_judgment(prepared, nominal, body)) == json_bytes(body)
    actual, reading = judgment_reading(body, (group,), cut())
    assert (
        actual is group and reading.interpretation_id == body["source_record"]["interpretation_id"]
    )
    assert body["decisions"][0]["outcome"] == "unresolved"
    assert [row["value"] for row in body["decisions"][0]["candidates"]] == ["normal"]
    assert "selected_value" not in body["decisions"][0]


def test_native_valid_original_frontier_is_retained_separately_from_diagnostic_rows(tmp_path):
    from corpus_structure.semantic.data_operation_read_index import SelectedRecordIndex

    index = SelectedRecordIndex(tmp_path / "selected.sqlite")
    original = dict(
        admission_id="admission:valid",
        product_id="product:judgment",
        evidence={"standing": "authored"},
    )
    page = {**cut().record, "obligations": [], "uses": [], "original_source_admissions": [original]}
    try:
        index.append_page(page)
        index.append_page(page)
        assert tuple(index.frontier_rows("original_source_admissions")) == (original,)
        assert index.retained_records == 1
        changed = {
            **page,
            "original_source_admissions": [{**original, "product_id": "product:foreign"}],
        }
        with pytest.raises(ValueError, match="different facts"):
            index.append_page(changed)
    finally:
        index.close()
