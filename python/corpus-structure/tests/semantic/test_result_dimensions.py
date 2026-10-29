"""Finite result contracts are release-bound and keep unrelated meanings separate."""

import json
from dataclasses import replace

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.operation_results import validate_result_dimension
from corpus_structure.semantic.types import RegistryRow

from .test_proposals import prepared


@pytest.mark.parametrize(
    "operation,dimension,valid,invalid",
    [
        ("execute_source", "readiness", "awaiting_agent", "done"),
        ("hold_submission", "decision", "proceed", "refused_context"),
        ("scientific_policy", "finding", "refuted", "accepted"),
        ("scientific_policy", "selection", "accepted", "warning"),
        ("check_submission", "disposition", "completed_refused", "proceed"),
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
    validate_result_dimension(release, "hold_submission", "decision", "proceed")
    row = next(r for r in release.registry_rows if r.kind == "execution_model")
    product = json.loads(row.body)
    domain = next(d for d in product["outcome_domains"] if d["id"] == "hold_decision")
    domain["values"] = ["held"]
    changed = replace(
        release,
        registry_rows=tuple(
            RegistryRow(r.kind, r.name, canonical_bytes(product)) if r is row else r
            for r in release.registry_rows
        ),
    )
    with pytest.raises(ValidationError):
        validate_result_dimension(changed, "hold_submission", "decision", "proceed")
    validate_result_dimension(changed, "hold_submission", "decision", "held")


def test_check_submission_contract_binds_session_commit_and_locator_is_subordinate():
    release = prepared(composed=True)
    product = json.loads(next(r.body for r in release.registry_rows if r.kind == "execution_model"))
    operation = next(o for o in product["operations"] if o["id"] == "check_submission")
    implementation = next(
        b for b in product["implementations"] if b["id"] == operation["implementation"]
    )
    assert (implementation["owner"], implementation["symbol"]) == (
        "intervene.semantic",
        "ProposalSession.commit",
    )
    assert (
        next(i for i in product["invariants"] if i["id"] == "packet_reads")["implementation"]
        == "submission"
    )


def test_changed_result_field_refuses_at_actual_constructor_binding():
    release = prepared(composed=True)
    with pytest.raises(ValueError, match="differs from constructor"):
        validate_result_dimension(
            release, "execute_source", "readiness", "source_ready", field="protocol"
        )
    validate_result_dimension(
        release, "execute_source", "readiness", "source_ready", field="status"
    )
