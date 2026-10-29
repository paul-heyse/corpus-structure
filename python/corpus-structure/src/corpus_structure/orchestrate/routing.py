"""The phase-zero propose chain over recorded inputs (O2, D6 §7)."""
from __future__ import annotations

from collections import Counter
from typing import Any
from types import SimpleNamespace

from sqlalchemy import Connection, select, text
from sqlalchemy.dialects.postgresql import insert

from corpus_structure.core.db import metadata
from corpus_structure.core.locators import LocatorIndex
from corpus_structure.core.vocab import PolicyChain, SkipReason, Stage, StatementKind, TOP_LEVEL_ANNOTATION_UNIT
from corpus_structure.orchestrate import agent, context, policy, runs, tasks
from corpus_structure.orchestrate.registry import RunConfigs
from corpus_structure.orchestrate.runner import unit_view
from corpus_structure.orchestrate.slices import selected
from corpus_structure.schema.registry import compiled_for


def propose(conn: Connection, run_id: int, registry: Any) -> None:
    run = conn.execute(text('SELECT schema_version_id, policy_version_id, phase FROM ops.run WHERE id=:r'), {'r': run_id}).one()
    compiled = compiled_for(conn, run.schema_version_id)
    enums = compiled.lookup.version_sets['StatementKind']
    language = policy.unit_language([m.stored for m in enums.members], policy.registry_configs(registry))
    source = conn.execute(text('SELECT source FROM ops.policy_version WHERE id=:p'), {'p': run.policy_version_id}).scalar_one()
    rules = policy.compile_policy(policy.parse_policy(source), language, policy.registry_configs(registry))
    table = metadata.tables['ops.policy_rule']
    rule_ids = {}
    for entry in rules.entries(PolicyChain.PROPOSE):
        action = entry.entry.do.model_dump(mode='json', exclude_none=True)
        stmt = insert(table).values(policy_version_id=run.policy_version_id, rule_key=entry.key,
            chain=entry.chain.value, priority=entry.priority, unit_type=entry.unit_type.value,
            condition=entry.entry.when, action=action, enabled=True).on_conflict_do_nothing()
        conn.execute(stmt)
        rule_ids[entry.key] = conn.execute(select(table.c.id).where(table.c.policy_version_id==run.policy_version_id, table.c.rule_key==entry.key)).scalar_one()
    view = context.run_view(conn, run_id)
    options = runs.stored_options(conn, run_id)
    scope = options.scope if isinstance(options.scope, dict) else None
    raw_locators = scope.get('locators') if scope is not None else None
    locators = [str(x) for x in raw_locators] if isinstance(raw_locators, list) else None
    configs = RunConfigs(registry, conn, options.configs)
    indices = {}
    counters: Counter[str] = Counter()
    scheduled: set[tuple[int | None, str]] = set()
    matched_units: dict[str, list[str]] = {}
    for entry in rules.entries(PolicyChain.PROPOSE):
        method = registry.method(entry.method)
        name = options.method_configs.get(entry.method, entry.entry.do.method.split('/',1)[1])
        if '/' in name:
            name = name.split('/',1)[1]
        rc = configs.config(entry.method, name)
        units = [unit_view(conn, view, ref) for ref in method.select(view, rc.config)]
        for unit in units:
            if unit.rendition_id is None or unit.document_id is None or unit.ref.unit_key is None:
                raise ValueError('propose units require rendition, document and unit key')
            if unit.rendition_id not in indices:
                from corpus_structure.methods.llm.agent_opus import page_of
                content = view.reader.content(unit.rendition_id)
                index = LocatorIndex(content, page_of(conn, unit.document_id))
                indices[unit.rendition_id] = (index, selected(index, locators))
            index, in_scope = indices[unit.rendition_id]
            segment = index.resolve(unit.ref.unit_key)
            hint = segment.attrs.get('hint', {})
            hint = hint if isinstance(hint, dict) else {}
            fallback = StatementKind.NARRATIVE if segment.kind in TOP_LEVEL_ANNOTATION_UNIT else StatementKind.REMARK
            kind = hint.get('statement_kind', fallback.value)
            bearing = hint.get('claim_bearing')
            if bearing is None:
                bearing = kind in enums.property('claim_bearing')
            thing = {'phase': run.phase, 'iteration': 0,
                'unit': SimpleNamespace(kind=segment.kind.value, statement_kind=kind, claim_bearing=bool(bearing)),
                'target': SimpleNamespace(kind=None,size=None,max_confidence=None,margin=None),
                'budget': SimpleNamespace(agent_packets_left=None,llm_tokens_left=None),
                'ran':lambda m:False,'outcome':lambda m:None,'judged_by':lambda m:False,
                'decision':lambda m:None,'confidence':lambda m:None}
            matched = matched_units.setdefault(unit.ref.unit_key, [e.key for e in rules.matches(PolicyChain.PROPOSE, thing)])
            identity = (rc.method_config_id, unit.ref.unit_key)
            if entry.key not in matched or identity in scheduled:
                continue
            reason = None
            if unit.ref.unit_key not in in_scope:
                reason = SkipReason.SCOPE
            elif entry.entry.do.limit is not None and counters[entry.key] >= entry.entry.do.limit:
                reason = SkipReason.LIMIT
            else:
                counters[entry.key] += 1
            scheduled.add(identity)
            trigger = {'values': {'phase': run.phase, 'iteration': 0,
                'unit.kind': segment.kind.value, 'unit.statement_kind': kind,
                'unit.claim_bearing': bool(bearing)}}
            tasks.create_tasks(conn, run_id, Stage.PROPOSE, rc, method, [unit],
                skipped={0:reason} if reason else {}, upstream=('ingest.html','resolve.symbol_scope'),
                fresh=entry.method in options.fresh, trigger_rule_id=rule_ids[entry.key],
                trigger_metrics=trigger)
    agent.settle_twins(conn, run_id=run_id)
