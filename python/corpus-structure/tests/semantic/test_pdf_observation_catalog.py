"""Selected provider-failure observations retain genuine native receipt custody.

This native journey is required after the combined current source capture. The
controlled submitted response establishes no actual model/provider qualification.
"""

import json
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256

import pytest
from pydantic import ValidationError

from corpus_structure.semantic.data_operation_external import ExternalDataSession
from corpus_structure.semantic.data_operation_service import (
    DemandOperationSelection,
    execute_data_demand,
)
from corpus_structure.semantic.demand_results import selected_read_snapshot
from corpus_structure.semantic.refusal_types import InvalidContinuation
from corpus_structure.serve.pdf_visual_evidence import visual_observation_manifest
from corpus_structure.serve.source_catalog import SourceCatalogRequest
from semantic.current_pdf_source_support import PROJECT, ROOT
from semantic.current_pdf_source_support import current_pdf_source as current_pdf_source


@pytest.mark.parametrize(
    "changes",
    [
        {"limit": 0},
        {"limit": 1001},
        {"limit": True},
        {"run_id": 1},
        {"task_id": 2},
        {"view": "recognition_observation"},
    ],
)
def test_current_source_catalog_requires_typed_bounded_semantic_scope(changes):
    with pytest.raises(ValidationError):
        SourceCatalogRequest.model_validate(
            dict(project_id="project:one", demand_id="demand:one", **changes)
        )


def test_failed_provider_observation_remains_selected_and_inspectable(
    current_pdf_source, monkeypatch, cli
):
    case = current_pdf_source
    with case.kernel.purpose("write").begin() as connection:
        demand = case.register(
            connection,
            "source.visual/recognize",
            selections=(
                DemandOperationSelection(
                    operation="source.visual_input/render", parameters={"selection": {"page_no": 1}}
                ),
            ),
        )
    execute_data_demand(
        case.kernel.purpose("write"),
        demand,
        source_root=ROOT,
        admission_engine=case.kernel.purpose("admit"),
        project_id=PROJECT,
        database_capacity=6,
    )
    session = ExternalDataSession(case.kernel.purpose("write"), PROJECT, demand_id=demand)
    (packet,) = session.queue()["packets"]
    claim = session.claim(packet["packet_id"])
    assert claim["state"] == "claimed"
    submitted = session.read(packet["packet_id"], claim)
    (image,) = submitted["input_views"]
    assert image["role"] == "image" and image["value"]["document"] == case.document_key
    raw = ""
    completed = session.submit(
        packet["packet_id"],
        claim,
        {
            "outcome": "success",
            "outputs": [
                {
                    "role": "observation",
                    "body": dict(
                        image=image["value"],
                        raw_response=raw,
                        response_digest=sha256(raw.encode()).hexdigest(),
                        finish_reason="inference_error",
                        runtime_identity_json='{"controlled":"no model inference"}',
                        provider_outcome="failed",
                        diagnostic="Independent controlled provider failure",
                    ),
                }
            ],
        },
        actor_assertion="controlled-source-native-test",
        model_assertion=None,
    )
    assert completed["state"] == "committed"
    selected = replace(case, demand_id=demand)
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        source, _ = selected.publication(connection)
        continuation, entries = None, []
        while True:
            page = visual_observation_manifest(
                connection, source, continuation=continuation, limit=1
            )
            entries.extend(page.observations)
            if page.continuation is None:
                break
            continuation = page.continuation
        (observation,) = entries
        assert observation.execution_outcome == "failed"
        assert observation.mapping_availability == "not_selected" and observation.mapped is None
        assert observation.raw_producer["producer_task_id"] == claim["task_id"]
        assert observation.raw_producer["producer_attempt"] == claim["attempt"]
        with pytest.raises(InvalidContinuation):
            visual_observation_manifest(
                connection,
                source,
                continuation={
                    "source": {**source.model_dump(), "read_id": "read:foreign"},
                    "page_no": None,
                    "native": {},
                },
            )
    from corpus_structure.semantic import runtime

    @contextmanager
    def opened(*args, **kwargs):
        assert kwargs["purpose"] == "read"
        yield case.kernel.purpose("read")

    monkeypatch.setattr(runtime, "open_runtime_engine", opened)
    result = cli(
        "source",
        "visual-observations",
        "--project",
        PROJECT,
        "--demand",
        demand,
        "--read",
        source.read_id,
        "--use",
        source.use_id,
        "--product",
        source.product_id,
        "--derivation",
        source.derivation_id,
        "--json",
    )
    assert result.exit_code == 0, result.output
    actual = json.loads(result.stdout)
    assert actual["observations"][0]["execution_outcome"] == "failed"
    assert actual["observations"][0]["raw"]["derivation_id"] == observation.raw.derivation_id
