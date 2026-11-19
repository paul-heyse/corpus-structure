"""Actual installed CLI continuation reuse after fresh native authorization."""

import os
from decimal import Decimal

import pytest
from evaluate.declared_record_native_support import PROJECT
from evaluate.declared_rich_native_support import NAMESPACE

from corpus_structure.semantic.data_operation_json import json_bytes, json_loads
from semantic.record_publication_native_support import authored_publication as authored_publication
from semantic.record_publication_native_support import (
    publish_authored,
)


@pytest.mark.skipif(
    os.environ.get("CORPUS_RUN_UDM_T14") != "1",
    reason="native continuation qualification requires viable publication and complete code custody",
)
@pytest.mark.parametrize("variant", ("demand", "rich", "contributions"))
def test_installed_cli_continuation_reuses_authorized_rows_across_processes(
    variant, authored_publication, native_settings, tmp_path
):
    from typing import cast

    from conftest import settings_for_native_clone

    from corpus_structure.semantic._data_operation_wire import WireRevokeDataSupportRequest
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from semantic.record_publication_native_support import run_observed_cli

    selected = publish_authored(
        authored_publication,
        ({"kind": "number", "number": Decimal("12")}, {"kind": "number", "number": Decimal("13")}),
        entities=("authored:one", "authored:two"),
        inference="native-continuation-" + variant,
    )
    database = authored_publication.kernel.engine.url.database
    assert database is not None
    settings = settings_for_native_clone(native_settings, database)
    entity_kind = authored_publication.kernel.identities[NAMESPACE + "DdoRichEntity", "kind"]
    environment = os.environ | {
        "CORPUS_DATABASE__URL": settings.database.url,
        "CORPUS_DATABASE__MAINTENANCE_URL": settings.database.maintenance_url,
        "CORPUS_DATABASE__READER_URL": settings.database.reader_url or "",
        "CORPUS_DATABASE__EVALUATOR_URL": settings.database.evaluator_url or "",
        "CORPUS_DATABASE__ADMISSION_URL": settings.database.admission_url or "",
        "CORPUS_CACHE__ROOT": str(tmp_path / "pages"),
        "CORPUS_CACHE__PROGRAM_STORE_BYTES": "0",
        "CORPUS_CACHE__PAGE_STORE_BYTES": str(8 * 1024**2),
        "CORPUS_RUNTIME__DEFAULT_PROJECT": PROJECT,
    }
    if variant == "rich":
        command = ["query", "entity"]
        rows_field, cursor_field = "rows", "cursor"
        miss_counters = ("derived", "prepared")
        projection_counter = "prepared"
    elif variant == "demand":
        command = ["query", "members", "--kind-contract", entity_kind]
        rows_field, cursor_field = "items", "continuation"
        miss_counters = ("demand_bodies", "demand_rows")
        projection_counter = "demand_rows"
    else:
        command = [
            "contributions",
            "list",
            "--kind-contract",
            entity_kind,
            "--no-include-interpretation",
            "--no-include-assessment",
            "--no-include-operations",
        ]
        rows_field, cursor_field = "items", "cursor"
        miss_counters = ("contribution_scopes", "contribution_rows")
        projection_counter = "contribution_rows"
    command += [
        "--demand",
        selected.demand_id,
        "--product",
        selected.product["id"],
        "--limit",
        "1",
        "--max-bytes",
        "1048576",
        "--json",
    ]

    def invoke(name, *, cursor=None, project=PROJECT, cached=True):
        arguments = [*command, "--project", project]
        if cursor is not None:
            arguments += ["--cursor", cursor]
        reply, observations = run_observed_cli(
            arguments,
            environment=environment
            if cached
            else environment | {"CORPUS_CACHE__PAGE_STORE_BYTES": "0"},
            observations=tmp_path / (name + ".json"),
        )
        return reply, observations

    reply, first_observations = invoke("first")
    assert reply.returncode == 0, reply.stdout + reply.stderr
    first = json_loads(reply.stdout)
    cursor = first[cursor_field]
    assert cursor is not None, first.get("reuse")
    assert all(first_observations[name] > 0 for name in miss_counters)

    reply, second_observations = invoke("second", cursor=cursor)
    assert reply.returncode == 0, reply.stdout + reply.stderr
    second = json_loads(reply.stdout)
    assert second_observations["page_hits"] == 1
    assert all(second_observations[name] == 0 for name in miss_counters)
    assert first["cut_id"] == second["cut_id"]
    assert len(first[rows_field]) == len(second[rows_field]) == 1
    assert second[cursor_field] is None

    def entity_id(row):
        if variant == "rich":
            return row["entity"]["entity_id"]
        if variant == "demand":
            return row["member_id"]
        assert row["population"] == "contribution"
        return row["row"]["reference"]["member_id"]

    assert [entity_id(first[rows_field][0]), entity_id(second[rows_field][0])] == [
        "authored:one",
        "authored:two",
    ]
    assert len(json_bytes(first)) <= 1048576 and len(json_bytes(second)) <= 1048576

    reply, uncached_observations = invoke("uncached", cursor=cursor, cached=False)
    assert reply.returncode == 0, reply.stdout + reply.stderr
    uncached = json_loads(reply.stdout)
    assert second[rows_field] == uncached[rows_field]
    assert second["cut_id"] == uncached["cut_id"]
    for field in ("unknowns", "examination", "scope", "populations"):
        if field in second:
            assert second[field] == uncached[field]
    assert all(uncached_observations[name] > 0 for name in miss_counters)

    refused, refused_observations = invoke("wrong-project", cursor=cursor, project="foreign")
    assert refused.returncode != 0
    assert refused_observations["page_lookups"] == 0

    assert refused_observations[projection_counter] == 0

    with authored_publication.kernel.purpose("write").begin() as connection:
        DataOperationStorage(connection).revoke_data_support(
            cast(
                WireRevokeDataSupportRequest,
                {
                    "project_id": PROJECT,
                    "original_source": None,
                    "selector_kind": "product",
                    "selector": selected.product["id"],
                    "reason": "qualify continuation refusal after actual support withdrawal",
                },
            )
        )
    revoked, revoked_observations = invoke("revoked", cursor=cursor)
    assert revoked.returncode != 0
    assert revoked_observations["page_lookups"] == 0
    assert revoked_observations[projection_counter] == 0
