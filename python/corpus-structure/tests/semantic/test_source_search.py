"""Source-only current native/MCP journeys through real DDO publication custody."""

import base64
from hashlib import sha256
from importlib.resources import files

import anyio
import pytest
from fastmcp import Client
from sqlalchemy.exc import DBAPIError

from corpus_structure.intervene.server import build_server
from corpus_structure.semantic.data_operation_json import json_loads
from corpus_structure.semantic.demand_results import selected_read_snapshot
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.source_search import SourceSearchRequest, search_source
from semantic.current_pdf_source_support import PROJECT
from semantic.current_pdf_source_support import (
    current_pdf_source_factory as current_pdf_source_factory,
)
from semantic.current_pdf_source_support import published_pdf_source as published_pdf_source


def test_source_search_requires_only_source_demand_and_mcp_returns_exact_handles(
    published_pdf_source,
):
    case = published_pdf_source
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        pin, _catalog = case.publication(connection)
        found = search_source(
            connection,
            SourceSearchRequest(
                project_id=PROJECT,
                demand_id=case.demand_id,
                read_id=pin.read_id,
                sources=(pin,),
                text="Alice",
            ),
        )
        assert found.rows and all("Alice" in hit.excerpt for hit in found.rows)
        for hit in found.rows:
            assert hit.source == pin and hit.original_source == case.document_key
            assert hit.selection.derivation_id == pin.derivation_id
            assert hit.projection_digest and hit.source_digest
            assert inspect_native_source(connection, hit.selection).rows

    async def journey():
        # The read receipt was genuinely committed above; no run binding or relabelled ID.
        async with Client(
            build_server(
                project=PROJECT, demand=case.demand_id, read_engine=case.kernel.purpose("read")
            )
        ) as client:
            response = await client.call_tool(
                "find",
                {
                    "request": dict(
                        project_id=PROJECT,
                        demand_id=case.demand_id,
                        read_id=pin.read_id,
                        sources=[pin.model_dump(mode="json")],
                        text="Alice",
                    )
                },
            )
            assert not response.is_error and response.structured_content is not None
            rows = json_loads(response.structured_content["exact_json"])["rows"]
            assert rows and rows[0]["selection"]["product_id"] == pin.product_id
            inspected = await client.call_tool("inspect_source", {"request": rows[0]["selection"]})
            assert not inspected.is_error and inspected.structured_content is not None
            assert inspected.structured_content["rows"]

    anyio.run(journey)


def test_artifact_pages_remain_bound_to_exact_selected_publication(published_pdf_source):
    case = published_pdf_source
    expected = (
        files("corpus_structure")
        .joinpath("model/semantic/docling-validation.schema.json")
        .read_bytes()
    )
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        pin, _ = case.publication(connection)
        request = NativeSourceRequest(
            **pin.model_dump(), view="artifact", artifact_digest=sha256(expected).hexdigest()
        )
        actual, selected = bytearray(), request
        while True:
            reply = inspect_native_source(connection, selected)
            (chunk,) = reply.rows
            assert chunk["offset"] == len(actual) and chunk["total_bytes"] == len(expected)
            assert chunk["encoding"] == "base64" and isinstance(chunk["data"], str)
            actual.extend(base64.b64decode(chunk["data"]))
            if reply.next_cursor is None:
                break
            selected = request.model_copy(update={"cursor": reply.next_cursor})
        assert actual == expected
        for changed in (
            {"artifact_digest": "0" * 64},
            {"derivation_id": "derivation:foreign"},
            {"read_id": "read:foreign"},
        ):
            with pytest.raises((ValueError, DBAPIError)), connection.begin_nested():
                inspect_native_source(connection, request.model_copy(update=changed))


def _search_request(case, pin, **changes):
    fields = dict(
        project_id=PROJECT,
        demand_id=case.demand_id,
        read_id=pin.read_id,
        sources=[pin.model_dump()],
        text="run",
    )
    fields.update(changes)
    return SourceSearchRequest.model_validate(fields)


def test_cached_native_search_preserves_english_rank_ties_and_exact_cursor(
    current_pdf_source_factory,
    monkeypatch,
):
    from sqlalchemy import delete, insert, text

    from corpus_structure.semantic.metadata import table
    from corpus_structure.semantic.pdf_source_search import search_source_snapshot
    from corpus_structure.semantic.refusal_types import InvalidContinuation

    with current_pdf_source_factory(
        (
            ("text", "The runner was running.", "", None),
            ("text", "The runner was running.", "", None),
            ("text", "A cat sleeps.", "", None),
        )
    ) as case:
        with selected_read_snapshot(case.kernel.purpose("read")) as connection:
            pin, _ = case.publication(connection)
        request = _search_request(case, pin, limit=1)
        with search_source_snapshot(case.kernel.purpose("read")) as connection:
            first = search_source(connection, request)
            assert len(first.rows) == 1 and first.rows[0].selection.section_pointer == "#/groups/0"
            assert "running" in first.rows[0].excerpt and first.rows[0].score > 0
            # An independent SQL scalar establishes widening of the server real;
            # the fixture's one matched term has the established rank 0.1.
            expected_score = connection.scalar(text("SELECT 0.1::real::double precision"))
            assert first.rows[0].score == expected_score

            scoped = request.model_copy(update={"sections": ("#/groups/0", "#/groups/1")})
            scoped_first = search_source(connection, scoped)
            assert scoped_first.next_cursor is not None and first.next_cursor is not None
            scoped_cursor = json_loads(base64.urlsafe_b64decode(scoped_first.next_cursor))
            original_cursor = json_loads(base64.urlsafe_b64decode(first.next_cursor))
            assert scoped_cursor["selection"] != original_cursor["selection"]
            for candidate, cursor in (
                (scoped, first.next_cursor),
                (request, scoped_first.next_cursor),
            ):
                with pytest.raises(InvalidContinuation), connection.begin_nested():
                    search_source(connection, candidate.model_copy(update={"cursor": cursor}))

        def no_projection(*args, **kwargs):
            raise AssertionError("a search cache hit rendered native section text")

        monkeypatch.setattr(
            "corpus_structure.ingest.pdf_section_views.published_section_projections",
            no_projection,
        )
        with search_source_snapshot(case.kernel.purpose("read")) as connection:
            second = search_source(
                connection, request.model_copy(update={"cursor": first.next_cursor})
            )
            assert [hit.selection.section_pointer for hit in second.rows] == ["#/groups/1"]
            assert second.rows[0].score == first.rows[0].score and second.next_cursor is None
            assert second.population_complete
            # Returned-row capacity no longer rejects the three-section population.
            bounded = search_source(connection, request.model_copy(update={"max_rows": 1}))
            assert len(bounded.rows) == 1 and bounded.next_cursor is not None
            # Missing/foreign bindings must refuse before any page is exposed.
            with pytest.raises(InvalidContinuation), connection.begin_nested():
                search_source(
                    connection,
                    request.model_copy(update={"text": "cat", "cursor": first.next_cursor}),
                )
            # Original cursor key/score encoding remains exact and stable on replay.
            assert first.next_cursor is not None
            body = json_loads(base64.urlsafe_b64decode(first.next_cursor))
            assert body["version"] == 1
            assert body["score"] == expected_score.hex()
            assert json_loads(body["key"]) == [
                pin.model_dump(),
                "#/groups/0",
                "direct",
                first.rows[0].projection_digest,
            ]

        # Only the stored candidate set changes in this writable clone. The
        # removed section never matches the query, so ranking stays the same.
        candidates = table("ops.pdf_source_search_section")
        stored_columns = tuple(column for column in candidates.c if column.name != "search_vector")
        with case.kernel.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE ops.pdf_source_search_section DISABLE TRIGGER semantic_immutable"
            )
            removed = (
                connection.execute(
                    delete(candidates)
                    .where(
                        candidates.c.section_pointer == "#/groups/2",
                        candidates.c.membership == "direct",
                    )
                    .returning(*stored_columns)
                )
                .mappings()
                .one()
            )
            connection.exec_driver_sql(
                "ALTER TABLE ops.pdf_source_search_section ENABLE TRIGGER semantic_immutable"
            )
        try:
            with search_source_snapshot(case.kernel.purpose("read")) as connection:
                fewer = search_source(connection, request)
                assert fewer.rows == first.rows and fewer.next_cursor is not None
                changed_cursor = json_loads(base64.urlsafe_b64decode(fewer.next_cursor))
                assert changed_cursor["selection"] != body["selection"]
                with pytest.raises(InvalidContinuation), connection.begin_nested():
                    search_source(
                        connection, request.model_copy(update={"cursor": first.next_cursor})
                    )
        finally:
            with case.kernel.engine.begin() as connection:
                connection.execute(insert(candidates).values(dict(removed)))
        with search_source_snapshot(case.kernel.purpose("read")) as connection:
            assert search_source(connection, request).next_cursor == first.next_cursor
            with pytest.raises(InvalidContinuation), connection.begin_nested():
                search_source(connection, request.model_copy(update={"cursor": fewer.next_cursor}))


def test_publication_fill_is_separately_bounded_replays_exact_set_and_authenticates_pin(
    published_pdf_source,
    monkeypatch,
):
    from copy import deepcopy

    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.pdf_source_search import (
        ensure_search_projection,
        projection_recipe,
        search_source_snapshot,
    )
    from corpus_structure.semantic.refusal_types import ReadLimit
    from corpus_structure.serve.selected_pdf import acquire_selected_pdf_source

    case = published_pdf_source
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        pin, _ = case.publication(connection)
    with search_source_snapshot(case.kernel.purpose("read")) as connection:
        source = acquire_selected_pdf_source(connection, pin)
        recipe, policy = projection_recipe(connection, source)
        with pytest.raises(ReadLimit), connection.begin_nested():
            ensure_search_projection(
                connection, source, recipe=recipe, policy=policy, fill_max_bytes=1
            )
        recorded = []
        original = DataOperationStorage.ensure_pdf_search_projection

        def capture(self, payload):
            if "rows" in payload:
                recorded.append(deepcopy(payload))
            return original(self, payload)

        monkeypatch.setattr(DataOperationStorage, "ensure_pdf_search_projection", capture)
        with connection.begin_nested() as first_fill:
            population = ensure_search_projection(connection, source, recipe=recipe, policy=policy)
            assert population.row_count > 0 and len(recorded) == 1
            first_fill.rollback()
        packet = recorded[0]
        # Validate both a new population and replay against the stored exact set.
        for replay in (False, True):
            if replay:
                assert (
                    original(DataOperationStorage(connection), packet)["set_digest"]
                    == population.digest
                )
            for change in ("text", "member", "recipe", "pin", "bound", "missing-row"):
                changed = deepcopy(packet)
                if change == "text":
                    text = changed["rows"][0]["projection"]["text"]
                    assert text
                    changed["rows"][0]["projection"]["text"] = (
                        "x" if text[0] != "x" else "y"
                    ) + text[1:]
                elif change == "member":
                    changed["rows"][0]["projection"]["items"].append("#/texts/999999")
                elif change == "recipe":
                    changed["recipe"]["policy_digest"] = "0" * 64
                elif change == "pin":
                    changed["source"]["derivation_id"] = "derivation:foreign"
                elif change == "bound":
                    changed["fill_max_bytes"] = 1
                else:
                    changed["rows"].pop()
                with pytest.raises(DBAPIError) as refused, connection.begin_nested():
                    original(DataOperationStorage(connection), changed)
                assert getattr(refused.value.orig, "sqlstate", None) == (
                    "54000" if change == "bound" else "23514"
                )
        assert (
            ensure_search_projection(connection, source, recipe=recipe, policy=policy) == population
        )


def test_opening_search_hit_rechecks_fresh_pinned_projection(published_pdf_source):
    from corpus_structure.semantic.pdf_source_search import search_source_snapshot

    case = published_pdf_source
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        pin, _ = case.publication(connection)
    with search_source_snapshot(case.kernel.purpose("read")) as connection:
        found = search_source(connection, _search_request(case, pin, text="Alice"))
        hit = found.rows[0]
        assert hit.selection.projection_digest == hit.projection_digest
        assert inspect_native_source(connection, hit.selection).rows
        with (
            pytest.raises(ValueError, match="freshly read pinned projection"),
            connection.begin_nested(),
        ):
            inspect_native_source(
                connection, hit.selection.model_copy(update={"projection_digest": "0" * 64})
            )
        with pytest.raises((ValueError, DBAPIError)), connection.begin_nested():
            inspect_native_source(
                connection, hit.selection.model_copy(update={"derivation_id": "derivation:foreign"})
            )


def test_concurrent_first_find_uses_one_bounded_producer_and_both_requests_progress(
    published_pdf_source,
    monkeypatch,
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event, Lock

    from corpus_structure.ingest import pdf_section_views
    from corpus_structure.semantic.pdf_source_search import search_source_snapshot

    case = published_pdf_source
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        pin, _ = case.publication(connection)
    with selected_read_snapshot(case.kernel.purpose("read")) as connection:
        from corpus_structure.semantic.pdf_record_reader import PublishedPdfReader
        from corpus_structure.serve.selected_pdf import acquire_selected_pdf_source

        source = acquire_selected_pdf_source(connection, pin)
        has_sections = bool(
            PublishedPdfReader(
                connection,
                source.physical,
                projection_context=source.prepared,
            ).sections()
        )
    entered, release, second_started = Event(), Event(), Event()
    lock, calls = Lock(), []
    original = pdf_section_views.published_section_projections

    def producer(*args, **kwargs):
        with lock:
            calls.append(kwargs["membership"])
        entered.set()
        assert release.wait(20), "test did not release the actual first-fill producer"
        return original(*args, **kwargs)

    monkeypatch.setattr(pdf_section_views, "published_section_projections", producer)

    def find(second=False):
        with search_source_snapshot(case.kernel.purpose("read")) as connection:
            if second:
                second_started.set()
            return search_source(connection, _search_request(case, pin, text="Alice"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(find)
        try:
            assert entered.wait(20)
            second = pool.submit(find, True)
            assert second_started.wait(20)
        finally:
            release.set()
        left, right = first.result(timeout=30), second.result(timeout=30)
    assert left.model_dump() == right.model_dump()
    # One fill invokes the central producer once for each membership, not once per caller.
    assert calls == (["direct", "descendants"] if has_sections else ["direct"])
