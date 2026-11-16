"""Native captured-recognition attribution over actual current claimed publications.

Current selected-record/rich admission suites own completed report and selected-context
custody. No old run/BoundReader/private-record transport is retained here.
"""

import json
from copy import deepcopy

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from semantic.current_pdf_integration_support import current_integration_journey


def captured_address(case):
    draft = case.drafts["integrated"]
    inputs = draft.companions["input"]
    outputs = {row["occurrence_id"]: row for row in draft.companions["occurrence"]}
    observations = {
        (ref.task_id, ref.product_key, ref.content_digest): product.values()
        for ref, product in case.observations
    }
    for relation in draft.companions["relation"]:
        if relation["kind"] != "decision" or relation["outcome"] not in {
            "selected",
            "added",
            "replaced",
            "retained_alternative",
        }:
            continue
        output = next((row for row in relation["endpoints"] if row["role"] == "output"), None)
        if output is None:
            continue
        selected = outputs[output["occurrence_id"]]
        for endpoint in relation["endpoints"]:
            if (
                endpoint["role"] not in {"input", "evidence", "alternative"}
                or "input_index" not in endpoint
            ):
                continue
            pin = inputs[endpoint["input_index"]]
            identity = (pin["task_id"], pin["product_key"], pin["content_digest"])
            observed = observations.get(identity)
            if observed is None:
                continue
            provider = next(
                row
                for row in observed["occurrences"]
                if row["occurrence_id"] == endpoint["occurrence_id"]
            )
            if "text" not in provider:
                continue
            return selected["pointer"], dict(
                selected_occurrence_id=selected["occurrence_id"],
                task_id=pin["task_id"],
                product_key=pin["product_key"],
                content_digest=pin["content_digest"],
                occurrence_id=provider["occurrence_id"],
                relation_id=relation["relation_id"],
                endpoint_role=endpoint["role"],
                relation_kind=relation["kind"],
                relation_outcome=relation["outcome"],
                provider_occurrence_json=json.dumps(provider),
                observation_json=json.dumps(observed["observation"]),
            )
    raise AssertionError("controlled rich integration must expose actual provider decision lineage")


def captured_text(connection, selected, pointer, address):
    return connection.scalar(
        text(
            "SELECT ops.record_captured_recognition_text(:task,:key,:digest,:pointer,CAST(:address AS jsonb))"
        ),
        {
            "task": selected.task_id,
            "key": selected.product_key,
            "digest": selected.content_digest,
            "pointer": pointer,
            "address": json.dumps(address),
        },
    )


def test_current_native_captured_text_keeps_actual_provider_precision_and_helper_acl(
    scenario_seeds, tmp_path, monkeypatch, native_settings
):
    with current_integration_journey(
        scenario_seeds, tmp_path, monkeypatch, native_settings
    ) as case:
        pointer, address = captured_address(case)
        provider = json.loads(address["provider_occurrence_json"])
        assert provider["precision"] == "coarse"
        assert "start" not in provider and "end" not in provider
        assert provider["text"] in {
            "equal",
            r"\begin{tabular}{cc}$x+1$ & 2\end{tabular}",
            '<chart type="line">\n| Time | Speed (m/s) |\n|---|---|\n|1|2|',
            "Value $y+2$ follows",
        }
        with case.reader().connect() as connection:
            assert (
                captured_text(connection, case.publications["integrated"], pointer, address)
                == provider["text"]
            )
            assert connection.scalar(
                text(
                    "SELECT has_function_privilege(current_user,'ops.record_captured_recognition_text(bigint,text,text,text,jsonb)','EXECUTE')"
                )
            )
            assert not connection.scalar(
                text(
                    "SELECT EXISTS(SELECT FROM pg_proc p CROSS JOIN LATERAL aclexplode(p.proacl) a "
                    "WHERE p.oid='ops.record_captured_recognition_text(bigint,text,text,text,jsonb)'::regprocedure AND a.grantee=0)"
                )
            )


def test_current_native_captured_lineage_and_precision_forgery_refuse(
    scenario_seeds, tmp_path, monkeypatch, native_settings
):
    with current_integration_journey(
        scenario_seeds, tmp_path, monkeypatch, native_settings
    ) as case:
        pointer, address = captured_address(case)
        with case.reader().connect() as connection:
            for change in ("occurrence", "product", "selected", "relation", "precision", "image"):
                forged = deepcopy(address)
                if change == "occurrence":
                    forged["occurrence_id"] = "not-the-selected-provider-occurrence"
                elif change == "product":
                    forged["content_digest"] = "d" * 64
                elif change == "selected":
                    forged["selected_occurrence_id"] = "not-a-selected-occurrence"
                elif change == "relation":
                    forged["relation_kind"] = "correspondence"
                elif change == "precision":
                    provider = json.loads(forged["provider_occurrence_json"])
                    provider.update(precision="exact", start=0, end=5)
                    forged["provider_occurrence_json"] = json.dumps(provider)
                else:
                    observed = json.loads(forged["observation_json"])
                    observed["image"]["precision"] = "exact"
                    forged["observation_json"] = json.dumps(observed)
                with pytest.raises(DBAPIError) as error, connection.begin_nested():
                    captured_text(connection, case.publications["integrated"], pointer, forged)
                assert isinstance(error.value.orig, psycopg.Error)
                assert error.value.orig.sqlstate == "23514"
