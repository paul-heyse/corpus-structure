"""Independent DDO identity vectors and discriminating semantic locality checks."""

from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import Any

import pytest

from corpus_structure.semantic.data_operation_identity import (
    AdmissionManifest,
    CollectionValue,
    OptionalValue,
    ProfileField,
    SemanticGraph,
    SemanticRequestKey,
    body_identity,
    canonical_identity,
    definition_fingerprint,
    eligibility_fingerprint,
    execution_attestation,
    implementation_slice_fingerprint,
    kind_fingerprint,
    product_identity,
    profile_identities,
    recipe_fingerprint,
    runtime_artifact_identity,
    semantic_fields,
    semantic_value,
    subject_identity,
)
from corpus_structure.semantic.data_operation_model import SubjectContext


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, b'["null"]'),
        (True, b'["boolean",true]'),
        (1, b'["integer","1"]'),
        ("1", b'["string","1"]'),
        (Decimal("1.200"), b'["decimal","1.2"]'),
        (0.0, b'["float","0x0.0p+0"]'),
        (-0.0, b'["float","-0x0.0p+0"]'),
        (date(2026, 11, 12), b'["date","2026-11-12"]'),
        (datetime(2026, 11, 12, tzinfo=UTC), b'["datetime","2026-11-12T00:00:00+00:00"]'),
        ({"x": []}, b'["mapping",[["x",["sequence",[]]]]]'),
        (OptionalValue("present", None), b'["present",["null"]]'),
        (OptionalValue("present", []), b'["present",["sequence",[]]]'),
        (OptionalValue("known-absent"), b'["known-absent"]'),
        (OptionalValue("unknown"), b'["unknown"]'),
        (OptionalValue("unavailable"), b'["unavailable"]'),
        (CollectionValue("set", (2, 1, 1)), b'["set",[["integer","1"],["integer","2"]]]'),
        (
            CollectionValue("bag", (2, 1, 1)),
            b'["bag",[["integer","1"],["integer","1"],["integer","2"]]]',
        ),
        (
            CollectionValue("ordered-bag", (2, 1)),
            b'["ordered-bag",[["integer","2"],["integer","1"]]]',
        ),
    ],
)
def test_independently_authored_canonical_vectors(value, expected):
    result = canonical_identity("vector", value)
    literal = b'["ddo","vector","1",' + expected + b"]"
    assert result.canonical_input == literal
    # SHA-256's library implementation is independent of production framing/normalization.
    assert result.digest == sha256(literal).hexdigest()


def test_literal_full_digest_vector_and_domain_separation():
    # The literal digest is generated once from the independently specified bytes.
    result = canonical_identity("vector", True)
    assert result.digest == "72da81d8b5b570bb7d1493f0b0882c8de91867e093710009e73fd572691cfd7e"
    assert canonical_identity("other", True).digest != result.digest


def test_exact_strings_and_rejections():
    assert canonical_identity("body", "e\u0301") != canonical_identity("body", "é")
    assert canonical_identity("body", "e\u0301").canonical_input.endswith(
        b'["string","e\xcc\x81"]]'
    )
    for value in (float("nan"), Decimal("Infinity"), datetime(2026, 1, 1)):
        with pytest.raises(ValueError):
            canonical_identity("body", value)
    with pytest.raises(UnicodeEncodeError):
        canonical_identity("body", "\ud800")
    with pytest.raises(TypeError):
        canonical_identity("body", {1: "value"})
    with pytest.raises(ValueError, match="duplicate"):
        semantic_fields((("urn:field", 1), ("urn:field", 2)))
    with pytest.raises(ValueError):
        semantic_value(OptionalValue("unknown", 4))


def graph_records() -> dict[str, Any]:
    return {
        "nodes": [
            {"id": "urn:root", "category": "kind", "payload": {"required": True}},
            {"id": "urn:base", "category": "kind", "payload": {"minimum": 1}},
            {"id": "urn:isolated", "category": "kind", "payload": {}},
        ],
        "edges": [
            {"source": "urn:root", "target": "urn:base", "relation": "inherits"},
            {
                "source": "urn:root",
                "target": "urn:base",
                "relation": "type_reference",
                "role": "left",
            },
            {
                "source": "urn:root",
                "target": "urn:base",
                "relation": "type_reference",
                "role": "right",
                "position": 0,
                "multiplicity": 2,
            },
        ],
    }


def test_rooted_memberships_parallel_roles_isolates_and_order():
    records = graph_records()
    graph = SemanticGraph(records)
    assert graph.node_ids == ("urn:base", "urn:isolated", "urn:root")
    assert graph.closure(("urn:root",)) == ("urn:base", "urn:root")
    assert graph.closure(("urn:base",), direction="dependents") == ("urn:base", "urn:root")
    assert graph.closure(("urn:isolated",)) == ("urn:isolated",)
    assert len(graph.rooted_record("urn:root")["edges"]) == 3
    assert graph.dependency_order() == ("urn:base", "urn:isolated", "urn:root")
    identity = kind_fingerprint(graph, "urn:root")
    records["nodes"].reverse()
    records["edges"].reverse()
    assert kind_fingerprint(records, "urn:root") == identity
    records["nodes"][0]["payload"]["unrelated"] = 99
    assert kind_fingerprint(records, "urn:root") == identity
    records["nodes"][1]["payload"]["minimum"] = 2
    assert kind_fingerprint(records, "urn:root") != identity
    # Caller mutation cannot change the captured immutable effective graph.
    assert kind_fingerprint(graph, "urn:root") == identity


@pytest.mark.parametrize("field,value", [("role", "new"), ("position", 1), ("multiplicity", 3)])
def test_meaningful_parallel_edge_attributes_affect_identity(field, value):
    records = graph_records()
    before = kind_fingerprint(records, "urn:root")
    records["edges"][-1][field] = value
    assert kind_fingerprint(records, "urn:root") != before


def test_duplicate_occurrences_do_not_disappear_in_connectivity():
    records = graph_records()
    before = kind_fingerprint(records, "urn:root")
    records["edges"].append(dict(records["edges"][-1]))
    assert kind_fingerprint(records, "urn:root") != before


def test_validate_entire_declared_universe_before_graph_construction():
    records = graph_records()
    records["edges"].append(
        {"source": "urn:isolated", "target": "urn:missing", "relation": "type_reference"}
    )
    with pytest.raises(ValueError, match=r"unresolved.*urn:missing"):
        kind_fingerprint(records, "urn:root")
    records = graph_records()
    records["nodes"].append(records["nodes"][0])
    with pytest.raises(ValueError, match="duplicate"):
        SemanticGraph(records)
    with pytest.raises(ValueError, match="unknown semantic root"):
        kind_fingerprint(graph_records(), "urn:missing")


@pytest.mark.parametrize(
    "field,value",
    [("position", True), ("position", -1), ("multiplicity", False), ("multiplicity", 0)],
)
def test_invalid_edge_cardinality_refuses(field, value):
    records = graph_records()
    records["edges"][0][field] = value
    with pytest.raises(ValueError):
        SemanticGraph(records)


def test_recursive_references_terminate_but_inheritance_cycles_refuse():
    records = graph_records()
    records["edges"] = [
        {"source": "urn:root", "target": "urn:base", "relation": "type_reference"},
        {"source": "urn:base", "target": "urn:root", "relation": "type_reference"},
        {"source": "urn:isolated", "target": "urn:isolated", "relation": "type_reference"},
    ]
    graph = SemanticGraph(records)
    assert graph.cyclic_components() == (("urn:base", "urn:root"), ("urn:isolated",))
    assert len(kind_fingerprint(graph, "urn:root").digest) == 64
    with pytest.raises(ValueError, match="no dependency order"):
        graph.dependency_order()
    records["edges"][0]["relation"] = "inherits"
    records["edges"][1]["relation"] = "inherits"
    with pytest.raises(ValueError, match="unsupported cycle"):
        SemanticGraph(records)


def test_scc_distinguishes_cycles_downstream_blockage_and_independent_nodes():
    records = {
        "nodes": [
            {"id": name, "category": "operation", "payload": {}} for name in ("A", "B", "C", "D")
        ],
        "edges": [
            {"source": "A", "target": "B", "relation": "possible_call"},
            {"source": "B", "target": "A", "relation": "possible_call"},
            {"source": "C", "target": "B", "relation": "possible_call"},
        ],
    }
    graph = SemanticGraph(records)
    assert graph.components() == (("A", "B"), ("C",), ("D",))
    assert graph.cyclic_components() == (("A", "B"),)
    assert graph.closure(("A",), direction="dependents") == ("A", "B", "C")
    with pytest.raises(ValueError, match="unsupported cycle"):
        graph.require_acyclic({"possible_call"})
    graph.require_acyclic({"possible_call"}, iteration_components=(("A", "B"),))
    with pytest.raises(ValueError, match="complete cyclic component"):
        graph.require_acyclic({"possible_call"}, iteration_components=(("A", "B"), ("D",)))


def test_execution_cycle_requires_explicit_iteration_contract():
    records = {
        "nodes": [{"id": "A", "category": "operation", "payload": {}}],
        "edges": [{"source": "A", "target": "A", "relation": "operation_dependency"}],
    }
    with pytest.raises(ValueError, match="unsupported cycle"):
        SemanticGraph(records)
    graph = SemanticGraph(records, iteration_components=(("A",),))
    assert graph.cyclic_components() == (("A",),)


def slice_records() -> dict[str, Any]:
    return {**graph_records(), "unknowns": [], "boundaries": [], "normalization": "python-cst-v1"}


def test_slice_dependency_completeness_and_normalization_are_explicit():
    records = slice_records()
    initial = implementation_slice_fingerprint(records, "urn:root")
    records["nodes"][2]["payload"]["outside"] = "changed"
    assert implementation_slice_fingerprint(records, "urn:root") == initial
    records["nodes"][1]["payload"]["minimum"] = 2
    assert implementation_slice_fingerprint(records, "urn:root") != initial
    records = slice_records()
    records["normalization"] = "python-cst-v2"
    assert implementation_slice_fingerprint(records, "urn:root") != initial
    records["unknowns"] = [{"source": "urn:root", "reason": "dynamic callback"}]
    with pytest.raises(ValueError, match="unknown required"):
        implementation_slice_fingerprint(records, "urn:root")
    records.pop("unknowns")
    with pytest.raises(ValueError, match="explicit dependency coverage"):
        implementation_slice_fingerprint(records, "urn:root")
    records = slice_records()
    records["boundaries"] = [{"reference": "model", "role": "weights", "content_digest": "abc"}]
    with pytest.raises(ValueError, match=r"interpretation|contract"):
        implementation_slice_fingerprint(records, "urn:root")


def test_definition_eligibility_recipe_projection_and_slice_changes():
    definition = {"recipe": {"algorithm": "v1"}, "eligible": ["A"]}
    before_definition = definition_fingerprint(definition)
    before_binding = eligibility_fingerprint(definition["eligible"])
    before_recipe = recipe_fingerprint(definition["recipe"])
    definition["eligible"].append("B")
    assert definition_fingerprint(definition) != before_definition
    assert eligibility_fingerprint(definition["eligible"]) != before_binding
    assert recipe_fingerprint(definition["recipe"]) == before_recipe
    records = slice_records()
    a = implementation_slice_fingerprint(records, "urn:root")
    recipe_a = recipe_fingerprint(definition["recipe"], implementation_slices=(a,))
    records["nodes"][1]["payload"]["minimum"] = 2
    b = implementation_slice_fingerprint(records, "urn:root")
    assert recipe_fingerprint(definition["recipe"], implementation_slices=(b,)) != recipe_a


def test_opaque_boundary_requires_capture_or_resolved_immutable_contract():
    records = slice_records()
    boundary = {"reference": "math.sqrt", "contract": "python.math.sqrt", "role": "callee"}
    records["boundaries"] = [boundary]
    with pytest.raises(ValueError, match="captured content or resolved contract revision"):
        implementation_slice_fingerprint(records, "urn:root")
    revision = sha256(b"admitted math.sqrt interpretation contract revision").hexdigest()
    boundary["contract"] = "contract:" + revision
    admitted = implementation_slice_fingerprint(records, "urn:root")
    boundary["content_digest"] = sha256(b"captured native implementation").hexdigest()
    assert implementation_slice_fingerprint(records, "urn:root") != admitted
    boundary["content_digest"] = "mutable-name"
    with pytest.raises(ValueError, match="SHA-256"):
        implementation_slice_fingerprint(records, "urn:root")


def test_subject_occurrence_context_order_and_product_provenance_separation():
    args = dict(
        original_source="sha256:source",
        projection="read-v1",
        occurrence="passage/0",
        context={"extent": [0, 3]},
        order=[0],
    )
    first = subject_identity(**args)
    for change in (
        {"occurrence": "passage/1"},
        {"context": {"extent": [3, 6]}},
        {"order": [1]},
        {"projection": "read-v2"},
    ):
        assert subject_identity(**{**args, **change}) != first
    body = body_identity({"text": "equal"})
    product = product_identity(kind="kind:one", subject=first.key, body=body.key)
    # Producing task/execution/recipe do not occur in the product's canonical input.
    assert product_identity(kind="kind:one", subject=first.key, body=body.key) == product
    assert product_identity(kind="kind:two", subject=first.key, body=body.key) != product


def test_provider_projections_are_declaration_roles_and_preserve_execution_details():
    fields = (
        ProfileField("model", "weights-v1", "semantic"),
        ProfileField("threads", 1, "execution"),
        ProfileField("dtype", "float32", "semantic"),
    )
    first = profile_identities(fields)
    changed = profile_identities((fields[0], replace(fields[1], value=8), fields[2]))
    assert first.inference == changed.inference
    assert first.execution != changed.execution
    assert (
        profile_identities((*fields[:2], replace(fields[2], value="float16"))).inference
        != first.inference
    )
    # Thread behavior can be semantic under another explicitly selected policy.
    semantic_threads = (fields[0], replace(fields[1], role="semantic"), fields[2])
    assert profile_identities(semantic_threads).inference != first.inference
    with pytest.raises(ValueError, match="duplicate"):
        profile_identities((fields[0], fields[0]))


def test_request_equivalence_is_separate_from_mutable_admission_and_runtime_custody():
    inputs = {"left": ["product:a"]}
    request = SemanticRequestKey(
        "recipe:a",
        "subject:a",
        inputs,
        {},
        "inference:a",
        subject_context=SubjectContext("project:a", "subject:a", "original:a", b"{}"),
    )
    first_identity = request.identity
    inputs["left"].append("product:b")
    assert request.identity == first_identity
    assert request.inputs["left"] == ("product:a",)
    with pytest.raises(TypeError):
        request.inputs["right"] = ("product:c",)
    with pytest.raises(TypeError):
        request.inputs["left"][0] = "product:c"
    assert (
        SemanticRequestKey(
            "recipe:a",
            "subject:a",
            inputs,
            {},
            "inference:a",
            subject_context=SubjectContext("project:a", "subject:a", "original:a", b"{}"),
        ).identity
        != first_identity
    )
    manifest = AdmissionManifest(
        first_identity.key, "binding:a", ["episode:1"], {"fence": 1}, "execution:a"
    )
    assert manifest.selected_support == ("episode:1",)
    with pytest.raises(TypeError):
        manifest.authorization["fence"] = 2
    assert replace(manifest, selected_support=["episode:2"]).identity != manifest.identity
    assert replace(manifest, binding_revision="binding:b").identity != manifest.identity
    assert request.identity == first_identity
    artifact = runtime_artifact_identity({"executable": "sha256:binary"})
    a = execution_attestation(
        runtime_artifact=artifact.key,
        release="release:a",
        execution_profile="profile:a",
        observed={},
    )
    b = execution_attestation(
        runtime_artifact=artifact.key,
        release="release:b",
        execution_profile="profile:a",
        observed={},
    )
    assert a != b
    assert artifact == runtime_artifact_identity({"executable": "sha256:binary"})


def test_actual_unbound_runtime_cache_consumes_separate_artifact_identity():
    import sys

    from corpus_structure.semantic.runtime_bindings import runtime_fingerprint

    captured = (("module.py", "a" * 64), ("asset", "b" * 64))
    expected = runtime_artifact_identity({"python": sys.version, "inputs": tuple(sorted(captured))})
    assert runtime_fingerprint(digests=captured) == "runtime-code:" + expected.digest
    assert runtime_fingerprint(digests=tuple(reversed(captured))) == runtime_fingerprint(
        digests=captured
    )
    assert runtime_fingerprint(digests=(("module.py", "c" * 64),)) != runtime_fingerprint(
        digests=captured
    )


def test_request_context_is_complete_and_immutable():
    def key(project="project", source="original", scope=b'{"page":1}'):
        return SemanticRequestKey(
            "recipe",
            "local",
            {},
            {},
            "inference",
            subject_context=SubjectContext(project, "local", source, scope),
        ).identity

    assert (
        len(
            {
                key().key,
                key(project="other").key,
                key(source="other").key,
                key(scope=b'{"page":2}').key,
            }
        )
        == 4
    )
    assert key(scope=b'{ "page" : 1 }') == key()
    assert key(scope=b'{"page":1.0}') == key()
    assert key(scope=b'{"page":true}') != key()
    context = SubjectContext("project", "local", "original", b'{"page":1}')
    detached = context.record
    detached["analyzed_scope"]["page"] = 2
    assert context.record["analyzed_scope"] == {"page": 1}
    with pytest.raises(ValueError, match="differs"):
        SemanticRequestKey("recipe", "wrong", {}, {}, "inference", subject_context=context)


def test_subject_context_equality_uses_tagged_json_meaning_not_python_numeric_equality():
    def context(scope):
        return SubjectContext("project", "local", "source", scope)

    integer, decimal = context(b'{"page":1}'), context(b'{"page":1.0}')
    boolean, string = context(b'{"page":true}'), context(b'{"page":"1"}')
    assert integer == decimal and hash(integer) == hash(decimal)
    assert len({integer, decimal, boolean, string}) == 3
    assert integer != boolean and integer != string and integer != object()
