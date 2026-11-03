"""Independent label expectations for released single-root alias compilation."""

import json
from dataclasses import replace

import pytest
import yaml

from corpus_structure.core.vocab import CaseRule
from corpus_structure.evaluate.semantic_alignment import SemanticSide, align_semantic
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.alias_policy import (
    ARTIFACT,
    RULE_INPUT,
    SOURCE_PROFILE,
    label_normalizer,
    released_label_policy,
)
from corpus_structure.semantic.domain_operations import domain_rule_inputs
from corpus_structure.semantic.prepare import prepare_release
from corpus_structure.semantic.regeneration import acquire_pack, compose_pack_inputs, prepare_pack
from corpus_structure.semantic.types import (
    PreparedArtifact,
    ResolvedDependencies,
    SourceArtifact,
    SourceBundle,
)


@pytest.fixture(scope="module")
def statistics_alias_release():
    return prepare_pack(DOMAINS / "statistics")


@pytest.mark.parametrize("content", [b"null", b"[]", b"scalar", b"rules: []\nrules: []"])
def test_malformed_operation_mapping_keeps_structured_preparation_diagnostic(content):
    from corpus_structure.semantic.types import PreparationError

    with pytest.raises(PreparationError) as caught:
        prepare_release(
            SourceBundle("unused", ()), ResolvedDependencies((SourceArtifact(RULE_INPUT, content),))
        )
    assert [(d.code, d.location) for d in caught.value.diagnostics] == [
        ("operation_rules", RULE_INPUT)
    ]


def test_composed_contexts_do_not_silently_discard_a_global_policy():
    from corpus_structure.semantic.alias_policy import compile_alias_policy

    with pytest.raises(ValueError, match="mutually exclusive"):
        compile_alias_policy(
            SourceBundle("unused", ()),
            (),
            {
                "alias_profile": SOURCE_PROFILE,
                "aliases": {"articles": ["the"]},
                "alias_contexts": [{"origin": "other", "aliases": {}}],
            },
            lambda name: name,
        )


def test_statistics_aliases_have_one_released_full_iri_meaning(statistics_alias_release):
    prepared = statistics_alias_release[-1]
    normalize = label_normalizer(prepared)
    family = "https://corpus-structure.dev/domains/statistics/DistributionFamily"
    assert normalize("the Normal distributions", family) == "normal"
    assert normalize("normally distributed", family) == "normal"
    assert normalize("gamma distributed", family) == "gamma"
    # Articles and rewrites remain pack-global, including imported core classes.
    core = "http://www.w3.org/ns/prov#Entity"
    assert normalize("the Normal distributions", core) == "normal distributions"
    assert normalize("normally distributed", core) == "normal"
    assert normalize("the Normal distributions", family, CaseRule.PRESERVE) == "Normal"
    assert normalize("distribution", family) == "distribution"  # never emptied
    product = json.loads(next(a.content for a in prepared.artifacts if a.kind == ARTIFACT))
    assert family in product["classes"]
    assert product["classes"][family]["head_words"] == {family: ["distribution", "distributions"]}
    assert label_normalizer(prepared)("the Claim", "__statement__") == "claim"


def test_alignment_uses_the_released_statistics_policy(statistics_alias_release):
    prepared = statistics_alias_release[-1]
    family = "https://corpus-structure.dev/domains/statistics/DistributionFamily"
    reference = SemanticSide(
        "unit", {"entities": [{"id": "r", "class_iri": family, "label": "Normal"}], "claims": []}
    )
    prediction = SemanticSide(
        "unit",
        {
            "entities": [{"id": "p", "class_iri": family, "label": "the Normal distribution"}],
            "claims": [],
        },
    )
    result = align_semantic(reference, prediction, prepared)
    assert result.entity_pairs == [("r", "p", "alias_normalization")]


def small_inputs(seed, name, *, aliases=None, rules=b"rules: []"):
    schema = {
        "id": f"https://example.org/{name}",
        "name": name,
        "imports": ["semantic_core"],
        "default_prefix": name,
        "prefixes": {name: f"https://example.org/{name}/"},
        "classes": {name.title(): {"is_a": "Entity"}},
    }
    core = next(s for s in seed.bundle.sources if s.name == "semantic_core")
    return replace(
        seed,
        origin=f"pack:{name}",
        name=name,
        bundle=SourceBundle(name, (core, SourceArtifact(name, yaml.safe_dump(schema).encode()))),
        dependencies=domain_rule_inputs(ResolvedDependencies(), rules, aliases=aliases or {}),
        qualifications=(),
        statements=(),
    )


def test_compatible_packs_coalesce_policy_without_order_winners(statistics_alias_release):
    seed = acquire_pack(DOMAINS / "statistics")
    a = small_inputs(
        seed, "alpha", aliases={"articles": ["the"], "head_words": {"Alpha": ["kind"]}}
    )
    b = small_inputs(
        seed, "beta", aliases={"articles": ["the"], "head_words": {"beta:Beta": ["sort"]}}
    )
    products = []
    for acquired in ((a, b), (b, a)):
        bundle, deps, profile = compose_pack_inputs(acquired)
        prepared = prepare_release(bundle, deps, profile)
        normalize = label_normalizer(prepared)
        assert normalize("the Amber kind", "https://example.org/alpha/Alpha") == "amber"
        assert normalize("the Blue sort", "https://example.org/beta/Beta") == "blue"
        assert normalize("the Amber sort", "https://example.org/alpha/Alpha") == "amber sort"
        assert normalize("the Core kind", "http://www.w3.org/ns/prov#Entity") == "core kind"
        assert any(a.kind == RULE_INPUT for a in prepared.artifacts)
        products.append(
            json.loads(next(a.content for a in prepared.artifacts if a.kind == ARTIFACT))
        )
    assert products[0] == products[1]


def test_shared_class_alias_conflict_and_nonalias_policy_refuse_with_origins():
    seed = acquire_pack(DOMAINS / "statistics")
    a = small_inputs(seed, "alpha", aliases={"articles": ["the"]})
    b = small_inputs(seed, "beta", aliases={"articles": ["a"]})
    bundle, deps, profile = compose_pack_inputs((a, b))
    with pytest.raises(ValueError, match=r"conflicting alias policy.*alpha.*beta"):
        prepare_release(bundle, deps, profile)
    b = small_inputs(seed, "beta", rules=b"rules: []\nguideline: different")
    with pytest.raises(ValueError, match=r"incompatible non-alias.*pack:alpha.*pack:beta"):
        compose_pack_inputs((a, b))
    b = small_inputs(seed, "beta", aliases={"articles": ["the"]})
    sources = list(b.bundle.sources)
    schema = yaml.safe_load(sources[-1].content)
    schema["prefixes"]["alpha"] = "https://different.example/"
    sources[-1] = replace(sources[-1], content=yaml.safe_dump(schema).encode())
    b = replace(b, bundle=replace(b.bundle, sources=tuple(sources)))
    with pytest.raises(ValueError, match="conflicting prefix alpha"):
        compose_pack_inputs((a, b))


def test_rewrite_order_source_namespace_and_duplicate_full_iri_policy(statistics_alias_release):
    from corpus_structure.semantic.alias_policy import compile_alias_policy

    prepared = statistics_alias_release[-1]
    family = "https://corpus-structure.dev/domains/statistics/DistributionFamily"
    aliases = {
        "articles": ["the"],
        "head_words": {"DistributionFamily": ["kind"], "stat:DistributionFamily": ["kind"]},
        "rewrites": [{"match": "^red", "replace": "amber"}, {"match": "^amber", "replace": "blue"}],
    }
    product = compile_alias_policy(
        statistics_alias_release[0],
        prepared.definitions,
        {"alias_profile": SOURCE_PROFILE, "aliases": aliases},
        prepared.expand_name,
    )
    released = replace(
        prepared,
        artifacts=tuple(
            replace(a, content=product) if a.kind == ARTIFACT else a for a in prepared.artifacts
        ),
    )
    assert label_normalizer(released)("the red kind", family) == "blue"
    borrowed = released_label_policy(released, family)
    borrowed.head_words[family] = ("blue",)
    assert label_normalizer(released)("the red kind", family) == "blue"
    aliases["head_words"]["stat:DistributionFamily"] = ["sort"]
    with pytest.raises(ValueError, match="conflicting alias spellings"):
        compile_alias_policy(
            statistics_alias_release[0],
            prepared.definitions,
            {"alias_profile": SOURCE_PROFILE, "aliases": aliases},
            prepared.expand_name,
        )
    aliases["head_words"] = {"missing:Class": ["kind"]}
    with pytest.raises((ValueError, KeyError), match="missing:Class"):
        compile_alias_policy(
            statistics_alias_release[0],
            prepared.definitions,
            {"alias_profile": SOURCE_PROFILE, "aliases": aliases},
            prepared.expand_name,
        )


def test_profile_identity_and_synthetic_hydration_execution_boundary(statistics_alias_release):
    from corpus_structure.semantic.archive_reader import reconstruct_release
    from corpus_structure.semantic.releases import _products

    bundle, deps, profile, prepared = statistics_alias_release
    artifact = next(a for a in deps.artifacts if a.name == RULE_INPUT)
    old_policy = yaml.safe_load(artifact.content)
    assert old_policy["identity"].pop("alias_profile") == SOURCE_PROFILE
    old_content = yaml.safe_dump(old_policy).encode()
    old_deps = replace(
        deps,
        artifacts=tuple(
            replace(a, content=old_content) if a.name == RULE_INPUT else a for a in deps.artifacts
        ),
    )
    with pytest.raises(ValueError, match="nonempty unversioned alias policy requires regeneration"):
        prepare_release(bundle, old_deps, profile)
    changed_policy = yaml.safe_load(artifact.content)
    changed_policy["identity"]["aliases"]["head_words"]["DistributionFamily"] = ["family"]
    changed_deps = replace(
        deps,
        artifacts=tuple(
            replace(a, content=yaml.safe_dump(changed_policy).encode())
            if a.name == RULE_INPUT
            else a
            for a in deps.artifacts
        ),
    )
    changed = prepare_release(bundle, changed_deps, profile)
    assert changed.release_id != prepared.release_id
    assert (
        label_normalizer(changed)(
            "the normal distribution",
            "https://corpus-structure.dev/domains/statistics/DistributionFamily",
        )
        == "normal distribution"
    )
    # Synthetic low-level hydration control: these replaced products deliberately retain
    # the current manifest, so this is not a coherent historical archive/opening receipt.
    # Hydrating compiler-14-shaped products does not execute aliases; requesting their
    # new meaning refuses. Full archive compatibility has separate native controls.
    old = replace(
        prepared,
        artifacts=(
            *(a for a in prepared.artifacts if a.kind not in {ARTIFACT, RULE_INPUT}),
            PreparedArtifact(RULE_INPUT, old_content),
        ),
    )
    archived = reconstruct_release(_products(old), old.manifest, bundle, profile, old.artifacts)
    assert archived.release_id == old.release_id
    with pytest.raises(ValueError, match="regeneration and admission"):
        released_label_policy(
            archived, "https://corpus-structure.dev/domains/statistics/DistributionFamily"
        )
    neutral = replace(old, artifacts=tuple(a for a in old.artifacts if a.kind != RULE_INPUT))
    assert (
        label_normalizer(neutral)("the Normal distribution", "anything")
        == "the normal distribution"
    )
