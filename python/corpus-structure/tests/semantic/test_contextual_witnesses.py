"""Independent authored-binding semantics; these controlled facts are unadmitted."""

from copy import deepcopy
from dataclasses import replace

import pytest

from corpus_structure.semantic.contextual_witnesses import (
    contextual_input_reference,
    project_contextual_witnesses,
)
from corpus_structure.semantic.data_operation_cpu_basis import CPUInputRole, cpu_input_basis
from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_support import (
    AuthoredFactSupportReference,
    ComputationalSupportReference,
)
from corpus_structure.semantic.data_operation_values import decode_semantic_value, semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.native_source_view import thaw_native
from corpus_structure.semantic.observations import source_python, source_value
from corpus_structure.semantic.selected_support import ProducerOutputOccurrence
from semantic.test_contextual_selected_encoder import case
from semantic.test_declared_contextual_operations import inputs


def witness_case():
    frame, occurrence, *_ = case("located-frame-2")
    pin = frame.pin.values()
    source_context = SubjectContext(
        pin["project_id"],
        pin["subject"],
        pin["original_source"],
        json_bytes(decode_semantic_value(json_loads(pin["analyzed_scope_meaning"]))),
        subject_definition=pin["subject_definition"],
    )
    context = source_context
    support = (ComputationalSupportReference(derivation_id="unadmitted:cue-episode"),)

    def role(name, product, body, *, member=None, selected=context, evidence=support, position=0):
        return CPUInputRole(
            name,
            position,
            1,
            product,
            member,
            "unadmitted:" + name,
            selected,
            thaw_native(body),
            evidence,
            producer_output=ProducerOutputOccurrence(
                member_id=None, role="result", position=0, multiplicity=1
            )
            if any(isinstance(ref, ComputationalSupportReference) for ref in evidence)
            else None,
        )

    carrier = role(
        "cues", "unadmitted:report", occurrence, member="subject", selected=source_context
    )
    other_body = dict(occurrence, contribution_id="source-contribution:" + "b" * 64)
    other = role(
        "cues",
        "unadmitted:other-report",
        other_body,
        member="unrelated",
        # Distinct retained member addresses can share a producer output position.
        position=0,
        selected=source_context,
    )

    def ref(value):
        return contextual_input_reference(value, contribution=True).model_dump(
            mode="python", exclude_none=True
        )

    carrier_ref, other_ref = ref(carrier), ref(other)
    hypotheses = dict(
        author_assertion="unadmitted author assertion",
        hypotheses=[
            dict(
                hypothesis_id="assertion:" + target,
                target_id=target,
                relation="denotes",
                asserted_basis="explicit_source_cue",
                cue_refs=[carrier_ref],
            )
            for target in ("one", "two")
        ],
    )
    query = dict(source_pin=pin, occurrence_id=occurrence["occurrence_id"], carrier=carrier_ref)
    roles = [
        role(
            "source",
            pin["source_product"],
            frame.value,
            member=pin.get("source_member"),
            selected=source_context,
            evidence=(),
        ),
        role("query", "unadmitted:query", query),
        role("inventory", "unadmitted:inventory", inputs()["inventory"]),
        role(
            "hypotheses",
            "unadmitted:hypotheses",
            hypotheses,
            evidence=(
                AuthoredFactSupportReference(
                    admission_id="unadmitted:authored", source_reference="unadmitted:source"
                ),
            ),
        ),
        carrier,
        other,
    ]
    # The header must describe the actual selected source contract.
    roles[0] = replace(roles[0], kind_contract=pin["kind_contract"])
    return frame, context, roles, other_ref


def project(frame, context, roles):
    basis = cpu_input_basis(
        "unadmitted:witness-control",
        context,
        tuple(roles),
        parameters=canonical_bytes(semantic_value({})),
        replicate=None,
    )
    return project_contextual_witnesses(basis, frame.record, check_active=lambda: None)


def test_private_binding_preserves_competing_authored_assertions_and_exact_carrier():
    frame, context, roles, other = witness_case()
    result = project(frame, context, roles)
    assert result["standing"] == "private_authored_source_binding_hypotheses"
    assert result["support_state"] == "unassessed"
    assert result["author_assertion"] == "unadmitted author assertion"
    witnesses = source_python(result["witnesses"])
    assert [(row["target_id"], row["support_state"], row["basis"]) for row in witnesses] == [
        ("one", "unassessed", "explicit_source_cue"),
        ("two", "unassessed", "explicit_source_cue"),
    ]
    assert all(row["evidence_ids"] == ["source-contribution:" + "a" * 64] for row in witnesses)
    assert result["query_input"] == {"variant": "product", "role": "query"}
    assert result["inventory_input"] == {"variant": "product", "role": "inventory"}
    assert other not in result["hypotheses"][0]["cue_refs"]
    assert result["hypotheses"] == roles[3].body["hypotheses"]
    roles[1] = replace(roles[1], product_id="unadmitted:equivalent-query")
    roles[2] = replace(roles[2], product_id="unadmitted:equivalent-inventory")
    assert project(frame, context, roles) == result


@pytest.mark.parametrize(
    "change,match",
    [
        ("same-span-carrier", "qualifying carrier"),
        ("missing-carrier", "exact query carrier"),
        ("foreign-target", "outside selected inventory"),
        ("duplicate-assertion", "repeats an assertion"),
        ("missing-authored", "admitted authored attribution"),
        ("unsupported-cue", "computational support"),
        ("wrong-source", "actual source occurrence"),
        ("wrong-anchor", "source slice is invalid"),
    ],
)
def test_binding_refuses_custody_substitution_without_promoting_absence(change, match):
    frame, context, roles, other = witness_case()
    roles = deepcopy(roles)
    hypotheses = roles[3].body["hypotheses"]
    if change == "same-span-carrier":
        hypotheses[0]["cue_refs"] = [other]
    elif change == "missing-carrier":
        roles.pop(4)
    elif change == "foreign-target":
        hypotheses[0]["target_id"] = "foreign"
    elif change == "duplicate-assertion":
        hypotheses.append(deepcopy(hypotheses[0]))
    elif change == "missing-authored":
        roles[3] = replace(roles[3], support=())
    elif change == "unsupported-cue":
        roles[4] = replace(roles[4], support=(), producer_output=None)
    elif change == "wrong-source":
        roles[4].body["pin"] = dict(roles[4].body["pin"], subject="other-source")
    elif change == "wrong-anchor":
        roles[4].body["anchors"][0]["source_piece"] = "invented cue"
    with pytest.raises(ValueError, match=match):
        project(frame, context, roles)


def test_arbitrary_retrieval_policy_witnesses_are_retired():
    from corpus_structure.semantic.contextual_operations import prepare_contextual_retrieval

    values = inputs()
    values["policy"]["witnesses"] = source_value([])
    with pytest.raises(ValueError, match="witness"):
        prepare_contextual_retrieval(**values, check_active=lambda: None)


def test_explicitly_empty_authored_population_stays_unassessed():
    frame, context, roles, _ = witness_case()
    roles[3].body["hypotheses"] = []
    result = project(frame, context, roles)
    assert result["hypotheses"] == []
    assert source_python(result["witnesses"]) == []
    assert result["support_state"] == "unassessed"


def test_witness_binding_executes_on_owned_cpu_with_original_basis():
    """Actual CPU correspondence; controlled headers provide no native admission."""
    import inspect
    from types import SimpleNamespace

    from corpus_structure.core.work import drive_prepared_work
    from corpus_structure.semantic.contextual_operations import contextual_operation_sources
    from corpus_structure.semantic.contextual_witnesses import execute_contextual_witness_kernel
    from corpus_structure.semantic.data_operation_cpu import PythonCPUDescriptor, plan_cpu_call
    from corpus_structure.semantic.data_operation_cpu_basis import cpu_authority_value
    from semantic.data_operation_port_support import scope

    frame, context, roles, _ = witness_case()
    processed = cpu_input_basis(
        "unadmitted:owned-witness-control",
        context,
        tuple(roles),
        parameters=canonical_bytes(semantic_value({})),
        replicate=None,
    )
    kernel = execute_contextual_witness_kernel
    signature = inspect.signature(kernel)
    arguments = signature.bind(
        input_basis=processed, frame_record=frame.record, check_active=lambda: None
    )
    sources = contextual_operation_sources()
    descriptor = PythonCPUDescriptor(
        tuple((row.module, row.filename, row.content) for row in sources.sources),
        kernel.__module__ + "." + kernel.__name__,
        (),
        verification="prepared-kernel",
        control_parameter="check_active",
    )
    cpu = scope()
    try:
        reply = drive_prepared_work(
            plan_cpu_call(
                descriptor,
                arguments,
                signature,
                verify=lambda: None,
                execution_owner=SimpleNamespace(cpu=cpu, reservation=None),
                check_active=lambda: None,
            ),
            lambda: None,
        )
        result = cpu_authority_value(reply.content, expected_basis=processed)
        assert reply.execution_receipt.result_digest
        assert [row["target_id"] for row in source_python(result["witnesses"])] == ["one", "two"]
        assert result["support_state"] == "unassessed"
    finally:
        cpu.close()


@pytest.mark.parametrize("outside_selection", [False, True])
def test_acquisition_pins_original_query_cut_and_refuses_missing_cues(
    monkeypatch, outside_selection
):
    """A controlled selected-index unit test, with no native or admission claim."""
    from contextlib import contextmanager

    from corpus_structure.semantic import contextual_selection as owner
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.semantic.data_operation_source_sets import (
        FrozenSourceSet,
        SelectedSourceSetEntry,
    )

    _frame, context, roles, other = witness_case()
    query_role = roles[1]
    from corpus_structure.semantic.demand_results import CutSelection
    from semantic.demand_result_support import demand_result_page

    page = demand_result_page()
    page.update(
        project_id=context.project_id,
        demand_id="unadmitted:query-demand",
        read_id="unadmitted:original-query-read",
    )
    cut = CutSelection.from_native(page)

    def selected_entry(product_id, member_id, selected_context):
        return SelectedSourceSetEntry.from_selected_header(
            dict(
                product_id=product_id,
                member_id=member_id,
                subject=selected_context.subject,
                subject_definition=selected_context.subject_definition,
                original_source=selected_context.original_source,
                analyzed_scope=json_loads(selected_context.analyzed_scope),
                use_id="unadmitted:query-use",
                derivation_id="unadmitted:query-episode",
                output_member_id=None,
                role="result",
                position=0,
                multiplicity=1,
            ),
            cut,
        )

    query_entry = selected_entry(query_role.product_id, query_role.member_id, context)
    selected = owner.ContextualVectorSelection(
        (FrozenSourceSet.from_selected("contextual-query", (query_entry,)),), (), context
    )

    def selected_query(connection, requested, **kwargs):
        assert requested.read_id == cut.record["read_id"]
        assert requested.expected_cut == cut.identity
        return query_role.body, query_entry, cut

    monkeypatch.setattr(owner, "_selected_product", selected_query)
    products, members = {}, {}
    for row in (roles[0], roles[4], roles[5]):
        values = dict(
            project_id=row.context.project_id,
            subject=row.context.subject,
            subject_definition=row.context.subject_definition,
            original_source=row.context.original_source,
            analyzed_scope=json_loads(row.context.analyzed_scope),
            kind_contract=row.kind_contract,
        )
        products[row.product_id] = dict(
            id=row.product_id, canonical_body=semantic_value(row.body), **values
        )
        if row.member_id is not None:
            members[row.product_id, row.member_id] = dict(
                product_id=row.product_id,
                member_id=row.member_id,
                body=semantic_value(row.body),
                **values,
            )
    if outside_selection:
        members.pop((roles[5].product_id, roles[5].member_id))

    class Index:
        def mapping(self, relation, keys):
            return products if relation == "kb.data_product" else members

    @contextmanager
    def read(*args, **kwargs):
        assert kwargs["read_id"] == cut.record["read_id"]
        assert kwargs["expected_cut"] == cut.identity
        assert kwargs["scope"] == {"product_ids": [query_role.product_id]}
        yield cut, Index()

    monkeypatch.setattr("corpus_structure.semantic.demand_results.selected_record_index", read)

    def candidates(index, exact_cut, *, product_id, member_id, anchor_use_id):
        assert exact_cut is query_entry.read
        assert anchor_use_id == query_entry.proof.anchor_use_id
        return (selected_entry(product_id, member_id, context),)

    monkeypatch.setattr(owner, "selected_source_entries", candidates)
    arguments = dict(
        project_id=context.project_id,
        query=owner.ContextualSelectedProduct("unadmitted:query-demand", query_role.product_id),
        cues=(query_role.body["carrier"], other),
    )
    if outside_selection:
        with pytest.raises(ValueError, match="unavailable or outside"):
            owner.acquire_contextual_witness_selection(None, selected, **arguments)
    else:
        actual = owner.acquire_contextual_witness_selection(None, selected, **arguments)
        assert actual.query_context == context
        assert actual.cuts == (cut,)
        assert {value.name for value in actual.source_sets} == {
            "contextual-query",
            "contextual-witness-source",
            "contextual-witness-cues",
        }
        cue_set = next(
            value for value in actual.source_sets if value.name == "contextual-witness-cues"
        )
        assert {(value.product, value.member) for value in cue_set.entries} == {
            (roles[4].product_id, "subject"),
            (roles[5].product_id, "unrelated"),
        }


def test_each_compatible_relation_keeps_exact_cited_carriers_without_same_span_substitution():
    """An author may cite two real roles; overlap alone supplies no relationship."""
    frame, context, roles, other = witness_case()
    carrier = contextual_input_reference(roles[4], contribution=True).model_dump(
        mode="python", exclude_none=True
    )
    roles[3].body["hypotheses"] = [
        dict(
            hypothesis_id="authored:" + relation,
            target_id="one",
            relation=relation,
            asserted_basis="producer_group",
            cue_refs=[carrier, other],
        )
        for relation in ("compared-with", "specializes")
    ]
    result = project(frame, context, roles)
    witnesses = source_python(result["witnesses"])
    assert {row["relation"] for row in witnesses} == {"compared-with", "specializes"}
    assert all(
        row["evidence_ids"] == [carrier["contribution_id"], other["contribution_id"]]
        for row in witnesses
    )
    assert all(
        row["basis"] == "producer_group" and row["support_state"] == "unassessed"
        for row in witnesses
    )
    assert result["author_assertion"] == "unadmitted author assertion"
    # The first cue shares its physical span with the second but has its own
    # contribution/member identity. Omitting the actual query carrier refuses.
    roles[3].body["hypotheses"][0]["cue_refs"] = [other]
    with pytest.raises(ValueError, match="qualifying carrier"):
        project(frame, context, roles)
