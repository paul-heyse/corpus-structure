"""Selected private candidates, captured reading events and finite interpretations.

Packet references address actual nominal members. Coverage, reading events and
finite reports remain fields of their actual whole product, never new members.
These projections neither run inference nor confer knowledge admission.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .data_operation_json import json_bytes
from .data_operation_kind_refinements import input_kind_refinements
from .observations import source_python
from .rich_queries import RichQueryRefused, RichQueryRow

if TYPE_CHECKING:
    from .types import PreparedRelease

CANDIDATE_NAMESPACE = "https://corpus-structure.dev/semantic/data-operation-candidate-inspection/"
READING_KIND = "https://corpus-structure.dev/semantic/data-operation-reading-resolution/DdoResolvedReadingReport"
FINITE_KIND = "https://corpus-structure.dev/semantic/data-operation-interpretation/DdoFiniteInterpretationProduct"
_ROOTS = {
    CANDIDATE_NAMESPACE + "DdoCandidateInspectionReport": "candidates",
    CANDIDATE_NAMESPACE + "DdoCandidateSourceRecord": "record",
    CANDIDATE_NAMESPACE + "DdoCandidateSourceContribution": "source-contribution",
    READING_KIND: "readings",
    FINITE_KIND: "finite",
}


@dataclass(frozen=True)
class CandidateFacetKinds:
    families: dict
    kinds: dict
    contracts: dict
    definitions: dict
    prepared: PreparedRelease

    @classmethod
    def from_model(cls, model, prepared):
        kinds = {kind.semantic_id: kind for kind in model.kinds}
        roots = tuple(root for root in _ROOTS if root in kinds)
        refinements = input_kind_refinements(model, roots) if roots else {}
        families = {nominal: _ROOTS[root] for root in roots for nominal in refinements[root]}
        definitions = {}
        for item in prepared.definitions:
            definitions.setdefault(item.iri, []).append(item)
        return cls(
            families,
            kinds,
            {item.key: item.owner for item in model.identities if item.domain == "kind"},
            definitions,
            prepared,
        )

    def validate(self, nominal, contract, body):
        kind = self.kinds.get(nominal)
        if (
            kind is None
            or not kind.complete
            or self.contracts.get(contract) != nominal
            or nominal not in self.families
        ):
            raise RichQueryRefused("private facet lacks its complete captured nominal contract")
        definitions = self.definitions.get(nominal, ())
        if len(definitions) != 1 or definitions[0].name != kind.name:
            raise RichQueryRefused("private facet lacks its captured nominal definition")
        # The actual released nominal owner supplies and checks defaults. A
        # missing spelling must never be replaced by a guessed private standing.
        body = self.prepared.validate_json(kind.name, json_bytes(body)).model_dump(
            mode="python", exclude_none=True
        )
        family = self.families[nominal]
        standing = {
            "candidates": "private_uncalibrated_candidates",
            "readings": "private_uncalibrated_candidates",
            "record": "candidate",
            "source-contribution": "retained_private",
            "finite": "private_candidate_relative",
        }[family]
        if body.get("standing") != standing:
            raise RichQueryRefused("private facet cannot upgrade its actual candidate standing")
        if family in {"record", "source-contribution"} and body["candidate_type"] != (
            "record" if family == "record" else "contribution"
        ):
            raise RichQueryRefused("private facet body differs from its actual nominal member kind")
        return family, body


def _bounded(value, bound):
    pending = [value]
    count = 0
    while pending:
        item = pending.pop()
        if isinstance(item, dict):
            pending.extend(item.values())
        elif isinstance(item, (tuple, list)):
            count += len(item)
            if count > bound:
                raise RichQueryRefused("private facet exceeds its complete nested-member bound")
            pending.extend(item)


def _row(population, **meaning):
    return RichQueryRow(dict(population=population, row=meaning))


def _base(selected, nominal, body, *, packet=None):
    reference = selected.reference
    if packet is not None:
        reference = reference.model_copy(
            update={"member_id": packet["member_id"], "kind_contract": packet["kind_contract"]}
        )
    return dict(
        reference=reference.model_dump(mode="python"),
        context=selected.context.identity_record if packet is None else packet["context"],
        nominal=nominal,
        standing=body["standing"],
        scientific_truth="not-established",
    )


def candidate_facets(
    selected,
    kinds,
    *,
    interpretation,
    assessment,
    member_id=None,
    max_members=100000,
    max_nested_members=1000,
):
    body = selected.body
    family, body = kinds.validate(selected.nominal, selected.reference.kind_contract, body)
    if family in {"record", "source-contribution"}:
        if selected.reference.member_id is None:
            raise RichQueryRefused("candidate member facet requires its actual selected member")
        if member_id is not None and member_id != selected.reference.member_id:
            return
        _bounded(body, max_nested_members)
        yield from _member_rows(
            selected,
            _base(selected, selected.nominal, body),
            body,
            interpretation=interpretation,
            assessment=assessment,
            events=None,
        )
        return
    if selected.reference.member_id is not None:
        raise RichQueryRefused("private report facet requires its actual selected whole")
    if family == "finite":
        if member_id is not None:
            return
        reports = source_python(body["reports"])
        if not isinstance(reports, list):
            raise RichQueryRefused("finite facet requires its complete retained report sequence")
        if len(reports) > max_members:
            raise RichQueryRefused("finite facet exceeds its actual report bound")
        base = _base(selected, selected.nominal, body)
        yield _row("contribution", **base)
        if interpretation:
            yield _row(
                "interpretation",
                **base,
                availability="observed",
                scope="captured-private-finite-report-population",
                meaning={key: value for key, value in body.items() if key != "reports"},
                report_count=len(reports),
            )
        for position, report in enumerate(reports):
            _bounded(report, max_nested_members)
            fields = dict(
                base,
                source_pin=body["source_pin"],
                mode=body["mode"],
                report_position=position,
                availability="observed",
                public_admission="not-established",
            )
            if interpretation:
                yield _row(
                    "interpretation",
                    **fields,
                    scope="typed-private-candidate-relative-finite-report",
                    meaning=report,
                )
            if assessment:
                yield _row(
                    "assessment",
                    **fields,
                    scope="captured-private-finite-producer-judgments",
                    judgments=report,
                )
        return

    packets = body["members"]
    if len(packets) > max_members:
        raise RichQueryRefused("candidate facet exceeds its actual member bound")
    members = {}
    for packet in packets:
        nominal = kinds.contracts.get(packet["kind_contract"])
        if kinds.families.get(nominal) not in {"record", "source-contribution"}:
            raise RichQueryRefused("candidate packet lacks its actual nominal member contract")
        _, value = kinds.validate(nominal, packet["kind_contract"], packet["body"])
        packet = {**packet, "body": value}
        if packet["member_id"] in members:
            raise RichQueryRefused("candidate packet repeats its actual member identity")
        members[packet["member_id"]] = (nominal, packet)
    events = None
    if family == "readings":
        if not body["reading_policy_digest"]:
            raise RichQueryRefused("reading facet requires its actual captured policy digest")
        events = source_python(body["reading_events"])
        if not isinstance(events, list) or any(not isinstance(event, dict) for event in events):
            raise RichQueryRefused("reading facet requires its complete retained event sequence")
        if len(events) > max_members:
            raise RichQueryRefused("reading facet exceeds its actual event bound")
    if member_id is None:
        base = _base(selected, selected.nominal, body)
        yield _row("contribution", **base)
        metadata = {
            key: value for key, value in body.items() if key not in {"members", "reading_events"}
        }
        if events is not None:
            metadata["reading_events"] = events
        _bounded(metadata, max_nested_members)
        if interpretation:
            yield _row(
                "interpretation",
                **base,
                availability="observed",
                scope="captured-private-candidate-inspection",
                meaning=metadata,
            )
        if assessment:
            yield _row(
                "assessment",
                **base,
                availability="observed" if events else "unknown",
                scope="captured-private-reading-events",
                reading_events=events or [],
                reading_policy_digest=body.get("reading_policy_digest"),
                public_admission="not-established",
                reason=None if events else "no-associated-reading-event-in-this-selected-output",
            )
        for coverage in body["coverage"]:
            yield _row(
                "coverage",
                **base,
                source_pin=body["source_pin"],
                coverage=coverage,
                source_scope="captured-inspection-scope",
                original_source_completeness="unknown",
            )
    by_reading = {}
    for event in events or ():
        by_reading.setdefault((event.get("record_id"), event.get("interpretation_id")), []).append(
            event
        )
    for identifier, (nominal, packet) in sorted(members.items()):
        if member_id is not None and member_id != identifier:
            continue
        value = packet["body"]
        _bounded(value, max_nested_members)
        matched = (
            by_reading.get((value["record_id"], value["interpretation_id"]), [])
            if value["candidate_type"] == "record"
            else []
        )
        _bounded(matched, max_nested_members)
        yield from _member_rows(
            selected,
            _base(selected, nominal, value, packet=packet),
            value,
            interpretation=interpretation,
            assessment=assessment,
            events=matched if events is not None else None,
            reading_policy_digest=body.get("reading_policy_digest"),
        )


def _member_rows(
    selected, base, body, *, interpretation, assessment, events, reading_policy_digest=None
):
    yield _row("contribution", **base)
    if interpretation:
        yield _row(
            "interpretation",
            **base,
            availability="observed",
            source_pin=body["pin"],
            meaning=body,
            scope="typed-private-source-candidate",
        )
    if assessment:
        yield _row(
            "assessment",
            **base,
            availability="observed" if events else "unknown",
            scope="captured-private-reading-events",
            reading_events=events or [],
            reading_policy_digest=reading_policy_digest,
            public_admission="not-established",
            reason=None if events else "no-associated-reading-event-in-this-selected-output",
        )
