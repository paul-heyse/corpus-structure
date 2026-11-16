"""Immutable document characterization, distinct from scientific admission.

LinkML owns boundary shapes and attachment-basis constraints. This module owns graph,
identity and closure invariants; reading projection performs no inference.
Current inventories use semantic product/member references.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from .identity import canonical_bytes
from .product_reference import ProductReference
from .types import (
    PreparationProfile,
    PreparedArtifact,
    PreparedRelease,
    SourceArtifact,
    SourceBundle,
)

if TYPE_CHECKING:
    from .data_product_reference import DataProductMemberReference, DataProductReference
    from .declared_formal_readings import DeclaredFormalInventory

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/characterization.yaml"
_INVENTORIES = ("occurrences", "annotations", "memberships", "roles", "terms", "choices")
_POLICY_ARTIFACT = "characterization/attachment-policies.json"


def characterization_inputs(
    bundle: SourceBundle,
    *,
    model_content: bytes | None = None,
    profile: PreparationProfile | None = None,
) -> SourceBundle:
    """Acquire and archive the trusted declaration; reserved names cannot be substituted."""
    content = _construction_model(_MODEL.read_bytes()) if model_content is None else model_content
    names = {source.name for source in bundle.sources}
    if "observations" not in names:
        from .observations import observation_inputs

        bundle = observation_inputs(bundle, profile=profile)
        names = {source.name for source in bundle.sources}
    if names & {"characterization", "characterization-root"}:
        from .prepare import _view

        module = next((s for s in bundle.sources if s.name == "characterization"), None)
        if (
            module is not None
            and module.content == content
            and "CharacterizationAttachmentBasis" in _view(bundle, profile).all_classes()
        ):
            return bundle
        raise ValueError("reserved characterization module supplied with another meaning")
    return SourceBundle(
        "characterization-root",
        (
            *bundle.sources,
            SourceArtifact("characterization", content),
            SourceArtifact(
                "characterization-root",
                yaml.safe_dump(
                    {
                        "id": "https://corpus-structure.dev/semantic/characterization-root",
                        "name": "semantic_characterization_root",
                        "imports": [bundle.root, "characterization"],
                    }
                ).encode(),
            ),
        ),
    )


def _construction_model(content: bytes) -> bytes:
    """Freeze ordinary authored declarations into the archived trusted model input."""
    from corpus_structure.methods.native_evidence_layers import HANLP_FAMILIES, SPACY_FAMILIES

    from .constructions.declarations import DECLARATIONS
    from .constructions.declarations import FAMILIES as construction_families
    from .constructions.evaluation import EVALUATION_FAMILIES
    from .constructions.math_scope import FAMILY as math_scope_family
    from .constructions.navigation import FAMILY as navigation_family
    from .constructions.retained_declarations import DECLARATION_FAMILY
    from .contextual_characterization import CONTEXT_FAMILIES
    from .formal_evidence import FAMILIES as formal_families
    from .interpretation_questions import CHARACTERIZATION_FAMILIES

    model = yaml.safe_load(content)
    model["classes"]["CharacterizationFullProfile"] = {
        "is_a": "SourceRecordProduct",
        "attributes": {
            "profile_name": {"equals_string": "full_characterization"},
            "required_families": {
                "equals_string": "|".join(
                    (
                        *SPACY_FAMILIES,
                        *HANLP_FAMILIES,
                        *formal_families,
                        *construction_families,
                        navigation_family,
                        DECLARATION_FAMILY,
                        math_scope_family,
                        *CONTEXT_FAMILIES,
                        *CHARACTERIZATION_FAMILIES,
                        *EVALUATION_FAMILIES,
                    )
                )
            },
        },
    }
    for declaration in DECLARATIONS.values():
        model["classes"]["CharacterizationRule_" + declaration.name] = {
            "is_a": "CharacterizationConstructionBasis",
            "attributes": {
                "kind": {"equals_string": "released_construction", "required": True},
                "rule_id": {"equals_string": declaration.rule_id, "required": True},
                "construction": {"range": "string", "required": True, "pattern": "^.+$"},
                "binding": {"range": "string", "required": True, "pattern": "^.+$"},
                "production": {"range": "string", "required": True, "pattern": "^.+$"},
                "support_codec": {"equals_string": "construction-membership-v1"},
                "production_name": {"equals_string": "prose__" + declaration.name},
                "support_roles": {"equals_string": "|".join(declaration.roles)},
            },
        }
    return yaml.safe_dump(model, sort_keys=False).encode()


def compile_attachment_policies(definitions) -> PreparedArtifact | None:
    """Compile subtype dispatch from the released declaration, not installed policy code."""
    policies = {}
    rules = {}
    for definition in definitions:
        if "CharacterizationAttachmentBasis" not in definition.ancestors:
            continue
        kind = next((p.equals_string for p in definition.properties if p.name == "kind"), None)
        rule = next((p.equals_string for p in definition.properties if p.name == "rule_id"), None)
        entry = {"class_name": definition.name, "schema_kind": f"json_schema/{definition.name}"}
        if rule is not None:
            if kind != "released_construction" or rule in rules:
                raise ValueError(
                    "released attachment rule requires a distinct construction rule identity"
                )
            rules[rule] = entry
            fixed = {
                p.name: p.equals_string
                for p in definition.properties
                if p.equals_string is not None
            }
            if fixed.get("support_codec") == "construction-membership-v1":
                entry["support"] = {
                    "codec": fixed["support_codec"],
                    "production": fixed["production_name"],
                    "roles": fixed["support_roles"].split("|"),
                }
        else:
            if not kind or kind in policies:
                raise ValueError("attachment basis subtype requires a distinct fixed kind")
            policies[kind] = entry
    if not policies:
        return None
    if "released_construction" in policies:
        policies["released_construction"]["rules"] = rules
    return PreparedArtifact(_POLICY_ARTIFACT, canonical_bytes(policies))


def compile_characterization_profiles(definitions):
    profiles = {}
    for definition in definitions:
        if definition.name == "CharacterizationFullProfile":
            fixed = {p.name: p.equals_string for p in definition.properties}
            profiles[fixed["profile_name"]] = fixed["required_families"].split("|")
    return (
        PreparedArtifact("characterization/profiles.json", canonical_bytes(profiles))
        if profiles
        else None
    )


def characterization_profiles(prepared):
    artifact = next(
        (a for a in prepared.artifacts if a.kind == "characterization/profiles.json"), None
    )
    return json.loads(artifact.content) if artifact is not None else {}


def attachment_policies(prepared: PreparedRelease) -> dict[str, Any]:
    artifact = next((a for a in prepared.artifacts if a.kind == _POLICY_ARTIFACT), None)
    if artifact is None:
        raise ValueError("release has no characterization attachment policy")
    return json.loads(artifact.content)


def occurrence_id(
    source: Mapping[str, Any], extents: Sequence[Mapping[str, Any]]
) -> str:
    """Stable across analyses and database placement, different at repeated native addresses."""
    return sha256(canonical_bytes({"base_document": dict(source), "extents": list(extents)})).hexdigest()


@dataclass(frozen=True, slots=True)
class AnnotationReference:
    layer: ProductReference
    local_id: str

    def __post_init__(self):
        if type(self.local_id) is not str or not self.local_id:
            raise ValueError("annotation reference requires a local ID")

    @property
    def product(self) -> ProductReference:
        return self.layer

    @property
    def member_id(self) -> str:
        return self.local_id

    def values(self) -> dict[str, Any]:
        return {"layer": self.layer.values(), "local_id": self.local_id}

    @property
    def identity(self) -> str:
        return "annotation:" + sha256(canonical_bytes(self.values())).hexdigest()


def _acyclic(edges: Mapping[str, Sequence[str]], label: str) -> None:
    from .graph_runtime import nx
    from .graph_topology import cyclic_components

    graph = nx.DiGraph(backend="networkx")
    graph.add_nodes_from(edges)
    graph.add_edges_from(
        (source, target) for source, targets in edges.items() for target in targets
    )
    if cyclic_components(graph):
        raise ValueError(f"{label} structural cycle")


def validate_inventory_graph(data, indexes, all_nodes, choice_members, validate_basis):
    """Local source, score, structural and choice invariants for current inventories."""
    from .observations import source_python

    for occurrence in data["occurrences"]:
        for extent in occurrence.get("extents", ()):
            if not extent.get("synthetic", False) and "start" in extent and extent["end"] <= extent["start"]:
                raise ValueError("literal source occurrence requires a nonempty extent")
    for name in _INVENTORIES[1:]:
        for item in data[name]:
            records = (item, *item["members"]) if name == "choices" else (item,)
            for record in records:
                for score in record.get("scores", ()):
                    value = source_python(score["value"])
                    if value is not None and type(value) not in {int, float}:
                        raise ValueError("native score requires an exact numeric source value or explicit null")

    def refs(values, index, label):
        if any(value not in index for value in values):
            raise ValueError(f"dangling {label} reference")

    structural = {key: [] for key in all_nodes}
    for name in ("annotations", "memberships", "roles", "terms"):
        for item in data[name]:
            refs(item.get("occurrences", ()), indexes["occurrences"], "occurrence")
            refs(item.get("premises", ()), all_nodes, "premise")
            refs(item.get("required_choices", ()), choice_members, "required choice")
            if name == "memberships":
                refs((item["group"], item["member"]), all_nodes, "membership")
                if item["structural"]:
                    structural[item["group"]].append(item["member"])
            elif name == "roles":
                refs((item["owner"], item["member"]), all_nodes, "role")
                basis = item["basis"]
                policy = validate_basis(basis)
                if policy and policy.get("support"):
                    _validate_construction_support(item, all_nodes, policy["support"])
                refs(basis.get("premises", ()), all_nodes, "attachment premise")
                refs(basis.get("choice_refs", ()), choice_members, "attachment choice")
            elif name == "terms":
                refs(item.get("required_choices", ()), choice_members, "term choice")
                for edge in item.get("children", ()):
                    if ("target" in edge) == ("choice_group" in edge):
                        raise ValueError("term child requires exactly one target or choice site")
                    target = edge.get("target", edge.get("choice_group"))
                    refs(
                        (target,),
                        indexes["terms"] if "target" in edge else indexes["choices"],
                        "term/site",
                    )
                    if not edge["structural"]:
                        raise ValueError(
                            "semantic term children must be structural; "
                            "use role assertions for referential relations"
                        )
                    structural[item["local_id"]].append(target)
                if item["kind"] == "binder" and not {"variable", "restrictor", "body"} <= {
                    e["role"] for e in item.get("children", ())
                }:
                    raise ValueError("binder requires explicit variable, restrictor and body")
    for group in data["choices"]:
        for member in group["members"]:
            refs((member["root"],), indexes["terms"], "choice root")
            refs(member.get("premises", ()), all_nodes, "choice premise")
            refs(member.get("required_choices", ()), choice_members, "required choice")
            structural[group["local_id"]].append(member["root"])
    _acyclic(structural, "term/containment")
    choice_edges = {
        m["local_id"]: m.get("required_choices", ()) for g in data["choices"] for m in g["members"]
    }
    _acyclic(choice_edges, "choice dependency")


def _reading_product(value: Mapping[str, Any]) -> DataProductReference:
    from .data_product_reference import DataProductReference

    return DataProductReference(**value)


def _reading_dependency(
    dependencies: Mapping[DataProductReference, DeclaredFormalInventory], pin: DataProductReference
) -> DeclaredFormalInventory:
    report = dependencies.get(pin)
    if report is None or report.reference != pin:
        raise ValueError("reading requires its exact nominal dependency closure")
    return report


def _reading_source(payload):
    return canonical_bytes(payload["source"]), canonical_bytes(payload["selectors"])


def project_reading(
    layer: DeclaredFormalInventory,
    root: str,
    *,
    choices: Sequence[str] = (),
    dependencies: Mapping[DataProductReference, DeclaredFormalInventory] | None = None,
    external_choices: Sequence[DataProductMemberReference] = (),
) -> dict[str, Any]:
    """Bounded supported DAG projection; unknown compatibility never creates combinations."""
    from .data_product_reference import DataProductMemberReference
    from .declared_formal_readings import DeclaredFormalInventory

    if not isinstance(layer, DeclaredFormalInventory):
        raise ValueError("reading requires a current nominal inventory")
    if any(not isinstance(ref, DataProductMemberReference) for ref in external_choices):
        raise ValueError("reading requires current semantic member choices")
    data = layer.payload
    dependencies = dependencies or {}
    terms = {t["local_id"]: t for t in data["terms"]}
    members = {m["local_id"]: (g, m) for g in data["choices"] for m in g["members"]}
    selected = set(validate_reading_choices(data, choices))
    external = {(ref.product, ref.member_id) for ref in external_choices}
    if len(external) != len(external_choices):
        raise ValueError("duplicate qualified analytical choice")
    # Only the actual dependency closure can supply upstream selections. A caller's
    # larger report cache is not authority to introduce an unrelated reading.
    reachable = set()
    pending_dependencies = [_reading_product(value) for value in data.get("dependencies", ())]
    while pending_dependencies:
        pin = pending_dependencies.pop()
        if pin in reachable:
            continue
        report = _reading_dependency(dependencies, pin)
        if _reading_source(report.payload) != _reading_source(data):
            raise ValueError("reading dependency belongs to a different source document")
        reachable.add(pin)
        pending_dependencies.extend(
            _reading_product(value) for value in report.payload.get("dependencies", ())
        )
    by_layer = {}
    for pin, identity in external:
        if pin not in reachable:
            raise ValueError("qualified choice is outside the reading dependency closure")
        _reading_dependency(dependencies, pin)
        by_layer.setdefault(pin, []).append(identity)
    for pin, identities in by_layer.items():
        body = _reading_dependency(dependencies, pin).payload
        validate_reading_choices(body, identities)
        for group in body["choices"]:
            for member in group["members"]:
                if member["local_id"] in identities:
                    _require_external_selection(member, external)
    for key in selected:
        _require_external_selection(members[key][1], external)
    found = set()
    unresolved = []
    groups = {g["local_id"]: g for g in data["choices"]}
    pending = [root]
    while pending:
        key = pending.pop()
        if key not in terms:
            raise ValueError("unknown reading root")
        if key in found:
            continue
        term = terms[key]
        if not set(term.get("required_choices", ())) <= selected:
            raise ValueError("reading requires an unselected analytical choice")
        _require_external_selection(term, external)
        found.add(key)
        for edge in term.get("children", ()):
            if "target" in edge:
                pending.append(edge["target"])
                continue
            group = groups[edge["choice_group"]]
            chosen = [m for m in group["members"] if m["local_id"] in selected]
            if len(chosen) > 1:
                raise ValueError("single-valued choice site requires exactly one member")
            if not chosen:
                unresolved.append(
                    {"owner": key, "role": edge["role"], "choice_group": group["local_id"]}
                )
            else:
                _require_external_selection(chosen[0], external)
                pending.append(chosen[0]["root"])
    for key in selected:
        if members[key][1]["root"] not in found:
            raise ValueError("selected analytical choice does not support reading root")
    # A selected upstream member requires its actual term/site closure, not just
    # the member record. Several independent roots may share one layer selection.
    visited = set()
    pending_support = [
        (pin, m["root"])
        for pin, identities in by_layer.items()
        for g in _reading_dependency(dependencies, pin).payload["choices"]
        for m in g["members"]
        if m["local_id"] in identities
    ]
    while pending_support:
        pin, key = pending_support.pop()
        if (pin, key) in visited:
            continue
        visited.add((pin, key))
        body = _reading_dependency(dependencies, pin).payload
        term = next((t for t in body["terms"] if t["local_id"] == key), None)
        if term is None:
            raise ValueError("selected upstream choice has no supported root")
        available = set(by_layer.get(pin, ()))
        if not set(term.get("required_choices", ())) <= available:
            raise ValueError("upstream reading requires an unselected analytical choice")
        _require_external_selection(term, external)
        for edge in term.get("children", ()):
            if "target" in edge:
                pending_support.append((pin, edge["target"]))
            else:
                group = next(g for g in body["choices"] if g["local_id"] == edge["choice_group"])
                chosen = [m for m in group["members"] if m["local_id"] in available]
                if len(chosen) > 1:
                    raise ValueError("upstream single-valued site requires exactly one member")
                if not chosen:
                    unresolved.append(
                        dict(
                            layer=pin.values(),
                            owner=key,
                            role=edge["role"],
                            choice_group=group["local_id"],
                        )
                    )
                else:
                    _require_external_selection(chosen[0], external)
                    pending_support.append((pin, chosen[0]["root"]))
    return {
        "root": root,
        "choices": sorted(selected),
        "terms": [t for t in data["terms"] if t["local_id"] in found],
        "outcome": "partial" if unresolved else "complete",
        "unresolved_sites": unresolved,
        "external_choices": [ref.values() for ref in external_choices],
    }


def _require_external_selection(record, selected):
    from .data_product_reference import read_member_reference

    if any(
        (ref.product, ref.member_id) not in selected
        for raw in record.get("required_external_choices", ())
        for ref in (read_member_reference(raw),)
    ):
        raise ValueError("reading requires an unselected qualified analytical choice")


def _validate_construction_support(role, nodes, support):
    if support["codec"] != "construction-membership-v1":
        raise ValueError("unsupported released construction support codec")
    basis = role["basis"]
    construction = nodes.get(basis["construction"], {})
    binding = nodes.get(basis["binding"], {})
    production = nodes.get(basis["production"], {})
    required = {basis["construction"], basis["binding"], basis["production"]}
    member = nodes.get(role["member"], {})
    choice_requirements = set().union(
        *(
            set(node.get("required_choices", ()))
            for node in (construction, binding, production, member, basis)
        )
    )
    external_requirements = {
        canonical_bytes(ref)
        for node in (construction, binding, production, member, basis)
        for ref in node.get("required_external_choices", ())
    }
    if not (
        required <= set(basis.get("premises", ()))
        and construction.get("kind") == "construction"
        and construction.get("rule_id") == basis["rule_id"]
        and role["owner"] == basis["construction"]
        and binding.get("group") == basis["construction"]
        and binding.get("member") == role["member"]
        and binding.get("role") == role["role"]
        and role["role"] in support["roles"]
        and basis["production"] in construction.get("premises", ())
        and production.get("kind") == "grammar.production"
        and production.get("native_label") == support["production"]
        and role.get("occurrences", ()) == binding.get("occurrences", ())
        and set(binding.get("occurrences", ())) <= set(member.get("occurrences", ()))
        and choice_requirements <= set(role.get("required_choices", ()))
        and set(role.get("required_choices", ())) == set(basis.get("choice_refs", ()))
        and external_requirements
        <= {canonical_bytes(ref) for ref in role.get("required_external_choices", ())}
    ):
        raise ValueError("attachment endpoints differ from released construction witness")
    reached = set()
    pending = list(production.get("premises", ()))
    while pending:
        key = pending.pop()
        if key in reached:
            continue
        reached.add(key)
        pending.extend(nodes.get(key, {}).get("premises", ()))
    if role["member"] not in reached:
        raise ValueError("attachment member is outside witnessed production")


def validate_reading_choices(payload: Mapping[str, Any], choices: Sequence[str]) -> tuple[str, ...]:
    """Validate an explicit compatible selection; never invent missing premises."""
    if len(set(choices)) != len(choices):
        raise ValueError("duplicate analytical choice")
    members = {m["local_id"]: (g, m) for g in payload.get("choices", ()) for m in g["members"]}
    selected = set(choices)
    groups = {}
    for key in choices:
        if key not in members:
            raise ValueError("unknown analytical choice")
        group, member = members[key]
        if not set(member.get("required_choices", ())) <= selected:
            raise ValueError("analytical choice requires missing choices")
        groups.setdefault(group["local_id"], []).append(key)
        if len(groups[group["local_id"]]) > 1 and group["compatibility"] != "compatible":
            raise ValueError("incompatible or unknown analytical choice combination")
    return tuple(sorted(selected))


def validate_released_attachment_rule(
    basis: Mapping[str, Any], policies: Mapping[str, Any], validate_schema
) -> None:
    """A witnessed rule must resolve to a released rule, never an arbitrary producer label."""
    if basis["kind"] != "released_construction":
        return
    rule = policies["released_construction"].get("rules", {}).get(basis.get("rule_id"))
    if rule is None:
        raise ValueError("witnessed construction requires a released attachment rule")
    validate_schema(rule["class_name"], basis)


def validate_attachment_basis(
    basis: Mapping[str, Any], policies: Mapping[str, Any], validate_schema
) -> None:
    """One mechanical policy dispatch for live validation and detached replay."""
    policy = policies.get(basis["kind"])
    if policy is None:
        raise ValueError("undeclared attachment basis")
    validate_schema(policy["class_name"], basis)
    validate_released_attachment_rule(basis, policies, validate_schema)
