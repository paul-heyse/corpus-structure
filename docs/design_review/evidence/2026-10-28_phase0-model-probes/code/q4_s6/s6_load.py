"""Copy of S6's ``code/s6_load.py`` (design-spikes, 2026-10-28) for probe Q-4. One patch: ``EVIDENCE`` names the
design-spikes folder, whose results (S1 pages, the v1 reference, the schema sources) are read as data; no
spike module is imported. Original docstring follows.

S6 row loader (brief step 3): the spike pages and the v1 reference as D3 rows.

Used by ``s6b_rows.py`` (and later packages). Loads into ``cs_spike_s6`` (DDL already applied):

- project, schema version (the spike's ``code/schema`` sources), guideline v1, methods and
  configurations, a policy version with one escalation rule, a debug slice;
- run 1: a finished ``slice`` run over the four spike pages, promoted;
- the four documents (and the Weibull page's document, for its ``reserved`` split), their
  renditions, segments (S1 blocks and the provisional sentences the samples use), ingest tasks
  and rendition builds;
- per core unit of the v1 reference (``results/s0r2/reference_v1``, stored form): a ``propose``
  task (M24 configuration) whose one ``claim_proposal`` observation holds the stored batch, then the
  unit's statements, entities (global entities merged across units), aliases, anchors, mentions,
  claims, evidence spans and supports; plus one derived claim with a ``derived_from`` link (T3's D1
  of D3 §10), since the reference holds no links;
- the golden run (kind ``golden``, parent run 1) over a dev golden set of the twelve core units:
  pass ``a`` = pass SV, pass ``b`` = pass HV, then pass ``c`` = the v1 reference
  (model-facing, with its decisions), each a ``golden_unit`` task, the pass ``c`` task created after
  both; the pass ``c`` items derived onto the authored rendition with ``context`` set on
  context-premise items; document splits (four ``dev`` pages, Weibull ``reserved``).

Keys are **placeholders**: ``prefix:sha256(canonical JSON of the item's parts)[:32]``, unique per run,
global entities merged by (type, identity, normalized label). They are not the D1 §10.1 keys,
which S6-F computes; nothing here depends on how keys are derived.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from psycopg.types.json import Jsonb

EVIDENCE = Path(__file__).resolve().parents[3] / "2026-10-28_design-spikes"  # patched: data source, read only
S1 = EVIDENCE / "results" / "s1"
S0R2 = EVIDENCE / "results" / "s0r2"
SAMPLE = json.loads((EVIDENCE / "sample.json").read_text())
SAMPLE2 = json.loads((S0R2 / "sample.json").read_text())
RENDITIONS = json.loads((S1 / "renditions.json").read_text())
CORE = ["T1", "T2", "T3", "T4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12"]
PAGES = ["special/LocationScale.html", "special/Normal.html", "special/LogNormal.html", "special/Gamma.html"]
T0 = datetime(2026, 10, 28, 9, 0, tzinfo=timezone.utc)


def cj(x) -> str:
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(x) -> str:
    return hashlib.sha256((x if isinstance(x, str) else cj(x)).encode()).hexdigest()


def key(prefix: str, parts) -> str:
    return f"{prefix}:{sha(parts)[:32]}"


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


REPO = EVIDENCE.parents[3]
CORPUS = REPO / "docs" / "statistics_corpus" / "corpus"


def doc_hash(source_uri: str) -> str:
    """sha256 of the original bytes (D3 kb.document.content_hash)."""
    return hashlib.sha256((CORPUS / source_uri).read_bytes()).hexdigest()


def _name(page: str) -> str:
    return page.replace("/", "__").removesuffix(".html")


def predicate_prefixes() -> dict[str, str]:
    out = {}
    for f, p in (("core.yaml", "core"), ("statistics.yaml", "stat")):
        y = yaml.safe_load((EVIDENCE / "code" / "schema" / f).read_text())
        for s in (y.get("slots") or {}):
            out.setdefault(s, p)
    return out


def page_segments(page: str) -> tuple[str, list[dict]]:
    text = (S1 / "canonical" / f"{_name(page)}.txt").read_text()
    segs = [json.loads(x) for x in (S1 / "segments" / f"{_name(page)}.jsonl").read_text().splitlines()]
    segs += [json.loads(x) for x in (S1 / "sentences" / f"{_name(page)}.provisional.jsonl").read_text().splitlines()]
    return text, segs


class Loader:
    def __init__(self, conn):
        self.c = conn
        self.prefix = predicate_prefixes()
        self.ids: dict[str, int] = {}          # named rows: project, run1, configs, ...
        self.seg_id: dict[str, int] = {}       # segment key -> id
        self.seg_rows: dict[str, list[dict]] = {}  # page -> segments with offsets
        self.ren_id: dict[str, int] = {}       # page -> rendition id
        self.doc_id: dict[str, int] = {}
        self.text: dict[str, str] = {}
        self.report: dict = {}

    def one(self, sql, params=()):
        return self.c.execute(sql, params).fetchone()[0]

    # -- meta and ops scaffolding ------------------------------------------------------------
    def scaffold(self):
        i = self.ids
        i["project"] = self.one("INSERT INTO meta.project (name, domain) VALUES ('cs_spike_s6', 'statistics') RETURNING id")
        source = {f: (EVIDENCE / "code" / "schema" / f).read_text() for f in ("statistics.yaml", "core.yaml")}
        i["schema"] = self.one(
            "INSERT INTO meta.schema_version (project_id, domain, label, content_hash, source, created_by) "
            "VALUES (%s, 'statistics', '0.1.0', %s, %s, 'agent:opus-5.5') RETURNING id",
            (i["project"], sha(source), Jsonb(source)))
        g = (EVIDENCE / "s0r2" / "guideline_v1.md").read_text()
        i["guideline"] = self.one(
            "INSERT INTO meta.guideline_version (project_id, domain, label, content_hash, body, schema_version_id, created_by) "
            "VALUES (%s, 'statistics', 'v1', %s, %s, %s, 'agent:opus-5.5') RETURNING id",
            (i["project"], sha(g), g, i["schema"]))
        methods = [("ingest.html", "1", "ingest"), ("agent.opus", "1", "agent"), ("consolidate.claims", "1", "consolidate"),
                   ("golden.pass", "1", "agent"), ("validate.rules", "1", "validate"), ("extract.gliner_schema", "1", "extract")]
        for name, ver, fam in methods:
            mid = self.one("INSERT INTO ops.method (name, version, family) VALUES (%s, %s, %s) RETURNING id", (name, ver, fam))
            cfgs = {"golden.pass": ["a", "b", "c"]}.get(name, ["default"])
            for cn in cfgs:
                params = {"method": name, "config": cn}
                if name == "ingest.html":
                    params = RENDITIONS[PAGES[0]]["config"]
                tier = {"ingest": "deterministic", "agent": "agent", "consolidate": "deterministic", "validate": "deterministic",
                        "extract": "encoder"}[fam]
                i[f"cfg:{name}/{cn}"] = self.one(
                    "INSERT INTO ops.method_config (method_id, name, params, config_hash, tier) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                    (mid, cn, Jsonb(params), key("cfg", params | {"_m": name}), tier))
        pol = "propose:\n  - agent.opus/default\nescalate:\n  - low_confidence: agent.opus/default\n"
        i["policy"] = self.one(
            "INSERT INTO ops.policy_version (project_id, label, content_hash, source, created_by) VALUES (%s, 'p0', %s, %s, 'human:operator') RETURNING id",
            (i["project"], sha(pol), pol))
        i["rule"] = self.one(
            "INSERT INTO ops.policy_rule (policy_version_id, rule_key, chain, priority, unit_type, condition, action) "
            "VALUES (%s, 'escalate.low_confidence.agent', 'escalate', 1, 'segment', 'claims.min_confidence < 0.5', %s) RETURNING id",
            (i["policy"], Jsonb({"method": "agent.opus/default", "limit": 50, "then": "stop"})))
        i["slice"] = self.one(
            "INSERT INTO ops.debug_slice (project_id, name, selector) VALUES (%s, 'spike-pages', %s) RETURNING id",
            (i["project"], Jsonb({"pages": PAGES})))

    def run(self, name, kind, status="finished", parent=None, started=T0, finished=T0 + timedelta(hours=1), reference=None):
        corpus = [(RENDITIONS[p]["document_key"], doc_hash(RENDITIONS[p]["source_uri"])) for p in PAGES]
        rid = self.one(
            "INSERT INTO ops.run (project_id, kind, phase, options, debug_slice_id, corpus_hash, schema_version_id, guideline_version_id, "
            "policy_version_id, code_commit, parent_run_id, reference_run_id, status, started_at, finished_at) "
            "VALUES (%s, %s, 0, %s, %s, %s, %s, %s, %s, '35ea59a', %s, %s, %s, %s, %s) RETURNING id",
            (self.ids["project"], kind, Jsonb({"corpus": "spike-pages"}), self.ids["slice"],
             sha({"corpus": sorted(corpus), "ingest": RENDITIONS[PAGES[0]]["config_hash"]}), self.ids["schema"], self.ids["guideline"],
             self.ids["policy"], parent, reference, status, started, finished))
        self.ids[name] = rid
        return rid

    def task(self, run, stage, unit_type, unit_id, unit_key, cfg, status="done", finished=None, created=None, **kw):
        cols = {"run_id": run, "stage": stage, "unit_type": unit_type, "unit_id": unit_id, "unit_key": unit_key,
                "method_config_id": self.ids[cfg], "input_hash": kw.pop("input_hash", sha([stage, unit_key, cfg])),
                "status": status, "finished_at": finished or (T0 + timedelta(minutes=10)), "created_at": created or T0,
                "started_at": T0 + timedelta(minutes=1), **kw}
        for k in ("cost", "trigger_metrics", "error"):
            if k in cols and cols[k] is not None:
                cols[k] = Jsonb(cols[k])
        names = ", ".join(cols)
        return self.one(f"INSERT INTO ops.task ({names}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id", tuple(cols.values()))

    # -- evidence plane ------------------------------------------------------------------------
    def pages(self, run):
        i = self.ids
        for page in PAGES:
            r = RENDITIONS[page]
            text, segs = page_segments(page)
            self.text[page] = text
            orig = Path("docs/statistics_corpus/corpus") / r["source_uri"]
            self.doc_id[page] = self.one(
                "INSERT INTO kb.document (project_id, key, source_uri, content_hash, original_path, mime, title, meta) "
                "VALUES (%s, %s, %s, %s, %s, 'text/html', %s, %s) RETURNING id",
                (i["project"], r["document_key"], r["source_uri"], doc_hash(r["source_uri"]), str(orig),
                 r.get("title"), Jsonb({"first_pass": True})))
            macros = (r.get("parse_detail") or {}).get("macros", {})
            digest = sha({"text": text, "segments": segs, "macros": macros})
            self.ren_id[page] = self.one(
                "INSERT INTO kb.rendition (document_id, key, content_digest, canonical_text, macros, parse_status) "
                "VALUES (%s, %s, %s, %s, %s, 'ok') RETURNING id",
                (self.doc_id[page], r["rendition_key"], digest, text, Jsonb(macros)))
            # depth and ordinal from the tree
            by_key = {s["key"]: s for s in segs}
            kids: dict = {}
            for s in segs:
                kids.setdefault(s.get("parent"), []).append(s)
            for ch in kids.values():
                ch.sort(key=lambda s: (s["start"], -s["end"]))
                for n, s in enumerate(ch):
                    s["_ordinal"] = n
            def depth(s):
                d, p = 0, s.get("parent")
                while p:
                    d, p = d + 1, by_key[p].get("parent")
                return d
            rows = []
            for s in segs:
                s["_depth"] = depth(s)
                attrs = {k: v for k, v in (s.get("attrs") or {}).items() if k != "sourceline"}   # diagnostics stay off segments (D1 §3.2)
                rows.append((self.ren_id[page], s["key"], s["kind"], s["_ordinal"], s["_depth"], s["start"], s["end"],
                             text[s["start"]:s["end"]], Jsonb(attrs), s.get("parse_status", "ok"), s.get("parse_reason")))
            with self.c.cursor() as cur:
                cur.executemany(
                    "INSERT INTO kb.segment (rendition_id, key, kind, ordinal, depth, start_offset, end_offset, text, attrs, parse_status, parse_reason) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", rows)
            for k, sid in self.c.execute("SELECT key, id FROM kb.segment WHERE rendition_id = %s", (self.ren_id[page],)):
                self.seg_id[k] = sid
            with self.c.cursor() as cur:
                cur.executemany("UPDATE kb.segment SET parent_id = %s WHERE id = %s",
                                [(self.seg_id[s["parent"]], self.seg_id[s["key"]]) for s in segs if s.get("parent")])
            self.seg_rows[page] = segs
            t = self.task(run, "ingest", "document", self.doc_id[page], r["document_key"], "cfg:ingest.html/default")
            self.c.execute(
                "INSERT INTO kb.rendition_build (document_id, method_config_id, rendition_id, task_id, parse_detail) VALUES (%s, %s, %s, %s, %s)",
                (self.doc_id[page], i["cfg:ingest.html/default"], self.ren_id[page], t,
                 Jsonb({"sourcelines": sum(1 for s in segs if "sourceline" in (s.get("attrs") or {}))})))
        # the Weibull page: a document only, for its reserved split
        e1 = SAMPLE2["units"]["E1"]
        self.doc_id[e1["page"]] = self.one(
            "INSERT INTO kb.document (project_id, key, source_uri, content_hash, original_path, mime) "
            "VALUES (%s, %s, %s, %s, %s, 'text/html') RETURNING id",
            (i["project"], e1["document_key"], "siegrist_random/random/" + e1["page"], doc_hash("siegrist_random/random/" + e1["page"]),
             "docs/statistics_corpus/corpus/siegrist_random/random/" + e1["page"]))

    def smallest_segment(self, page, start, end) -> int:
        best = min((s for s in self.seg_rows[page] if s["start"] <= start and end <= s["end"]),
                   key=lambda s: (s["end"] - s["start"], -s.get("_depth", 0)))
        return self.seg_id[best["key"]]

    def span(self, page, start, end) -> int:
        ren = self.ren_id[page]
        row = self.c.execute(
            "INSERT INTO kb.span (rendition_id, start_offset, end_offset, segment_id, text) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (rendition_id, start_offset, end_offset) DO NOTHING RETURNING id",
            (ren, start, end, self.smallest_segment(page, start, end), self.text[page][start:end])).fetchone()
        if row:
            return row[0]
        return self.one("SELECT id FROM kb.span WHERE rendition_id = %s AND start_offset = %s AND end_offset = %s", (ren, start, end))

    # -- knowledge plane -----------------------------------------------------------------------
    def unit_locator(self, u) -> str:
        return " + ".join(p["locator"] for p in SAMPLE["units"][u]["parts"])

    def unit_segment(self, u) -> int:
        return self.seg_id[SAMPLE["units"][u]["parts"][-1]["segment_key"]]

    def unit_ranges(self, u):
        return [(p["start"], p["end"]) for p in SAMPLE["units"][u]["parts"]]

    def load_unit(self, run, u, batch, task_status="done", materialize=True):
        page = SAMPLE["units"][u]["page"]
        ukey = key("unit", self.unit_locator(u))
        t = self.task(run, "propose", "segment", self.unit_segment(u), ukey, "cfg:agent.opus/default", status=task_status,
                      cost={"wall_ms": 1, "model": "reference_v1"}, packet_hash=sha(batch))
        obs = self.one(
            "INSERT INTO kb.observation (task_id, ordinal, kind, rendition_id, segment_id, payload, outcome) "
            "VALUES (%s, 0, 'claim_proposal', %s, %s, %s, 'produced') RETURNING id",
            (t, self.ren_id[page], self.unit_segment(u), Jsonb({"batch": batch})))
        out = {"task": t, "observation": obs, "unit_key": ukey}
        if materialize:
            out |= self.materialize(run, u, batch, obs)
        return out

    def materialize(self, run, u, batch, obs):
        page = SAMPLE["units"][u]["page"]
        ekeys, eids = {}, {}
        for st in batch.get("statements", []):
            anchors = st["anchor"]
            lo = min(next(s for s in self.seg_rows[page] if s["key"] == a)["start"] for a in anchors)
            hi = max(next(s for s in self.seg_rows[page] if s["key"] == a)["end"] for a in anchors)
            cont = min((s for s in self.seg_rows[page] if s["kind"] in ("unit", "paragraph", "details", "list_item", "sentence")
                        and s["start"] <= lo and hi <= s["end"]), key=lambda s: s["end"] - s["start"])
            k = key("stm", {"anchor": sorted(anchors)})
            eid = self.one(
                "INSERT INTO kb.entity (run_id, key, schema_version_id, type, label, scope, scope_segment_id, kind) "
                "VALUES (%s, %s, %s, 'Statement', %s, 'local', %s, %s) RETURNING id",
                (run, k, self.ids["schema"], f"{st['kind']} {u}:{st['local_ref']}", self.seg_id[cont["key"]], st["kind"]))
            for a in anchors:
                self.c.execute("INSERT INTO kb.entity_anchor (entity_id, segment_id) VALUES (%s, %s)", (eid, self.seg_id[a]))
            ekeys[st["local_ref"]], eids[st["local_ref"]] = k, eid
        ents = {e["local_ref"]: e for e in batch.get("entities", [])}
        # A `Statement`-typed *entity* (a statement outside the batch, "the last result") has no
        # StatementKind, which kb.entity's CHECK requires; D1 OPEN-D1-5 keeps such references
        # `unsupported` until `extref`. Not loaded; recorded as a misfit with the claims using it.
        misfits = []
        for r, e in list(ents.items()):
            if e["type"] == "Statement":
                misfits.append({"unit": u, "item": r, "kind": "entity", "why": "Statement-typed entity without a kind (kb.entity CHECK (type = 'Statement') = (kind IS NOT NULL)); OPEN-D1-5 extref"})
                del ents[r]

        def refof(v):   # an identity value naming another batch entity: {"ref": r} or the bare local ref
            r = v.get("ref") if isinstance(v, dict) else v if isinstance(v, str) else None
            return r if r in ents or r in ekeys else None

        def ekey(r):
            if r in ekeys:
                return ekeys[r]
            e = ents[r]
            if e["scope"] == "local":
                parts = {"type": e["type"], "scope_segment": e.get("scope_segment"), "symbol": e.get("symbol") or norm(e["label"])}
            else:
                ident = {s: (ekey(refof(v)) if refof(v) else v) for s, v in (e.get("identity") or {}).items()}
                parts = {"type": e["type"], "identity": ident, "label": norm(e["label"])}
            ekeys[r] = key("ent", parts)
            return ekeys[r]

        merged = 0
        for r, e in ents.items():
            k = ekey(r)
            ident = {s: (ekey(refof(v)) if refof(v) else v) for s, v in (e.get("identity") or {}).items()}   # refs stored as entity keys
            row = self.c.execute(
                "INSERT INTO kb.entity (run_id, key, schema_version_id, type, label, scope, scope_segment_id, attrs) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (run_id, key) DO NOTHING RETURNING id",
                (run, k, self.ids["schema"], e["type"], e["label"], e["scope"],
                 self.seg_id.get(e.get("scope_segment")) if e["scope"] == "local" else None, Jsonb(ident))).fetchone()
            if row:
                eid = row[0]
            else:
                merged += 1
                eid = self.one("SELECT id FROM kb.entity WHERE run_id = %s AND key = %s", (run, k))
            eids[r] = eid
            aliases = [(e["label"], "label")] + [(a, "term") for a in e.get("aliases", [])] + ([(e["symbol"], "symbol")] if e.get("symbol") else [])
            for a, kind in aliases:
                self.c.execute("INSERT INTO kb.entity_alias (entity_id, alias, normalized, alias_kind) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING",
                               (eid, a, norm(a), kind))
            if e["scope"] == "local" and e.get("scope_segment"):
                self.c.execute("INSERT INTO kb.entity_anchor (entity_id, segment_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                               (eid, self.seg_id[e["scope_segment"]]))
            self.c.execute("INSERT INTO kb.entity_mention (entity_id, observation_id) VALUES (%s, %s) ON CONFLICT DO NOTHING", (eid, obs))

        claims = []
        for c in batch.get("claims", []):
            o = (c.get("object") or {}).get("ref")
            if c["subject"] not in ents and c["subject"] not in ekeys or (o is not None and o not in ents and o not in ekeys):
                misfits.append({"unit": u, "item": c["local_ref"], "kind": "claim", "why": "uses a misfit entity"})
            else:
                claims.append(c)
        ckeys = {c["local_ref"]: key("clm", {"unit": u, "local_ref": c["local_ref"], "run": "placeholder"}) for c in claims}

        def resolve(v):   # local refs inside values and condition trees -> keys (D3 §6.1)
            if isinstance(v, list):
                return [resolve(x) for x in v]
            if not isinstance(v, dict):
                return v
            out = {}
            for k2, x in v.items():
                if k2 == "ref" and v.get("op") == "claim":
                    out[k2] = ckeys.get(x, x)
                elif k2 == "ref" and isinstance(x, str):
                    out[k2] = ekeys.get(x, x)
                elif k2 == "claim" and isinstance(x, str):
                    out[k2] = ckeys.get(x, x)
                elif k2 == "entity" and isinstance(x, str):
                    out[k2] = ekeys.get(x, x)
                else:
                    out[k2] = resolve(x)
            return out

        cids, n_ev = {}, 0
        for c in claims:
            obj = c.get("object") or {}
            oref = obj.get("ref") if set(obj) == {"ref"} else None
            q = {k2: v for k2, v in resolve(c.get("qualifiers") or {}).items()
                 if not (k2 == "modality" and v == "asserted") and not (k2 == "polarity" and v == "positive")}   # defaults omitted (D3 §6.1)
            pred = f"{self.prefix.get(c['predicate'], 'stat')}:{c['predicate']}"
            cid = self.one(
                "INSERT INTO kb.claim (run_id, key, subject_id, predicate, object_entity_id, object_value, qualifiers, statement_id, "
                "statement_role, status, establishment) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'accepted', 'stated') RETURNING id",
                (run, ckeys[c["local_ref"]], eids[c["subject"]], pred, eids.get(oref) if oref else None,
                 None if oref else Jsonb(resolve(obj)), Jsonb(q), eids.get(c.get("statement")), c.get("statement_role")))
            cids[c["local_ref"]] = cid
            for ev in c.get("evidence", []):
                sp = self.span(page, ev["start"], ev["end"])
                n_ev += self.c.execute("INSERT INTO kb.claim_evidence (claim_id, span_id, role) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                                       (cid, sp, ev["role"])).rowcount
            self.c.execute("INSERT INTO kb.claim_support (claim_id, observation_id) VALUES (%s, %s)", (cid, obs))
        return {"entities": eids, "entity_keys": ekeys, "claims": cids, "claim_keys": ckeys, "merged_globals": merged, "evidence_rows": n_ev, "misfits": misfits}

    def escalation(self, run, u, unit_rows):
        """An escalate task triggered by the policy rule, with a judgment observation on a span (why a method ran, D3 §9)."""
        page = SAMPLE["units"][u]["page"]
        t = self.task(run, "escalate", "segment", self.unit_segment(u), unit_rows["unit_key"], "cfg:agent.opus/default",
                      trigger_rule_id=self.ids["rule"], trigger_metrics={"claims.min_confidence": 0.4},
                      cost={"wall_ms": 2, "tokens_in": 1200, "tokens_out": 300}, finished=T0 + timedelta(minutes=20))
        sp = self.one("SELECT ce.span_id FROM kb.claim_evidence ce WHERE ce.claim_id = %s LIMIT 1", (next(iter(unit_rows["claims"].values())),))
        self.c.execute("INSERT INTO kb.observation (task_id, ordinal, kind, rendition_id, span_id, payload, outcome) VALUES (%s, 0, 'judgment', %s, %s, %s, 'produced')",
                       (t, self.ren_id[page], sp, Jsonb({"target": {"kind": "claim", "ref": next(iter(unit_rows["claim_keys"].values()))},
                                                         "decision": "accept", "rationale": "spike", "guideline_version": "v1"})))
        return t

    def derived_link(self, run, unit_rows):
        """T3's D1 (D3 §10): Y's standard deviation derived from C3, linked derived_from."""
        c3 = unit_rows["claims"]["c_aX_normal"]
        src = self.c.execute("SELECT subject_id, object_entity_id, qualifiers, statement_id FROM kb.claim WHERE id = %s", (c3,)).fetchone()
        q = dict(src[2])
        pv = dict(q.get("param_values", {}))
        pv.pop("variance", None)
        pv["standard_deviation"] = {"t": "formula", "latex": "\\lvert b \\rvert \\sigma", "symbols": {}}
        q["param_values"] = pv
        d1 = self.one(
            "INSERT INTO kb.claim (run_id, key, subject_id, predicate, object_entity_id, qualifiers, statement_id, statement_role, status, establishment) "
            "VALUES (%s, %s, %s, 'stat:has_distribution', %s, %s, %s, 'conclusion', 'accepted', 'derived') RETURNING id",
            (run, key("clm", {"derived": "D1", "from": c3}), src[0], src[1], Jsonb(q), src[3]))
        self.c.execute("INSERT INTO kb.claim_link (run_id, from_claim_id, link_type, to_claim_id, detail) VALUES (%s, %s, 'derived_from', %s, %s)",
                       (run, d1, c3, Jsonb({"rule": "stat.variance_to_sd"})))
        return d1

    # -- goldens ---------------------------------------------------------------------------------
    def goldens(self, main_run):
        i = self.ids
        for page in PAGES:
            self.c.execute("INSERT INTO eval.document_split (project_id, document_id, split, reason, seed) VALUES (%s, %s, 'dev', 'forced to dev: spike page', NULL)",
                           (i["project"], self.doc_id[page]))
        self.c.execute("INSERT INTO eval.document_split (project_id, document_id, split, reason) VALUES (%s, %s, 'reserved', 'reserved: worked-example page (D7 §3.1)')",
                       (i["project"], self.doc_id["special/Weibull.html"]))
        gs = self.one(
            "INSERT INTO eval.golden_set (project_id, label, split, schema_version_id, guideline_version_id, sampling) "
            "VALUES (%s, 'spike-core12', 'dev', %s, %s, %s) RETURNING id",
            (i["project"], i["schema"], i["guideline"], Jsonb({"forced_units": CORE, "sampler": "none (spike sample)", "seed": None})))
        grun = self.run("golden_run", "golden", parent=main_run, started=T0 + timedelta(hours=2), finished=T0 + timedelta(hours=5), reference=main_run)
        inputs_rec = json.loads((EVIDENCE / "records" / "s0r2.inputs.json").read_text())
        ref_hash = next(o["sha256"] for o in inputs_rec["outputs"] if o["path"] == "results/s0r2/inputs/packet_v1")
        decisions = json.loads((S0R2 / "reference_model_v1" / "decisions_v1.json").read_text())
        passes = [("a", S0R2 / "pass_sv", "claude-sonnet-5.5", "subagent:pass-sv"),
                  ("b", S0R2 / "pass_hv", "claude-haiku-5.5", "subagent:pass-hv"),
                  ("c", S0R2 / "reference_model_v1", "claude-opus-5.5", "root:reference-v1")]
        n_items, n_context, order = 0, 0, []
        for n, u in enumerate(CORE):
            page = SAMPLE["units"][u]["page"]
            gu = self.one(
                "INSERT INTO eval.golden_unit (golden_set_id, unit_key, current_locator, authored_rendition_id, status, agreement) "
                "VALUES (%s, %s, %s, %s, 'adjudicated', %s) RETURNING id",
                (gs, key("unit", self.unit_locator(u)), self.unit_locator(u), self.ren_id[page],
                 Jsonb({"source": "results/s0r2/compare/sv_vs_hv.core/score.json"})))
            frame = {}
            for p in SAMPLE2["units"][u]["parts"]:
                for s in p["sentences"]:
                    frame[s["id"]] = {"locator": f"{p['locator']}~{s['id']}", "text": self.text[page][s["start"]:s["end"]]}
            for cx in SAMPLE2["units"][u].get("context", []):
                frame[cx["id"]] = {"locator": f"{page}@c:{cx['key']}", "text": self.text[page][cx["start"]:cx["end"]]}
            for j, (p, folder, model, sess) in enumerate(passes):
                created = T0 + timedelta(hours=2, minutes=10 * n + (30 if p == "c" else j))
                t = self.task(grun, "golden", "golden_unit", gu, key("unit", self.unit_locator(u)), f"cfg:golden.pass/{p}",
                              created=created, finished=created + timedelta(minutes=5), attempt=1)
                order.append((u, p, t, created))
                batch = json.loads((folder / f"{u}.json").read_text())
                gp = self.one(
                    "INSERT INTO eval.golden_pass (golden_unit_id, pass, guideline_version_id, batch, citation_frame, decisions, session_ref, model, inputs) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id",
                    (gu, p, i["guideline"], Jsonb(batch), Jsonb(frame),
                     Jsonb([d for d in decisions if d.get("unit") == u]) if p == "c" else None, sess, model,
                     Jsonb({"guideline_version": "v1", "annotator_reference_hash": sha((S0R2 / "inputs" / "packet_v1" / "reference.md").read_text()),
                            "packet_hash": ref_hash, "m13_version": "s0r2_sample.py binding sites"})))
                self.c.execute(
                    "INSERT INTO ops.intervention (project_id, run_id, task_id, actor, kind, target, refs) VALUES (%s, %s, %s, %s, 'golden_write', %s, %s)",
                    (i["project"], grun, t, f"agent:{model}", Jsonb({"kind": "golden_unit", "ref": gu}), Jsonb({"golden_pass": gp})))
                if p == "c":
                    stored = json.loads((S0R2 / "reference_v1" / f"{u}.json").read_text())
                    a, b = self._items(gp, page, u, stored)
                    n_items += a
                    n_context += b
        return {"golden_set": gs, "golden_run": grun, "items": n_items, "context_items": n_context, "task_order": order}

    def _items(self, gp, page, u, stored):
        ranges = self.unit_ranges(u)
        inside = lambda s, e: any(lo <= s and e <= hi for lo, hi in ranges)  # noqa: E731
        segpos = {s["key"]: (s["start"], s["end"]) for s in self.seg_rows[page]}
        ctx_st = {st["local_ref"] for st in stored.get("statements", []) if not all(inside(*segpos[a]) for a in st["anchor"])}
        rows = []
        for t, coll in (("statement", "statements"), ("entity", "entities"), ("claim", "claims"),
                        ("alternative", "alternatives"), ("unsupported", "unsupported")):
            for it in stored.get(coll, []):
                ctx = (t == "statement" and it["local_ref"] in ctx_st) or (t == "claim" and it.get("statement") in ctx_st)
                rows.append((gp, self.ren_id[page], t, it["local_ref"], Jsonb(it), ctx))
        with self.c.cursor() as cur:
            cur.executemany("INSERT INTO eval.golden_item (golden_pass_id, rendition_id, item_type, local_ref, payload, context) "
                            "VALUES (%s, %s, %s, %s, %s, %s)", rows)
        return len(rows), sum(1 for r in rows if r[5])
