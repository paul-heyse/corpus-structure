"""Declared learned-spaCy sentences/tokens over one captured original source.

The existing atom-preserving tokenizer/layout and GPU host own computation. This
owner retains typed original coordinates, closed inventories and execution receipts;
it performs no source discovery, scientific inference or native publication.
"""

from __future__ import annotations

import base64
import inspect
import json
from collections.abc import Callable, Mapping
from contextlib import nullcontext
from dataclasses import asdict, dataclass, field, replace
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel

from corpus_structure.ingest.sentences import (
    Block,
    SentenceConfig,
    boundaries,
    make_doc,
    pipeline,
    prepare_layout,
)

from .data_operation_model import SubjectContext
from .identity import canonical_bytes
from .source_products import FrozenNativeSource, source_product_inputs, source_subject
from .types import PreparedRelease, SourceArtifact, SourceBundle

if TYPE_CHECKING:
    from corpus_structure.methods.native_host import NativeHostGroup

    from .data_operation_admission import PreparedCapabilityIdentity
    from .data_operation_bindings import BindingResult
    from .data_operation_model import EffectiveDataOperationModel, EffectiveOperation
    from .data_operation_ports import PortCompletion, PythonRoleValue

_MODEL = Path(__file__).resolve().parents[1] / "model/semantic/data-operation-sentences.yaml"


def sentence_product_inputs(bundle: SourceBundle) -> SourceBundle:
    bundle = source_product_inputs(bundle)
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
class SentenceInventory:
    content: bytes
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    execution_receipts: tuple[bytes, ...] = ()
    subject_context: SubjectContext | None = None

    def _publication_context(self):
        if self.subject_context is None:
            raise ValueError(
                "native product identity requires an explicit acquired subject context"
            )
        return self.subject_context

    @property
    def semantic_id(self) -> str:
        from .data_operation_identity import body_identity, contextual_product_identity

        kind = next(
            identity.key
            for identity in self.model.identities
            if identity.owner == self.prepared.index.definitions["DdoSentenceInventory"].iri
            and identity.domain == "kind"
        )
        value = self.value.model_dump(mode="python", exclude_unset=True)
        return contextual_product_identity(
            kind=kind,
            context=self._publication_context(),
            body=body_identity(value).key,
        ).key

    @property
    def value(self) -> BaseModel:
        return self.prepared.validate_json("DdoSentenceInventory", self.content)

    def inventory(self, kind: str) -> tuple[dict[str, Any], ...]:
        if kind not in {"sentence", "token"}:
            raise ValueError("unknown native sentence inventory kind")
        return tuple(
            packet["body"]
            for packet in json.loads(self.content)["members"]
            if packet["body"]["record_type"] == kind
        )


def validate_sentence_inventory(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    value: Mapping[str, Any],
    source: FrozenNativeSource,
    *,
    receipts: tuple[bytes, ...] = (),
    subject_context: SubjectContext | None = None,
) -> SentenceInventory:
    checked = prepared.validate_json("DdoSentenceInventory", canonical_bytes(value)).model_dump(
        mode="json", exclude_unset=True
    )
    selected = source.value
    expected_attributes = {"LEMMA", "POS", "TAG", "MORPH", "DEP", "SENT_START"}
    columns = checked["annotation_columns"]
    if len({row["block_id"] for row in columns}) != len(columns) or any(
        set(row["attributes"]) != expected_attributes
        or not 0 <= row["start"] < row["end"] <= len(selected["text"])
        for row in columns
    ):
        raise ValueError(
            "native annotation availability is not its closed actual attribute inventory"
        )
    if checked["source"] != selected["source"] or checked["selectors"] != selected["selectors"]:
        raise ValueError("sentence inventory differs from exact original source/scope")
    by_id = {}
    for packet in checked["members"]:
        body = packet["body"]
        if body["local_id"] in by_id or packet["member_id"] != body["local_id"]:
            raise ValueError("sentence inventory repeats or relabels an original member")
        if not 0 <= body["start"] < body["end"] <= len(selected["text"]):
            raise ValueError("sentence inventory exceeds original projection coordinates")
        if body["local_id"] != _id(
            checked["source"], body["record_type"], body["block_id"], body["start"], body["end"]
        ):
            raise ValueError("sentence member identity differs from original source interval")
        if packet["context"] != {
            "subject": source_subject(selected["source"]),
            "original_source": selected["source"]["document"],
            "analyzed_scope": {"source": selected["source"], "selectors": selected["selectors"]},
        }:
            raise ValueError("sentence member context differs from original source")
        nominal = "DdoNativeToken" if body["record_type"] == "token" else "DdoNativeSentence"
        if packet["kind_contract"] != next(
            identity.key
            for identity in model.identities
            if identity.owner == prepared.index.definitions[nominal].iri
            and identity.domain == "kind"
        ):
            raise ValueError("sentence member differs from its nominal contract")
        block = next((row for row in columns if row["block_id"] == body["block_id"]), None)
        if block is None or not block["start"] <= body["start"] < body["end"] <= block["end"]:
            raise ValueError("native unit exceeds its actual prepared block bounds")
        by_id[body["local_id"]] = (body["record_type"], body)
    if {row["block_id"] for row in columns} != {body["block_id"] for _kind, body in by_id.values()}:
        raise ValueError("native annotation availability differs from analyzed token blocks")
    for kind, body in by_id.values():
        if kind == "sentence":
            tokens = [by_id.get(identifier) for identifier in body["token_ids"]]
            if not tokens or any(
                token is None
                or token[0] != "token"
                or token[1].get("sentence_ref") != body["local_id"]
                or token[1]["block_id"] != body["block_id"]
                or not body["start"] <= token[1]["start"] < token[1]["end"] <= body["end"]
                for token in tokens
            ):
                raise ValueError("sentence/token inventory membership is not exact")
        else:
            if any(
                not 0 <= index < len(selected["pieces"])
                or selected["pieces"][index]["end"] <= body["start"]
                or body["end"] <= selected["pieces"][index]["start"]
                for index in body["piece_indices"]
            ):
                raise ValueError("token references another original source piece")
            if "head_ref" in body and (
                body.get("dependency", "") == ""
                or by_id.get(body["head_ref"], (None, {}))[0] != "token"
                or by_id[body["head_ref"]][1]["block_id"] != body["block_id"]
            ):
                raise ValueError("native dependency head is outside its original token block")
            if body.get("dependency") and "head_ref" not in body:
                raise ValueError("native dependency label lacks its actual head reference")
            if "sentence_ref" in body and by_id.get(body["sentence_ref"], (None,))[0] != "sentence":
                raise ValueError("token references a missing canonical sentence")
    for kind, body in by_id.values():
        if kind == "sentence":
            expected = [
                token["local_id"]
                for candidate_kind, token in by_id.values()
                if candidate_kind == "token" and token.get("sentence_ref") == body["local_id"]
            ]
            if body["token_ids"] != expected:
                raise ValueError("sentence inventory omits or reorders canonical token members")
        else:
            expected = [
                index
                for index, piece in enumerate(selected["pieces"])
                if piece["start"] < body["end"] and body["start"] < piece["end"]
            ]
            if body["piece_indices"] != expected:
                raise ValueError("token inventory omits original intersecting source pieces")
    from corpus_structure.methods.native_evidence_layers import SPACY_FAMILIES

    if {row["family"] for row in checked["coverage"]} != set(SPACY_FAMILIES) or len(
        checked["coverage"]
    ) != len(SPACY_FAMILIES):
        raise ValueError("native family coverage omits or repeats a declared spaCy family")
    if any(row["eligible"] != selected["selectors"] for row in checked["coverage"]):
        raise ValueError("native family coverage differs from frozen eligible source")
    if checked["outcome"] != (
        "complete"
        if all(row["outcome"] in {"complete", "empty"} for row in checked["coverage"])
        else "partial"
    ):
        raise ValueError("native product outcome differs from actual family coverage")
    return SentenceInventory(canonical_bytes(checked), prepared, model, receipts, subject_context)


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


def _native_records(selected, block, layout, doc):
    """Detach native labels and source units once from the same authenticated Doc."""
    from corpus_structure.ingest.annotations import annotation_availability, native_token_columns

    records = []
    sentences = [(block.start + a, block.start + b) for a, b in boundaries(block.block, doc)]
    sentence_ids = [_id(selected["source"], "sentence", block.block_id, a, b) for a, b in sentences]
    tokens = []
    for ordinal, (token, native) in enumerate(zip(layout.tokens, doc, strict=True)):
        identifier = _id(selected["source"], "token", block.block_id, token.start, token.end)
        sentence = next(
            (
                identity
                for (a, b), identity in zip(sentences, sentence_ids, strict=True)
                if a <= token.start < token.end <= b
            ),
            None,
        )
        body = dict(
            local_id=identifier,
            block_id=block.block_id,
            ordinal=ordinal,
            start=token.start,
            end=token.end,
            space=token.space,
            role=token.role,
            lower=native.lower_,
            is_alpha=native.is_alpha,
            is_space=native.is_space,
            is_punct=native.is_punct,
            is_quote=native.is_quote,
            like_num=native.like_num,
            piece_indices=[
                index
                for index in range(len(selected["pieces"]))
                if selected["pieces"][index]["start"] < token.end
                and token.start < selected["pieces"][index]["end"]
            ],
        )
        columns = native_token_columns(native)
        native_head = columns.pop("head")
        body.update(columns)
        body["sent_start"] = native.is_sent_start
        if columns["dependency"]:
            head = layout.tokens[native_head]
            body["head_ref"] = _id(
                selected["source"], "token", block.block_id, head.start, head.end
            )
        if sentence is not None:
            body["sentence_ref"] = sentence
        tokens.append(body)
        records.append(("token", body))
    for ordinal, ((start, end), identifier) in enumerate(zip(sentences, sentence_ids, strict=True)):
        records.append(
            (
                "sentence",
                dict(
                    local_id=identifier,
                    block_id=block.block_id,
                    ordinal=ordinal,
                    start=start,
                    end=end,
                    token_ids=[
                        token["local_id"]
                        for token in tokens
                        if token.get("sentence_ref") == identifier
                    ],
                ),
            )
        )
    availability = {row.attribute: row.status for row in annotation_availability(doc)}
    return records, dict(
        block_id=block.block_id, start=block.start, end=block.end, attributes=availability
    )


@dataclass(frozen=True)
class PreparedSentenceProfile:
    prepared: PreparedRelease
    model: EffectiveDataOperationModel
    configuration: SentenceConfig
    asset_digest: str

    def run(
        self,
        source: FrozenNativeSource,
        *,
        check_active: Callable[[], None] = lambda: None,
        subject_context: SubjectContext | None = None,
        host: NativeHostGroup | None = None,
    ) -> SentenceInventory:
        from corpus_structure.core.execution_policy import CharacterizationExecutionPolicy
        from corpus_structure.methods.native_host import NativeHostGroup
        from corpus_structure.settings import NemotronSettings

        check_active()
        source = FrozenNativeSource.acquire(self.prepared, source.value)
        selected = source.value
        blocks, coverage = _blocks(source)
        records, receipts, annotation_columns = [], [], []
        if blocks:
            nlp = pipeline(self.configuration)  # Tokenizer only; learned weights stay in CUDA host.
            selection = nlp.selection()
            if sentence_profile_assets(self.configuration).digest != self.asset_digest:
                raise ValueError("sentence model/assets changed after explicit preparation")
            # An explicitly supplied host belongs to the enclosing execution owner;
            # direct bounded calls acquire and drain their own original host.
            lifetime = (
                nullcontext(host)
                if host is not None
                else NativeHostGroup(CharacterizationExecutionPolicy(), NemotronSettings().endpoint)
            )
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
                        detached, native_availability = _native_records(
                            selected, block, layout, doc
                        )
                        records.extend(detached)
                        annotation_columns.append(native_availability)
        context = dict(
            subject=source_subject(selected["source"]),
            original_source=selected["source"]["document"],
            analyzed_scope=dict(source=selected["source"], selectors=selected["selectors"]),
        )
        packets = []
        for kind, body in records:
            body = {"record_type": kind, **body}
            nominal = "DdoNativeToken" if kind == "token" else "DdoNativeSentence"
            packets.append(
                dict(
                    member_id=body["local_id"],
                    kind_contract=next(
                        identity.key
                        for identity in self.model.identities
                        if identity.owner == self.prepared.index.definitions[nominal].iri
                        and identity.domain == "kind"
                    ),
                    context=context,
                    body=body,
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
            annotation_columns=annotation_columns,
            members=packets,
        )
        value["outcome"] = (
            "complete"
            if all(row["outcome"] in {"complete", "empty"} for row in value["coverage"])
            else "partial"
        )
        check_active()
        return validate_sentence_inventory(
            self.prepared,
            self.model,
            value,
            source,
            receipts=tuple(receipts),
            subject_context=subject_context,
        )


def prepare_sentence_profile(
    prepared: PreparedRelease,
    model: EffectiveDataOperationModel,
    configuration: SentenceConfig | None = None,
) -> PreparedSentenceProfile:
    configuration = configuration or SentenceConfig(exclude=("ner",))
    if (
        not {
            "DdoSelectedNativeSource",
            "DdoNativeToken",
            "DdoNativeSentence",
            "DdoSentenceInventory",
        }
        <= prepared.index.definitions.keys()
    ):
        raise ValueError("sentence preparation requires its acquired nominal source/product model")
    return PreparedSentenceProfile(
        prepared, model, configuration, sentence_profile_assets(configuration).digest
    )


def _semantic_nodes(content: bytes, names: tuple[str, ...]):
    """Normalize the named real semantic definitions, excluding transport siblings."""
    import ast

    module = ast.parse(content)
    result = []
    for name in names:
        matches = [
            node
            for node in module.body
            if (isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name == name)
            or (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == name for target in node.targets
                )
            )
        ]
        if len(matches) != 1:
            raise ValueError("sentence semantic asset has no unique actual definition: " + name)
        result.append((name, ast.dump(matches[0], include_attributes=False)))
    return result


def sentence_execution_custody() -> SourceArtifact:
    """Physical host/transport/adapter code is exact runtime custody."""
    root = Path(__file__).parent
    paths = (
        Path(__file__),
        root.parent / "methods/native_profiles.py",
        root.parent / "ingest/hosted_spacy.py",
    )
    return SourceArtifact(
        "sentences/execution-custody",
        canonical_bytes(
            {
                "version": "spacy-execution-custody-v1",
                "files": [
                    (str(path.relative_to(root.parent)), path.read_bytes().hex()) for path in paths
                ],
            }
        ),
    )


def sentence_profile_assets(configuration: SentenceConfig | None = None) -> SourceArtifact:
    from importlib.metadata import version

    from corpus_structure.methods.native_evidence_layers import SPACY_COLUMNS, SPACY_FAMILIES
    from corpus_structure.methods.native_profiles import spacy_observation_policy, spacy_selection

    configuration = configuration or SentenceConfig(exclude=("ner",))
    selection = spacy_selection(configuration)
    root = Path(__file__).parent
    paths = (
        root / "source_products.py",
        root.parent / "ingest/sentences.py",
        root.parent / "methods/source_preparation.py",
        _MODEL,
        root.parent / "model/semantic/data-operation-source.yaml",
    )
    annotations = root.parent / "ingest/annotations.py"
    return SourceArtifact(
        "sentences/profile-assets",
        canonical_bytes(
            {
                "interpretation": "spacy-native-semantic-assets-ast-v1",
                "native_families": SPACY_FAMILIES,
                "native_family_columns": SPACY_COLUMNS,
                "target": _semantic_nodes(
                    Path(__file__).read_bytes(),
                    (
                        "_id",
                        "validate_sentence_inventory",
                        "_Block",
                        "_blocks",
                        "_native_records",
                        "spacy_family_coverage",
                        "_semantic_nodes",
                        "sentence_profile_assets",
                    ),
                ),
                "native_columns": _semantic_nodes(
                    annotations.read_bytes(),
                    (
                        "_ATTRIBUTES",
                        "AnnotationAvailability",
                        "annotation_availability",
                        "native_token_columns",
                    ),
                ),
                "sources": [
                    (str(path.relative_to(root.parent)), path.read_bytes().hex()) for path in paths
                ],
                "profile": json.loads(
                    selection.native.identity_projections(
                        inference_policy=spacy_observation_policy()
                    ).inference.canonical_input
                ),
                "libraries": {name: version(name) for name in ("spacy", "thinc", "pydantic")},
            }
        ),
    )


def sentence_operation_sources():
    from .python_operation_sources import PythonSource, PythonSourceCollection

    path = Path(__file__).parents[1] / "methods/sentence_evidence.py"
    return PythonSourceCollection(
        (PythonSource("corpus_structure.methods.sentence_evidence", path.read_bytes(), str(path)),),
        boundary_contracts=(sentence_profile_assets(), sentence_execution_custody()),
    )


def execute_sentence_profile(receiver, source: FrozenNativeSource) -> SentenceInventory:
    return receiver.profile.run(source, check_active=receiver.check_active, host=receiver.host)


@dataclass(frozen=True)
class SentenceSourceReadings:
    """Immediate native/construction boundary consumes retained canonical units only."""

    product: SentenceInventory
    source: FrozenNativeSource
    _sentences: tuple[bytes, ...] = field(init=False, repr=False)
    _sentence_by_id: Mapping[str, bytes] = field(init=False, repr=False)
    _token_by_id: Mapping[str, bytes] = field(init=False, repr=False)

    def __post_init__(self):
        validate_sentence_inventory(
            self.product.prepared, self.product.model, json.loads(self.product.content), self.source
        )
        sentences = self.product.inventory("sentence")
        object.__setattr__(self, "_sentences", tuple(canonical_bytes(row) for row in sentences))
        object.__setattr__(
            self,
            "_sentence_by_id",
            MappingProxyType({row["local_id"]: canonical_bytes(row) for row in sentences}),
        )
        object.__setattr__(
            self,
            "_token_by_id",
            MappingProxyType(
                {row["local_id"]: canonical_bytes(row) for row in self.product.inventory("token")}
            ),
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
        return tuple(json.loads(self.product.content)["annotation_columns"])


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
            return_annotation=SentenceInventory,
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
        required_sources = sentence_operation_sources()
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
        retained = {artifact.name: artifact for artifact in self.custody}
        if len(retained) != len(self.custody) or any(
            retained.get(actual.name) != actual
            for actual in (sentence_profile_assets(), sentence_execution_custody())
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

        for function in (_blocks, _native_records, validate_sentence_inventory):
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
        from .data_operation_identity import decode_semantic_value
        from .data_operation_ports import PortRefusal, PythonRoleValue

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

    def _completion(self, product, binding=None):
        if binding is not None:
            product = replace(product, subject_context=binding.subject_context)
        from .data_operation_identity import semantic_value
        from .data_operation_ports import PortCompletion, RoleValue

        # Product meaning uses the exact typed record's fields; display JSON and native
        # member packets are deliberate projections of that same validated product.
        model_value = product.value.model_dump(mode="python", exclude_unset=True)
        packets = json.loads(product.content)["members"]
        native_members = tuple(
            canonical_bytes(
                {
                    "member_id": packet["member_id"],
                    "kind_contract": packet["kind_contract"],
                    "context": packet["context"],
                    "body": semantic_value(packet["body"]),
                }
            )
            for packet in packets
        )
        output = next(role for role in self.operation.roles if role.direction == "output")
        contracts = {(item.owner, item.domain): item.key for item in self.profile.model.identities}
        return PortCompletion(
            self.operation.semantic_id,
            (
                RoleValue(
                    output.name,
                    contracts[output.kind, "kind"],
                    product.content,
                    canonical_bytes(semantic_value(model_value)),
                    native_members,
                ),
            ),
            execution_evidence=canonical_bytes(
                [json.loads(receipt) for receipt in product.execution_receipts]
            ),
        )

    @property
    def native_selections(self):
        from corpus_structure.methods.native_profiles import spacy_selection

        return (spacy_selection(self.profile.configuration),)

    def plan_python(self, values, *, binding=None, check_active=lambda: None, execution_owner):
        """Submit through the invocation's one shared host and work-handle owner."""
        from corpus_structure.core.method import PreparedWork
        from corpus_structure.methods.sentence_evidence import SentenceEvidenceOperation

        self._verify()
        source = self._source(values, binding)
        check_active()

        def compute():
            self._verify()
            product = SentenceEvidenceOperation(
                self.profile, check_active, execution_owner.native_hosts
            ).run(source)
            self._verify()
            return self._completion(product, binding)

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
        product = SentenceEvidenceOperation(self.profile, check_active, self.host).run(source)
        self._verify()
        return self._completion(product, binding)


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
        or outputs[0].kind != expected["DdoSentenceInventory"].iri
        or inputs[0].parameter != "source"
    ):
        raise PortRefusal("operation does not establish the prepared sentence profile")
    port = PreparedSentencePort(
        identity,
        selected,
        prepare_sentence_profile(prepared, model),
        authorize,
        host,
        custody,
        sources,
    )
    port._verify()
    return port
