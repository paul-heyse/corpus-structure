"""Located native context and source-level hypotheses, separate from evaluation.

Native clusters and RST labels remain attributed evidence. Hypotheses name actual
symbolic sites and external choices; this module never evaluates inherited environments,
settles scientific identity or creates a Cartesian product of analytical alternatives.
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from corpus_structure.methods.native_evidence_layers import (
    digest,
    source_identity,
    source_projection,
    source_selector,
)
from corpus_structure.methods.pm2_dipo_products import _pair, _tree_children, _validate_boundaries
from corpus_structure.semantic.characterization import occurrence_id
from corpus_structure.semantic.data_product_reference import (
    DataProductMemberReference,
    DataProductReference,
    member_reference,
    read_member_reference,
)
from corpus_structure.semantic.declared_record_sources import DeclaredNativeFrameSource
from corpus_structure.semantic.identity import canonical_bytes

CONTEXT_FAMILIES = (
    "context.structure",
    "context.reference",
    "context.host",
    "context.binding",
    "context.inheritance",
    "context.attribution",
    "maverick.mentions",
    "maverick.clusters",
    "dipo.edus",
    "dipo.rst",
)
REVISION = "contextual-source-hypotheses-1"


@dataclass(frozen=True)
class ContextPart:
    view: DeclaredNativeFrameSource
    start: int
    end: int

    def selector(self):
        return source_selector(self.view, self.start, self.end)


@dataclass(frozen=True)
class ContextInput:
    """An ordered exact provider layout; synthetic joins have no literal authority."""

    parts: tuple[ContextPart, ...]
    focal: tuple[dict[str, Any], ...]
    text: str
    segments: tuple[tuple[int, int, ContextPart], ...]
    gaps: tuple[dict[str, Any], ...]

    @classmethod
    def build(cls, parts: Sequence[ContextPart], focal: Sequence[Mapping[str, Any]]):
        if not parts:
            raise ValueError("context requires a nonempty exact source population")
        chunks, segments, gaps = [], [], []
        position = 0
        for index, part in enumerate(parts):
            if not 0 <= part.start < part.end <= len(part.view.text):
                raise ValueError("context source part lies outside its projection")
            if index:
                previous = parts[index - 1]
                contiguous = (
                    source_identity(previous.view) == source_identity(part.view)
                    and previous.end == part.start
                )
                if not contiguous:
                    chunks.append("\n")
                    position += 1
                    gaps.append(
                        dict(
                            left_selector=previous.selector(),
                            right_selector=part.selector(),
                            reason="synthetic selection join; original crossing unexamined",
                        )
                    )
            text = part.view.text[part.start : part.end]
            chunks.append(text)
            segments.append((position, position + len(text), part))
            position += len(text)
        examined = [p.selector() for p in parts]
        for selector in focal:
            if not any(
                selector["projection"] == s["projection"]
                and s["start"] <= selector.get("start", s["start"])
                and selector.get("end", s["end"]) <= s["end"]
                for s in examined
            ):
                raise ValueError("focal output scope is outside examined context")
        return cls(
            tuple(parts),
            tuple(dict(s) for s in focal),
            "".join(chunks),
            tuple(segments),
            tuple(gaps),
        )

    def declaration(self):
        return dict(
            focal=list(self.focal),
            examined=[p.selector() for p in self.parts],
            gaps=list(self.gaps),
        )

    def occurrences(self, builder, start: int, end: int):
        if not 0 <= start < end <= len(self.text):
            raise ValueError("provider character extent lies outside examined context")
        result, consumed = [], 0
        for a, b, part in self.segments:
            left, right = max(a, start), min(b, end)
            if left < right:
                result.append(
                    builder.occurrence(part.view, part.start + left - a, part.start + right - a)
                )
                consumed += right - left
        if not result:
            raise ValueError("provider extent contains no literal source member")
        # The omitted characters can only be the explicitly constructed synthetic joins.
        joined = sum(
            max(0, min(end, self.segments[i][0]) - max(start, self.segments[i - 1][1]))
            for i in range(1, len(self.segments))
        )
        if consumed + joined != end - start:
            raise ValueError("provider extent crosses an unmapped context gap")
        return result


class ContextualLayer:
    def __init__(self, base, scope, operation, context: ContextInput):
        self.base, self.scope, self.operation = dict(base), dict(scope), dict(operation)
        self.profile, self.families = REVISION, CONTEXT_FAMILIES
        self.occurrences: dict[str, dict[str, Any]] = {}
        self.annotations: list[dict[str, Any]] = []
        self.memberships: list[dict[str, Any]] = []
        self.roles: list[dict[str, Any]] = []
        self.covered: dict[str, list[tuple[dict[str, Any], str, str | None]]] = {
            family: [] for family in self.families
        }
        self.context = context
        self.terms: list[dict[str, Any]] = []
        self.choices: list[dict[str, Any]] = []
        self.support = list(
            dict.fromkeys(
                self.occurrence(part.view, part.start, part.end) for part in context.parts
            )
        )
        self.scope_id = "context-scope:" + digest(context.declaration())
        self.annotation(
            self.scope_id,
            "context.examined_scope",
            "context.structure",
            self.support,
            "exact-source-context-1",
            "examined",
            context=context.declaration(),
        )
        self._proxies: dict[tuple[DataProductReference, str], str] = {}
        self._dependencies: dict[DataProductReference, Any] = {}
        self._semantic_dependencies: dict[DataProductReference, Any] = {}
        self._choice_groups: dict[tuple[DataProductReference, str], tuple[str, str]] = {}
        self._native_clusters: list[tuple[str, list[str]]] = []
        self._mention_metadata: dict[str, dict[str, Any]] = {}
        self._rst_hosts: list[tuple[list[str], list[str], str]] = []
        self._quotes: list[tuple[str, int, int, str]] = []

    def node(
        self,
        key,
        kind,
        family,
        occurrences,
        label,
        *,
        scheme=REVISION,
        status="private_proposal",
        **values,
    ):
        self.annotation(key, kind, family, occurrences or self.support, scheme, label, **values)
        self.annotations[-1]["status"] = status
        return key

    def inventory(self):
        """Return the exact members consumed by current nominal product assembly."""
        return {
            "occurrences": list(self.occurrences.values()),
            "annotations": self.annotations,
            "memberships": self.memberships,
            "roles": self.roles,
            "terms": self.terms,
            "choices": self.choices,
        }

    def record(
        self,
        family: str,
        selectors: Sequence[Mapping[str, Any]],
        status: str = "complete",
        reason: str | None = None,
    ) -> None:
        if family in self.covered:
            self.covered[family].extend((dict(selector), status, reason) for selector in selectors)

    def occurrence(self, view: DeclaredNativeFrameSource, start: int, end: int) -> str:
        if not 0 <= start < end <= len(view.text):
            raise ValueError("native extent is outside its source projection")
        extents = []
        position = start
        native = view.view
        real, real_ends, items = native.native_pieces, native.native_ends, native.items_by_ref
        piece_ends = native.ends
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

    def depend(
        self,
        layers: Mapping[DataProductReference, Any],
        *,
        semantic_pins=None,
    ):
        self._dependencies = {pin: report for pin, report in layers.items()}
        self._semantic_dependencies = {
            pin: self._dependencies[pin]
            for pin in (self._dependencies if semantic_pins is None else semantic_pins)
        }
        for pin, report in layers.items():
            if not isinstance(pin, DataProductReference):
                raise ValueError("context dependency requires a current semantic product reference")
            actual_base = report.payload["source"]
            if actual_base != self.base:
                raise ValueError("context dependency belongs to another source document")
            for member_id, (group, _member) in report.choice_members.items():
                self._choice_groups[pin, member_id] = (group["local_id"], group["compatibility"])

    def proxy(self, pin: DataProductReference, local_id: str, *, family: str) -> str:
        identity = (pin, local_id)
        if identity in self._proxies:
            return self._proxies[identity]
        report = self._dependencies.get(pin)
        if report is None:
            raise ValueError("context endpoint requires its exact retained dependency")
        body = report.payload
        source = report.members.get(local_id)
        if source is None or source["record_type"] not in {"annotation", "term"}:
            raise ValueError("context endpoint is outside its admitted graph member population")
        external = member_reference(pin, local_id).values()
        occurrences = {o["local_id"]: o for o in body["occurrences"]}
        selected = []
        for oid in source.get("occurrences", ()):
            occurrence = occurrences[oid]
            # A source-local endpoint must belong to this operation's examined source.
            if not all(
                any(
                    e["projection"] == source_projection(part.view)
                    and part.start
                    <= e.get("start", part.start)
                    <= e.get("end", part.end)
                    <= part.end
                    for part in self.context.parts
                )
                for e in occurrence["extents"]
            ):
                raise ValueError("context endpoint lies outside actual examined source")
            self.occurrences.setdefault(oid, occurrence)
            selected.append(oid)
        key = "context-proxy:" + digest(external)
        self.node(
            key,
            "context.symbolic_site"
            if "kind" in source
            and source["kind"]
            in {
                "binder",
                "participant",
                "operator",
                "predicate",
                "attribution",
                "clause_relation",
                "unknown",
            }
            else "context.evidence_site",
            family,
            selected,
            source.get("value", source.get("native_label", source["kind"])),
            external_premises=[external],
            context=self.context.declaration(),
            status="native_evidence"
            if family in {"maverick.mentions", "maverick.clusters", "dipo.edus", "dipo.rst"}
            else "private_proposal",
        )
        self._proxies[identity] = key
        return key

    def required_choices(
        self, pin: DataProductReference, node: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        return [
            member_reference(pin, choice).values() for choice in node.get("required_choices", ())
        ] + list(node.get("required_external_choices", ()))

    def propose(
        self,
        owner: str,
        member: str,
        role: str,
        family: str,
        *,
        premises: Sequence[str] = (),
        external=(),
        choices=(),
        support=None,
    ):
        nodes = {a["local_id"]: a for a in self.annotations}
        if owner not in nodes or member not in nodes:
            raise ValueError("context hypothesis has an unknown endpoint")
        seen = {}
        for choice in choices:
            reference = read_member_reference(choice)
            if not isinstance(reference, DataProductMemberReference):
                raise ValueError("context hypothesis requires a current semantic member reference")
            pin, local_id = reference.product, reference.member_id
            selected = self._choice_groups.get((pin, local_id))
            if selected is None:
                raise ValueError("context hypothesis requires an unknown analytical choice")
            group, compatibility = selected
            if compatibility in {"exclusive", "unknown"}:
                previous = seen.setdefault((pin, group), local_id)
                if previous != local_id:
                    raise ValueError("context hypothesis combines incompatible analytical choices")
        occurrences = list(
            dict.fromkeys(
                support
                if support is not None
                else [*nodes[owner]["occurrences"], *nodes[member]["occurrences"]]
            )
        )
        active_quotes = sorted(self.quotation_state(nodes[owner]["occurrences"]))
        premises = list(dict.fromkeys([*premises, *active_quotes]))
        basis = dict(
            kind="contextual_proposal",
            status="private_proposal",
            rule_id=REVISION,
            premises=list(premises),
            external_premises=list(external),
        )
        hypothesis = "context-hypothesis:" + digest(
            [owner, member, role, list(premises), list(external), list(choices)]
        )
        kinds = {
            "context.reference": "contextual.referent_hypothesis",
            "context.host": "contextual.host_hypothesis",
            "context.binding": "contextual.binding_hypothesis",
            "context.inheritance": "contextual.inheritance_hypothesis",
            "context.attribution": "contextual.attribution_hypothesis",
        }
        if not any(a["local_id"] == hypothesis for a in self.annotations):
            self.node(
                hypothesis,
                kinds[family],
                family,
                occurrences,
                role,
                premises=[owner, member, *premises],
                external_premises=list(external),
                context=self.context.declaration(),
            )
        basis["premises"] = [hypothesis, *premises]
        value = dict(
            owner=owner,
            member=member,
            role=role,
            scheme=REVISION,
            family=family,
            occurrences=occurrences,
            basis=basis,
            required_external_choices=list(choices),
        )
        key = "context-role:" + digest(value)
        if not any(row["local_id"] == key for row in self.roles):
            self.roles.append(dict(local_id=key, **value))
        return key

    def propose_checked(self, *args, **kwargs):
        try:
            return self.propose(*args, **kwargs)
        except ValueError as error:
            family = args[3]
            self.record(family, [p.selector() for p in self.context.parts], "partial", str(error))
            return None

    def quotation_state(self, occurrences):
        extents = [e for oid in occurrences for e in self.occurrences[oid]["extents"]]
        return frozenset(
            key
            for projection, start, end, key in self._quotes
            if extents
            and all(
                e["projection"] == projection
                and start <= e.get("start", -1)
                and e.get("end", end + 1) <= end
                for e in extents
            )
        )

    def quotations(self):
        protected = []
        for layer in self._semantic_dependencies.values():
            body = layer.payload
            occurrences = {o["local_id"]: o for o in body["occurrences"]}
            for annotation in body["annotations"]:
                token = annotation.get("native_token")
                if token and token["source_role"] != "prose":
                    protected.extend(
                        e for oid in annotation["occurrences"] for e in occurrences[oid]["extents"]
                    )
        protected_by_projection = {}
        for extent in protected:
            if extent.get("start", 0) < extent.get("end", 0):
                protected_by_projection.setdefault(extent["projection"], []).append(
                    (extent.get("start", 0), extent.get("end", 0))
                )
        protected_intervals = {}
        for projection, intervals in protected_by_projection.items():
            merged = []
            for start, end in sorted(intervals):
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
                else:
                    merged.append((start, end))
            protected_intervals[projection] = (
                tuple(start for start, _ in merged),
                tuple(end for _, end in merged),
            )
        for part in self.context.parts:
            starts, ends = protected_intervals.get(source_projection(part.view), ((), ()))
            stack = []
            for position in range(part.start, part.end):
                character = part.view.text[position]
                if character not in {'"', "“", "”"} or (
                    position > part.start and part.view.text[position - 1] == "\\"
                ):
                    continue
                protected_index = bisect_right(starts, position) - 1
                if protected_index >= 0 and position < ends[protected_index]:
                    continue
                if (
                    character in {'"', "”"}
                    and stack
                    and (
                        (character == "”" and stack[-1][0] == "“")
                        or (character == '"' and stack[-1][0] == '"')
                    )
                ):
                    _, start = stack.pop()
                    occurrence = self.occurrence(part.view, start, position + 1)
                    key = "context-quote:" + digest(
                        [source_projection(part.view), start, position + 1]
                    )
                    self.node(
                        key,
                        "context.quotation",
                        "context.structure",
                        [occurrence],
                        "paired_source_delimiters",
                        scheme="source-quotation-delimiters-1",
                        status="native_evidence",
                    )
                    self._quotes.append((source_projection(part.view), start, position + 1, key))
                elif character in {'"', "“"}:
                    stack.append((character, position))
            if stack:
                self.record(
                    "context.structure",
                    [part.selector()],
                    "partial",
                    "unclosed source quotation delimiter; quotation context remains incomplete",
                )

    def structural(self):
        """Retain actual hierarchy; heading/list proposals do not become copied qualifiers."""
        selected = {}
        self.quotations()
        for part in self.context.parts:
            native = part.view.view
            by_pointer = native.selected_items(part.start, part.end)
            for pointer, item in by_pointer:
                pieces = [
                    native.pieces[index]
                    for index in native.piece_indices_by_item[pointer]
                    if native.pieces[index]["start"] < part.end
                    and part.start < native.pieces[index]["end"]
                ]
                if not pieces:
                    continue
                occurrences = [
                    self.occurrence(part.view, max(part.start, p["start"]), min(part.end, p["end"]))
                    for p in pieces
                ]
                key = "context-structure:" + digest([source_projection(part.view), pointer])
                if key not in selected:
                    self.node(
                        key,
                        "context.source_item",
                        "context.structure",
                        occurrences,
                        item.get("label", "unknown"),
                        scheme="native-source-hierarchy-1",
                        status="native_evidence",
                        context=self.context.declaration(),
                    )
                    selected[key] = (item, part.view, occurrences)
        for key, (item, view, occurrences) in selected.items():
            parent = item.get("parent", {}).get("$ref")
            parent_key = "context-structure:" + digest([source_projection(view), parent])
            if parent_key in selected:
                self.membership(
                    parent_key,
                    key,
                    "native_child",
                    list(selected).index(key),
                    "context.structure",
                    occurrences,
                )
        # Only a common original section/list hierarchy can nominate heading context.
        # Quoted items do not inherit an outside heading merely by preceding order.
        for key, (item, view, occurrences) in selected.items():
            if item.get("label") != "list_item":
                continue
            ancestors = set()
            pointer = item.get("parent", {}).get("$ref")
            by_pointer = {
                node["self_ref"]: node
                for node in (*getattr(view, "items", ()), *getattr(view, "ancestors", ()))
            }
            while pointer and pointer not in ancestors:
                ancestors.add(pointer)
                pointer = by_pointer.get(pointer, {}).get("parent", {}).get("$ref")
            for heading, (node, heading_view, _) in selected.items():
                if source_identity(heading_view) != source_identity(view) or node.get(
                    "label"
                ) not in {
                    "section_header",
                    "title",
                    "heading",
                }:
                    continue
                if node.get("parent", {}).get("$ref") in ancestors and self.quotation_state(
                    occurrences
                ) == self.quotation_state(selected[heading][2]):
                    self.propose(
                        key,
                        heading,
                        "heading_context",
                        "context.inheritance",
                        premises=[key, heading],
                    )
        self.record("context.structure", [p.selector() for p in self.context.parts])
        self.record("context.inheritance", [p.selector() for p in self.context.parts])

    def maverick(
        self,
        tokens: Sequence[dict[str, Any]],
        request: Mapping[str, Any],
        reply: Mapping[str, Any],
        *,
        run="maverick",
    ):
        if reply.get("tokens") != [t["text"] for t in tokens] or request.get(
            "sentences"
        ) != self.sentences(tokens):
            raise ValueError("Maverick returned a different admitted canonical token population")

        def spans(value):
            if not isinstance(value, list):
                raise ValueError("Maverick mention population must be ordered")
            result = []
            for span in value:
                if (
                    not isinstance(span, (list, tuple))
                    or len(span) != 2
                    or any(type(x) is not int for x in span)
                    or not 0 <= span[0] <= span[1] < len(tokens)
                ):
                    raise ValueError("Maverick mention endpoint outside canonical population")
                result.append(tuple(span))
            return result

        detected, supplied = (
            spans(reply.get("mentions", [])),
            spans(request.get("predefined_mentions", [])),
        )
        clusters = [spans(group) for group in reply.get("clusters", [])]
        assigned = {span for group in clusters for span in group}
        if sum(len(set(group)) for group in clusters) != len(assigned):
            raise ValueError("Maverick local partition has competing canonical memberships")
        mentions = {}
        for first, last in sorted(set(detected) | set(supplied) | assigned):
            key = "maverick-mention:" + digest([run, self.scope_id, first, last])
            # Native endpoint crossing a sentence is retained as refused mapping.
            mapped = tokens[first]["sentence"] == tokens[last]["sentence"]
            occurrences = (
                list(
                    dict.fromkeys(
                        o for token in tokens[first : last + 1] for o in token["occurrences"]
                    )
                )
                if mapped
                else self.support
            )
            native = dict(
                native_run=run,
                coordinate_unit="inclusive_canonical_token",
                first=first,
                last=last,
                detected=(first, last) in detected,
                supplied=(first, last) in supplied,
                clustered=(first, last) in assigned,
                mapping_status="mapped" if mapped else "unmapped",
            )
            if not mapped:
                native["reason"] = (
                    "native mention endpoints cross supplied canonical sentence ownership"
                )
            self.node(
                key,
                "native.mention" if mapped else "native.unmapped_mention",
                "maverick.mentions",
                occurrences,
                "mention",
                scheme="maverick-mes-canonical-1",
                status="native_evidence",
                native_mention=native,
                context=self.context.declaration(),
            )
            mentions[first, last] = key
            self._mention_metadata[key] = native
        for index, group in enumerate(clusters):
            keys = [mentions[pair] for pair in dict.fromkeys(group)]
            occurrences = [
                o
                for key in keys
                for a in self.annotations
                if a["local_id"] == key
                for o in a["occurrences"]
            ]
            cluster = "maverick-cluster:" + digest([run, self.scope_id, index])
            self.node(
                cluster,
                "native.coreference_cluster",
                "maverick.clusters",
                occurrences,
                str(index),
                scheme="maverick-local-partition-1",
                status="native_evidence",
                context=self.context.declaration(),
            )
            for order, key in enumerate(keys):
                self.membership(
                    cluster,
                    key,
                    "native_member",
                    order,
                    "maverick.clusters",
                    next(a["occurrences"] for a in self.annotations if a["local_id"] == key),
                )
            self._native_clusters.append((cluster, keys))
        # Native subtoken inventory and clusters are separate populations. They have
        # examined-context support, never fabricated source-character authority.
        raw_detected = [tuple(p) for p in reply.get("mentions_subtokens", [])]
        raw_clusters = [[tuple(p) for p in group] for group in reply.get("clusters_subtokens", [])]
        raw_assigned = {pair for group in raw_clusters for pair in group}
        reasons = {
            tuple(row["subtokens"]): row["reason"] for row in reply.get("unmapped_mentions", [])
        }
        for first, last in sorted(set(raw_detected) | raw_assigned):
            if type(first) is not int or type(last) is not int or not 0 <= first <= last:
                raise ValueError("invalid native Maverick subtoken endpoints")
            key = "maverick-subtoken:" + digest([run, self.scope_id, first, last])
            native = dict(
                native_run=run,
                coordinate_unit="inclusive_subtoken",
                first=first,
                last=last,
                detected=(first, last) in raw_detected,
                supplied=False,
                clustered=(first, last) in raw_assigned,
                mapping_status="unmapped",
                reason=reasons.get(
                    (first, last),
                    "native subtoken coordinates retained without an authenticated "
                    "character correspondence",
                ),
            )
            self.node(
                key,
                "native.unmapped_mention",
                "maverick.mentions",
                self.support,
                "native-subtoken-mention",
                scheme="maverick-mes-subtoken-1",
                status="native_evidence",
                native_mention=native,
                context=self.context.declaration(),
            )
        for index, group in enumerate(raw_clusters):
            key = "maverick-subtoken-cluster:" + digest([run, self.scope_id, index])
            self.node(
                key,
                "native.coreference_subtoken_cluster",
                "maverick.clusters",
                self.support,
                str(index),
                scheme="maverick-local-subtoken-partition-1",
                status="native_evidence",
                context=self.context.declaration(),
            )
            for order, (first, last) in enumerate(group):
                member = "maverick-subtoken:" + digest([run, self.scope_id, first, last])
                self.membership(
                    key, member, "native_subtoken_member", order, "maverick.clusters", self.support
                )
        for family in ("maverick.mentions", "maverick.clusters"):
            self.record(family, [p.selector() for p in self.context.parts])

    @staticmethod
    def sentences(tokens):
        result, current = [], object()
        for token in tokens:
            if token["sentence"] != current:
                result.append([])
                current = token["sentence"]
            result[-1].append(token["text"])
        return result

    def dipo(self, request: Mapping[str, Any], reply: Mapping[str, Any], *, run="dipo"):
        mode = request.get("mode", "learned")
        if (
            mode not in {"learned", "layout_forced"}
            or request.get("text") != self.context.text
            or reply.get("mode", "learned") != mode
        ):
            raise ValueError(
                "ordinary Dipo context requires actual raw-source prediction, "
                "not paired diagnostic reconstruction"
            )
        rows, splits = reply["edus"], reply["spans"]
        _tree_children(splits, len(rows))
        token_count = reply["post_tokenizer_tokens"]
        if type(token_count) is not int or token_count < 1:
            raise ValueError("Dipo native token population is invalid")
        position, previous_char, ends, edus = 0, 0, [], []
        for index, row in enumerate(rows):
            a, b = _pair(row["tokens"], token_count)
            start, end = _pair(row["chars"], len(self.context.text))
            if a != position or start < previous_char:
                raise ValueError("Dipo EDUs do not partition ordered native tokens/characters")
            text = self.context.text[start:end]
            if row["text"] != " ".join(text.split()):
                raise ValueError("Dipo native EDU text differs from exact raw-source coordinates")
            occurrences = self.context.occurrences(self, start, end)
            key = "dipo-edu:" + digest([run, self.scope_id, index])
            self.node(
                key,
                "native.edu",
                "dipo.edus",
                occurrences,
                row["text"],
                scheme="dipo-dmrst-raw-edu-1",
                status="native_evidence",
                native_edu=dict(
                    native_run=run,
                    mode=mode,
                    index=index,
                    token_start=a,
                    token_end=b,
                    provider_start=start,
                    provider_end=end,
                    text=row["text"],
                ),
                context=self.context.declaration(),
            )
            edus.append((key, occurrences))
            position, previous_char = b, end
            ends.append(b)
        if position != token_count:
            raise ValueError("Dipo EDU result omits native token population")
        _validate_boundaries(
            reply.get("boundaries", []), ends, layout_forced=mode == "layout_forced"
        )
        for index, boundary in enumerate(reply["boundaries"]):
            key = "dipo-boundary:" + digest([run, self.scope_id, index, boundary])
            self.node(
                key,
                "native.edu_boundary",
                "dipo.edus",
                self.support,
                boundary["disposition"],
                scheme="dipo-native-boundary-1",
                status="native_evidence",
                native_boundary=dict(boundary),
                context=self.context.declaration(),
            )
        ranges = {(i, i + 1): entry for i, entry in enumerate(edus)}
        for split in sorted(splits, key=lambda row: row["right"][1] - row["left"][0]):
            left, right = tuple(split["left"]), tuple(split["right"])
            members = [*ranges[left][1], *ranges[right][1]]
            key = "dipo-rst:" + digest([run, self.scope_id, left, right])
            self.node(
                key,
                "native.rst_node",
                "dipo.rst",
                members,
                split["relation"],
                scheme="dipo-rst-relation-1",
                status="native_evidence",
                native_rst=dict(
                    left_start=left[0],
                    left_end=left[1],
                    right_start=right[0],
                    right_end=right[1],
                    nuclearity=split["nuclearity"],
                ),
                context=self.context.declaration(),
            )
            for order, child in enumerate((left, right)):
                label = "nucleus" if split["nuclearity"][order] == "N" else "satellite"
                self.membership(key, ranges[child][0], label, order, "dipo.rst", ranges[child][1])
            ranges[left[0], right[1]] = (key, list(dict.fromkeys(members)))
            if "condition" in split["relation"].casefold():
                if split["nuclearity"] == "NS":
                    self._rst_hosts.append((ranges[right][1], ranges[left][1], key))
                elif split["nuclearity"] == "SN":
                    self._rst_hosts.append((ranges[left][1], ranges[right][1], key))
                else:
                    self._rst_hosts.extend(
                        (
                            (ranges[left][1], ranges[right][1], key),
                            (ranges[right][1], ranges[left][1], key),
                        )
                    )
        root = ranges[0, len(edus)]
        if len(edus) == 1:
            key = "dipo-singleton:" + digest([run, self.scope_id])
            self.node(
                key,
                "native.rst_singleton",
                "dipo.rst",
                root[1],
                "singleton",
                scheme="dipo-rst-relation-1",
                status="native_evidence",
                context=self.context.declaration(),
            )
            self.membership(key, root[0], "single_edu", 0, "dipo.rst", root[1])
        for family in ("dipo.edus", "dipo.rst"):
            self.record(family, [p.selector() for p in self.context.parts])

    def hypotheses(self):
        source_nodes = {a["local_id"]: a for a in self.annotations}
        for group, cluster in self._native_clusters:
            for mention in cluster:
                source = source_nodes[mention]
                if (
                    self._mention_metadata.get(mention, source.get("native_mention", {})).get(
                        "mapping_status"
                    )
                    == "mapped"
                ):
                    self.propose_checked(
                        mention,
                        group,
                        "source_local_coreference_group_candidate",
                        "context.reference",
                        premises=[mention, group],
                        support=source["occurrences"],
                    )
        if (
            not self._mention_metadata
            and self.covered["maverick.mentions"]
            and all(status == "complete" for _, status, _ in self.covered["maverick.mentions"])
        ):
            self.node(
                "unknown-native-reference:" + self.scope_id,
                "context.unresolved_reference",
                "context.reference",
                self.support,
                "native detector supplied no source candidates; reference presence remains unknown",
                status="unknown",
                context=self.context.declaration(),
            )
        for mention in [
            a
            for a in self.annotations
            if a["local_id"] in self._mention_metadata
            and self._mention_metadata[a["local_id"]]["mapping_status"] == "mapped"
            and not self._mention_metadata[a["local_id"]]["clustered"]
        ]:
            self.node(
                "unresolved-reference:" + digest(mention["local_id"]),
                "context.unresolved_reference",
                "context.reference",
                mention["occurrences"],
                "no_native_cluster_candidate",
                status="unknown",
                premises=[mention["local_id"]],
                context=self.context.declaration(),
            )
        source_occurrences = dict(self.occurrences)
        for layer in self._semantic_dependencies.values():
            source_occurrences.update((o["local_id"], o) for o in layer.payload["occurrences"])

        def overlaps(left, right):
            return any(
                a["projection"] == b["projection"]
                and a.get("start", 0) < b.get("end", 0)
                and b.get("start", 0) < a.get("end", 0)
                for x in left
                for a in source_occurrences[x]["extents"]
                for y in right
                for b in source_occurrences[y]["extents"]
            )

        for pin, report in self._semantic_dependencies.items():
            terms = {t["local_id"]: t for t in report.payload["terms"]}
            for term in terms.values():
                if not term.get("occurrences"):
                    continue
                try:
                    site = self.proxy(
                        pin,
                        term["local_id"],
                        family="context.binding" if term["kind"] == "binder" else "context.host",
                    )
                except ValueError:
                    continue  # Outside examined context is never silently brought into inference.
                if term["kind"] == "binder":
                    for edge in term.get("children", ()):
                        if edge["role"] == "variable" and "choice_group" in edge:
                            self.record(
                                "context.binding",
                                [p.selector() for p in self.context.parts],
                                "partial",
                                "packed binder variable site remains choice-dependent; "
                                "no alternative expansion",
                            )
                        if edge["role"] == "variable" and edge.get("target") in terms:
                            variable = terms[edge["target"]]
                            target = self.proxy(pin, variable["local_id"], family="context.binding")
                            self.propose_checked(
                                site,
                                target,
                                "declared_binding_site",
                                "context.binding",
                                external=[member_reference(pin, term["local_id"]).values()],
                                choices=[
                                    *self.required_choices(pin, term),
                                    *self.required_choices(pin, variable),
                                ],
                            )
                elif term["kind"] == "predicate":
                    node_index = {a["local_id"]: a for a in self.annotations}
                    for inherited in list(self.roles):
                        if inherited["role"] != "heading_context":
                            continue
                        item = node_index[inherited["owner"]]
                        if overlaps(
                            term["occurrences"], item["occurrences"]
                        ) and self.quotation_state(term["occurrences"]) == self.quotation_state(
                            node_index[inherited["member"]]["occurrences"]
                        ):
                            self.propose_checked(
                                site,
                                inherited["member"],
                                "list_heading_participant_context_candidate",
                                "context.inheritance",
                                premises=[inherited["basis"]["premises"][0]],
                                external=[member_reference(pin, term["local_id"]).values()],
                                choices=self.required_choices(pin, term),
                            )
                elif term["kind"] == "attribution":
                    for edge in term.get("children", ()):
                        if (
                            edge["role"] in {"source", "reporter", "content", "body"}
                            and edge.get("target") in terms
                        ):
                            child = terms[edge["target"]]
                            target = self.proxy(
                                pin, child["local_id"], family="context.attribution"
                            )
                            self.propose_checked(
                                site,
                                target,
                                "attribution_" + edge["role"],
                                "context.attribution",
                                external=[member_reference(pin, term["local_id"]).values()],
                                choices=[
                                    *self.required_choices(pin, term),
                                    *self.required_choices(pin, child),
                                ],
                            )
                elif term["kind"] in {"operator", "unknown"}:
                    for satellite, nucleus, native in self._rst_hosts:
                        if not overlaps(term["occurrences"], satellite):
                            continue
                        for host in terms.values():
                            if host["kind"] not in {"predicate", "clause_relation"} or not overlaps(
                                host.get("occurrences", ()), nucleus
                            ):
                                continue
                            target = self.proxy(pin, host["local_id"], family="context.host")
                            self.propose_checked(
                                site,
                                target,
                                "native_condition_host_candidate",
                                "context.host",
                                premises=[native],
                                external=[
                                    member_reference(pin, term["local_id"]).values(),
                                    member_reference(pin, host["local_id"]).values(),
                                ],
                                choices=[
                                    *self.required_choices(pin, term),
                                    *self.required_choices(pin, host),
                                ],
                            )
        for family in (
            "context.reference",
            "context.host",
            "context.binding",
            "context.attribution",
        ):
            required_native = (
                ("maverick.mentions", "maverick.clusters")
                if family == "context.reference"
                else ("dipo.edus", "dipo.rst")
                if family == "context.host"
                else ()
            )
            reasons = [
                native
                for native in required_native
                if not self.covered[native]
                or any(status != "complete" for _, status, _ in self.covered[native])
            ]
            symbolic_family = {
                "context.host": "construction.scope",
                "context.binding": "construction.scope",
                "context.attribution": "construction.attribution",
            }.get(family)
            symbolic = symbolic_family is None or any(
                any(
                    row["family"] == symbolic_family
                    and row["outcome"] in {"complete", "empty"}
                    and row["availability"] == "available"
                    for row in layer.payload["coverage"]
                )
                for layer in self._semantic_dependencies.values()
            )
            if not symbolic:
                reasons.append("TC05/06 complete " + symbolic_family)
            self.record(
                family,
                [p.selector() for p in self.context.parts],
                "partial" if reasons else "complete",
                "missing/incomplete contextual premises: " + ", ".join(reasons)
                if reasons
                else None,
            )
        symbolic_available = any(
            any(
                row["family"] in {"construction.predication", "construction.source_readings"}
                and row["outcome"] in {"complete", "empty"}
                and row["availability"] == "available"
                for row in layer.payload["coverage"]
            )
            for layer in self._semantic_dependencies.values()
        )
        if not symbolic_available:
            self.record(
                "context.inheritance",
                [p.selector() for p in self.context.parts],
                "partial",
                "structural heading context retained; TC05/06 grammatical "
                "participant sites unavailable",
            )
        if self.context.gaps:
            for family in (
                "context.reference",
                "context.host",
                "context.binding",
                "context.inheritance",
                "context.attribution",
            ):
                self.record(
                    family,
                    [p.selector() for p in self.context.parts],
                    "partial",
                    "unexamined original crossings are retained in context.gaps",
                )
