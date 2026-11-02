"""Independent qualifier-role and scientific grouping expectations at the release boundary."""

import json
from dataclasses import replace
from hashlib import sha256
from types import SimpleNamespace

import duckdb
import pytest
import yaml

from corpus_structure.semantic.archive_reader import reconstruct_release
from corpus_structure.semantic.comparison_projection import (
    ARTIFACT,
    ComparisonProjection,
    comparison_projection,
)
from corpus_structure.semantic.domain_operations import ReleasedRulesPolicy
from corpus_structure.semantic.identity import canonical_bytes, fact_key
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.releases import _products
from corpus_structure.semantic.types import (
    PreparationError,
    PreparationProfile,
    PreparedArtifact,
    SourceArtifact,
    SourceBundle,
)


def comparison_bundle(qualifiers="attribution measure", identity="", *, extra=None):
    annotations = {"cs:role": "predicate"}
    if qualifiers is not None:
        annotations["cs:qualifiers"] = qualifiers
    if identity is not None:
        annotations["cs:identity_qualifiers"] = identity
    source = {
        "id": "https://example.org/comparison",
        "name": "comparison",
        "prefixes": {"ex": "https://example.org/"},
        "default_prefix": "ex",
        "default_range": "string",
        "types": {"string": {"base": "str", "uri": "xsd:string"}},
        "classes": {
            "Thing": {
                "attributes": {
                    "id": {"identifier": True},
                    "owns": {"annotations": annotations},
                }
            },
            "Qualification": {
                "attributes": {
                    "interval": {},
                    "attribution": {},
                    "measure": {},
                    "source": {"annotations": {"cs:key_role": "provenance"}},
                }
            },
        },
    }
    if extra is not None:
        extra(source)
    return SourceBundle(
        "comparison", (SourceArtifact("comparison", yaml.safe_dump(source).encode()),)
    )


def test_comparison_can_group_distinct_facts_and_still_preserves_interval_context():
    prepared = prepare_release(comparison_bundle())
    projection = comparison_projection(prepared)
    first: dict[str, object] = {
        "interval": "2020",
        "attribution": "Alice",
        "measure": "1",
        "source": "s1",
    }
    second: dict[str, object] = {
        "interval": "2020",
        "attribution": "Bob",
        "measure": "2",
        "source": "s2",
    }
    partitions = [
        projection.partition("Thing", "https://example.org/owns", "Qualification", q)
        for q in (first, second)
    ]
    assert partitions == [
        (
            {"interval": "2020", "attribution": "Alice", "measure": "1"},
            {"interval": "2020"},
            {"attribution": "Alice", "measure": "1"},
        ),
        (
            {"interval": "2020", "attribution": "Bob", "measure": "2"},
            {"interval": "2020"},
            {"attribution": "Bob", "measure": "2"},
        ),
    ]
    facts = [
        prepared.fact_identity("r", "owner", "https://example.org/owns", "land", q)
        for q in (first, second)
    ]
    assert facts[0] != facts[1]
    assert facts[0] == fact_key(
        prepared.release_id,
        "r",
        "owner",
        "https://example.org/owns",
        "land",
        {"interval": "2020", "attribution": "Alice", "measure": "1"},
    )
    assert projection.partition(
        "Thing", "https://example.org/owns", "Qualification", {**first, "interval": "2021"}
    )[1] == {"interval": "2021"}


def test_legacy_overlap_is_intentional_context_and_omission_is_explicit_default():
    prepared = prepare_release(comparison_bundle(identity="attribution"))
    _, context, compared = comparison_projection(prepared).partition(
        "Thing",
        "https://example.org/owns",
        "Qualification",
        {"attribution": "Alice", "measure": "1"},
    )
    assert context == {"attribution": "Alice"}
    assert compared == {"measure": "1"}
    default = prepare_release(comparison_bundle(None, None))
    projection = comparison_projection(default)
    assert isinstance(projection, ComparisonProjection)
    assert projection.default == "non-provenance-qualification-is-context-v1"
    assert projection.predicates == ()
    assert projection.partition(
        "Thing", "https://example.org/owns", "Qualification", {"measure": "1", "source": "s"}
    ) == ({"measure": "1"}, {"measure": "1"}, {})


def test_empty_authored_lists_without_a_qualification_scope_remain_readable():
    bundle = comparison_bundle("", "", extra=lambda source: source["classes"].pop("Qualification"))
    prepared = prepare_release(bundle)
    projection = comparison_projection(prepared)
    assert isinstance(projection, ComparisonProjection)
    assert projection.qualifications == () and projection.predicates == ()
    archived = reconstruct_release(
        _products(prepared), prepared.manifest, bundle, PreparationProfile(), prepared.artifacts
    )
    assert comparison_projection(archived) == projection


@pytest.mark.parametrize(
    ("qualifiers", "identity"),
    [
        ("missing", ""),
        ("measure measure", ""),
        ("measure", "measure measure"),
        ("measure", "attribution"),
        ("source", ""),
    ],
)
def test_invalid_projection_is_located_preparation_refusal(qualifiers, identity):
    with pytest.raises(PreparationError) as refusal:
        prepare_release(comparison_bundle(qualifiers, identity))
    diagnostic = refusal.value.diagnostics[0]
    assert diagnostic.code == "comparison_projection"
    assert diagnostic.location == "Thing/owns/comparison"


def test_property_in_another_qualification_scope_does_not_resolve():
    def unrelated(source):
        source["classes"].update(
            {
                "OtherQualification": {"is_a": "Qualification", "attributes": {"foreign": {}}},
                "ChosenQualification": {"is_a": "Qualification"},
                "AgentClaim": {
                    "attributes": {
                        "qualification": {
                            "range": "ChosenQualification",
                            "required": True,
                            "inlined": True,
                        }
                    }
                },
            }
        )

    with pytest.raises(PreparationError, match="unavailable qualification property foreign"):
        prepare_release(comparison_bundle("foreign", extra=unrelated))


def test_archive_reads_checked_product_without_compilation_or_annotation_interpretation(
    monkeypatch,
):
    bundle = comparison_bundle()
    prepared = prepare_release(bundle)
    import corpus_structure.semantic.comparison_projection as compiler

    def unavailable(*args, **kwargs):
        raise AssertionError("comparison compilation is not a read dependency")

    monkeypatch.setattr(compiler, "compile_comparison_projection", unavailable)
    archived = reconstruct_release(
        _products(prepared), prepared.manifest, bundle, PreparationProfile(), prepared.artifacts
    )
    assert comparison_projection(archived) == comparison_projection(prepared)
    assert comparison_projection(archived).partition(
        "Thing", "https://example.org/owns", "Qualification", {"attribution": "Alice"}
    )[2] == {"attribution": "Alice"}
    with pytest.raises(ValueError, match="exact resolved projection"):
        comparison_projection(
            replace(prepared, artifacts=tuple(a for a in prepared.artifacts if a.kind != ARTIFACT))
        )


def test_invalid_archived_resolved_scope_refuses():
    prepared = prepare_release(comparison_bundle())
    artifacts = []
    for artifact in prepared.artifacts:
        if artifact.kind == ARTIFACT:
            body = json.loads(artifact.content)
            body["predicates"][0]["compared"][0]["iri"] = "https://other.example/attribution"
            artifact = PreparedArtifact(ARTIFACT, canonical_bytes(body))
        artifacts.append(artifact)
    with pytest.raises(ValueError, match="property/scope/role differs"):
        comparison_projection(replace(prepared, artifacts=tuple(artifacts)))


def test_historical_projection_refuses_instead_of_reinterpreting_archived_lists():
    prepared = prepare_release(comparison_bundle(None, None))
    manifest = json.loads(prepared.manifest)
    manifest["profile"]["compiler_version"] = "13"
    rows = tuple(
        replace(
            row, body=canonical_bytes({**json.loads(row.body), "cs:qualifiers": "measure missing"})
        )
        if row.kind == "operation_property" and row.name == "Thing/owns"
        else row
        for row in prepared.registry_rows
    )
    historical = replace(
        prepared,
        manifest=canonical_bytes(manifest),
        registry_rows=rows,
        artifacts=tuple(a for a in prepared.artifacts if a.kind != ARTIFACT),
    )
    # The historical registry remains evidence, not a supported translation route.
    with pytest.raises(ValueError, match=r"^unsupported comparison projection compiler 13$"):
        comparison_projection(historical)
    row = next(r for r in rows if r.kind == "operation_property" and r.name == "Thing/owns")
    assert json.loads(row.body)["cs:qualifiers"] == "measure missing"


def test_scientific_consumer_uses_projection_preserving_group_keys_and_occurrences():
    prepared = prepare_release(comparison_bundle())
    policy = object.__new__(ReleasedRulesPolicy)
    policy.prepared = prepared
    policy.definitions = {d.name: d for d in prepared.definitions}
    policy.metadata = {}
    policy.comparison_projection = comparison_projection(prepared)
    candidates = tuple(
        SimpleNamespace(
            class_name="Thing",
            predicate="https://example.org/owns",
            qualification_class="Qualification",
            qualification={"interval": "2020", "attribution": who, "measure": value},
            subject="owner",
            statement="statement",
            object="land",
            fact_id=f"fact:{who}",
            occurrence_id=f"occ:{who}",
        )
        for who, value in (("Alice", "1"), ("Bob", "2"))
    )
    with duckdb.connect() as connection:
        captured = []

        def disagreements(relation):
            captured.extend(relation.to_arrow_table().to_pylist())
            return relation.query(
                "meaning_rows",
                "SELECT key FROM meaning_rows GROUP BY key HAVING count(DISTINCT meaning)>1",
            )

        scope = SimpleNamespace(connection=connection, operation_disagreements=disagreements)
        generated, unresolved, equivalent, assessments = policy.scientific_decisions(
            SimpleNamespace(candidates=candidates, batch=SimpleNamespace(occurrence=())), scope
        )
    expected_key = sha256(
        canonical_bytes(
            [
                "sequence",
                [
                    ["string", "owner"],
                    ["string", "https://example.org/owns"],
                    ["string", "statement"],
                    ["string", "land"],
                    ["mapping", [["interval", ["string", "2020"]]]],
                ],
            ]
        )
    ).hexdigest()
    assert [r["key"] for r in captured] == [expected_key, expected_key]
    assert [json.loads(r["meaning"]) for r in captured] == [
        [
            "mapping",
            [
                ["bindings", ["sequence", []]],
                [
                    "qualifiers",
                    [
                        "mapping",
                        [["attribution", ["string", "Alice"]], ["measure", ["string", "1"]]],
                    ],
                ],
            ],
        ],
        [
            "mapping",
            [
                ["bindings", ["sequence", []]],
                [
                    "qualifiers",
                    ["mapping", [["attribution", ["string", "Bob"]], ["measure", ["string", "2"]]]],
                ],
            ],
        ],
    ]
    assert dict(generated) == {
        "occ:Alice": {"disagreement:" + expected_key},
        "occ:Bob": {"disagreement:" + expected_key},
    }
    assert not unresolved and not equivalent and not assessments
