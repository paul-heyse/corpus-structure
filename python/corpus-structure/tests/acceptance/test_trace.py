"""C3's deterministic journey through real stages, MCP submission and typed queries."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.intervene.server import build_server
from corpus_structure.intervene.service import Session
from corpus_structure.intervene.testing import submit_batches
from corpus_structure.orchestrate import phase0, project
from corpus_structure.serve.journey import coverage, serve_query
from corpus_structure.serve.protocol import Scope

REPO = Path(__file__).resolve().parents[4]
UNITS = ("T1-leadin", "T1-dfn1", "T2", "T3", "T4")


def fixtures() -> dict[str, Any]:
    return {name: json.loads((REPO / "fixtures/s0" / f"{name}.json").read_text()) for name in UNITS}


def snapshot(conn: Any, run: int, aliases: dict[str, str]) -> Any:
    """Physical ids differ between projects; model keys and semantic rows must agree."""
    entities = conn.execute(text(
        "SELECT key,type,label,scope,kind,attrs FROM kb.entity WHERE run_id=:r ORDER BY key"
    ), {"r": run}).all()
    claims = conn.execute(text(
        "SELECT c.key,c.predicate,s.key,o.key,c.object_value,c.qualifiers,c.modality,c.polarity,c.status "
        "FROM kb.claim c JOIN kb.entity s ON s.id=c.subject_id "
        "LEFT JOIN kb.entity o ON o.id=c.object_entity_id WHERE c.run_id=:r ORDER BY c.key"
    ), {"r": run}).all()
    links = conn.execute(text(
        "SELECT a.key,l.link_type,b.key,l.detail FROM kb.claim_link l "
        "JOIN kb.claim a ON a.id=l.from_claim_id JOIN kb.claim b ON b.id=l.to_claim_id "
        "WHERE l.run_id=:r ORDER BY a.key,l.link_type,b.key"
    ), {"r": run}).all()
    return normalize_ids([[list(row) for row in group] for group in (entities, claims, links)], aliases)


def normalize_ids(value: Any, aliases: dict[str, str]) -> Any:
    if isinstance(value, str): return aliases.get(value, value)
    if isinstance(value, dict):
        return {k: normalize_ids(v, aliases) for k,v in value.items()}
    if isinstance(value, (list, tuple)):
        return [normalize_ids(v, aliases) for v in value]
    return value


def namespace_ids(conn: Any, run: int) -> dict[str, str]:
    # D1 deliberately scopes document identity to the project NAME. Compare local
    # identities by source and anchor structure across these distinct namespaces;
    # global keys remain literal and must agree. No key scheme is changed here.
    rows = conn.execute(text(
        "SELECT e.key,e.type,e.scope,e.label,e.statement_ordinal,s.kind,s.start_offset,s.end_offset,d.source_uri "
        "FROM kb.entity e LEFT JOIN kb.segment s ON s.id=e.scope_segment_id "
        "LEFT JOIN kb.rendition r ON r.id=s.rendition_id LEFT JOIN kb.document d ON d.id=r.document_id "
        "WHERE e.run_id=:r"), {"r":run}).all()
    aliases = {r.key: json.dumps(list(r)[1:], ensure_ascii=False) for r in rows if r.scope == "local"}
    segments = conn.execute(text(
        "SELECT s.key,d.source_uri,s.kind,s.start_offset,s.end_offset FROM kb.segment s "
        "JOIN kb.run_rendition rr ON rr.rendition_id=s.rendition_id "
        "JOIN kb.document d ON d.id=rr.document_id WHERE rr.run_id=:r"), {"r":run}).all()
    aliases.update({r[0]: json.dumps(list(r)[1:]) for r in segments})
    for unit in ("T1", "T2", "T3", "T4"):
        target = json.loads((REPO / "fixtures/trace" / f"{unit}.target.json").read_text())
        keyed = target_keys(conn,run,target)
        for ref,key in keyed.claims.items(): aliases.setdefault(key, f"{unit}:{ref}")
    c = conn.execute(text("SELECT key,predicate,subject_id,object_value FROM kb.claim WHERE run_id=:r"), {"r":run}).all()
    entity_ids = dict(conn.execute(text("SELECT id,key FROM kb.entity WHERE run_id=:r"), {"r":run}).all())
    for row in c:
        aliases.setdefault(row.key, json.dumps([row.predicate, aliases.get(entity_ids[row.subject_id], entity_ids[row.subject_id]), row.object_value],sort_keys=True))
    return aliases


def target_keys(conn: Any, run: int, target: dict[str, Any]) -> Any:
    # The authored target is independent of the proposals and consolidation. Only the
    # established locator/canonical-key primitives are shared, never the pass or queries.
    import yaml
    from corpus_structure.core import tex
    from corpus_structure.core.batch import AuthoredBatch, CitationFrame
    from corpus_structure.core.db import repo
    from corpus_structure.core.keys import KeyContext, key_claims
    from corpus_structure.consolidate.pass_ import ConsolidateConfig
    from corpus_structure.methods.llm.parse import RenditionView, parse
    from corpus_structure.schema.compile import compile_paths
    from corpus_structure.validate.adapter import candidates_from_batch

    compiled = compile_paths([REPO / "domains/statistics"])
    cfg = ConsolidateConfig.model_validate({k: v for k, v in yaml.safe_load(
        (REPO / "domains/statistics/methods.yaml").read_text()).items() if k in {"aliases", "math"}})
    rid, doc = conn.execute(text(
        "SELECT rr.rendition_id,d.key FROM kb.run_rendition rr JOIN kb.document d ON d.id=rr.document_id "
        "WHERE rr.run_id=:r AND d.source_uri=:uri"),
        {"r": run, "uri": "siegrist_random/random/" + target["page"]}).one()
    content = repo.read_rendition(conn, rid)
    macros = tex.effective_macros(content.macros, cfg.macros())
    ctx = KeyContext(doc, content, target["page"], macros)
    stored = parse(RenditionView(content, target["page"], ctx.rendition_key, macros),
                   AuthoredBatch.model_validate(target["batch"]),
                   CitationFrame.model_validate(target["frame"]), compiled.names.to_prefixed).stored
    return key_claims(candidates_from_batch(stored, compiled), ctx, compiled.key_schema,
                      cfg.labels(compiled.names.to_prefixed))


def returned_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys = {value["key"]} if isinstance(value.get("key"), str) else set()
        return keys | set().union(*(returned_keys(v) for v in value.values()))
    if isinstance(value, list):
        return set().union(*(returned_keys(v) for v in value))
    return set()


def claim_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        own = [value] if "predicate" in value else []
        return own + [r for v in value.values() for r in claim_rows(v)]
    if isinstance(value, list):
        return [r for v in value for r in claim_rows(v)]
    return []


def matches(value: Any, pattern: dict[str, Any], refs: dict[str, str]) -> bool:
    """Independent interpretation of the hand-authored forbidden-result patterns."""
    from corpus_structure.core.tex import token_form
    if not isinstance(value, dict):
        return value == refs.get(pattern.get("ref")) if "ref" in pattern else False
    if set(pattern) == {"ref"}:
        return value.get("key", value.get("ref")) == refs[pattern["ref"]]
    for field, wanted in pattern.items():
        if field == "kind":
            continue
        if field in {"condition", "lacks_condition"}:
            def nodes(v: Any) -> Any:
                if isinstance(v, dict):
                    yield v
                    for child in v.values(): yield from nodes(child)
                elif isinstance(v, list):
                    for child in v: yield from nodes(child)
            found = any(matches(node, wanted, refs) for node in nodes(value.get("conditions")))
            if found != (field == "condition"): return False
            continue
        if field in {"param_values", "param_value"}:
            values = value.get("qualifiers", {}).get("stat:param_values", {})
            if isinstance(values, list): values = {x["key"]: x["value"] for x in values}
            if field == "param_value":
                if not any(matches(v, wanted, refs) for v in values.values()): return False
            elif not all(k in values and matches(values[k], v, refs) for k,v in wanted.items()): return False
            continue
        actual = value.get(field)
        if field == "ref":
            if actual != refs[wanted]: return False
        elif field == "identity":
            if not isinstance(actual, dict): return False
            for slot, expected in wanted.items():
                got = actual.get("stat:" + slot, actual.get(slot))
                if isinstance(expected, dict):
                    if not matches(got, expected, refs): return False
                elif got != expected: return False
        elif isinstance(wanted, dict):
            if not matches(actual, wanted, refs): return False
        elif field in {"type", "predicate"}:
            if not isinstance(actual,str) or actual.split(":")[-1] != wanted.split(":")[-1]: return False
        elif field == "latex":
            if not isinstance(actual,str) or token_form(actual,{}) != token_form(wanted,{}): return False
        elif actual != wanted:
            return False
    return True


def journey(engine: Any, tmp: Path, name: str, cli: Any, *, reverse: bool = False, desired_order: list[str] | None = None) -> dict[str, Any]:
    from corpus_structure.orchestrate.testing import run_to_completion
    from corpus_structure.serve.registry import build_registry

    pack = REPO / "domains/statistics"
    registry = phase0.registry(pack)
    with engine.begin() as conn:
        initialized = project.init_project(conn, domain="statistics", corpus=REPO / "fixtures/trace/corpus",
                                           registry=registry, name=name)
    url = engine.url.set(drivername="postgresql").render_as_string(hide_password=False)
    from corpus_structure.consolidate import run_pass
    reports = []
    def recording_pass(*args: Any) -> Any:
        report = run_pass(*args)
        reports.append(report)
        return report
    # The existing expectation role isolates the reverse journey's task custody from
    # the forward project's completed cache entries while preserving packet content.
    explicit = {"method_configs": {"agent.opus": "expectation"}} if reverse else {}
    args = dict(url=url, project_name=name, slice="trace", run_pass=recording_pass,
                explicit=explicit, method_settings=MethodSettings(data_dir=tmp, model_cache=tmp))
    first = run_to_completion(engine, **args)
    assert first.status == "finished"
    with engine.connect() as conn:
        before = coverage(conn, first.run_id, Scope.run())
        assert before.unresolved == 5
    data = fixtures()
    batches = {r["unit_key"]: (r["batch"], r["frame"]) for r in data.values()}
    if reverse:
        with engine.begin() as conn:
            tasks = conn.execute(text("SELECT id,unit_key FROM ops.task WHERE run_id=:r AND stage='propose' "
                                      "AND status='awaiting_agent' ORDER BY id"), {"r": first.run_id}).all()
            priorities = {key: len(desired_order or []) - i for i,key in enumerate(desired_order or [])}
            for task_id, unit_key in tasks:
                priority = priorities[unit_key]
                conn.execute(text("UPDATE ops.task SET priority=:p WHERE id=:t"), {"p": priority, "t": task_id})
    server = build_server(Session(engine))
    submitted = submit_batches(server, first.run_id, batches)
    assert len(submitted) == 5
    for result in submitted.values():
        assert result.status == "done" and result.accepted and not result.rejected and not result.dropped and not result.findings
    with engine.connect() as conn:
        assert coverage(conn, first.run_id, Scope.run()) == before
    second = run_to_completion(engine, **args)
    assert second.status == "finished"
    from corpus_structure.serve.queries import GENERIC
    queries = build_registry(GENERIC, pack)
    answers = []
    with engine.connect() as conn:
        units = Scope.of_units(tuple(batches))
        assert coverage(conn, second.run_id, units).extracted == 5
        assert len(reports[-1].consumed) == coverage(conn, second.run_id, units).extracted
        assert set(reports[-1].consumed) == {result.task_id for result in submitted.values()}
        assert not coverage(conn, second.run_id, units).partial
        for unit in ("T1", "T2", "T3", "T4"):
            target = json.loads((REPO / "fixtures/trace" / f"{unit}.target.json").read_text())
            keyed = target_keys(conn, second.run_id, target)
            expected = keyed.entities | keyed.statements | keyed.claims
            all_claims = serve_query(conn, queries, "claims", {"include_suppositions": True},
                                     run=second.run_id, max_chars=1_000_000).rows
            all_entities = serve_query(conn, queries, "entity", {}, run=second.run_id,
                                       max_chars=1_000_000).rows
            for forbidden in target["must_not"]:
                values = all_entities if forbidden["pattern"]["kind"] == "entity" else all_claims
                assert not any(matches(row, forbidden["pattern"], expected) for row in values), forbidden
            for question in target["questions"]:
                answer = serve_query(conn, queries, question["query"], question["params"],
                                     run=second.run_id, max_chars=1_000_000)
                assert answer.rows, question
                got = returned_keys(answer.rows)
                assert {expected[ref] for ref in question["returns"]} <= got, question
                if question.get("returns_with_suppositions"):
                    with_premises = serve_query(conn, queries, question["query"],
                        {**question["params"], "include_suppositions": True},
                        run=second.run_id, max_chars=1_000_000)
                    assert {expected[ref] for ref in question["returns_with_suppositions"]} <= returned_keys(with_premises.rows), (question, with_premises.model_dump(mode="json"), reports[-1])
                assert all(row["evidence"] for row in claim_rows(answer.rows))
                from corpus_structure.settings import Settings
                command = ["query", question["query"], "--run", str(second.run_id),
                           "--json", "--max-chars", "1000000"]
                for key, value in question["params"].items():
                    command += ["--param", f"{key}={value}"]
                result = cli(*command, settings=lambda: Settings(database={"url": url}))
                assert result.exit_code == 0, result.output
                assert json.loads(result.stdout) == answer.model_dump(mode="json")
                answers.append((question["query"], question["params"], answer.rows))
        fates = conn.execute(text("SELECT status,count(*) FROM ops.task WHERE run_id=:r AND stage='propose' "
                                  "AND unit_key=ANY(:u) GROUP BY status"),
                             {"r": second.run_id, "u": list(batches)}).all()
        assert fates == [("reused", 5)]
        hashes = conn.execute(text("SELECT unit_key,packet_hash FROM ops.task WHERE run_id=:r "
                                  "AND stage='propose' AND unit_key=ANY(:u) ORDER BY unit_key"),
                              {"r": second.run_id, "u": list(batches)}).all()
        aliases = namespace_ids(conn, second.run_id)
        knowledge = snapshot(conn, second.run_id, aliases)
        knowledge = [sorted(group, key=lambda row: json.dumps(row, sort_keys=True)) for group in knowledge]
        answers = normalize_ids(answers, aliases)
        # Query ordering is pinned-run deterministic; cross-project identifiers have
        # different hashes, so compare the logical row sets across namespaces.
        answers = [(name, params, sorted(rows, key=lambda row: json.dumps(row, sort_keys=True)))
                   for name, params, rows in answers]
    return dict(run=second.run_id, project=initialized.project_id, knowledge=knowledge,
                hashes=hashes, answers=answers, order=list(submitted))


def test_trace_journey_and_reverse_submission(committing_db: Any, tmp_path: Path, cli: Any) -> None:
    a = journey(committing_db, tmp_path, "trace-forward", cli)
    b = journey(committing_db, tmp_path, "trace-reverse", cli, reverse=True, desired_order=list(reversed(a["order"])))
    assert b["order"] == list(reversed(a["order"]))
    assert a["knowledge"] == b["knowledge"]
    assert a["hashes"] == b["hashes"]
    assert a["answers"] == b["answers"]
    # Return to the ordinary extraction role: reuse can select forward-project
    # observations. They must map by source identity onto this run's documents.
    from corpus_structure.consolidate import run_pass
    from corpus_structure.orchestrate.testing import run_to_completion
    reports = []
    def recording_pass(*args: Any) -> Any:
        report = run_pass(*args)
        reports.append(report)
        return report
    reused = run_to_completion(committing_db,
        url=committing_db.url.set(drivername="postgresql").render_as_string(hide_password=False),
        project_name="trace-reverse", slice="trace", run_pass=recording_pass,
        method_settings=MethodSettings(data_dir=tmp_path, model_cache=tmp_path))
    assert reused.status == "finished"
    assert len(reports[-1].consumed) == 5 and "unreadable_proposal" not in reports[-1].drops
    with committing_db.connect() as conn:
        aliases = namespace_ids(conn, reused.run_id)
        actual = snapshot(conn, reused.run_id, aliases)
        assert [sorted(group, key=lambda row: json.dumps(row, sort_keys=True)) for group in actual] == a["knowledge"]
