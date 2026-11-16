"""Exact retained occurrence carriers shared by current contextual producers."""

import json

from corpus_structure.semantic.contributions import contribution_identity, occurrence_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_value


def retained_occurrences(
    upstream,
    nodes,
    pin,
    operation_key,
    semantic_types=(),
    *,
    canonical_producer=False,
    required_occurrence_ids: tuple[str, ...] = (),
):
    """Authenticate selected producer locations; role proposals remain distinct products.

    Multiple pieces in one native item may share an encoder context without making
    their intervening characters a new asserted source occurrence.
    """
    products, contexts, coordinates = [], {}, {}
    required = set(required_occurrence_ids)
    for original in upstream.get("contributions", ()):
        if semantic_types and original["semantic_type"] not in semantic_types:
            continue
        if required and original.get("occurrence_id") not in required:
            continue
        anchors = tuple(original.get("anchors", ()))
        if original.get("kind") not in {"occurrence", "proposal", "group"} or not anchors:
            continue
        has_exact_context = True
        for anchor in anchors:
            node = nodes.get(anchor["pointer"])
            if node is None or anchor["pin"] != pin or anchor["space"] != "native":
                raise ValueError("retained occurrence differs from actual native source")
            start, end = anchor.get("start"), anchor.get("end")
            if anchor["precision"] != "exact":
                has_exact_context = False
            elif (
                type(start) is not int
                or type(end) is not int
                or not 0 <= start < end <= len(node.get("text", ""))
                or node["text"][start:end] != anchor["source_piece"]
            ):
                raise ValueError("retained occurrence source slice is invalid")
            coordinates[anchor["pointer"]] = dict(
                pin=pin, space="native", pointer=anchor["pointer"], text=node.get("text", "")
            )
        occurrence = occurrence_identity(anchors)
        if occurrence != original["occurrence_id"]:
            raise ValueError("retained occurrence identity differs from actual source anchors")
        component, value = original.get("component"), original.get("value")
        if canonical_producer:
            # SourceValue records object key order. Heading identities must survive
            # both PostgreSQL JSONB and canonical detached JSON representations.
            component = json.loads(canonical_bytes(component))
            value = json.loads(canonical_bytes(value))
        product = dict(
            contract="RetainedContributionSemantics",
            kind="occurrence",
            semantic_type="contextual.located_mention",
            operation_key=operation_key,
            item_key=original["contribution_id"],
            pin=pin,
            anchors=anchors,
            occurrence_id=occurrence,
            disposition="located_proposal",
            standing="retained_private",
            score_state="missing",
            value=source_value(
                dict(
                    producer_semantic_type=original["semantic_type"],
                    producer_component=component,
                    producer_value=value,
                )
            ),
            computation_dependencies=(original["contribution_id"], original["operation_key"]),
        )
        product["contribution_id"] = contribution_identity(product)
        products.append(product)
        if has_exact_context and len({a["pointer"] for a in anchors}) == 1:
            start, end = min(a["start"] for a in anchors), max(a["end"] for a in anchors)
            text = nodes[anchors[0]["pointer"]]["text"]
            contexts[occurrence] = (text, start, end, text[start:end])
    if missing := required - contexts.keys():
        raise ValueError(
            "selected producer lacks an exact native query carrier for "
            + ", ".join(sorted(missing))
        )
    return tuple(products), contexts, tuple(coordinates.values())
