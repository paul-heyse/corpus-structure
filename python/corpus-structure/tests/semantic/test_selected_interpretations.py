"""Actual captured private proposal types and current selected-read transport.

Controlled native replies here establish adapter semantics, not native admission.
"""

from decimal import Decimal

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_admission import bound_data_operation_model
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.types import ResolvedDependencies
from corpus_structure.serve.interpretations import (
    SelectedProposalRequest,
    inspect_selected_proposals,
)
from semantic.test_external_rich_extraction import rich_bundle as rich_bundle


@pytest.fixture(scope="module")
def prepared(rich_bundle):
    return prepare_release(rich_bundle, data_operation_dependencies(ResolvedDependencies()))


def body():
    return dict(
        proposal_type="alternative",
        standing="private_proposed",
        id="a1",
        claims=[{"member_id": "claim:c1"}],
        faithful=True,
        reason="Explicit private alternative",
    )


@pytest.mark.parametrize("invalid", [None, "unknown-kind", "accepted-standing"])
def test_selected_proposals_keep_actual_nominal_kind_context_and_private_standing(
    prepared, monkeypatch, invalid
):
    from corpus_structure.serve import interpretations

    model = bound_data_operation_model(prepared)
    iri = prepared.index.definitions["DdoRichAlternativeProposal"].iri
    kind = next(
        identity.key
        for identity in model.identities
        if identity.owner == iri and identity.domain == "kind"
    )
    value = body()
    if invalid == "accepted-standing":
        value["standing"] = "accepted"
    row = dict(
        product_id="product:selected",
        member_id="alternative:a1",
        use_id="use:selected",
        derivation_id="derivation:original",
        subject="source:selected",
        subject_definition="original-source-view",
        original_source="document:selected",
        analyzed_scope={"fraction": Decimal("0.123456789012345678901")},
        kind_contract=kind,
        body=value,
    )
    cut = {
        "release_id": prepared.release_id,
        "read_id": "read:selected",
        "scope": {"fraction": Decimal("0.123456789012345678901")},
    }
    result = dict(
        cut=cut,
        items=[row, {**row, "kind_contract": "unrelated", "body": {"standing": "accepted"}}],
        obligations=[{"fate": "unknown"}],
        uses=[],
        populations=[],
        continuation="next:exact",
        page_complete=False,
    )
    monkeypatch.setattr(interpretations, "serve_demand_query", lambda connection, request: result)
    monkeypatch.setattr(interpretations, "open_release", lambda connection, release: prepared)
    request = SelectedProposalRequest(
        project_id="project:selected",
        demand_id="demand:selected",
        kind_contract="unknown-kind" if invalid == "unknown-kind" else None,
    )
    if invalid is not None:
        with pytest.raises(ValueError):
            inspect_selected_proposals(None, request)
        return
    answer = inspect_selected_proposals(None, request)
    assert answer.body["items"] == [row]
    assert answer.body["cut"] == cut and answer.body["obligations"] == [{"fate": "unknown"}]
    assert answer.body["knowledge"] == "observed"
    assert answer.body["capability"] == "selected_private_proposal_members"
    assert answer.body["continuation"] == "next:exact"


def test_current_private_request_refuses_integer_review_aliases():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        SelectedProposalRequest.model_validate(
            {"review_run_id": 1, "review_cut_id": 2, "contribution_ids": ["c"]}
        )
    with pytest.raises(ValidationError):
        SelectedProposalRequest.model_validate(
            {"project_id": "p", "demand_id": "d", "view": "support"}
        )


def test_main_mcp_private_proposal_tool_preserves_exact_scope_and_server_selection(monkeypatch):
    import anyio
    from fastmcp import Client
    from sqlalchemy import create_engine

    from corpus_structure.intervene import interpretation_tools
    from corpus_structure.intervene.server import build_server
    from corpus_structure.semantic.data_operation_json import json_loads
    from corpus_structure.serve.interpretations import answer

    seen = []

    def inspect(connection, request):
        seen.append(request)
        return answer(
            "selected_private_proposals",
            {
                "cut": {"analyzed_scope": {"fraction": Decimal("0.123456789012345678901")}},
                "items": [],
                "knowledge": "unknown",
            },
        )

    monkeypatch.setattr(interpretation_tools, "inspect_selected_proposals", inspect)
    engine = create_engine("sqlite://")

    async def check():
        async with Client(
            build_server(project="project:one", demand="demand:one", read_engine=engine)
        ) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            annotations = tools["inspect_private_proposals"].annotations
            assert annotations is not None and annotations.read_only_hint is True
            assert (
                "group_measurement_interpretations" not in tools
                and "inspect_terminology_review" not in tools
            )
            for project in ("project:foreign", "project:one"):
                response = await client.call_tool(
                    "inspect_private_proposals",
                    {"request": {"project_id": project, "demand_id": "demand:one"}},
                    raise_on_error=False,
                )
                assert response.is_error == (project == "project:foreign")
                if not response.is_error:
                    assert response.structured_content is not None
                    content = json_loads(response.structured_content["exact_json"])
                    assert content["body"]["cut"]["analyzed_scope"]["fraction"] == Decimal(
                        "0.123456789012345678901"
                    )
            assert len(seen) == 1 and "original_source" not in seen[0].model_fields_set

    try:
        anyio.run(check)
    finally:
        engine.dispose()


def test_grouped_mcp_tool_preserves_root_pins_and_server_authority(monkeypatch):
    import anyio
    from fastmcp import Client
    from sqlalchemy import create_engine

    from corpus_structure.intervene import interpretation_tools
    from corpus_structure.intervene.server import build_server
    from corpus_structure.serve.interpretations import answer

    seen = []

    def inspect(connection, request):
        seen.append(request)
        return answer("grouped_source_record_interpretations", {"items": [], "knowledge": "unknown"})

    monkeypatch.setattr(interpretation_tools, "group_selected_interpretations", inspect)
    engine = create_engine("sqlite://")

    async def check():
        async with Client(build_server(project="project:one", demand="demand:one", read_engine=engine)) as client:
            tools = {tool.name: tool for tool in await client.list_tools()}
            assert tools["group_source_record_interpretations"].annotations.read_only_hint is True
            for demand in ("demand:foreign", "demand:one"):
                result = await client.call_tool("group_source_record_interpretations", {"request": {"project_id": "project:one", "demand_id": demand, "roots": [{"product_id": "product:one", "member_id": "record:one", "interpretation_id": "reading:one"}]}}, raise_on_error=False)
                assert result.is_error == (demand == "demand:foreign")
        assert len(seen) == 1
        assert seen[0].roots[0].interpretation_id == "reading:one"

    try:
        anyio.run(check)
    finally:
        engine.dispose()
