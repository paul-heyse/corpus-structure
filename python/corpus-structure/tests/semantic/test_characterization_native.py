"""Real current primary products/cuts and independent scientific counterexamples."""

import os
from copy import deepcopy
from hashlib import sha256
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from corpus_structure.semantic.characterization import (
    validate_inventory_topology,
    verify_interpreted_attachment_witnesses,
)
from corpus_structure.semantic.characterization_evidence import (
    validate_formal_normalization,
    validate_formal_positions,
)
from corpus_structure.semantic.construction_products import (
    ConstructionOptions,
    PreparedConstructionProfile,
    validate_construction_product,
)
from corpus_structure.semantic.data_operation_json import json_bytes
from corpus_structure.semantic.data_operation_model import SubjectContext
from corpus_structure.semantic.data_operation_values import decode_semantic_value
from corpus_structure.semantic.formal_evidence import grammar_identity
from corpus_structure.semantic.formal_products import (
    FormalEvidenceOptions,
    prepare_formal_evidence,
    validate_formal_product,
)
from corpus_structure.semantic.native_source_view import thaw_native
from corpus_structure.semantic.source_products import source_subject
from semantic.characterization_evidence_support import EVIDENCE_MUTATIONS
from semantic.characterization_native_support import (
    characterization_source as characterization_source,
)
from semantic.characterization_native_support import (
    current_characterization_recipe as current_characterization_recipe,
)
from semantic.characterization_native_support import (
    operation_product,
    operation_use,
)
from semantic.data_operation_kernel_support import prepare_kernel
from semantic.formal_products_support import selected

FORMAL = "text.formal_evidence/source-native"
CONSTRUCTION = "text.constructions/source-native"
COMPOSITION = "text.compose_view/source-native"
SENTENCES = "segment.sentences/source-native"


@pytest.fixture(scope="module")
def profiles(current_characterization_recipe):
    acquired = prepare_kernel(current_characterization_recipe)
    formal = prepare_formal_evidence(acquired.prepared, acquired.model, grammar=grammar_identity())
    source = selected(formal, "Not every trial succeeds.")
    value = source.value
    context = SubjectContext(
        "scientific-kernel-controls",
        source_subject(value["source"]),
        value["source"]["document"],
        json_bytes(thaw_native({"source": value["source"], "selectors": value["selectors"]})),
        subject_definition="original-source-view",
    )
    primary = formal.run(source, FormalEvidenceOptions(), subject_context=context)
    construction = PreparedConstructionProfile(acquired.prepared, acquired.model)
    product = construction.run(source, (primary,), subject_context=context)
    return acquired, source, context, primary, product


@pytest.fixture(scope="module")
def positioned_formal(profiles):
    acquired = profiles[0]
    formal = prepare_formal_evidence(acquired.prepared, acquired.model, grammar=grammar_identity())
    source = selected(formal)
    value = source.value
    context = SubjectContext(
        "positioned-formal-controls",
        source_subject(value["source"]),
        value["source"]["document"],
        json_bytes(thaw_native({"source": value["source"], "selectors": value["selectors"]})),
        subject_definition="original-source-view",
    )
    return (
        acquired,
        source,
        context,
        formal.run(source, FormalEvidenceOptions(), subject_context=context),
    )


@pytest.mark.parametrize("characterization_source", ["unprojected-formula"], indirect=True)
def test_native_current_publication_replay_keeps_partial_family_and_exact_product(
    characterization_source,
):
    source = characterization_source
    demand, result, snapshot = source.run(CONSTRUCTION)
    # Exact source discovery, formal evidence, sentences and construction each complete.
    assert result.receipt_count == 4
    product = operation_product(snapshot, CONSTRUCTION)
    body = decode_semantic_value(product["body"])
    assert body["source"] == source.source.value["source"]
    assert body["outcome"] == "partial"
    assert any(
        row["availability"] != "available" or row["outcome"] not in {"complete", "empty"}
        for row in body["coverage"]
    )
    original = operation_use(snapshot, CONSTRUCTION)
    replay, reread = source.advance(demand)
    assert replay.receipt_count == 0
    assert operation_product(reread, CONSTRUCTION)["product_id"] == product["product_id"]
    assert operation_use(reread, CONSTRUCTION)["derivation_id"] == original["derivation_id"]
    detail = source.query(
        demand, operation_id=CONSTRUCTION, product_id=product["product_id"], containers_only=True
    )
    assert detail["items"][0]["body"] == body
    assert detail["items"][0]["derivation_id"] == original["derivation_id"]
    assert detail["cut"]["project_id"] == source.factory.project_id


def test_native_current_source_only_then_selected_composition_preserves_actual_dependencies(
    characterization_source,
):
    source = characterization_source
    demand, _, snapshot = source.run(COMPOSITION, profile="source_only")
    weak = decode_semantic_value(operation_product(snapshot, COMPOSITION)["body"])
    assert weak["profile"] == "source_only" and weak["products"] == weak["active"] == []
    assert weak["sources"][0]["source"]["document"] == source.factory.key
    analytical_demand, _, primary = source.run(CONSTRUCTION)
    formal = operation_product(primary, FORMAL)
    construction = operation_product(primary, CONSTRUCTION)
    sentences = operation_product(primary, SENTENCES)
    from corpus_structure.semantic.data_operation_source_sets import SelectedSourceSetEntry
    from corpus_structure.semantic.demand_results import CutSelection

    selections = {}
    for operation in (FORMAL, SENTENCES, CONSTRUCTION):
        product = operation_product(primary, operation)
        (manifest,) = [
            packet
            for packet in decode_semantic_value(product["body"])["members"]
            if packet["body"].get("record_type") == "manifest"
        ]
        selected = source.query(
            analytical_demand,
            operation_id=operation,
            product_id=product["product_id"],
            member_id=manifest["member_id"],
        )
        (header,) = selected["items"]
        assert header["kind_contract"] == manifest["kind_contract"]
        selections[operation] = SelectedSourceSetEntry.from_selected_header(
            header, CutSelection(json_bytes(selected["cut"]))
        )
    # Published analytical products stay outside a request that selects empty sets.
    _, _, unselected = source.run(COMPOSITION, profile="selected_layers")
    empty = decode_semantic_value(operation_product(unselected, COMPOSITION)["body"])
    assert empty["products"] == empty["active"] == []
    _, _, combined = source.run(
        COMPOSITION,
        profile="selected_layers",
        products=tuple(selections.values()),
        active=(selections[CONSTRUCTION],),
    )
    view = decode_semantic_value(operation_product(combined, COMPOSITION)["body"])
    assert {row["product_id"] for row in view["products"]} == {
        formal["product_id"],
        sentences["product_id"],
        construction["product_id"],
    }
    assert {row["product_id"] for row in view["active"]} == {construction["product_id"]}
    assert view["original_document"] == source.factory.key
    assert all(row["outcome"] in {"complete", "empty", "unknown"} for row in view["coverage"])
    # A prior exact cut is immutable when later analytical work becomes available.
    assert (
        source.query(demand, operation_id=COMPOSITION, containers_only=True)["items"][0]["body"]
        == weak
    )


def test_native_current_members_page_without_losing_source_positions(characterization_source):
    source = characterization_source
    demand, _, snapshot = source.run(CONSTRUCTION)
    product = operation_product(snapshot, FORMAL)
    body = decode_semantic_value(product["body"])
    expected = {
        row["member_id"] for row in body["members"] if row["body"]["record_type"] == "occurrence"
    }
    rows, cursor, cut = [], None, None
    for _ in range(200):
        page = source.inspect(
            demand,
            inventory="occurrences",
            operation_id=FORMAL,
            product_id=product["product_id"],
            limit=1,
            cursor=cursor,
        )
        cut = page["cut_id"] if cut is None else cut
        assert page["cut_id"] == cut
        rows.extend(page["items"])
        cursor = page["continuation"]
        if cursor is None:
            break
    else:
        pytest.fail("bounded characterization member pagination did not finish")
    assert {row["member_id"] for row in rows} == expected
    extents = [extent for row in rows for extent in row["body"]["extents"]]
    assert {"#/texts/1", "#/texts/2"} <= {extent["native_pointer"] for extent in extents}
    for extent in extents:
        if extent["native_pointer"] in {"#/texts/1", "#/texts/2"}:
            assert extent["page"] == (3 if extent["native_pointer"] == "#/texts/1" else 4)
            assert source.source.value["text"][extent["start"] : extent["end"]] == extent["text"]
    empty = source.inspect(
        demand, inventory="terms", operation_id=FORMAL, product_id="not-selected"
    )
    assert empty["items"] == [] and empty["knowledge"] == "unknown"


def test_native_current_summary_omits_members_and_preserves_unknown_coverage(
    characterization_source,
):
    source = characterization_source
    demand, _, snapshot = source.run(CONSTRUCTION)
    product = operation_product(snapshot, CONSTRUCTION)
    actual = decode_semantic_value(product["body"])
    page = source.inspect(demand, operation_id=CONSTRUCTION, product_id=product["product_id"])
    (row,) = page["items"]
    assert (
        row["product_id"] == product["product_id"]
        and row["derivation_id"] == operation_use(snapshot, CONSTRUCTION)["derivation_id"]
    )
    assert "body" not in row and "resource_handle" not in page
    assert row["summary"]["outcome"] == actual["outcome"] == "partial"
    assert sum(row["summary"]["member_counts"].values()) == len(actual["members"])
    assert row["summary"]["providers"] is None
    assert [
        (value["family"], value["outcome"], value["availability"])
        for value in row["summary"]["coverage"]
    ] == [
        (value["family"], value["outcome"], value["availability"]) for value in actual["coverage"]
    ]


def test_native_current_cpu_receipts_retain_actual_fence_and_replay(
    characterization_source, commit_db_engine
):
    from corpus_structure.semantic.identity import canonical_bytes

    source = characterization_source
    demand, _, snapshot = source.run(FORMAL)
    use = operation_use(snapshot, FORMAL)
    with commit_db_engine.connect() as connection:
        intent = (
            connection.execute(
                text(
                    "SELECT i.payload,i.producer_task_id,i.producer_attempt,i.producer_holder,i.request_id,i.generation "
                    "FROM ops.data_completion_intent i JOIN ops.data_request r ON r.id=i.request_id "
                    "WHERE r.id=:request"
                ),
                {"request": use["request_id"]},
            )
            .mappings()
            .one()
        )
    evidence = intent["payload"]["execution_evidence"]
    assert (
        evidence["request_id"] == intent["request_id"]
        and evidence["generation"] == intent["generation"]
    )
    assert (
        evidence["task_id"] == intent["producer_task_id"]
        and evidence["attempt"] == intent["producer_attempt"]
    )
    assert evidence["holder"] == intent["producer_holder"]
    (receipt,) = evidence["cpu_receipts"]
    assert receipt["pid"] != os.getpid() and receipt["main_thread"] is True
    # The formal worker returns this canonical product value. Its receipt is
    # retained independently of the optional duplicate physical-reply body.
    published = decode_semantic_value(operation_product(snapshot, FORMAL)["body"])
    assert receipt["result_digest"] == sha256(canonical_bytes(published)).hexdigest()
    assert evidence["provider_receipts"] == evidence["host_receipts"] == []
    replay, repeated = source.advance(demand)
    assert replay.receipt_count == 0
    assert operation_use(repeated, FORMAL)["derivation_id"] == use["derivation_id"]


def test_native_current_complete_selected_envelope_obeys_independent_read_bound(
    characterization_source,
):
    source = characterization_source
    demand, _, snapshot = source.run(FORMAL)
    expected = operation_product(snapshot, FORMAL)
    page = source.query(
        demand,
        operation_id=FORMAL,
        product_id=expected["product_id"],
        containers_only=True,
        max_bytes=64 * 1024**2,
    )
    assert json_bytes(page["items"][0]["body"]) == json_bytes(
        decode_semantic_value(expected["body"])
    )
    with pytest.raises((DBAPIError, ValueError), match="max_bytes"):
        source.query(
            demand,
            operation_id=FORMAL,
            product_id=expected["product_id"],
            containers_only=True,
            max_bytes=1024,
        )
    again = source.query(demand, operation_id=FORMAL, containers_only=True)
    assert again["items"][0]["product_id"] == expected["product_id"]


def test_native_current_reply_bound_refuses_before_atomic_product_publication(
    characterization_source, commit_db_engine
):
    from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutionError

    source = characterization_source
    demand = source.register(FORMAL)
    with pytest.raises(NativeDemandExecutionError):
        source.advance(
            demand,
            policy=CharacterizationExecutionPolicy(
                workers=1, max_submissions=1, max_reply_bytes=256
            ),
        )
    with commit_db_engine.connect() as connection:
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM ops.data_completion_intent i JOIN ops.data_request r ON r.id=i.request_id "
                    "WHERE r.operation_id=:operation"
                ),
                {"operation": FORMAL},
            )
            == 0
        )
    page = source.query(demand, view="operations", operation_id=FORMAL)
    assert all(row["obligation"]["fate"] != "fulfilled" for row in page["items"])


def test_native_current_new_rule_release_reuses_exact_original_formal_product(
    characterization_source, commit_db_engine, tmp_path
):
    from corpus_structure.methods.annotation_rules import AnnotationRule
    from semantic.characterization_native_support import characterization_recipe
    from semantic.data_operation_kernel_support import admit_kernel

    source = characterization_source
    old_demand, _, original = source.run(CONSTRUCTION)
    old_kernel = source.kernel
    old_formal = operation_use(original, FORMAL)
    rule = AnnotationRule(
        rule="retained-copula",
        variant="is",
        mechanism="token",
        pattern=[{"LOWER": "is"}],
        bindings={"cue": {"node": "match"}},
    )
    recipe = characterization_recipe(
        tmp_path / "new-rule", construction_options=ConstructionOptions(annotation_rules=(rule,))
    )
    with commit_db_engine.begin() as connection:
        source.factory.kernel = admit_kernel(connection, recipe)
    assert source.kernel.prepared.release_id != old_kernel.prepared.release_id
    assert source.kernel.identities[FORMAL, "recipe"] == old_kernel.identities[FORMAL, "recipe"]
    assert (
        source.kernel.identities[CONSTRUCTION, "recipe"]
        != old_kernel.identities[CONSTRUCTION, "recipe"]
    )
    _, _, current = source.run(CONSTRUCTION)
    assert operation_use(current, FORMAL)["derivation_id"] == old_formal["derivation_id"]
    assert (
        operation_product(current, FORMAL)["product_id"]
        == operation_product(original, FORMAL)["product_id"]
    )
    retained = source.query(old_demand, operation_id=FORMAL, containers_only=True)
    assert retained["cut"]["release_id"] == old_kernel.prepared.release_id
    assert retained["items"][0]["product_id"] == operation_product(original, FORMAL)["product_id"]


def test_native_current_reads_do_not_reacquire_an_unrelated_execution_owner(
    characterization_source, monkeypatch
):
    from corpus_structure.orchestrate.data_operations import NativeDemandExecutor

    source = characterization_source
    demand, _, snapshot = source.run(CONSTRUCTION)
    expected = operation_product(snapshot, CONSTRUCTION)
    monkeypatch.setattr(
        NativeDemandExecutor,
        "__init__",
        lambda *_args, **_kwargs: pytest.fail("a retained read attempted execution acquisition"),
    )
    actual = source.query(demand, operation_id=CONSTRUCTION, containers_only=True)
    assert actual["items"][0]["product_id"] == expected["product_id"]
    assert actual["items"][0]["body"] == decode_semantic_value(expected["body"])


@pytest.mark.parametrize("characterization_source", ["unprojected-formula"], indirect=True)
def test_native_current_unprojected_formula_keeps_item_anchored_original_syntax(
    characterization_source,
):
    source = characterization_source
    assert source.source.value["text"] == ""
    original = next(item for item in source.source.value["items"] if item.get("label") == "formula")
    assert original["text"] == "" and original["orig"] == "x+1"
    demand, _, snapshot = source.run(FORMAL)
    body = decode_semantic_value(operation_product(snapshot, FORMAL)["body"])
    inputs = [
        packet["body"]["formal_input"]
        for packet in body["members"]
        if packet["body"].get("kind") == "formal.input"
    ]
    assert inputs and all(item["original_text"] == "x+1" for item in inputs)
    by_representation = {item["representation"]: item for item in inputs}
    assert (
        by_representation["source_text"]["text"] == "x+1"
        and by_representation["source_text"]["syntax_outcome"] == "complete"
    )
    assert (
        by_representation["recognized_latex"]["text"] == ""
        and by_representation["recognized_latex"]["syntax_outcome"] == "failed"
    )
    assert (
        next(row for row in body["coverage"] if row["family"] == "formal.math")["outcome"]
        == "partial"
    )
    occurrences = [
        packet["body"]
        for packet in body["members"]
        if packet["body"]["record_type"] == "occurrence"
    ]
    assert any(
        extent["native_pointer"] == original["self_ref"] and "start" not in extent
        for row in occurrences
        for extent in row["extents"]
    )
    replay, repeated = source.advance(demand)
    assert replay.receipt_count == 0
    assert (
        operation_product(repeated, FORMAL)["product_id"]
        == operation_product(snapshot, FORMAL)["product_id"]
    )


@pytest.mark.parametrize(
    "field,bad",
    [
        ("text", "invented"),
        ("native_pointer", "#/foreign"),
        ("page", 999),
        ("projection", "f" * 64),
    ],
)
def test_current_formal_validator_refuses_foreign_original_evidence(positioned_formal, field, bad):
    acquired, source, context, primary = positioned_formal
    body = thaw_native(primary.value)
    occurrence = next(
        row["body"] for row in body["members"] if row["body"]["record_type"] == "occurrence"
    )
    occurrence["extents"][0][field] = bad
    with pytest.raises(ValueError):
        validate_formal_product(
            acquired.prepared, body, source, model=acquired.model, subject_context=context
        )


@pytest.mark.parametrize(
    "mutation", ["nominal", "dependency", "dangling", "unreleased-rule", "choice"]
)
def test_current_construction_validator_refuses_relabelled_or_unreleased_witness(
    profiles, mutation
):
    acquired, source, context, primary, product = profiles
    body = thaw_native(product.value)
    if mutation == "nominal":
        body["members"][0]["kind_contract"] = "another-contract"
    elif mutation == "dependency":
        owner = next(
            row["member_id"] for row in body["members"] if row["body"]["record_type"] == "term"
        )
        body["formal_support"].append(
            dict(
                owner=owner, use="external_premise", position=0,
                target=dict(
                    variant="member", role="formal", occurrence="99",
                    member_id=primary.value["members"][0]["member_id"],
                ),
            )
        )
    elif mutation == "dangling":
        term = next(row["body"] for row in body["members"] if row["body"]["record_type"] == "term")
        term["children"] = [{"role": "body", "target": "missing", "structural": True}]
    elif mutation == "unreleased-rule":
        role = next(row["body"] for row in body["members"] if row["body"]["record_type"] == "role")
        role["basis"]["rule_id"] = "invented-rule"
    else:
        body["members"] = [
            row for row in body["members"] if row["body"]["record_type"] != "choice_member"
        ]
    with pytest.raises(
        ValueError, match="original formal input" if mutation == "dependency" else None
    ):
        validate_construction_product(
            acquired.prepared, acquired.model, body, source, (primary,), subject_context=context
        )


def test_current_composition_missing_dependency_and_source_only_claim_refuse(profiles):
    from corpus_structure.semantic.enriched_document_products import compose_enriched_document

    acquired, source, _, primary, product = profiles
    with pytest.raises(ValueError, match="missing an exact selected dependency"):
        compose_enriched_document(
            acquired.prepared, acquired.model, (source,), (product,), active=(product.reference,)
        )
    with pytest.raises(ValueError, match="source-only"):
        compose_enriched_document(
            acquired.prepared, acquired.model, (source,), (primary,), profile="source_only"
        )
    weak = compose_enriched_document(
        acquired.prepared, acquired.model, (source,), (), profile="full_characterization"
    )
    assert weak.value["outcome"] == "partial"
    coverage = weak.value["coverage"]
    assert coverage and all(row["outcome"] == "unknown" for row in coverage)


def _inventory() -> dict[str, Any]:
    occurrences = [
        dict(
            local_id="o" + str(i),
            extents=[
                dict(
                    projection="p",
                    native_pointer="#/texts/" + str(i),
                    start=i * 4,
                    end=i * 4 + 3,
                    text="x=1",
                    synthetic=False,
                )
            ],
        )
        for i in range(2)
    ]
    return dict(
        occurrences=occurrences,
        annotations=[
            dict(local_id="a" + str(i), kind="native", family="syntax", occurrences=["o" + str(i)])
            for i in range(2)
        ],
        memberships=[],
        roles=[],
        terms=[
            dict(
                local_id="predicate",
                kind="predicate",
                children=[dict(role="participant", target="participant", structural=True)],
            ),
            dict(local_id="participant", kind="participant"),
        ],
        choices=[
            dict(
                local_id="alternatives",
                compatibility="exclusive",
                members=[dict(local_id="reading", root="predicate")],
            )
        ],
    )


def _indexes(data):
    return {
        name: {row["local_id"]: row for row in data[name]}
        for name in ("occurrences", "annotations", "memberships", "roles", "terms", "choices")
    }


@pytest.mark.parametrize("mutation", EVIDENCE_MUTATIONS)
def test_current_formal_evidence_kernel_keeps_independent_counterexamples(mutation):
    from semantic.characterization_evidence_support import evidence_rows, mutate_evidence

    body = _inventory()
    evidence = evidence_rows(body["occurrences"])
    for annotation in evidence["annotations"]:
        if annotation["local_id"] in {"symbol", "formal-token"}:
            annotation["occurrences"] = ["o0"]
    body.update(annotations=evidence["annotations"])
    expected_indexes = _indexes(body)
    validate_formal_positions(expected_indexes)
    validate_formal_normalization(expected_indexes["annotations"])
    invalid = deepcopy(body)
    mutate_evidence(invalid, mutation)
    with pytest.raises(ValueError):
        indexes = _indexes(invalid)
        validate_formal_positions(indexes)
        validate_formal_normalization(indexes["annotations"])


def test_current_shared_graph_kernel_keeps_factorized_diamond_and_refuses_cycle():
    body, stages = _inventory(), 24
    for index in range(stages):
        body["terms"].append(
            dict(
                local_id=f"d{index}",
                kind="operator",
                children=[
                    dict(role="left", target=f"l{index}", structural=True),
                    dict(role="right", target=f"r{index}", structural=True),
                ],
            )
        )
        for branch in ("l", "r"):
            body["terms"].append(
                dict(
                    local_id=f"{branch}{index}",
                    kind="operator",
                    children=[dict(role="body", target=f"d{index + 1}", structural=True)],
                )
            )
    body["terms"].append(dict(local_id=f"d{stages}", kind="participant"))

    def check(value):
        indexes = _indexes(value)
        nodes = {key: row for index in indexes.values() for key, row in index.items()}
        nodes["reading"] = value["choices"][0]["members"][0]
        validate_inventory_topology(value, indexes, nodes, {"reading": value["choices"][0]})

    check(body)
    assert len(body["terms"]) == 3 * stages + 3
    assert sum(len(row.get("children", ())) for row in body["terms"]) == 4 * stages + 1
    body["terms"][-1]["children"] = [dict(role="back", target="d0", structural=True)]
    with pytest.raises(ValueError, match="cycle"):
        check(body)


@pytest.mark.parametrize(
    "mutation",
    ["foreign_occurrence", "dropped_choices", "dropped_basis_choices", "dropped_external_choices"],
)
def test_current_shared_witness_kernel_preserves_source_and_choice_conservation(profiles, mutation):
    from corpus_structure.semantic.characterization import (
        attachment_policies,
        validate_attachment_basis,
    )
    from corpus_structure.semantic.identity import canonical_bytes
    from semantic.characterization_evidence_support import mutate_witness, witness_rows

    acquired = profiles[0]
    policies = attachment_policies(acquired.prepared)
    body = witness_rows(_inventory())
    for annotation in body["annotations"]:
        if annotation["local_id"] in {"construction", "production"}:
            annotation["occurrences"] = ["o0"]

    def check(value):
        indexes = _indexes(value)
        nodes = {key: row for index in indexes.values() for key, row in index.items()}
        nodes["reading"] = value["choices"][0]["members"][0]

        for role in value["roles"]:
            validate_attachment_basis(
                role["basis"],
                policies,
                lambda name, item: acquired.prepared.validate_json(
                    "DdoSemantic" + name.removeprefix("Characterization"), canonical_bytes(item)
                ),
            )
        validate_inventory_topology(value, indexes, nodes, {"reading": value["choices"][0]})
        verify_interpreted_attachment_witnesses(value["roles"], nodes, policies)

    check(body)
    invalid = deepcopy(body)
    mutate_witness(invalid, mutation)
    with pytest.raises(ValueError, match="attachment"):
        check(invalid)
