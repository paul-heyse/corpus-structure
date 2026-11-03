"""Parsing and custody refusal controls; actual managed-provider evidence lives in its dated folder."""

import importlib.util
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from PIL import Image

from corpus_structure.methods.llm.producer import producer_binding


def service_module(name):
    path = Path(__file__).resolve().parents[4] / "services/nemotron-parse" / (name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("method", ["agent.opus", "agent.general"])
def test_two_producer_identities_share_one_contract(method):
    assert producer_binding(method, {"model": "configured"}).configured_model == "configured"


@pytest.mark.parametrize(
    "values,unit",
    [
        ({"mode": "adjudicate"}, "source_view"),
        ({"proposal_protocol": "unimplemented"}, "source_view"),
        ({"proposal_version": "unimplemented"}, "source_view"),
        ({"execution_kind": "unimplemented"}, "source_view"),
        ({}, "document"),
    ],
)
def test_incompatible_producer_bindings_refuse(values, unit):
    with pytest.raises(ValueError, match="not executable"):
        producer_binding("agent.general", {"model": "configured", **values}, unit=unit)


@pytest.mark.parametrize(
    "response_generation,expected", [("g", "succeeded"), ("replacement", "failed")]
)
def test_backend_retains_generation_mismatch_without_trust_upgrade(
    tmp_path, response_generation, expected
):
    worker = service_module("worker")
    backend = worker.RecordingBackend(
        {
            "timeout_seconds": 1,
            "endpoint": "http://controlled/v1",
            "model": "configured-alias",
            "identity_assurance": "trusted_managed_service",
            "service_binding": {"generation": "g"},
        },
        tmp_path,
    )
    backend.client.close()

    def response(request):
        assert request.headers["x-corpus-generation"] == "g"
        return httpx.Response(
            200,
            headers={"x-corpus-generation": response_generation},
            json={
                "model": "provider-reported-alias",
                "choices": [{"message": {"content": "source"}, "finish_reason": "stop"}],
            },
        )

    backend.client = httpx.Client(transport=httpx.MockTransport(response))

    @dataclass
    class Settings:
        temperature: float = 0

    with Image.new("RGB", (8, 8), "white") as image:
        if expected == "failed":
            with pytest.raises(ValueError, match="generation boundary"):
                backend(image, prompt="parse", stage="fullpage", settings=Settings())
        else:
            assert (
                backend(image, prompt="parse", stage="fullpage", settings=Settings())["raw_out"]
                == "source"
            )
    row = backend.rows[0]
    assert row["outcome"] == expected
    assert row["identity_assurance"] == (
        "trusted_managed_service" if expected == "succeeded" else "provider_reported"
    )
    assert (tmp_path / row["http_response"]).exists()
    backend.client.close()


def test_persisted_producer_version_cannot_be_silently_relabelled():
    with pytest.raises(ValueError, match="persisted producer version"):
        producer_binding("agent.general", {"model": "configured"}, method_version="semantic-old")
