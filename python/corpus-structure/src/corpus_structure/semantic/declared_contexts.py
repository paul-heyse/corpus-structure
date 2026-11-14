"""Named structural context selection over an explicitly bound closed population."""

from __future__ import annotations

import json
from dataclasses import dataclass
from hashlib import sha256

from .declared_record_sources import DeclaredNativeFrameSource
from .identity import canonical_bytes
from .source_contexts import ContextRelationship, RetrievalOutcome, SourceContextRead


@dataclass(frozen=True)
class DeclaredContextPopulation:
    """Already selected source bodies and their actual compiled role witness.

    This value supplies no authorization. The prepared operation's binding/admission
    owns authenticity, and its declared population owns this finite universe.
    """

    sources: tuple[DeclaredNativeFrameSource, ...]
    witness: bytes

    @classmethod
    def from_role(cls, prepared, role, values, *, project):
        if role.population_witness is None or role.state not in {"present", "known-absent"}:
            raise ValueError("related context requires an explicitly bound population")
        witness = json.loads(role.population_witness)
        if witness.get("complete") is not True or not witness.get("identity") or not isinstance(witness.get("evidence"), dict):
            raise ValueError("related context requires complete native population standing")
        if len(values) != len(role.members) or any(member.member is None for member in role.members) or set(witness.get("members", ())) != {member.member for member in role.members}:
            raise ValueError("related context bodies differ from the selected population membership")
        sources = tuple(DeclaredNativeFrameSource.acquire(prepared, value, member, project=project) for value, member in zip(values, role.members, strict=True))
        if len({source.source_key for source in sources}) != len(sources):
            raise ValueError("related context population repeats a qualified source member")
        return cls(sources, role.population_witness)


def select_related_context(population, primary, request, *, limit):
    """Preserve native links/ancestors/order; never infer a semantic attachment."""
    if not isinstance(population, DeclaredContextPopulation) or not isinstance(primary, DeclaredNativeFrameSource):
        raise TypeError("declared context selection requires original-relative bound sources")
    if type(limit) is not int or not 1 <= limit <= 8:
        raise ValueError("context lookup requires a source bound between one and eight")
    native = json.loads(primary.native_context)
    nodes = {item["self_ref"]: item for item in native["items"]}
    node = nodes.get(request.pointer)
    if node is None:
        raise ValueError("context lookup pointer is outside its selected primary source")
    digest = sha256(canonical_bytes([primary.pin.values(), json.loads(population.witness), request.__dict__])).hexdigest()

    def result(sources, candidates, outcome, reason):
        return SourceContextRead(tuple(sources), tuple(source.pin for source in candidates), digest, outcome, reason)

    targets = set()
    if request.targets:
        field = {ContextRelationship.CAPTION: "captions", ContextRelationship.NOTE: "footnotes", ContextRelationship.REFERENCE: "references"}.get(request.relationship)
        declared = {link.get("$ref") for link in node.get(field, ()) if isinstance(link, dict)} if field else set()
        if not set(request.targets) <= declared:
            raise ValueError("context targets differ from the selected item's native links")
        targets = set(request.targets) - nodes.keys()
    elif request.relationship == ContextRelationship.NEIGHBOR:
        parent_ref = node.get("parent", {}).get("$ref")
        parent = nodes.get(parent_ref)
        if parent is None or not isinstance(parent.get("children"), list):
            return result((), (), RetrievalOutcome.MISSING_SCOPE, "native sibling order is unavailable in the selected source")
        children = [link.get("$ref") for link in parent["children"] if isinstance(link, dict)]
        if children.count(request.pointer) != 1:
            return result((), (), RetrievalOutcome.MISSING_SCOPE, "native parent does not own one exact ordered child occurrence")
        position = children.index(request.pointer)
        targets = set(children[max(0, position - 1):position] + children[position + 1:position + 2])
    elif request.relationship != ContextRelationship.ANCESTOR:
        return result((), (), RetrievalOutcome.MISSING_SCOPE, "no explicit native target for this relation")
    ancestors = {item["self_ref"] for item in native.get("ancestors", ())}
    candidates = []
    for source in population.sources:
        if source.source_key == primary.source_key or source.original_key != primary.original_key or source.pin.values()["project_id"] != primary.pin.values()["project_id"]:
            continue
        if request.relationship == ContextRelationship.ANCESTOR and not request.targets:
            matches = source.membership == "direct" and source.section_pointer in ancestors
        else:
            pointers = {item["self_ref"] for item in json.loads(source.native_context)["items"]}
            matches = bool(targets & pointers)
        if matches:
            candidates.append(source)
    candidates.sort(key=lambda source: source.source_key)
    if len(candidates) > limit:
        return result((), candidates[:limit], RetrievalOutcome.RESOURCE_LIMIT, "related source candidate bound exceeded before context assembly")
    if not candidates:
        return result((), (), RetrievalOutcome.NO_MATCH, "no selected same-original source in the declared relation scope")
    if request.targets and len(candidates) > len(set(request.targets)):
        return result((), candidates, RetrievalOutcome.AMBIGUOUS, "multiple selected projections cover an explicit target")
    return result(candidates, candidates, RetrievalOutcome.SELECTED, "selected native relation; semantic role attachment remains unresolved")
