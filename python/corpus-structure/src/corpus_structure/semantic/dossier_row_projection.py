"""Pure row projection over one acquired dossier's normalized values."""


def dossier_rows(members, passages, sources, facets):
    """Preserve member/citation order and the original selected facet order."""
    facets_by_member = {}
    for ordinal, facet in enumerate(facets):
        key = facet["member_id"]
        group = facets_by_member.get(key, [])
        group += [{"ordinal": ordinal, "value": facet}]
        facets_by_member[key] = group
    for member, spans, opposite in members:
        member_id = member["member_id"]
        citations = [
            {
                "member_id": member_id,
                "source": sources[passages[span["passage_id"]]],
                "citation": span,
            }
            for span in spans
        ]
        if opposite is not None:
            citations += [
                {
                    "member_id": member_id,
                    "context": "opposite_comparison_side",
                    "source": opposite[0],
                    "citation": opposite[1],
                }
            ]
        yield {
            "members": [member],
            "citations": citations,
            "supported_facets": facets_by_member.get(member_id, []),
        }
