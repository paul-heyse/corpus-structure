"""Compile pack-relative label policy once; consumers use its immutable release product."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from functools import lru_cache
from typing import TYPE_CHECKING, Any

import yaml

from corpus_structure.core.keys import LabelRules, normalize_label
from corpus_structure.core.vocab import CaseRule

from .identity import canonical_bytes

if TYPE_CHECKING:
    from .types import ClassDefinition, PreparedRelease, SourceBundle

SOURCE_PROFILE = "class-alias-input-1"
PROFILE = "class-iri-aliases-1"
ARTIFACT = "operation/alias-policy.json"
RULE_INPUT = "operation/domain-rules.yaml"


def compile_alias_policy(
    bundle: SourceBundle,
    definitions: tuple[ClassDefinition, ...],
    identity: Mapping[str, Any],
    expand_name: Callable[[str], str],
) -> bytes | None:
    """Resolve contexts using the root compiler's validated definitions and supplied bytes.

    Parsing source ownership/imports does not prepare component schemas. Full class IRIs come
    exclusively from the already prepared definitions, including explicit class_uri overrides.
    """
    if set(identity) - {"alias_profile", "aliases", "alias_contexts"}:
        raise ValueError("unknown alias input field")
    profile = identity.get("alias_profile")
    if profile is None:
        if "alias_contexts" in identity:
            raise ValueError("alias contexts require a versioned input profile")
        if LabelRules.model_validate(identity.get("aliases", {})) != LabelRules():
            raise ValueError("nonempty unversioned alias policy requires regeneration")
        return None
    if profile != SOURCE_PROFILE:
        raise ValueError("unsupported alias input profile")
    contexts = identity.get("alias_contexts")
    if contexts is not None and "aliases" in identity:
        raise ValueError("aliases and alias_contexts are mutually exclusive")
    if contexts is None:
        contexts = [{"origin": bundle.root, "aliases": identity.get("aliases", {})}]
    if not isinstance(contexts, list) or not contexts:
        raise ValueError("alias contexts must be a nonempty list")
    classes = {d.name: d.iri for d in definitions}
    documents = {source.name: yaml.safe_load(source.content) for source in bundle.sources}
    policies: dict[str, dict[str, Any]] = {}
    origins: dict[str, list[str]] = {}
    for context in contexts:
        if not isinstance(context, dict) or set(context) - {"origin", "root", "aliases"}:
            raise ValueError("invalid alias context")
        origin = context.get("origin")
        if not isinstance(origin, str) or not origin:
            raise ValueError("alias context requires an origin")
        root = context.get("root")
        visible = set(classes)
        if root is not None:
            closure: set[str] = set()
            pending = [root]
            while pending:
                name = pending.pop()
                if name in closure:
                    continue
                if name not in documents:
                    raise ValueError(f"{origin}: unresolved alias source {name}")
                closure.add(name)
                pending.extend(documents[name].get("imports", ()))
            visible = {name for module in closure for name in documents[module].get("classes", {})}
        visible_iris = {classes[name] for name in visible}
        rules = LabelRules.model_validate(context.get("aliases", {}))
        heads: dict[str, tuple[str, ...]] = {}
        for key, words in rules.head_words.items():
            if key in visible:
                iri = classes[key]
            elif key in visible_iris:
                iri = key
            else:
                iri = expand_name(key)
            if iri not in visible_iris:
                raise ValueError(f"{origin}: alias class is not in its source closure: {key}")
            if iri in heads and heads[iri] != words:
                raise ValueError(f"{origin}: conflicting alias spellings for {iri}")
            heads[iri] = words
        for iri in sorted(visible_iris):
            policy = {
                "articles": list(rules.articles),
                "head_words": {iri: list(heads.get(iri, ()))},
                "rewrites": [r.model_dump(mode="json") for r in rules.rewrites],
            }
            if iri in policies and policies[iri] != policy:
                raise ValueError(f"conflicting alias policy for {iri}: {origins[iri]} and {origin}")
            policies[iri] = policy
            origins.setdefault(iri, []).append(origin)
    return canonical_bytes(
        {
            "profile": PROFILE,
            "classes": policies,
            "origins": {k: sorted(set(v)) for k, v in origins.items()},
        }
    )


@lru_cache(maxsize=32)
def _released_policy(content: bytes) -> Mapping[str, LabelRules]:
    product = json.loads(content)
    if set(product) != {"profile", "classes", "origins"} or product["profile"] != PROFILE:
        raise ValueError("unsupported released alias profile; regenerate and admit the release")
    return {iri: LabelRules.model_validate(policy) for iri, policy in product["classes"].items()}


def _released_content(prepared: PreparedRelease) -> bytes | None:
    artifacts = [a for a in prepared.artifacts if a.kind == ARTIFACT]
    if len(artifacts) == 1:
        return artifacts[0].content
    if artifacts:
        raise ValueError("release repeats its alias policy")
    source = next((a for a in prepared.artifacts if a.kind == RULE_INPUT), None)
    identity = yaml.safe_load(source.content).get("identity", {}) if source else {}
    if (
        identity.get("alias_profile")
        or "alias_contexts" in identity
        or LabelRules.model_validate(identity.get("aliases", {})) != LabelRules()
    ):
        raise ValueError("released alias policy requires regeneration and admission")
    # An absent/empty policy already declared no label transformations. This is not
    # a compatibility interpretation of an old nonempty policy.
    return None


def released_label_policy(prepared: PreparedRelease, class_iri: str) -> LabelRules:
    """Use declared released meaning; old nonempty aliases never acquire new interpretation."""
    content = _released_content(prepared)
    if content is None:
        return LabelRules()
    if class_iri == "__statement__":
        from .statement_types import statement_definition

        class_iri = statement_definition(prepared).iri
    # Do not lend the cached policy's nested mutable head-word mapping to callers.
    try:
        return _released_policy(content)[class_iri].model_copy(deep=True)
    except KeyError:
        raise ValueError(f"released alias policy has no class {class_iri}") from None


def label_normalizer(prepared: PreparedRelease) -> Callable[..., str]:
    """Bind one released artifact lifetime for an identity/alignment operation."""
    content = _released_content(prepared)
    policies = _released_policy(content) if content is not None else None
    neutral = LabelRules()

    def normalize(text: str, iri: str, case: CaseRule = CaseRule.FOLD) -> str:
        if policies is None:
            return normalize_label(text, iri, neutral, case)
        if iri == "__statement__":
            from .statement_types import statement_definition

            iri = statement_definition(prepared).iri
        if iri not in policies:
            raise ValueError(f"released alias policy has no class {iri}")
        return normalize_label(text, iri, policies[iri], case)

    return normalize
