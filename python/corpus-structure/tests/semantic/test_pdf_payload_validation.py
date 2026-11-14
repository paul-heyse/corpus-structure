"""Actual frozen payloads must satisfy semantics beyond IPC shape/checksums."""

import json
from copy import deepcopy

import pytest
from pdf_acceptance_support import inventory

from corpus_structure.semantic.pdf_payload_validation import FrozenPayloadStore
from corpus_structure.semantic.pdf_record_identity import byte_root
from semantic.pdf_payload_validation_support import captured as captured

from . import pdf_integration_support as integrated_examples

native_source = integrated_examples.native_source
independent_integrated = integrated_examples.independent_integrated


@pytest.mark.parametrize(
    "change",
    [
        None,
        "segmented",
        "empty_companions",
        "missing_coverage",
        "missing_decision",
        "wrong_kind",
        "exact_glyph",
        "out_of_bounds_region",
        "wrong_region_page",
        "missing_region_page",
        "forged_text",
        "missing_local_endpoint",
        "duplicate_occurrence",
        "duplicate_endpoint",
        "segmented_duplicate_endpoint",
        "missing_structural",
        "missing_recognition",
    ],
)
def test_frozen_selected_companions_retain_complete_meaning(
    tmp_path,
    independent_integrated,
    change,
):
    value = independent_integrated
    segmented = change in {"segmented", "segmented_duplicate_endpoint"}
    defect = None if change == "segmented" else change
    if defect is not None:
        integrated_examples.mutate_selected(value, defect.removeprefix("segmented_"))
    store = FrozenPayloadStore(tmp_path / "meaning.sqlite")
    try:
        for family, key in (
            ("input", "inputs"),
            ("occurrence", "occurrences"),
            ("relation", "relations"),
            ("coverage", "coverage"),
            ("mapping_report", "mapping_reports"),
        ):
            for ordinal, body in enumerate(value.get(key, ())):
                body = deepcopy(body)
                if segmented and family == "relation" and ordinal == 0:
                    for name, kind, profile, payload in (
                        (
                            "endpoints",
                            "y",
                            "pdf-companion-json-field-v1",
                            json.dumps(body.pop("endpoints")).encode(),
                        ),
                        (
                            "evidence",
                            "s",
                            "pdf-record-scalar-v1:s",
                            body.pop("evidence").encode(),
                        ),
                    ):
                        length, root = byte_root((payload,))
                        store.add(
                            "companion_field",
                            dict(
                                family=family,
                                local_id="0",
                                field_name=name,
                                stream_id=name,
                                scalar_kind=kind,
                            ),
                        )
                        store.add(
                            "artifact_stream",
                            dict(
                                stream_id=name,
                                byte_length=length,
                                byte_root=root.hex(),
                                encoding_profile=profile,
                            ),
                        )
                        store.add(
                            "artifact_part", dict(stream_id=name, ordinal=0, body=payload.hex())
                        )
                store.add(
                    "companion",
                    dict(family=family, local_id=str(ordinal), ordinal=ordinal, body=body),
                )
        if defect is None:
            store.validate_integrated_meaning(value["content"]["document"])
        else:
            with pytest.raises(ValueError):
                store.validate_integrated_meaning(value["content"]["document"])
    finally:
        store.close()


@pytest.mark.parametrize(
    "state,outcome,accepted",
    [
        ("omitted", "partial", True),
        ("empty", "partial", True),
        ("null", "partial", False),
        ("omitted", "complete", False),
    ],
)
def test_raw_frozen_coverage_distinguishes_absent_empty_and_null_supports(
    tmp_path,
    independent_integrated,
    state,
    outcome,
    accepted,
):
    value = independent_integrated
    coverage = value["coverage"][0]
    coverage["outcome"] = outcome
    if state == "omitted":
        coverage.pop("supports")
    else:
        coverage["supports"] = [] if state == "empty" else None
    original = deepcopy(coverage)
    store = FrozenPayloadStore(tmp_path / "optional-supports.sqlite")
    try:
        for family, key in (
            ("input", "inputs"),
            ("occurrence", "occurrences"),
            ("relation", "relations"),
            ("coverage", "coverage"),
        ):
            for ordinal, body in enumerate(value[key]):
                store.add("companion", dict(family=family, local_id=str(ordinal), body=body))
        if accepted:
            store.validate_integrated_meaning(value["content"]["document"])
        else:
            with pytest.raises(
                ValueError,
                match=(
                    "must be an array"
                    if state == "null"
                    else "complete coverage requires qualified input"
                ),
            ):
                store.validate_integrated_meaning(value["content"]["document"])
        assert next(store.companions("coverage"))["body"] == original
        assert coverage == original
    finally:
        store.close()


def test_frozen_occurrence_text_uses_lossless_checked_byte_field(tmp_path):
    store = FrozenPayloadStore(tmp_path / "text.sqlite")
    spelling = "equal\x00Ω"
    payload = spelling.encode()
    length, root = byte_root((payload,))
    row = dict(family="occurrence", local_id="o", body={"occurrence_id": "o"})
    try:
        store.add(
            "companion_field",
            dict(
                family="occurrence",
                local_id="o",
                field_name="text",
                stream_id="text",
                scalar_kind="s",
            ),
        )
        store.add(
            "artifact_stream",
            dict(
                stream_id="text",
                byte_length=length,
                byte_root=root.hex(),
                encoding_profile="pdf-record-scalar-v1:s",
            ),
        )
        store.add("artifact_part", dict(stream_id="text", ordinal=0, body=payload.hex()))
        assert store.companion_value(row)["text"] == spelling
        store.db.execute("UPDATE part SET body=? WHERE stream='text'", (b"changed",))
        with pytest.raises(ValueError):
            store.companion_value(row)
    finally:
        store.close()


def test_valid_frozen_page_checks_actual_bytes_and_semantics(tmp_path):
    page = inventory()
    store, row, document, projection = captured(tmp_path, page)
    try:
        assert store.value(row) == page
        store.validate(document, projection)
    finally:
        store.close()


@pytest.mark.parametrize(
    "defect,diagnostic",
    [
        ("offset", "recognized line range"),
        ("geometry", "raster-to-PDF"),
        ("endpoint", "estimated-word address"),
        ("page", "outside native scope"),
    ],
)
def test_structurally_legal_persisted_payload_cannot_bypass_domain_rules(
    tmp_path, defect, diagnostic
):
    page = deepcopy(inventory())
    if defect == "offset":
        page["ocr_regions"][0]["lines"][0]["words"][0]["end"] = 2
    elif defect == "geometry":
        page["ocr_regions"][0]["lines"][0]["words"][0]["left"] += 1
    elif defect == "endpoint":
        page["candidates"][0]["ocr_word_index"] = 99
    else:
        page["page_no"] = 2
    store, _, document, projection = captured(tmp_path, page)
    try:
        with pytest.raises(ValueError, match=diagnostic):
            store.validate(document, projection)
    finally:
        store.close()


def test_forged_logical_claim_fails_against_captured_ipc(tmp_path):
    store, row, _, _ = captured(tmp_path, inventory())
    row["body"]["payload_logical_digest"] = "0" * 64
    try:
        with pytest.raises(ValueError, match="logical digest"):
            store.value(row)
    finally:
        store.close()


def test_runtime_report_is_not_omitted_from_frozen_semantics(tmp_path):
    store, _, document, projection = captured(tmp_path, inventory())
    value = dict(effective_options="[]")
    # Isolate the shared cross-field rule: the primitive field is a legal JSON string.
    store.schemas["runtime_report"] = {"type": "object"}
    payload = json.dumps(value).encode()
    length, root = byte_root((payload,))
    store.add(
        "companion",
        dict(
            family="native_metadata",
            local_id="runtime:0",
            ordinal=1,
            body=dict(kind="runtime_report", ordinal=0),
        ),
    )
    store.add(
        "companion_field",
        dict(
            family="native_metadata", local_id="runtime:0", field_name="value", stream_id="runtime"
        ),
    )
    store.add(
        "artifact_stream",
        dict(
            stream_id="runtime",
            byte_length=length,
            byte_root=root.hex(),
            encoding_profile="pdf-companion-json-field-v1",
        ),
    )
    store.add("artifact_part", dict(stream_id="runtime", ordinal=0, body=payload.hex()))
    try:
        with pytest.raises(ValueError, match="upstream option object"):
            store.validate(document, projection)
    finally:
        store.close()


def test_false_complete_coverage_fails_over_captured_page_inventory(tmp_path):
    page = inventory()
    page["ocr_regions"][0]["outcome"] = "partial"
    store, _, document, projection = captured(tmp_path, page)
    document["groups"] = [dict(self_ref="#/groups/0", label="section")]
    document["texts"] = [dict(self_ref="#/texts/0", label="text", text="x", children=[])]
    health = dict(
        source_scope="whole_document",
        inline_coverage="complete",
        inline_scope=["#/groups/0"],
        inline_membership="direct",
        candidate_policy="native-font-token-vector-ocr-word-v3",
    )
    store.db.execute(
        "UPDATE entry SET body=? WHERE family='companion' AND key=?",
        (
            json.dumps(dict(family="health", local_id="health", body=health)),
            json.dumps(["health", "health"]),
        ),
    )
    projection.write_text(
        "\n".join(
            json.dumps(dict(family=family, body=body))
            for family, body in [
                (
                    "access",
                    dict(pointer="#/groups/0", label="section", section_pointer="#/groups/0"),
                ),
                (
                    "access",
                    dict(
                        pointer="#/texts/0",
                        label="text",
                        parent_pointer="#/groups/0",
                        section_pointer="#/groups/0",
                    ),
                ),
                ("region", dict(pointer="#/texts/0", page_no=1)),
            ]
        )
    )
    try:
        with pytest.raises(ValueError, match="complete word inventory"):
            store.validate(document, projection)
    finally:
        store.close()


def test_family_kind_page_and_exists_selectors_do_not_decode_unrelated_rows(tmp_path):
    store, row, _, _ = captured(tmp_path, inventory())
    try:
        for family, local, body in (
            ("occurrence", "unrelated", {}),
            ("native_metadata", "runtime:9", {"kind": "runtime_report"}),
            ("native_metadata", "page:2", {"kind": "inline_candidate_pages", "page_no": 2}),
        ):
            store.add("companion", dict(family=family, local_id=local, body=body))
            # A selector for the real page must not even parse these payloads.
            store.db.execute(
                "UPDATE entry SET body='not JSON' WHERE family='companion' AND key=?",
                (json.dumps([family, local]),),
            )
        assert list(
            store.companions("native_metadata", kind="inline_candidate_pages", page_nos=[1])
        ) == [row]
        assert list(store.companions("native_metadata", page_nos=[])) == []
        assert store.has_companions("native_metadata", kind="runtime_report")
        assert not store.has_companions("coverage")
        where, parameters = store._selection("native_metadata", "inline_candidate_pages", [1])
        plan = store.db.execute(
            "EXPLAIN QUERY PLAN SELECT body FROM entry WHERE " + where, parameters
        ).fetchall()
        assert any("SEARCH entry USING INDEX" in detail for *_, detail in plan)
    finally:
        store.close()


def test_stream_verifies_and_consumes_actual_parts_once_with_canonical_blocking(
    tmp_path, monkeypatch
):
    store = FrozenPayloadStore(tmp_path / "parts.sqlite")
    payload = bytes(range(256)) * 800
    chunks = [payload[:13], payload[13:70001], payload[70001:]]
    length, root = byte_root((payload,))
    store.add(
        "artifact_stream", dict(stream_id="fragmented", byte_length=length, byte_root=root.hex())
    )
    for ordinal, chunk in enumerate(chunks):
        store.add("artifact_part", dict(stream_id="fragmented", ordinal=ordinal, body=chunk.hex()))
    original = store.parts
    calls = []

    def parts(stream):
        calls.append(stream)
        yield from original(stream)

    monkeypatch.setattr(store, "parts", parts)
    try:
        descriptor, actual = store.stream("fragmented")
        assert actual == payload and descriptor["byte_root"] == root.hex()
        assert calls == ["fragmented"]
    finally:
        store.close()


def add_report(store, index):
    value = dict(
        page_no=1,
        candidate_index=index,
        item_pointers=["#/texts/0"],
        outcome="unresolved",
        basis="unmatched-native-text",
        detail="Independent unresolved word",
    )
    payload = json.dumps(value).encode()
    length, root = byte_root((payload,))
    local = f"inline:{index}"
    store.add(
        "companion",
        dict(
            family="native_metadata",
            local_id=local,
            ordinal=index,
            body=dict(kind="inline_alignment_reports", ordinal=index),
        ),
    )
    store.add(
        "companion_field",
        dict(family="native_metadata", local_id=local, field_name="value", stream_id=local),
    )
    store.add(
        "artifact_stream",
        dict(
            stream_id=local,
            byte_length=length,
            byte_root=root.hex(),
            encoding_profile="pdf-companion-json-field-v1",
        ),
    )
    store.add("artifact_part", dict(stream_id=local, ordinal=0, body=payload.hex()))


def test_frozen_page_decodes_once_across_multiple_original_candidate_reports(tmp_path, monkeypatch):
    from corpus_structure.semantic.pdf_payloads import PreparedPayloadFamily

    page = inventory()
    page["candidates"].append(deepcopy(page["candidates"][0]))
    store, _, document, projection = captured(tmp_path, page)
    for index in (0, 1):
        add_report(store, index)
    store.add(
        "companion",
        dict(
            family="input",
            local_id="0",
            body=dict(role="structural", task_id=12, product_key="native", content_digest="a" * 64),
        ),
    )
    projection.write_text(
        "\n".join(
            json.dumps(dict(family=family, body=body))
            for family, body in (
                ("access", dict(pointer="#/texts/0", label="text", content_layer="body")),
                (
                    "region",
                    dict(
                        pointer="#/texts/0",
                        page_no=1,
                        left=26,
                        top=40,
                        right=66,
                        bottom=60,
                        origin="top_left",
                    ),
                ),
            )
        )
    )
    original = PreparedPayloadFamily.decode
    calls = []

    def decode(self, *args, **kwargs):
        calls.append(kwargs["logical_digest"])
        return original(self, *args, **kwargs)

    monkeypatch.setattr(PreparedPayloadFamily, "decode", decode)
    try:
        store.validate(document, projection)
        assert len(calls) == 1
    finally:
        store.close()


@pytest.mark.parametrize("defect", ["schema", "logical", "locator", "bytes", "encoding"])
def test_a_previous_success_never_authorizes_changed_frozen_payload(tmp_path, defect):
    store, row, document, projection = captured(tmp_path, inventory())
    try:
        store.validate(document, projection)
        if defect == "bytes":
            store.db.execute("UPDATE part SET body=? WHERE stream='page'", (b"changed",))
        elif defect == "encoding":
            (raw,) = store.db.execute(
                "SELECT body FROM entry WHERE family='artifact_stream' AND key='page'"
            ).fetchone()
            descriptor = json.loads(raw)
            descriptor["encoding_profile"] = "pdf-companion-json-field-v1"
            store.db.execute(
                "UPDATE entry SET body=? WHERE family='artifact_stream' AND key='page'",
                (json.dumps(descriptor),),
            )
        else:
            field = {
                "schema": "payload_schema_digest",
                "logical": "payload_logical_digest",
                "locator": "page_no",
            }[defect]
            row["body"][field] = 2 if defect == "locator" else "0" * 64
            store.db.execute(
                "UPDATE entry SET body=? WHERE family='companion' AND key=?",
                (json.dumps(row), json.dumps(["native_metadata", "page:0"])),
            )
        with pytest.raises(ValueError):
            store.validate(document, projection)
    finally:
        store.close()


def test_captured_publication_policy_and_actual_metadata_kind_inventory_are_used(
    tmp_path, monkeypatch
):
    from corpus_structure.semantic import pdf_contracts
    from corpus_structure.semantic.pdf_payloads import schema_dump

    store, _, document, projection = captured(tmp_path, inventory())
    policy = pdf_contracts.integrated_metadata_policy()
    store.add(
        "validation_contract",
        json.loads(
            schema_dump(
                dict(
                    schemas=store.schemas,
                    publication_kind="integrated",
                    integrated_metadata_policy=policy,
                )
            )
        ),
    )

    def no_installed_policy():
        raise AssertionError("the exact captured publication policy must be reused")

    monkeypatch.setattr(pdf_contracts, "integrated_metadata_policy", no_installed_policy)
    # This policy-only example has no content items; it still declares its selected
    # input roles and partial coverage instead of bypassing integrated meaning.
    for ordinal, role in enumerate(("structural", "recognition")):
        store.add(
            "companion",
            dict(
                family="input",
                local_id=str(ordinal),
                body=dict(
                    role=role, task_id=41, product_key=f"source-{ordinal}", content_digest="a" * 64
                ),
            ),
        )
    store.add(
        "companion",
        dict(
            family="coverage",
            local_id="scope",
            body=dict(
                coverage_id="scope",
                scope="page:1",
                family="table",
                discovery_policy="fixture",
                detail="unassessed mapping",
                outcome="partial",
                supports=[],
            ),
        ),
    )
    for ordinal, family in enumerate(("body", "furniture")):
        pointer = f"#/{family}"
        document[family] = dict(self_ref=pointer, children=[])
        store.add(
            "companion",
            dict(
                family="occurrence",
                local_id=pointer,
                body=dict(
                    occurrence_id=pointer,
                    kind="item",
                    address_space="selected_item",
                    precision="item",
                    pointer=pointer,
                ),
            ),
        )
        store.add(
            "companion",
            dict(
                family="relation",
                local_id=f"decision-{ordinal}",
                body=dict(
                    relation_id=f"decision-{ordinal}",
                    kind="decision",
                    outcome="selected",
                    policy="fixture",
                    evidence="empty container retained",
                    endpoints=[
                        dict(role="input", input_index=0, occurrence_id=pointer),
                        dict(role="output", occurrence_id=pointer),
                    ],
                ),
            ),
        )
    try:
        store.validate(document, projection)
        payload = b'{"effective_options":"{}"}'
        length, root = byte_root((payload,))
        store.add(
            "companion",
            dict(
                family="native_metadata",
                local_id="runtime:0",
                body=dict(kind="runtime_report", ordinal=0),
            ),
        )
        store.add(
            "companion_field",
            dict(
                family="native_metadata",
                local_id="runtime:0",
                field_name="value",
                stream_id="runtime",
            ),
        )
        store.add(
            "artifact_stream",
            dict(
                stream_id="runtime",
                byte_length=length,
                byte_root=root.hex(),
                encoding_profile="pdf-companion-json-field-v1",
            ),
        )
        store.add("artifact_part", dict(stream_id="runtime", ordinal=0, body=payload.hex()))
        with pytest.raises(ValueError, match="qualified input graph"):
            store.validate(document, projection)
    finally:
        store.close()
