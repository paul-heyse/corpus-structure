"""Dossier membership from original retained source products, including endpoint evidence.

Source roles establish useful private membership. They establish no independently
assessed semantic fact; the protected StructuralReport route owns that stronger claim.
"""

from hashlib import sha256

from corpus_structure.semantic.contributions import contribution_identity
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.observations import source_python
from corpus_structure.semantic.structural_products import (
    DossierContributionCitation,
    DossierMember,
    LocatedDefinitionSpan,
)


def derive_contribution_members(
    inputs, reference, payload, *, root=None
) -> tuple[DossierMember, ...]:
    """Consume only detached owned-reader output; authenticate again at native replay."""
    rows = {r["contribution_id"]: r for r in payload["contributions"]}
    selected = rows.get(reference.contribution_id)
    if selected is None or any(contribution_identity(r) != key for key, r in rows.items()):
        raise ValueError("retained contribution differs from immutable contents")
    if reference.contribution_id not in inputs.dependencies:
        raise ValueError("dossier contribution outside declared dependencies")
    if selected["semantic_type"] not in {
        "structural.located_participant",
        "structural.scoped_attachment",
        "structural.artifact",
    }:
        raise ValueError("dossier contribution requires a current source structural product")
    reachable, pending = {}, [reference.contribution_id]
    while pending:
        key = pending.pop()
        if key in reachable:
            continue
        row = rows.get(key)
        if row is None:
            raise ValueError("retained contribution endpoint unavailable")
        reachable[key] = row
        pending.extend(e["contribution_id"] for e in row.get("endpoints", ()))
        pending.extend(row.get("members", ()))
    if set(reachable) != set(rows):
        raise ValueError("retained contribution closure includes unrelated products")
    views = {v["source_view_id"]: v for v in payload["sources"]}
    sources = {s.source_view_id: s for s in inputs.sources}
    citations, dependencies = [], []
    for row in sorted(reachable.values(), key=lambda r: r["contribution_id"]):
        dependencies.extend((row["contribution_id"], *row.get("computation_dependencies", ())))
        for anchor in row.get("anchors", ()):
            pin = anchor["pin"]
            source = sources.get(pin["source_view_id"])
            view = views.get(pin["source_view_id"])
            if (
                source is None
                or view is None
                or any(
                    pin.get(k) != getattr(source, v)
                    for k, v in (
                        ("native_product_task_id", "native_task_id"),
                        ("product_key", "native_product_key"),
                        ("product_digest", "native_content_digest"),
                        ("projection_digest", "projection_digest"),
                        ("recipe_digest", "recipe_digest"),
                    )
                )
            ):
                raise ValueError("contribution source differs from original dossier source")
            if (
                pin != view["pin"]
                or anchor.get("space") != "native"
                or anchor.get("precision") != "exact"
            ):
                raise ValueError("contribution citation lacks an exact native source bridge")
            projection = view["projection"]
            matches = [
                p
                for p in projection["pieces"]
                if p.get("kind") == "native_text"
                and p["item_ref"]
                + (
                    "/data/table_cells/" + str(p["cell_index"])
                    if p.get("cell_index") is not None
                    else ""
                )
                == anchor["pointer"]
            ]
            if len(matches) != 1:
                raise ValueError("contribution citation has ambiguous native field bridge")
            piece = matches[0]
            start, end = piece["start"] + anchor["start"], piece["start"] + anchor["end"]
            quote = anchor["source_piece"]
            if (
                not piece["start"] <= start < end <= piece["end"]
                or projection["text"][start:end] != quote
            ):
                raise ValueError("contribution citation differs from original source text")
            passages = [
                p
                for p in inputs.passages
                if p.source_ref == source.identity and p.start <= start < end <= p.end
            ]
            if not passages:
                raise ValueError("contribution endpoint citation outside dossier passage closure")
            for p in passages:
                if p.text[start - p.start : end - p.start] != quote:
                    raise ValueError("contribution citation differs from dossier passage")
                citations.append(
                    DossierContributionCitation(
                        contribution_id=row["contribution_id"],
                        source_ref=source.identity,
                        source_pointer=anchor["pointer"],
                        span=LocatedDefinitionSpan(
                            passage_id=p.passage_id, start=start, end=end, text=quote
                        ),
                    )
                )
    if not citations:
        raise ValueError("dossier contribution lacks located endpoint evidence")
    citations = tuple(
        sorted(
            set(citations),
            key=lambda c: (
                c.source_ref,
                c.span.start,
                c.span.end,
                c.contribution_id,
                c.span.passage_id,
            ),
        )
    )
    if root is not None and (
        selected["kind"] != "relation"
        or not any(citation.span in (root.term, root.content) for citation in citations)
    ):
        return ()
    meaning = source_python(selected["value"])
    raw_role = meaning.get("role", meaning.get("relation", "unresolved_sense"))
    role = (
        raw_role
        if raw_role in {"exception", "revision", "conflict", "open_question"}
        else (
            "relationship"
            if selected["kind"] == "relation"
            else "terminology"
            if raw_role in {"header", "row_label", "symbol", "declaration"}
            else "usage"
            if raw_role.startswith("procedure_")
            else "unresolved_sense"
        )
    )
    region = meaning.get("region", meaning.get("scope", meaning.get("source_pointer", "unknown")))
    scope = ",".join(sorted({c.source_ref for c in citations})) + ":" + region
    key = sha256(
        canonical_bytes(
            dict(
                contribution_ref=reference.model_dump(mode="json"),
                role=role,
                citations=[c.model_dump(mode="json") for c in citations],
                scope=scope,
                **({"sense": root.component_id} if root is not None else {}),
            )
        )
    ).hexdigest()
    primary = citations[0].span
    return (
        DossierMember(
            member_id=key,
            passage_id=primary.passage_id,
            citation=primary,
            role=role,
            sense=root.component_id if root is not None else "unresolved",
            scope=scope,
            relation_product_id=reference.contribution_id,
            contribution_ref=reference,
            contribution_citations=citations,
            computation_dependencies=tuple(sorted(set(dependencies))),
            qualification="proposed",
        ),
    )
