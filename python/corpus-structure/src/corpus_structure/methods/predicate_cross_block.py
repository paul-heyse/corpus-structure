"""Project retained cross-block primary host relations into domain contributions."""

from corpus_structure.semantic.constructions.retained_rules import (
    CrossBlockQualifier as CrossBlockQualifier,
)
from corpus_structure.semantic.constructions.retained_rules import (
    CrossBlockTarget as CrossBlockTarget,
)


def cross_block_qualifiers(frame, annotations, selected, hosts, population, native, pieces):
    """Read exact shared relations; no sibling, lexical or dependency rule runs here."""
    from .predicate_frames import _project

    seen = set()
    for product in annotations:
        layers = getattr(product, "primary_layers", {})
        result = _project(frame.text, product)
        cues = {
            cue.primary_ref.local_id: cue
            for cue in result.unresolved_cues
            if cue.primary_ref is not None
        }
        for pin, report in layers.items():
            body = report.payload
            terms = {term["local_id"]: term for term in body["terms"]}
            for key, cue in cues.items():
                if cue.primary_ref.layer != pin or (pin, key) in seen:
                    continue
                if not all(selected.start <= a < b <= selected.end for a, b in cue.span.extents):
                    continue
                relations = [
                    r
                    for r in body["roles"]
                    if r["owner"] == key and r["role"] == "cross_block_host"
                ]
                if not relations:
                    continue
                seen.add((pin, key))
                targets = tuple(
                    host
                    for host in hosts
                    if host.primary_ref is not None
                    and host.primary_ref.layer == pin
                    and any(role["member"] == host.primary_ref.local_id for role in relations)
                )
                groups = [
                    terms[edge["target"]]["value"]
                    for edge in terms[key].get("children", ())
                    if edge["role"] == "native_list_group" and "target" in edge
                ]
                predecessors = [
                    edge["target"]
                    for edge in terms[key].get("children", ())
                    if edge["role"] == "prior_qualifier" and "target" in edge
                ]
                if len(groups) == 1 and not predecessors:
                    witness = dict(kind="list_intro", list_group=groups[0])
                elif len(predecessors) == 1 and not groups:
                    previous = [
                        row["contribution_id"]
                        for row in population.values()
                        if row.get("component", {}).get("kind") == "predicate_cue"
                        and row["component"].get("scope") == selected.key
                        and row["component"].get("effective_version") == selected.version
                        and row["component"].get("primary_node")
                        == dict(layer=pin.values(), local_id=predecessors[0])
                    ]
                    if len(previous) != 1:
                        continue
                    witness = dict(kind="parameter_note", parameterization=previous[0])
                else:
                    continue
                yield CrossBlockQualifier(product, cue, targets, witness)
