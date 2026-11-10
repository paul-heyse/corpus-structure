"""Independent source-preserving terminology and portable-contract controls."""

import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.interpretations import (
    lookup_terms,
    normalize_term,
    validate_interpretation_payload,
)
from corpus_structure.semantic.portable_interpretation import export_interpretation_contract
from corpus_structure.semantic.regeneration import prepare_packs


@pytest.fixture(scope="module")
def prepared():
    return prepare_packs((DOMAINS / "statistics",))[-1]


def payload(prepared):
    lookup = lookup_terms(prepared, "distribution_family", "Gaussian distribution")
    return dict(
        source_record=dict(
            project_id="research",
            run_id=1,
            cut_id=2,
            release_id=prepared.release_id,
            realization_id="realization",
            data_revision=1,
            record_id="record",
            interpretation_id="interpretation",
            source_view_id=1,
        ),
        vocabulary_release=prepared.release_id,
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


def test_lookup_preserves_synonym_predicate_and_selected_universe(prepared):
    result = lookup_terms(prepared, "distribution_family", "  GAUSSIAN   distribution ")
    assert result["examined"] == 6 and [r["value"] for r in result["candidates"]] == ["normal"]
    assert result["candidates"][0]["matching_field"] == "synonym"
    assert (
        result["candidates"][0]["matching_predicate"]
        == "http://purl.obolibrary.org/obo/IAO_0000118"
    )
    assert lookup_terms(prepared, "distribution_family", "Weibull")["candidates"] == []
    assert lookup_terms(prepared, "distribution_attribute", "sample variance")["candidates"] == []
    assert lookup_terms(prepared, "distribution_attribute", "mean")["candidates"] == []
    assert len(lookup_terms(prepared, "distribution_attribute", browse=True)["candidates"]) == 3
    with pytest.raises(ValueError, match="either"):
        lookup_terms(prepared, "distribution_family", "normal", browse=True)


def test_normalization_does_not_strip_accents_or_punctuation():
    assert normalize_term(" e\u0301  X ") == normalize_term("é x")
    assert normalize_term("é") != normalize_term("e")
    assert normalize_term("normal-distribution") != normalize_term("normal distribution")


def test_released_subtype_and_semantic_closure(prepared):
    value = payload(prepared)
    prepared.validate_json(
        "TerminologyInterpretationV1",
        json.dumps(
            dict(
                kind="proposal",
                semantic_type="terminology.interpretation",
                effect="retain_private",
                assessment_event="local-contribution-1",
                question="interpret.terminology",
                value=value,
            )
        ).encode(),
    )
    validate_interpretation_payload(prepared, "terminology.interpretation", value)
    assert value["decisions"][0]["mapping_predicate"].endswith("closeMatch")


@pytest.mark.parametrize(
    "mutation", ["pin", "meaning", "selected", "duplicate", "predicate", "unresolved"]
)
def test_interpretation_semantic_corruption_refuses(prepared, mutation):
    value = payload(prepared)
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
        validate_interpretation_payload(prepared, "terminology.interpretation", value)


def test_unit_metadata_is_captured_draft_unchecked_and_unexecuted(prepared):
    metadata = prepared.vocabulary_metadata
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


def test_independent_offline_authoring_consumer(prepared, tmp_path):
    package = tmp_path / "contract"
    report = export_interpretation_contract(prepared, package)
    instance: dict[str, Any] = dict(
        kind="proposal",
        semantic_type="terminology.interpretation",
        effect="retain_private",
        assessment_event="local-contribution-1",
        question="interpret.terminology",
        value=payload(prepared),
    )
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
    instance["value"]["source_record"]["run_id"] = "1"
    path.write_text(json.dumps(instance))
    invalid = subprocess.run(args, cwd=tmp_path, capture_output=True, text=True)
    assert invalid.returncode == 1
    result = json.loads(invalid.stdout)
    assert result["errors"] and result["errors"][0]["instance_path"] == [
        "value",
        "source_record",
        "run_id",
    ]
    # A wrong externally supplied digest refuses, even though the schema itself is valid.
    wrong = subprocess.run([*args[:-1], "0" * 64], cwd=tmp_path, capture_output=True, text=True)
    assert wrong.returncode != 0


def test_authored_kernel_retains_explicit_decision_without_reextracting(prepared, tmp_path):
    from types import SimpleNamespace

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.interpretations import (
        AuthoredInterpretationConfig,
        TerminologyInterpretationMethod,
    )
    from corpus_structure.semantic.observations import source_python

    value = payload(prepared)
    source = dict(
        project_id="research",
        run_id=1,
        cut_id=2,
        release_id=prepared.release_id,
        result_revision=1,
        source_view_id=1,
        native_task_id=3,
        native_product_key="native",
        native_content_digest="a" * 64,
        projection_digest="b" * 64,
        recipe_digest="c" * 64,
        coordinate_version=3,
    )
    cfg = AuthoredInterpretationConfig.model_validate(dict(source=source, reviews=[value]))
    reader = SimpleNamespace(prepared=prepared)
    method = TerminologyInterpretationMethod()
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, 1, "source")
    context = SimpleNamespace(reader=reader, check_active=lambda: None)
    (result,) = method.run([SimpleNamespace(ref=ref)], cfg, context)
    assert result.contributions is not None
    assert result.contribution_operations is not None
    assert len(result.contributions) == 1
    row = result.contributions[0]
    assert "occurrence_id" not in row and row["anchors"] == ()
    assert source_python(row["value"]) == value
    assert result.contribution_operations[0]["question"] == "interpret.terminology"
    assert value["source_record"]["run_id"] == 1


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


def test_authored_source_records_decode_json_lists_without_scalar_loss(prepared):
    from types import SimpleNamespace

    from corpus_structure.core.method import UnitRef
    from corpus_structure.core.vocab import TaskUnitType
    from corpus_structure.methods.interpretations import AuthorSourceRecordsMethod
    from corpus_structure.semantic.record_contracts import (
        bind_record_candidates,
        interpretation_identity,
        record_identity,
    )

    from .test_record_contracts import measurement_record

    record, coordinates = measurement_record()
    record["record_id"] = record_identity(prepared.release_id, record)
    record["interpretation_id"] = interpretation_identity(record)
    pin = record["pin"]
    source = dict(
        project_id="research",
        run_id=1,
        cut_id=2,
        release_id=prepared.release_id,
        result_revision=1,
        source_view_id=pin["source_view_id"],
        native_task_id=pin["native_product_task_id"],
        native_product_key=pin["product_key"],
        native_content_digest=pin["product_digest"],
        projection_digest=pin["projection_digest"],
        recipe_digest=pin["recipe_digest"],
        coordinate_version=3,
    )
    method = AuthorSourceRecordsMethod()
    authored = json.loads(json.dumps(dict(source=source, records=[record])))
    assert isinstance(authored["records"][0]["fields"], list)
    cfg = method.Config.model_validate(authored)
    ref = UnitRef(TaskUnitType.SOURCE_VIEW, pin["source_view_id"], pin["source"])
    ctx = SimpleNamespace(reader=SimpleNamespace(prepared=prepared), check_active=lambda: None)
    (result,) = method.run([SimpleNamespace(ref=ref)], cfg, ctx)
    assert result.records is not None
    assert isinstance(result.records[0]["fields"], tuple)
    fields = {f["role"]: f for f in result.records[0]["fields"]}
    assert fields["original_value"]["value"] == {
        "kind": "decimal",
        "lexical": "1.234567890123456789e-400",
    }
    (bound,) = bind_record_candidates(
        prepared, source=pin["source"], records=result.records, coordinate_texts=coordinates
    )
    assert bound.model_dump(mode="python")["record_id"] == record["record_id"]


def test_descriptive_unit_reference_corruption_refuses(prepared):
    from dataclasses import replace

    from corpus_structure.semantic.identity import canonical_bytes
    from corpus_structure.semantic.terminology import ARTIFACT, decode_vocabulary_metadata
    from corpus_structure.semantic.types import PreparedArtifact

    artifact = next(a for a in prepared.artifacts if a.kind == ARTIFACT)
    body = json.loads(artifact.content)
    member = body["enums"]["RecognizedTimeUnit"]["members"][0]
    member["source_identifier"]["status"] = "checked"
    damaged = replace(
        prepared,
        artifacts=tuple(
            PreparedArtifact(a.kind, canonical_bytes(body)) if a.kind == ARTIFACT else a
            for a in prepared.artifacts
        ),
    )
    result = decode_vocabulary_metadata(damaged)
    assert result["status"] == "corrupt"
    assert "descriptive unit identifier" in result["reason"]
    assert all(
        d.outcome != "unchecked" or d.message == "not4curation:unchecked"
        for d in prepared.diagnostics
    )


def test_retained_review_answer_uses_json_context_and_keeps_byte_bound():
    from corpus_structure.semantic.query import ReadLimit
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
