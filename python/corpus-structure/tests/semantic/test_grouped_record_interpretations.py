"""Independent grouped-reading expectations; controlled reads grant no native authority."""

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace

import pytest
from evaluate.declared_record_grading_support import current, current_reading

from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext, json_context_meaning
from corpus_structure.semantic.declared_candidate_products import candidate_member_id
from corpus_structure.semantic.grouped_record_interpretations import (
    GroupedInterpretationRequest,
    InterpretationRoot,
    grouped_candidate_product,
)
from corpus_structure.semantic.observations import source_value
from corpus_structure.semantic.record_contracts import interpretation_identity
from corpus_structure.semantic.rich_knowledge_contracts import DdoRichSelectedMember
from corpus_structure.serve.selected_contributions import SelectedContribution


def universe(*, second_source=False, resolved=False):
    prepared, model = current()
    first, _ = current_reading("measurement", 2 if second_source else 1)
    scope = {
        "source": {
            "document": first["pin"]["document"],
            "document_subject": "original-document:" + "a" * 64,
            "projection": first["pin"]["projection_digest"],
            "section_pointer": first["pin"]["section_pointer"],
            "membership": "descendants",
        },
        "selectors": [
            {
                "projection": first["pin"]["projection_digest"],
                "native_pointer": first["pin"]["section_pointer"],
            }
        ],
    }
    first["pin"]["analyzed_scope_meaning"] = json_context_meaning(json_bytes(scope)).decode()
    from corpus_structure.semantic.record_contracts import (
        anchor_identity,
        evidence_set_identity,
        record_family_contract,
        record_identity,
    )

    anchors = {}
    for anchor in first["anchors"]:
        old = anchor["anchor_id"]
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors[old] = anchor["anchor_id"]
    first["occurrence_anchors"] = [anchors[key] for key in first["occurrence_anchors"]]
    sets = {}
    for evidence in first["evidence_sets"]:
        old = evidence["set_id"]
        evidence["anchors"] = [anchors[key] for key in evidence["anchors"]]
        evidence["set_id"] = evidence_set_identity(evidence)
        sets[old] = evidence["set_id"]
    for field in first["fields"]:
        field["evidence_sets"] = [sets[key] for key in field["evidence_sets"]]
    first["record_id"] = record_identity(record_family_contract(model, first["contract"]), first)
    first["standing"] = "candidate"
    first["interpretation_id"] = interpretation_identity(first)
    second = deepcopy(first)
    second["fields"][0]["original"] = "Alternative original spelling"
    second["computation_dependencies"] = (
        *second.get("computation_dependencies", ()),
        "observation:alternative",
    )
    second["interpretation_id"] = interpretation_identity(second)
    pin = first["pin"]
    context = SubjectContext(
        pin["project_id"],
        pin["subject"],
        pin["original_source"],
        json_bytes(scope),
        subject_definition=pin["subject_definition"],
    )
    contracts = {item.owner: item.key for item in model.identities if item.domain == "kind"}
    definition = next(
        item
        for item in prepared.definitions
        if item.name == ("DdoResolvedReadingReport" if resolved else "DdoCandidateInspectionReport")
    )
    member_definition = next(
        item for item in prepared.definitions if item.name == "DdoCandidateSourceRecord"
    )
    packets = [
        {
            "member_id": candidate_member_id("record", row),
            "kind_contract": contracts[member_definition.iri],
            "context": {key: value for key, value in context.record.items() if key != "project_id"},
            "body": {**row, "candidate_type": "record"},
        }
        for row in (first, second)
    ]
    body = dict(
        source_pin=pin,
        standing="private_uncalibrated_candidates",
        inspection_outcome="produced",
        members=packets,
        operations=[],
        coordinate_texts=[],
        coverage=[],
        diagnostics_json="{}",
    )
    if resolved:
        body.update(
            reading_policy_digest="a" * 64,
            reading_events=source_value(
                [
                    {
                        "record_id": first["record_id"],
                        "interpretation_id": first["interpretation_id"],
                        "outcome": "not_run",
                        "final_event_score": None,
                        "diagnostics": ["actual retained unavailable policy"],
                    }
                ]
            ),
        )
    reference = DdoRichSelectedMember(
        product_id="product:other" if second_source else "product:one",
        member_id=None,
        kind_contract=contracts[definition.iri],
        support_references=(
            {
                "kind": "computation",
                "derivation_id": "derivation:one",
                "admission_use_id": "use:one",
            },
        ),
    )
    return (
        prepared,
        model,
        SelectedContribution(
            reference,
            context,
            body,
            definition.iri,
            "operation:one",
            "use:one",
            "derivation:one",
            {},
        ),
        first,
        second,
    )


def test_member_or_reading_root_keeps_complete_alternatives_all_fields_and_real_events():
    prepared, model, selected, first, second = universe(resolved=True)
    roots = (
        InterpretationRoot(
            product_id=selected.reference.product_id,
            member_id=candidate_member_id("record", first),
            interpretation_id=first["interpretation_id"],
        ),
    )
    (group,) = grouped_candidate_product(prepared, model, selected, roots)
    assert group.record_id == first["record_id"]
    assert group.standing == "private_uncalibrated_candidates"
    assert group.alternatives_complete_within == "selected_candidate_product"
    actual = {reading.interpretation_id: reading for reading in group.readings}
    assert len(actual) == 2
    assert json_bytes(actual[first["interpretation_id"]].body) == json_bytes(first)
    assert json_bytes(actual[second["interpretation_id"]].body) == json_bytes(second)
    assert actual[first["interpretation_id"]].reading_events[0]["outcome"] == "not_run"
    assert actual[first["interpretation_id"]].reading_events[0]["final_event_score"] is None
    assert actual[second["interpretation_id"]].reading_events == ()
    assert all(reading.reference.product_id == "product:one" for reading in group.readings)
    assert "fact_id" not in type(group).model_fields


@pytest.mark.parametrize(
    "mutation",
    [
        "identity",
        "context",
        "standing",
        "unknown-member",
        "unknown-reading",
        "wrong-kind",
        "member-kind",
        "duplicate-event",
    ],
)
def test_invalid_nominal_occurrence_context_standing_and_root_refuse(mutation):
    prepared, model, selected, _first, _ = universe(resolved=True)
    body = deepcopy(selected.body)
    root = InterpretationRoot(product_id="product:one")
    if mutation == "identity":
        body["members"][0]["body"]["record_id"] = "same-label-wrong-occurrence"
    elif mutation == "context":
        body["members"][0]["context"]["subject"] = "subject:foreign"
    elif mutation == "standing":
        body["standing"] = "accepted"
    elif mutation == "unknown-member":
        root = root.model_copy(update={"member_id": "record:missing"})
    elif mutation == "unknown-reading":
        root = root.model_copy(update={"interpretation_id": "missing"})
    elif mutation == "member-kind":
        body["members"][0]["kind_contract"] = "wrong-kind-contract"
    elif mutation == "wrong-kind":
        selected = replace(selected, nominal="unrelated-kind")
    else:
        from corpus_structure.semantic.observations import source_python

        events = source_python(body["reading_events"])
        body["reading_events"] = source_value(events + events)
    with pytest.raises(ValueError):
        grouped_candidate_product(prepared, model, replace(selected, body=body), (root,))


def test_group_paging_pins_cut_and_selection_and_never_splits_readings(monkeypatch):
    from evaluate.declared_record_grading_support import cut

    from corpus_structure.serve import interpretations, selected_contributions

    prepared, model, first, *_ = universe()
    _, _, second, *_ = universe(second_source=True)
    observed = []

    @contextmanager
    def scope(connection, request, *, product_ids):
        assert set(product_ids) == {"product:one", "product:other"}
        observed.append(request)
        yield SimpleNamespace(
            prepared=prepared,
            model=model,
            cut=cut(),
            products=lambda: iter((first, second)),
            index=SimpleNamespace(frontier_rows=lambda name: iter(({"fate": "unknown"},))),
        )

    monkeypatch.setattr(selected_contributions, "selected_contribution_scope", scope)
    request = GroupedInterpretationRequest(
        project_id="project:one",
        demand_id="demand:source",
        roots=(
            InterpretationRoot(product_id="product:one"),
            InterpretationRoot(product_id="product:other"),
        ),
        limit=1,
    )
    page = interpretations.group_selected_interpretations(None, request)
    items = page.body["items"]
    assert isinstance(items, list) and len(items) == 1
    first_item = items[0]
    assert isinstance(first_item, dict)
    readings = first_item["readings"]
    assert isinstance(readings, list) and len(readings) == 2
    assert page.body["page_complete"] is False and page.body["examined_groups"] == 2
    universes = page.body["candidate_universes"]
    assert isinstance(universes, list) and len(universes) == 2
    token = page.body["continuation"]
    next_page = interpretations.group_selected_interpretations(
        None, request.model_copy(update={"cursor": token})
    )
    next_items = next_page.body["items"]
    assert isinstance(next_items, list) and len(next_items) == 1
    second_item = next_items[0]
    assert isinstance(second_item, dict)
    assert next_page.body["page_complete"] is True
    assert first_item["identity"] != second_item["identity"]
    assert observed[-1].read_id == "read:source" and observed[-1].expected_cut == cut().identity
    with pytest.raises(ValueError):
        interpretations.group_selected_interpretations(
            None, request.model_copy(update={"cursor": token, "demand_id": "demand:foreign"})
        )
    import base64

    from corpus_structure.semantic.data_operation_json import json_loads

    assert isinstance(token, str)
    bad_cursor = json_loads(base64.urlsafe_b64decode(token))
    bad_cursor["implementation"] = "0" * 64
    forged = base64.urlsafe_b64encode(json_bytes(bad_cursor)).decode()
    with pytest.raises(ValueError):
        interpretations.group_selected_interpretations(
            None, request.model_copy(update={"cursor": forged})
        )
    with pytest.raises(ValueError):
        interpretations.group_selected_interpretations(
            None, request.model_copy(update={"implementation": "0" * 64})
        )
    with pytest.raises(ValueError):
        interpretations.group_selected_interpretations(
            None,
            request.model_copy(
                update={"cursor": token, "read_id": "read:foreign", "expected_cut": cut().identity}
            ),
        )
    from corpus_structure.semantic.refusals import ReadLimit

    with pytest.raises(ReadLimit):
        interpretations.group_selected_interpretations(
            None, request.model_copy(update={"max_bytes": 1024})
        )


def test_actual_finite_report_attaches_only_to_the_complete_exact_reading_group():
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.finite_interpretation_products import (
        finite_interpretation_values,
    )
    from corpus_structure.semantic.grouped_record_interpretations import (
        attach_finite_interpretations,
    )

    prepared, model, candidate, *_ = universe()
    groups = grouped_candidate_product(
        prepared, model, candidate, (InterpretationRoot(product_id="product:one"),)
    )
    product = finite_interpretation_values(
        candidate.body,
        {
            "version": "finite-interpretation-policy-1",
            "mode": "records",
            "requests": source_value({}),
            "dependencies": [],
        },
    )
    nominal = "captured:finite"
    # The controlled finite schema adapter supplies only already separately tested
    # shape admission; expected group membership and outcomes remain independent.
    finite_prepared = SimpleNamespace(
        definitions=(
            SimpleNamespace(iri=nominal, name="DdoFiniteInterpretationProduct", ancestors=()),
        ),
        validate_json=lambda name, content: SimpleNamespace(
            model_dump=lambda **kwargs: json_loads(content)
        ),
    )
    finite = replace(
        candidate,
        nominal=nominal,
        body=product,
        reference=candidate.reference.model_copy(update={"product_id": "product:finite"}),
    )
    (group,) = attach_finite_interpretations(
        finite_prepared, finite, groups, candidate_product_id="product:one"
    )
    assert len(group.finite_interpretations) == 1
    actual = group.finite_interpretations[0]
    assert actual.reference.product_id == "product:finite"
    assert actual.report["outcome"] == "not_run"
    assert actual.report["probability_standing"] == "not_computed"
    assert "result" not in actual.report
    bad = deepcopy(product)
    from corpus_structure.semantic.observations import source_python

    reports = source_python(bad["reports"])
    reports[0]["interpretation_ids"] = reports[0]["interpretation_ids"][:-1]
    bad["reports"] = source_value(reports)
    with pytest.raises(ValueError):
        attach_finite_interpretations(
            finite_prepared, replace(finite, body=bad), groups, candidate_product_id="product:one"
        )


def test_omitted_dependencies_keep_original_body_distinct_from_explicit_empty():
    prepared, model, selected, first, _ = universe()
    root = (InterpretationRoot(product_id="product:one"),)
    (omitted,) = grouped_candidate_product(prepared, model, selected, root)
    explicit_body = deepcopy(selected.body)
    explicit_body["members"][0]["body"]["computation_dependencies"] = []
    (explicit,) = grouped_candidate_product(
        prepared, model, replace(selected, body=explicit_body), root
    )
    assert omitted.computation_dependencies == explicit.computation_dependencies
    assert omitted.retained_input_digest != explicit.retained_input_digest
    assert omitted.dependency_coverage == "unknown"
    assert explicit.dependency_coverage == "recorded"
    before = next(
        row for row in omitted.readings if row.interpretation_id == first["interpretation_id"]
    )
    after = next(
        row for row in explicit.readings if row.interpretation_id == first["interpretation_id"]
    )
    assert "computation_dependencies" not in before.body
    assert after.body["computation_dependencies"] == []


def test_native_acquisition_scopes_exact_roots_and_preserves_explicit_null_source(monkeypatch):
    from corpus_structure.serve import selected_contributions

    seen = []
    index, prepared, model = object(), object(), object()

    @contextmanager
    def acquire(connection, demand_id, **kwargs):
        seen.append((demand_id, kwargs))
        yield SimpleNamespace(record={"release_id": "release:exact"}), index

    monkeypatch.setattr(selected_contributions, "selected_record_index", acquire)
    monkeypatch.setattr(
        selected_contributions,
        "open_release",
        lambda connection, release: prepared if release == "release:exact" else None,
    )
    monkeypatch.setattr(
        selected_contributions,
        "bound_data_operation_model",
        lambda value: model if value is prepared else None,
    )
    request = GroupedInterpretationRequest(
        project_id="project:one",
        demand_id="demand:one",
        original_source=None,
        roots=(
            InterpretationRoot(product_id="product:one"),
            InterpretationRoot(product_id="product:two"),
        ),
    )
    with selected_contributions.selected_contribution_scope(
        None, request, product_ids=["product:two", "product:one"]
    ) as selected:
        assert selected.prepared is prepared and selected.index is index
        assert selected.model is model
    assert seen[0][0] == "demand:one"
    assert seen[0][1]["scope"] == {
        "product_ids": ["product:one", "product:two"],
        "original_source": None,
    }
    assert seen[0][1]["capture_frontier"] is True
    assert seen[0][1]["max_total_records"] == request.max_graph_records
    assert seen[0][1]["max_total_bytes"] == request.max_graph_bytes
