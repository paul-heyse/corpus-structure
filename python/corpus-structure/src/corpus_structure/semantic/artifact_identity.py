"""Source-work-scoped artifact candidates; scores confer no equivalence authority."""

from __future__ import annotations

import re
from contextlib import contextmanager
from hashlib import sha256
from itertools import combinations
from typing import Literal

from pydantic import Field, JsonValue, model_validator
from rapidfuzz.fuzz import ratio

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


_ALIAS = re.compile(r'\s*\((?:alias:|also called|also known as)\s*"([^"\r\n]+)"\s*\)', re.I | re.ASCII)
_ALIAS_ABSENCE = re.compile(r'\s*\((aliases:\s*none)\s*\)', re.I | re.ASCII)


def source_alias_fields(text: str, artifact_end: int, source_pointer: str) -> dict:
    """Read explicit alias declarations attached to this exact artifact citation."""
    spans = []
    cursor = artifact_end
    while (match := _ALIAS.match(text, cursor)) is not None and match.group(1).strip():
        start, end = match.span(1)
        spans.append(dict(source_pointer=source_pointer, start=start, end=end, text=match.group(1)))
        cursor = match.end()
    if spans:
        return dict(
            aliases=tuple(span["text"] for span in spans),
            alias_state="observed",
            alias_occurrences=tuple(spans),
        )
    if (absence := _ALIAS_ABSENCE.match(text, artifact_end)) is not None:
        start, end = absence.span(1)
        return dict(
            aliases=(),
            alias_state="known_empty",
            alias_occurrences=(),
            alias_absence=dict(source_pointer=source_pointer, start=start, end=end, text=absence.group(1)),
        )
    return dict(aliases=(), alias_state="unknown", alias_occurrences=())


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


class ArtifactRecord(StructuralValue):
    contribution_id: str = Field(min_length=1)
    occurrence_id: str = Field(min_length=1)
    artifact: SourceArtifactOccurrence
    source_contribution: dict[str, JsonValue]
    citations: tuple[ArtifactCitation, ...] = Field(min_length=1)


class ArtifactModelField(StructuralValue):
    name: str = Field(min_length=1)
    value: float | None = Field(default=None, allow_inf_nan=False)


class ArtifactPairKey(StructuralValue):
    left: str = Field(min_length=1)
    right: str = Field(min_length=1)


class ArtifactNomination(ArtifactPairKey):
    relationship: RetainedContributionRef


ArtifactRoute = Literal["exact_code", "lexical_title", "external_pairs", "native_alias_array"]


class ArtifactPair(StructuralValue):
    left: str
    right: str
    candidate_routes: tuple[ArtifactRoute, ...] = Field(min_length=1)
    scope_state: Literal["compatible", "excluded"]
    revision_relation: Literal["same_observed", "different_observed", "unknown"]
    lexical_score: float = Field(ge=0, le=1)
    model_probability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    model_id: str | None = None
    model_evidence: tuple[ArtifactModelField, ...] = ()
    standing: Literal["candidate_relative_private"] = "candidate_relative_private"
    dependencies: tuple[str, ...]


def normalized_code(code: str | None) -> str | None:
    """Only an observed source-local numeric identifier qualifies for exact evidence."""
    if code is None:
        return None
    value = code.strip()
    if not re.fullmatch(r"[A-Za-z]?\d+(?:[.\-]\d+)*[A-Za-z]?", value):
        return None
    return value.casefold()


def pair_candidates(
    records: tuple[ArtifactRecord, ...],
    *,
    external_nominations: tuple[ArtifactNomination, ...] = (),
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
    alias = {(min(left, right), max(left, right)) for left, right in native_alias_pairs}
    forbidden = {(min(left, right), max(left, right)) for left, right in exclusions}
    if any(len(p) != 2 or p[0] == p[1] or not set(p) <= by_id.keys() for p in external.keys() | forbidden | alias):
        raise ValueError("pair endpoints must be distinct selected artifact records")
    anchors = frozenset(known_anchor_ids)
    if len(anchors) != len(known_anchor_ids) or not anchors <= by_id.keys():
        raise ValueError("known anchors must be distinct exact selected artifact records")
    from .identity_resolution import constrained_label_groups

    result = []
    for left, right in combinations(sorted(by_id), 2):
        a, b = by_id[left], by_id[right]
        av, bv = a.artifact, b.artifact
        if a.occurrence_id == b.occurrence_id:
            continue
        compatible = (av.source_work, av.artifact_kind) == (bv.source_work, bv.artifact_kind)
        routes: list[ArtifactRoute] = []
        code_a, code_b = normalized_code(av.controlled_code), normalized_code(bv.controlled_code)
        if compatible and code_a is not None and code_a == code_b:
            routes.append("exact_code")
        lexical = ratio(av.title, bv.title) / 100 if av.title and bv.title else 0.0
        if compatible and av.title and bv.title and lexical * 100 >= title_threshold:
            routes.append("lexical_title")
        if (left, right) in external:
            routes.append("external_pairs")
        if (left, right) in alias:
            if not compatible or not set(alias_tokens(av)) & set(alias_tokens(bv)):
                raise ValueError("native alias pair lacks compatible observed aliases")
            routes.append("native_alias_array")
        if not routes:
            continue
        revision = (
            "unknown"
            if av.revision_state != "observed" or bv.revision_state != "observed"
            else "same_observed"
            if av.revision == bv.revision
            else "different_observed"
        )
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
        result.append(
            ArtifactPair(
                left=left,
                right=right,
                candidate_routes=tuple(routes),
                scope_state="compatible" if compatible and permitted else "excluded",
                revision_relation=revision,
                lexical_score=lexical,
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
    allowed = tuple((p.left, p.right) for p in pairs if p.scope_state == "compatible")
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
                "model_probability": float(probabilities[(p.left, p.right)]["match_probability"]),
                "model_id": policy.identity,
                "model_evidence": tuple(
                    ArtifactModelField(name=key, value=value)
                    for key, value in probabilities[(p.left, p.right)].items()
                    if key.startswith(("gamma_", "mw_", "tf_"))
                ),
            }
        )
        if p.scope_state == "compatible"
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

    eligible = [r for r in records if r.artifact.aliases]
    if len(eligible) < 2:
        return (), ()
    payload = [
        dict(
            unique_id=r.contribution_id,
            source_work=r.artifact.source_work,
            artifact_kind=r.artifact.artifact_kind,
            aliases=list(alias_tokens(r.artifact)),
        )
        for r in eligible
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
        counts = (
            tuple(dict(row) for row in linker.blocking_analysis.count_comparisons_from_blocking_rules(
                record_sample_proportion=1.0
            ))
            if count_rules
            else ()
        )
    pairs = tuple(
        sorted(
            {
                (min(row["join_key_l"], row["join_key_r"]), max(row["join_key_l"], row["join_key_r"]))
                for row in blocked
            }
        )
    )
    return pairs, counts


class ArtifactIdentityProduct(StructuralValue):
    """One selected source-work cohort, candidate routes and frozen model results."""

    protocol: Literal["artifact-identity-2"] = "artifact-identity-2"
    identity_grain: Literal["source_work_artifact_lineage"] = "source_work_artifact_lineage"
    records: tuple[ArtifactRecord, ...] = ()
    pairs: tuple[ArtifactPair, ...] = ()
    native_alias_pairs: tuple[ArtifactPairKey, ...] = ()
    external_nominations: tuple[ArtifactNomination, ...] = ()
    policy: ArtifactScoringPolicy
    source_mapping_provenance: tuple[str, ...] = ()
    known_anchor_ids: tuple[str, ...] = ()
    unbound_source_ids: tuple[int, ...] = ()
    standing: Literal["candidate_relative_private"] = "candidate_relative_private"

    @model_validator(mode="after")
    def membership(self):
        by_id = {r.contribution_id: r for r in self.records}
        if len(by_id) != len(self.records):
            raise ValueError("identity record identifiers repeat")
        anchors = frozenset(self.known_anchor_ids)
        if len(anchors) != len(self.known_anchor_ids) or not anchors <= by_id.keys():
            raise ValueError("known anchors must be distinct selected artifact records")
        by_pair = {(p.left, p.right): p for p in self.pairs}
        if len(by_pair) != len(self.pairs):
            raise ValueError("identity pairs repeat")
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
            if pair.model_probability is not None and (
                pair.scope_state != "compatible" or pair.model_id != self.policy.identity
            ):
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
        if nominated != {key for key, p in by_pair.items() if "external_pairs" in p.candidate_routes}:
            raise ValueError("external pair route lacks an authenticated nomination")

        alias_pairs = {(p.left, p.right) for p in self.native_alias_pairs}
        if len(alias_pairs) != len(self.native_alias_pairs) or alias_pairs != {
            key for key, p in by_pair.items() if "native_alias_array" in p.candidate_routes
        }:
            raise ValueError("native alias pair ledger differs from candidate routes")
        for left, right in alias_pairs:
            a, b = by_id[left].artifact, by_id[right].artifact
            if (
                (a.source_work, a.artifact_kind) != (b.source_work, b.artifact_kind)
                or not set(alias_tokens(a)) & set(alias_tokens(b))
            ):
                raise ValueError("native alias pair lacks compatible located alias evidence")
        return self
