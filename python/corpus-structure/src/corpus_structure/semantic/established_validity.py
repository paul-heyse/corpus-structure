"""Actual trusted-producer validation, retained in its original sealed intent.

This is a record of successful Python validation, not independent native replay or
current support authority. Readers still acquire current support and caller rights.
"""

from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .data_operation_identity import body_identity
from .data_operation_json import json_bytes, json_loads


class ProductValidation(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    format: Literal["producer-product-validation-1"] = "producer-product-validation-1"
    release_id: str = Field(min_length=1)
    validator_contract: Literal[
        "formal/profile-assets",
        "characterization/construction-assets",
        "characterization/contextual-assets",
    ]
    validator_revision: str = Field(pattern=r"^[0-9a-f]{64}$")
    body_id: str = Field(pattern=r"^body:[0-9a-f]{64}$")
    source_json: str = Field(min_length=1)
    selectors_json: str = Field(min_length=1)
    subject_context_json: str | None


def admitted_validator_revision(model, contract):
    revisions = {
        asset.content_digest
        for operation in model.operations
        for asset in operation.assets
        if asset.contract == contract
    }
    return next(iter(revisions)) if len(revisions) == 1 else None


def _body_id(body):
    return body_identity(body).key


def _json(value):
    return json_bytes(value).decode()


def _context_matches(model, context, body):
    from .data_operation_model import validate_subject_context
    from .source_products import source_subject

    validate_subject_context(model, context)
    return (
        context.subject == source_subject(body["source"])
        and context.original_source == body["source"]["document"]
        and json_loads(context.analyzed_scope)
        == json_loads(_json(dict(source=body["source"], selectors=body["selectors"])))
    )


def successful_product_validation(prepared, model, body, contract, revision, context):
    """Called only at the full semantic validator's successful return boundary."""
    if admitted_validator_revision(model, contract) != revision:
        return None
    if context is not None and not _context_matches(model, context, body):
        return None
    return ProductValidation(
        release_id=prepared.release_id,
        validator_contract=contract,
        validator_revision=revision,
        body_id=_body_id(body),
        source_json=_json(body["source"]),
        selectors_json=_json(body["selectors"]),
        subject_context_json=None if context is None else _json(context.identity_record),
    )


def bind_product_validation(product, context):
    """Bind the already successful result to the acquired publication context."""
    proof = product.established_validity
    if proof is None or context is None:
        return None
    body = product.value.model_dump(mode="python", exclude_unset=True)
    if proof.body_id != _body_id(body) or not _context_matches(product.model, context, body):
        return None
    if (
        proof.subject_context_json is not None
        and json_loads(proof.subject_context_json) != context.identity_record
    ):
        return None
    return proof.model_copy(update={"subject_context_json": _json(context.identity_record)})


def selected_product_validation(member):
    """Read the native projection carried by this exact selected whole input."""
    if member is None or member.member is not None:
        return None
    evidence = json.loads(member.support_evidence)
    value = evidence.get("product_validation")
    return None if value is None else ProductValidation.model_validate(value, strict=True)


def established_product_matches(proof, *, prepared, model, body, source, context, contract):
    """Only immutable correspondence is reused; no mutable standing is cached."""
    if proof is None or context is None:
        return False
    if not _context_matches(model, context, body):
        return False
    selected = source.value
    return (
        proof.release_id == prepared.release_id
        and proof.validator_contract == contract
        and proof.validator_revision == admitted_validator_revision(model, contract)
        and proof.body_id == _body_id(body)
        and proof.source_json == _json(body["source"]) == _json(selected["source"])
        and proof.selectors_json == _json(body["selectors"]) == _json(selected["selectors"])
        and proof.subject_context_json is not None
        and json_loads(proof.subject_context_json) == context.identity_record
    )


def product_validation_native_sql(*, target_metadata=None):
    """Render validation correspondence from typed expressions and physical models."""
    from pglast import ast, enums
    from pglast.stream import RawStream
    from sqlalchemy import Text, cast, column, func, literal, or_, select, true
    from sqlalchemy.dialects.postgresql import JSONB, array

    from .metadata import metadata as default_metadata
    from .native_program import (
        Assign,
        Block,
        ForQuery,
        If,
        Local,
        Parameter,
        Raise,
        core_parameter,
        core_variable,
        function,
        pg_type,
        sql_function,
    )

    metadata = default_metadata if target_metadata is None else target_metadata
    request = metadata.tables["ops.data_request"]
    definition = metadata.tables["sem.data_operation_definition"].alias("definition")
    jsonb = JSONB()
    proof, output, body, expected = (
        core_variable(name, jsonb) for name in ("proof", "output", "body", "expected_context")
    )
    completion = core_variable("completion", jsonb)

    def r(field):
        return core_variable("r", request.c[field].type, field)

    def json_array(value, name):
        return func.jsonb_array_elements(value).table_valued(column("value", jsonb)).alias(name)

    def validations(payload):
        return func.coalesce(
            payload["execution_evidence"]["product_validations"], cast(literal("[]"), jsonb)
        )

    def context(values):
        return func.jsonb_build_object(
            *(item for key, value in values.items() for item in (key, value))
        )

    context_value = context(
        dict(
            project_id=r("project_id"),
            subject=r("subject"),
            subject_definition=func.ops.ddo_operation_subject(r("release_id"), r("operation_id")),
            original_source=r("original_source"),
            analyzed_scope=r("analyzed_scope"),
        )
    )
    assets = json_array(definition.c.support_contract["assets"], "asset")
    admitted = (
        select(literal(1))
        .select_from(definition.join(assets, true()))
        .where(
            definition.c.release_id == r("release_id"),
            definition.c.operation_id == r("operation_id"),
            assets.c.value["contract"].astext == proof["validator_contract"].astext,
            assets.c.value["content_digest"].astext == proof["validator_revision"].astext,
        )
        .exists()
    )
    fields = array(list(ProductValidation.model_fields), type_=Text)
    invalid_proof = or_(
        func.jsonb_typeof(proof).is_distinct_from("object"),
        ~proof.has_all(fields),
        proof.op("-")(fields).is_distinct_from(cast(literal("{}"), jsonb)),
        proof["format"].astext.is_distinct_from(ProductValidation.model_fields["format"].default),
        proof["release_id"].astext.is_distinct_from(r("release_id")),
        cast(proof["subject_context_json"].astext, jsonb).is_distinct_from(expected),
        ~admitted,
    )
    source = cast(proof["source_json"].astext, jsonb)
    selectors = cast(proof["selectors_json"].astext, jsonb)
    # The admitted source-view subject differs from the original document's
    # document_subject. Trusted Python validation established that relation;
    # this guard retains its exact governed context and canonical input basis.
    mismatched_result = or_(
        output["member_id"].astext.is_not(None),
        proof["body_id"].astext.is_distinct_from(func.data.ddo_identity("body", body)),
        func.data.ddo_json(func.data.ddo_field(body, "source")).is_distinct_from(source),
        func.data.ddo_json(func.data.ddo_field(body, "selectors")).is_distinct_from(selectors),
        expected["original_source"].astext.is_distinct_from(source["document"].astext),
        expected["analyzed_scope"].is_distinct_from(
            context(dict(source=source, selectors=selectors))
        ),
    )
    proofs = json_array(validations(completion), "validation")
    guard_parameters = (
        Parameter("r", pg_type(str(request.schema), request.name)),
        Parameter("completion", pg_type("jsonb")),
    )
    guard = function(
        "ops",
        "ddo_require_product_validations",
        parameters=guard_parameters,
        returns=pg_type("void"),
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
        body=Block(
            locals=tuple(
                Local(name, pg_type("jsonb"))
                for name in ("proof", "output", "body", "expected_context")
            ),
            statements=(
                Assign("expected_context", context_value),
                ForQuery(
                    ("proof",),
                    select(proofs.c.value),
                    (
                        If(
                            invalid_proof,
                            (
                                Raise(
                                    "product validation lacks its actual admitted validator/context",
                                    "23514",
                                ),
                            ),
                        ),
                        If(
                            func.jsonb_array_length(completion["outputs"]) != 1,
                            (
                                Raise(
                                    "product validation requires its exact single whole result",
                                    "23514",
                                ),
                            ),
                        ),
                        Assign("output", completion["outputs"][0]),
                        Assign("body", func.data.ddo_normalize(output["product"]["body"])),
                        If(
                            mismatched_result,
                            (
                                Raise(
                                    "product validation differs from its exact canonical result/source/scope",
                                    "23514",
                                ),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )

    episode = metadata.tables["ops.data_derivation"].alias("episode")
    intent = metadata.tables["ops.data_completion_intent"].alias("intent")
    result = metadata.tables["ops.data_derivation_output"].alias("output")
    product = metadata.tables["kb.data_product"].alias("product")
    retained = json_array(validations(intent.c.payload), "proof")
    value = retained.c.value
    statement = (
        select(value)
        .select_from(
            episode.join(intent, intent.c.id == episode.c.intent_id)
            .join(
                result,
                (result.c.derivation_id == episode.c.id)
                & (result.c.product_id == core_parameter(2, result.c.product_id.type))
                & result.c.member_id.is_(None),
            )
            .join(product, product.c.id == result.c.product_id)
            .join(retained, true())
        )
        .where(
            episode.c.id == core_parameter(1, episode.c.id.type),
            value["release_id"].astext == episode.c.release_id,
            value["body_id"].astext == product.c.body_digest,
            cast(value["subject_context_json"].astext, jsonb)
            == context(
                {
                    name: product.c[name]
                    for name in (
                        "project_id",
                        "subject",
                        "subject_definition",
                        "original_source",
                        "analyzed_scope",
                    )
                }
            ),
        )
        .limit(1)
    )
    reader_parameters = (
        Parameter("episode_id", pg_type("text")),
        Parameter("product_id", pg_type("text")),
    )
    reader = sql_function(
        "ops",
        "ddo_product_validation",
        parameters=reader_parameters,
        returns=pg_type("jsonb"),
        body=statement,
        volatility="stable",
        security_definer=True,
        search_path=("pg_catalog", "pg_temp"),
    )

    def revoke(name, parameters):
        return RawStream()(
            ast.GrantStmt(
                is_grant=False,
                targtype=enums.GrantTargetType.ACL_TARGET_OBJECT,
                objtype=enums.ObjectType.OBJECT_FUNCTION,
                objects=(
                    ast.ObjectWithArgs(
                        objname=(ast.String(sval="ops"), ast.String(sval=name)),
                        objargs=tuple(parameter.type_ for parameter in parameters),
                        args_unspecified=False,
                    ),
                ),
                grantees=(ast.RoleSpec(roletype=enums.RoleSpecType.ROLESPEC_PUBLIC),),
                behavior=enums.DropBehavior.DROP_RESTRICT,
            )
        )

    return (
        ";\n".join(
            (
                guard,
                revoke("ddo_require_product_validations", guard_parameters),
                reader,
                revoke("ddo_product_validation", reader_parameters),
            )
        )
        + ";\n"
    )
