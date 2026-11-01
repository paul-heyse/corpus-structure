"""Input graph assessments cannot be reassigned by surviving output pointer spellings."""

import json
from dataclasses import replace
from typing import Any

import pytest
import yaml

from corpus_structure.semantic.pdf_contracts import (
    integrated_metadata_policy,
    trusted_pdf_context,
    validate_pdf_report_metadata,
)
from corpus_structure.semantic.types import SourceArtifact


def integrated() -> dict[str, Any]:
    return dict(
        kind="integrated",
        source_scope="whole_document",
        document={"pages": {}},
        items=[{"pointer": "#/texts/0", "label": "formula"}],
        health=dict(
            conversion="success",
            display_coverage="partial",
            inline_coverage="unknown",
            cell_coverage="unknown",
            formula_outcomes=[{"pointer": "#/texts/0", "outcome": "unknown"}],
        ),
    )


def test_current_unknown_inventory_is_accepted_without_transferring_input_assessments():
    validate_pdf_report_metadata(integrated())


@pytest.mark.parametrize("defect", ["success", "nonformula", "missing", "coverage", "runtime"])
def test_stale_assessment_refuses_even_when_pointer_or_section_spelling_survives(defect):
    value = integrated()
    if defect == "success":
        value["health"]["formula_outcomes"][0]["outcome"] = "succeeded"
    elif defect == "nonformula":
        value["items"][0]["label"] = "text"
    elif defect == "missing":
        value["health"]["formula_outcomes"] = []
    elif defect == "coverage":
        value["recognition_coverage"] = [{"section_pointer": "#/groups/0"}]
    else:
        value["metadata_kinds"] = ["runtime_report"]
    with pytest.raises(ValueError, match=r"integration|formula recognition"):
        validate_pdf_report_metadata(value)


def test_policy_is_loaded_from_exact_context_schema_instead_of_installed_yaml():
    context = trusted_pdf_context()
    staging = context.staging
    assert staging is not None
    schema = yaml.safe_load(staging.content)
    policy = json.loads(schema["annotations"]["pds:integrated_metadata_policy"])
    policy["formula_outcome"] = "not_requested"
    schema["annotations"]["pds:integrated_metadata_policy"] = json.dumps(policy)
    archived = replace(
        context, staging=SourceArtifact(staging.name, yaml.safe_dump(schema).encode())
    )
    assert integrated_metadata_policy(archived)["formula_outcome"] == "not_requested"
    assert integrated_metadata_policy(context)["formula_outcome"] == "unknown"
