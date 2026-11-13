"""Materialize a sealed observation cut and publish one fresh evaluated realization.

Source reports remain immutable operational data. Domain policy is an explicit release-bound
operation; storage validity and a singleton candidate never substitute for its findings.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping
from contextlib import suppress
from dataclasses import asdict, dataclass, fields, replace
from hashlib import sha256
from pathlib import Path
from types import MappingProxyType, SimpleNamespace
from typing import Any, Protocol

import pyarrow as pa
import yaml
from linkml_runtime.utils.yamlutils import DupCheckYamlLoader
from sqlalchemy import func, select
from sqlalchemy.engine import Engine

from corpus_structure.settings import AnalyticsSettings

from ._operation_ids import CutId, RunId
from .analytics import AnalysisScope, CandidateInput, compile_projection
from .consolidation import FactItem, FactValueLowerer, SourceItem, assemble
from .identity import canonical_bytes, claim_source_item, occurrence_key
from .metadata import table
from .operations import OperationConflict, cut_observations
from .publication import (
    AlternativeGroupRow,
    AlternativeMemberRow,
    AssessmentRow,
    CoverageRow,
    EntityResolutionRow,
    EvidenceRow,
    EvidenceSourceRow,
    MembershipRow,
    PublicationBatch,
    PublicationReceipt,
    ScientificRepresentativeRow,
    SelectionRow,
    _publish,
)
from .query import SnapshotBinding
from .record_projection import RecordAdmissionRow
from .refusals import (
    SemanticOperationRefusal,
    SemanticReason,
    SemanticReasonCode,
    SemanticRefusal,
    semantic_reason_identity,
)
from .releases import open_release
from .types import PreparedRelease, ResolvedDependencies, SourceArtifact

RULE_INPUT = "operation/domain-rules.yaml"
VERSION = "semantic-domain-3"


class DomainOperationRefused(SemanticRefusal):
    """A required interpretation or scientific policy is unavailable; no output is selected."""


class IdentityResolutionConflict(DomainOperationRefused):
    """A required identity equality contradicts a source-grounded exclusion."""

    code = "identity_conflict"

    def __init__(self, release_id, exclusion_id, left, right, entity_id):
        self.release_id = release_id
        self.exclusion_id = exclusion_id
        self.left = left
        self.right = right
        self.entity_id = entity_id
        super().__init__(
            f"identity_conflict: exclusion {exclusion_id} contradicts "
            f"mandatory identity {entity_id}"
        )


def _eligible_exclusion(exclusion):
    return any(
        e.get("outcome") == "located" and e["role"] == "primary" for e in exclusion["evidence"]
    )


def _policy_yaml(content):
    """Keep LinkML duplicate refusal and lower its location-tagged strings to YAML scalars."""

    def scalars(value):
        if isinstance(value, str):
            return value[:]
        if isinstance(value, dict):
            return {scalars(k): scalars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [scalars(v) for v in value]
        return value

    return scalars(yaml.load(content, Loader=DupCheckYamlLoader))


def domain_rule_inputs(
    dependencies: ResolvedDependencies,
    domain: bytes,
    core: bytes = b"",
    *,
    aliases: Mapping[str, Any] | None = None,
    execution_model=None,
) -> ResolvedDependencies:
    """Archive existing rules as one operation dependency, never read latest files in a run."""
    from .alias_policy import SOURCE_PROFILE
    from .scientific_evidence import scientific_policy_recipe

    source = _policy_yaml(domain) or {}
    base = _policy_yaml(core) or {}
    if set(base) - {"rules"}:
        raise ValueError("core operation rules must contain only rules")
    source["rules"] = [*base.get("rules", ()), *source.get("rules", ())]
    operation = {"name": "semantic-domain", "version": VERSION}
    if "operation" in source and source["operation"] != operation:
        raise ValueError("unsupported domain operation header")
    source["operation"] = operation
    from .rule_views import RULE_VIEW_ABI

    source["rule_view_abi"] = RULE_VIEW_ABI
    if aliases is not None:
        source["identity"] = {"aliases": dict(aliases)}
    identity = source.setdefault("identity", {})
    if not isinstance(identity, dict):
        raise ValueError("invalid operation identity policy")
    if identity.get("alias_profile", SOURCE_PROFILE) != SOURCE_PROFILE:
        raise ValueError("unsupported alias input profile")
    identity["alias_profile"] = SOURCE_PROFILE
    if any(a.name == RULE_INPUT for a in dependencies.artifacts):
        raise ValueError("domain rules already declared")
    return replace(
        dependencies,
        artifacts=(
            *dependencies.artifacts,
            SourceArtifact(RULE_INPUT, yaml.safe_dump(source, sort_keys=True).encode()),
            SourceArtifact(
                "operation/scientific-policy.json",
                canonical_bytes(scientific_policy_recipe(model=execution_model)),
            ),
            *(
                SourceArtifact(
                    "operation/" + name,
                    (Path(__file__).resolve().parents[1] / "model/semantic" / name).read_bytes(),
                )
                for name in ("scientific.yaml", "scientific-policies.yaml")
            ),
            SourceArtifact(
                "operation/rule-view.yaml",
                (
                    Path(__file__).resolve().parents[1] / "model/semantic/rule-view.yaml"
                ).read_bytes(),
            ),
        ),
    )


@dataclass(frozen=True)
class ClaimCandidate:
    fact_id: str
    occurrence_id: str
    observation_key: str
    local_id: str
    subject: str
    class_name: str
    predicate: str
    object: Any
    qualification: Mapping[str, Any]
    establishment: str
    statement: str | None
    statement_kind: str | None
    statement_role: str | None
    alternatives: tuple[str, ...]
    evidence_count: int
    macros: Mapping[str, Any]
    qualification_class: str = "Qualification"
    unresolved_references: tuple[str, ...] = ()
    rule_object: Any = None
    rule_qualification: Mapping[str, Any] | None = None
    constants: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateContextIndex:
    premises: Mapping[str | None, frozenset[str]]
    global_premises: frozenset[str]
    symbols_by_occurrence: Mapping[str, frozenset[str]]
    symbol_owners: Mapping[str, frozenset[str]]

    @classmethod
    def prepare(cls, prepared, candidates, gives):
        premises = defaultdict(set)
        global_premises = set()
        symbol_owners = defaultdict(set)
        for candidate in candidates:
            if prepared.member_has_behavior(
                "StatementRole", candidate.statement_role, "participates_as_premise"
            ):
                premises[candidate.statement].add(candidate.occurrence_id)
                if prepared.member_has_behavior(
                    "StatementKind", candidate.statement_kind, "global_premise_context"
                ):
                    global_premises.add(candidate.occurrence_id)
            for symbol in gives.get(candidate.occurrence_id, ()):
                symbol_owners[symbol].add(candidate.occurrence_id)
        return cls(
            MappingProxyType({key: frozenset(members) for key, members in premises.items()}),
            frozenset(global_premises),
            MappingProxyType({key: frozenset(members) for key, members in gives.items()}),
            MappingProxyType({key: frozenset(members) for key, members in symbol_owners.items()}),
        )

    def statement_premises(self, candidate) -> tuple[str, ...]:
        return tuple(
            sorted(
                (self.premises.get(candidate.statement, frozenset()) | self.global_premises)
                - {candidate.occurrence_id}
            )
        )

    def given_by_others(self, occurrence_id: str) -> tuple[str, ...]:
        return tuple(
            sorted(
                symbol for symbol, owners in self.symbol_owners.items() if owners - {occurrence_id}
            )
        )


def _candidate_reading(prepared, candidate, raw, readings):
    """Translate only owned preparation/reading inability; programming errors propagate."""
    from corpus_structure.core.evidence import MacroDef

    from .analysis_contracts import prepare_interpretation_context
    from .grammar_profile import GRAMMAR_KINDS
    from .rule_views import Reading
    from .types import PreparationError

    lexical = raw.get("expression")
    if lexical is None:
        return None, None
    if raw.get("language") != "latex":
        return None, SemanticReason(
            "unsupported_interpretation",
            "evaluate",
            prepared.release_id,
            (candidate.occurrence_id,),
            expected="latex",
            actual=raw.get("language"),
            detail="scientific expression language has no declared reading operation",
        )
    try:
        macros = {name: MacroDef.model_validate(value) for name, value in candidate.macros.items()}
        kind = str(raw.get("kind"))
        context = prepare_interpretation_context(
            prepared,
            macros=macros,
            constants=candidate.constants,
            bindings=raw.get("bindings", ()),
            kind="set_expr" if kind == "set" else "any_value",
            demand="symbolic",
        )
        key = (lexical, kind, context.key())
        if key not in readings:
            from corpus_structure.methods.math.prepared import PreparedMathInput

            result = PreparedMathInput(context, lexical).symbolic_reading()
            context.validate_result(
                produced=("lexical", "syntax", "occurrences", "interpretation", "symbolic"),
                interpretation=result.status.value,
                completeness="failed" if result.failure else "complete",
            )
            readings[key] = Reading(
                result.status.value,
                GRAMMAR_KINDS.get(result.kind or ""),
                tuple(
                    sorted(
                        {
                            occurrence.name
                            for occurrence in result.occurrences
                            if not occurrence.constant
                        }
                    )
                ),
            )
        reading = readings[key]
    except PreparationError as error:
        # These describe source meaning that this operation cannot prepare. Admission,
        # runtime and internal result-contract defects retain their failure identity.
        source_context_codes = {
            "analysis_binding_kind",
            "analysis_declaration",
            "analysis_declaration_authority",
        }
        if not error.diagnostics or any(
            diagnostic.code not in source_context_codes for diagnostic in error.diagnostics
        ):
            raise
        return None, SemanticReason(
            "preparation_failed",
            "evaluate",
            prepared.release_id,
            (candidate.occurrence_id,),
            expected="prepared interpretation context",
            actual=",".join(sorted({diagnostic.code for diagnostic in error.diagnostics})),
            detail=str(error),
        )
    if reading.status != "ok":
        return reading, SemanticReason(
            "preparation_failed" if reading.status == "failed" else "unsupported_interpretation",
            "evaluate",
            prepared.release_id,
            (candidate.occurrence_id,),
            expected="ok",
            actual=reading.status,
            detail="mathematical reading " + reading.status,
        )
    return reading, None


@dataclass(frozen=True)
class NativeEvidenceLink:
    observation_id: int
    source_view_id: int
    start: int
    end: int
    native_address: str


def _evidence_link(observation, descriptor, start, end, locator):
    frame = descriptor.get("frame")
    from .proposals import NativeProposalFrame, native_address, native_statement_source

    if isinstance(frame, NativeProposalFrame):
        cited = native_statement_source(frame, locator)
        return NativeEvidenceLink(
            observation["id"],
            cited.source_view_id,
            start,
            end,
            native_address(cited, start=start, end=end),
        )
    return observation["id"], descriptor["rendition_id"], start, end


def _evidence_source_text(descriptor, locator):
    from .proposals import NativeProposalFrame, native_statement_source

    frame = descriptor.get("frame")
    return (
        native_statement_source(frame, locator).text
        if isinstance(frame, NativeProposalFrame)
        else descriptor["text"]
    )


@dataclass(frozen=True)
class CutInput:
    cut_id: CutId
    run_id: RunId
    project_id: str
    prepared: PreparedRelease
    output_realization_id: str
    reports: tuple[Mapping[str, Any], ...]
    candidates: tuple[ClaimCandidate, ...]
    batch: PublicationBatch
    entity_metadata: Mapping[str, Mapping[str, Any]]
    source_links: Mapping[str, tuple[int, int, int, int] | NativeEvidenceLink]
    source_binding: SnapshotBinding
    record_reports: tuple[Mapping[str, Any], ...] = ()
    record_policy_bindings: tuple[Mapping[str, Any], ...] = ()


@dataclass(frozen=True)
class PolicyDecision:
    selected: frozenset[str]
    assessments: tuple[AssessmentRow, ...]
    alternative_group: tuple[AlternativeGroupRow, ...] = ()
    alternative_member: tuple[AlternativeMemberRow, ...] = ()
    scientific_representative: tuple[ScientificRepresentativeRow, ...] = ()
    record_admission: tuple[RecordAdmissionRow, ...] = ()


class DomainPolicy(Protocol):
    release_id: str
    version: str

    def evaluate(
        self, inputs: CutInput, scope: AnalysisScope, fused: pa.Table
    ) -> PolicyDecision: ...


@dataclass(frozen=True)
class DomainResult:
    run_id: RunId
    cut_id: CutId
    realization_id: str
    receipt: PublicationReceipt
    reports: int
    occurrences: int
    data_revision: int
    derivation_receipts: tuple[PublicationReceipt, ...] = ()


def _source_batch_id(release_id, output, observations):
    return (
        "cut:"
        + sha256(
            canonical_bytes(
                [
                    release_id,
                    output,
                    [(row["observation_key"], row["payload"]) for row in observations],
                    VERSION,
                ]
            )
        ).hexdigest()
    )


def _completed_result(engine, cut_id: CutId, output, policy):
    """Read an immutable completed result without reinterpreting a changed live input."""
    with (
        engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn,
        conn.begin(),
    ):
        conn.exec_driver_sql("SET TRANSACTION READ ONLY")
        cuts, runs = table("ops.input_cut"), table("ops.run")
        cut = conn.execute(select(cuts).where(cuts.c.id == cut_id)).mappings().one()
        job = conn.execute(select(runs).where(runs.c.id == cut["run_id"])).mappings().one()
        if job["status"] != "finished":
            return None
        if not cut["final"] or not job["sealed"] or job["result_realization_id"] != output:
            raise DomainOperationRefused("finished run is bound to another final cut or output")
        if policy is not None and (
            policy.release_id != cut["release_id"] or policy.version != VERSION
        ):
            raise DomainOperationRefused(
                "finished result policy version differs from its recorded binding"
            )
        observations = cut_observations(conn, cut_id)
        batch_id = _source_batch_id(cut["release_id"], output, observations)
        batches = table("data.batch")
        receipts = (
            conn.execute(
                select(batches)
                .where(
                    batches.c.release_id == cut["release_id"], batches.c.realization_id == output
                )
                .order_by(batches.c.data_revision)
            )
            .mappings()
            .all()
        )
        source = next((row for row in receipts if row["batch_id"] == batch_id), None)
        if source is None:
            raise OperationConflict("finished result has no matching immutable source receipt")
        revision = conn.execute(
            select(table("data.realization").c.data_revision).where(
                table("data.realization").c.realization_id == output,
                table("data.realization").c.release_id == cut["release_id"],
            )
        ).scalar_one()
        count = conn.execute(
            select(func.count())
            .select_from(table("data.occurrence"))
            .where(
                table("data.occurrence").c.realization_id == output,
                table("data.occurrence").c.release_id == cut["release_id"],
            )
        ).scalar_one()
        receipt = PublicationReceipt(
            source["batch_id"], source["data_revision"], source["content_digest"]
        )
        proofs = tuple(
            PublicationReceipt(row["batch_id"], row["data_revision"], row["content_digest"])
            for row in receipts
            if row["batch_id"] != batch_id
        )
        return DomainResult(
            RunId(job["id"]), cut_id, output, receipt, len(observations), count, revision, proofs
        )


def _plain(value):
    from pydantic import BaseModel

    if isinstance(value, BaseModel):
        return {k: _plain(v) for k, v in value if k in value.model_fields_set}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    return value


def _native(value):
    """Keep generated Python collection shapes while reconstructing typed records."""
    from pydantic import BaseModel

    if isinstance(value, BaseModel):
        return {k: _native(v) for k, v in value if k in value.model_fields_set}
    if isinstance(value, tuple):
        return tuple(_native(v) for v in value)
    if isinstance(value, list):
        return [_native(v) for v in value]
    if isinstance(value, dict):
        return {k: _native(v) for k, v in value.items()}
    return value


def _reference(prepared, range_name, value, entities, claims=None):
    """Rewrite through compiled positions, retaining this consumer's equal-collision policy."""
    from .reference_positions import ReferencePositionError, rewrite_references

    if value is None or range_name not in {d.name for d in prepared.definitions}:
        return value
    try:
        return rewrite_references(
            prepared, range_name, value, classes=entities, facts=claims, collision="equal"
        )
    except ReferencePositionError as exc:
        raise DomainOperationRefused(str(exc)) from exc


def _entity_references(prepared, range_name, value):
    from .reference_positions import collect_references

    if value is None or range_name not in {d.name for d in prepared.definitions}:
        return set()
    return {
        ref.target for ref in collect_references(prepared, range_name, value) if ref.kind == "class"
    }


def _claim_references(prepared, range_name, value):
    from .reference_positions import collect_references

    if value is None or range_name not in {d.name for d in prepared.definitions}:
        return set()
    return {
        ref.target for ref in collect_references(prepared, range_name, value) if ref.kind == "fact"
    }


def _source_fact_id(prepared, output, item):
    definition = next(d for d in prepared.definitions if d.name == item.class_name)
    prop = next(p for p in definition.properties if p.name == item.property_name)
    obj = _plain(
        prepared.property_adapter(
            item.class_name, item.property_name, item=prop.multivalued
        ).validate_python(item.object, strict=True)
    )
    qualification = _plain(prepared.validate_python(item.qualification_class, item.qualification))
    return prepared.fact_identity(
        output,
        item.subject,
        prop.iri,
        obj,
        qualification,
        qualification_class=item.qualification_class,
    )


def _property_value(prepared, definition, prop, value, mapping, claims=None):
    from .proposals import _property_value as scalar_projection
    from .publication import native_constraints

    value = _native(value)
    by_name = {d.name: d for d in prepared.definitions}
    if prop.range in by_name:
        if not prop.inlined:
            from .reference_positions import ReferencePositionError, class_reference_value

            try:
                target = class_reference_value(prepared, value)
            except ReferencePositionError as exc:
                raise DomainOperationRefused(str(exc)) from exc
            return mapping.get(target, target)
        return _reference(prepared, prop.range, value, mapping, claims)
    native_range = native_constraints(prepared)[definition.iri, prop.iri]["native_range"]
    if prop.range in {v.enum for v in prepared.vocabularies}:
        native_range = "string"
    projected = scalar_projection(value, native_range)
    if prop.reference_role == "fact" and claims is not None:
        if projected not in claims:
            raise DomainOperationRefused("unavailable source claim reference")
        return claims[projected]
    return projected


def _known_input(conn, prepared, job, observations):
    """Read selected input metadata once under the same exact revision as the sealed cut."""
    from dataclasses import fields

    from .publication import STAGE_TYPES
    from .query import ReadSession

    realization = table("data.realization")
    m = table("data.membership")
    revision = conn.execute(
        select(realization.c.data_revision).where(
            realization.c.realization_id == job["input_realization_id"],
            realization.c.release_id == job["release_id"],
        )
    ).scalar_one()
    if revision != job["input_revision"]:
        raise DomainOperationRefused("input realization revision differs from bound operation")
    memberships = (
        conn.execute(
            select(m).where(
                m.c.release_id == job["release_id"],
                m.c.realization_id == job["input_realization_id"],
                m.c.entity_id.is_not(None),
            )
        )
        .mappings()
        .all()
    )
    ids = {row["entity_id"] for row in memberships}
    membership_ids = select(m.c.entity_id).where(
        m.c.release_id == job["release_id"],
        m.c.realization_id == job["input_realization_id"],
        m.c.entity_id.is_not(None),
    )
    if not ids:
        return {}, {}
    f, s = table("data.fact"), table("data.selection")
    from sqlalchemy import exists

    roles = table("sem.operation_property_role")
    role_membership = m.alias("role_membership")
    eligible = exists(
        select(1)
        .select_from(
            role_membership.join(
                roles,
                (roles.c.release_id == role_membership.c.release_id)
                & (roles.c.class_id == role_membership.c.class_id),
            )
        )
        .where(
            role_membership.c.release_id == f.c.release_id,
            role_membership.c.realization_id == f.c.realization_id,
            role_membership.c.entity_id == f.c.subject_id,
            roles.c.property_id == f.c.property_id,
            roles.c.role.in_(("identity", "required", "display")),
        )
    )
    facts = (
        conn.execute(
            select(f)
            .join(
                s,
                (s.c.release_id == f.c.release_id)
                & (s.c.realization_id == f.c.realization_id)
                & (s.c.fact_id == f.c.fact_id),
            )
            .where(
                f.c.release_id == job["release_id"],
                f.c.realization_id == job["input_realization_id"],
                f.c.subject_id.in_(membership_ids),
                eligible,
            )
        )
        .mappings()
        .all()
    )
    session = ReadSession(
        conn,
        SnapshotBinding(
            job["release_id"], job["input_realization_id"], revision, "input:" + str(job["id"])
        ),
        prepared,
    )
    values, nodes, _ = session.load_values(
        {
            value
            for row in facts
            for value in (row["object_value_id"], row["qualification_value_id"])
            if value is not None
        },
        ids,
    )
    node_by_id = {node.value_id: node for node in nodes}
    from collections import defaultdict

    facts_by_entity = defaultdict(list)
    for fact in facts:
        facts_by_entity[fact["subject_id"]].append(fact)
    definitions = {d.iri: d for d in prepared.definitions}
    metadata: dict[str, dict[str, Any]] = {}
    for row in memberships:
        d = definitions[row["class_id"]]
        item = metadata.setdefault(
            row["entity_id"],
            {
                "id": row["entity_id"],
                "class_iris": [],
                "known": True,
                "fields": {},
                "attributes": [],
                "input_facts": [],
            },
        )
        item["class_iris"].append(d.iri)
    for identity, item in metadata.items():
        item["class_iris"] = tuple(sorted(set(item["class_iris"])))
        d = min(
            (definitions[iri] for iri in item["class_iris"]),
            key=lambda d: (-len(d.ancestors), d.iri),
        )
        item["class_iri"] = d.iri
        properties = {p.iri: p for iri in item["class_iris"] for p in definitions[iri].properties}
        for fact in facts_by_entity[identity]:
            prop = properties.get(fact["property_id"])
            if prop is None:
                continue
            value = values[fact["object_value_id"]]
            item["input_facts"].append(
                (
                    fact,
                    prop,
                    value,
                    values[fact["qualification_value_id"]],
                    definitions[node_by_id[fact["qualification_value_id"]].datatype].name,
                )
            )
            item["fields"][prop.name] = value
            if isinstance(value, str):
                item["attributes"].append(
                    {
                        "predicate": prop.iri,
                        "value": {"kind": "entity", "target": value}
                        if prop.range in {d.name for d in prepared.definitions} and not prop.inlined
                        else {"kind": "text", "text": value},
                    }
                )
                if (
                    any(
                        "display" in prepared.index.property_roles.get((iri, prop.iri), frozenset())
                        for iri in item["class_iris"]
                    )
                    and not prop.multivalued
                ):
                    item["label"] = value
    copied = {}
    support = table("data.membership_support")
    support_selection = select(support).where(
        support.c.release_id == job["release_id"],
        support.c.realization_id == job["input_realization_id"],
        support.c.entity_id.in_(membership_ids),
    )
    supports = conn.execute(support_selection).mappings().all()
    excluded = table("data.identity_exclusion")
    exclusion_selection = select(excluded).where(
        excluded.c.release_id == job["release_id"],
        excluded.c.realization_id == job["input_realization_id"],
        excluded.c.left_entity_id.in_(membership_ids),
        excluded.c.right_entity_id.in_(membership_ids),
    )
    exclusion_rows = conn.execute(exclusion_selection).mappings().all()
    retained_exclusions = exclusion_selection.subquery("input_exclusions")
    links = table("data.identity_exclusion_evidence")
    link_selection = select(links).where(
        links.c.release_id == job["release_id"],
        links.c.realization_id == job["input_realization_id"],
        links.c.exclusion_id.in_(select(retained_exclusions.c.exclusion_id)),
    )
    exclusion_links = conn.execute(link_selection).mappings().all()
    required_evidence = select(support_selection.subquery().c.evidence_id).union(
        select(link_selection.subquery().c.evidence_id)
    )
    for name, rows in (
        ("identity_exclusion", exclusion_rows),
        ("identity_exclusion_evidence", exclusion_links),
    ):
        row_type = STAGE_TYPES[name][0]
        copied[name] = tuple(
            row_type(**{f.name: row[f.name] for f in fields(row_type)}) for row in rows
        )
    observations_table = table("kb.observation")
    copied["_identity_exclusion_sources"] = tuple(
        conn.execute(
            select(observations_table.c.id, observations_table.c.observation_key).where(
                observations_table.c.id.in_(select(retained_exclusions.c.observation_id))
            )
        ).all()
    )
    for name, rows in [("membership", memberships), ("membership_support", supports)]:
        row_type = STAGE_TYPES[name][0]
        copied[name] = tuple(
            row_type(**{f.name: row[f.name] for f in fields(row_type)}) for row in rows
        )
    for name in ("evidence", "evidence_source"):
        target = table("data." + name)
        row_type = STAGE_TYPES[name][0]
        rows = conn.execute(
            select(target).where(
                target.c.release_id == job["release_id"],
                target.c.realization_id == job["input_realization_id"],
                target.c.evidence_id.in_(required_evidence),
            )
        ).mappings()
        copied[name] = tuple(
            row_type(**{f.name: row[f.name] for f in fields(row_type)}) for row in rows
        )
    return metadata, copied


def _cut_input(engine: Engine, cut_id: CutId, output: str) -> CutInput:
    with (
        engine.connect().execution_options(
            isolation_level="REPEATABLE READ", postgresql_readonly=True
        ) as conn,
        conn.begin(),
    ):
        cut = (
            conn.execute(
                select(table("ops.input_cut")).where(table("ops.input_cut").c.id == cut_id)
            )
            .mappings()
            .one()
        )
        job = (
            conn.execute(select(table("ops.run")).where(table("ops.run").c.id == cut["run_id"]))
            .mappings()
            .one()
        )
        if not cut["final"] or not job["sealed"]:
            raise DomainOperationRefused("consolidation requires a sealed final observation cut")
        prepared = open_release(conn, cut["release_id"])
        observations = list({row["id"]: row for row in cut_observations(conn, cut_id)}.values())
        from .source_frames import load_source_frames, packet_bound_source_tasks

        required_origins = packet_bound_source_tasks(job["id"], cut_id=cut_id).subquery()
        source_frames = load_source_frames(
            conn, conn.execute(select(required_origins.c.id).distinct()).scalars()
        )
        descriptors: dict[int, dict[str, Any] | None] = {}
        o, t = table("kb.observation"), table("ops.task")
        config, method = table("ops.method_config"), table("ops.method")
        cut_tasks = table("ops.cut_task")
        source_selection = (
            select(
                o.c.id,
                o.c.source_view_id,
                t.c.unit_key,
                method.c.name.label("provider"),
                method.c.version,
                config.c.params,
            )
            .select_from(
                o.join(t, t.c.id == o.c.task_id)
                .join(config, config.c.id == t.c.method_config_id)
                .join(method, method.c.id == config.c.method_id)
            )
            .where(
                o.c.task_id.in_(
                    select(cut_tasks.c.origin_task_id).where(cut_tasks.c.cut_id == cut_id)
                )
            )
        )
        source_rows = conn.execute(source_selection).mappings().all()
        from .proposals import NativeProposalFrame
        from .source_views import load_source_view

        d = table("kb.document")
        reports_by_id = {row["id"]: row for row in observations}
        views = {}
        source_uris = {}
        for source in source_rows:
            report = reports_by_id[source["id"]]
            frame = source_frames.get(report["task_id"])
            view_id = (
                frame.source_view_id
                if isinstance(frame, NativeProposalFrame)
                else source["source_view_id"]
            )
            if view_id is not None:
                if view_id not in views:
                    views[view_id] = load_source_view(conn, view_id, analysis=False)
                view = views[view_id]
                document_id = view.ref.document_id
                if document_id not in source_uris:
                    source_uris[document_id] = conn.execute(
                        select(d.c.source_uri).where(d.c.id == document_id)
                    ).scalar_one()
                source_uri = source_uris[document_id]
                descriptors[source["id"]] = {
                    "rendition_id": None,
                    "source_view_id": view.ref.id,
                    "source_uri": source_uri,
                    "text": view.text,
                    "provider": source["provider"],
                    "version": source["version"],
                    "rendition_key": view.ref.key,
                    "content": {"macros": {}},
                    "page": source_uri,
                    "math": source["params"].get("math"),
                    "frame": frame,
                }
            else:
                descriptors[source["id"]] = None

        tasks = (
            conn.execute(select(t.c.id, t.c.status, t.c.unit_key).where(t.c.run_id == job["id"]))
            .mappings()
            .all()
        )
        envelopes = (
            conn.execute(
                select(table("ops.task_result"))
                .join(
                    table("ops.cut_task"),
                    table("ops.cut_task").c.origin_task_id == table("ops.task_result").c.task_id,
                )
                .where(table("ops.cut_task").c.cut_id == cut_id)
            )
            .mappings()
            .all()
        )
        # Records belong to sealed task-result envelopes, including completed-empty
        # reports with no kb.observation row. One bound reader owns the whole cut.
        record_reports = ()
        from .record_projection import ARTIFACT as RECORD_PROJECTION

        if (
            any(artifact.kind == RECORD_PROJECTION for artifact in prepared.artifacts)
            or "LocalContributionPublicationPolicy" in prepared.index.definitions
        ):
            from .operations import BoundReader
            from .records import read_private_record_reports

            origin = table("ops.task").alias("record_origin")
            config, method = table("ops.method_config"), table("ops.method")
            view, document = table("kb.source_view"), table("kb.document")
            selected_tasks = (
                conn.execute(
                    select(
                        cut_tasks.c.task_id,
                        cut_tasks.c.origin_task_id,
                        t.c.unit_key,
                        document.c.source_uri,
                        method.c.name.label("provider"),
                        method.c.version.label("operation_version"),
                    )
                    .join(t, t.c.id == cut_tasks.c.task_id)
                    .join(origin, origin.c.id == cut_tasks.c.origin_task_id)
                    .join(config, config.c.id == origin.c.method_config_id)
                    .join(method, method.c.id == config.c.method_id)
                    .outerjoin(
                        view,
                        (origin.c.unit_type == "source_view") & (view.c.id == origin.c.unit_id),
                    )
                    .outerjoin(document, document.c.id == view.c.document_id)
                    .where(
                        cut_tasks.c.cut_id == cut_id, t.c.status.in_(("done", "empty", "reused"))
                    )
                    .order_by(cut_tasks.c.task_id)
                )
                .mappings()
                .all()
            )
            # Primary characterization has its own published private products and
            # task-result envelope, rather than an absent SourceObservationBatch.
            # Read its protected inventory through the existing bounded port; do
            # not manufacture a logical record source for a document-level task.
            if any(
                isinstance(row["body"], dict) and "characterization" in row["body"]
                for row in envelopes
            ):
                from .characterization_store import read_inventory

                primary_tasks = set()
                after = None
                while True:
                    page = read_inventory(conn, job["id"], after=after, limit=1000)
                    primary_tasks.update(row["reference"]["task_id"] for row in page["products"])
                    after = page["continuation"]
                    if after is None:
                        break
                selected_tasks = [
                    row for row in selected_tasks if row["origin_task_id"] not in primary_tasks
                ]
            bound = BoundReader(conn, job["id"], prepared, cut_id, analysis=False)
            private = read_private_record_reports(
                bound, tuple(row["task_id"] for row in selected_tasks)
            )
            from .observations import source_python

            report_bodies = {row["task_id"]: row["body"] for row in envelopes}
            record_reports = tuple(
                dict(
                    selected_task_id=report.selected_task_id,
                    origin_task_id=report.origin_task_id,
                    cut_id=cut_id,
                    source=report.source or selected["unit_key"],
                    outcome=report.outcome or "unknown",
                    records=report.records,
                    source_uri=selected["source_uri"],
                    provider=selected["provider"],
                    operation_version=selected["operation_version"],
                    contributions=report_bodies.get(report.origin_task_id, {}).get("contributions")
                    or (),
                    contribution_operations=report_bodies.get(report.origin_task_id, {}).get(
                        "contribution_operations"
                    )
                    or (),
                    record_policy_events=source_python(
                        report_bodies[report.origin_task_id]["parse_detail"]
                    ).get("record_policy_events", ())
                    if report_bodies.get(report.origin_task_id, {}).get("parse_detail")
                    else (),
                )
                for selected, report in zip(selected_tasks, private, strict=True)
            )
        from .local_semantic_admission import load_semantic_grade_evidence

        job = dict(job, local_semantic_grades=load_semantic_grade_evidence(conn, dict(job), cut_id))
        from .structural_admission import load_structural_grade_evidence

        job = dict(job, structural_grades=load_structural_grade_evidence(conn, dict(job), cut_id))
        known, copied = _known_input(conn, prepared, job, observations)
    return _project_cut(
        prepared,
        job,
        cut,
        observations,
        descriptors,
        tasks,
        envelopes,
        output,
        known,
        copied,
        record_reports=record_reports,
    )


def _entity_mappings(prepared, observations, output, known, contexts):
    """Exact declared identity keys and explicitly global label policy, never fuzzy identity."""
    from corpus_structure.core.vocab import CaseRule

    from .alias_policy import label_normalizer

    by_iri = {d.iri: d for d in prepared.definitions}
    meta = {
        row.name: json.loads(row.body)
        for row in prepared.registry_rows
        if row.kind == "operation_class"
    }
    normalize_label = label_normalizer(prepared)

    mappings = {}
    entries = []
    parsed = {}
    for observation in observations:
        if observation["payload_definition"] != "AgentStoredBatch":
            continue
        payload = prepared.validate_json(
            "AgentStoredBatch", json.dumps(observation["payload"])
        ).model_dump(mode="python", exclude_unset=True)
        parsed[observation["id"]] = payload
        mapping = {
            e["id"]: "entity:"
            + sha256(
                canonical_bytes(
                    [
                        prepared.release_id,
                        output,
                        observation["observation_key"],
                        "entities",
                        i,
                        e["id"],
                    ]
                )
            ).hexdigest()
            for i, e in enumerate(payload.get("entities", ()))
        }
        mappings[observation["id"]] = mapping
        if observation["id"] in contexts:
            for e in payload.get("entities", ()):
                entries.append((observation, e, by_iri[e["class_iri"]]))
    observation_keys = {row["id"]: row["observation_key"] for row in observations}
    original_mappings = {oid: dict(mapping) for oid, mapping in mappings.items()}
    exclusions = []
    for oid, payload in parsed.items():
        if payload.get("identity_exclusions") and prepared.execution_model_id is None:
            raise DomainOperationRefused("identity exclusions require semantic-2")
        for exclusion in payload.get("identity_exclusions", ()):
            if _eligible_exclusion(exclusion):

                def endpoint(value, oid=oid):
                    return (
                        ("known", value["target"])
                        if value["kind"] == "known"
                        else (observation_keys[oid], value["target"])
                    )

                exclusions.append(
                    (oid, exclusion, endpoint(exclusion["left"]), endpoint(exclusion["right"]))
                )
    soft_groups = {}
    soft_ids = {}

    def label_key(definition, label):
        case = (
            CaseRule.FOLD
            if meta[definition.name].get("cs:case") == "casefold"
            else CaseRule.PRESERVE
        )
        return (definition.iri, normalize_label(label, definition.iri, case))

    for observation, entity, definition in entries:
        groups = [g for g in definition.identity_groups if g != definition.identity_slots]
        if (
            not groups
            and meta.get(definition.name, {}).get("cs:scope") == "global"
            and entity.get("label")
        ):
            node = (observation["observation_key"], entity["id"])
            soft_groups.setdefault(label_key(definition, entity["label"]), set()).add(node)
            soft_ids[node] = original_mappings[observation["id"]][entity["id"]]
    for identity, item in known.items():
        for iri in item["class_iris"]:
            definition = by_iri[iri]
            if (
                not [g for g in definition.identity_groups if g != definition.identity_slots]
                and meta.get(definition.name, {}).get("cs:scope") == "global"
                and item.get("label")
            ):
                node = ("known", identity)
                soft_groups.setdefault(label_key(definition, item["label"]), set()).add(node)
                soft_ids[node] = identity
    soft_resolved = {}
    from .identity_resolution import constrained_label_groups

    for (iri, label), members in soft_groups.items():
        anchors = {node for node in members if node[0] == "known"}
        forbidden = [
            (left, right)
            for _, _, left, right in exclusions
            if left in members and right in members
        ]
        if not forbidden and len(anchors) <= 1:
            canonical = (
                soft_ids[next(iter(anchors))]
                if anchors
                else "entity:"
                + sha256(
                    canonical_bytes([prepared.release_id, output, iri, "label", label])
                ).hexdigest()
            )
            soft_resolved.update((node, canonical) for node in members)
            continue
        # Ambiguous reference labels do not choose one existing identity by incidental order.
        partitions = (
            constrained_label_groups(members, forbidden, anchors)
            if len(anchors) <= 1
            else tuple(frozenset((node,)) for node in sorted(members))
        )
        for group in partitions:
            anchored = group & anchors
            canonical = (
                soft_ids[next(iter(anchored))]
                if anchored
                else min(soft_ids[node] for node in group)
            )
            soft_resolved.update((node, canonical) for node in group)
    resolved = set()
    decisions: dict[
        tuple[int, str],
        tuple[str, str, tuple[str, ...], list[tuple[str, ...]], list[tuple[int, str]]],
    ] = {}
    keys = {}
    known_labels = {}
    for identity, item in known.items():
        for iri in item["class_iris"]:
            definition = by_iri[iri]
            groups = [g for g in definition.identity_groups if g != definition.identity_slots]
            if not groups:
                if meta.get(definition.name, {}).get("cs:scope") == "global" and item.get("label"):
                    case = (
                        CaseRule.FOLD
                        if meta[definition.name].get("cs:case") == "casefold"
                        else CaseRule.PRESERVE
                    )
                    label = normalize_label(item["label"], iri, case)
                    match = (iri, label)
                    known_labels.setdefault(match, identity)
                continue
            if not all(all(name in item["fields"] for name in g) for g in groups):
                continue
            for key in prepared.entity_keys(
                definition.name, output, item["fields"], include_identifier=False
            ):
                if key in keys and keys[key] != identity:
                    raise DomainOperationRefused("input contains incompatible declared entity keys")
                keys[key] = identity
    pending = list(entries)
    progress = False
    while pending:
        progress = False
        remaining = []
        for observation, e, definition in pending:
            oid = observation["id"]
            mapping = mappings[oid]
            fields = {p.name: p for p in definition.properties}
            attrs = {}
            dependencies = []
            for attribute in e.get("attributes", ()):
                prop = next(p for p in definition.properties if p.iri == attribute["predicate"])
                from .expression_context import bind_expression_context

                value = bind_expression_context(attribute["value"], contexts[oid][0])
                if (
                    prop.name
                    in {
                        name
                        for g in definition.identity_groups
                        if g != definition.identity_slots
                        for name in g
                    }
                    and value.get("kind") == "entity"
                    and value.get("target") in mapping
                ):
                    dependencies.append((oid, value["target"]))
                attrs[prop.name] = _property_value(prepared, definition, prop, value, mapping)
            if e.get("scope") is not None and "scope_locator" in fields:
                attrs.setdefault("scope_locator", e["scope"]["locator"])
            groups = [g for g in definition.identity_groups if g != definition.identity_slots]
            basis = (
                "declared_key"
                if groups
                else "global_label"
                if meta.get(definition.name, {}).get("cs:scope") == "global"
                else "source_local"
            )
            outcome = "resolved"
            relevant = ()
            if groups and all(all(name in attrs for name in g) for g in groups):
                if any(dep not in resolved for dep in dependencies):
                    decisions[oid, e["id"]] = (basis, "ungrounded_cycle", (), groups, dependencies)
                    remaining.append((observation, e, definition))
                    continue
                candidates = prepared.entity_keys(
                    definition.name, output, attrs, include_identifier=False
                )
                matches = {keys[key] for key in candidates if key in keys}
                if len(matches) > 1:
                    raise DomainOperationRefused(
                        "declared keys bridge incompatible existing identity assignments"
                    )
                relevant = tuple(sorted(matches or set(candidates)))
                canonical = next(iter(matches)) if matches else min(candidates)
                for key in candidates:
                    keys[key] = canonical
                mapping[e["id"]] = canonical
            elif (
                not groups
                and meta.get(definition.name, {}).get("cs:scope") == "global"
                and e.get("label")
            ):
                mapping[e["id"]] = soft_resolved[(observation_keys[oid], e["id"])]
                members = soft_groups[label_key(definition, e["label"])]
                relevant = tuple(sorted(soft_ids[node] for node in members if node[0] == "known"))
                if len(relevant) > 1:
                    outcome = "ambiguous_anchor"
            elif groups or basis == "global_label":
                outcome = "incomplete_key"
            decisions[oid, e["id"]] = (basis, outcome, relevant, groups, dependencies)
            # An absent/incomplete semantic key never licenses a label merge for a keyed class.
            resolved.add((oid, e["id"]))
            progress = True
        if not progress:
            # Recursive, ungrounded identity declarations retain source-qualified references.
            break
        pending = remaining
    for oid, exclusion, _left, _right in exclusions:

        def mapped(endpoint, oid=oid):
            if endpoint["kind"] == "known":
                if endpoint["target"] not in known:
                    raise DomainOperationRefused("identity exclusion has an unbound known endpoint")
                return endpoint["target"]
            if endpoint["target"] not in mappings[oid]:
                raise DomainOperationRefused("identity exclusion has an undeclared local endpoint")
            return mappings[oid][endpoint["target"]]

        left, right = mapped(exclusion["left"]), mapped(exclusion["right"])
        if left == right:
            raise IdentityResolutionConflict(
                prepared.release_id, exclusion["id"], exclusion["left"], exclusion["right"], left
            )
    for observation, entity, definition in pending if not progress else ():
        oid, local = observation["id"], entity["id"]
        groups = [g for g in definition.identity_groups if g != definition.identity_slots]
        decisions.setdefault((oid, local), ("declared_key", "ungrounded_cycle", (), groups, []))
    entry_definitions = {
        (observation["id"], entity["id"]): definition for observation, entity, definition in entries
    }
    rows = tuple(
        EntityResolutionRow(
            oid,
            local,
            mappings[oid][local],
            basis,
            outcome,
            canonical_bytes(relevant).decode(),
            canonical_bytes(
                {
                    "groups": groups,
                    "class": definition.iri,
                    "property_cases": {
                        prop.name: prop.case_policy
                        for prop in definition.properties
                        if any(prop.name in group for group in groups)
                    },
                    "label_scope": meta.get(definition.name, {}).get("cs:scope", "local"),
                    "label_case": meta.get(definition.name, {}).get("cs:case", "preserve"),
                }
            ).decode(),
            canonical_bytes(dependencies).decode(),
            "declared_identity" if outcome == "resolved" else outcome,
            "resolve_identity",
            VERSION,
        )
        for (oid, local), (basis, outcome, relevant, groups, dependencies) in sorted(
            decisions.items()
        )
        for definition in (entry_definitions[oid, local],)
    )
    return mappings, parsed, rows


def _project_cut(
    prepared,
    job,
    cut,
    observations,
    descriptors,
    tasks,
    envelopes,
    output,
    known,
    copied,
    *,
    record_reports=(),
):
    definitions = {d.iri: d for d in prepared.definitions}
    by_name = {d.name: d for d in prepared.definitions}
    reports = []
    items = []
    claims = []
    metadata = dict(known)
    coverage = []
    source_links = {}
    evidence_roles = {}
    contents = {}
    from corpus_structure.core.evidence import MacroDef
    from corpus_structure.core.tex import effective_macros
    from corpus_structure.methods.math.methods import MathSection

    contexts = {}
    for observation in observations:
        descriptor = descriptors[observation["id"]]
        if observation["payload_definition"] != "AgentStoredBatch" or descriptor is None:
            continue
        section = MathSection.model_validate(descriptor["math"] or {})
        source_macros = {
            name: MacroDef.model_validate(value)
            for name, value in descriptor["content"].get("macros", {}).items()
        }
        contexts[observation["id"]] = (
            effective_macros(source_macros, section.macro_table()),
            tuple(sorted(set(section.constants))),
        )
    if len({constants for _, constants in contexts.values()}) > 1:
        raise DomainOperationRefused("cut has incompatible recorded mathematical constant profiles")
    entity_mappings, parsed, resolution_decisions = _entity_mappings(
        prepared, observations, output, known, contexts
    )

    def coverage_row(
        family, scope, outcome, reason=None, source_outcome=None, required_capability=None
    ):
        key = (
            "coverage:"
            + sha256(
                canonical_bytes(
                    [cut["id"], family, scope, outcome, reason, source_outcome, required_capability]
                )
            ).hexdigest()
        )
        coverage.append(
            CoverageRow(key, family, scope, outcome, reason, source_outcome, required_capability)
        )

    for task in tasks:
        if task["status"] not in {"done", "empty", "reused"}:
            coverage_row(
                "task",
                task["unit_key"] or str(task["id"]),
                "failed" if task["status"] == "failed" else "unanalysed",
                str(task["status"]),
            )
    from .outcomes import PreparedCoverageLowerer

    coverage_lowerer = PreparedCoverageLowerer.from_release(prepared)
    for envelope in envelopes:
        for c in envelope["body"].get("coverage", ()):
            converted = coverage_lowerer.lower(
                c["outcome"], c.get("reason"), c.get("required_capability")
            )
            coverage_row(
                c["family"],
                c["scope"],
                converted.outcome,
                converted.reason,
                converted.source_outcome,
                converted.required_capability,
            )
    for observation in observations:
        reports.append(dict(observation))
        if (
            observation["payload_definition"] == "SourceObservation"
            and observation["kind"] == "author_markup"
        ):
            from corpus_structure.core.evidence import RenditionContent
            from corpus_structure.semantic.observations import source_python
            from corpus_structure.semantic.source_projection import project_markup

            descriptor = descriptors[observation["id"]]
            if descriptor is None:
                coverage_row(
                    "author_markup",
                    observation["observation_key"],
                    "partial",
                    "source rendition unavailable",
                )
                continue
            payload = source_python(observation["payload"]["payload"])
            # A source envelope retains the canonical markup segment key in its payload value.
            if payload.get("synthesize") is None:
                continue
            segment_key = (payload.get("value") or {}).get("segment")
            if segment_key is None:
                coverage_row(
                    "author_markup",
                    observation["observation_key"],
                    "partial",
                    "markup has no segment locator",
                )
                continue
            if descriptor["rendition_id"] not in contents:
                contents[descriptor["rendition_id"]] = RenditionContent.model_validate(
                    descriptor["content"]
                )
            projected = project_markup(
                prepared,
                output,
                observation_key=observation["observation_key"],
                payload=payload,
                content=contents[descriptor["rendition_id"]],
                page=descriptor["page"],
                source_uri=descriptor["source_uri"],
                rendition_key=descriptor["rendition_key"],
                segment_key=segment_key,
                provider=descriptor["provider"],
                operation_version=descriptor["version"],
            )
            coordinates = {eid: (start, end) for eid, start, end in projected.evidence_ranges}
            items.extend(
                replace(
                    item,
                    evidence=tuple(
                        replace(
                            e,
                            locator="rendition:"
                            + descriptor["rendition_key"]
                            + ":span:"
                            + str(coordinates[e.evidence_id][0])
                            + ":"
                            + str(coordinates[e.evidence_id][1]),
                        )
                        for e in item.evidence
                    ),
                )
                for item in projected.items
            )
            for ordinal, (eid, start, end) in enumerate(projected.evidence_ranges):
                role = payload["synthesize"]["evidence"][ordinal].get("role")
                if role is not None:
                    evidence_roles[eid] = role
                source_links[eid] = _evidence_link(observation, descriptor, start, end, "")
            for locator in projected.unresolved:
                coverage_row("author_markup", locator, "partial", "unresolved source reference")
            continue
        if observation["payload_definition"] != "AgentStoredBatch":
            coverage_row(
                observation["kind"],
                observation["observation_key"],
                "unanalysed",
                "source report retained; no domain assertion projection declared",
            )
            continue
        descriptor = descriptors[observation["id"]]
        payload = parsed[observation["id"]]
        if descriptor is None:
            coverage_row(
                "claim_proposal", payload["unit_ref"], "partial", "source rendition unavailable"
            )
            continue
        source = observation["observation_key"]
        mapping = entity_mappings[observation["id"]]
        statements = {s["id"]: dict(s) for s in payload.get("statements", ())}
        from corpus_structure.core.evidence import RenditionContent
        from corpus_structure.core.locators import LocatorIndex

        from .proposals import statement_anchor
        from .source_projection import statement_identity

        if statements:
            from .proposals import NativeProposalFrame

            source_index = (
                None
                if isinstance(descriptor["frame"], NativeProposalFrame)
                else LocatorIndex(
                    RenditionContent.model_validate(descriptor["content"]), descriptor["page"]
                )
            )
            for statement in statements.values():
                if statement["kind"] != "outside":
                    statement["anchor"] = statement_anchor(
                        statement["anchor"], descriptor["frame"], index=source_index
                    )
                else:
                    coverage_row(
                        "statement",
                        source + "/" + statement["id"],
                        "partial",
                        "explicit unresolved external statement reference",
                    )

        def statement_source_key(anchor, *, descriptor=descriptor):
            from .proposals import NativeProposalFrame, native_statement_source

            frame = descriptor["frame"]
            return (
                native_statement_source(frame, anchor).unit_ref
                if isinstance(frame, NativeProposalFrame)
                else descriptor["rendition_key"]
            )

        statement_ids = {
            ref: statement_identity(
                prepared.release_id,
                output,
                statement_source_key(statement["anchor"]),
                statement["anchor"],
            )
            for ref, statement in statements.items()
            if statement["kind"] != "outside"
        }
        # Source local refs stay distinct until a declared identity operation authorizes a merge.
        # This substrate never treats a fuzzy label or ontology mapping as identity.
        source_attributes = {}
        for e in payload.get("entities", ()):
            entity_id = mapping[e["id"]]
            declared_attributes = list(e.get("attributes", ()))
            definition = definitions[e["class_iri"]]
            source_attributes[e["id"]] = declared_attributes
            present = {
                p.name
                for p in definition.properties
                if any(a["predicate"] == p.iri for a in declared_attributes)
            } | {"id"}
            required = {
                p.name
                for p in definition.properties
                if p.required or (p.minimum_cardinality or 0) > 0
            } | {n for group in definition.identity_groups for n in group}
            complete = required <= present
            if not complete:
                coverage_row(
                    "entity",
                    source + "/" + e["id"],
                    "partial",
                    "declared entity lacks required identifying fields: "
                    + ",".join(sorted(required - present)),
                )
            current = {
                **e,
                "id": entity_id,
                "attributes": declared_attributes,
                "representable": complete,
            }
            prior = metadata.get(entity_id)
            # Rule display projection is deterministic; each source's own attributes
            # below remain distinct and never inherit the last report's values.
            if prior is not None and prior.get("known"):
                continue
            if prior is None or canonical_bytes(current) < canonical_bytes(prior):
                metadata[entity_id] = current
        from corpus_structure.core.evidence import MacroDef

        from .expression_context import bind_expression_context

        macros, constants = contexts[observation["id"]]
        claim_rows = []
        claim_refs = {}
        source_claims = {c["id"]: (i, c) for i, c in enumerate(payload.get("claims", ()))}
        occurrence_refs = {
            ref: occurrence_key(prepared.release_id, output, source, claim_source_item(i))
            for ref, (i, c) in source_claims.items()
        }
        qclass = next(
            p.range for p in by_name["AgentClaim"].properties if p.name == "qualification"
        )
        qualification_class = qclass

        def dependencies_of(claim, qclass, mapping):
            refs = _claim_references(prepared, "Value", claim["object"]) | _claim_references(
                prepared, qclass, claim["qualification"]
            )
            subject = mapping.get(claim["subject"], claim["subject"])
            if subject in metadata:
                definition = definitions[metadata[subject]["class_iri"]]
                prop = next((p for p in definition.properties if p.iri == claim["predicate"]), None)
                if prop is not None and prop.reference_role == "fact":
                    refs.add(claim["object"]["text"])
            return refs

        dependencies = {
            ref: dependencies_of(claim, qclass, mapping)
            for ref, (i, claim) in source_claims.items()
        }
        from graphlib import CycleError, TopologicalSorter

        topology = TopologicalSorter(
            {ref: refs & source_claims.keys() for ref, refs in dependencies.items()}
        )
        with suppress(CycleError):
            topology.prepare()
        ordered = []
        while ready := topology.get_ready():
            ordered.extend(sorted(ready))
            topology.done(*ready)
        for ref in source_claims.keys() - set(ordered):
            coverage_row("claim", source + "/" + ref, "partial", "cyclic source claim reference")
        for ref in ordered:
            i, claim = source_claims[ref]
            if not dependencies[ref] <= claim_refs.keys():
                coverage_row(
                    "claim", source + "/" + ref, "partial", "unavailable source claim premise"
                )
                continue
            located = []
            for j, e in enumerate(claim["evidence"]):
                if e.get("outcome") != "located" or e.get("start") is None or e.get("end") is None:
                    continue
                start, end = e["start"], e["end"]
                if not 0 <= start < end <= len(_evidence_source_text(descriptor, e["locator"])):
                    raise DomainOperationRefused("claim evidence lies outside its cited source")
                # Location uncertainty is source evidence, never silently upgraded to exactness.
                key = "evidence:" + sha256(canonical_bytes([source, "claims", i, j, e])).hexdigest()
                locator = canonical_bytes(
                    {"locator": e["locator"], "start": start, "end": end, "role": e["role"]}
                ).decode()
                located.append(
                    EvidenceRow(
                        key,
                        descriptor["source_uri"],
                        locator,
                        descriptor["provider"],
                        descriptor["version"],
                    )
                )
                source_links[key] = _evidence_link(
                    observation, descriptor, start, end, e["locator"]
                )
                evidence_roles[key] = e["role"]
            if not located or not any(
                e.get("outcome") == "located" and e["role"] == "primary" for e in claim["evidence"]
            ):
                coverage_row(
                    "claim", source + "/" + claim["id"], "partial", "no located primary evidence"
                )
                continue
            subject = mapping.get(claim["subject"], claim["subject"])
            if subject not in metadata or metadata[subject].get("representable") is False:
                coverage_row(
                    "claim",
                    source + "/" + claim["id"],
                    "partial",
                    "bound reference membership projection unavailable",
                )
                continue
            definition = definitions[metadata[subject]["class_iri"]]
            prop = next(p for p in definition.properties if p.iri == claim["predicate"])
            obj = _property_value(
                prepared,
                definition,
                prop,
                bind_expression_context(claim["object"], macros),
                {**mapping, **statement_ids},
                claim_refs,
            )
            qclass = next(d.name for d in prepared.definitions if d.name == "AgentClaim")
            qualification_class = next(
                p.range for p in by_name[qclass].properties if p.name == "qualification"
            )
            qual = _reference(
                prepared,
                qualification_class,
                bind_expression_context(_plain(claim["qualification"]), macros),
                {**mapping, **statement_ids},
                claim_refs,
            )
            if not isinstance(qual, dict):
                raise DomainOperationRefused("qualification must be an explicit typed record")
            referenced = (
                {obj}
                if prop.range in by_name and not prop.inlined
                else _entity_references(prepared, prop.range, obj)
            ) | _entity_references(prepared, qualification_class, qual)
            if any(
                ref not in metadata or metadata[ref].get("representable") is False
                for ref in referenced
            ):
                coverage_row(
                    "claim",
                    source + "/" + claim["id"],
                    "partial",
                    "declared endpoint lacks representable class identity",
                )
                continue
            item = SourceItem(
                subject,
                definition.name,
                prop.name,
                obj,
                qual,
                source,
                claim_source_item(i),
                claim["establishment"],
                tuple(located),
                qualification_class,
            )
            claim_refs[claim["id"]] = _source_fact_id(prepared, output, item)
            items.append(item)
            claim_rows.append((claim, item))
        # Each source attribute is an independent assertion. Neither entity labels nor
        # assigned identifiers inherit another claim's evidence or qualification.
        for local, e in ((e["id"], e) for e in payload.get("entities", ())):
            subject = mapping[local]
            definition = definitions[e["class_iri"]]
            if metadata[subject].get("representable") is False:
                continue
            for index, attribute in enumerate(source_attributes[local]):
                prop = next(p for p in definition.properties if p.iri == attribute["predicate"])
                located = []
                for ordinal, citation in enumerate(attribute["evidence"]):
                    if citation.get("outcome") != "located":
                        continue
                    start, end = citation["start"], citation["end"]
                    if (
                        not 0
                        <= start
                        < end
                        <= len(_evidence_source_text(descriptor, citation["locator"]))
                    ):
                        raise DomainOperationRefused(
                            "attribute evidence lies outside its cited source"
                        )
                    eid = (
                        "evidence:"
                        + sha256(
                            canonical_bytes(
                                [source, "entities", local, "attributes", index, ordinal, citation]
                            )
                        ).hexdigest()
                    )
                    located.append(
                        EvidenceRow(
                            eid,
                            descriptor["source_uri"],
                            canonical_bytes(
                                {
                                    "locator": citation["locator"],
                                    "start": start,
                                    "end": end,
                                    "role": citation["role"],
                                }
                            ).decode(),
                            descriptor["provider"],
                            descriptor["version"],
                        )
                    )
                    evidence_roles[eid] = citation["role"]
                    source_links[eid] = _evidence_link(
                        observation, descriptor, start, end, citation["locator"]
                    )
                if not located:
                    coverage_row(
                        "attribute",
                        f"{source}/entities/{local}/attributes/{index}",
                        "partial",
                        "attribute lacks located support",
                    )
                    continue
                value = _property_value(
                    prepared,
                    definition,
                    prop,
                    bind_expression_context(attribute["value"], macros),
                    {**mapping, **statement_ids},
                    claim_refs,
                )
                qualification = _reference(
                    prepared,
                    qualification_class,
                    bind_expression_context(_plain(attribute["qualification"]), macros),
                    {**mapping, **statement_ids},
                    claim_refs,
                )
                if not isinstance(qualification, dict):
                    raise DomainOperationRefused("attribute qualification requires a typed record")
                items.append(
                    SourceItem(
                        subject,
                        definition.name,
                        prop.name,
                        value,
                        qualification,
                        source,
                        f"entities/{local}/attributes/{index}",
                        attribute["establishment"],
                        tuple(located),
                        qualification_class,
                    )
                )
        for claim, item in claim_rows:
            statement = statements.get(claim.get("statement"))
            if statement is not None and statement["kind"] != "outside":
                sid = statement_ids[claim["statement"]]
                props = {"locator": statement["anchor"]}
                from .statement_types import statement_definition, statement_kinds

                statement_type = statement_definition(prepared)
                if statement["kind"] in statement_kinds(prepared):
                    props["statement_kind"] = statement["kind"]
                elif statement["kind"] != "outside":
                    raise DomainOperationRefused(
                        "statement kind differs from its declared source-statement range"
                    )
                for name, value in props.items():
                    items.append(
                        replace(
                            item,
                            subject=sid,
                            class_name=statement_type.name,
                            property_name=name,
                            object=value,
                            item="statements/" + claim["statement"] + "/" + name,
                            qualification={"modality": "asserted", "polarity": True},
                            qualification_class="Qualification",
                        )
                    )
            fid = _source_fact_id(prepared, output, item)
            prop = next(
                p for p in by_name[item.class_name].properties if p.name == item.property_name
            )
            alternatives = tuple(
                a["id"] for a in payload.get("alternatives", ()) if claim["id"] in a["members"]
            )
            statement = statements.get(claim.get("statement"))
            definition = by_name[item.class_name]
            rule_object = _reference(
                prepared,
                "Value",
                bind_expression_context(claim["object"], macros),
                {**mapping, **statement_ids},
                occurrence_refs,
            )
            rule_qualification = _reference(
                prepared,
                qualification_class,
                bind_expression_context(_plain(claim["qualification"]), macros),
                {**mapping, **statement_ids},
                occurrence_refs,
            )
            claims.append(
                ClaimCandidate(
                    fid,
                    occurrence_key(prepared.release_id, output, source, item.item),
                    source,
                    claim["id"],
                    item.subject,
                    item.class_name,
                    claim["predicate"],
                    item.object,
                    item.qualification,
                    item.establishment,
                    statement_ids.get(claim.get("statement")),
                    statement.get("kind") if statement else None,
                    claim.get("statement_role"),
                    alternatives,
                    len(item.evidence),
                    {name: value.model_dump(mode="python") for name, value in macros.items()},
                    qualification_class,
                    tuple(
                        sorted(
                            ref
                            for ref in {
                                item.subject,
                                *_entity_references(
                                    prepared, qualification_class, item.qualification
                                ),
                                *(
                                    _entity_references(prepared, prop.range, item.object)
                                    if prop.inlined
                                    else {item.object}
                                    if prop.range in by_name
                                    else set()
                                ),
                            }
                            if ref in metadata
                            and metadata[ref].get("reference")
                            and not metadata[ref].get("known")
                        )
                    ),
                    rule_object,
                    rule_qualification,
                    constants,
                )
            )
        for unsupported in payload.get("unsupported", ()):
            coverage_row(
                "unsupported", source + "/" + unsupported["id"], "partial", unsupported["reason"]
            )
    batch_id = _source_batch_id(prepared.release_id, output, observations)
    batch = assemble(prepared, output, batch_id, tuple(items))
    from .publication import (
        EntityRow,
        IdentityExclusionEvidenceRow,
        IdentityExclusionRow,
    )

    exclusion_rows = []
    exclusion_links = []
    exclusion_evidence = []
    exclusion_entities = set()
    for observation in observations:
        payload = parsed.get(observation["id"], {})
        descriptor = descriptors[observation["id"]]
        for exclusion in payload.get("identity_exclusions", ()):
            source = observation["observation_key"]
            if descriptor is None or not _eligible_exclusion(exclusion):
                coverage_row(
                    "identity_exclusion",
                    source + "/" + exclusion["id"],
                    "partial",
                    "no located primary identity evidence",
                )
                continue
            mapping = entity_mappings[observation["id"]]

            def endpoint(value, mapping=mapping):
                return mapping[value["target"]] if value["kind"] == "local" else value["target"]

            left, right = endpoint(exclusion["left"]), endpoint(exclusion["right"])
            if any(identity not in metadata for identity in (left, right)):
                raise DomainOperationRefused(
                    "identity exclusion endpoint lacks representable required identity: "
                    + exclusion["id"]
                )
            xid = (
                "identity-exclusion:"
                + sha256(
                    canonical_bytes([prepared.release_id, output, source, exclusion["id"]])
                ).hexdigest()
            )
            exclusion_rows.append(
                IdentityExclusionRow(
                    exclusion_id=xid,
                    observation_id=observation["id"],
                    local_id=exclusion["id"],
                    left_kind=exclusion["left"]["kind"],
                    left_ref=exclusion["left"]["target"],
                    right_kind=exclusion["right"]["kind"],
                    right_ref=exclusion["right"]["target"],
                    left_entity_id=left,
                    right_entity_id=right,
                    reason=exclusion["reason"],
                    operation_id="resolve_identity",
                    operation_version=VERSION,
                )
            )
            for ordinal, citation in enumerate(exclusion["evidence"]):
                if citation.get("outcome") != "located":
                    continue
                start, end = citation["start"], citation["end"]
                if (
                    not 0
                    <= start
                    < end
                    <= len(_evidence_source_text(descriptor, citation["locator"]))
                ):
                    raise DomainOperationRefused("identity evidence lies outside its cited source")
                eid = (
                    "evidence:"
                    + sha256(
                        canonical_bytes(
                            [source, "identity_exclusions", exclusion["id"], ordinal, citation]
                        )
                    ).hexdigest()
                )
                exclusion_evidence.append(
                    EvidenceRow(
                        eid,
                        descriptor["source_uri"],
                        canonical_bytes(
                            {
                                "locator": citation["locator"],
                                "start": start,
                                "end": end,
                                "role": citation["role"],
                            }
                        ).decode(),
                        descriptor["provider"],
                        descriptor["version"],
                    )
                )
                evidence_roles[eid] = citation["role"]
                source_links[eid] = _evidence_link(
                    observation, descriptor, start, end, citation["locator"]
                )
                exclusion_links.append(IdentityExclusionEvidenceRow(xid, eid))
                for identity in (left, right):
                    exclusion_entities.add(EntityRow(identity))

    def rows_union(old, new):
        from dataclasses import astuple

        return tuple(sorted(set((*old, *new)), key=lambda row: canonical_bytes(astuple(row))))

    batch = replace(
        batch,
        entity=rows_union(batch.entity, exclusion_entities),
        evidence=rows_union(batch.evidence, exclusion_evidence),
        identity_exclusion=tuple(exclusion_rows),
        identity_exclusion_evidence=tuple(exclusion_links),
    )
    from .publication import EntityInputRow, FactInputRow

    used = {e.entity_id for e in batch.entity} & known.keys()
    pending = set(used)
    while pending:
        identity = pending.pop()
        for _original, prop, value, qualification, qclass in known[identity]["input_facts"]:
            refs = (
                {value}
                if prop.range in by_name and not prop.inlined
                else _entity_references(prepared, prop.range, value)
            ) | _entity_references(prepared, qclass, qualification)
            for ref in refs & known.keys() - used:
                used.add(ref)
                pending.add(ref)
    # Carry admitted input metadata as facts with explicit native lineage, never as
    # new source occurrences or as assertions attributed to the current report.
    input_items = []
    input_fact_links = []
    for identity in sorted(used):
        d = definitions[known[identity]["class_iri"]]
        for original, prop, value, qualification, qclass in known[identity]["input_facts"]:
            input_items.append(FactItem(identity, d.name, prop.name, value, qualification, qclass))
            fid = prepared.fact_identity(
                output, identity, prop.iri, value, qualification, qualification_class=qclass
            )
            input_fact_links.append(
                FactInputRow(
                    fid,
                    job["input_realization_id"],
                    job["input_revision"],
                    original["fact_id"],
                    job["id"],
                )
            )
    input_lowerer = FactValueLowerer(prepared, output)
    for item in input_items:
        input_lowerer.add(item)
    inherited = input_lowerer.graph("input-metadata")
    incoming: dict[str, Any] = {}
    for name in ("entity", "typed_value", "value_role", "fact"):
        merged = (*getattr(batch, name), *getattr(inherited, name))
        if name == "fact":
            by_fact = {}
            for fact in merged:
                if fact.fact_id not in by_fact or (
                    fact.object_value_id,
                    fact.qualification_value_id,
                ) < (
                    by_fact[fact.fact_id].object_value_id,
                    by_fact[fact.fact_id].qualification_value_id,
                ):
                    by_fact[fact.fact_id] = fact
            incoming[name] = tuple(sorted(by_fact.values(), key=lambda f: f.fact_id))
        else:
            incoming[name] = tuple(
                sorted(
                    set(merged),
                    key=lambda row: canonical_bytes(__import__("dataclasses").astuple(row)),
                )
            )
    source_keys = dict(copied.pop("_identity_exclusion_sources", ()))
    inherited_ids = {}
    inherited_exclusions = []
    for row in copied.pop("identity_exclusion", ()):
        if row.left_entity_id in used and row.right_entity_id in used:
            xid = (
                "identity-exclusion:"
                + sha256(
                    canonical_bytes(
                        [prepared.release_id, output, source_keys[row.observation_id], row.local_id]
                    )
                ).hexdigest()
            )
            inherited_ids[row.exclusion_id] = xid
            inherited_exclusions.append(replace(row, exclusion_id=xid))
    inherited_links = [
        replace(row, exclusion_id=inherited_ids[row.exclusion_id])
        for row in copied.pop("identity_exclusion_evidence", ())
        if row.exclusion_id in inherited_ids
    ]
    batch = replace(
        batch,
        identity_exclusion=rows_union(batch.identity_exclusion, inherited_exclusions),
        identity_exclusion_evidence=rows_union(batch.identity_exclusion_evidence, inherited_links),
    )
    imported_evidence = {
        row.evidence_id for row in copied.get("membership_support", ()) if row.entity_id in used
    } | {
        row.evidence_id
        for rows in (
            batch.membership_support,
            batch.occurrence_evidence,
            batch.identity_exclusion_evidence,
        )
        for row in rows
    }
    for name, rows in copied.items():
        if name in {"evidence", "evidence_source"}:
            rows = tuple(row for row in rows if row.evidence_id in imported_evidence)
        if name.startswith("membership"):
            rows = tuple(row for row in rows if row.entity_id in used)
        incoming[name] = tuple(
            sorted(
                set(
                    (
                        *(
                            row
                            for row in getattr(batch, name)
                            if name != "membership"
                            or (row.entity_id, row.class_id)
                            not in {(r.entity_id, r.class_id) for r in rows}
                        ),
                        *rows,
                    )
                ),
                key=lambda row: canonical_bytes(__import__("dataclasses").astuple(row)),
            )
        )
    batch = replace(
        batch,
        **incoming,
        fact_input=tuple(sorted(set(input_fact_links), key=lambda row: row.fact_id)),
        entity_input=tuple(
            EntityInputRow(
                identity, job["input_realization_id"], job["input_revision"], identity, job["id"]
            )
            for identity in sorted(used)
        ),
        coverage=tuple(sorted(coverage, key=lambda c: c.coverage_id)),
    )
    # Source links are resolved to native spans only in the final short publication transaction.
    from .publication import OccurrenceContextRow, OccurrenceEvidenceRoleRow

    batch = replace(
        batch,
        occurrence_context=tuple(
            OccurrenceContextRow(c.occurrence_id, c.statement, c.statement_role)
            for c in claims
            if c.statement is not None or c.statement_role is not None
        ),
        occurrence_evidence_role=tuple(
            OccurrenceEvidenceRoleRow(
                link.occurrence_id, link.evidence_id, evidence_roles[link.evidence_id]
            )
            for link in batch.occurrence_evidence
            if link.evidence_id in evidence_roles
        ),
    )
    from .publication import EntitySourceRow

    decided = {(row.observation_id, row.local_id) for row in resolution_decisions}
    existing_memberships = {(row.entity_id, row.class_id) for row in batch.membership}
    batch = replace(
        batch,
        entity=rows_union(
            batch.entity,
            {
                EntityRow(identity)
                for mapping in entity_mappings.values()
                for identity in mapping.values()
            },
        ),
        # A released entity declaration supplies class membership even when the node
        # is only an endpoint or isolate. It does not invent a source property assertion:
        # exact declaration/resolution lineage below is its separate native support basis.
        membership=rows_union(
            batch.membership,
            {
                MembershipRow(mapping[e["id"]], e["class_iri"], "agent_asserted")
                for observation in observations
                if observation["payload_definition"] == "AgentStoredBatch"
                for mapping in (entity_mappings[observation["id"]],)
                for e in parsed[observation["id"]].get("entities", ())
                if (observation["id"], e["id"]) in decided
                and metadata[mapping[e["id"]]].get("representable") is not False
                and (mapping[e["id"]], e["class_iri"]) not in existing_memberships
            },
        ),
        entity_resolution=resolution_decisions,
        entity_source=tuple(
            sorted(
                {
                    EntitySourceRow(mapping[e["id"]], observation["id"], e["id"])
                    for observation in observations
                    if observation["payload_definition"] == "AgentStoredBatch"
                    for mapping in (entity_mappings[observation["id"]],)
                    for e in parsed[observation["id"]].get("entities", ())
                    if (observation["id"], e["id"]) in decided
                },
                key=lambda row: (row.entity_id, row.observation_id, row.local_id),
            )
        ),
    )
    source_links = {
        eid: link
        for eid, link in source_links.items()
        if eid in {e.evidence_id for e in batch.evidence}
    }
    # Assembly was extended with cut-specific selections, provenance and coverage.
    # Bind once to those final rows before exposing the input to transport consumers.
    if record_reports and any(
        artifact.kind == "record_projection.json" for artifact in prepared.artifacts
    ):
        from .record_assertions import lower_record_assertions
        from .record_projection import (
            RecordAssertionRow,
            RecordAssertionSupportRow,
            project_record_reports,
        )

        projection = project_record_reports(prepared, record_reports)
        lowered = lower_record_assertions(prepared, output, batch.batch_id, record_reports)
        additions: dict[str, Any] = {}
        for field in fields(PublicationBatch):
            left, right = getattr(batch, field.name), getattr(lowered.batch, field.name)
            if isinstance(left, tuple) and isinstance(right, tuple):
                additions[field.name] = tuple(dict.fromkeys((*left, *right)))
        batch = replace(batch, **additions)
        projection["record_assertion"] = tuple(
            RecordAssertionRow(**asdict(row)) for row in lowered.assertions
        )
        projection["record_assertion_support"] = tuple(
            RecordAssertionSupportRow(**asdict(row)) for row in lowered.support
        )
        batch = replace(batch, **projection)
    from .local_admission import project_local_assertions
    from .local_semantic_admission import project_semantic_assertions
    from .structural_admission import project_structural_assertions

    batch = replace(
        batch,
        structural_assertion=project_structural_assertions(
            prepared, job.get("structural_grades", ())
        ),
        local_assertion=project_local_assertions(prepared, record_reports),
        local_semantic_assertion=project_semantic_assertions(
            prepared, job.get("local_semantic_grades", ())
        ),
    )
    batch = batch.bind_preparation(prepared)
    return CutInput(
        CutId(cut["id"]),
        RunId(job["id"]),
        job["project_id"],
        prepared,
        output,
        tuple(reports),
        tuple(claims),
        batch,
        MappingProxyType(
            {
                key: value
                for key, value in metadata.items()
                if key in used or key in {row.entity_id for row in batch.entity}
            }
        ),
        MappingProxyType(source_links),
        SnapshotBinding(
            job["release_id"],
            job["input_realization_id"],
            job["input_revision"],
            "cut:" + str(cut["id"]),
        ),
        tuple(record_reports),
        tuple(json.loads(job["dependencies"]).get("record_acceptance", ()))
        if job.get("dependencies")
        else (),
    )


def consolidate_cut(
    engine: Engine,
    cut_id: CutId,
    output_realization_id: str,
    *,
    analytics: AnalyticsSettings | None = None,
    policy: DomainPolicy | None = None,
    attempts: int = 3,
) -> DomainResult:
    completed = _completed_result(engine, cut_id, output_realization_id, policy)
    if completed is not None:
        return completed
    inputs = _cut_input(engine, cut_id, output_realization_id)
    admitted = ReleasedRulesPolicy(inputs.prepared)
    if policy is None:
        policy = admitted
    if policy.version != admitted.version:
        raise DomainOperationRefused("scientific policy version differs from admitted operation")
    if policy.release_id != inputs.prepared.release_id:
        raise DomainOperationRefused("scientific policy belongs to another release")
    binding = inputs.source_binding
    compiled = compile_projection(inputs.prepared, binding, kind="candidate")
    packet = CandidateInput.from_admitted_cut(
        inputs.prepared, inputs, decision_universe=policy.version
    )
    resources = AnalyticsSettings() if analytics is None else analytics
    with AnalysisScope(
        packet,
        threads=resources.threads,
        memory_limit=resources.memory_limit,
        scratch_path=resources.scratch_path,
    ) as scope:
        fused = scope.fuse(scope.relation("candidate_input")).to_arrow_table()
        decision = policy.evaluate(inputs, scope, fused)
    facts = {f.fact_id for f in inputs.batch.fact}
    if not decision.selected.issubset(facts):
        raise DomainOperationRefused("policy selected facts outside its input universe")
    from .record_admission import cap_record_selections

    selected, record_admission = cap_record_selections(
        inputs.batch, decision.selected, decision.record_admission
    )
    batch = replace(
        inputs.batch,
        record_admission=record_admission,
        selection=tuple(SelectionRow(f) for f in sorted(selected)),
        assessment=decision.assessments,
        alternative_group=decision.alternative_group,
        alternative_member=decision.alternative_member,
        scientific_representative=tuple(
            row
            for row in decision.scientific_representative
            if row.fact_id in selected and row.representative_fact_id in selected
        ),
    )
    source_links = inputs.source_links

    def publish(conn, batch):
        from ._operation_calls import begin_evaluation, end_stage, finish_evaluation
        from ._operation_ids import CutId, RealizationId

        begin_evaluation(
            conn, cut_id=CutId(cut_id), output_realization_id=RealizationId(output_realization_id)
        )
        done = (
            conn.execute(
                select(table("ops.run").c.status).where(table("ops.run").c.id == inputs.run_id)
            ).scalar_one()
            == "finished"
        )
        from .arrow_publication import SnapshotDerivedPublication, publish_arrow_on_connection

        receipt = publish_arrow_on_connection(conn, batch)
        if done:
            return receipt
        # A source receipt, proof receipts and the run result are one atomic transaction. The
        # source receipt remains its own identity even when inference advances the final revision.
        from .inference import derive

        end_stage(conn)
        inferred = derive(
            conn,
            SnapshotBinding(
                batch.release_id, batch.realization_id, receipt.data_revision, "cut:" + str(cut_id)
            ),
        )
        if inferred.batch.fact or inferred.batch.derivation:
            publish_arrow_on_connection(
                conn,
                SnapshotDerivedPublication.from_rows(
                    inferred.batch,
                    source=inferred.binding,
                    operation_id="publish_inference",
                    projection_id="accepted",
                ),
            )
        finish_evaluation(
            conn,
            cut_id=CutId(cut_id),
            output_realization_id=RealizationId(output_realization_id),
            batch_id=batch.batch_id,
        )
        return receipt

    if source_links:
        rows = []
        for eid, link in sorted(source_links.items()):
            if not isinstance(link, NativeEvidenceLink):
                raise DomainOperationRefused(
                    "publication requires current SourceView evidence custody"
                )
            rows.append(
                EvidenceSourceRow(
                    eid,
                    link.observation_id,
                    None,
                    None,
                    source_view_id=link.source_view_id,
                    native_address=link.native_address,
                )
            )
        batch = replace(
            batch,
            evidence_source=tuple(
                sorted(set((*batch.evidence_source, *rows)), key=lambda row: row.evidence_id)
            ),
        )
    batch = batch.bind_preparation(inputs.prepared)
    from .arrow_publication import SnapshotDerivedPublication

    publication = SnapshotDerivedPublication.from_rows(
        batch,
        source=inputs.source_binding,
        operation_id="evaluate",
        projection_id=compiled.projection_id,
        contract_id="candidate",
        cut_id=cut_id,
        profile_digest=compiled.profile.digest,
    )
    receipt = _publish(engine, publication, publish, attempts=attempts)
    with engine.connect() as conn:
        revision = conn.execute(
            select(table("data.realization").c.data_revision).where(
                table("data.realization").c.realization_id == output_realization_id
            )
        ).scalar_one()
        receipts = (
            conn.execute(
                select(table("data.batch"))
                .where(
                    table("data.batch").c.realization_id == output_realization_id,
                    table("data.batch").c.release_id == batch.release_id,
                    table("data.batch").c.batch_id != batch.batch_id,
                )
                .order_by(table("data.batch").c.data_revision)
            )
            .mappings()
            .all()
        )
        proofs = tuple(
            PublicationReceipt(row["batch_id"], row["data_revision"], row["content_digest"])
            for row in receipts
        )
    return DomainResult(
        inputs.run_id,
        cut_id,
        output_realization_id,
        receipt,
        len(inputs.reports),
        len(batch.occurrence),
        revision,
        proofs,
    )


def _bindings(value):
    if isinstance(value, dict):
        found = [value["bindings"]] if "bindings" in value else []
        return [*found, *(b for k, v in value.items() if k != "bindings" for b in _bindings(v))]
    if isinstance(value, (list, tuple)):
        return [b for member in value for b in _bindings(member)]
    return []


def _without_bindings(value):
    if isinstance(value, dict):
        return {k: _without_bindings(v) for k, v in value.items() if k != "bindings"}
    if isinstance(value, (list, tuple)):
        return [_without_bindings(v) for v in value]
    return value


class ReleasedRulesPolicy:
    """The existing rule language and finalize decision table over release-derived views."""

    version = VERSION

    def __init__(self, prepared: PreparedRelease):
        from corpus_structure.schema.rulelang import BUILTIN, Builtin, Vocabulary

        from .rule_views import build_rule_language

        self.prepared = prepared
        self.release_id = prepared.release_id
        artifact = next((a for a in prepared.artifacts if a.kind == RULE_INPUT), None)
        if artifact is None:
            raise DomainOperationRefused("release has no declared domain rules operation")
        self.source = _policy_yaml(artifact.content) or {}
        if not isinstance(self.source, dict):
            raise DomainOperationRefused("domain rule artifact is not an object")
        self.definitions = {d.name: d for d in prepared.definitions}
        self.metadata = {}
        for row in prepared.registry_rows:
            if row.kind == "operation_property":
                body = json.loads(row.body)
                self.metadata[body["class"], body["property"]] = body
        from .comparison_projection import comparison_projection

        self.comparison_projection = comparison_projection(prepared)
        self.prefixes = {
            row.name: json.loads(row.body)["uri"]
            for row in prepared.registry_rows
            if row.kind == "prefix"
        }
        self.validate_source()
        self.version = self.source["operation"]["version"]
        if prepared.execution_model_id is not None:
            from .contracts import bound_execution_model

            execution = bound_execution_model(prepared)
            for name in ("resolve_identity", "evaluate", "scientific_policy"):
                operation = execution.require_operation(name)
                if operation.policy_version != self.version:
                    raise DomainOperationRefused(
                        f"{name}: policy version differs from the archived domain implementation"
                    )
        self.enums = {}
        for row in prepared.registry_rows:
            if row.kind == "enum_definition":
                body = json.loads(row.body)
                enum_uri = body.get("enum_uri")
                if enum_uri:
                    self.enums[self.compact(prepared.expand_name(enum_uri))] = tuple(
                        prepared.enum_members(row.name)
                    )
        # Classes, qualifier schemas and memberships come from the same immutable binding.
        from .statement_types import effective_bindings

        qualification = effective_bindings(prepared)["qualification"]
        qprops = (
            {p.name: p for p in self.definitions[qualification].properties} if qualification else {}
        )
        self.qprops = qprops
        builtins = {
            "enums": Builtin(self.enums, "map[list[string]]"),
            "is_a": Builtin(self.is_a, "function(string, string)->boolean"),
        }
        for name, values in self.source.get("tables", {}).items():
            if all(isinstance(v, list) for v in values.values()):
                typ = "map[list[string]]"
            elif all(isinstance(v, str) for v in values.values()):
                typ = "map[string]"
            else:
                raise DomainOperationRefused("unsupported released rule lookup table")
            builtins[name] = Builtin(values, typ)
        classes = frozenset(self.compact(d.iri) for d in prepared.definitions)
        predicates = frozenset(
            self.compact(p.iri) for d in prepared.definitions for p in d.properties
        )
        groups = frozenset(g for row in self.metadata.values() for g in row.get("groups", ()))
        values = {
            ("Claim", "predicate"): Vocabulary("predicates", predicates),
            ("Claim", "groups"): Vocabulary("predicate subsets", groups),
            ("Entity", "type"): Vocabulary("entity classes", classes),
            ("Claim", "establishment"): Vocabulary(
                "Establishment", frozenset(prepared.enum_members("Establishment"))
            ),
        }
        from .statement_types import statement_kinds as bound_statement_kinds

        statement_kinds = Vocabulary("StatementKind", bound_statement_kinds(prepared))
        statement_roles = Vocabulary(
            "StatementRole", frozenset(prepared.enum_members("StatementRole"))
        )
        values[("Claim", "statement_kind")] = statement_kinds
        values[("Statement", "kind")] = statement_kinds
        values[("Claim", "statement_role")] = statement_roles
        values[("Value", "t")] = Vocabulary(
            "Value discriminators",
            frozenset(
                p.equals_string
                for d in prepared.definitions
                if d.name == "Value" or "Value" in d.ancestors
                for p in d.properties
                if p.name == "kind" and p.equals_string
            ),
        )
        values[("Binding", "bind")] = Vocabulary(
            "ExpressionBinding kinds",
            frozenset(
                p.equals_string
                for d in prepared.definitions
                if d.name == "ExpressionBinding" or "ExpressionBinding" in d.ancestors
                for p in d.properties
                if p.name == "kind" and p.equals_string
            ),
        )
        keys = {
            (BUILTIN, name): Vocabulary("keys of $" + name, frozenset(builtin.value))
            for name, builtin in builtins.items()
            if isinstance(builtin.value, Mapping)
        }
        keys[("Entity", "identity")] = Vocabulary(
            "identity slots",
            frozenset(
                self.compact(prop.iri)
                for definition in prepared.definitions
                if definition.name == "Entity" or "Entity" in definition.ancestors
                for group in definition.identity_groups
                for prop in definition.properties
                if prop.name in group
            ),
        )
        for prop in qprops.values():
            if prop.range in {
                row.name for row in prepared.registry_rows if row.kind == "enum_definition"
            }:
                values["Qualifiers", prop.name] = Vocabulary(
                    prop.range, frozenset(prepared.enum_members(prop.range))
                )
        self.language = build_rule_language(
            prepared,
            qprops=qprops,
            builtins=builtins,
            values=values,
            keys=keys,
            arguments={"is_a": (Vocabulary("classes", classes), Vocabulary("classes", classes))},
            views=self.source.get("views", {}),
        )
        self.rules = []
        seen = set()
        for section in ("rules", "guideline"):
            for raw in self.source.get(section, ()):
                rid = raw["id"]
                if rid in seen:
                    raise DomainOperationRefused("duplicate released rule id")
                seen.add(rid)
                if "finalize" not in raw.get("at", ("batch", "finalize")):
                    continue
                self.rules.append(
                    (
                        raw,
                        self.language.compile(rid, raw.get("when", "true")),
                        self.language.compile(rid, raw["check"]),
                    )
                )

    def validate_source(self):
        from .alias_policy import label_normalizer
        from .analytical_kernels import ALTERNATIVE_OF, SAME_SLOT, ViewSpec

        source = self.source
        if set(source) - {
            "rules",
            "guideline",
            "views",
            "tables",
            "derive",
            "identity",
            "operation",
            "rule_view_abi",
        }:
            raise DomainOperationRefused("unknown domain operation policy section")
        from .rule_views import RULE_VIEW_ABI

        if source.get("rule_view_abi") != RULE_VIEW_ABI:
            raise SemanticOperationRefusal(
                SemanticReason(
                    "incompatible_bindings",
                    "evaluate",
                    self.prepared.release_id,
                    expected=RULE_VIEW_ABI,
                    actual=source.get("rule_view_abi"),
                )
            )
        if source.get("operation") != {"name": "semantic-domain", "version": VERSION}:
            raise DomainOperationRefused("unsupported domain operation name/version")
        if source.get("derive"):
            raise DomainOperationRefused(
                "operation derive rules require an admitted inference profile"
            )
        identity = source.get("identity", {})
        if not isinstance(identity, dict) or set(identity) - {
            "aliases",
            "alias_profile",
            "alias_contexts",
        }:
            raise DomainOperationRefused("invalid operation identity policy")
        label_normalizer(self.prepared)
        props = {p.iri for d in self.prepared.definitions for p in d.properties}
        groups = {g for body in self.metadata.values() for g in body.get("groups", ())}

        def applies(value):
            values = [value] if isinstance(value, str) else value
            if (
                not isinstance(values, (tuple, list))
                or not values
                or any(not isinstance(v, str) for v in values)
            ):
                raise DomainOperationRefused("invalid rule applies_to")
            selected = set()
            for token in values:
                if token == "any":
                    selected.update(props)
                elif token.startswith("subset:"):
                    group = token[7:]
                    if group not in groups:
                        raise DomainOperationRefused("unknown operation predicate subset " + group)
                    selected.update(
                        body["property"]
                        for body in self.metadata.values()
                        if group in body.get("groups", ())
                    )
                else:
                    iri = self.prepared.expand_name(token)
                    if iri not in props:
                        raise DomainOperationRefused("unknown operation predicate " + token)
                    selected.add(iri)
            return selected

        for section in ("rules", "guideline"):
            if not isinstance(source.get(section, []), list):
                raise DomainOperationRefused("operation rules must be a list")
            for rule in source.get(section, ()):
                if not isinstance(rule, dict) or set(rule) - {
                    "id",
                    "applies_to",
                    "at",
                    "severity",
                    "when",
                    "check",
                    "description",
                }:
                    raise DomainOperationRefused("invalid operation rule shape")
                if (
                    not isinstance(rule.get("id"), str)
                    or not rule["id"]
                    or not isinstance(rule.get("check"), str)
                ):
                    raise DomainOperationRefused("operation rule requires id and check")
                sites = rule.get("at", ("batch", "finalize"))
                if (
                    not isinstance(sites, (list, tuple))
                    or not sites
                    or any(s not in {"batch", "finalize"} for s in sites)
                ):
                    raise DomainOperationRefused("unknown operation rule call site")
                if rule.get("severity", "error") not in {"error", "warning"}:
                    raise DomainOperationRefused("unknown operation rule severity")
                applies(rule.get("applies_to", "any"))
        tables = source.get("tables", {})
        if not isinstance(tables, dict) or any(
            not isinstance(key, str)
            or not isinstance(value, dict)
            or any(not isinstance(k, str) for k in value)
            or not (
                all(isinstance(v, str) for v in value.values())
                or all(
                    isinstance(v, list) and all(isinstance(x, str) for x in v)
                    for v in value.values()
                )
            )
            for key, value in tables.items()
        ):
            raise DomainOperationRefused("invalid released rule lookup table")
        views = source.get("views", {})
        if not isinstance(views, dict):
            raise DomainOperationRefused("operation views must be a mapping")
        for name, decl in views.items():
            if (
                not isinstance(name, str)
                or not name.isidentifier()
                or name in {SAME_SLOT, ALTERNATIVE_OF}
                or not isinstance(decl, dict)
                or set(decl) - {"description", "applies_to", "source", "match", "project"}
            ):
                raise DomainOperationRefused("invalid operation view declaration")
            if not {"applies_to", "source", "match", "project"} <= decl.keys():
                raise DomainOperationRefused("incomplete operation view declaration")
            match = decl["match"]
            if (
                not isinstance(match, dict)
                or set(match) != {"source", "claim"}
                or any(v not in {"subject", "object"} for v in match.values())
            ):
                raise DomainOperationRefused("unknown operation view match side")
            if (
                not isinstance(decl["source"], str)
                or self.prepared.expand_name(decl["source"]) not in props
            ):
                raise DomainOperationRefused("unknown operation view source property")
            spec = ViewSpec.from_declaration(name, decl, applies(decl["applies_to"]))
            if spec.attr == "identity" and (
                spec.slot is None or self.prepared.expand_name(spec.slot) not in props
            ):
                raise DomainOperationRefused("unknown operation view identity projection")

    def compact(self, iri):
        choices = [
            (len(uri), prefix + ":" + iri[len(uri) :])
            for prefix, uri in self.prefixes.items()
            if iri.startswith(uri)
        ]
        return max(choices)[1] if choices else iri

    def is_a(self, child, parent):
        expanded = self.prepared.expand_name(child)
        target = self.prepared.expand_name(parent)
        definition = next((d for d in self.prepared.definitions if d.iri == expanded), None)
        ancestor = next((d.name for d in self.prepared.definitions if d.iri == target), None)
        return definition is not None and (expanded == target or ancestor in definition.ancestors)

    def applies(self, raw, candidate):
        source = raw.get("applies_to", "any")
        if isinstance(source, str):
            source = [source]
        groups = self.metadata.get((candidate.class_name, candidate.predicate), {}).get(
            "groups", ()
        )
        for token in source:
            if token == "any":
                return True
            if token.startswith("subset:"):
                if token[7:] in groups:
                    return True
            elif self.prepared.expand_name(token) == candidate.predicate:
                return True
        return False

    def scientific_decisions(self, inputs, scope):
        """Declared source disagreements and existing scientific value comparisons.

        Equivalence is an assessment between retained facts. It never rewrites fact meaning
        or turns an undecided comparison into inequality.
        """
        from collections import defaultdict

        from corpus_structure.core.evidence import MacroDef

        from .identity import _meaning
        from .operation_results import validate_result_dimension
        from .scientific_evidence import EvidenceTier as Tier
        from .scientific_evidence import (
            ScientificInterpretationUnavailable,
            SemanticComparator,
            grammar_name,
        )

        groups = defaultdict(list)
        rows = []
        by_group = defaultdict(list)
        assessments = []
        comparators = {}
        generated = defaultdict(set)
        unresolved = set()
        equivalent_components = []
        for c in inputs.candidates:
            qual, identity, compared = self.comparison_projection.partition(
                c.class_name, c.predicate, c.qualification_class, c.qualification
            )
            meta = self.metadata.get((c.class_name, c.predicate), {})
            # Scope, modality, conditions and time stay exact context boundaries.
            key = sha256(
                canonical_bytes(
                    _meaning(
                        [c.subject, c.predicate, c.statement, _without_bindings(c.object), identity]
                    )
                )
            ).hexdigest()
            meaning = canonical_bytes(
                _meaning(
                    {
                        "qualifiers": compared,
                        "bindings": _bindings([c.object, c.qualification]),
                    }
                )
            ).decode()
            rows.append({"key": key, "meaning": meaning})
            by_group[key].append(c)
            prop = next(
                p for p in self.definitions[c.class_name].properties if p.iri == c.predicate
            )
            if (
                prop.constraint_scope == "accepted_value"
                and meta.get("cs:role") == "predicate"
                and (not prop.multivalued or str(meta.get("cs:functional", "")).lower() == "true")
            ):
                slot = canonical_bytes(_meaning([c.subject, c.predicate, qual]))
                groups[slot].append(c)
        relation = pa.Table.from_pylist(
            rows, schema=pa.schema([pa.field("key", pa.string()), pa.field("meaning", pa.string())])
        )
        split = {
            row["key"]
            for row in scope.operation_disagreements(scope.connection.from_arrow(relation))
            .to_arrow_table()
            .to_pylist()
        }
        for key in split:
            members = by_group[key]
            if len({c.fact_id for c in members}) > 1:
                for c in members:
                    generated[c.occurrence_id].add("disagreement:" + key)

        context_by_occurrence = {
            o.occurrence_id: o.report_qualification_value_id for o in inputs.batch.occurrence
        }

        def assessment(a, b, outcome, reason, tier, evidence=None, semantic_reason=None):
            from .scientific_evidence import scientific_assessment_reason

            validate_result_dimension(self.prepared, "scientific_policy", "comparison", outcome)
            for c, other in ((a, b), (b, a)):
                detail = canonical_bytes(
                    {
                        "other_fact_id": other.fact_id,
                        "other_occurrence_id": other.occurrence_id,
                        "tier": tier,
                        "policy": "scientific-evidence-1/consolidation",
                        "evidence_profile": "consolidation-evidence-1",
                        "detail": reason,
                    }
                ).decode()
                aid = (
                    "assessment:"
                    + sha256(
                        canonical_bytes(
                            [
                                VERSION,
                                "value_equivalence",
                                c.occurrence_id,
                                semantic_reason_identity(semantic_reason)
                                if semantic_reason is not None
                                else detail,
                                other.occurrence_id,
                                outcome,
                            ]
                        )
                    ).hexdigest()
                )
                assessments.append(
                    AssessmentRow(
                        aid,
                        "scientific.value_equivalence",
                        VERSION,
                        outcome,
                        occurrence_id=c.occurrence_id,
                        reason=scientific_assessment_reason(
                            evidence,
                            detail=reason or f"{tier} comparison: {outcome}",
                            semantic_reason=semantic_reason,
                            context={
                                "left": a.object,
                                "right": b.object,
                                "qualification": a.qualification,
                                "macros": a.macros,
                                "constants": sorted(a.constants),
                                "right_macros": b.macros,
                                "right_constants": sorted(b.constants),
                            },
                        ),
                        uncertainty=reason if outcome == "undecided" else None,
                        counterpart_fact_id=other.fact_id,
                        counterpart_occurrence_id=other.occurrence_id,
                        context_value_id=context_by_occurrence[c.occurrence_id],
                        comparison_tier=tier,
                        semantic_reason=semantic_reason,
                    )
                )

        for slot, members in groups.items():
            # Distinct report occurrences of one fact need no scientific comparison.
            distinct = {
                c.fact_id: c for c in sorted(members, key=lambda c: c.occurrence_id, reverse=True)
            }
            ordered = sorted(
                distinct.values(), key=lambda c: (canonical_bytes(_meaning(c.object)), c.fact_id)
            )
            if len(ordered) < 2:
                continue
            parent = {c.fact_id: c.fact_id for c in ordered}

            def root(key, parent):
                while parent[key] != key:
                    key = parent[key]
                return key

            for index, a in enumerate(ordered):
                for b in ordered[index + 1 :]:
                    reason = None
                    reason_code: SemanticReasonCode | None = None
                    comparison = None
                    operative_macros = dict(a.macros)
                    if _bindings(a.object) != _bindings(b.object):
                        reason = "distinct explicit expression bindings"
                        reason_code = "incompatible_bindings"
                    elif set(a.constants) != set(b.constants):
                        reason = "incompatible source constant declarations"
                        reason_code = "incompatible_bindings"
                    elif isinstance(a.object, dict) and isinstance(b.object, dict):
                        left_context = a.object.get("macro_context", {})
                        right_context = b.object.get("macro_context", {})
                        if any(
                            left_context[name] != right_context[name]
                            for name in left_context.keys() & right_context.keys()
                        ):
                            reason = "incompatible referenced source macro definitions"
                            reason_code = "incompatible_bindings"
                        else:
                            for name in right_context:
                                operative_macros[name] = b.macros[name]
                    if reason is None:
                        try:
                            descriptor = next(
                                p
                                for p in self.definitions[a.class_name].properties
                                if p.iri == a.predicate
                            )
                            if descriptor.range in self.definitions and not descriptor.inlined:
                                left, right = (
                                    {"kind": "entity", "target": v} for v in (a.object, b.object)
                                )
                            else:
                                left, right = a.object, b.object
                            macro_key = canonical_bytes(
                                [
                                    operative_macros,
                                    sorted(a.constants),
                                    self.prepared.execution_model_id,
                                ]
                            )
                            if macro_key not in comparators:
                                comparators[macro_key] = SemanticComparator(
                                    {
                                        name: MacroDef.model_validate(value)
                                        for name, value in operative_macros.items()
                                    },
                                    a.constants,
                                    prepared=self.prepared,
                                )
                            comparator = comparators[macro_key]
                            condition = a.qualification.get("condition")
                            conditions = (condition,) if condition is not None else ()
                            if conditions:

                                def expected(node):
                                    if node["kind"] == "all":
                                        return [
                                            part
                                            for child in node["terms"]
                                            for part in expected(child)
                                        ]
                                    return [{"compare": "cmp"}.get(node["kind"], node["kind"])]

                                leaves = expected(conditions[0])
                                variables = tuple(
                                    dict.fromkeys(
                                        grammar_name(key)
                                        for value in (left, right)
                                        for key in _bindings(value)
                                    )
                                )
                                member_constraints, relations = comparator._constraints(
                                    list(conditions), variables
                                )
                                if len(member_constraints) != leaves.count("member") or len(
                                    relations
                                ) != leaves.count("cmp"):
                                    raise DomainOperationRefused(
                                        "mathematical restriction reading is incomplete"
                                    )
                            comparison = comparator.compare(
                                left, right, conditions, ref_eq=lambda x, y: x == y
                            )
                        except (DomainOperationRefused, ScientificInterpretationUnavailable) as exc:
                            reason = str(exc)
                            reason_code = "unsupported_interpretation"
                    if comparison is None:
                        assessment(
                            a,
                            b,
                            "undecided",
                            reason or "no faithful comparison operand",
                            "undecided",
                            semantic_reason=SemanticReason(
                                reason_code or "missing_operands",
                                "scientific_policy",
                                self.prepared.release_id,
                                (a.occurrence_id, b.occurrence_id),
                                detail=reason or "no faithful comparison operand",
                            ),
                        )
                        unresolved.update(c.occurrence_id for c in members)
                        continue
                    if comparison.tier is Tier.UNDECIDED:
                        detail = comparison.detail
                        assessment(
                            a,
                            b,
                            "undecided",
                            detail,
                            "undecided",
                            comparison.evidence,
                            SemanticReason(
                                "unsupported_interpretation",
                                "scientific_policy",
                                self.prepared.release_id,
                                (a.occurrence_id, b.occurrence_id),
                                expected="decisive scientific comparison",
                                actual=comparison.evidence.numeric,
                                detail=detail,
                            ),
                        )
                        unresolved.update(c.occurrence_id for c in members)
                    elif comparison.equal:
                        assessment(
                            a,
                            b,
                            "equivalent",
                            comparison.detail,
                            comparison.tier.value,
                            comparison.evidence,
                        )
                        ra, rb = root(a.fact_id, parent), root(b.fact_id, parent)
                        parent[max(ra, rb)] = min(ra, rb)
                    else:
                        assessment(
                            a,
                            b,
                            "different",
                            comparison.detail,
                            comparison.tier.value,
                            comparison.evidence,
                        )
                        group = "value_disagreement:" + sha256(slot).hexdigest()
                        for c in members:
                            generated[c.occurrence_id].add(group)
            components = defaultdict(list)
            for c in ordered:
                components[root(c.fact_id, parent)].append(c)
            for component in components.values():
                if len(component) > 1:
                    equivalent_components.append(
                        tuple(c.fact_id for c in sorted(component, key=lambda c: c.fact_id))
                    )
        return generated, unresolved, equivalent_components, assessments

    def alternative_products(self, inputs, generated):
        """Canonical proposition groups; source-local labels stay provenance, not identity."""
        from .identity import alternative_group_key

        by_source = {(c.observation_key, c.local_id): c for c in inputs.candidates}
        by_occurrence = {c.occurrence_id: c for c in inputs.candidates}
        products: dict[str, dict[str, Any]] = {}
        incomplete = set()

        def add(facts, cause, kind):
            facts = tuple(sorted(set(facts)))
            if len(facts) < 2:
                return
            key = alternative_group_key(
                inputs.prepared.release_id, inputs.output_realization_id, facts
            )
            product = products.setdefault(key, {"members": facts, "sources": {}, "generated": {}})
            product[kind][canonical_bytes(cause)] = cause

        for report in inputs.reports:
            if report["payload_definition"] != "AgentStoredBatch":
                continue
            source = report["observation_key"]
            for group in report["payload"].get("alternatives", ()):
                materialized = [
                    by_source[source, ref] for ref in group["members"] if (source, ref) in by_source
                ]
                if len(materialized) != len(group["members"]):
                    incomplete.update(c.occurrence_id for c in materialized)
                add(
                    (c.fact_id for c in materialized),
                    {
                        "observation_key": source,
                        "local_id": group["id"],
                        "faithful": group["faithful"],
                        "reason": group["reason"],
                    },
                    "sources",
                )
        members = {}
        for occurrence, keys in generated.items():
            for key in keys:
                members.setdefault(key, set()).add(by_occurrence[occurrence].fact_id)
        for key, facts in members.items():
            add(
                facts,
                {
                    "kind": "qualifier_binding_disagreement"
                    if key.startswith("disagreement:")
                    else "scientific_value_difference",
                    "key": key,
                },
                "generated",
            )
        rows = []
        links = []
        view_members = []
        for key, product in sorted(products.items()):
            reason = canonical_bytes(
                {
                    kind: [value for _, value in sorted(product[kind].items())]
                    for kind in ("sources", "generated")
                }
            ).decode()
            rows.append(AlternativeGroupRow(key, reason, "consolidate.alternatives", VERSION))
            links.extend(AlternativeMemberRow(key, fact) for fact in product["members"])
            view_members.extend(
                {"group": key, "claim": c.occurrence_id}
                for c in inputs.candidates
                if c.fact_id in product["members"]
            )
        return tuple(rows), tuple(links), view_members, incomplete

    def evaluate(self, inputs: CutInput, scope: AnalysisScope, fused: pa.Table) -> PolicyDecision:

        from .rule_views import (
            BindingView,
            EntityView,
            NodeView,
            QualifiersView,
            StatementView,
            binding_symbols,
            project_rule_value,
        )

        errors = set()
        ambiguous = set()
        assessments = []
        views = {}
        readings = {}
        generated, unresolved, equivalent_components, scientific = self.scientific_decisions(
            inputs, scope
        )
        assessments.extend(scientific)
        alternative_groups, alternative_members, group_views, incomplete_alternatives = (
            self.alternative_products(inputs, generated)
        )
        unresolved.update(incomplete_alternatives)
        candidates = inputs.candidates
        candidate_facts = {c.fact_id for c in candidates}
        by_occurrence = {c.occurrence_id: c.fact_id for c in candidates}

        def entity(key):
            meta = inputs.entity_metadata.get(key, {})
            identity = {}
            for attribute in meta.get("attributes", ()):
                value = attribute["value"]
                raw = value.get("text") if value.get("kind") == "text" else value.get("target")
                if isinstance(raw, str):
                    identity[self.compact(attribute["predicate"])] = raw
            return EntityView(
                key,
                key,
                self.compact(meta.get("class_iri", "")),
                meta.get("label") or "",
                identity.get(next((k for k in identity if k.endswith(":symbol")), "")),
                identity,
            )

        def nodes(value):
            if value is None:
                return []
            kind = value["kind"]
            if kind in {"all", "any"}:
                return [
                    NodeView("and" if kind == "all" else "or", None, None, None, None),
                    *(n for term in value["terms"] for n in nodes(term)),
                ]
            if kind == "not":
                return [NodeView("not", None, None, None, None), *nodes(value["term"])]
            if kind == "claim":
                return [NodeView("claim", value["ref"], None, None, None)]
            if kind == "member":
                return [NodeView("member", None, None, None, value["x"]["expression"])]
            if kind == "compare":
                return [NodeView("cmp", None, None, value["relation"], value["lhs"]["expression"])]
            if kind == "forall":
                return [
                    NodeView("forall", None, value["variable"], None, None),
                    *nodes(value["body"]),
                ]
            if kind == "atomic":
                return [NodeView("pred", None, value["predicate"], None, None)]
            if kind == "escape":
                raise SemanticOperationRefusal(
                    SemanticReason(
                        "unsupported_interpretation",
                        "evaluate",
                        self.prepared.release_id,
                        expected="admitted condition projection",
                        actual="escape",
                        detail="source condition remains uninterpreted: " + value["reason"],
                    )
                )
            raise SemanticOperationRefusal(
                SemanticReason(
                    "unsupported_interpretation",
                    "evaluate",
                    self.prepared.release_id,
                    expected="admitted condition projection",
                    actual=kind,
                    detail="condition structure has no admitted rule projection",
                )
            )

        gives = {}
        for candidate in candidates:
            props = self.metadata.get((candidate.class_name, candidate.predicate), {})
            param_map = props.get("cs:param_map")
            entries = candidate.qualification.get(param_map, ()) if param_map else ()
            symbols = frozenset()
            if param_map and self.prepared.member_has_behavior(
                "StatementRole", candidate.statement_role, "supplies_binding_symbol"
            ):
                binding = self.prepared.index.properties[self.qprops[param_map].range, "value"]
                members = entries.values() if isinstance(entries, dict) else entries
                symbols = binding_symbols(
                    self.prepared, binding, (entry.get("value", entry) for entry in members)
                )
            gives[candidate.occurrence_id] = symbols
        context_index = CandidateContextIndex.prepare(self.prepared, candidates, gives)
        # The rule operation evaluates source assertions. Its view item IDs are occurrence
        # references; canonical fact IDs remain separate in ClaimCandidate and assessments.
        from .analytical_kernels import (
            VIEW_ALTERNATIVES,
            VIEW_CLAIMS,
            VIEW_ENTITIES,
            VIEW_IDENTITY,
            ViewSpec,
        )

        entities = {key: entity(key) for key in inputs.entity_metadata}
        specs = []
        for name, decl in self.source.get("views", {}).items():
            applies = {
                c.predicate
                for c in candidates
                if self.applies({"applies_to": decl["applies_to"]}, c)
            }
            normalized = {**decl, "source": self.prepared.expand_name(decl["source"])}
            specs.append(ViewSpec.from_declaration(name, normalized, applies))
        tables = (
            pa.Table.from_pylist(
                [
                    {
                        "claim": c.occurrence_id,
                        "predicate": c.predicate,
                        "subject": c.subject,
                        "object": c.object
                        if isinstance(c.object, str) and c.object in entities
                        else None,
                        "statement": c.statement,
                    }
                    for c in candidates
                ],
                schema=VIEW_CLAIMS,
            ),
            pa.Table.from_pylist(
                [
                    {
                        "entity": e.id,
                        "key": e.key,
                        "type": e.type,
                        "label": e.label,
                        "symbol": e.symbol,
                    }
                    for e in entities.values()
                ],
                schema=VIEW_ENTITIES,
            ),
            pa.Table.from_pylist(
                [
                    {"entity": e.id, "slot": slot, "value": value}
                    for e in entities.values()
                    for slot, value in e.identity.items()
                ],
                schema=VIEW_IDENTITY,
            ),
            pa.Table.from_pylist(group_views, schema=VIEW_ALTERNATIVES),
        )
        facts = {
            (row["claim"], row["view"]): tuple(row["facts"])
            for row in scope.views(
                scope.connection.from_arrow(tables[0]),
                scope.connection.from_arrow(tables[1]),
                scope.connection.from_arrow(tables[2]),
                scope.connection.from_arrow(tables[3]),
                specs,
            )
            .to_arrow_table()
            .to_pylist()
        }
        fused_ids = set(fused["fact_id"].to_pylist())
        if candidate_facts - fused_ids:
            raise DomainOperationRefused("fusion omitted a source-supported fact")
        for c in candidates:
            qvalues: dict[str, Any] = {name: None for name in self.qprops}
            qvalues.update(
                c.rule_qualification if c.rule_qualification is not None else c.qualification
            )

            obj = None
            value = None
            bindings = []
            unknown = None
            unknown_reason = None
            reading_note = None
            reading_reason = None
            if isinstance(c.object, str) and c.object in inputs.entity_metadata:
                obj = entity(c.object)
                prop = next(
                    p for p in self.definitions[c.class_name].properties if p.iri == c.predicate
                )
                value = project_rule_value(
                    self.prepared, prop, c.rule_object if c.rule_object is not None else c.object
                )
            else:
                raw = c.rule_object if c.rule_object is not None else c.object
                reading = None
                if isinstance(raw, dict):
                    reading, reading_reason = _candidate_reading(self.prepared, c, raw, readings)
                    reading_note = reading_reason.render() if reading_reason is not None else None
                    if raw.get("language") == "latex":
                        bindings = [
                            BindingView(
                                binding["symbol"],
                                binding["kind"],
                                binding.get("entity"),
                                binding.get("claim"),
                                binding.get("parameter"),
                            )
                            for binding in raw.get("bindings", ())
                        ]
                prop = next(
                    p for p in self.definitions[c.class_name].properties if p.iri == c.predicate
                )
                value = project_rule_value(self.prepared, prop, raw, reading)
            # Multiple located reports of the same proposition are support, not competing
            # scientific claims. The kernels preserve occurrence addresses for source
            # policy, then these semantic set views collapse through canonical facts.
            same = tuple(
                sorted(
                    {
                        by_occurrence[oid]
                        for oid in facts.get((c.occurrence_id, "same_slot"), ())
                        if by_occurrence[oid] != c.fact_id
                    }
                )
            )
            alternatives = tuple(
                sorted(
                    {
                        by_occurrence[oid]
                        for oid in facts.get((c.occurrence_id, "alternative_of"), ())
                        if by_occurrence[oid] != c.fact_id
                    }
                )
            )
            if alternatives:
                ambiguous.add(c.occurrence_id)
            try:
                condition_nodes = tuple(
                    nodes(
                        (
                            c.rule_qualification
                            if c.rule_qualification is not None
                            else c.qualification
                        ).get("condition")
                    )
                )
            except SemanticOperationRefusal as exc:
                condition_nodes = ()
                unknown_reason = replace(
                    exc.semantic_reason,
                    references=(c.occurrence_id, *exc.semantic_reason.references),
                )
                unknown = unknown_reason.render()
            statement = (
                StatementView(c.statement, c.statement, c.statement_kind or "")
                if c.statement
                else None
            )
            meta = self.metadata.get((c.class_name, c.predicate), {})
            view = SimpleNamespace(
                id=c.occurrence_id,
                key=c.occurrence_id,
                predicate=self.compact(c.predicate),
                groups=tuple(meta.get("groups", ())),
                subject=entity(c.subject),
                object=obj,
                value=value,
                qualifiers=QualifiersView(qvalues),
                qualification_values={
                    name: project_rule_value(self.prepared, self.qprops[name], raw)
                    for name, raw in qvalues.items()
                    if raw is not None
                    and not self.qprops[name].multivalued
                    and (
                        self.qprops[name].range not in self.definitions
                        or self.qprops[name].range == "Value"
                        or "Value" in self.definitions[self.qprops[name].range].ancestors
                    )
                },
                statement=statement,
                statement_kind=c.statement_kind,
                statement_role=c.statement_role,
                establishment=c.establishment,
                bindings=tuple(bindings),
                condition_nodes=condition_nodes,
                claim_refs=tuple(n.ref for n in condition_nodes if n.ref is not None),
                statement_premises=context_index.statement_premises(c),
                gives_symbols=tuple(sorted(gives[c.occurrence_id])),
                given_by_others=context_index.given_by_others(c.occurrence_id),
                same_slot=same,
                alternative_of=alternatives,
                evidence_count=c.evidence_count,
                unresolved_symbols=sum(b.bind == "unresolved" for b in bindings),
            )
            for name in self.source.get("views", {}):
                setattr(view, name, facts.get((c.occurrence_id, name), ()))
            findings = []
            if c.occurrence_id in incomplete_alternatives:
                unknown_reason = SemanticReason(
                    "missing_operands",
                    "evaluate",
                    self.prepared.release_id,
                    (c.occurrence_id,),
                    expected="materialized alternative members",
                    actual="incomplete alternative",
                    detail="source alternative has an unmaterialized member",
                )
                unknown = unknown_reason.render()
            if c.unresolved_references:
                unknown_reason = SemanticReason(
                    "missing_operands",
                    "evaluate",
                    self.prepared.release_id,
                    (c.occurrence_id, *c.unresolved_references),
                    expected="bound source endpoints",
                    actual="unresolved endpoints",
                    detail="unresolved declared source endpoint: "
                    + ",".join(c.unresolved_references),
                )
                unknown = unknown_reason.render()
            if reading_note:
                findings.append(
                    ("operation.not_checkable", "warning", reading_note, reading_reason)
                )
            if unknown:
                # Unchecked projection or reading establishes neither a rule pass nor a refutation.
                findings.append(("operation.not_checkable", "warning", unknown, unknown_reason))
            for raw, when, check in self.rules:
                if not self.applies(raw, c):
                    continue
                if unknown and raw["id"].startswith("guideline."):
                    continue
                if when.evaluate({"claim": view}) and not check.evaluate({"claim": view}):
                    findings.append(
                        (
                            raw["id"],
                            "warning"
                            if raw in self.source.get("guideline", ())
                            else raw.get("severity", "error"),
                            raw.get("description", raw["id"]),
                            None,
                        )
                    )
            for rule, severity, message, semantic_reason in findings:
                aid = (
                    "assessment:"
                    + sha256(
                        canonical_bytes(
                            [
                                VERSION,
                                c.occurrence_id,
                                rule,
                                severity,
                                semantic_reason_identity(semantic_reason)
                                if semantic_reason is not None
                                else message,
                            ]
                        )
                    ).hexdigest()
                )
                from .operation_results import validate_result_dimension

                finding = "refuted" if severity == "error" else "warning"
                validate_result_dimension(
                    self.prepared,
                    "scientific_policy",
                    "finding",
                    finding,
                    field="assessment.outcome",
                )
                assessments.append(
                    AssessmentRow(
                        aid,
                        rule,
                        VERSION,
                        finding,
                        occurrence_id=c.occurrence_id,
                        reason=message,
                        uncertainty=unknown or reading_note,
                        semantic_reason=semantic_reason,
                    )
                )
                if severity == "error":
                    errors.add(c.occurrence_id)
            status = (
                "rejected"
                if c.occurrence_id in errors
                else "ambiguous"
                if c.occurrence_id in ambiguous
                else "candidate"
                if unknown or c.occurrence_id in unresolved
                else "accepted"
            )
            aid = (
                "assessment:"
                + sha256(canonical_bytes([VERSION, c.occurrence_id, status])).hexdigest()
            )
            from .operation_results import validate_result_dimension

            validate_result_dimension(
                self.prepared, "scientific_policy", "selection", status, field="selection.outcome"
            )
            assessments.append(
                AssessmentRow(
                    aid,
                    "consolidate.status",
                    VERSION,
                    status,
                    occurrence_id=c.occurrence_id,
                    uncertainty=unknown,
                    semantic_reason=unknown_reason,
                )
            )
            views[c.occurrence_id] = status
        # Structural source declarations are independent of the scientific claim decision table.
        selected = {f.fact_id for f in inputs.batch.fact if f.fact_id not in candidate_facts}
        display = {}
        values = {v.value_id: v for v in inputs.batch.typed_value}
        for fact in inputs.batch.fact:
            if fact.fact_id not in selected:
                continue
            prop = next(
                (
                    p
                    for d in self.prepared.definitions
                    for p in d.properties
                    if p.iri == fact.property_id
                ),
                None,
            )
            if (
                prop is not None
                and not prop.multivalued
                and any(
                    m.get("cs:role") == "display" and m["property"] == fact.property_id
                    for m in self.metadata.values()
                )
            ):
                display.setdefault((fact.subject_id, fact.property_id), []).append(fact)
        for group in display.values():
            keep = min(
                group,
                key=lambda fact: (values[fact.object_value_id].text_value or "", fact.fact_id),
            )
            selected.difference_update(
                fact.fact_id for fact in group if fact.fact_id != keep.fact_id
            )
        selected.update(c.fact_id for c in candidates if views[c.occurrence_id] == "accepted")
        representative_rows = []
        covered = set()
        for component in equivalent_components:
            accepted = sorted(set(component) & selected)
            if not accepted:
                continue
            component_id = (
                "component:" + sha256(canonical_bytes(sorted(set(component)))).hexdigest()
            )
            representative_rows.extend(
                ScientificRepresentativeRow(fact, accepted[0], "min-fact-id-1", component_id)
                for fact in accepted
            )
            covered.update(accepted)
        representative_rows.extend(
            ScientificRepresentativeRow(
                fact,
                fact,
                "min-fact-id-1",
                "component:" + sha256(canonical_bytes([fact])).hexdigest(),
            )
            for fact in sorted(selected - covered)
        )
        from .record_admission import cap_record_selections, evaluate_record_admissions

        record_admission = evaluate_record_admissions(
            self.prepared, inputs.record_reports, inputs.record_policy_bindings
        )
        selected, record_admission = cap_record_selections(
            inputs.batch, frozenset(selected), record_admission
        )
        return PolicyDecision(
            frozenset(selected),
            tuple(sorted(assessments, key=lambda a: a.assessment_id)),
            alternative_groups,
            alternative_members,
            tuple(
                sorted(
                    (
                        row
                        for row in representative_rows
                        if row.fact_id in selected and row.representative_fact_id in selected
                    ),
                    key=lambda row: row.fact_id,
                )
            ),
            record_admission,
        )
