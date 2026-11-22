"""Current request-byte controls and real definition CPU/native publication custody.

Controlled request/raw values test the library contract without provider authority.
The native source/named-component case retains actual execution and selected support;
no old run snapshots or installed located-model RPCs supply a counterpart.
"""

import json
import struct
import sys
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.methods.gliner import GlinerInput
from corpus_structure.methods.model_observation import batch_receipt, report_observation_digest


def _literal_hash(value):
    # Independent native reference bytes, deliberately not the producer's hash helper.
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def _literal_current_observation():
    profile = {
        "snapshot": "/acquired",
        "checkpoint": "checkpoint",
        "timeout_seconds": 120.0,
        "artifact_hashes": [["z", "last"], ["a", "first"]],
        "device": "cuda",
        "dtype": "float32",
        "execution_profile": "exact-numerical-identity",
    }
    policy = {
        "request_version": "located-model-request-2",
        "definition": {"bare": ['{"entities":[', {"field": "term_entity"}, "]}"]},
        "inference": {"operation": "batch_extract", "include_spans": True},
    }
    config = dict(profile=profile, description_arm="bare", term_entity="term", threshold=0.5)
    header = {
        "release": "r",
        "version": "native-local-v1",
        "declaration": '{"entities":["term"]}',
        "profile": {
            "checkpoint": "checkpoint",
            "timeout_seconds": "120",
            "artifact_hashes": [["a", "first"], ["z", "last"]],
            "device": "cuda",
            "dtype": "float32",
            "execution_profile": "exact-numerical-identity",
        },
        "threshold": "0.5",
        "overlap": "flat",
        "evaluation": False,
        "inference": {"operation": "batch_extract", "include_spans": True},
    }
    member = _literal_hash(
        [
            "located-model-member-2",
            "text.gliner_definitions/source-native",
            "context",
            "b" * 64,
            " \u03b1\t\u03b2",
        ]
    )
    key = _literal_hash(["located-model-request-2", header, [member]])
    receipt = dict(version=2, header=header, members=[member], digest=key)
    report = dict(
        request_digest=key,
        computation=key,
        raw_json='{"entities":{}}',
        effective_profile_json='{"device":"cuda","dtype":"float32"}',
        batch_receipt_json=json.dumps(receipt),
        member_ordinal=0,
    )
    report["observation_digest"] = _literal_hash(
        [
            "located-model-observation-2",
            key,
            0,
            member,
            report["raw_json"],
            report["effective_profile_json"],
        ]
    )
    return policy, config, receipt, report


def test_current_definition_request_binds_independent_header_member_and_ordered_schema_bytes():
    policy, config, expected, report = _literal_current_observation()
    pack = SimpleNamespace(
        release="r", version="native-local-v1", declaration_json=expected["header"]["declaration"]
    )
    member = GlinerInput(
        "context", "b" * 64, " \u03b1\t\u03b2", "text.gliner_definitions/source-native"
    )
    arguments = (pack, config["profile"], (member,), 0.5, "flat", False, policy["inference"])
    assert batch_receipt(*arguments) == expected
    assert report_observation_digest(report) == report["observation_digest"]
    ordered = replace(member, context_id="second-context")
    first = batch_receipt(pack, config["profile"], (member, ordered), *arguments[3:])
    second = batch_receipt(pack, config["profile"], (ordered, member), *arguments[3:])
    assert first["members"] == list(reversed(second["members"]))
    assert first["digest"] != second["digest"]
    # Arrays and exact submitted text are ordered meaning, not canonicalized sets.
    schema_digests = []
    for declaration in ('{"entities":["term","content"]}', '{"entities":["content","term"]}'):
        selected = SimpleNamespace(**{**vars(pack), "declaration_json": declaration})
        schema_digests.append(batch_receipt(selected, *arguments[1:])["digest"])
    assert len(set(schema_digests)) == 2
    assert expected["digest"] not in schema_digests
    changed_profile = {**config["profile"], "execution_profile": "other-numerical-policy"}
    assert batch_receipt(pack, changed_profile, *arguments[2:])["digest"] != expected["digest"]
    assert (
        batch_receipt(*arguments[:-1], {"operation": "batch_extract", "include_spans": False})[
            "digest"
        ]
        != expected["digest"]
    )


@pytest.mark.parametrize(
    "change",
    ["missing-receipt", "ordinal", "member", "duplicate", "receipt-shape", "raw", "profile"],
)
def test_current_definition_observation_keeps_exact_original_batch_commitment(change):
    _, _, receipt, report = _literal_current_observation()
    changed = deepcopy(report)
    if change == "missing-receipt":
        changed.pop("batch_receipt_json")
    elif change == "ordinal":
        changed["member_ordinal"] = 1
    elif change in {"member", "duplicate", "receipt-shape"}:
        value = deepcopy(receipt)
        if change == "member":
            value["members"] = ["f" * 64]
        elif change == "duplicate":
            value["members"] *= 2
        else:
            value["extra"] = True
        changed["batch_receipt_json"] = json.dumps(value)
    else:
        changed["raw_json" if change == "raw" else "effective_profile_json"] = "{}"
        assert report_observation_digest(changed) != report["observation_digest"]
        return
    with pytest.raises(ValueError):
        report_observation_digest(changed)


@pytest.mark.parametrize("ordinal", [-1, 1, True, 0.0, "0", None, 2**63])
def test_current_observation_refuses_wrong_or_untyped_member_position(ordinal):
    _, _, _, report = _literal_current_observation()
    with pytest.raises(ValueError):
        report_observation_digest({**report, "member_ordinal": ordinal})


def test_current_named_definition_preserves_source_cue_and_refuses_changed_cpu_body_atomically(
    semantic_bare_engine, native_settings, tmp_path, monkeypatch
):
    from corpus_structure.semantic.data_operation_storage import DataOperationStorage
    from corpus_structure.semantic.data_operation_values import (
        decode_semantic_value,
        semantic_value,
    )
    from corpus_structure.semantic.structural_products import read_definition_components_report
    from semantic.current_pdf_source_support import admit_current_target
    from semantic.structural_production_native_support import (
        NAMED,
        produce_source_reports,
        recipe,
        selected_for_source,
    )
    from semantic.test_sentence_partition_chain_native import _private_source

    literal = "We define variance as spread."
    with _private_source(
        semantic_bare_engine, native_settings, tmp_path, monkeypatch, literal
    ) as source:
        kernel = admit_current_target(source, recipe(tmp_path / "recipe"), tmp_path / "consumer")
        retain = DataOperationStorage.retain_data_completion_intent
        attempted = []
        counts = text(
            "SELECT (SELECT count(*) FROM ops.data_completion_intent),(SELECT count(*) FROM kb.data_product),(SELECT count(*) FROM ops.data_derivation),(SELECT count(*) FROM ops.data_publication_receipt)"
        )

        def intercept(storage, payload):
            with kernel.engine.connect() as connection:
                operation = connection.scalar(
                    text("SELECT operation_id FROM ops.data_request WHERE id=:id"),
                    {"id": payload["request_id"]},
                )
            if operation == NAMED and not attempted:
                changed = deepcopy(payload)
                body = decode_semantic_value(changed["completion"]["outputs"][0]["product"]["body"])
                body["inputs"]["question"] += " altered after the original CPU reply"
                read_definition_components_report(body)
                changed["completion"]["outputs"][0]["product"]["body"] = semantic_value(body)
                assert (
                    changed["completion"]["execution_evidence"]
                    == payload["completion"]["execution_evidence"]
                )
                with kernel.engine.connect() as connection:
                    before = connection.execute(counts).one()
                with (
                    pytest.raises(DBAPIError, match="definition publication differs"),
                    storage.connection.begin_nested(),
                ):
                    retain(storage, changed)
                with kernel.engine.connect() as connection:
                    assert connection.execute(counts).one() == before
                attempted.append(payload["request_id"])
            return retain(storage, payload)

        monkeypatch.setattr(DataOperationStorage, "retain_data_completion_intent", intercept)
        _, original, products, _ = produce_source_reports(source, kernel, NAMED, text=literal)
        assert attempted
        (report,) = selected_for_source(
            kernel,
            products,
            "urn:corpus:structural:DeclaredNamedDefinitionComponentsReport",
            original,
        )
        assert report.body["sources_input"][0]["member_id"] == original.row["member_id"]
        packets = report.body["members"]
        assert packets and "components" not in report.body["definition_components"]
        with kernel.engine.connect() as connection:
            admitted = connection.execute(
                text(
                    "SELECT member_id, kind_contract FROM kb.data_product_member "
                    "WHERE product_id = :product_id"
                ),
                {"product_id": report.row["product_id"]},
            ).all()
        assert set(admitted) == {
            (packet["body"]["component_id"], packet["kind_contract"]) for packet in packets
        }
        components = [packet["body"] for packet in packets]
        (matched,) = [
            component
            for component in components
            if component["term"]["text"] == "variance"
            and component["content"]["text"].startswith("spread")
        ]
        assert matched["basis"] == "matched_cue"
        (_annotations,) = selected_for_source(
            kernel,
            products,
            "https://corpus-structure.dev/semantic/data-operation-sentences/DdoSourceAnnotations",
            original,
        )
        (_constructions,) = selected_for_source(
            kernel,
            products,
            "https://corpus-structure.dev/semantic/data-operation-constructions/DdoPrimaryConstructionProduct",
            original,
        )
        (recorded,) = [
            row
            for row in report.body["witnesses"]
            if row["component_id"] == matched["component_id"]
        ]
        witness = recorded["basis"]
        assert witness["annotation_product"] == {"variant": "product", "role": "annotations"}
        assert witness["primary_match"]["role"] == "constructions"
        assert witness["primary_match"]["variant"] == "member"


def test_native_model_report_preserves_exact_binary_profile_and_scores(commit_db_engine):
    values = (
        120.0,
        0.1,
        -0.0,
        float.fromhex("0x0.0000000000001p-1022"),
        float.fromhex("0x0.fffffffffffffp-1022"),
        sys.float_info.min,
        sys.float_info.max,
    )
    with commit_db_engine.connect() as conn, conn.begin():
        for value in values:
            actual = conn.scalar(
                text("SELECT float8send(data.record_source_float(CAST(:value AS jsonb)))"),
                {"value": json.dumps({"kind": "float", "hexadecimal": value.hex()})},
            )
            assert actual == struct.pack("!d", value)
