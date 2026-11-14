"""Method/release dimensions are admission data, independent from operation protocol outcomes."""

from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
import yaml
from pydantic import BaseModel

from corpus_structure.core.method import ObservationDraft, UnitRef, UnitResult
from corpus_structure.core.vocab import ObservationOutcome, TaskUnitType
from corpus_structure.semantic.contracts import compile_execution_model, trusted_execution_inputs
from corpus_structure.semantic.observations import bind_result
from corpus_structure.semantic.operation_results import validate_method_dimension
from corpus_structure.semantic.operations import record_method
from corpus_structure.semantic.types import PreparedRelease, RegistryRow, SourceArtifact


def bind(model):
    return PreparedRelease(
        "test-release",
        b"{}",
        (),
        (),
        (RegistryRow("execution_model", model.model_id, model.content),),
        (),
        (),
        (),
        (),
        (),
        execution_model_id=model.model_id,
    )


@pytest.fixture(scope="module")
def prepared():
    return bind(compile_execution_model(trusted_execution_inputs()))


@pytest.mark.parametrize(
    "method,dimension,value",
    [
        ("ingest.pdf", "family", "ingest"),
        ("ingest.pdf", "tier", "encoder"),
        ("agent.general", "confidence_source", "agent"),
        ("extract.math", "observation.family", "mention"),
        ("normalize.formula", "observation.family", "value"),
        ("agent.opus", "observation.outcome", "failed"),
        ("agent.opus", "observation.confidence_source", "agent"),
    ],
)
def test_admitted_method_specific_values(prepared, method, dimension, value):
    validate_method_dimension(prepared, method, dimension, value)


@pytest.mark.parametrize(
    "method,dimension,value",
    [
        ("ingest.pdf", "family", "extract"),
        ("ingest.pdf", "tier", "agent"),
        ("agent.general", "confidence_source", None),
        ("extract.math", "observation.family", "value"),
        ("normalize.formula", "observation.family", "mention"),
        ("normalize.formula", "observation.outcome", "done"),
        ("agent.opus", "observation.confidence_source", "verifiers"),
        ("not.declared", "family", "ingest"),
    ],
)
def test_wrong_method_or_dimension_values_refuse(prepared, method, dimension, value):
    with pytest.raises(ValueError):
        validate_method_dimension(prepared, method, dimension, value)


def test_metadata_refusal_precedes_any_configuration_write(prepared):
    connection = MagicMock()
    method = SimpleNamespace(
        name="ingest.pdf", family="extract", tier="encoder", confidence_source=None
    )
    with pytest.raises(ValueError):
        record_method(connection, method, "default", {}, "hash", prepared=prepared)
    connection.execute.assert_not_called()


def test_observation_family_refuses_before_source_report_publication(prepared):
    class Payload(BaseModel):
        text: str

    result = UnitResult(
        ref=UnitRef(TaskUnitType.SOURCE_VIEW, 1, "unit"),
        outcome=ObservationOutcome.PRODUCED,
        observations=(
            ObservationDraft(
                kind="mention",
                payload=Payload(text="source"),
                payload_class=Payload,
                payload_version="1",
            ),
        ),
    )
    with pytest.raises(ValueError):
        bind_result(
            prepared,
            source="source",
            method="normalize.formula",
            operation_version="1",
            configuration_hash="c",
            input_hash="i",
            invocation_key="v",
            result=result,
        )


def test_release_extension_is_explicit_and_does_not_widen_another_method():
    inputs = trusted_execution_inputs()
    catalog = yaml.safe_load(inputs.catalog.content)
    domain = next(d for d in catalog["outcome_domains"] if d["id"] == "report_family_extract_math")
    domain["values"].append("authored_extension")
    extended = bind(
        compile_execution_model(
            replace(
                inputs,
                catalog=SourceArtifact(
                    inputs.catalog.name, yaml.safe_dump(catalog, sort_keys=False).encode()
                ),
            )
        )
    )
    validate_method_dimension(extended, "extract.math", "observation.family", "authored_extension")
    with pytest.raises(ValueError):
        validate_method_dimension(
            extended, "normalize.formula", "observation.family", "authored_extension"
        )
