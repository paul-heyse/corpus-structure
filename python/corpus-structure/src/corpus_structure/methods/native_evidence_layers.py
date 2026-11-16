"""Shared source selectors, native family declarations and retained column readers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from corpus_structure.ingest.annotations import AnnotationProduct
from corpus_structure.semantic.identity import canonical_bytes


SPACY_FAMILIES = (
    "spacy.tokens",
    "spacy.sentences",
    "spacy.lemma",
    "spacy.pos",
    "spacy.tag",
    "spacy.morphology",
    "spacy.dependency",
)
HANLP_FAMILIES = (
    "hanlp.tokens",
    "hanlp.lemma",
    "hanlp.pos",
    "hanlp.dependency",
    "hanlp.constituency",
    "hanlp.srl",
)
SPACY_COLUMNS = dict(
    zip(("SENT_START", "LEMMA", "POS", "TAG", "MORPH", "DEP"), SPACY_FAMILIES[1:], strict=True)
)
HANLP_SCHEMES = {
    "lemma": "hanlp-lemma-native-1",
    "pos": "hanlp-ptb-pos-native-1",
    "dependency": "hanlp-universal-dependencies-1",
    "constituency": "hanlp-ptb-constituency-1",
    "srl": "hanlp-propbank-srl-native-1",
}


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def source_identity(view):
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    return view.source_key if isinstance(view, DeclaredNativeFrameSource) else view.ref.id


def source_projection(view):
    from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

    return (
        view.projection_digest
        if isinstance(view, DeclaredNativeFrameSource)
        else view.ref.projection_digest
    )


def source_selector(view: Any, start: int, end: int, pointer: str | None = None) -> dict[str, Any]:
    row = dict(projection=source_projection(view), start=start, end=end)
    if pointer is not None:
        row["native_pointer"] = pointer
    return row


def has_selected_native_text(view: Any, selectors: Sequence[Mapping[str, Any]]) -> bool:
    """Whether selected projected native characters contain language input.

    Item-only formula recognition has independent eligibility in the formal owner.
    Empty projections and synthetic separators do not become provider requests.
    """
    items = {item["self_ref"]: item for item in getattr(view, "items", ())}
    for piece in view.pieces:
        if piece["kind"] != "native_text":
            continue
        for selector in selectors:
            if selector["projection"] != source_projection(view):
                continue
            pointer = selector.get("native_pointer")
            current, seen = piece.get("item_ref"), set()
            while pointer and current and current != pointer and current not in seen:
                seen.add(current)
                current = (items.get(current, {}).get("parent") or {}).get("$ref")
            if pointer and current != pointer:
                continue
            start = max(piece["start"], selector.get("start", 0))
            end = min(piece["end"], selector.get("end", len(view.text)))
            if start < end and view.text[start:end].strip():
                return True
    return False




class PrimaryAnnotationProduct(AnnotationProduct):
    """A local native working view with exact retained primary-layer dependencies.

    The extra reference is deliberately not a dataclass field: serialization keeps the
    existing detached columns, while durable primary meaning stays in its pinned layers.
    """

    primary_layers: Mapping

    def __init__(self, *, primary_layers=None, **values):
        from types import MappingProxyType

        AnnotationProduct.__init__(self, **values)
        object.__setattr__(self, "primary_layers", MappingProxyType(dict(primary_layers or {})))


def retained_annotation_profile(native_run, requested=None):
    """Recover the retained execution identity, never an ambient installed profile.

    Absent execution metadata preserves the historical unprofiled contract. An
    explicit request cannot authenticate against missing or different metadata.
    """
    from dataclasses import replace

    from corpus_structure.ingest.annotations import AnnotationProfile
    from corpus_structure.ingest.sentences import SentenceConfig
    from corpus_structure.methods.native_profiles import NativeProfile
    from corpus_structure.semantic.observations import source_python

    native = None
    if "execution_profile" in native_run:
        wire = source_python(native_run["execution_profile"])
        if not isinstance(wire, dict):
            raise ValueError("retained native execution profile is not an object")
        try:
            native = NativeProfile(**wire)
        except (TypeError, ValueError) as error:
            raise ValueError("retained native execution profile is invalid") from error
        if canonical_bytes(native.wire) != canonical_bytes(wire):
            raise ValueError("retained native execution profile is not a complete frozen snapshot")
        if native.provider != "spacy":
            raise ValueError("retained annotation execution profile belongs to another provider")
        configuration = SentenceConfig.model_validate(native.parameters)
        if canonical_bytes(configuration.model_dump(mode="json")) != canonical_bytes(
            native.parameters
        ):
            raise ValueError(
                "retained native execution parameters are not a complete frozen configuration"
            )
    else:
        configuration = SentenceConfig(
            spacy_version=native_run["runtime_version"],
            model=native_run["model"],
            model_version=native_run["model_version"],
            exclude=("ner",),
        )
    if (configuration.model, configuration.model_version, configuration.spacy_version) != (
        native_run["model"],
        native_run["model_version"],
        native_run["runtime_version"],
    ):
        raise ValueError("retained execution configuration differs from native model/runtime")
    fingerprint = None if native is None else native.fingerprint
    if requested is None:
        return AnnotationProfile(configuration, execution_profile=fingerprint)
    if (
        requested.configuration.model,
        requested.configuration.model_version,
        requested.configuration.spacy_version,
    ) != (configuration.model, configuration.model_version, configuration.spacy_version):
        raise ValueError("retained native producer differs from demanded model/runtime")
    if native is not None and requested.configuration != configuration:
        raise ValueError("retained annotation configuration differs from requested parameters")
    if requested.execution_profile is not None and requested.execution_profile != fingerprint:
        raise ValueError("retained annotation execution profile differs or is unavailable")
    return replace(requested, execution_profile=fingerprint)


def retained_annotation_products(layers, view, profile):
    """Restore exact whole-block native working columns without NLP or private policy."""
    from dataclasses import asdict

    from corpus_structure.ingest.annotations import (
        _ATTRIBUTES,
        AnnotationAvailability,
        ComponentPin,
        SentenceAnnotation,
        TokenAnnotation,
    )
    from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece
    from corpus_structure.ingest.sentences import TextLayout, TextToken
    from corpus_structure.semantic.proposals import native_source_frame
    from corpus_structure.semantic.source_contexts import NativeSourcePin

    source = NativeSourcePin.from_source(native_source_frame(view, ()))
    result = []
    seen = set()
    for layer in layers.values():
        body = layer.payload
        if body["base_document"] != view.ref.native_product.values():
            raise ValueError("retained native columns belong to another base document")
        matching = [
            value
            for value in body["source_scope"]["source_views"]
            if value["source_view_id"] == view.ref.id
        ]
        if not matching:
            continue
        expected = dict(
            source_view_id=view.ref.id,
            key=view.ref.key,
            base_document=view.ref.native_product.values(),
            section_pointer=view.ref.section_pointer,
            membership=view.ref.membership,
            projection_digest=view.ref.projection_digest,
            recipe_digest=view.ref.recipe_digest,
        )
        if matching != [expected]:
            raise ValueError(
                "retained native columns differ from exact source-view recipe and scope"
            )
        annotations = {a["local_id"]: a for a in body["annotations"]}
        occurrences = {o["local_id"]: o for o in body["occurrences"]}
        runs = {r["local_id"]: r for r in body.get("native_runs", ()) if r["provider"] == "spacy"}
        profiles = {key: retained_annotation_profile(run, profile) for key, run in runs.items()}
        blocks = {}
        for annotation in annotations.values():
            token = annotation.get("native_token")
            if token and token["native_run"] in runs:
                extents = [
                    e for oid in annotation["occurrences"] for e in occurrences[oid]["extents"]
                ]
                if all(
                    e["source_view_id"] == view.ref.id
                    and e["projection"] == view.ref.projection_digest
                    for e in extents
                ):
                    blocks.setdefault(token["container"], []).append((annotation, extents))
        for container, population in blocks.items():
            if container in seen:
                raise ValueError(
                    "retained primary selection has competing native block populations"
                )
            seen.add(container)
            population.sort(key=lambda pair: pair[0]["native_token"]["index"])
            rows = [a["native_token"] for a, _ in population]
            if [row["index"] for row in rows] != list(range(len(rows))):
                raise ValueError("retained native block omits original token indices")
            block = annotations[container]
            extents = [e for oid in block["occurrences"] for e in occurrences[oid]["extents"]]
            start, end = extents[0]["start"], extents[-1]["end"]
            native_run = runs[rows[0]["native_run"]]
            effective_profile = profiles[rows[0]["native_run"]]
            cfg = effective_profile.configuration
            if (
                native_run["model"],
                native_run["model_version"],
                native_run["runtime_version"],
            ) != (cfg.model, cfg.model_version, cfg.spacy_version):
                raise ValueError("retained native producer differs from demanded model/runtime")
            prefix = f"spacy/{view.ref.id}/"
            if not container.startswith(prefix) or not container.endswith("/block"):
                raise ValueError("unsupported retained native block identity recipe")
            block_id = container[len(prefix) : -len("/block")]
            pieces = tuple(
                ProjectedPiece(
                    item_ref=p.get("item_ref"), **{k: v for k, v in p.items() if k != "item_ref"}
                )
                for p in view.pieces
                if start <= p["start"] < p["end"] <= end
            )
            sentence_ids = list(dict.fromkeys(row["sentence"] for row in rows if "sentence" in row))
            sentences = []
            for key in sentence_ids:
                spans = [
                    e
                    for oid in annotations[key]["occurrences"]
                    for e in occurrences[oid]["extents"]
                ]
                sentences.append(SentenceAnnotation(spans[0]["start"], spans[-1]["end"]))
            tokens = []
            for (_annotation, extents), row in zip(population, rows, strict=True):
                a, b = extents[0]["start"], extents[-1]["end"]
                if view.text[a:b] != row["text"]:
                    raise ValueError("retained native token differs from exact source text")
                tokens.append(
                    TokenAnnotation(
                        a,
                        b,
                        row["space"],
                        row["source_role"],
                        row.get("lemma", ""),
                        row.get("pos", ""),
                        row.get("tag", ""),
                        tuple(row.get("morphology", ())),
                        row.get("dependency", ""),
                        row.get("native_head", row["index"]),
                        sentence_ids.index(row["sentence"]) if "sentence" in row else None,
                        tuple(i for i, p in enumerate(pieces) if p.start < b and a < p.end),
                    )
                )
            by_pointer = {item["self_ref"]: item for item in view.items}
            display = tuple(
                (p.start, p.end)
                for p in pieces
                if p.item_ref in by_pointer
                and by_pointer[p.item_ref].get("label") == "formula"
                and by_pointer.get(by_pointer[p.item_ref].get("parent", {}).get("$ref"), {}).get(
                    "label"
                )
                != "inline"
            )
            layout = TextLayout(
                start,
                end,
                sha256(view.text[start:end].encode()).hexdigest(),
                tuple(TextToken(t.start, t.end, t.space, t.role) for t in tokens),
                display,
                native_run["layout_recipe"],
            )
            statuses = {a["family"]: a["status"] for a in native_run.get("availability", ())}
            availability = tuple(
                AnnotationAvailability(column, statuses.get(SPACY_COLUMNS[column], "absent"))
                for column in _ATTRIBUTES
            )
            components = tuple(ComponentPin(**row) for row in native_run.get("components", ()))
            layout_digest = digest(asdict(layout))
            profile_digest = digest(effective_profile.identity())
            identity = dict(
                source=asdict(source),
                block_id=block_id,
                kind=block["native_label"],
                native_pieces=[p.to_wire() for p in pieces],
                layout_digest=layout_digest,
                profile_digest=profile_digest,
                components=[asdict(c) for c in components],
                pipeline_config_digest=native_run["configuration_digest"],
            )
            result.append(
                PrimaryAnnotationProduct(
                    primary_layers=layers,
                    source=source,
                    block_id=block_id,
                    kind=block["native_label"],
                    block_start=start,
                    block_end=end,
                    display_spans=display,
                    text_digest=layout.text_digest,
                    native_pieces=pieces,
                    layout_digest=layout_digest,
                    layout_recipe=layout.recipe,
                    profile_recipe=effective_profile.recipe,
                    profile_digest=profile_digest,
                    spacy_version=cfg.spacy_version,
                    model=cfg.model,
                    model_version=cfg.model_version,
                    components=components,
                    pipeline_config_digest=native_run["configuration_digest"],
                    availability=availability,
                    tokens=tuple(tokens),
                    sentences=tuple(sentences),
                    dependency_digest=digest(identity),
                )
            )
    return tuple(sorted(result, key=lambda product: product.block_start))
