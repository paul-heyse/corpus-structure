"""Immutable document characterization, distinct from scientific admission.

LinkML owns boundary shapes and attachment-basis constraints. This module owns graph,
identity and closure invariants; neither codec nor read projection performs inference.
Local references become globally qualified only after the containing layer is pinned.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from .identity import canonical_bytes
from .product_reference import ProductReference
from .types import PreparedArtifact, PreparedRelease, SourceArtifact, SourceBundle

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/characterization.yaml"
_INVENTORIES = ("occurrences", "annotations", "memberships", "roles", "terms", "choices")
_POLICY_ARTIFACT = "characterization/attachment-policies.json"


def characterization_inputs(
    bundle: SourceBundle, *, model_content: bytes | None = None
) -> SourceBundle:
    """Acquire and archive the trusted declaration; reserved names cannot be substituted."""
    content = _construction_model(_MODEL.read_bytes()) if model_content is None else model_content
    names = {source.name for source in bundle.sources}
    if "observations" not in names:
        from .observations import observation_inputs

        bundle = observation_inputs(bundle)
        names = {source.name for source in bundle.sources}
    if names & {"characterization", "characterization-root"}:
        from .prepare import _view

        module = next((s for s in bundle.sources if s.name == "characterization"), None)
        if (
            module is not None
            and module.content == content
            and "AnnotationLayer" in _view(bundle).all_classes()
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


def _pin(value: Mapping[str, Any]) -> ProductReference:
    return ProductReference(**value)


def occurrence_id(
    base_document: ProductReference | Mapping[str, Any], extents: Sequence[Mapping[str, Any]]
) -> str:
    """Stable across analyses and database placement, different at repeated native addresses."""
    base = (
        base_document.values()
        if isinstance(base_document, ProductReference)
        else dict(base_document)
    )
    portable = [{k: v for k, v in extent.items() if k != "source_view_id"} for extent in extents]
    return sha256(canonical_bytes({"base_document": base, "extents": portable})).hexdigest()


@dataclass(frozen=True, slots=True)
class AnnotationReference:
    layer: ProductReference
    local_id: str

    def __post_init__(self):
        if type(self.local_id) is not str or not self.local_id:
            raise ValueError("annotation reference requires a local ID")

    def values(self) -> dict[str, Any]:
        return {"layer": self.layer.values(), "local_id": self.local_id}

    @property
    def identity(self) -> str:
        return "annotation:" + sha256(canonical_bytes(self.values())).hexdigest()


def annotation_reference(layer: ProductReference, local_id: str) -> AnnotationReference:
    return AnnotationReference(layer, local_id)


@dataclass(frozen=True, slots=True)
class LayerReport:
    """Canonical detached bytes keep validated state immutable; payload is a fresh value."""

    content: bytes

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.content)

    @property
    def content_digest(self) -> str:
        return sha256(self.content).hexdigest()

    @property
    def base_document(self) -> ProductReference:
        return _pin(self.payload["base_document"])

    def reference(self, task_id: int) -> ProductReference:
        return ProductReference(
            task_id, "characterization-layer:" + self.content_digest, self.content_digest
        )


@dataclass(frozen=True, slots=True)
class EnrichedDocumentView:
    content: bytes

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.content)

    @property
    def content_digest(self) -> str:
        return sha256(self.content).hexdigest()

    @property
    def base_document(self) -> ProductReference:
        return _pin(self.payload["base_document"])

    def reference(self, task_id: int) -> ProductReference:
        return ProductReference(
            task_id, "characterization-view:" + self.content_digest, self.content_digest
        )


def layer_reference(task_id: int, report: LayerReport) -> ProductReference:
    return report.reference(task_id)


def _shape(prepared: PreparedRelease, name: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    # JSON is the declared product wire: a single generated strict boundary validates it.
    return prepared.validate_json(name, canonical_bytes(dict(payload))).model_dump(
        mode="json", exclude_none=True
    )


def _acyclic(edges: Mapping[str, Sequence[str]], label: str) -> None:
    done: set[str] = set()
    visiting: set[str] = set()
    for start in edges:
        if start in done:
            continue
        stack = [(start, False)]
        while stack:
            node, leave = stack.pop()
            if leave:
                visiting.discard(node)
                done.add(node)
            elif node in visiting:
                raise ValueError(f"{label} structural cycle")
            elif node not in done:
                visiting.add(node)
                stack.append((node, True))
                stack.extend((target, False) for target in reversed(edges.get(node, ())))


def _scope(scope, base):
    ids = scope["source_view_ids"]
    views = scope["source_views"]
    if (
        len(set(ids)) != len(ids)
        or set(ids) != {v["source_view_id"] for v in views}
        or len(views) != len(ids)
    ):
        raise ValueError("source scope requires one exact portable pin per source view")
    if any(v["base_document"] != base for v in views):
        raise ValueError("source scope has wrong-source document pin")
    projections = {v["projection_digest"] for v in views}
    for selector in scope["selectors"]:
        _selector(selector, projections)
    return {v["source_view_id"]: v for v in views}


def _selector(selector, projections):
    if selector["projection"] not in projections:
        raise ValueError("source selector references an unselected projection")
    if ("start" in selector) != ("end" in selector) or selector.get("end", 0) < selector.get(
        "start", 0
    ):
        raise ValueError("source selector has invalid extent")


def _coverage(rows, scope, operation=None, *, composed=False):
    projections = {v["projection_digest"] for v in scope["source_views"]}
    seen = set()
    for row in rows:
        identity = canonical_bytes(row) if composed else row["family"]
        if identity in seen:
            raise ValueError("family coverage must be unique")
        seen.add(identity)
        if operation is not None and (
            row["operation"] != operation["key"]
            or row["family"] not in operation["produced_families"]
        ):
            raise ValueError("coverage differs from declared operation family")
        for field in ("eligible", "examined", "unexamined"):
            for selector in row.get(field, ()):
                _selector(selector, projections)
        if row["outcome"] in {"complete", "empty"}:
            if row["availability"] != "available" or row.get("unexamined"):
                raise ValueError("complete or empty family requires available fully examined scope")
            if not row.get("eligible") or row.get("examined") != row.get("eligible"):
                raise ValueError("complete or empty family must examine its eligible scope")
        elif not row.get("reason"):
            raise ValueError("incomplete family coverage requires a reason")
    if operation is not None and seen != set(operation["produced_families"]):
        raise ValueError("operation must account for every produced family")


def _require_layer_contract(payload: Mapping[str, Any]) -> None:
    if payload.get("format") != "characterization-layer-v1":
        raise ValueError("unsupported characterization layer contract")


_PUBLISHED_MANIFEST = object()


@dataclass(frozen=True)
class LayerManifest:
    """Authenticated metadata of one sealed layer; never an uploaded layer value."""

    pin: ProductReference
    content: bytes
    _authority: object

    def __post_init__(self):
        if self._authority is not _PUBLISHED_MANIFEST:
            raise ValueError("layer manifests require a protected published-product read")
        _require_layer_contract(self.payload)

    @property
    def payload(self) -> dict[str, Any]:
        return json.loads(self.content)

    @property
    def base_document(self) -> ProductReference:
        return _pin(self.payload["base_document"])

    def reference(self, task_id: int) -> ProductReference:
        if task_id != self.pin.task_id:
            raise ValueError("manifest differs from exact producing task")
        return self.pin


def _published_layer_manifest(reference: ProductReference, payload: Mapping[str, Any]) -> LayerManifest:
    return LayerManifest(reference, canonical_bytes(payload), _PUBLISHED_MANIFEST)


class _LayerValidation:
    """One explicitly supplied archived-release closure; never resolves ambient state."""

    def __init__(
        self,
        prepared: PreparedRelease,
        releases: Mapping[str, PreparedRelease] | None,
        dependencies: Mapping[ProductReference, LayerReport] | None,
    ):
        self.prepared = prepared
        self.releases = releases or {}
        self.dependencies = dependencies
        self.validated: dict[str, LayerReport] = {}
        self.visiting: set[str] = set()

    def validate(
        self,
        payload: Mapping[str, Any],
        *,
        dependencies: Mapping[ProductReference, LayerReport] | None = None,
    ) -> LayerReport:
        # The callback signature also serves the shared detached-view validator.
        if dependencies is not None and dependencies is not self.dependencies:
            raise ValueError("layer validation dependency context differs")
        _require_layer_contract(payload)
        release_id = payload["release_id"]
        prepared = (
            self.prepared
            if release_id == self.prepared.release_id
            else self.releases.get(release_id)
        )
        if prepared is None or prepared.release_id != release_id:
            raise ValueError("layer requires its own archived semantic release")
        key = sha256(canonical_bytes(payload)).hexdigest()
        if key in self.validated:
            return self.validated[key]
        if key in self.visiting:
            raise ValueError("layer dependency cycle")
        self.visiting.add(key)
        try:
            data = _shape(prepared, "AnnotationLayer", payload)
            for reference in data.get("dependencies", ()):
                pin = _pin(reference)
                report = self.dependencies.get(pin) if self.dependencies is not None else None
                if report is None or report.reference(pin.task_id) != pin:
                    raise ValueError("layer requires exact dependency closure")
                validated = self.validate(report.payload)
                if validated.content != report.content:
                    raise ValueError("dependency differs from its own released canonical contract")
            policies = attachment_policies(prepared)
            validate_json = prepared.validate_json

            def validate_basis(basis):
                validate_attachment_basis(
                    basis,
                    policies,
                    lambda name, value: validate_json(name, canonical_bytes(value)),
                )
                return (
                    policies.get("released_construction", {})
                    .get("rules", {})
                    .get(basis.get("rule_id"), {})
                )

            result = validate_layer_structure(
                data,
                validate_basis=validate_basis,
                dependencies=self.dependencies,
            )
            self.validated[key] = result
            return result
        finally:
            self.visiting.remove(key)


def validate_layer(
    prepared: PreparedRelease,
    payload: Mapping[str, Any],
    *,
    dependencies: Mapping[ProductReference, LayerReport] | None = None,
    releases: Mapping[str, PreparedRelease] | None = None,
) -> LayerReport:
    """Validate every participating v1 layer under its own explicitly archived release.

    ``prepared`` owns this payload. ``releases`` supplies differing dependency releases;
    same-release calls need no map. Neither layer bytes nor producer provenance are rebased.
    """
    if payload.get("release_id") != prepared.release_id:
        raise ValueError("characterization layer uses another semantic release")
    return _LayerValidation(prepared, releases, dependencies).validate(payload)


def validate_layer_structure(
    payload: Mapping[str, Any],
    *,
    validate_basis,
    dependencies: Mapping[ProductReference, LayerReport] | None = None,
) -> LayerReport:
    """Graph checks after participating layers receive their own archived schema validation.

    ``validate_basis`` must validate the dispatched released subtype; detached callers
    supply their archived JSON Schema validator, live callers use PreparedRelease.
    """
    _require_layer_contract(payload)
    data = json.loads(canonical_bytes(payload))
    for name in _INVENTORIES:
        data.setdefault(name, [])
    data.setdefault("dependencies", [])
    base = data["base_document"]
    views = _scope(data["source_scope"], base)
    _coverage(data["coverage"], data["source_scope"], data["operation"])
    if data["outcome"] not in data["operation"]["outcomes"]:
        raise ValueError("layer outcome is not declared by its operation")
    pins = [_pin(p) for p in data["dependencies"]]
    if len(set(pins)) != len(pins):
        raise ValueError("duplicate layer dependency")
    if pins and dependencies is None:
        raise ValueError("layer requires dependency closure")
    for pin in pins:
        dependency = dependencies.get(pin) if dependencies is not None else None
        if (
            dependency is None
            or dependency.reference(pin.task_id) != pin
            or dependency.base_document != _pin(base)
        ):
            raise ValueError("layer has missing or wrong-source dependency")
        _require_layer_contract(dependency.payload)
    if not set(_pin(p) for p in data["operation"].get("required_layers", ())) <= set(pins):
        raise ValueError("required operation layer missing from dependencies")
    all_nodes = {}
    indexes = {}
    for name in _INVENTORIES:
        index = {}
        for item in data[name]:
            key = item["local_id"]
            if key in all_nodes:
                raise ValueError("local IDs must be distinct across the layer")
            all_nodes[key] = item
            index[key] = item
        indexes[name] = index
    from .characterization_evidence import validate_evidence
    from .observations import source_python

    validate_evidence(data, indexes)
    for name in _INVENTORIES[1:]:
        for item in data[name]:
            scores = list(item.get("scores", ()))
            if name == "choices":
                scores.extend(
                    score for member in item["members"] for score in member.get("scores", ())
                )
            for score in scores:
                value = source_python(score["value"])
                if value is not None and type(value) not in {int, float}:
                    raise ValueError(
                        "native score must be an exact numeric source value or explicit null"
                    )
    coverage_by_family = {row["family"]: row for row in data["coverage"]}
    for name in _INVENTORIES[1:]:
        for item in data[name]:
            family = coverage_by_family.get(item["family"])
            if family is None:
                raise ValueError("inventory item has undeclared family")
            if family["outcome"] == "empty":
                raise ValueError("successful empty family contains output")
    choice_members = {}
    for group in data["choices"]:
        for member in group["members"]:
            key = member["local_id"]
            if key in all_nodes:
                raise ValueError("choice member local ID repeats")
            all_nodes[key] = member
            choice_members[key] = group

    def refs(values, index, label):
        if any(value not in index for value in values):
            raise ValueError(f"dangling {label} reference")

    for occurrence in data["occurrences"]:
        for extent in occurrence["extents"]:
            view = views.get(extent["source_view_id"])
            if view is None or extent["projection"] != view["projection_digest"]:
                raise ValueError("occurrence has wrong-source projection")
            _selector(extent, {view["projection_digest"]})
            if not extent["synthetic"] and "start" in extent and extent["end"] <= extent["start"]:
                raise ValueError("literal source occurrence requires a nonempty extent")
            if (
                "text" in extent
                and not extent["synthetic"]
                and (
                    "start" not in extent or len(extent["text"]) != extent["end"] - extent["start"]
                )
            ):
                raise ValueError("literal source text differs from its exact extent")
        if occurrence["local_id"] != occurrence_id(base, occurrence["extents"]):
            raise ValueError("occurrence identity differs from ordered source addresses")
    # References are layer-qualified only across immutable layer boundaries.
    # All premise-bearing records share the same external closure validation.
    premise_records = list(all_nodes.values()) + [r["basis"] for r in data["roles"]]
    dependency_indexes = {}
    for item in premise_records:
        for external in (
            *item.get("external_premises", ()),
            *item.get("required_external_choices", ()),
        ):
            pin = _pin(external["layer"])
            if pin not in pins:
                raise ValueError("external premise layer missing from dependencies")
            if dependencies is None:
                raise ValueError("external premise requires dependency closure")
            layer = dependencies.get(pin)
            if (
                layer is None
                or layer.reference(pin.task_id) != pin
                or layer.base_document != _pin(base)
            ):
                raise ValueError("external premise has missing or wrong-source dependency")
            if pin not in dependency_indexes:
                body = layer.payload
                node_ids = {n["local_id"] for k in _INVENTORIES for n in body[k]}
                node_ids.update(m["local_id"] for g in body["choices"] for m in g["members"])
                dependency_indexes[pin] = node_ids
            if external["local_id"] not in dependency_indexes[pin]:
                raise ValueError("dangling external premise")
        for external in item.get("required_external_choices", ()):
            if dependencies is None:
                raise ValueError("external choice requires exact dependency closure")
            body = dependencies[_pin(external["layer"])].payload
            if external["local_id"] not in {
                m["local_id"] for g in body["choices"] for m in g["members"]
            }:
                raise ValueError("required external choice is not a choice member")
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
    if data["outcome"] == "complete" and any(
        c["outcome"] not in {"complete", "empty"} for c in data["coverage"]
    ):
        raise ValueError("complete layer contains incomplete family coverage")
    return LayerReport(canonical_bytes(data))


def validate_view(
    prepared: PreparedRelease,
    payload: Mapping[str, Any],
    layers: Mapping[ProductReference, LayerReport],
    *,
    releases: Mapping[str, PreparedRelease] | None = None,
) -> EnrichedDocumentView:
    data = _shape(prepared, "EnrichedDocumentView", payload)
    if data["release_id"] != prepared.release_id:
        raise ValueError("view uses another semantic release")
    if data["profile"] == "full_characterization":
        families = characterization_profiles(prepared).get(data["profile"])
        if families is None or not set(families) <= {
            row["family"] for row in data.get("coverage", ())
        }:
            raise ValueError(
                "full characterization requires every released baseline family outcome"
            )
    return validate_view_structure(
        data,
        layers,
        validate_layer=_LayerValidation(prepared, releases, layers).validate,
    )


def validate_view_structure(
    payload: Mapping[str, Any], layers: Mapping[ProductReference, LayerReport | LayerManifest], *, validate_layer
) -> EnrichedDocumentView:
    """Shared v1 closure checks; callback validates each layer under its own release."""
    if payload.get("format") != "enriched-document-view-v1":
        raise ValueError("unsupported enriched document view contract")
    data = json.loads(canonical_bytes(payload))
    _scope(data["source_scope"], data["base_document"])
    data.setdefault("layers", [])
    data.setdefault("coverage", [])
    pins = [_pin(p) for p in data["layers"]]
    if len(set(pins)) != len(pins):
        raise ValueError("duplicate selected layer")
    active = [_pin(p) for p in data.get("active_layers", data["layers"])]
    if len(set(active)) != len(active) or not set(active) <= set(pins):
        raise ValueError("active layer selection differs from retained dependency closure")
    if bool(active) != bool(pins):
        raise ValueError("analytical view requires active layers")
    if data["profile"] == "source_only":
        if pins or data["coverage"]:
            raise ValueError("source_only view cannot claim analytical layers or coverage")
    elif not pins:
        raise ValueError("analytical view requires selected layers")
    coverage = {}
    for pin in pins:
        layer = layers.get(pin)
        if layer is None or layer.reference(pin.task_id) != pin:
            raise ValueError("view has missing layer or malformed pin")
        body = layer.payload
        _require_layer_contract(body)
        if body["base_document"] != data["base_document"]:
            raise ValueError("view mixes incompatible source pins")
        if not set(_pin(p) for p in body["dependencies"]) <= set(pins):
            raise ValueError("view lacks selected layer dependency closure")
        # A composed view may contain several independently analyzed source subsets.
        # Exact selector inclusion avoids inventing geometric/native containment.
        if not scope_contains(data["source_scope"], body["source_scope"]):
            raise ValueError("view source scope does not contain selected layer scope")
        if pin in active:
            for row in body["coverage"]:
                coverage[canonical_bytes(row)] = row
    _coverage(data["coverage"], data["source_scope"], composed=True)
    if any(canonical_bytes(row) not in coverage for row in data["coverage"]):
        raise ValueError("view coverage is not supported by selected layers")
    for pin in pins:
        if isinstance(layers[pin], LayerManifest):
            if validate_layer is not None:
                raise ValueError("published manifests cannot replace full layer validation")
            continue
        if validate_layer is None:
            raise ValueError("published composition requires protected layer manifests")
        validated = validate_layer(layers[pin].payload, dependencies=layers)
        if validated.content != layers[pin].content:
            raise ValueError("selected layer differs from its own released canonical contract")
    return EnrichedDocumentView(canonical_bytes(data))


def validate_published_view(
    prepared: PreparedRelease, payload: Mapping[str, Any],
    layers: Mapping[ProductReference, LayerManifest],
) -> EnrichedDocumentView:
    """Compose metadata whose immutable layer validity is held by native publication.

    Full unsealed/local layers still enter validate_view/validate_layer. This route accepts
    only manifests obtained from protected reads, preserving original archived authority.
    """
    if any(not isinstance(layer, LayerManifest) for layer in layers.values()):
        raise ValueError("published composition requires authenticated layer manifests")
    data = _shape(prepared, "EnrichedDocumentView", payload)
    if data["release_id"] != prepared.release_id:
        raise ValueError("view uses another semantic release")
    if data["profile"] == "full_characterization":
        families = characterization_profiles(prepared).get(data["profile"])
        if families is None or not set(families) <= {row["family"] for row in data.get("coverage", ())}:
            raise ValueError("full characterization requires every released baseline family outcome")
    return validate_view_structure(data, layers, validate_layer=None)


def encode_layer(layer: LayerReport) -> bytes:
    return layer.content


def decode_layer(
    prepared: PreparedRelease,
    content: bytes | str,
    *,
    dependencies: Mapping[ProductReference, LayerReport] | None = None,
    releases: Mapping[str, PreparedRelease] | None = None,
) -> LayerReport:
    return validate_layer(
        prepared, json.loads(content), dependencies=dependencies, releases=releases
    )


def encode_view(view: EnrichedDocumentView) -> bytes:
    return view.content


def decode_view(
    prepared: PreparedRelease,
    content: bytes | str,
    layers: Mapping[ProductReference, LayerReport],
    *,
    releases: Mapping[str, PreparedRelease] | None = None,
) -> EnrichedDocumentView:
    return validate_view(prepared, json.loads(content), layers, releases=releases)


def project_reading(
    layer: LayerReport,
    root: str,
    *,
    choices: Sequence[str] = (),
    dependencies: Mapping[ProductReference, LayerReport] | None = None,
    external_choices: Sequence[AnnotationReference] = (),
) -> dict[str, Any]:
    """Bounded supported DAG projection; unknown compatibility never creates combinations."""
    data = layer.payload
    dependencies = dependencies or {}
    terms = {t["local_id"]: t for t in data["terms"]}
    members = {m["local_id"]: (g, m) for g in data["choices"] for m in g["members"]}
    selected = set(validate_reading_choices(data, choices))
    external = {(_pin(ref.values()["layer"]), ref.local_id) for ref in external_choices}
    if len(external) != len(external_choices):
        raise ValueError("duplicate qualified analytical choice")
    # Only the actual dependency closure can supply upstream selections. A caller's
    # larger report cache is not authority to introduce an unrelated reading.
    reachable = set()
    pending_dependencies = [_pin(value) for value in data.get("dependencies", ())]
    while pending_dependencies:
        pin = pending_dependencies.pop()
        if pin in reachable:
            continue
        report = dependencies.get(pin) if dependencies is not None else None
        if report is None or report.reference(pin.task_id) != pin:
            raise ValueError("reading requires exact retained dependency closure")
        if report.payload["base_document"] != data["base_document"]:
            raise ValueError("reading dependency belongs to a different source document")
        reachable.add(pin)
        pending_dependencies.extend(_pin(value) for value in report.payload.get("dependencies", ()))
    by_layer = {}
    for pin, identity in external:
        if pin not in reachable:
            raise ValueError("qualified choice is outside the reading dependency closure")
        dependency = dependencies.get(pin) if dependencies is not None else None
        if dependency is None or dependency.reference(pin.task_id) != pin:
            raise ValueError("qualified choice requires exact retained dependency")
        by_layer.setdefault(pin, []).append(identity)
    for pin, identities in by_layer.items():
        body = dependencies[pin].payload
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
        for g in dependencies[pin].payload["choices"]
        for m in g["members"]
        if m["local_id"] in identities
    ]
    while pending_support:
        pin, key = pending_support.pop()
        if (pin, key) in visited:
            continue
        visited.add((pin, key))
        body = dependencies[pin].payload
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
    if any(
        (_pin(ref["layer"]), ref["local_id"]) not in selected
        for ref in record.get("required_external_choices", ())
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


def scope_contains(container: Mapping[str, Any], subset: Mapping[str, Any]) -> bool:
    """Portable pin/selector set inclusion, with no inferred native-tree containment."""
    return (
        set(subset["source_view_ids"]) <= set(container["source_view_ids"])
        and {canonical_bytes(v) for v in subset["source_views"]}
        <= {canonical_bytes(v) for v in container["source_views"]}
        and {canonical_bytes(v) for v in subset["selectors"]}
        <= {canonical_bytes(v) for v in container["selectors"]}
    )


def select_primary_layers(layers, source_view, *, families):
    """A consumer's frozen selection must cover its actual native source population."""
    requested = set(families)
    if not requested:
        raise ValueError("primary read requires explicit families")
    selected = {
        pin: layer
        for pin, layer in layers.items()
        if source_view.ref.id in layer.payload["source_scope"]["source_view_ids"]
    }
    for family in requested:
        selectors = [
            selector
            for layer in selected.values()
            for row in layer.payload["coverage"]
            if row["family"] == family
            and row["outcome"] in {"complete", "empty"}
            and row["availability"] == "available"
            for selector in row.get("examined", ())
            if selector["projection"] == source_view.ref.projection_digest
        ]
        if not selectors:
            raise ValueError(
                f"primary family {family} is missing or incomplete in frozen selection"
            )
        for piece in source_view.pieces:
            if piece["kind"] != "native_text":
                continue
            intervals = sorted(
                (
                    max(piece["start"], s.get("start", 0)),
                    min(piece["end"], s.get("end", len(source_view.text))),
                )
                for s in selectors
                if not s.get("native_pointer") or s["native_pointer"] == piece["item_ref"]
            )
            position = piece["start"]
            for start, end in intervals:
                if start > position:
                    break
                position = max(position, end)
            if position < piece["end"]:
                raise ValueError(f"primary family {family} leaves native source unexamined")
    return selected


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
