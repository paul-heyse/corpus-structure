"""Bounded disclosure interpretation is distinct from complete protected provenance."""

from copy import deepcopy
from dataclasses import asdict
from functools import lru_cache

import pytest

from corpus_structure.semantic.authority_leaf import validate_authority_leaf
from corpus_structure.semantic.record_policy_authority import AUTHORIZATION_EFFECT, AUTHORIZATION_FACTORY, AUTHORIZATION_KIND


@lru_cache(maxsize=1)
def public_policy_body():
    from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
    from corpus_structure.semantic.record_policy import RecordAcceptanceInstance
    from corpus_structure.semantic.record_policy_authority import DdoRecordPolicyApplicability, policy_authorization_value
    from semantic.record_policy_support import fitted, calibrated

    source = DeclaredStructuralSource(
        source='["product:source",null]', subject="selected-source", subject_definition="source-view",
        document="source:A", original_source="source:A", project_id="project:A", projection_digest="a" * 64,
        section_pointer="#/groups/0", membership="direct", analyzed_scope_meaning='["null"]',
        source_product="product:source", kind_contract="kind:source",
    )
    feature = fitted()
    instance = RecordAcceptanceInstance(feature=feature, calibration=calibrated(feature), threshold=0.5,
        threshold_procedure="fixed", conditioning_assumptions="controlled finite source cut")
    return policy_authorization_value(
        instance, family_contract="kind:table", reading_recipe="recipe:readings", judgment_basis_digest="b" * 64,
        applicability=DdoRecordPolicyApplicability(project_id="project:A", sources=(source,)),
    ).model_dump(mode="json")


def disclosure():
    from corpus_structure.semantic.data_operation_identity import semantic_value
    row = dict(
        format="ddo-native-authority-leaf-v1", derivation_id="issuer:one", use_id="use:one",
        issuer_operation="record_policy.authorize", release_id="release:one", runtime_id="runtime:one",
        recipe="recipe:one", product_id="product:authorization", kind_contract="kind:authorization",
        intent_id="intent:opaque", receipt_id="receipt:opaque", standing="valid", protected_dependencies="undisclosed",
    )
    effect = {**asdict(AUTHORIZATION_EFFECT), "authorization": list(AUTHORIZATION_EFFECT.authorization)}
    definition = dict(
        profile="command", recipe="recipe:one", support_contract=dict(effects=[effect], capabilities=dict(
            preparation="native-publication", forms=["scalar"], prepared_factory=dict(entrypoint=AUTHORIZATION_FACTORY),
        )),
    )
    contracts = dict(
        products={"product:authorization": {"kind_contract": "kind:authorization", "canonical_body": semantic_value(public_policy_body())}},
        kinds={"kind:authorization": {"kind": AUTHORIZATION_KIND, "universe": "ordinary"}},
        definitions={("release:one", "record_policy.authorize"): definition},
        runtimes={("release:one", "runtime:one")},
    )
    return row, contracts


def test_bounded_authority_requires_actual_captured_contracts():
    row, contracts = disclosure()
    leaf = validate_authority_leaf(row, **contracts)
    assert leaf.product_id == "product:authorization"
    assert leaf.protected_dependencies == "undisclosed"
    for field in ("kinds", "definitions", "runtimes"):
        with pytest.raises(ValueError, match="captured"):
            validate_authority_leaf(row, **{**contracts, field: None})


@pytest.mark.parametrize("changed", [
    {"issuer_operation": "unrelated"}, {"recipe": "another"}, {"runtime_id": "another"},
    {"protected_dependencies": "complete"}, {"protected_inputs": ["secret"]},
])
def test_bounded_authority_cannot_claim_unknown_issuer_or_hidden_closure(changed):
    row, contracts = disclosure()
    with pytest.raises(ValueError):
        validate_authority_leaf({**row, **changed}, **contracts)


def test_same_named_kind_or_factory_is_not_a_captured_native_command():
    row, contracts = disclosure()
    for change in ("effect", "factory", "universe", "profile"):
        modified = deepcopy(contracts)
        definition = modified["definitions"]["release:one", "record_policy.authorize"]
        if change == "effect":
            definition["support_contract"]["effects"] = []
        elif change == "factory":
            definition["support_contract"]["capabilities"]["prepared_factory"]["entrypoint"] = "foreign.factory"
        elif change == "universe":
            modified["kinds"]["kind:authorization"]["universe"] = "evaluator"
        else:
            definition["profile"] = "derivation"
        with pytest.raises(ValueError):
            validate_authority_leaf(row, **modified)


def test_virtual_authority_parquet_preserves_closed_fields_and_nullable_use(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from corpus_structure.serve.demand_export import _relation_schema

    row, _ = disclosure()
    row = {**row, "use_id": None}
    schema, columns = _relation_schema("ops.data_authority_leaf", set(row), "cut:controlled")
    assert columns == ()
    assert schema.field("use_id").nullable
    assert not schema.field("receipt_id").nullable
    path = tmp_path / "authority.parquet"
    pq.write_table(pa.Table.from_pylist([row], schema=schema), path)
    retained = pq.read_table(path)
    assert retained.to_pylist() == [row]
    assert retained.schema.metadata[b"cs.cut"] == b"cut:controlled"
    with pytest.raises(ValueError, match="closed disclosure fields"):
        _relation_schema("ops.data_authority_leaf", set(row) | {"hidden_reference"}, "cut:controlled")
