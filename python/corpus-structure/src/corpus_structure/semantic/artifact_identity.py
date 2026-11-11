"""Source-work-scoped artifact candidates; scores confer no equivalence authority."""

from __future__ import annotations

import re
from collections import defaultdict
from contextlib import contextmanager
from hashlib import sha256
from itertools import combinations
from typing import Literal

from pydantic import Field, JsonValue, TypeAdapter, model_validator
from rapidfuzz.fuzz import ratio

from .characterization import AnnotationReference
from .identity import canonical_bytes
from .retained_contributions import RetainedContributionRef
from .structural_base import StructuralValue


class ArtifactAliasSpan(StructuralValue):
    """An exact character extent in an authenticated native item."""

    source_pointer: str = Field(min_length=1)
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def extent(self):
        if self.end - self.start != len(self.text) or not self.text.strip():
            raise ValueError("artifact alias evidence differs from its exact native extent")
        return self


class SourceArtifactOccurrence(StructuralValue):
    protocol: Literal["source-artifact-occurrence-2"] = "source-artifact-occurrence-2"
    artifact_kind: Literal["table", "figure", "theorem", "section"]
    source_work: str = Field(min_length=1)
    controlled_code: str | None = None
    title: str | None = None
    aliases: tuple[str, ...] = ()
    alias_state: Literal["unknown", "known_empty", "observed"] = "unknown"
    alias_occurrences: tuple[ArtifactAliasSpan, ...] = ()
    alias_absence: ArtifactAliasSpan | None = None
    revision: str | None = None
    revision_state: Literal["observed", "unknown", "malformed", "unresolved"] = "unknown"
    occurrence_role: Literal["caption", "reference"]
    scope: str = Field(min_length=1)
    source_pointer: str = Field(min_length=1)
    dependencies: tuple[str, ...] = Field(min_length=1)
    primary_node: AnnotationReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def provenance(self):
        if self.alias_state == "observed":
            if (
                not self.alias_occurrences
                or tuple(a.text for a in self.alias_occurrences) != self.aliases
                or len(set(self.alias_occurrences)) != len(self.alias_occurrences)
                or self.alias_absence is not None
            ):
                raise ValueError("observed aliases require distinct exact located evidence")
        elif (
            self.aliases
            or self.alias_occurrences
            or (self.alias_absence is not None) != (self.alias_state == "known_empty")
        ):
            raise ValueError("known empty aliases require explicit source evidence")
        if (self.revision is not None) != (self.revision_state == "observed"):
            raise ValueError("only observed revisions carry an interpreted revision")
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError("artifact dependencies repeat")
        return self


class ArtifactCitation(StructuralValue):
    source_ref: str = Field(min_length=1)
    passage_id: str = Field(min_length=1)
    source_pointer: str = Field(min_length=1)
    start: int = Field(ge=0, strict=True)
    end: int = Field(gt=0, strict=True)
    text: str = Field(min_length=1)

    @model_validator(mode="after")
    def extent(self):
        if self.end <= self.start or self.end - self.start != len(self.text):
            raise ValueError("artifact citation differs from its extent")
        return self


class ArtifactSourceLabel(StructuralValue):
    """A label explicitly attached to an artifact designator in a native item."""

    state: Literal["observed", "unknown", "unresolved"] = "unknown"
    value: str | None = None
    evidence: tuple[ArtifactAliasSpan, ...] = ()

    @model_validator(mode="after")
    def provenance(self):
        labels = {span.text for span in self.evidence}
        if self.state != (
            "unknown" if not labels else "observed" if len(labels) == 1 else "unresolved"
        ) or self.value != (next(iter(labels)) if len(labels) == 1 else None):
            raise ValueError("artifact source label differs from its located evidence")
        return self


class ArtifactReferenceDesignator(StructuralValue):
    """A source names an alternate designator and its numbering namespace."""

    target_code: str
    target_numbering: str
    cue: ArtifactAliasSpan
    primary_node: AnnotationReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class ArtifactRecord(StructuralValue):
    contribution_id: str = Field(min_length=1)
    occurrence_id: str = Field(min_length=1)
    artifact: SourceArtifactOccurrence
    source_contribution: dict[str, JsonValue]
    citations: tuple[ArtifactCitation, ...] = Field(min_length=1)
    numbering: ArtifactSourceLabel = Field(default_factory=ArtifactSourceLabel)
    revision: ArtifactSourceLabel = Field(default_factory=ArtifactSourceLabel)
    explicit_reference: ArtifactReferenceDesignator | None = None
    primary_node: AnnotationReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class ArtifactModelField(StructuralValue):
    name: str = Field(min_length=1)
    value: float | None = Field(default=None, allow_inf_nan=False)


class ArtifactPairKey(StructuralValue):
    left: str = Field(min_length=1)
    right: str = Field(min_length=1)


class ArtifactNominationEndpoint(StructuralValue):
    role: Literal["attachment", "target"]
    record_id: str
    contribution_id: str
    origin_source_view_id: int
    origin_anchor_id: str


class ArtifactNomination(ArtifactPairKey):
    kind: Literal["artifact_reference_target"] = "artifact_reference_target"
    relationship: RetainedContributionRef
    endpoints: tuple[ArtifactNominationEndpoint, ArtifactNominationEndpoint]
    origin_cue: ArtifactAliasSpan
    primary_node: AnnotationReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )

    @model_validator(mode="after")
    def direction(self):
        if (
            tuple(e.role for e in self.endpoints) != ("attachment", "target")
            or sorted(e.record_id for e in self.endpoints) != [self.left, self.right]
            or self.left >= self.right
        ):
            raise ValueError("artifact nomination must preserve directed distinct endpoints")
        return self


ArtifactRoute = Literal[
    "exact_code",
    "unscoped_code",
    "lexical_title",
    "explicit_reference",
    "external_pairs",
    "native_alias_array",
]
ARTIFACT_ROUTES: tuple[ArtifactRoute, ...] = (
    "exact_code",
    "unscoped_code",
    "lexical_title",
    "explicit_reference",
    "external_pairs",
    "native_alias_array",
)


class ArtifactPair(StructuralValue):
    left: str
    right: str
    candidate_routes: tuple[ArtifactRoute, ...] = Field(min_length=1)
    scope_state: Literal["compatible", "excluded"]
    numbering_relation: Literal["same_observed", "different_observed", "unknown", "unresolved"]
    revision_relation: Literal["same_observed", "different_observed", "unknown", "unresolved"]
    score_status: Literal[
        "eligible",
        "scored",
        "excluded",
        "reference_only",
        "namespace_unavailable",
        "no_comparable_features",
    ]
    lexical_score: float = Field(ge=0, le=1)
    model_probability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    model_id: str | None = None
    model_evidence: tuple[ArtifactModelField, ...] = ()
    standing: Literal["candidate_relative_private"] = "candidate_relative_private"
    dependencies: tuple[str, ...]


class ArtifactRouteCount(StructuralValue):
    route: ArtifactRoute
    nominated: int
    eligible: int
    marginal: int
    cumulative: int


def artifact_route_counts(pairs: tuple[ArtifactPair, ...]) -> tuple[ArtifactRouteCount, ...]:
    seen = set()
    counts = []
    for route in ARTIFACT_ROUTES:
        nominated = tuple(p for p in pairs if route in p.candidate_routes)
        keys = {(p.left, p.right) for p in nominated}
        marginal = len(keys - seen)
        seen.update(keys)
        counts.append(
            ArtifactRouteCount(
                route=route,
                nominated=len(nominated),
                eligible=sum(p.score_status in {"eligible", "scored"} for p in nominated),
                marginal=marginal,
                cumulative=len(seen),
            )
        )
    return tuple(counts)


def normalized_code(code: str | None) -> str | None:
    """Only an observed source-local numeric identifier qualifies for exact evidence."""
    if code is None:
        return None
    value = code.strip()
    if not re.fullmatch(r"[A-Za-z]?\d+(?:[.\-]\d+)*[A-Za-z]?", value):
        return None
    return value.casefold()


def label_relation(left: ArtifactSourceLabel, right: ArtifactSourceLabel):
    if "unresolved" in (left.state, right.state):
        return "unresolved"
    if left.value is None or right.value is None:
        return "unknown"
    return "same_observed" if left.value == right.value else "different_observed"


def artifact_scope(record: ArtifactRecord) -> tuple[str, str]:
    return record.artifact.source_work, record.artifact.artifact_kind


class ArtifactReferenceResolution(StructuralValue):
    attachment: str
    targets: tuple[str, ...]
    outcome: Literal["witnessed_candidate", "ambiguous", "no_compatible_candidate"]


class ArtifactDeclaredEndpoint(StructuralValue):
    record_id: str
    citation: ArtifactCitation
    work_cue: ArtifactCitation | None = Field(default=None, exclude_if=lambda value: value is None)
    work_primary_node: AnnotationReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


class ArtifactDeclaredRelationship(StructuralValue):
    """One source declaration with exact target alternatives and their original citations."""

    kind: Literal["reference", "same_lineage", "supersedes"]
    source_id: str
    origin: ArtifactCitation
    targets: tuple[ArtifactDeclaredEndpoint, ...]
    outcome: Literal["witnessed_candidate", "ambiguous", "no_compatible_candidate"]
    primary_node: AnnotationReference | None = Field(
        default=None, exclude_if=lambda value: value is None
    )


def artifact_reference_resolutions(
    records: tuple[ArtifactRecord, ...],
) -> tuple[ArtifactReferenceResolution, ...]:
    """Join explicit scoped designators to selected physical captions."""
    captions: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
    for record in records:
        if (
            record.artifact.occurrence_role == "caption"
            and (namespace := record.numbering.value)
            and (code := normalized_code(record.artifact.controlled_code))
        ):
            captions[(*artifact_scope(record), namespace, code)].append(record.contribution_id)
    resolutions = []
    for record in sorted(records, key=lambda r: r.contribution_id):
        if (cue := record.explicit_reference) is None:
            continue
        targets = tuple(
            sorted(
                captions.get(
                    (*artifact_scope(record), cue.target_numbering, cue.target_code.casefold()), ()
                )
            )
        )
        resolutions.append(
            ArtifactReferenceResolution(
                attachment=record.contribution_id,
                targets=targets,
                outcome="no_compatible_candidate"
                if not targets
                else "witnessed_candidate"
                if len(targets) == 1
                else "ambiguous",
            )
        )
    return tuple(resolutions)


def artifact_score_status(a: ArtifactRecord, b: ArtifactRecord, *, excluded: bool = False):
    numbering = label_relation(a.numbering, b.numbering)
    av, bv = a.artifact, b.artifact
    if excluded or artifact_scope(a) != artifact_scope(b) or numbering == "different_observed":
        return "excluded"
    if "reference" in (av.occurrence_role, bv.occurrence_role):
        return "reference_only"
    comparable_codes = normalized_code(av.controlled_code) and normalized_code(bv.controlled_code)
    if comparable_codes and numbering != "same_observed":
        return "namespace_unavailable"
    if not comparable_codes and not (av.title and bv.title):
        return "no_comparable_features"
    return "eligible"


def pair_candidates(
    records: tuple[ArtifactRecord, ...],
    *,
    external_nominations: tuple[ArtifactNomination, ...] = (),
    declared_relationships: tuple[ArtifactDeclaredRelationship, ...] = (),
    explicit_references: tuple[ArtifactReferenceResolution, ...] = (),
    native_alias_pairs: tuple[tuple[str, str], ...] = (),
    title_threshold=70.0,
    exclusions=(),
    known_anchor_ids=(),
) -> tuple[ArtifactPair, ...]:
    """Retain generator provenance once per pair; never partition a whole component."""
    if not 0 <= title_threshold <= 100:
        raise ValueError("title threshold must be between zero and100")
    by_id = {r.contribution_id: r for r in records}
    if len(by_id) != len(records):
        raise ValueError("artifact record identifiers repeat")
    external: dict[tuple[str, str], set[str]] = {}
    for nomination in external_nominations:
        key = (min(nomination.left, nomination.right), max(nomination.left, nomination.right))
        external.setdefault(key, set()).add(nomination.relationship.contribution_id)
    for declaration in declared_relationships:
        for target in declaration.targets:
            left, right = sorted((declaration.source_id, target.record_id))
            key = (left, right)
            external.setdefault(key, set()).add("artifact-declaration:" + declaration.identity)
    alias = {(min(left, right), max(left, right)) for left, right in native_alias_pairs}
    forbidden = {(min(left, right), max(left, right)) for left, right in exclusions}
    if any(
        len(p) != 2 or p[0] == p[1] or not set(p) <= by_id.keys()
        for p in external.keys() | forbidden | alias
    ):
        raise ValueError("pair endpoints must be distinct selected artifact records")
    anchors = frozenset(known_anchor_ids)
    if len(anchors) != len(known_anchor_ids) or not anchors <= by_id.keys():
        raise ValueError("known anchors must be distinct exact selected artifact records")
    from .identity_resolution import constrained_label_groups

    scope = {key: artifact_scope(r) for key, r in by_id.items()}
    codes = {key: normalized_code(r.artifact.controlled_code) for key, r in by_id.items()}
    code_blocks: dict[tuple, list[str]] = defaultdict(list)
    title_blocks: dict[tuple, list[str]] = defaultdict(list)
    for key in sorted(by_id):
        if code := codes[key]:
            code_blocks[(*scope[key], code)].append(key)
        if by_id[key].artifact.title:
            title_blocks[scope[key]].append(key)

    routed: dict[tuple[str, str], set[ArtifactRoute]] = defaultdict(set)
    lexical_scores = {}
    for block in code_blocks.values():
        for left, right in combinations(block, 2):
            numbering = label_relation(by_id[left].numbering, by_id[right].numbering)
            if numbering != "different_observed":
                routed[left, right].add(
                    "exact_code" if numbering == "same_observed" else "unscoped_code"
                )
    for block in title_blocks.values():
        for left, right in combinations(block, 2):
            a, b = by_id[left], by_id[right]
            title_a, title_b = a.artifact.title, b.artifact.title
            if (
                not title_a
                or not title_b
                or a.occurrence_id == b.occurrence_id
                or label_relation(a.numbering, b.numbering) == "different_observed"
            ):
                continue
            lexical = ratio(title_a, title_b) / 100
            if (
                lexical * 100 >= title_threshold
                or (left, right) in routed
                or (left, right) in external
                or (left, right) in alias
            ):
                lexical_scores[left, right] = lexical
            if lexical * 100 >= title_threshold:
                routed[left, right].add("lexical_title")
    for key in external:
        routed[key].add("external_pairs")
    for reference in explicit_references:
        for target in reference.targets:
            left, right = sorted((reference.attachment, target))
            routed[left, right].add("explicit_reference")
    for left, right in alias:
        a, b = by_id[left], by_id[right]
        if scope[left] != scope[right] or not set(alias_tokens(a.artifact)) & set(
            alias_tokens(b.artifact)
        ):
            raise ValueError("native alias pair lacks compatible observed aliases")
        if label_relation(a.numbering, b.numbering) != "different_observed":
            routed[left, right].add("native_alias_array")

    result = []
    for (left, right), routes in sorted(routed.items()):
        a, b = by_id[left], by_id[right]
        if a.occurrence_id == b.occurrence_id:
            continue
        av, bv = a.artifact, b.artifact
        numbering = label_relation(a.numbering, b.numbering)
        # This is one pair proposal, not an equivalence or connected-component universe.
        # Reusing the existing guard cannot authorize an unexamined transitive bridge.
        permitted = (
            len(
                constrained_label_groups(
                    (left, right),
                    ((left, right),) if (left, right) in forbidden else (),
                    anchors.intersection((left, right)),
                )
            )
            == 1
        )
        score_status = artifact_score_status(a, b, excluded=not permitted)
        result.append(
            ArtifactPair(
                left=left,
                right=right,
                candidate_routes=tuple(route for route in ARTIFACT_ROUTES if route in routes),
                scope_state="excluded" if score_status == "excluded" else "compatible",
                numbering_relation=numbering,
                revision_relation=label_relation(a.revision, b.revision),
                score_status=score_status,
                lexical_score=lexical_scores.get((left, right), 0.0),
                dependencies=tuple(
                    sorted(
                        {
                            left,
                            right,
                            *av.dependencies,
                            *bv.dependencies,
                            *external.get((left, right), ()),
                        }
                    )
                ),
            )
        )
    return tuple(result)


class ArtifactScoringPolicy(StructuralValue):
    """Declared model assumptions, not calibrated source truth."""

    prior: float = Field(gt=0, lt=1)
    code_m: float = Field(gt=0, lt=1)
    code_u: float = Field(gt=0, lt=1)
    title_m: float = Field(gt=0, lt=1)
    title_u: float = Field(gt=0, lt=1)


def alias_tokens(artifact: SourceArtifactOccurrence) -> tuple[str, ...]:
    return tuple(sorted({alias.strip().casefold() for alias in artifact.aliases}))


@contextmanager
def artifact_linker(records: tuple[ArtifactRecord, ...], policy: ArtifactScoringPolicy):
    """One bounded provider instance for the released fixed model."""
    import duckdb
    from splink import DuckDBAPI, Linker, SettingsCreator
    from splink.comparison_library import ExactMatch

    payload = [
        dict(
            unique_id=r.contribution_id,
            source_dataset="artifacts",
            controlled_code=normalized_code(r.artifact.controlled_code),
            title=r.artifact.title.casefold().strip() if r.artifact.title else None,
        )
        for r in records
    ]
    settings = SettingsCreator(
        link_type="dedupe_only",
        probability_two_random_records_match=policy.prior,
        comparisons=[
            ExactMatch("controlled_code").configure(
                m_probabilities=[policy.code_m, 1 - policy.code_m],
                u_probabilities=[policy.code_u, 1 - policy.code_u],
            ),
            ExactMatch("title").configure(
                m_probabilities=[policy.title_m, 1 - policy.title_m],
                u_probabilities=[policy.title_u, 1 - policy.title_u],
            ),
        ],
        retain_matching_columns=True,
        retain_intermediate_calculation_columns=True,
    )
    with duckdb.connect() as connection:
        api = DuckDBAPI(connection=connection)
        yield Linker(api.register(payload, dataset_display_name="artifacts"), settings)


def predict_artifact_pairs(linker, allowed: tuple[tuple[str, str], ...]):
    """Register exactly one deduplicated pair population for a provider prediction."""
    if not allowed:
        return {}
    table = linker.table_management.register_table(
        [
            dict(
                join_key_l=left,
                join_key_r=right,
                source_dataset_l="artifacts",
                source_dataset_r="artifacts",
                match_key="external",
            )
            for left, right in allowed
        ],
        "owned_artifact_pairs",
        overwrite=True,
    )
    linker.table_management.register_blocked_pairs_for_predict(table)
    predictions = linker.inference.predict().as_record_list()
    scored = {
        (min(r["unique_id_l"], r["unique_id_r"]), max(r["unique_id_l"], r["unique_id_r"])): r
        for r in predictions
    }
    if len(predictions) != len(allowed) or set(scored) != set(allowed):
        raise ValueError("provider changed selected pair membership")
    return scored


def score_pairs(
    records: tuple[ArtifactRecord, ...],
    pairs: tuple[ArtifactPair, ...],
    policy: ArtifactScoringPolicy,
) -> tuple[ArtifactPair, ...]:
    """Score exactly the registered eligible pair IDs using a frozen Splink model."""
    allowed = tuple((p.left, p.right) for p in pairs if p.score_status == "eligible")
    if not allowed:
        return pairs
    source = {r.contribution_id for r in records}
    if any(left not in source or right not in source for left, right in allowed):
        raise ValueError("scored pair outside selected population")
    with artifact_linker(records, policy) as linker:
        probabilities = predict_artifact_pairs(linker, allowed)
    return tuple(
        ArtifactPair.model_validate(
            {
                **p.model_dump(),
                "score_status": "scored",
                "model_probability": float(probabilities[(p.left, p.right)]["match_probability"]),
                "model_id": policy.identity,
                "model_evidence": tuple(
                    ArtifactModelField(name=key, value=value)
                    for key, value in probabilities[(p.left, p.right)].items()
                    if key.startswith(("gamma_", "mw_", "tf_"))
                ),
            }
        )
        if p.score_status == "eligible"
        else p
        for p in pairs
    )


def pair_identity(pair: ArtifactPair) -> str:
    return sha256(canonical_bytes([pair.left, pair.right])).hexdigest()


def native_alias_candidates(
    records: tuple[ArtifactRecord, ...], *, count_rules: bool = False
) -> tuple[tuple[tuple[str, str], ...], tuple[dict[str, JsonValue], ...]]:
    """Actual Splink array blocking; title-derived aliases must not be fabricated."""
    import duckdb
    from splink import DuckDBAPI, Linker, SettingsCreator, block_on

    eligible = {r.contribution_id: r for r in records if r.artifact.aliases}
    if len(eligible) < 2:
        return (), ()
    payload = [
        dict(
            unique_id=r.contribution_id,
            source_work=r.artifact.source_work,
            artifact_kind=r.artifact.artifact_kind,
            aliases=list(alias_tokens(r.artifact)),
        )
        for r in eligible.values()
    ]
    settings = SettingsCreator(
        link_type="dedupe_only",
        comparisons=[],
        blocking_rules_to_generate_predictions=[
            block_on("source_work", "artifact_kind", "aliases", arrays_to_explode=["aliases"])
        ],
    )
    with duckdb.connect() as connection:
        api = DuckDBAPI(connection=connection)
        linker = Linker(api.register(payload, dataset_display_name="artifacts"), settings)
        blocked = linker.inference.compute_blocked_pairs_for_predict().as_record_list()
        counts: tuple[dict[str, JsonValue], ...] = ()
        if count_rules:
            counts = TypeAdapter(tuple[dict[str, JsonValue], ...]).validate_python(
                linker.blocking_analysis.count_comparisons_from_blocking_rules(
                    record_sample_proportion=1.0
                )
            )
    pairs = tuple(
        sorted(
            {
                (
                    min(row["join_key_l"], row["join_key_r"]),
                    max(row["join_key_l"], row["join_key_r"]),
                )
                for row in blocked
                if label_relation(
                    eligible[row["join_key_l"]].numbering, eligible[row["join_key_r"]].numbering
                )
                != "different_observed"
            }
        )
    )
    return pairs, counts


class ArtifactIdentityProduct(StructuralValue):
    """One selected source-work cohort, candidate routes and frozen model results."""

    protocol: Literal["artifact-identity-3", "artifact-identity-4", "artifact-identity-5"] = (
        "artifact-identity-3"
    )
    identity_grain: Literal["source_work_artifact_lineage"] = "source_work_artifact_lineage"
    records: tuple[ArtifactRecord, ...] = ()
    pairs: tuple[ArtifactPair, ...] = ()
    native_alias_pairs: tuple[ArtifactPairKey, ...] = ()
    external_nominations: tuple[ArtifactNomination, ...] = ()
    explicit_references: tuple[ArtifactReferenceResolution, ...] = ()
    declared_relationships: tuple[ArtifactDeclaredRelationship, ...] | None = Field(
        default=None, exclude_if=lambda value: value is None
    )
    route_counts: tuple[ArtifactRouteCount, ...]
    policy: ArtifactScoringPolicy
    source_mapping_provenance: tuple[str, ...] = ()
    known_anchor_ids: tuple[str, ...] = ()
    unbound_source_ids: tuple[int, ...] = ()
    standing: Literal["candidate_relative_private"] = "candidate_relative_private"

    @model_validator(mode="after")
    def membership(self):
        by_id = {r.contribution_id: r for r in self.records}
        if self.protocol == "artifact-identity-5" and (
            any(
                record.primary_node is None
                or record.artifact.primary_node != record.primary_node
                or (
                    record.explicit_reference is not None
                    and record.explicit_reference.primary_node is None
                )
                for record in self.records
            )
            or any(nomination.primary_node is None for nomination in self.external_nominations)
            or any(
                declaration.primary_node is None
                or any(
                    (target.work_cue is None) != (target.work_primary_node is None)
                    for target in declaration.targets
                )
                for declaration in self.declared_relationships or ()
            )
        ):
            raise ValueError("current artifact identity requires exact primary source witnesses")
        if len(by_id) != len(self.records):
            raise ValueError("identity record identifiers repeat")
        anchors = frozenset(self.known_anchor_ids)
        if len(anchors) != len(self.known_anchor_ids) or not anchors <= by_id.keys():
            raise ValueError("known anchors must be distinct selected artifact records")
        by_pair = {(p.left, p.right): p for p in self.pairs}
        if len(by_pair) != len(self.pairs):
            raise ValueError("identity pairs repeat")
        if self.route_counts != artifact_route_counts(self.pairs):
            raise ValueError("artifact route counts differ from the selected pair ledger")
        explicit_pairs = {
            tuple(sorted((reference.attachment, target)))
            for reference in self.explicit_references
            for target in reference.targets
        }
        if self.explicit_references != artifact_reference_resolutions(
            self.records
        ) or explicit_pairs != {
            key for key, pair in by_pair.items() if "explicit_reference" in pair.candidate_routes
        }:
            raise ValueError("artifact explicit reference differs from selected source targets")
        for pair in self.pairs:
            if pair.left >= pair.right or not {pair.left, pair.right} <= by_id.keys():
                raise ValueError("identity pair outside exact cohort")
            a, b = by_id[pair.left], by_id[pair.right]
            if pair.scope_state == "compatible" and (
                a.artifact.source_work,
                a.artifact.artifact_kind,
            ) != (b.artifact.source_work, b.artifact.artifact_kind):
                raise ValueError("identity pair crosses source-work or artifact kind")
            if pair.scope_state == "compatible" and pair.left in anchors and pair.right in anchors:
                raise ValueError("distinct known artifact anchors cannot form a compatible pair")
            if pair.score_status == "scored":
                valid_score = (
                    pair.scope_state == "compatible"
                    and pair.model_id == self.policy.identity
                    and pair.model_probability is not None
                )
            else:
                valid_score = (
                    pair.model_probability is None
                    and pair.model_id is None
                    and not pair.model_evidence
                )
            if not valid_score:
                raise ValueError("identity score lacks selected frozen model custody")
        nomination_ids = set()
        nominated = set()
        for nomination in self.external_nominations:
            relation_id = nomination.relationship.contribution_id
            key = (nomination.left, nomination.right)
            pair = by_pair.get(key)
            if (
                relation_id in nomination_ids
                or pair is None
                or "external_pairs" not in pair.candidate_routes
                or relation_id not in pair.dependencies
            ):
                raise ValueError("external nomination lacks its exact pair and relationship proof")
            nomination_ids.add(relation_id)
            nominated.add(key)
        if (self.protocol in {"artifact-identity-4", "artifact-identity-5"}) != (
            self.declared_relationships is not None
        ):
            raise ValueError("artifact declaration ledger differs from the selected protocol")
        for declaration in self.declared_relationships or ():
            if declaration.outcome != (
                "no_compatible_candidate"
                if not declaration.targets
                else "witnessed_candidate"
                if len(declaration.targets) == 1
                else "ambiguous"
            ):
                raise ValueError("artifact declaration does not preserve its target alternatives")
            if declaration.source_id not in by_id:
                raise ValueError("artifact declaration is outside the selected occurrence cohort")
            for target in declaration.targets:
                left, right = sorted((declaration.source_id, target.record_id))
                key = (left, right)
                pair = by_pair.get(key)
                if (
                    pair is None
                    or "external_pairs" not in pair.candidate_routes
                    or "artifact-declaration:" + declaration.identity not in pair.dependencies
                ):
                    raise ValueError("artifact declaration lacks its exact pair route")
                nominated.add(key)
        if nominated != {
            key for key, p in by_pair.items() if "external_pairs" in p.candidate_routes
        }:
            raise ValueError("external pair route lacks an authenticated nomination")

        alias_pairs = {(p.left, p.right) for p in self.native_alias_pairs}
        if len(alias_pairs) != len(self.native_alias_pairs) or alias_pairs != {
            key for key, p in by_pair.items() if "native_alias_array" in p.candidate_routes
        }:
            raise ValueError("native alias pair ledger differs from candidate routes")
        for left, right in alias_pairs:
            a, b = by_id[left].artifact, by_id[right].artifact
            if (a.source_work, a.artifact_kind) != (b.source_work, b.artifact_kind) or not set(
                alias_tokens(a)
            ) & set(alias_tokens(b)):
                raise ValueError("native alias pair lacks compatible located alias evidence")
        return self
