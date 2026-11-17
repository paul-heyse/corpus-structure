"""Native immutable-correspondence guard with an actual Python-validated body.

The controlled request/definition rows exercise this guard only. They confer no
producer fence, runtime authority, published product, or current support standing.
"""

import json

import pytest
from pglast import ast
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.data_operation_identity import semantic_value
from corpus_structure.semantic.established_validity import product_validation_native_sql
from corpus_structure.semantic.formal_products import FormalEvidenceOptions
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.prepared_sql import prepare_sql
from semantic.formal_products_support import profile as profile
from semantic.formal_products_support import publication_context, selected
from semantic.test_data_operation_cpu_basis import cpu_basis_connection as cpu_basis_connection


def test_retained_validation_requires_exact_whole_product_context(semantic_bare_engine):
    """Controlled rows test immutable correspondence, not current support authority."""
    from sqlalchemy import Column, MetaData, Table, Text
    from sqlalchemy.dialects.postgresql import JSONB

    physical = MetaData()
    episode = Table("data_derivation", physical, Column("id", Text), Column("intent_id", Text), Column("release_id", Text), schema="ops")
    intent = Table("data_completion_intent", physical, Column("id", Text), Column("payload", JSONB), schema="ops")
    output = Table("data_derivation_output", physical, Column("derivation_id", Text), Column("product_id", Text), Column("member_id", Text), schema="ops")
    product = Table(
        "data_product", physical,
        *(Column(name, Text) for name in ("id", "body_digest", "project_id", "subject", "subject_definition", "original_source")),
        Column("analyzed_scope", JSONB), schema="kb",
    )
    context = dict(project_id="project", subject="subject", subject_definition="definition", original_source="original", analyzed_scope={"scope": "whole"})
    expected = dict(release_id="release", body_id="body:result", subject_context_json=json.dumps(context))
    changed = {**expected, "subject_context_json": json.dumps({**context, "original_source": "other"})}
    prepared = prepare_sql(product_validation_native_sql(), source="retained-validation-control")
    declaration = next(
        prepared.excerpt(index)
        for index, raw in enumerate(prepared.statements)
        if isinstance(raw.stmt, ast.CreateFunctionStmt)
        and raw.stmt.funcname[-1].sval == "ddo_product_validation"
    )
    with semantic_bare_engine.connect() as conn:
        tx = conn.begin()
        conn.exec_driver_sql("CREATE SCHEMA ops")
        conn.exec_driver_sql("CREATE SCHEMA kb")
        physical.create_all(conn)
        conn.exec_driver_sql(declaration, execution_options={"no_parameters": True})
        conn.execute(episode.insert().values(id="episode", intent_id="intent", release_id="release"))
        conn.execute(intent.insert().values(id="intent", payload={"execution_evidence": {"product_validations": [changed, expected]}}))
        conn.execute(product.insert().values(id="product", body_digest="body:result", **context))
        conn.execute(output.insert().values(derivation_id="episode", product_id="product", member_id="member"))
        query = text("SELECT ops.ddo_product_validation(:episode,:product)")
        assert conn.execute(query, dict(episode="episode", product="product")).scalar_one() is None
        conn.execute(output.update().values(member_id=None))
        assert conn.execute(query, dict(episode="episode", product="product")).scalar_one() == expected
        assert conn.execute(query, dict(episode="other", product="product")).scalar_one() is None
        assert conn.execute(query, dict(episode="episode", product="other")).scalar_one() is None
        conn.execute(product.update().values(body_digest="body:other"))
        assert conn.execute(query, dict(episode="episode", product="product")).scalar_one() is None
        tx.rollback()


def test_native_guard_binds_actual_validator_body_and_premises(profile, cpu_basis_connection):
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    connection = cpu_basis_connection
    for source, names in (
        (native_sql(native_protocol_sources()), {"ddo_identity", "ddo_json"}),
        (product_validation_native_sql(), {"ddo_require_product_validations"}),
    ):
        parsed = prepare_sql(source, source="established-validity-correspondence-control")
        for index, statement in enumerate(parsed.statements):
            node = statement.stmt
            if (
                isinstance(node, ast.CreateFunctionStmt)
                and node.funcname
                and node.funcname[-1].sval in names
            ):
                connection.exec_driver_sql(
                    parsed.excerpt(index), execution_options={"no_parameters": True}
                )

    source = selected(profile, "Quantity: 2 kg")
    context = publication_context(source)
    product = profile.run(source, FormalEvidenceOptions(), subject_context=context)
    proof = product.established_validity
    assert proof is not None
    operation = next(
        item
        for item in profile.model.operations
        if any(asset.contract == proof.validator_contract for asset in item.assets)
    )
    connection.execute(
        table("sem.data_operation_definition")
        .insert()
        .values(
            release_id=profile.prepared.release_id,
            operation_id=operation.semantic_id,
            subject_definition=context.subject_definition,
            recipe="recipe:controlled-validity",
            profile="derivation",
            implementation_revision="implementation:controlled-validity",
            input_roles=[],
            output_roles=[],
            support_contract={
                "assets": [
                    {
                        "contract": proof.validator_contract,
                        "content_digest": proof.validator_revision,
                    }
                ]
            },
            binding_expression={},
            definition_identity="definition:controlled-validity",
            eligibility_identity="eligibility:controlled-validity",
            quantified=False,
            dependencies=[],
        )
    )
    request = dict(
        context.record, release_id=profile.prepared.release_id, operation_id=operation.semantic_id
    )
    completion = {
        "outputs": [
            {
                "product": {
                    "body": semantic_value(
                        product.value.model_dump(mode="json", exclude_unset=True)
                    )
                }
            }
        ],
        "execution_evidence": {"product_validations": [proof.model_dump(mode="json")]},
    }

    def check(value):
        connection.execute(
            text(
                "SELECT ops.ddo_require_product_validations("
                "jsonb_populate_record(NULL::ops.data_request,CAST(:request AS jsonb)),"
                "CAST(:completion AS jsonb))"
            ),
            {
                "request": canonical_bytes(request).decode(),
                "completion": canonical_bytes(value).decode(),
            },
        )

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
        with pytest.raises(DBAPIError), connection.begin_nested():
            check(changed)
