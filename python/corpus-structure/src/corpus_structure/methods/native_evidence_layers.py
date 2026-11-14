"""Detach complete native linguistic evidence into the shared characterization model.

No domain-role normalization, phrase whitelist or winning-provider selection belongs here.
Source members use exact ordered token occurrences; structural groups never invent a quote
covering intervening source. Native processing and publication are separate responsibilities.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from hashlib import sha256
from typing import Any

from corpus_structure.ingest.annotations import AnnotationProduct
from corpus_structure.semantic.characterization import occurrence_id, validate_layer
from corpus_structure.semantic.identity import canonical_bytes

from .pm2_hanlp_products import _dependency_graph

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


class NativeEvidenceBuilder:
    """One private, detached layer assembled under authoritative operation identity."""

    def __init__(
        self,
        base: Mapping[str, Any],
        scope: Mapping[str, Any],
        operation: Mapping[str, Any],
        *,
        profile: str,
        families: Sequence[str],
    ):
        self.base, self.scope = dict(base), dict(scope)
        self.profile, self.families = profile, tuple(families)
        self.operation = {
            **operation,
            "produced_families": list(self.families),
            "preconditions": ["exact-source-projection", "protected-atom-layout"],
            "effects": ["retain-native-linguistic-evidence"],
            "result_determinants": ["runtime", "model", "configuration", "input", "context"],
            "outcomes": ["complete", "partial", "failed"],
        }
        self.occurrences: dict[str, dict[str, Any]] = {}
        self.annotations: list[dict[str, Any]] = []
        self.memberships: list[dict[str, Any]] = []
        self.roles: list[dict[str, Any]] = []
        self.native_runs: list[dict[str, Any]] = []
        self.covered: dict[str, list[tuple[dict[str, Any], str, str | None]]] = {
            f: [] for f in families
        }
        self._source_maps: dict[int, Any] = {}

    def record(
        self,
        family: str,
        selectors: Sequence[Mapping[str, Any]],
        status: str = "complete",
        reason: str | None = None,
    ) -> None:
        if family in self.covered:
            self.covered[family].extend((dict(selector), status, reason) for selector in selectors)

    def occurrence(self, view: Any, start: int, end: int) -> str:
        if not 0 <= start < end <= len(view.text):
            raise ValueError("native extent is outside its source projection")
        extents = []
        position = start
        if source_identity(view) not in self._source_maps:
            real = [p for p in view.pieces if p["kind"] == "native_text"]
            items = {node["self_ref"]: node for node in getattr(view, "items", ())}
            self._source_maps[source_identity(view)] = (
                [p["end"] for p in view.pieces],
                real,
                [p["end"] for p in real],
                items,
            )
        piece_ends, real, real_ends, items = self._source_maps[source_identity(view)]
        first = bisect_right(piece_ends, start)
        for piece in view.pieces[first:]:
            if piece["start"] >= end:
                break
            a, b = max(start, piece["start"]), min(end, piece["end"])
            if a >= b:
                continue
            if a != position:
                raise ValueError("native extent crosses an unmapped source gap")
            synthetic = piece["kind"] != "native_text"
            # A separator has no native character authority. Its contextual pointer is
            # a real adjacent source item and synthetic remains explicit throughout.
            nearest = bisect_left(real_ends, a)
            pointer = piece.get("item_ref") or (
                real[nearest]["item_ref"] if nearest < len(real) else None
            )
            if pointer is None:
                raise ValueError("synthetic token has no source context")
            extent = dict(
                projection=source_projection(view),
                native_pointer=pointer,
                start=a,
                end=b,
                text=view.text[a:b],
                synthetic=synthetic,
            )
            from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource

            if not isinstance(view, DeclaredNativeFrameSource):
                extent["source_view_id"] = view.ref.id
            if not synthetic:
                node = items.get(pointer, {})
                pages = {
                    prov["page_no"]
                    for prov in node.get("prov", ())
                    if type(prov.get("page_no")) is int and prov["page_no"] > 0
                }
                # A multi-page native item needs finer original correspondence;
                # retaining unknown is preferable to assigning all text one page.
                if len(pages) == 1:
                    extent["page"] = next(iter(pages))
            extents.append(extent)
            position = b
        if position != end:
            raise ValueError("native extent is not covered by retained source pieces")
        identity = occurrence_id(self.base, extents)
        self.occurrences.setdefault(identity, dict(local_id=identity, extents=extents))
        return identity

    def annotation(
        self,
        key: str,
        kind: str,
        family: str,
        occurrences: Sequence[str],
        scheme: str,
        label: str,
        **values: Any,
    ) -> str:
        members = list(dict.fromkeys(occurrences))
        if not members:
            raise ValueError("native annotation requires exact source members")
        self.annotations.append(
            dict(
                local_id=key,
                kind=kind,
                family=family,
                vocabulary=scheme,
                native_scheme=scheme,
                native_label=label,
                status="native_evidence",
                occurrences=members,
                **values,
            )
        )
        return key

    def membership(
        self,
        group: str,
        member: str,
        role: str,
        order: int,
        family: str,
        occurrences: Sequence[str],
        *,
        structural: bool = True,
    ) -> None:
        row = dict(
            group=group,
            member=member,
            role=role,
            order=order,
            family=family,
            occurrences=list(dict.fromkeys(occurrences)),
            scope=group,
            structural=structural,
        )
        self.memberships.append(dict(local_id="membership:" + digest(row), **row))

    def role(
        self,
        owner: str,
        member: str,
        label: str,
        scheme: str,
        family: str,
        occurrences: Sequence[str],
    ) -> None:
        row = dict(
            owner=owner,
            member=member,
            role=label,
            scheme=scheme,
            family=family,
            occurrences=list(dict.fromkeys(occurrences)),
            basis=dict(
                kind="native_prediction",
                status="recorded",
                native_scheme=scheme,
                native_label=label,
            ),
        )
        self.roles.append(dict(local_id="role:" + digest(row), **row))

    def spacy(
        self, view: Any, product: AnnotationProduct, native_run: str
    ) -> tuple[str, list[dict[str, Any]]]:
        """Retain all columns, whitespace tokens, atom roles and whole-block heads."""
        prefix = f"spacy/{view.ref.id}/{product.block_id}"
        block = prefix + "/block"
        block_occurrence = self.occurrence(view, product.block_start, product.block_end)
        self.annotation(
            block,
            "native.block",
            "spacy.tokens",
            [block_occurrence],
            "spacy-source-layout-1",
            product.kind,
        )
        sentence_ids = []
        for index, sentence in enumerate(product.sentences):
            key = prefix + f"/sentence/{index}"
            self.annotation(
                key,
                "native.sentence",
                "spacy.sentences",
                [self.occurrence(view, sentence.start, sentence.end)],
                "spacy-sentence-boundary-1",
                "sentence",
            )
            sentence_ids.append(key)
        tokens: list[dict[str, Any]] = []
        availability = {c.attribute: c.status for c in product.availability}
        for index, token in enumerate(product.tokens):
            key = prefix + f"/token/{index}"
            occurrence = self.occurrence(view, token.start, token.end)
            text = view.text[token.start : token.end]
            native: dict[str, Any] = dict(
                index=index,
                container=block,
                native_run=native_run,
                text=text,
                space=token.space,
                whitespace=" " if token.space else "",
                source_role=token.role,
            )
            if token.sentence is not None:
                native["sentence"] = sentence_ids[token.sentence]
            for attribute, column, value in (
                ("LEMMA", "lemma", token.lemma),
                ("POS", "pos", token.pos),
                ("TAG", "tag", token.tag),
                ("MORPH", "morphology", list(token.morphology)),
                ("DEP", "dependency", token.dependency),
            ):
                if SPACY_COLUMNS[attribute] in self.covered and availability.get(attribute) in {
                    "complete",
                    "partial",
                }:
                    native[column] = value
            if "spacy.dependency" in self.covered and availability.get("DEP") in {
                "complete",
                "partial",
            }:
                native.update(native_head=token.head, head_index_base=0)
            self.annotation(
                key,
                "native.token",
                "spacy.tokens",
                [occurrence],
                "spacy-token-columns-1",
                text,
                native_token=native,
            )
            self.membership(block, key, "token", index, "spacy.tokens", [occurrence])
            if "sentence" in native:
                self.membership(
                    native["sentence"], key, "token", index, "spacy.sentences", [occurrence]
                )
            tokens.append(dict(key=key, occurrence=occurrence, source=token, text=text))
        if availability.get("DEP") in {"complete", "partial"}:
            for token in tokens:
                row = token["source"]
                if row.dependency:
                    if not 0 <= row.head < len(tokens):
                        raise ValueError("spaCy native head is outside its block")
                    self.role(
                        tokens[row.head]["key"],
                        token["key"],
                        row.dependency,
                        "spacy-english-dependency-1",
                        "spacy.dependency",
                        [token["occurrence"]],
                    )
        selectors = [source_selector(view, product.block_start, product.block_end)]
        self.record("spacy.tokens", selectors)
        for column in product.availability:
            self.record(
                SPACY_COLUMNS[column.attribute],
                selectors,
                "complete"
                if column.status in {"complete", "not_applicable"}
                else "partial"
                if column.status == "partial"
                else "failed",
                None
                if column.status in {"complete", "not_applicable"}
                else f"native {column.attribute} column is {column.status}",
            )
        return block, tokens

    def hanlp_sentence(
        self,
        view: Any,
        product: AnnotationProduct,
        words: Sequence[dict[str, Any]],
        number: int,
        native: Mapping[str, Any],
        preparation: Mapping[str, Any],
        native_run: str,
    ) -> None:
        """Validate heads independently; one malformed head cannot erase valid siblings."""
        from corpus_structure.semantic.observations import source_value

        prefix = f"hanlp/{view.ref.id}/{product.block_id}/sentence/{number}"
        occurrences = [t["occurrence"] for t in words]
        selector = source_selector(view, words[0]["source"].start, words[-1]["source"].end)
        self.annotation(
            prefix,
            "native.sentence",
            "hanlp.tokens",
            occurrences,
            "hanlp-canonical-sentence-1",
            "sentence",
            **(
                {"native_batch": source_value(preparation["batch_receipt"])}
                if "batch_receipt" in preparation
                else {}
            ),
        )
        prepared_words = preparation.get("prepared_words")
        if (
            not isinstance(prepared_words, list)
            or len(prepared_words) != len(words)
            or any(not isinstance(x, str) for x in prepared_words)
        ):
            raise ValueError("HanLP prepared word population differs from canonical tokens")
        spans = preparation.get("word_subwords")
        if spans is not None and (not isinstance(spans, list) or len(spans) != len(words)):
            raise ValueError("HanLP subword correspondence differs from canonical tokens")
        token_ids = []
        native_rows = []
        for index, token in enumerate(words):
            key = prefix + f"/token/{index}"
            row = dict(
                index=index,
                container=prefix,
                sentence=prefix,
                native_run=native_run,
                text=token["text"],
                space=token["source"].space,
                whitespace=" " if token["source"].space else "",
                source_role=token["source"].role,
                prepared_text=prepared_words[index],
            )
            if spans is not None:
                if any(type(p) is not int or p < 0 for p in spans[index]):
                    raise ValueError("HanLP subword position is not a native nonnegative index")
                row["subword_positions"] = list(spans[index])
            self.annotation(
                key,
                "native.token",
                "hanlp.tokens",
                [token["occurrence"]],
                "hanlp-canonical-token-1",
                token["text"],
                native_token=row,
            )
            self.membership(prefix, key, "token", index, "hanlp.tokens", [token["occurrence"]])
            # Explicit native-to-common correspondence; no text search or relabelling.
            self.membership(
                key,
                token["key"],
                "canonical_token",
                0,
                "hanlp.tokens",
                [token["occurrence"]],
                structural=False,
            )
            token_ids.append(key)
            native_rows.append(row)
        self.record("hanlp.tokens", [selector])
        for name in ("lemma", "pos", "dependency", "constituency", "srl"):
            family = "hanlp." + name
            checkpoint = (len(self.annotations), len(self.memberships), len(self.roles))
            try:
                value = native[name]
                if name in {"lemma", "pos"}:
                    if (
                        not isinstance(value, list)
                        or len(value) != len(words)
                        or any(not isinstance(x, str) or not x for x in value)
                    ):
                        raise ValueError(
                            f"HanLP {name} head does not cover its canonical token population"
                        )
                    for row, label in zip(native_rows, value, strict=True):
                        row["lemma" if name == "lemma" else "tag"] = label
                elif name == "dependency":
                    _dependency_graph(value, len(words))
                    for index, (head, label) in enumerate(value):
                        native_rows[index].update(
                            native_head=head, head_index_base=1, dependency=label
                        )
                        self.role(
                            prefix if head == 0 else token_ids[head - 1],
                            token_ids[index],
                            label,
                            HANLP_SCHEMES[name],
                            family,
                            [occurrences[index]],
                        )
                elif name == "constituency":
                    self._constituency(prefix, value, prepared_words, token_ids, occurrences)
                else:
                    missing = self._srl(prefix, value, prepared_words, token_ids, occurrences)
                    if missing:
                        self.record(
                            family,
                            [selector],
                            "partial",
                            "native SRL group lacks a unique PRED marker; "
                            "every supplied role is retained",
                        )
                        continue
            except (KeyError, ValueError, TypeError) as error:
                del self.annotations[checkpoint[0] :]
                del self.memberships[checkpoint[1] :]
                del self.roles[checkpoint[2] :]
                self.record(family, [selector], "failed", str(error))
            else:
                self.record(family, [selector], "complete")

    def _constituency(
        self, prefix: str, tree: Any, prepared: list[str], tokens: list[str], occurrences: list[str]
    ) -> None:
        family, scheme = "hanlp.constituency", HANLP_SCHEMES["constituency"]
        leaves: list[str] = []
        serial = 0

        def visit(node: Any, depth: int) -> tuple[str, list[str]]:
            nonlocal serial
            if depth > 2 * len(tokens) + 2:
                raise ValueError("HanLP constituency depth exceeds native sentence bound")
            if isinstance(node, str):
                index = len(leaves)
                if index >= len(tokens):
                    raise ValueError("HanLP constituency yield exceeds canonical population")
                leaves.append(node)
                return tokens[index], [occurrences[index]]
            if (
                not isinstance(node, (tuple, list))
                or len(node) != 2
                or not isinstance(node[0], str)
                or not node[0]
                or not isinstance(node[1], (tuple, list))
                or not node[1]
            ):
                raise ValueError("HanLP returned malformed constituency node")
            key = prefix + f"/constituent/{serial}"
            serial += 1
            children = [visit(child, depth + 1) for child in node[1]]
            members = [o for _, os in children for o in os]
            self.annotation(key, "native.constituent", family, members, scheme, node[0])
            for order, (child, os) in enumerate(children):
                self.membership(key, child, "child", order, family, os)
            return key, members

        root, members = visit(tree, 0)
        if leaves != prepared:
            raise ValueError("HanLP constituency yield differs from prepared canonical tokens")
        self.membership(prefix, root, "constituency_root", 0, family, members)

    def _srl(
        self,
        prefix: str,
        frames: Any,
        prepared: list[str],
        tokens: list[str],
        occurrences: list[str],
    ) -> bool:
        family, scheme = "hanlp.srl", HANLP_SCHEMES["srl"]
        if not isinstance(frames, list):
            raise ValueError("HanLP SRL head must contain ordered native role groups")
        missing_predicate = False
        for index, frame in enumerate(frames):
            if not isinstance(frame, list) or not frame:
                raise ValueError("HanLP SRL returned an empty or malformed role group")
            members = []
            parsed = []
            for role in frame:
                if not isinstance(role, (list, tuple)) or len(role) != 4:
                    raise ValueError("HanLP SRL returned malformed role")
                text, label, start, end = role
                if (
                    not isinstance(text, str)
                    or not isinstance(label, str)
                    or not label
                    or type(start) is not int
                    or type(end) is not int
                    or not 0 <= start < end <= len(tokens)
                ):
                    raise ValueError("HanLP SRL role lies outside native sentence")
                if " ".join(prepared[start:end]) != text:
                    raise ValueError("HanLP SRL rendering differs from prepared canonical words")
                parsed.append((text, label, start, end))
                members.extend(occurrences[start:end])
            frame_id = prefix + f"/srl/{index}"
            self.annotation(
                frame_id, "native.srl_group", family, members, scheme, "native-role-group"
            )
            missing_predicate |= sum(label == "PRED" for _, label, _, _ in parsed) != 1
            for order, (_text, label, start, end) in enumerate(parsed):
                role_id = frame_id + f"/member/{order}"
                self.annotation(
                    role_id, "native.srl_role", family, occurrences[start:end], scheme, label
                )
                self.membership(frame_id, role_id, label, order, family, occurrences[start:end])
                self.role(frame_id, role_id, label, scheme, family, occurrences[start:end])
                for token_index in range(start, end):
                    self.membership(
                        role_id,
                        tokens[token_index],
                        "token",
                        token_index - start,
                        family,
                        [occurrences[token_index]],
                    )
        return missing_predicate

    def coverage_values(self):
        coverage = []
        for family in self.families:
            rows = self.covered[family]
            if not rows:
                rows = [
                    (dict(s), "failed", "producer did not examine requested source scope")
                    for s in self.scope["selectors"]
                ]
            # Eligible/examined source denotes the actual admitted source units; a gap
            # is recorded explicitly by the producer rather than hidden by item count.
            eligible = list({canonical_bytes(s): s for s, _, _ in rows}.values())
            examined = list(
                {
                    canonical_bytes(s): s
                    for s, status, _ in rows
                    if status in {"complete", "empty", "partial"}
                }.values()
            )
            unexamined = list(
                {
                    canonical_bytes(s): s
                    for s, status, _ in rows
                    if status not in {"complete", "empty", "partial"}
                }.values()
            )
            complete = all(status in {"complete", "empty"} for _, status, _ in rows)
            reasons = list(dict.fromkeys(reason for _, _, reason in rows if reason))
            statuses = {status for _, status, _ in rows}
            outcome = (
                "empty"
                if statuses == {"empty"}
                else "complete"
                if complete
                else "partial"
                if examined
                else "unsupported"
                if statuses == {"unsupported"}
                else "failed"
            )
            row = dict(
                family=family,
                operation=self.operation["key"],
                eligible=eligible,
                examined=eligible if complete else examined,
                unexamined=unexamined,
                availability="available"
                if complete or examined
                else "unsupported"
                if outcome == "unsupported"
                else "unavailable",
                outcome=outcome,
                profile=self.profile,
            )
            if not complete:
                row["reason"] = "; ".join(reasons) or "native family is incomplete"
            coverage.append(row)
        return coverage

    def payload(
        self, release_id: str, *, dependencies: Sequence[Mapping[str, Any]] = ()
    ) -> dict[str, Any]:
        coverage = self.coverage_values()
        return dict(
            format="characterization-layer-v1",
            base_document=self.base,
            release_id=release_id,
            operation=self.operation,
            source_scope=self.scope,
            outcome="complete"
            if all(c["outcome"] in {"complete", "empty"} for c in coverage)
            else "partial",
            occurrences=list(self.occurrences.values()),
            annotations=self.annotations,
            memberships=self.memberships,
            roles=self.roles,
            terms=[],
            choices=[],
            dependencies=list(dependencies),
            coverage=coverage,
            native_runs=self.native_runs,
        )

    def finish(
        self,
        prepared: Any,
        *,
        dependencies: Mapping[Any, Any] | None = None,
        releases: Mapping[str, Any] | None = None,
    ):
        pins = [] if dependencies is None else [pin.values() for pin in dependencies]
        return validate_layer(
            prepared,
            self.payload(prepared.release_id, dependencies=pins),
            dependencies=dependencies,
            releases=releases,
        )


def retained_spacy_docs(
    layer: Any,
    source_views: Mapping[int, Any],
    vocab: Any,
    *,
    required: Sequence[str] = ("lemma", "pos", "tag", "morphology", "dependency"),
) -> dict[str, Any]:
    """Build consumer-local whole-block Docs from an ordinary retained layer read.

    This route performs no tokenizer/model inference and never slices with Span.as_doc.
    The caller selects the exact layer and source closure through TC-02 before calling.
    """
    from spacy.tokens import Doc

    body = layer.payload
    occurrences = {o["local_id"]: o for o in body["occurrences"]}
    annotations = {a["local_id"]: a for a in body["annotations"]}
    rows: dict[str, list[dict[str, Any]]] = {}
    for item in annotations.values():
        token = item.get("native_token")
        if token is not None and token["native_run"] == "spacy":
            rows.setdefault(token["container"], []).append(item)
    docs = {}
    for container, tokens in rows.items():
        tokens.sort(key=lambda a: a["native_token"]["index"])
        native = [a["native_token"] for a in tokens]
        if [t["index"] for t in native] != list(range(len(native))):
            raise ValueError("retained spaCy token indices are not the whole original block")
        if any(field not in token for token in native for field in required):
            raise ValueError("retained spaCy block lacks required native columns")
        block = annotations[container]
        extents = [e for oid in block["occurrences"] for e in occurrences[oid]["extents"]]
        view_ids = {e["source_view_id"] for e in extents}
        if len(view_ids) != 1:
            raise ValueError("spaCy native block spans different projections")
        view = source_views[next(iter(view_ids))]
        base = body["base_document"]
        if view.ref.native_product.values() != base:
            raise ValueError("retained spaCy view differs from exact base document")
        start, end = extents[0]["start"], extents[-1]["end"]
        for extent in extents:
            if (
                extent["projection"] != view.ref.projection_digest
                or extent["text"] != view.text[extent["start"] : extent["end"]]
            ):
                raise ValueError("retained spaCy source extent differs from selected projection")
        complete_dependency = all(t.get("dependency") for t in native)
        doc = Doc(
            vocab,
            words=[t["text"] for t in native],
            spaces=[t["space"] for t in native],
            lemmas=[t.get("lemma", "") for t in native],
            pos=[t.get("pos", "") for t in native],
            tags=[t.get("tag", "") for t in native],
            morphs=["|".join(t.get("morphology", ())) for t in native],
            heads=[t["native_head"] for t in native] if complete_dependency else None,
            deps=[t["dependency"] for t in native] if complete_dependency else None,
            sent_starts=None
            if complete_dependency
            else [
                i == 0 or t.get("sentence") != native[i - 1].get("sentence")
                for i, t in enumerate(native)
            ],
        )
        if doc.text != view.text[start:end]:
            raise ValueError("retained spaCy whole-block text/whitespace differs")
        for actual, item in zip(doc, tokens, strict=True):
            expected = item["native_token"]
            extents = [e for oid in item["occurrences"] for e in occurrences[oid]["extents"]]
            if (
                actual.idx + start != extents[0]["start"]
                or actual.idx + start + len(actual.text) != extents[-1]["end"]
                or actual.whitespace_ != expected["whitespace"]
            ):
                raise ValueError("retained spaCy token/source correspondence differs")
            if complete_dependency and (
                actual.head.i != expected["native_head"] or actual.dep_ != expected["dependency"]
            ):
                raise ValueError("retained spaCy dependency columns differ")
            if (
                actual.lemma_ != expected.get("lemma", "")
                or actual.pos_ != expected.get("pos", "")
                or actual.tag_ != expected.get("tag", "")
            ):
                raise ValueError("retained spaCy lexical columns differ")
        from corpus_structure.ingest.sentences import Block, boundaries

        actual_sentences = [
            (start + a, start + b) for a, b in boundaries(Block(doc.text, (), (), ()), doc)
        ]
        sentence_ids = list(dict.fromkeys(t["sentence"] for t in native if "sentence" in t))
        expected_sentences = []
        for sentence_id in sentence_ids:
            members = [
                e
                for oid in annotations[sentence_id]["occurrences"]
                for e in occurrences[oid]["extents"]
            ]
            expected_sentences.append((members[0]["start"], members[-1]["end"]))
        if actual_sentences != expected_sentences:
            raise ValueError("restored spaCy sentences differ from retained ownership")
        docs[container] = doc
    return docs


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
