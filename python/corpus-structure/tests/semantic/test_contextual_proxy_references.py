"""Pure contextual replay controls; native authority has separate qualification."""

from collections import Counter
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.contextual_proxy_references import expand_selected_contextual_proxies
from corpus_structure.semantic.data_operation_values import semantic_value
from corpus_structure.semantic.data_product_reference import SemanticReference


@pytest.mark.parametrize("last_member", ["two", "missing"])
def test_contextual_replay_prepares_shared_target_without_widening_member_access(last_member):
    calls = Counter()

    class Rows(dict):
        def __init__(self, name, records):
            super().__init__(records)
            self.name = name

        def __getitem__(self, key):
            calls[self.name] += 1
            return super().__getitem__(key)

        def get(self, key, default=None):
            try:
                return self[key]
            except KeyError:
                return default

    pin = dict(role="formal", product_id="parent", position=0, multiplicity=1)
    use = dict(id="use", fate="fulfilled", derivation_id="episode", selection={"inputs": [pin]})
    target = dict(
        output_role="result",
        path="/formal_proxy_support/*/target",
        input_role="formal",
        variant="member",
        input_kind="inventory",
    )
    tables = {
        "ops.demand_use": {"use": use},
        "ops.data_derivation": {"episode": dict(release_id="release", request_id="request")},
        "ops.data_request": {"request": dict(operation_id="operation")},
        "sem.data_operation_definition": {
            ("release", "operation"): dict(
                support_contract={"reference_targets": [target]},
                input_roles=[
                    dict(name="formal", kind="inventory", accepted_kind_contracts=["kind"])
                ],
            )
        },
        "kb.data_product": {"parent": dict(project_id="project", kind_contract="kind")},
        "kb.data_product_member": {
            ("parent", member): dict(
                body=semantic_value(dict(record_type="annotation", local_id=member))
            )
            for member in ("one", "two")
        },
        "kb.data_product_partition": {},
        "sem.data_kind_contract": {"kind": {}},
    }
    maps = {relation: Rows(relation, records) for relation, records in tables.items()}

    def rows_for(relation, **fields):
        calls[relation + ":rows"] += 1
        if relation == "ops.data_derivation_output":
            return (dict(derivation_id="episode", role="result"),)
        if relation == "ops.data_derivation_input":
            return (pin,)
        assert relation == "ops.demand_use"
        return (use,)

    index = SimpleNamespace(mapping=lambda relation, _: maps[relation], rows_for=rows_for)
    cut = SimpleNamespace(record={"project_id": "project"})
    members = ("one", last_member)
    value = dict(
        formal_proxy_support=[
            dict(
                owner="proxy:" + member,
                target=SemanticReference.member("formal", member).values(),
            )
            for member in members
        ],
        construction_proxy_support=[],
        members=[
            dict(member_id="proxy:" + member, body=dict(kind="context.symbolic_site"))
            for member in members
        ],
    )
    if last_member == "missing":
        with pytest.raises(ValueError, match="does not resolve its declared target"):
            expand_selected_contextual_proxies(value, index, cut, "contextual")
    else:
        expanded = expand_selected_contextual_proxies(value, index, cut, "contextual")
        for member, packet in zip(members, expanded["members"], strict=True):
            assert packet["body"]["external_premises"] == [
                dict(
                    product_id="parent",
                    member_id=member,
                )
            ]
    assert calls["ops.demand_use"] == 1
    assert calls["sem.data_operation_definition"] == 1
    # The graph checks scalar parents once, then the prepared path checks their
    # exact historical/current intersection once for both member references.
    assert calls["ops.data_derivation_input:rows"] == 2
    assert calls["kb.data_product"] == 1
