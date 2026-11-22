"""Current selected characterization preserves the native cut and exact scoped selection."""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from corpus_structure.serve.characterization import (
    DemandCharacterizationRequest,
    _characterization_summary,
    inspect_demand_characterization,
)


@pytest.mark.parametrize(
    "inventory,view,record_type,containers",
    [
        ("summary", "members", None, True),
        ("occurrences", "members", "occurrence", False),
        ("annotations", "members", "annotation", False),
        ("terms", "members", "term", False),
        ("memberships", "members", "membership", False),
        ("choices", "members", "choice", False),
        ("coverage", "coverage", None, False),
    ],
)
@pytest.mark.parametrize("source", ["omitted", None, "original:selected"])
def test_inventory_delegates_real_selected_population_without_losing_null_source_semantics(
    monkeypatch, inventory, view, record_type, containers, source
):
    from corpus_structure.semantic import contribution_queries

    received = []
    result = dict(
        cut={"read_id": "read:actual", "scope": {"fraction": Decimal("0.123456789012345678901")}},
        items=[],
        obligations=[{"fate": "waiting"}],
        uses=[],
        populations=[{"status": "incomplete"}],
        page_complete=False,
        continuation="exact:continuation",
        knowledge="unknown",
    )

    def read(connection, request):
        received.append(request)
        return result

    monkeypatch.setattr(contribution_queries, "read_demand_contributions", read)
    value = dict(
        project_id="project:selected",
        demand_id="demand:selected",
        inventory=inventory,
        product_id="product:selected",
        member_id="membership:off-page",
        cursor="previous:continuation",
        limit=2,
    )
    if source != "omitted":
        value["original_source"] = source
    selected = DemandCharacterizationRequest.model_validate(value)
    actual = inspect_demand_characterization(None, selected)
    if inventory == "summary":
        assert actual["projection"] == "characterization-summary-1"
        assert actual["cut"] is result["cut"]
        assert actual["continuation"] == result["continuation"]
    else:
        assert actual is result
    request = received[0]
    assert request.view == view and request.record_type == record_type
    assert request.containers_only is containers
    assert request.product_id == "product:selected" and request.member_id == "membership:off-page"
    assert request.cursor == "previous:continuation" and request.limit == 2
    assert ("original_source" in request.model_fields_set) is (source != "omitted")
    assert request.original_source == (None if source == "omitted" else source)
    assert actual["knowledge"] == "unknown" and not actual["page_complete"]


def test_current_characterization_refuses_task_layer_pins_and_unbounded_reads():
    for values in (
        {"run_id": 1, "task_id": 2, "product_key": "view", "content_digest": "a" * 64},
        {"limit": 0},
        {"max_bytes": 1},
        {"inventory": "reading", "layer_key": "old-layer"},
    ):
        with pytest.raises(ValidationError):
            DemandCharacterizationRequest.model_validate(
                {"project_id": "project:selected", "demand_id": "demand:selected", **values}
            )


def _native_header(index=0):
    return dict(
        spacy_version="3.8.11",
        model="retained-model",
        model_version="original-version",
        profile_recipe="original-profile:" + str(index),
        pipeline_config_digest="a" * 64,
        availability=[dict(family="syntax", attribute="dependency", status="complete")],
        configuration="private pipeline configuration",
        tokens=[{"text": "private token"}],
    )


def test_summary_projects_metadata_counts_and_original_provider_digests_without_payloads():
    body = dict(
        source={"document": "original", "projection": "b" * 64},
        outcome="partial",
        members=[
            {"body": {"record_type": "annotation", "text": "private annotation"}},
            {"body": {"record_type": "annotation"}},
            {"body": {"record_type": "term"}},
        ],
        coverage=[
            dict(
                family="roles",
                outcome="unknown",
                availability="unavailable",
                reason="private reason",
            )
        ],
        dependencies=[{"product_id": "original-primary"}],
        blocks=[{"annotation": _native_header()}, {"annotation": _native_header()}],
    )
    summary = _characterization_summary(body, native_annotation=True)
    assert summary["member_counts"] == {"annotation": 2, "term": 1}
    assert summary["dependency_count"] == 1
    assert summary["coverage"] == (
        {"family": "roles", "outcome": "unknown", "availability": "unavailable"},
    )
    (provider,) = summary["providers"]
    assert provider["provider"] == "spacy" and provider["runtime_version"] == "3.8.11"
    assert provider["configuration_digest"] == "a" * 64
    assert provider["availability"][0]["status"] == "complete"
    from corpus_structure.semantic.data_operation_json import json_bytes

    assert b"private" not in json_bytes(summary)
    assert "members" not in summary and "blocks" not in summary
    # A similarly spelled value in an unrelated nominal kind grants no provider attribution.
    assert _characterization_summary(body)["providers"] is None
    unknown = _characterization_summary({"outcome": "partial"})
    assert unknown["coverage"] is None and unknown["member_counts"] is None


def test_summary_metadata_bounds_report_actual_omissions():
    headers = []
    for index in range(18):
        header = _native_header(index)
        header["availability"] = header["availability"] * 40
        headers.append({"annotation": header})
    summary = _characterization_summary(
        {
            "blocks": headers,
            "coverage": [
                dict(family=str(index), outcome="partial", availability="unknown")
                for index in range(70)
            ],
            "members": [],
        },
        native_annotation=True,
    )
    assert len(summary["providers"]) == 16 and summary["providers_omitted"] == 2
    assert all(
        len(provider["availability"]) == 32 and provider["availability_omitted"] == 8
        for provider in summary["providers"]
    )
    assert len(summary["coverage"]) == 64 and summary["coverage_omitted"] == 6
    assert summary["member_counts"] == {}


def test_summary_preserves_selected_custody_and_does_not_advertise_full_body_resource(monkeypatch):
    from types import SimpleNamespace

    from corpus_structure.semantic import contribution_queries, releases
    from corpus_structure.serve import source_catalog

    body = dict(
        outcome="partial", members=[], coverage=[], blocks=[{"annotation": _native_header()}]
    )
    row = dict(
        product_id="product:actual",
        use_id="use:actual",
        derivation_id="derivation:actual",
        kind_contract="kind:native",
        body=body,
        meaning_body=["string", "private tagged value"],
    )
    result = dict(
        cut={"release_id": "release:actual"},
        items=[row],
        obligations=[],
        uses=[],
        populations=[],
        knowledge="observed",
        page_complete=False,
        continuation="same:cursor",
        resource_handle="full:body",
    )
    monkeypatch.setattr(contribution_queries, "read_demand_contributions", lambda *_: result)
    prepared = SimpleNamespace()
    monkeypatch.setattr(releases, "open_release", lambda *_: prepared)
    monkeypatch.setattr(
        source_catalog,
        "_kind_contracts",
        lambda _, root: (
            {"kind:native": "DdoSourceAnnotations"} if root == "DdoCharacterizationEnvelope" else {}
        ),
    )
    actual = inspect_demand_characterization(
        None, DemandCharacterizationRequest(project_id="p", demand_id="d")
    )
    assert actual["cut"] is result["cut"] and actual["continuation"] == "same:cursor"
    assert actual["items"][0]["product_id"] == "product:actual"
    assert actual["items"][0]["use_id"] == "use:actual"
    assert actual["items"][0]["derivation_id"] == "derivation:actual"
    assert {"body", "meaning_body"}.isdisjoint(actual["items"][0])
    assert "resource_handle" not in actual
    assert actual["items"][0]["summary"]["outcome"] == "partial"
    assert result["items"][0]["meaning_body"] == ["string", "private tagged value"]
    assert result["items"][0]["body"] is body and result["resource_handle"] == "full:body"
