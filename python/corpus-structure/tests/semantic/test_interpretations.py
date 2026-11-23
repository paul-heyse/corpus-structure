"""Independent source-preserving terminology and portable-contract controls."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.semantic.interpretations import (
    lookup_terms,
    normalize_term,
    validate_interpretation_payload,
)
from corpus_structure.semantic.portable_interpretation import export_interpretation_contract


def payload(statistics_pack_prepared):
    from evaluate.declared_record_policy_support import source

    lookup = lookup_terms(statistics_pack_prepared, "distribution_family", "Gaussian distribution")
    return dict(
        standing="private_authored_judgment",
        judgment_type="terminology.interpretation",
        source_record=dict(
            project_id="research",
            demand_id="demand:source",
            read_id="read:source",
            cut_id="cut:source",
            release_id=statistics_pack_prepared.release_id,
            runtime_id="runtime:source",
            read_scope_json="{}",
            product_id="product:source",
            member_id="member:source",
            kind_contract="kind:source",
            family_contract="family:source",
            record_id="record",
            interpretation_id="interpretation",
            source_pin=source(1).model_dump(mode="json", exclude_none=True),
        ),
        vocabulary_release=statistics_pack_prepared.release_id,
        metadata_digest=lookup["metadata_digest"],
        lookup_policy="released-lexical-1",
        decisions=[
            dict(
                field="distribution_family",
                focus=dict(
                    role="term",
                    anchor_id="anchor",
                    start=0,
                    end=21,
                    source_piece="Gaussian distribution",
                ),
                candidates=lookup["candidates"],
                outcome="selected",
                selected_value="normal",
                mapping_predicate="http://www.w3.org/2004/02/skos/core#closeMatch",
                mapping_direction="source_to_term",
                assessment=(
                    "Source context supports a distribution family; lexical "
                    "equality alone does not prove equivalence."
                ),
                reviewer="independent-reviewer",
            )
        ],
    )


def test_lookup_preserves_synonym_predicate_and_selected_universe(statistics_pack_prepared):
    result = lookup_terms(
        statistics_pack_prepared, "distribution_family", "  GAUSSIAN   distribution "
    )
    assert result["examined"] == 6 and [r["value"] for r in result["candidates"]] == ["normal"]
    assert result["candidates"][0]["matching_field"] == "synonym"
    assert (
        result["candidates"][0]["matching_predicate"]
        == "http://purl.obolibrary.org/obo/IAO_0000118"
    )
    assert (
        lookup_terms(statistics_pack_prepared, "distribution_family", "Weibull")["candidates"] == []
    )
    assert (
        lookup_terms(statistics_pack_prepared, "distribution_attribute", "sample variance")[
            "candidates"
        ]
        == []
    )
    assert (
        lookup_terms(statistics_pack_prepared, "distribution_attribute", "mean")["candidates"] == []
    )
    assert (
        len(
            lookup_terms(statistics_pack_prepared, "distribution_attribute", browse=True)[
                "candidates"
            ]
        )
        == 3
    )
    with pytest.raises(ValueError, match="either"):
        lookup_terms(statistics_pack_prepared, "distribution_family", "normal", browse=True)


def test_normalization_does_not_strip_accents_or_punctuation():
    assert normalize_term(" e\u0301  X ") == normalize_term("é x")
    assert normalize_term("é") != normalize_term("e")
    assert normalize_term("normal-distribution") != normalize_term("normal distribution")


def test_released_subtype_and_semantic_closure(statistics_pack_prepared):
    value = payload(statistics_pack_prepared)
    statistics_pack_prepared.validate_json(
        "DdoAuthoredTerminologyJudgment",
        json.dumps(value).encode(),
    )
    validate_interpretation_payload(statistics_pack_prepared, "terminology.interpretation", value)
    assert value["decisions"][0]["mapping_predicate"].endswith("closeMatch")


def test_no_match_requires_an_explicit_empty_candidate_collection(statistics_pack_prepared):
    value = payload(statistics_pack_prepared)
    decision = value["decisions"][0]
    decision.update(candidates=[], outcome="no_match")
    decision["focus"].update(source_piece="Weibull", end=len("Weibull"))
    for field in ("selected_value", "mapping_predicate", "mapping_direction"):
        del decision[field]

    kind = "DdoAuthoredTerminologyJudgment"
    statistics_pack_prepared.validate_json(kind, json.dumps(value).encode())
    validate_interpretation_payload(statistics_pack_prepared, "terminology.interpretation", value)
    del decision["candidates"]
    with pytest.raises(ValueError, match="candidates"):
        statistics_pack_prepared.validate_json(kind, json.dumps(value).encode())


@pytest.mark.parametrize(
    "mutation", ["pin", "meaning", "selected", "duplicate", "predicate", "unresolved"]
)
def test_interpretation_semantic_corruption_refuses(statistics_pack_prepared, mutation):
    value = payload(statistics_pack_prepared)
    decision = value["decisions"][0]
    if mutation == "pin":
        value["metadata_digest"] = "0" * 64
    elif mutation == "meaning":
        decision["candidates"][0]["meaning"] = "STATO:wrong"
    elif mutation == "selected":
        decision["selected_value"] = "poisson"
    elif mutation == "duplicate":
        value["decisions"].append(deepcopy(decision))
    elif mutation == "predicate":
        decision["mapping_predicate"] = "denotes"
    else:
        decision["outcome"] = "unresolved"
    with pytest.raises(ValueError):
        validate_interpretation_payload(
            statistics_pack_prepared, "terminology.interpretation", value
        )


def test_unit_metadata_is_captured_draft_unchecked_and_unexecuted(statistics_pack_prepared):
    metadata = statistics_pack_prepared.vocabulary_metadata
    assert metadata["version"] == 2 and metadata["sources"]["valuesets_units"]["status"] == "DRAFT"
    hour = next(
        m for m in metadata["enums"]["RecognizedTimeUnit"]["members"] if m["value"] == "HOUR"
    )
    assert hour["meaning"] is None
    assert hour["source_identifier"] == dict(
        iri="http://purl.obolibrary.org/obo/UO_0000032",
        status="unchecked",
        provenance="captured_valuesets_declaration",
    )
    assert hour["status"] == "local" and hour["coverage"]["numerical_equivalence"] == "unassessed"
    assert any(a["predicate"] == "conversion_to_second" for a in hour["annotations"])
    assert all(
        m["status"] == "checked"
        for m in metadata["enums"]["StatisticalDistributionFamily"]["members"]
    )


def test_independent_offline_authoring_consumer(statistics_pack_prepared, tmp_path):
    package = tmp_path / "contract"
    report = export_interpretation_contract(statistics_pack_prepared, package)
    instance: dict[str, Any] = payload(statistics_pack_prepared)
    path = tmp_path / "input.json"
    path.write_text(json.dumps(instance))
    script = Path(__file__).parents[4] / "examples/offline_interpretation.py"
    args = [
        sys.executable,
        "-I",
        str(script),
        str(package),
        str(path),
        "--expected-digest",
        report["manifest_digest"],
    ]
    run = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True)
    assert run.returncode == 0, run.stderr
    assert json.loads(run.stdout)["claim"] == "structural_preflight_only"
    instance["source_record"]["member_id"] = 1
    path.write_text(json.dumps(instance))
    invalid = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True)
    assert invalid.returncode == 1
    result = json.loads(invalid.stdout)
    assert result["errors"] and result["errors"][0]["instance_path"] == [
        "source_record",
        "member_id",
    ]
    # A wrong externally supplied digest refuses, even though the schema itself is valid.
    wrong = subprocess.run([*args[:-1], "0" * 64], cwd=tmp_path, capture_output=True, text=True)
    assert wrong.returncode != 0


def test_offline_error_inventory_and_file_bounds(tmp_path):
    import runpy
    from hashlib import sha256

    consumer = runpy.run_path(str(Path(__file__).parents[4] / "examples/offline_interpretation.py"))
    package = tmp_path / "package"
    package.mkdir()
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {f"field{i}": {"type": "integer"} for i in range(120)},
    }
    content = json.dumps(schema).encode()
    (package / "schema.json").write_bytes(content)
    (package / "manifest.json").write_text(
        json.dumps(
            dict(
                version=1,
                mode="validation",
                dialect="https://json-schema.org/draft/2020-12/schema",
                entry="schema.json",
                schema_digest=sha256(content).hexdigest(),
                release_id="independent-fixture",
                limitations=["structural_preflight_only"],
            )
        )
    )
    result = consumer["preflight"](package, {f"field{i}": "wrong" for i in range(120)})
    assert result["outcome"] == "failed" and len(result["errors"]) == 100
    assert result["inventory_complete"] is False and result["complete"] is False
    oversized = tmp_path / "oversized"
    oversized.write_bytes(b"x" * 9)
    with pytest.raises(ValueError, match="byte limit"):
        consumer["bounded_read"](oversized, 8)


def test_authored_source_records_decode_json_lists_without_scalar_loss(
    statistics_pack_prepared, statistics_pack_inputs
):
    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.record_contracts import (
        bind_record_candidates,
        interpretation_identity,
        record_family_contract,
        record_identity,
    )
    from semantic.record_contracts_support import measurement_record

    record, coordinates = measurement_record()
    from evaluate.declared_record_policy_support import source

    from corpus_structure.semantic.record_contracts import anchor_identity, evidence_set_identity

    pin = source(1).model_dump(mode="json", exclude_none=True)
    record["pin"] = pin
    anchors = {}
    for anchor in record["anchors"]:
        old = anchor["anchor_id"]
        anchor["pin"] = pin
        anchor["anchor_id"] = anchor_identity(anchor)
        anchors[old] = anchor["anchor_id"]
    record["occurrence_anchors"] = [anchors[key] for key in record["occurrence_anchors"]]
    sets = {}
    for evidence in record["evidence_sets"]:
        old = evidence["set_id"]
        evidence["anchors"] = [anchors[key] for key in evidence["anchors"]]
        evidence["set_id"] = evidence_set_identity(evidence)
        sets[old] = evidence["set_id"]
    for field in record["fields"]:
        field["evidence_sets"] = [sets[key] for key in field["evidence_sets"]]
    coordinates = [{**coordinate, "pin": pin} for coordinate in coordinates]
    from corpus_structure.semantic.data_operation_compilation import compile_data_operations

    model = compile_data_operations(statistics_pack_inputs[0])
    record["record_id"] = record_identity(record_family_contract(model, record["contract"]), record)
    record["interpretation_id"] = interpretation_identity(record)
    authored = json.loads(json.dumps(record))
    assert isinstance(authored["fields"], list)
    decoded = statistics_pack_prepared.validate_json(
        "SourceRecord", canonical_bytes(authored)
    ).model_dump(mode="python", exclude_none=True)
    assert isinstance(decoded["fields"], tuple)
    fields = {field["role"]: field for field in decoded["fields"]}
    assert fields["original_value"]["value"] == {
        "kind": "decimal",
        "lexical": "1.234567890123456789e-400",
    }
    (bound,) = bind_record_candidates(
        statistics_pack_prepared,
        model=model,
        source=record["pin"]["source"],
        records=(decoded,),
        coordinate_texts=coordinates,
    )
    assert bound.model_dump(mode="python")["record_id"] == record["record_id"]


def test_descriptive_unit_reference_corruption_refuses(statistics_pack_prepared):
    from dataclasses import replace

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.terminology import ARTIFACT, decode_vocabulary_metadata
    from corpus_structure.semantic.types import PreparedArtifact

    artifact = next(a for a in statistics_pack_prepared.artifacts if a.kind == ARTIFACT)
    body = json.loads(artifact.content)
    member = body["enums"]["RecognizedTimeUnit"]["members"][0]
    member["source_identifier"]["status"] = "checked"
    damaged = replace(
        statistics_pack_prepared,
        artifacts=tuple(
            PreparedArtifact(a.kind, canonical_bytes(body)) if a.kind == ARTIFACT else a
            for a in statistics_pack_prepared.artifacts
        ),
    )
    result = decode_vocabulary_metadata(damaged)
    assert result["status"] == "corrupt"
    assert "descriptive unit identifier" in result["reason"]
    assert all(
        d.outcome != "unchecked" or d.message == "not4curation:unchecked"
        for d in statistics_pack_prepared.diagnostics
    )


def test_retained_review_answer_uses_json_context_and_keeps_byte_bound():
    from corpus_structure.semantic.refusal_types import ReadLimit
    from corpus_structure.serve.interpretations import answer

    # Retained product readers reconstruct tuple populations in Python. Transport
    # JSON must preserve them as arrays, including an explicitly empty anchor set.
    body = dict(
        contributions=(
            dict(
                anchors=(),
                value=dict(
                    kind="object",
                    fields=(dict(name="assessment", value=dict(kind="text", text="reviewed")),),
                ),
            ),
        )
    )
    result = answer("retained_review", body)
    assert result.model_dump(mode="json")["body"] == dict(
        contributions=[
            dict(
                anchors=[],
                value=dict(
                    kind="object",
                    fields=[dict(name="assessment", value=dict(kind="text", text="reviewed"))],
                ),
            )
        ]
    )
    with pytest.raises(ReadLimit, match="byte budget"):
        answer("retained_review", body, max_bytes=20)
