"""Declared-kind catalog membership and exact selected-source correspondence.

The adapter controls use genuine compiled schemas with controlled read replies;
publication admission and trust remain the separate native journey obligation.
"""

from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest

from corpus_structure.semantic.composed import data_operation_dependencies
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.pdf_capture import pdf_capture_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.source_discovery import source_discovery_inputs
from corpus_structure.semantic.types import ResolvedDependencies, SourceArtifact, SourceBundle
from corpus_structure.serve.native_source import NativeSourceResponse
from corpus_structure.serve.source_catalog import (
    SourceCatalogRequest,
    _kind_contracts,
    read_source_catalog,
)


@pytest.fixture(scope="module")
def prepared_catalog():
    path = Path(__file__).parents[2] / "src/corpus_structure/model/semantic/core.yaml"
    bundle = source_discovery_inputs(
        pdf_capture_inputs(SourceBundle("core", (SourceArtifact("core", path.read_bytes()),)))
    )
    return prepare_release(bundle, data_operation_dependencies(ResolvedDependencies()))


def publication():
    return dict(
        document="original:book",
        source_digest="a" * 64,
        logical_digest="b" * 64,
        schema_digest="c" * 64,
        recipe_digest="d" * 64,
        kind="native",
        health=dict(
            conversion="success",
            display_coverage="unknown",
            inline_coverage="unknown",
            cell_coverage="unknown",
        ),
    )


def test_catalog_classifies_actual_nominal_inheritance_not_operation_or_body_spelling(
    prepared_catalog,
):
    actual = _kind_contracts(prepared_catalog, "DdoPdfPublication")
    assert set(actual.values()) == {
        "DdoPdfPublication",
        "DdoPdfCapture",
        "DdoPdfEnrichedPublication",
        "DdoPdfIntegratedPublication",
        "DdoPdfOrganizedPublication",
    }
    assert set(_kind_contracts(prepared_catalog, "DdoSelectedNativeSource").values()) == {
        "DdoSelectedNativeSource"
    }


@pytest.mark.parametrize("defect", [None, "different-cut", "ambiguous-header"])
def test_catalog_requires_exact_selected_native_publication_header(
    prepared_catalog, monkeypatch, defect
):
    from corpus_structure.semantic import releases
    from corpus_structure.serve import source_catalog

    kind = next(
        key
        for key, name in _kind_contracts(prepared_catalog, "DdoPdfPublication").items()
        if name == "DdoPdfCapture"
    )
    cut = dict(
        project_id="project:one",
        demand_id="demand:one",
        read_id="read:one",
        release_id=prepared_catalog.release_id,
    )
    header = dict(
        member_id=None,
        kind_contract=kind,
        subject="subject:original",
        subject_definition="original-document",
        original_source="original:book",
        analyzed_scope={"scope": "whole-document"},
        use_id="use:one",
        product_id="product:one",
        derivation_id="derivation:original",
    )
    # A misleading operation ID and superficially publication-shaped nonmatching kind
    # do not grant membership. The compiled nominal contract alone selects the row.
    page = dict(
        cut=cut,
        items=[
            dict(header, body=publication()),
            dict(header, kind_contract="unrelated-kind", body=publication()),
        ],
        obligations=[{"operation_id": "unrelated.operation", "fate": "unknown"}],
        uses=[],
        populations=[],
        continuation="next:pinned",
        page_complete=False,
    )

    def query(connection, request):
        assert request.containers_only and request.view == "members"
        assert request.cursor == "prior:pinned" and request.limit == 2
        return page

    monkeypatch.setattr(source_catalog, "serve_demand_query", query)
    monkeypatch.setattr(releases, "open_release", lambda connection, release: prepared_catalog)
    seen = []

    def inspect(connection, request, *, cancellation):
        seen.append(request)
        return NativeSourceResponse(
            selection=request,
            release_id="release:original-producer",
            cut={**cut, "read_id": "read:foreign"} if defect == "different-cut" else cut,
            health={"conversion": "success"},
            rows=[{"artifact_digest": "a" * 64}] * (2 if defect == "ambiguous-header" else 1),
        )

    monkeypatch.setattr(source_catalog, "inspect_native_source", inspect)
    request = SourceCatalogRequest(
        project_id="project:one", demand_id="demand:one", cursor="prior:pinned", limit=2
    )
    if defect is not None:
        with pytest.raises(ValueError, match=r"exact selected read|one complete native header"):
            read_source_catalog(None, request)
        return
    response = read_source_catalog(None, request)
    assert len(response.rows) == len(seen) == 1
    assert seen[0].model_dump(
        include={"project_id", "demand_id", "read_id", "use_id", "product_id", "derivation_id"}
    ) == {
        "project_id": "project:one",
        "demand_id": "demand:one",
        "read_id": "read:one",
        "use_id": "use:one",
        "product_id": "product:one",
        "derivation_id": "derivation:original",
    }
    assert response.rows[0]["release_id"] == "release:original-producer"
    assert response.rows[0]["publication"] == publication()
    assert response.obligations == page["obligations"]
    assert not response.page_complete and response.next_cursor == "next:pinned"
    assert len(json_bytes(response.model_dump(mode="python"))) < request.max_bytes


@pytest.mark.parametrize("member_id", [None, "member:actual-selected-packet"])
def test_view_catalog_preserves_member_identity_exact_scope_and_unknown_standing(
    prepared_catalog, monkeypatch, member_id
):
    from corpus_structure.semantic import releases, serving_identity
    from corpus_structure.semantic.data_operation_values import semantic_value
    from corpus_structure.semantic.demand_results import CutSelection
    from corpus_structure.semantic.native_source_view import thaw_native
    from corpus_structure.serve import source_catalog
    from semantic.test_rich_query_delivery import CUT
    from semantic.test_source_discovery import source

    kind = next(iter(_kind_contracts(prepared_catalog, "DdoSelectedNativeSource")))
    body = thaw_native(
        source(SimpleNamespace(prepared=prepared_catalog), document="original:book", start=1, end=3)
    )
    row = dict(
        obligation_id="obligation:population",
        member_id=member_id,
        kind_contract=kind,
        subject="subject:original-view",
        subject_definition="original-source-view",
        original_source="original:book",
        analyzed_scope={"selectors": body["selectors"]},
        use_id="use:population",
        product_id="product:population",
        derivation_id="derivation:population",
        body=body,
    )
    page = dict(
        cut={**CUT, "release_id": prepared_catalog.release_id, "read_id": "read:population"},
        items=[row],
        obligations=[{"fate": "unknown"}],
        uses=[],
        populations=[{"complete": False}],
        continuation=None,
        page_complete=True,
    )
    monkeypatch.setattr(releases, "open_release", lambda connection, release: prepared_catalog)

    calls = []

    def answer(connection, program, demand, **request):
        calls.append(request)
        assert program == "read_selected_outputs" and demand == "demand:population"
        assert not request.get("body", False)
        if request.get("source_metadata"):
            assert request["kind_contracts"] == [kind]
            assert request["read_id"] == "read:population"
            values = [
                {
                    **{name: value for name, value in row.items() if name != "body"},
                    "source": semantic_value(body["source"]),
                    "selectors": semantic_value(body["selectors"]),
                }
            ]
        else:
            values = []
        return dict(cut=page["cut"], rows=values, answer_after=None, oversized=None)

    def frontier(connection, demand, **request):
        assert request["view"] == "frontier"
        assert request["continuation"]["obligation_id"] == "obligation:population"
        return SimpleNamespace(cut=CutSelection.from_native(page["cut"]), record=page)

    monkeypatch.setattr(source_catalog, "read_selected_answer", answer)
    monkeypatch.setattr(source_catalog, "read_demand_result", frontier)
    monkeypatch.setattr(
        serving_identity,
        "installed_read_implementation",
        lambda *args, **kwargs: nullcontext("implementation:catalog"),
    )
    monkeypatch.setattr(
        source_catalog,
        "inspect_native_source",
        lambda *args, **kwargs: pytest.fail("view catalog opened a native PDF"),
    )
    response = read_source_catalog(
        None,
        SourceCatalogRequest(project_id="project:one", demand_id="demand:population", view="views"),
    )
    assert response.rows[0]["member_id"] == row["member_id"]
    assert response.rows[0]["source"] == body["source"]
    assert response.rows[0]["selectors"] == body["selectors"]
    assert response.rows[0]["analyzed_scope"] == row["analyzed_scope"]
    assert response.populations == [{"complete": False}] and response.obligations == [
        {"fate": "unknown"}
    ]
    assert len(calls) == 2
