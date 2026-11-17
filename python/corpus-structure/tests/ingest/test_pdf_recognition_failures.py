"""Provider failures are classified at the recorded HTTP boundary, without model calls."""

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path

import httpx
import pytest
from PIL import Image

from corpus_structure.ingest.pdf_recognition import RecognitionPage, terminal_recognition_result


@pytest.fixture
def worker_module():
    path = Path(__file__).parents[4] / "services/nemotron-parse/worker.py"
    spec = importlib.util.spec_from_file_location("controlled_recognition_worker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("status", [400, 413, 422, 401, 403, 404, 409, 500, 503])
@pytest.mark.parametrize("generation", ["admitted", "changed"])
def test_http_failure_class_requires_input_status_and_admitted_generation(
    tmp_path, worker_module, status, generation
):
    backend = worker_module.RecordingBackend(
        dict(
            model="test",
            identity_assurance="trusted_managed_service",
            service_binding={"generation": "admitted"},
            timeout_seconds=1,
            endpoint="http://controlled/v1",
        ),
        tmp_path,
    )
    backend.client.close()
    backend.client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                status,
                json={"error": "controlled response"},
                headers={"x-corpus-generation": generation},
            )
        )
    )

    @dataclass
    class Settings:
        max_tokens: int = 1

    try:
        with (
            Image.new("RGB", (2, 2)) as image,
            pytest.raises(
                (
                    httpx.HTTPStatusError,
                    worker_module.TerminalInputRefusal,
                    worker_module.ServiceGenerationChanged,
                )
            ),
        ):
            backend(image, prompt="input", stage="fullpage", settings=Settings())
    finally:
        backend.client.close()
    row = json.loads((tmp_path / "request-000.json").read_bytes())
    expected = "terminal" if status in {400, 413, 422} and generation == "admitted" else "execution"
    assert row["outcome"] == "failed" and row["outcome_class"] == expected
    assert row["http_status"] == status and row["response_generation"] == generation


@pytest.mark.parametrize(
    "result,terminal",
    [
        ({"outcome": "failed"}, False),
        ({"outcome": "failed", "outcome_class": "execution"}, False),
        ({"outcome": "failed", "outcome_class": "terminal"}, True),
        ({"outcome": "succeeded"}, True),
    ],
)
def test_unclassified_failure_has_no_reuse_or_publication_standing(tmp_path, result, terminal):
    page = RecognitionPage(1, tmp_path, result, {})
    assert terminal_recognition_result(result) is terminal
    assert page.terminal_outcome is terminal
    assert page.execution_failed is not terminal
