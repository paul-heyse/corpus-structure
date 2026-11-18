"""Native allowlist projection controls; these do not qualify protected issuance."""

from dataclasses import dataclass
from functools import cache

import pytest
from pglast import ast
from scenario_recipes import register_scenario_builder
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.declared_structural_references import DeclaredStructuralSource
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import metadata
from corpus_structure.semantic.prepared_sql import prepare_sql
from corpus_structure.semantic.record_policy import RecordAcceptanceInstance
from corpus_structure.semantic.record_policy_authority import (
    DdoFittedRecordPolicy,
    DdoRecordPolicyApplicability,
    policy_authorization_value,
)
from corpus_structure.semantic.record_policy_completion_native import (
    record_policy_completion_native_sql,
)
from semantic.record_policy_support import calibrated, fitted
from test_preparation import preparation_fixture


@dataclass(frozen=True)
class PolicyProjectionRecipe:
    sql: bytes
    codecs: bytes


@dataclass(frozen=True)
class PolicyProjectionStage:
    @property
    def seed_files(self):
        return ()

    def validate_clone(self, admin):
        with admin.connect() as connection:
            assert connection.scalar(
                text(
                    "SELECT to_regprocedure('ops.ddo_policy_authorization_value(jsonb)') IS NOT NULL"
                )
            )


def build_policy_projection(recipe, admin, writer, directory, *, purpose_engine=None):
    with admin.begin() as connection:
        for sql, names in (
            (recipe.codecs, {"ddo_normalize", "ddo_field", "ddo_json"}),
            (recipe.sql, {"ddo_policy_authorization_value", "ddo_policy_authorization_meaning"}),
        ):
            parsed = prepare_sql(sql.decode(), source="policy-projection-source")
            for index, statement in enumerate(parsed.statements):
                if (
                    isinstance(statement.stmt, ast.CreateFunctionStmt)
                    and statement.stmt.funcname
                    and statement.stmt.funcname[-1].sval in names
                ):
                    connection.exec_driver_sql(
                        parsed.excerpt(index), execution_options={"no_parameters": True}
                    )
    return PolicyProjectionStage()


register_scenario_builder(PolicyProjectionRecipe, build_policy_projection)


@preparation_fixture("record_policy_projection")
def policy_projection_connection(scenario_seeds):
    from corpus_structure.semantic.data_operation_storage import native_protocol_sources, native_sql

    recipe = PolicyProjectionRecipe(
        record_policy_completion_native_sql(metadata).encode(),
        native_sql(native_protocol_sources()).encode(),
    )
    with scenario_seeds.rollback_family(recipe) as case:
        yield case.connection


@cache
def basis():
    source = DeclaredStructuralSource(
        source='["product:source",null]',
        subject="native:selected",
        subject_definition="selected-native-source",
        document="original:one",
        projection_digest="a" * 64,
        section_pointer="#/groups/0",
        membership="descendants",
        project_id="project:one",
        original_source="original:one",
        analyzed_scope_meaning='["null"]',
        source_product="product:source",
        kind_contract="kind:source",
    )
    feature = fitted()
    instance = RecordAcceptanceInstance(
        feature=feature,
        calibration=calibrated(feature),
        threshold=0.5,
        threshold_procedure="fixed-threshold-1",
        conditioning_assumptions="explicit source population",
    )
    return DdoFittedRecordPolicy.from_instance(
        instance,
        family_contract="kind:table-reading",
        reading_recipe="recipe:reading",
        judgment_basis_digest="b" * 64,
        applicability=DdoRecordPolicyApplicability(project_id=source.project_id, sources=(source,)),
    )


def project(connection, value):
    return connection.scalar(
        text("SELECT ops.ddo_policy_authorization_value(CAST(:basis AS jsonb))"),
        {"basis": canonical_bytes(value).decode()},
    )


def test_native_projection_matches_exact_public_parameters_and_raw_digest_bytes(
    policy_projection_connection,
):
    current = basis()
    expected = policy_authorization_value(
        current.instance,
        family_contract=current.family_contract,
        reading_recipe=current.reading_recipe,
        judgment_basis_digest=current.judgment_basis_digest,
        applicability=current.applicability,
        numerical_policy=current.numerical_policy,
    ).model_dump(mode="json")
    actual = project(policy_projection_connection, current.model_dump(mode="json"))
    assert actual == expected
    assert set(actual) == set(expected)
    assert (
        "fit" not in actual and "instance" not in actual and "instance_canonical_json" not in actual
    )
    assert actual["policy_instance_digest"] == current.instance.digest
    assert actual["feature_instance_digest"] == current.instance.feature.digest
    assert actual["source_release_id"] == "release:test"


@pytest.mark.parametrize(
    "field", ["instance_canonical_json", "feature_canonical_json", "calibration_canonical_json"]
)
def test_native_projection_refuses_changed_canonical_parameter_body(
    policy_projection_connection, field
):
    current = basis().model_dump(mode="json")
    current[field] = "{}"
    with pytest.raises(DBAPIError, match="canonical fitted"):
        project(policy_projection_connection, current)


@pytest.mark.parametrize(
    "change",
    [
        "missing-calibration",
        "same-fit-frame",
        "same-reference",
        "changed-feature-digest",
        "provisional-fit",
    ],
)
def test_native_projection_refuses_unfitted_or_unheld_out_basis(
    policy_projection_connection, change
):
    import json

    current = basis().model_dump(mode="json")
    instance = current["instance"]
    if change == "missing-calibration":
        instance["calibration"] = None
    elif change == "same-fit-frame":
        instance["calibration"]["fit"]["frame_digest"] = instance["feature"]["fit"]["frame_digest"]
    elif change == "same-reference":
        instance["calibration"]["fit"]["reference_digest"] = instance["feature"]["fit"][
            "reference_digest"
        ]
    elif change == "changed-feature-digest":
        instance["calibration"]["feature_instance_digest"] = "c" * 64
    else:
        instance["feature"]["fit"]["standing"] = "provisional"
    for field, value in (
        ("instance", instance),
        ("feature", instance["feature"]),
        ("calibration", instance["calibration"]),
    ):
        current[field + "_canonical_json"] = canonical_bytes(value).decode()
    # The typed Python boundary independently refuses these malformed fitted values.
    with pytest.raises(ValueError):
        DdoFittedRecordPolicy.model_validate_json(json.dumps(current))
    with pytest.raises(DBAPIError, match="canonical fitted"):
        project(policy_projection_connection, current)


def test_native_projection_preserves_exact_floating_point_semantic_subtrees(
    policy_projection_connection,
):
    from corpus_structure.semantic.data_operation_identity import semantic_value

    current = basis()
    feature = current.instance.feature.model_copy(
        update={
            "parameters": current.instance.feature.parameters.model_copy(
                update={"intercept": -0.0}
            ),
        }
    )
    assert current.instance.calibration is not None
    calibration = current.instance.calibration.model_copy(
        update={"feature_instance_digest": feature.digest}
    )
    instance = RecordAcceptanceInstance.model_validate_json(
        canonical_bytes(
            current.instance.model_copy(
                update={"feature": feature, "calibration": calibration}
            ).model_dump(mode="json")
        )
    )
    changed = DdoFittedRecordPolicy.from_instance(
        instance,
        family_contract=current.family_contract,
        reading_recipe=current.reading_recipe,
        judgment_basis_digest=current.judgment_basis_digest,
        applicability=current.applicability,
    )
    expected = policy_authorization_value(
        instance,
        family_contract=changed.family_contract,
        reading_recipe=changed.reading_recipe,
        judgment_basis_digest=changed.judgment_basis_digest,
        applicability=changed.applicability,
    ).model_dump(mode="json")
    actual = policy_projection_connection.scalar(
        text("SELECT ops.ddo_policy_authorization_meaning(CAST(:basis AS jsonb))"),
        {"basis": canonical_bytes(semantic_value(changed.model_dump(mode="json"))).decode()},
    )
    assert actual == semantic_value(expected)
    expected["parameters"]["intercept"] = 0.0
    assert actual != semantic_value(expected)
