"""Source-work-scoped artifact candidates; scores confer no equivalence authority."""
from __future__ import annotations

from itertools import combinations
from typing import Literal
import re

from pydantic import Field, model_validator
from rapidfuzz.fuzz import ratio

from .identity import canonical_bytes
from .structural_products import StructuralValue
from hashlib import sha256


class SourceArtifactOccurrence(StructuralValue):
    protocol: Literal['source-artifact-occurrence-1'] = 'source-artifact-occurrence-1'
    artifact_kind: Literal['table', 'figure', 'theorem', 'section']
    source_work: str = Field(min_length=1)
    controlled_code: str | None = None
    title: str | None = None
    aliases: tuple[str, ...] = ()
    revision: str | None = None
    revision_state: Literal['observed', 'unknown', 'malformed', 'unresolved'] = 'unknown'
    occurrence_role: Literal['caption', 'reference']
    scope: str = Field(min_length=1)
    source_pointer: str = Field(min_length=1)
    dependencies: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode='after')
    def provenance(self):
        if (self.revision is not None) != (self.revision_state == 'observed'):
            raise ValueError('only observed revisions carry an interpreted revision')
        if len(set(self.dependencies)) != len(self.dependencies):
            raise ValueError('artifact dependencies repeat')
        return self


class ArtifactRecord(StructuralValue):
    contribution_id: str = Field(min_length=1)
    occurrence_id: str = Field(min_length=1)
    artifact: SourceArtifactOccurrence


class ArtifactPair(StructuralValue):
    left: str
    right: str
    candidate_routes: tuple[str, ...] = Field(min_length=1)
    scope_state: Literal['compatible', 'excluded']
    revision_relation: Literal['same_observed', 'different_observed', 'unknown']
    lexical_score: float = Field(ge=0, le=1)
    model_probability: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    standing: Literal['candidate_relative_private'] = 'candidate_relative_private'
    dependencies: tuple[str, ...]


def normalized_code(code: str | None) -> str | None:
    """Only an observed source-local numeric identifier qualifies for exact evidence."""
    if code is None:
        return None
    value = code.strip()
    if not re.fullmatch(r'[A-Za-z]?\d+(?:[.\-]\d+)*[A-Za-z]?', value):
        return None
    return value.casefold()


def pair_candidates(records: tuple[ArtifactRecord, ...], *, external_pairs=(), title_threshold=70.0,
                    exclusions=()) -> tuple[ArtifactPair, ...]:
    """Retain generator provenance once per pair; never partition a whole component."""
    if not 0 <= title_threshold <= 100:
        raise ValueError('title threshold must be between zero and100')
    by_id = {r.contribution_id: r for r in records}
    if len(by_id) != len(records):
        raise ValueError('artifact record identifiers repeat')
    external = {tuple(sorted(p)) for p in external_pairs}
    forbidden = {tuple(sorted(p)) for p in exclusions}
    if any(len(p) != 2 or p[0] == p[1] or not set(p) <= by_id.keys() for p in external | forbidden):
        raise ValueError('pair endpoints must be distinct selected artifact records')
    result = []
    for left, right in combinations(sorted(by_id), 2):
        a, b = by_id[left], by_id[right]
        av, bv = a.artifact, b.artifact
        if a.occurrence_id == b.occurrence_id:
            continue
        compatible = (av.source_work, av.artifact_kind) == (bv.source_work, bv.artifact_kind)
        routes = []
        code_a, code_b = normalized_code(av.controlled_code), normalized_code(bv.controlled_code)
        if compatible and code_a is not None and code_a == code_b:
            routes.append('exact_code')
        lexical = ratio(av.title, bv.title) / 100 if av.title and bv.title else 0.0
        if compatible and av.title and bv.title and lexical * 100 >= title_threshold:
            routes.append('lexical_title')
        if compatible and set(av.aliases) & set(bv.aliases):
            routes.append('alias_array')
        if (left, right) in external:
            routes.append('external_pairs')
        if not routes:
            continue
        revision = ('unknown' if av.revision_state != 'observed' or bv.revision_state != 'observed'
                    else 'same_observed' if av.revision == bv.revision else 'different_observed')
        result.append(ArtifactPair(left=left, right=right, candidate_routes=tuple(routes),
            scope_state='compatible' if compatible and (left, right) not in forbidden else 'excluded',
            revision_relation=revision, lexical_score=lexical,
            dependencies=tuple(sorted(set((left, right, *av.dependencies, *bv.dependencies))))))
    return tuple(result)


class ArtifactScoringPolicy(StructuralValue):
    """Declared model assumptions, not calibrated source truth."""
    prior: float = Field(gt=0, lt=1)
    code_m: float = Field(gt=0, lt=1)
    code_u: float = Field(gt=0, lt=1)
    title_m: float = Field(gt=0, lt=1)
    title_u: float = Field(gt=0, lt=1)


def score_pairs(records: tuple[ArtifactRecord, ...], pairs: tuple[ArtifactPair, ...],
                policy: ArtifactScoringPolicy) -> tuple[ArtifactPair, ...]:
    """Score exactly the registered eligible pair IDs using a frozen Splink model."""
    import duckdb
    from splink import DuckDBAPI, Linker, SettingsCreator
    from splink.comparison_library import ExactMatch

    allowed = tuple(p for p in pairs if p.scope_state == 'compatible')
    if not allowed:
        return pairs
    source = {r.contribution_id: r for r in records}
    if any(p.left not in source or p.right not in source for p in allowed):
        raise ValueError('scored pair outside selected population')
    payload = [dict(unique_id=r.contribution_id, source_dataset='artifacts',
        controlled_code=normalized_code(r.artifact.controlled_code),
        title=r.artifact.title.casefold().strip() if r.artifact.title else None)
        for r in records]
    settings = SettingsCreator(link_type='dedupe_only',
        probability_two_random_records_match=policy.prior,
        comparisons=[ExactMatch('controlled_code').configure(
            m_probabilities=[policy.code_m, 1-policy.code_m],
            u_probabilities=[policy.code_u, 1-policy.code_u]),
            ExactMatch('title').configure(m_probabilities=[policy.title_m,1-policy.title_m],
                u_probabilities=[policy.title_u,1-policy.title_u])],
        retain_intermediate_calculation_columns=True)
    with duckdb.connect() as connection:
        api = DuckDBAPI(connection=connection)
        linker = Linker(api.register(payload, dataset_display_name="artifacts"), settings)
        table = linker.table_management.register_table([
            dict(join_key_l=p.left, join_key_r=p.right,
                 source_dataset_l='artifacts', source_dataset_r='artifacts', match_key='external')
            for p in allowed], 'owned_artifact_pairs')
        linker.table_management.register_blocked_pairs_for_predict(table)
        predicted = linker.inference.predict().as_record_list()
    probabilities = {tuple(sorted((r['unique_id_l'],r['unique_id_r']))):float(r['match_probability'])
                     for r in predicted}
    if set(probabilities) != {(p.left,p.right) for p in allowed}:
        raise ValueError('provider changed selected pair membership')
    return tuple(p.model_copy(update={'model_probability': probabilities[(p.left,p.right)]})
                 if p.scope_state == 'compatible' else p for p in pairs)


def pair_identity(pair: ArtifactPair) -> str:
    return sha256(canonical_bytes([pair.left,pair.right])).hexdigest()


def native_alias_candidates(records: tuple[ArtifactRecord, ...]) -> tuple[tuple[str, str], ...]:
    """Actual Splink array blocking; title-derived aliases must not be fabricated."""
    import duckdb
    from splink import DuckDBAPI, Linker, SettingsCreator, block_on

    eligible = [r for r in records if r.artifact.aliases]
    if len(eligible) < 2:
        return ()
    payload = [dict(unique_id=r.contribution_id, source_work=r.artifact.source_work,
                    artifact_kind=r.artifact.artifact_kind, aliases=list(r.artifact.aliases))
               for r in eligible]
    settings = SettingsCreator(link_type='dedupe_only', comparisons=[],
        blocking_rules_to_generate_predictions=[block_on('source_work','artifact_kind','aliases',
                                                        arrays_to_explode=['aliases'])])
    with duckdb.connect() as connection:
        api = DuckDBAPI(connection=connection)
        linker = Linker(api.register(payload,dataset_display_name='artifacts'),settings)
        blocked = linker.inference.compute_blocked_pairs_for_predict().as_record_list()
    return tuple(sorted({tuple(sorted((r['join_key_l'],r['join_key_r']))) for r in blocked}))
