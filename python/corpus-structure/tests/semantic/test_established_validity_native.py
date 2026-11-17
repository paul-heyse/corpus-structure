"""Native immutable-correspondence guard with an actual Python-validated body.

The controlled request/definition rows exercise this guard only. They confer no
producer fence, runtime authority, published product, or current support standing.
"""

import json

import pytest
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.established_validity import product_validation_native_sql
from corpus_structure.semantic.formal_products import FormalEvidenceOptions
from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import publication_context, selected
from semantic.test_data_operation_cpu_basis import cpu_basis_connection as cpu_basis_connection


def test_native_guard_binds_actual_validator_body_and_premises(profile, cpu_basis_connection):
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    connection = cpu_basis_connection
    for source, names in (
        (native_sql(native_protocol_sources()), {"ddo_identity"}),
        (product_validation_native_sql(), {"ddo_require_product_validations"}),
    ):
        parsed = prepare_sql(source, source="established-validity-correspondence-control")
        for index, statement in enumerate(parsed.statements):
            node = statement.stmt
            if isinstance(node, ast.CreateFunctionStmt) and node.funcname[-1].sval in names:
                connection.exec_driver_sql(parsed.excerpt(index), execution_options={"no_parameters": True})

    source = selected(profile, "Quantity: 2 kg")
    context = publication_context(source)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    proof = product.established_validity
    assert proof is not None
    operation = next(
        item for item in profile.model.operations
        if any(asset.contract == proof.validator_contract for asset in item.assets)
    )
    connection.execute(table("sem.data_operation_definition").insert().values(
        release_id=profile.prepared.release_id,
        operation_id=operation.semantic_id,
        subject_definition=context.subject_definition,
        recipe="recipe:controlled-validity",
        profile="derivation",
        implementation_revision="implementation:controlled-validity",
        input_roles=[], output_roles=[],
        support_contract={"assets": [{"contract": proof.validator_contract,
                                     "content_digest": proof.validator_revision}]},
        binding_expression={}, definition_identity="definition:controlled-validity",
        eligibility_identity="eligibility:controlled-validity", quantified=False, dependencies=[],
    ))
    request = dict(
        context.record, release_id=profile.prepared.release_id, operation_id=operation.semantic_id
    )
    completion = {
        "outputs": [{"product": {"body": semantic_value(
            product.value.model_dump(mode="json", exclude_unset=True)
        )}}],
        "execution_evidence": {"product_validations": [proof.model_dump(mode="json")]},
    }

    def check(value):
        connection.execute(text(
            "SELECT ops.ddo_require_product_validations("
            "jsonb_populate_record(NULL::ops.data_request,CAST(:request AS jsonb)),"
            "CAST(:completion AS jsonb))"
        ), {"request": canonical_bytes(request).decode(),
            "completion": canonical_bytes(value).decode()})

    check(completion)
    for field, replacement in (
        ("validator_revision", "0" * 64),
        ("body_id", "body:" + "0" * 64),
        ("source_json", "{}"),
        ("selectors_json", "[]"),
        ("subject_context_json", "{}"),
        ("release_id", "another-release"),
    ):
        changed = json.loads(canonical_bytes(completion))
        changed["execution_evidence"]["product_validations"][0][field] = replacement
        with pytest.raises(DBAPIError):
            with connection.begin_nested():
                check(changed)
