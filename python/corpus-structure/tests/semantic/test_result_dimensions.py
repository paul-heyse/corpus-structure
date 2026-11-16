"""Finite result contracts are release-bound and keep unrelated meanings separate."""

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_results import validate_result_dimension
from corpus_structure.semantic.types import RegistryRow
from semantic.proposals_support import prepared


@pytest.mark.parametrize(
    "operation,dimension,valid,invalid",
    [
        ("scientific_policy", "finding", "refuted", "accepted"),
        ("scientific_policy", "selection", "accepted", "warning"),
        ("read_original", "outcome", "missing", "failed"),
    ],
)
def test_result_dimensions_refuse_cross_domain_values(operation, dimension, valid, invalid):
    release = prepared(composed=True)
    validate_result_dimension(release, operation, dimension, valid)
    with pytest.raises(ValidationError):
        validate_result_dimension(release, operation, dimension, invalid)


def test_changed_bound_domain_changes_runtime_acceptance_and_does_not_reuse_old_adapter():
    release = prepared(composed=True)
    validate_result_dimension(release, "read_original", "outcome", "missing")
    row = next(r for r in release.registry_rows if r.kind == "execution_model")
    product = json.loads(row.body)
    domain = next(d for d in product["outcome_domains"] if d["id"] == "read")
    domain["values"] = ["source_ready"]
    changed = replace(
        release,
        registry_rows=tuple(
            RegistryRow(r.kind, r.name, canonical_bytes(product)) if r is row else r
            for r in release.registry_rows
        ),
    )
    with pytest.raises(ValidationError):
        validate_result_dimension(changed, "read_original", "outcome", "missing")
    validate_result_dimension(changed, "read_original", "outcome", "source_ready")


def test_changed_result_field_refuses_at_actual_constructor_binding():
    release = prepared(composed=True)
    with pytest.raises(ValueError, match="differs from constructor"):
        validate_result_dimension(release, "read_original", "outcome", "missing", field="protocol")
    validate_result_dimension(release, "read_original", "outcome", "missing", field="outcome")


def test_schema_only_preparation_has_no_operational_result_authority():
    release = prepared(composed=False)
    with pytest.raises(ValueError, match="composed execution binding"):
        validate_result_dimension(release, "complete", "protocol", "done")
