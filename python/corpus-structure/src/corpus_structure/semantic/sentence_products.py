"""Declared learned-spaCy sentences/tokens over one captured original source.

The existing atom-preserving tokenizer/layout and GPU host own computation. This
owner retains typed original coordinates, closed inventories and execution receipts;
it performs no source discovery, scientific inference or native publication.
"""

from __future__ import annotations

import base64
import inspect
import json
from bisect import bisect_left
from collections.abc import Callable, Mapping
from contextlib import nullcontext
from dataclasses import asdict, dataclass, field, replace
from functools import cached_property
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Protocol

import yaml
from pydantic import BaseModel

from corpus_structure.ingest.sentences import (
    Block,
    SentenceConfig,
    make_doc,
    pipeline,
    prepare_layout,
)

from .data_operation_model import SubjectContext
from .data_operation_outcomes import successful_return_outcome
from .identity import canonical_bytes
from .source_products import FrozenNativeSource, source_product_inputs, source_subject
from .types import PreparationProfile, PreparedRelease, SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from corpus_structure.methods.native_host import NativeHostGroup

    from .data_operation_admission import PreparedCapabilityIdentity
    from .data_operation_bindings import BindingResult
    from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation
    from .data_operation_ports import PortCompletion, PythonRoleValue

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-sentences.yaml"


def sentence_product_inputs(
    bundle: SourceBundle, *, profile: PreparationProfile | None = None
) -> SourceBundle:
    from .data_product_reference import reference_inputs

    bundle = reference_inputs(source_product_inputs(bundle, profile=profile))
    names = {source.name for source in bundle.sources}
    if names & {"data_operation_sentences", "data_operation_sentences_root"}:
        raise ValueError("sentence profile uses reserved source schema names")
    root = "data_operation_sentences_root"
    return SourceBundle(
        root,
        (
            *bundle.sources,
            SourceArtifact("data_operation_sentences", _MODEL.read_bytes()),
            SourceArtifact(
                root,
                yaml.safe_dump(
                    {
                        "id": "urn:corpus:data-operation-sentences-root",
                        "name": root,
                        "imports": [bundle.root, "data_operation_sentences"],
                    }
                ).encode(),
            ),
        ),
    )


def _id(source, kind, block_id, start, end):
    return sha256(
        canonical_bytes(
            {"source": source, "kind": kind, "block_id": block_id, "start": start, "end": end}
        )
    ).hexdigest()


@dataclass(frozen=True)
class SourceAnnotations:
    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    execution_receipts: tuple[bytes, ...] = ()
    subject_context: SubjectContext | None = None
    partitions: tuple[bytes, ...] | None = None

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    @cached_property
    def semantic_id(self) -> str:
        from .data_operation_identity import body_identity, contextual_product_identity

        kind = next(
            identity.key
            for identity in self.model.identities
            if identity.owner == self.prepared.index.definitions["DdoSourceAnnotations"].iri
            and identity.domain == "kind"
        )
        value = (
            json.loads(self.content)
            if self.partitions is not None
            else self.value.model_dump(mode="python", exclude_unset=True)
        )
        return contextual_product_identity(
            kind=kind,
            context=self._publication_context(),
            body=body_identity(value).key,
        ).key

    @property
    def configuration(self):
        return SentenceConfig.model_validate(json.loads(self.content)["configuration"])

    @property
    def value(self) -> BaseModel:
        content = self.content
        if self.partitions is not None:
            body = json.loads(content)
            body.pop("rows")
            content = canonical_bytes(body)
        return self.prepared.validate_json("DdoSourceAnnotations", content)

    def inventory(self, kind: str) -> tuple[dict[str, Any], ...]:
        if kind not in {"sentence", "token"}:
            raise ValueError("unknown native sentence inventory kind")
        return tuple(
            row for row in source_annotation_member_values(self) if row["record_type"] == kind
        )


_TOKEN_FIELDS = frozenset(
    (
        "start",
        "end",
        "space",
        "role",
        "lemma",
        "pos",
        "tag",
        "dependency",
        "morphology",
        "head",
        "sentence",
        "piece_indices",
    )
)


class AnnotationView(Protocol):
    @property
    def content(self) -> bytes: ...

    @property
    def partitions(self) -> tuple[bytes, ...] | None: ...


def source_annotation_blocks(
    value: Mapping[str, Any] | AnnotationView, partitions: tuple[bytes, ...] | None = None
) -> tuple[dict[str, Any], ...]:
    """Recover working block coordinates and columns from authenticated rows and layout."""
    from .data_operation_partitions import partition_header
    from .sentence_partitions import COLLECTION, blocks_from_packets

    if isinstance(value, Mapping):
        body = value
    else:
        partitions = value.partitions
        body = json.loads(value.content)
    if partitions is None:
        return tuple(body["blocks"])
    packets = tuple(json.loads(packet) for packet in partitions)
    if partition_header(packets) != body[COLLECTION]:
        raise ValueError("annotation rows differ from their selected collection commitment")
    rows = blocks_from_packets(packets)
    return tuple(
        _annotation_block(layout, block)
        for layout, block in zip(body["block_layouts"], rows, strict=True)
    )


def _annotation_block(layout, block):
    annotation = layout["annotation"]
    if (annotation["block_id"], annotation["block_start"], annotation["block_end"]) != (
        block.key,
        block.start,
        block.end,
    ):
        raise ValueError("annotation layout differs from its selected row partition")
    tokens, sentences, lexemes = [], [], []
    for row in block.rows:
        position = dict(start=block.start + row["start"], end=block.start + row["end"])
        if row["record_type"] == "sentence":
            if row["ordinal"] != len(sentences):
                raise ValueError("annotation sentence ordinals must be contiguous")
            sentences.append(position)
        elif row["record_type"] == "token":
            if row["ordinal"] != len(tokens):
                raise ValueError("annotation token ordinals must be contiguous")
            tokens.append({key: row[key] for key in _TOKEN_FIELDS if key in row} | position)
            lexemes.append(
                {
                    key: item
                    for key, item in row.items()
                    if key not in _TOKEN_FIELDS | {"record_type", "ordinal", "extent"}
                }
            )
        else:
            raise ValueError("unknown annotation record type")
    return dict(
        annotation=dict(annotation, tokens=tokens, sentences=sentences),
        piece_offset=layout["piece_offset"],
        lexemes=lexemes,
    )


def _annotation_row(block) -> dict[str, Any]:
    annotation = block["annotation"]
    return {
        **annotation,
        "source": {"content": canonical_bytes(annotation["source"]).decode()},
        "display_spans": [[span["start"], span["end"]] for span in annotation["display_spans"]],
        "native_pieces": [
            {"item_ref": None, "cell_index": None, "source_field": None, **piece}
            for piece in annotation["native_pieces"]
        ],
        "tokens": [{"sentence": None, **token} for token in annotation["tokens"]],
    }


def source_annotation_rows(value: Mapping[str, Any] | AnnotationView) -> tuple[dict[str, Any], ...]:
    """Restore the working AnnotationProduct columns without creating retained members."""
    return tuple(_annotation_row(block) for block in source_annotation_blocks(value))


def _restore_selected_annotation_rows(source, value, rows):
    from corpus_structure.ingest.annotations import AnnotationProfile, restore_annotations

    from .declared_record_sources import DeclaredNativeFrameSource

    selected = source.value
    if value["source"] != selected["source"] or value["selectors"] != selected["selectors"]:
        raise ValueError("retained annotations differ from their exact original source/scope")
    if not rows:
        return ()
    frame = DeclaredNativeFrameSource(source.content.decode(), rows[0]["source"]["content"])
    return restore_annotations(
        rows,
        source=frame,
        profile=AnnotationProfile(
            SentenceConfig.model_validate(value["configuration"]),
            execution_profile=value["execution_profile"],
        ),
        require_complete=False,
    )


def retained_source_annotation_products(source, native):
    """Restore captured blocks once from an authenticated nominal annotation input."""
    return _restore_selected_annotation_rows(
        source, json.loads(native.content), source_annotation_rows(native)
    )


def restore_selected_annotation_partition(source, header, layout, packet):
    """Read one block packet already acquired through its exact selected parent."""
    from .sentence_partitions import blocks_from_packets

    (block,) = blocks_from_packets((packet,))
    row = _annotation_row(_annotation_block(layout, block))
    (product,) = _restore_selected_annotation_rows(source, header, (row,))
    return product


def source_annotation_member_values(
    value: Mapping[str, Any] | AnnotationView,
) -> tuple[dict[str, Any], ...]:
    """Read original units from detached annotations; no second stored token inventory."""
    result = []
    blocks = source_annotation_blocks(value)
    if not isinstance(value, Mapping):
        value = json.loads(value.content)
    for block in blocks:
        annotation, lexemes = block["annotation"], block["lexemes"]
        sentences = annotation["sentences"]
        sentence_ids = [
            _id(value["source"], "sentence", annotation["block_id"], row["start"], row["end"])
            for row in sentences
        ]
        token_ids = [
            _id(value["source"], "token", annotation["block_id"], row["start"], row["end"])
            for row in annotation["tokens"]
        ]
        tokens_by_sentence: dict[str, list[str]] = {}
        for ordinal, (token, lexeme) in enumerate(zip(annotation["tokens"], lexemes, strict=True)):
            piece_indices = [block["piece_offset"] + index for index in token["piece_indices"]]
            body = {
                "record_type": "token",
                "local_id": token_ids[ordinal],
                "block_id": annotation["block_id"],
                "ordinal": ordinal,
                **{
                    key: token[key]
                    for key in (
                        "start",
                        "end",
                        "space",
                        "role",
                        "lemma",
                        "pos",
                        "tag",
                        "morphology",
                        "dependency",
                    )
                },
                **lexeme,
                "piece_indices": piece_indices,
            }
            if token.get("sentence") is not None:
                sentence_id = sentence_ids[token["sentence"]]
                body["sentence_ref"] = sentence_id
                tokens_by_sentence.setdefault(sentence_id, []).append(token_ids[ordinal])
            if token["dependency"]:
                body["head_ref"] = token_ids[token["head"]]
            result.append(body)
        for ordinal, (sentence, identifier) in enumerate(zip(sentences, sentence_ids, strict=True)):
            result.append(
                {
                    "record_type": "sentence",
                    "local_id": identifier,
                    "block_id": annotation["block_id"],
                    "ordinal": ordinal,
                    **sentence,
                    "token_ids": tokens_by_sentence.get(identifier, []),
                }
            )
    return tuple(result)


def source_annotation_packets(prepared, model, value):
    """Publish genuine native units from the already retained annotation population."""
    from .characterization_manifests import manifest_contract

    context = dict(
        subject=source_subject(value["source"]),
        subject_definition="original-source-view",
        original_source=value["source"]["document"],
        analyzed_scope=dict(source=value["source"], selectors=value["selectors"]),
    )
    contracts = {
        name: manifest_contract(prepared, model, name)
        for name in (
            "DdoNativeBlock",
            "DdoNativeToken",
            "DdoNativeSentence",
            "DdoSourceAnnotationManifest",
        )
    }
    packets = []
    for ordinal, block in enumerate(value["blocks"]):
        annotation = block["annotation"]
        start, end = annotation["block_start"], annotation["block_end"]
        identifier = _id(value["source"], "block", annotation["block_id"], start, end)
        packets.append(
            dict(
                member_id=identifier,
                kind_contract=contracts["DdoNativeBlock"],
                context=context,
                body=dict(
                    record_type="native_block",
                    local_id=identifier,
                    block_id=annotation["block_id"],
                    ordinal=ordinal,
                    start=start,
                    end=end,
                ),
            )
        )
    for row in source_annotation_member_values(value):
        name = "DdoNativeToken" if row["record_type"] == "token" else "DdoNativeSentence"
        body = {key: row[key] for key in ("local_id", "block_id", "ordinal", "start", "end")}
        body["record_type"] = "native_" + row["record_type"]
        packets.append(
            dict(
                member_id=row["local_id"],
                kind_contract=contracts[name],
                context=context,
                body=body,
            )
        )
    return [
        *packets,
        annotation_manifest(
            value,
            kind_contract=contracts["DdoSourceAnnotationManifest"],
        ),
    ]


def annotation_manifest(value, *, kind_contract):
    from .characterization_manifests import compact_manifest

    return compact_manifest(value, kind_contract)


def validate_source_annotations(
    prepared,
    model,
    value,
    source,
    *,
    receipts=(),
    subject_context=None,
    configuration=None,
    partitions=None,
):
    from corpus_structure.ingest.annotations import AnnotationProfile, restore_annotations

    from .declared_record_sources import DeclaredNativeFrameSource

    raw = dict(value)
    if set(raw) == {"header", "partitions"}:
        if partitions is not None:
            raise ValueError("explicit annotation partitions repeat the selected envelope")
        partitions = tuple(canonical_bytes(packet) for packet in raw["partitions"])
        raw = raw["header"]
    commitment = raw.pop("rows") if partitions is not None else None
    checked = prepared.validate_json("DdoSourceAnnotations", canonical_bytes(raw)).model_dump(
        mode="json", exclude_unset=True
    )
    if commitment is not None:
        checked["rows"] = commitment
    selected = source.value
    frozen_configuration = SentenceConfig.model_validate(checked["configuration"])
    if configuration is not None and configuration != frozen_configuration:
        raise ValueError("annotation configuration differs from its captured model profile")
    configuration = frozen_configuration
    if checked["source"] != selected["source"] or checked["selectors"] != selected["selectors"]:
        raise ValueError("source annotations differ from exact original source/scope")
    result = SourceAnnotations(
        canonical_bytes(checked), prepared, model, receipts, subject_context, partitions
    )
    blocks = source_annotation_blocks(result)
    if blocks:
        if configuration is None:
            raise ValueError("annotation validation requires its captured model configuration")
        rows = tuple(_annotation_row(block) for block in blocks)
        frame = DeclaredNativeFrameSource(source.content.decode(), rows[0]["source"]["content"])
        products = restore_annotations(
            rows,
            source=frame,
            profile=AnnotationProfile(
                configuration, execution_profile=checked["execution_profile"]
            ),
            require_complete=False,
        )
        pieces = selected["pieces"]
        piece_starts = [piece["start"] for piece in pieces]
        for product, block in zip(products, blocks, strict=True):
            if len(product.tokens) != len(block["lexemes"]):
                raise ValueError("native lexical columns differ from their actual token population")
            first = bisect_left(piece_starts, product.block_start)
            stop = bisect_left(piece_starts, product.block_end, lo=first)
            if (
                first == len(pieces)
                or piece_starts[first] != product.block_start
                or block["piece_offset"] != first
                or [piece.to_wire() for piece in product.native_pieces] != pieces[first:stop]
            ):
                raise ValueError("annotations differ from original selected native pieces")
            if any(
                not product.block_start <= row.start < row.end <= product.block_end
                for row in product.sentences
            ):
                raise ValueError("annotation sentences exceed the actual source block")
            if any(
                token.sentence is not None
                and (
                    not 0 <= token.sentence < len(product.sentences)
                    or not product.sentences[token.sentence].start
                    <= token.start
                    < token.end
                    <= product.sentences[token.sentence].end
                )
                for token in product.tokens
            ):
                raise ValueError("annotation token/sentence membership is not exact")
    from corpus_structure.methods.native_evidence_layers import SPACY_FAMILIES

    if len(checked["coverage"]) != len(SPACY_FAMILIES) or {
        row["family"] for row in checked["coverage"]
    } != set(SPACY_FAMILIES):
        raise ValueError("native family coverage omits or repeats a declared spaCy family")
    if any(row["eligible"] != selected["selectors"] for row in checked["coverage"]):
        raise ValueError("native family coverage differs from frozen eligible source")
    if checked["outcome"] != (
        "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in checked["coverage"])
        else "partial"
    ):
        raise ValueError("native product outcome differs from actual family coverage")
    if partitions is not None:
        from .characterization_manifests import manifest_contract

        expected_members = [
            annotation_manifest(
                checked,
                kind_contract=manifest_contract(prepared, model, "DdoSourceAnnotationManifest"),
            )
        ]
    else:
        expected_members = source_annotation_packets(prepared, model, checked)
    if checked["members"] != expected_members:
        raise ValueError("annotation members differ from their actual retained native population")
    return result


@dataclass(frozen=True)
class _Block:
    block_id: str
    start: int
    end: int
    block: Block
    pieces: tuple[int, ...]


def _blocks(source: FrozenNativeSource):
    from corpus_structure.methods.source_preparation import annotation_block_owner

    selected = source.value
    nodes = {item["self_ref"]: item for item in source.native_items()}
    ancestry = source.selector_index()
    grouped: dict[str, list[int]] = {}
    for index, piece in enumerate(selected["pieces"]):
        if piece["kind"] == "native_text":
            grouped.setdefault(annotation_block_owner(piece["item_ref"], nodes), []).append(index)
    blocks, coverage = [], []
    for pointer, indices in grouped.items():
        populations = (
            [[index] for index in indices]
            if nodes.get(pointer, {}).get("label") == "table"
            else [indices]
        )
        for members in populations:
            start, end = (
                selected["pieces"][members[0]]["start"],
                selected["pieces"][members[-1]]["end"],
            )
            block_id = (
                pointer
                if nodes.get(pointer, {}).get("label") != "table"
                else pointer
                + ":cell:"
                + str(selected["pieces"][members[0]].get("cell_index", members[0]))
            )
            # Selection is already frozen. Do not turn a partial fragment into a
            # new canonical sentence or silently widen beyond the selected scope.
            pointers = {selected["pieces"][index]["item_ref"] for index in members}
            pages = {
                row["page_no"] for pointer_ in pointers for row in nodes[pointer_].get("prov", ())
            }
            relevant = [
                selector
                for selector in selected["selectors"]
                if (any(ancestry.matches(selector, member) is not False for member in pointers))
                and ("page" not in selector or selector["page"] in pages)
                and selector.get("start", 0) < end
                and start < selector.get("end", len(selected["text"]))
            ]
            if not relevant:
                continue
            eligible = any(
                selector.get("start", 0) <= start
                and end <= selector.get("end", len(selected["text"]))
                and all(ancestry.matches(selector, member) is True for member in pointers)
                and ("page" not in selector or pages == {selector["page"]})
                for selector in relevant
            )
            if not eligible:
                coverage.append(
                    dict(
                        block_id=block_id,
                        native_pointer=pointer,
                        start=start,
                        end=end,
                        outcome="unsupported",
                        reason="selected scope does not contain the complete original block",
                    )
                )
                continue
            text = selected["text"][start:end]
            if not text.strip():
                coverage.append(
                    dict(
                        block_id=block_id,
                        native_pointer=pointer,
                        start=start,
                        end=end,
                        outcome="empty",
                    )
                )
                continue
            inline, display, markers = [], [], []
            for index in members:
                piece = selected["pieces"][index]
                node = nodes[piece["item_ref"]]
                extent = (piece["start"] - start, piece["end"] - start)
                if node["label"] == "formula":
                    inline.append(extent)
                    if nodes.get(node.get("parent", {}).get("$ref"), {}).get("label") != "inline":
                        display.append(extent)
                if node["label"] in {"reference", "reference_marker"}:
                    markers.append(extent)
            blocks.append(
                _Block(
                    block_id,
                    start,
                    end,
                    Block(text, tuple(inline), tuple(display), tuple(markers)),
                    tuple(range(members[0], members[-1] + 1)),
                )
            )
            coverage.append(
                dict(
                    block_id=block_id,
                    native_pointer=pointer,
                    start=start,
                    end=end,
                    outcome="complete",
                )
            )
    projected = {
        piece.get("item_ref") for piece in selected["pieces"] if piece["kind"] == "native_text"
    }
    for item in selected["items"]:
        pointer = item["self_ref"]
        has_text = any(
            isinstance(item.get(field), str) and item[field].strip() for field in ("text", "orig")
        )
        has_cell_context = any(
            cell.get("text") or cell.get("ref")
            for cell in item.get("data", {}).get("table_cells", [])
        )
        if (
            pointer not in projected
            and (has_text or has_cell_context)
            and any(
                ancestry.matches(selector, pointer) is not False
                for selector in selected["selectors"]
            )
        ):
            coverage.append(
                dict(
                    block_id=pointer,
                    native_pointer=pointer,
                    start=0,
                    end=0,
                    outcome="unsupported",
                    reason="original native atom has no projected character interval",
                )
            )
    return tuple(blocks), coverage


def spacy_family_coverage(selected, block_coverage, annotation_columns):
    """Declare native families from actual layout examination and Doc column standing."""
    from corpus_structure.methods.native_evidence_layers import SPACY_COLUMNS, SPACY_FAMILIES

    columns = {row["block_id"]: row["attributes"] for row in annotation_columns}
    native_attributes = {family: attribute for attribute, family in SPACY_COLUMNS.items()}
    result = []
    for family in SPACY_FAMILIES:
        examined, unexamined, statuses, reasons = [], [], [], []
        for block in block_coverage:
            scope = {
                "projection": selected["source"]["projection"],
                "start": block["start"],
                "end": block["end"],
            }
            if "native_pointer" in block:
                scope["native_pointer"] = block["native_pointer"]
            status = block["outcome"]
            if status == "complete":
                status = (
                    "complete"
                    if family == "spacy.tokens"
                    else columns[block["block_id"]][native_attributes[family]]
                )
            statuses.append(status)
            (unexamined if status == "unsupported" else examined).append(scope)
            if "reason" in block:
                reasons.append(block["reason"])
            if status in {"absent", "partial"}:
                reasons.append("native " + native_attributes[family] + " column is " + status)
        if not statuses:
            outcome, availability = "empty", "available"
            examined = selected["selectors"]
        elif set(statuses) <= {"empty", "not_applicable"}:
            outcome, availability = "empty", "available"
        elif set(statuses) <= {"complete", "empty", "not_applicable"}:
            outcome, availability = "complete", "available"
        elif set(statuses) == {"unsupported"}:
            outcome, availability = "unsupported", "unsupported"
        elif set(statuses) == {"absent"}:
            outcome, availability = "unknown", "unavailable"
        else:
            outcome, availability = (
                "partial",
                "available"
                if any(status in {"complete", "partial"} for status in statuses)
                else "unknown",
            )
        result.append(
            dict(
                family=family,
                eligible=selected["selectors"],
                examined=examined,
                unexamined=unexamined,
                availability=availability,
                outcome=outcome,
                **({"reason": "; ".join(dict.fromkeys(reasons))} if reasons else {}),
            )
        )
    return result


def _detach_annotation_block(
    selected, block, layout, doc, source_pin, configuration, execution_profile
) -> dict[str, Any]:
    from corpus_structure.ingest.annotations import AnnotationInput, AnnotationProfile, annotate
    from corpus_structure.ingest.pdf_hierarchy import ProjectedPiece

    nodes = {row["self_ref"]: row for row in selected["items"]}
    label = nodes.get(block.block_id.split(":cell:")[0], {}).get("label")
    kind = (
        "table_cell"
        if label == "table"
        else "list_item"
        if label == "list_item"
        else "caption"
        if label == "caption"
        else "paragraph"
    )
    # ProjectedPiece.to_wire omits absent optional fields, including a synthetic
    # separator's item_ref. Restore that actual absence at the typed boundary.
    restored_pieces = []
    for index in block.pieces:
        fields: dict[str, Any] = {"item_ref": None, **selected["pieces"][index]}
        restored_pieces.append(ProjectedPiece(**fields))
    pieces = tuple(restored_pieces)
    supplied = AnnotationInput(source_pin, block.block_id, kind, block.block, layout, pieces)
    (annotation,) = annotate(
        (supplied,),
        AnnotationProfile(configuration, execution_profile=execution_profile),
        processed_docs=(doc,),
        require_complete=False,
    )

    def present(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: present(item) for key, item in value.items() if item is not None}
        if isinstance(value, (tuple, list)):
            return [present(item) for item in value]
        return value

    value: dict[str, Any] = present(asdict(annotation))
    value["source"] = source_pin.values()
    value["display_spans"] = [{"start": a, "end": b} for a, b in annotation.display_spans]
    lexemes = [
        dict(
            lower=token.lower_,
            is_alpha=token.is_alpha,
            is_space=token.is_space,
            is_punct=token.is_punct,
            is_quote=token.is_quote,
            like_num=token.like_num,
            sent_start=token.is_sent_start,
        )
        for token in doc
    ]
    return {"annotation": value, "lexemes": present(lexemes), "piece_offset": block.pieces[0]}


@dataclass(frozen=True)
class PreparedSentenceProfile:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    configuration: SentenceConfig
    asset_digest: str
    selection: Any

    def run(
        self,
        source: FrozenNativeSource,
        *,
        check_active: Callable[[], None] = lambda: None,
        subject_context: SubjectContext | None = None,
        host: NativeHostGroup | None = None,
        source_pin=None,
    ) -> SourceAnnotations:
        from corpus_structure.methods.native_host import NativeHostGroup
        from corpus_structure.settings import Settings

        check_active()
        source = FrozenNativeSource.acquire(self.prepared, source.value)
        selected = source.value
        blocks, coverage = _blocks(source)
        records, receipts, annotation_columns = [], [], []
        selection = self.selection
        if blocks:
            nlp = pipeline(self.configuration)  # Tokenizer only; learned weights stay in CUDA host.
            if source_pin is None:
                raise ValueError(
                    "source annotations require their actual admitted source/member pin"
                )
            if nlp.selection().native.fingerprint != selection.native.fingerprint:
                raise ValueError(
                    "tokenizer execution profile differs from captured spaCy selection"
                )
            if (
                sentence_profile_assets(self.configuration, selection=selection).digest
                != self.asset_digest
            ):
                raise ValueError("sentence model/assets changed after explicit preparation")
            # An explicitly supplied host belongs to the enclosing execution owner;
            # direct bounded calls acquire and drain their own original host.
            if host is None:
                settings = Settings()
                lifetime = NativeHostGroup(
                    settings.characterization_execution, settings.nemotron.endpoint
                )
            else:
                lifetime = nullcontext(host)
            with lifetime as active_host:
                active_host.declare((selection,))
                for offset in range(0, len(blocks), self.configuration.batch_size):
                    check_active()
                    admitted = []
                    for block in blocks[offset : offset + self.configuration.batch_size]:
                        layout = prepare_layout(nlp, block.block, start=block.start)
                        original = make_doc(nlp, block.block, layout, start=block.start)
                        admitted.append((block, layout, original))
                    result = active_host.infer_result(
                        selection,
                        {
                            "version": "spacy-host-1",
                            "documents": [
                                {"content": base64.b64encode(original.to_bytes()).decode("ascii")}
                                for _block, _layout, original in admitted
                            ],
                        },
                        check_active,
                    )
                    receipts.append(canonical_bytes(asdict(result.receipt)))
                    docs = nlp.decode(result.payload["documents"])
                    if len(docs) != len(admitted):
                        raise ValueError("spaCy changed the original admitted document population")
                    for (block, layout, original), doc in zip(admitted, docs, strict=True):
                        if doc.text != original.text or [
                            (token.idx, len(token.text)) for token in doc
                        ] != [(token.idx, len(token.text)) for token in original]:
                            raise ValueError("spaCy changed the original admitted token population")
                        detached = _detach_annotation_block(
                            selected,
                            block,
                            layout,
                            doc,
                            source_pin,
                            self.configuration,
                            selection.native.fingerprint,
                        )
                        records.append(detached)
                        annotation_columns.append(
                            dict(
                                block_id=block.block_id,
                                start=block.start,
                                end=block.end,
                                attributes={
                                    row["attribute"]: row["status"]
                                    for row in detached["annotation"]["availability"]
                                },
                            )
                        )
        value = dict(
            source=selected["source"],
            selectors=selected["selectors"],
            outcome="partial"
            if any(row["outcome"] == "unsupported" for row in coverage)
            else "complete",
            block_coverage=coverage,
            coverage=spacy_family_coverage(selected, coverage, annotation_columns),
            blocks=records,
            configuration=self.configuration.model_dump(mode="json"),
            execution_profile=selection.native.fingerprint,
        )
        value["outcome"] = (
            "complete"
            if all(row["outcome"] in {"complete", "empty"} for row in value["coverage"])
            else "partial"
        )
        from .characterization_manifests import manifest_contract
        from .data_operation_partitions import partition_header
        from .sentence_partitions import partition_source_annotations

        value["members"] = [
            annotation_manifest(
                value,
                kind_contract=manifest_contract(
                    self.prepared, self.model, "DdoSourceAnnotationManifest"
                ),
            )
        ]
        header, packets = partition_source_annotations(value)
        header["rows"] = partition_header(packets)
        check_active()
        return validate_source_annotations(
            self.prepared,
            self.model,
            header,
            source,
            receipts=tuple(receipts),
            configuration=self.configuration,
            subject_context=subject_context,
            partitions=tuple(canonical_bytes(packet) for packet in packets),
        )


def prepare_sentence_profile(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    configuration: SentenceConfig | None = None,
    *,
    selection=None,
) -> PreparedSentenceProfile:
    configuration = configuration or SentenceConfig(exclude=("ner",))
    if (
        not {
            "DdoSelectedNativeSource",
            "DdoAnnotationToken",
            "DdoSourceAnnotationManifest",
            "DdoSourceAnnotations",
        }
        <= prepared.index.definitions.keys()
    ):
        raise ValueError("sentence preparation requires its acquired nominal source/product model")
    if selection is None:
        from corpus_structure.methods.native_profiles import spacy_selection

        selection = spacy_selection(configuration) if selection is None else selection
    return PreparedSentenceProfile(
        prepared,
        model,
        configuration,
        sentence_profile_assets(configuration, selection=selection).digest,
        selection,
    )


def sentence_provider_asset(selection):
    from corpus_structure.methods.native_profiles import spacy_observation_policy

    from .data_operation_provider_profiles import profile_asset

    return profile_asset(
        "sentences/provider-inference-profile", selection, spacy_observation_policy()
    )


def sentence_provider_attestation(selection):
    from corpus_structure.methods.native_profiles import spacy_observation_policy

    from .data_operation_provider_profiles import profile_attestation

    return profile_attestation(selection, spacy_observation_policy())


def sentence_execution_custody(
    configuration: SentenceConfig | None = None, *, selection=None
) -> SourceArtifact:
    """Physical host/transport/adapter code is exact runtime custody."""
    if selection is None:
        from corpus_structure.methods.native_profiles import spacy_selection

        selection = spacy_selection(configuration or SentenceConfig(exclude=("ner",)))
    root = Path(__file__).parent
    paths = (
        Path(__file__),
        root / "sentence_partitions.py",
        root.parent / "methods/native_profiles.py",
        root.parent / "ingest/hosted_spacy.py",
    )
    return SourceArtifact(
        "sentences/execution-custody",
        canonical_bytes(
            {
                "version": "spacy-execution-custody-v1",
                "configuration": (configuration or SentenceConfig(exclude=("ner",))).model_dump(
                    mode="json"
                ),
                "selection": selection.declaration(),
                "provider_profile": sentence_provider_attestation(selection),
                "files": [
                    (str(path.relative_to(root.parent)), path.read_bytes().hex()) for path in paths
                ],
            }
        ),
        runtime_transport=True,
    )


def sentence_profile_assets(
    configuration: SentenceConfig | None = None, *, selection=None
) -> SourceArtifact:
    from corpus_structure.methods.native_evidence_layers import SPACY_COLUMNS, SPACY_FAMILIES
    from corpus_structure.methods.native_profiles import spacy_observation_policy, spacy_selection

    from .operation_code_assets import code_asset

    configuration = configuration or SentenceConfig(exclude=("ner",))
    selection = spacy_selection(configuration) if selection is None else selection
    root = Path(__file__).parents[1]
    return code_asset(
        "sentences/profile-assets",
        (execute_sentence_profile, PreparedSentenceProfile.run, validate_source_annotations),
        (
            ("sentence-annotations", _MODEL),
            ("source-products", root / "model/semantic/data-operation-source.yaml"),
        ),
        parameters={
            "native_families": SPACY_FAMILIES,
            "native_family_columns": SPACY_COLUMNS,
            "inference": json.loads(
                selection.native.identity_projections(
                    inference_policy=spacy_observation_policy()
                ).inference.canonical_input
            ),
        },
    )


def sentence_operation_sources(configuration: SentenceConfig | None = None, *, selection=None):
    from corpus_structure.methods.native_profiles import spacy_selection

    from .python_operation_sources import PythonSource, PythonSourceCollection

    selection = (
        spacy_selection(configuration or SentenceConfig(exclude=("ner",)))
        if selection is None
        else selection
    )
    path = Path(__file__).parents[1] / "methods/sentence_evidence.py"
    return PythonSourceCollection(
        (
            PythonSource(
                "corpus_structure.semantic.sentence_products",
                Path(__file__).read_bytes(),
                str(Path(__file__)),
            ),
            PythonSource(
                "corpus_structure.methods.sentence_evidence", path.read_bytes(), str(path)
            ),
            PythonSource(
                "corpus_structure.semantic.sentence_partitions",
                Path(__file__).with_name("sentence_partitions.py").read_bytes(),
                str(Path(__file__).with_name("sentence_partitions.py")),
            ),
        ),
        boundary_contracts=(
            sentence_provider_asset(selection),
            sentence_profile_assets(configuration, selection=selection),
            sentence_execution_custody(configuration, selection=selection),
        ),
    )


def execute_sentence_profile(receiver, source: FrozenNativeSource) -> SourceAnnotations:
    return receiver.profile.run(
        source,
        check_active=receiver.check_active,
        host=receiver.host,
        source_pin=receiver.source_pin,
    )


@dataclass(frozen=True)
class SourceAnnotationReadings:
    """Immediate native/construction boundary consumes retained canonical units only."""

    product: SourceAnnotations
    source: FrozenNativeSource
    _sentences: tuple[bytes, ...] = field(init=False, repr=False)
    _sentence_by_id: Mapping[str, bytes] = field(init=False, repr=False)
    _token_by_id: Mapping[str, bytes] = field(init=False, repr=False)

    def __post_init__(self):
        validate_source_annotations(
            self.product.prepared,
            self.product.model,
            json.loads(self.product.content),
            self.source,
            configuration=self.product.configuration,
            partitions=self.product.partitions,
        )
        ordered_sentences, sentences, tokens = [], {}, {}
        for row in source_annotation_member_values(self.product):
            content = canonical_bytes(row)
            if row["record_type"] == "sentence":
                ordered_sentences.append(content)
                sentences[row["local_id"]] = content
            else:
                tokens[row["local_id"]] = content
        object.__setattr__(self, "_sentences", tuple(ordered_sentences))
        object.__setattr__(
            self,
            "_sentence_by_id",
            MappingProxyType(sentences),
        )
        object.__setattr__(
            self,
            "_token_by_id",
            MappingProxyType(tokens),
        )

    def sentences(self, *, start: int = 0, end: int | None = None):
        text = self.source.value["text"]
        end = len(text) if end is None else end
        if not 0 <= start <= end <= len(text):
            raise ValueError("sentence read scope exceeds original source")
        return tuple(
            row
            for content in self._sentences
            for row in (json.loads(content),)
            if start <= row["start"] < row["end"] <= end
        )

    def tokens(self, sentence: str):
        selected = self._sentence_by_id.get(sentence)
        if selected is None:
            raise ValueError("sentence read requires a retained original sentence ID")
        return tuple(
            json.loads(self._token_by_id[identifier])
            for identifier in json.loads(selected)["token_ids"]
        )

    def native_annotations(self, sentence: str):
        """Retained actual columns for this canonical sentence, with no NLP call."""
        return self.tokens(sentence)

    def annotation_availability(self):
        body = json.loads(self.product.content)
        layouts = body["block_layouts"] if self.product.partitions is not None else body["blocks"]
        return tuple(
            dict(
                block_id=row["block_id"],
                start=row["block_start"],
                end=row["block_end"],
                attributes={item["attribute"]: item["status"] for item in row["availability"]},
            )
            for row in (layout["annotation"] for layout in layouts)
        )


@dataclass(frozen=True)
class PreparedSentencePort:
    """Admitted prepared implementation of the original source-native entrypoint."""

    identity: PreparedCapabilityIdentity
    operation: EffectiveOperation
    profile: PreparedSentenceProfile
    authorize: Callable[[PreparedCapabilityIdentity], None]
    host: NativeHostGroup | None = None
    custody: tuple[SourceArtifact, ...] = ()
    sources: Any = None

    @property
    def logical_signature(self):

        return inspect.Signature(
            (
                inspect.Parameter(
                    "source", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=FrozenNativeSource
                ),
            ),
            return_annotation=SourceAnnotations,
        )

    def _verify(self) -> None:
        from dataclasses import asdict

        from .data_operation_ports import PortRefusal

        model = self.profile.model
        ids = {(item.owner, item.domain): item.key for item in model.identities}
        operation = self.operation
        if operation.implementation_root is None:
            raise PortRefusal("sentence capability lacks an implementation root")
        expected = dict(
            model_digest=sha256(model.content).hexdigest(),
            operation=operation.semantic_id,
            definition=ids[operation.semantic_id, "definition"],
            recipe=ids[operation.semantic_id, "recipe"],
            implementation=ids[operation.implementation_root, "implementation-slice"],
            declaration="corpus_structure.methods.sentence_evidence.SentenceEvidenceOperation.run",
            capabilities=canonical_bytes(asdict(operation.capabilities)),
            eligibility=ids[operation.semantic_id, "eligibility"],
        )
        required_sources = sentence_operation_sources(self.profile.configuration)
        sources = self.sources if self.sources is not None else required_sources
        actual_sources = {source.module: source for source in sources.sources}
        if any(
            source.module not in actual_sources
            or actual_sources[source.module].content != source.content
            for source in required_sources.sources
        ):
            raise PortRefusal("sentence capability lacks its required original source subset")
        if any(Path(source.filename).read_bytes() != source.content for source in sources.sources):
            raise PortRefusal("sentence acquired source archive changed")
        from .data_operation_provider_profiles import operation_profile

        profile = operation_profile(self.operation, sources.boundary_contracts)
        if (
            profile is None
            or profile["identity"]
            != sentence_provider_attestation(self.profile.selection)["identity"]
        ):
            raise PortRefusal("acquired sentence provider differs from captured semantic profile")
        retained = {artifact.name: artifact for artifact in self.custody}
        if len(retained) != len(self.custody) or any(
            retained.get(actual.name) != actual
            for actual in (
                sentence_profile_assets(
                    self.profile.configuration, selection=self.profile.selection
                ),
                sentence_execution_custody(
                    self.profile.configuration, selection=self.profile.selection
                ),
            )
        ):
            raise PortRefusal("sentence runtime/parser assets differ from acquired custody")
        expected["source_digest"] = sha256(
            canonical_bytes(
                tuple(
                    (source.module, sha256(source.content).hexdigest())
                    for source in sources.sources
                )
            )
        ).hexdigest()
        if any(getattr(self.identity, name) != value for name, value in expected.items()):
            raise PortRefusal(
                "sentence capability differs from admitted source/operation correspondence"
            )
        # Prepared opaque resources are not closed Python functions, but their
        # original endpoint and resource bridge still require actual loaded-code
        # correspondence, not only a matching on-disk file.
        from types import CodeType

        from corpus_structure.methods import sentence_evidence as endpoint

        def declared(content, filename, *path):
            code = compile(content, filename, "exec", dont_inherit=True)
            for name in path:
                code = next(
                    item
                    for item in code.co_consts
                    if isinstance(item, CodeType) and item.co_name == name
                )
            return code

        source = actual_sources[endpoint.__name__]
        runtime = inspect.getattr_static(endpoint.SentenceEvidenceOperation, "run")
        if (
            not inspect.isfunction(runtime)
            or runtime.__code__
            != declared(source.content, source.filename, "SentenceEvidenceOperation", "run")
            or runtime.__globals__ is not endpoint.__dict__
        ):
            raise PortRefusal("loaded sentence endpoint differs from acquired implementation")
        if (
            endpoint.execute_sentence_profile is not execute_sentence_profile
            or execute_sentence_profile.__code__
            != declared(Path(__file__).read_bytes(), __file__, "execute_sentence_profile")
        ):
            raise PortRefusal(
                "loaded sentence resource bridge differs from acquired implementation"
            )
        if self.profile.run.__func__.__code__ != declared(
            Path(__file__).read_bytes(), __file__, "PreparedSentenceProfile", "run"
        ):
            raise PortRefusal(
                "loaded sentence resource algorithm differs from acquired implementation"
            )
        from corpus_structure.ingest import annotations

        for function in (_blocks, _detach_annotation_block, validate_source_annotations):
            if function.__code__ != declared(
                Path(__file__).read_bytes(), __file__, function.__name__
            ):
                raise PortRefusal("loaded sentence semantic algorithm differs from acquired source")
        for function in (annotations.annotation_availability, annotations.native_token_columns):
            if (
                function.__code__
                != declared(
                    Path(annotations.__file__).read_bytes(), annotations.__file__, function.__name__
                )
                or function.__globals__ is not annotations.__dict__
            ):
                raise PortRefusal("loaded native annotation columns differ from acquired source")
        contracts = {item.name: item.digest for item in sources.boundary_contracts}
        boundaries = (
            *operation.assets,
            *(
                boundary
                for implementation in model.implementation_slices
                if implementation.root == operation.implementation_root
                for boundary in implementation.boundaries
            ),
        )
        if not operation.assets or any(
            contracts.get(boundary.contract) != boundary.content_digest for boundary in boundaries
        ):
            raise PortRefusal(
                "sentence parser assets differ from explicitly acquired boundary custody"
            )
        if self.identity.assets != canonical_bytes(
            tuple(asdict(boundary) for boundary in boundaries)
        ):
            raise PortRefusal("sentence capability has another acquired resource boundary")
        self.authorize(self.identity)

    def _source(self, values, binding):
        from .data_operation_ports import PortRefusal, PythonRoleValue
        from .data_operation_values import decode_semantic_value

        inputs = tuple(role for role in self.operation.roles if role.direction == "input")
        contracts = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        if len(values) != 1 or not isinstance(values[0], PythonRoleValue):
            raise PortRefusal("sentence capability requires one typed selected-source role")
        value = values[0]
        if value.role != inputs[0].name or value.kind_contract != contracts[inputs[0].kind, "kind"]:
            raise PortRefusal("sentence source role has another nominal contract")
        actual = value.value
        if isinstance(actual, FrozenNativeSource):
            source = FrozenNativeSource.acquire(self.profile.prepared, actual.value)
        elif isinstance(actual, BaseModel):
            source = FrozenNativeSource.acquire(
                self.profile.prepared, actual.model_dump(mode="json", exclude_unset=True)
            )
        elif isinstance(actual, Mapping):
            source = FrozenNativeSource.acquire(self.profile.prepared, actual)
        else:
            raise PortRefusal("sentence source ingress requires its explicit selected-source value")
        if binding is not None and (
            not binding.sufficient
            or binding.operation != self.operation.semantic_id
            or binding.subject != source_subject(source.value["source"])
            or decode_semantic_value(json.loads(binding.parameters)) != {}
        ):
            raise PortRefusal("sentence input differs from the frozen source binding")
        return source

    def _source_pin(self, source, binding):
        from .data_operation_ports import PortRefusal
        from .declared_record_sources import DeclaredRecordSource, DeclaredSourcePin

        if binding is None or binding.subject_context is None:
            if not _blocks(source)[0]:
                return None
            raise PortRefusal("annotations require actual selected source/member custody")
        members = [
            member for role in binding.roles if role.role == "source" for member in role.members
        ]
        if len(members) != 1:
            raise PortRefusal("annotations require one authentic source/member pin")
        address = DeclaredRecordSource.from_bound(
            source, members[0], project=binding.subject_context.project_id
        )
        return DeclaredSourcePin(canonical_bytes(address.pin()).decode())

    def _completion(self, product, source, binding=None):
        if binding is not None:
            product = replace(product, subject_context=binding.subject_context)
        from ._data_operation_wire import WireKindContract, WireOutputMember
        from .data_operation_ports import PortCompletion, PortRefusal
        from .established_validity import RuleObservedInput, successful_rule_attestation
        from .sentence_partitions import partitioned_role

        # Product meaning uses the exact typed record's fields; display JSON and native
        # member packets are deliberate projections of that same validated product.
        if product.partitions is None:
            raise PortRefusal("annotation completion requires its partitioned population")
        model_value = json.loads(product.content)
        partitions = tuple(json.loads(packet) for packet in product.partitions)
        output = next(role for role in self.operation.roles if role.direction == "output")
        contracts = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        result = partitioned_role(
            output.name, contracts[output.kind, "kind"], model_value, partitions
        )
        attestations = ()
        if binding is not None and binding.subject_context is not None:
            from corpus_structure.methods.sentence_evidence import verify_annotation_source

            selected = source.value
            verify_annotation_source(
                model_value["source"],
                model_value["selectors"],
                selected["source"],
                selected["selectors"],
            )
            rule = next(
                rule
                for rule in self.profile.model.rules
                if rule.id == "segment.sentences/exact-source-scope"
            )
            kind = next(
                kind for kind in self.profile.model.kinds if kind.semantic_id == output.kind
            )
            assert result.meaning is not None
            packet: WireOutputMember = {
                "role": result.role,
                "position": 0,
                "multiplicity": 1,
                "product": {
                    "kind_contract": WireKindContract(result.kind_contract),
                    "body": json.loads(result.meaning),
                    "members": [json.loads(member) for member in result.members],
                },
            }
            attestations = (
                successful_rule_attestation(
                    rule,
                    kind,
                    self.operation.semantic_id,
                    packet,
                    binding.subject_context,
                    selected_inputs={"source": (RuleObservedInput(selected),)},
                ),
            )
        return PortCompletion(
            self.operation.semantic_id,
            (result,),
            execution_evidence=canonical_bytes(
                [json.loads(receipt) for receipt in product.execution_receipts]
            ),
            outcome=successful_return_outcome(self.operation),
            rule_attestations=attestations,
        )

    @property
    def native_selections(self):

        return (self.profile.selection,)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        """Submit through the invocation's one shared host and work-handle owner."""
        from corpus_structure.core.method import PreparedWork
        from corpus_structure.methods.sentence_evidence import SentenceEvidenceOperation

        self._verify()
        source = self._source(values, binding)
        check_active()

        def compute():
            self._verify()
            source_pin = self._source_pin(source, binding)
            product = SentenceEvidenceOperation(
                self.profile, check_active, execution_owner.native_hosts, source_pin=source_pin
            ).run(source)
            self._verify()
            return self._completion(product, source, binding)

        (completion,) = yield (PreparedWork(lambda: execution_owner.submit_python(compute)),)
        check_active()
        self._verify()
        return completion

    def invoke_python(
        self,
        values: tuple[PythonRoleValue, ...],
        *,
        binding: BindingResult | None = None,
        check_active: Callable[[], None] = lambda: None,
    ) -> PortCompletion:
        from corpus_structure.methods.sentence_evidence import SentenceEvidenceOperation

        self._verify()
        source = self._source(values, binding)
        product = SentenceEvidenceOperation(
            self.profile, check_active, self.host, source_pin=self._source_pin(source, binding)
        ).run(source)
        self._verify()
        return self._completion(product, source, binding)


def resolve_sentence_port(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    operation: str,
    *,
    identity: PreparedCapabilityIdentity,
    authorize: Callable[[PreparedCapabilityIdentity], None],
    host: NativeHostGroup | None = None,
    custody: tuple[SourceArtifact, ...] = (),
    sources=None,
    configuration: SentenceConfig | None = None,
) -> PreparedSentencePort:
    from .data_operation_ports import PortRefusal

    selected = model.operation(operation)
    inputs = tuple(role for role in selected.roles if role.direction == "input")
    outputs = tuple(role for role in selected.roles if role.direction == "output")
    expected = prepared.index.definitions
    if (
        selected.capabilities.forms != ("scalar",)
        or selected.capabilities.preparation != "resource"
        or selected.capabilities.cancellation != "cooperative"
        or selected.capabilities.ownership != "immutable"
        or selected.effects
        or len(inputs) != 1
        or len(outputs) != 1
        or inputs[0].kind != expected["DdoSelectedNativeSource"].iri
        or outputs[0].kind != expected["DdoSourceAnnotations"].iri
        or inputs[0].parameter != "source"
    ):
        raise PortRefusal("operation does not establish the prepared sentence profile")
    captured = [artifact for artifact in custody if artifact.name == "sentences/execution-custody"]
    if len(captured) != 1:
        raise PortRefusal("sentence acquisition requires one frozen configuration custody")
    record = json.loads(captured[0].content)
    frozen = SentenceConfig.model_validate(record["configuration"])
    from corpus_structure.methods.native_profiles import NativeProfile, NativeSelection

    declaration = record["selection"]
    native = NativeProfile.from_content(canonical_bytes(declaration["profile"]))
    if native.fingerprint != declaration["fingerprint"]:
        raise PortRefusal("spaCy captured selection fingerprint differs")
    selection = NativeSelection(native, Path(declaration["assets"]))
    if configuration is not None and configuration != frozen:
        raise PortRefusal("sentence acquisition configuration differs from frozen custody")
    port = PreparedSentencePort(
        identity,
        selected,
        prepare_sentence_profile(prepared, model, frozen, selection=selection),
        authorize,
        host,
        custody,
        sources,
    )
    port._verify()
    return port
