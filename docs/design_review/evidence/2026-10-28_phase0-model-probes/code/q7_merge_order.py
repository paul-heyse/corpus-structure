"""Probe Q-7 (P0-P-Q7, record ``p0q.merge-order``): D5 §3.6's declared must-link order, procedural against set-based.

    UV_PROJECT_ENVIRONMENT=$PWD/build/probe-venv uv run --frozen --project docs/design_review/evidence/2026-10-28_phase0-model-probes \
        python docs/design_review/evidence/2026-10-28_phase0-model-probes/code/q7_merge_order.py

The declared order (D5 §3.6 as amended by P0-D-2): agent/human ``merge`` judgments first, then match score
descending, then the pair key (the two entity keys in canonical order) ascending; a union is refused when it
would join a cannot-linked pair. No database server is used: DuckDB 2.0 runs in process over Arrow tables.

Implementations compared on every fixture and every shuffle:

- ``py_declared``: the reference. Canonicalize and deduplicate pairs (a pair both judged and scored ranks as a
  judgment), sort by the declared order, union-find with refusal (a union is refused when any member of one
  component is cannot-linked to any member of the other).
- ``py_arrival``: the same union-find in input order, without the declared sort: what D5 §3.6 warns about.
- ``duck_sequential``: DuckDB ``WITH RECURSIVE … USING KEY (node)``. The keyed state is each node's component
  label plus one clock row; iteration *i* takes the must-link of rank *i* (``row_number()`` over the declared
  order), reads both components from ``recurring.st``, refuses through a ``NOT EXISTS`` cannot-link anti-join
  over the two components, and otherwise relabels both components to the smaller label. One iteration per
  must-link.
- ``duck_components_antijoin``: the purely set-based form: connected components by
  ``USING KEY (node, min(comp))`` label propagation over the must-links, after an anti-join that drops must-links
  whose own pair is cannot-linked. It needs no order. Its cannot-linked pairs left inside one component are
  counted.
- ``duck_hybrid``: set-based components over all must-links; components holding no cannot-linked pair are final
  (no union inside them can be refused); only the components that hold one are passed to ``duck_sequential``.

Fixtures: named hand-made cases with hand-written expected partitions (independent of every implementation),
in which the order decides which union is refused, and random fixtures whose cannot-links are drawn inside
must-link components (so they interact), with tied scores and some judgments. Each fixture is run over
shuffled inputs: row order permuted, each pair's orientation flipped at random. Writes ``results/q7/``.
"""

from __future__ import annotations

import json
import random
import statistics
import time
from pathlib import Path

import duckdb
import pyarrow as pa

OUT = Path(__file__).resolve().parent.parent / "results" / "q7"
SHUFFLES = 40

# --- fixtures -----------------------------------------------------------------------------------------
# must: (a, b, score or None, judged); cannot: (a, b). Expected partitions are written by hand from D5 §3.6.
NAMED = {
    "chain3": {
        "must": [("A", "B", 0.9, False), ("B", "C", 0.8, False)], "cannot": [("A", "C")],
        "expected": [["A", "B"], ["C"]],
        "why": "A–B first by score; B–C would join A and C"},
    "tie_by_pair_key": {
        "must": [("C", "B", 0.8, False), ("B", "A", 0.8, False)], "cannot": [("C", "A")],
        "expected": [["A", "B"], ["C"]],
        "why": "equal scores: pair key (A,B) < (B,C); pairs given reversed"},
    "judgment_first": {
        "must": [("B", "C", 0.95, False), ("C", "D", None, True)], "cannot": [("B", "D")],
        "expected": [["B"], ["C", "D"]],
        "why": "the merge judgment C–D ranks above the 0.95 pair; B–C then joins B and D"},
    "refusal_cascade": {
        "must": [("A", "B", 0.9, False), ("B", "C", 0.8, False), ("C", "D", 0.7, False), ("A", "D", 0.6, False)], "cannot": [("A", "C")],
        "expected": [["A", "B"], ["C", "D"]],
        "why": "B–C refused; C–D accepted; A–D refused because {A,B} and {C,D} hold A–C"},
    "two_cannots": {
        "must": [("A", "B", 0.9, False), ("C", "D", 0.9, False), ("B", "C", 0.5, False), ("A", "D", 0.4, False)],
        "cannot": [("A", "C"), ("B", "D")],
        "expected": [["A", "B"], ["C", "D"]],
        "why": "B–C refused by A–C, A–D refused by B–D; in arrival order B–C first gives {A,D},{B,C}"},
    "duplicate_pair": {
        "must": [("A", "B", 0.55, False), ("B", "A", None, True), ("B", "C", 0.99, False)], "cannot": [("A", "C")],
        "expected": [["A", "B"], ["C"]],
        "why": "A–B scored and judged counts once, as a judgment, so it precedes B–C at 0.99"},
    "isolated_and_long_chain": {
        "must": [("E1", "E2", 0.7, False), ("E2", "E3", 0.7, False), ("E3", "E4", 0.7, False), ("E4", "E5", 0.7, False)],
        "cannot": [("E1", "E5"), ("X", "E3")],
        "expected": [["E1", "E2", "E3", "E4"], ["E5"], ["X"]],
        "why": "ties broken by pair key along the chain: E4–E5 is last and joins E1 and E5; X is cannot-linked only"},
}


def random_fixture(seed: int, n: int, m: int, c: int, judged_share: float = 0.05) -> dict:
    rnd = random.Random(seed)
    nodes = [f"ent:{seed}-{i:05d}" for i in range(n)]
    must, seen = [], set()
    while len(must) < m:
        a, b = rnd.sample(nodes[: max(2, n)], 2)
        # locality, so components are chains and clusters rather than one giant component
        b = nodes[min(n - 1, max(0, nodes.index(a) + rnd.randint(-6, 6)))] if rnd.random() < 0.85 else b
        if a == b or tuple(sorted((a, b))) in seen:
            continue
        seen.add(tuple(sorted((a, b))))
        judged = rnd.random() < judged_share
        must.append((a, b, None if judged else round(0.5 + 0.05 * rnd.randint(0, 10), 2), judged))
    # cannot-links inside must components, so that they interact with the order
    comp = components_plain(nodes, must)
    groups: dict[str, list] = {}
    for k, r in comp.items():
        groups.setdefault(r, []).append(k)
    big = [g for g in groups.values() if len(g) >= 3]
    cannot, cseen = [], set()
    while len(cannot) < c and big:
        g = rnd.choice(big)
        a, b = rnd.sample(g, 2)
        p = tuple(sorted((a, b)))
        if p in cseen or p in seen:
            continue
        cseen.add(p)
        cannot.append((a, b))
    return {"must": must, "cannot": cannot, "nodes": nodes}


def clustered_fixture(seed: int, n: int, bridge_share: float = 0.02, hot_share: float = 0.2) -> dict:
    """Entity-resolution-shaped: clusters of 2-8 candidates with dense must-links inside, a few cross-cluster
    bridges, and cannot-links inside a share of the clusters (so their order matters)."""
    rnd = random.Random(seed)
    nodes = [f"ent:c{seed}-{i:06d}" for i in range(n)]
    clusters, i = [], 0
    while i < n:
        k = min(n - i, rnd.randint(2, 8))
        clusters.append(nodes[i:i + k])
        i += k
    must, seen, cannot = [], set(), []

    def add(a, b):
        p = (min(a, b), max(a, b))
        if a != b and p not in seen:
            seen.add(p)
            judged = rnd.random() < 0.05
            must.append((a, b, None if judged else round(0.5 + 0.05 * rnd.randint(0, 10), 2), judged))
    for cl in clusters:
        for x in range(len(cl)):
            for y in range(x + 1, len(cl)):
                if rnd.random() < 0.6:
                    add(cl[x], cl[y])
        if len(cl) >= 3 and rnd.random() < hot_share:
            a, b = rnd.sample(cl, 2)
            if (min(a, b), max(a, b)) not in seen:
                cannot.append((a, b))
    for _ in range(int(bridge_share * len(must))):
        c1, c2 = rnd.sample(clusters, 2)
        add(rnd.choice(c1), rnd.choice(c2))
    return {"must": must, "cannot": cannot, "nodes": nodes}


def components_plain(nodes, must) -> dict:
    parent = {k: k for k in nodes}

    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b, *_ in must:
        ra, rb = f(a), f(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)
    return {k: f(k) for k in nodes}


# --- the procedural reference -----------------------------------------------------------------------

def canonical(must):
    """One row per canonical pair; a pair both judged and scored ranks as a judgment, with its best score."""
    out: dict[tuple, list] = {}
    for a, b, s, j in must:
        p = (a, b) if a <= b else (b, a)
        cur = out.setdefault(p, [None, False])
        cur[1] = cur[1] or j
        if s is not None:
            cur[0] = s if cur[0] is None else max(cur[0], s)
    return [(p[0], p[1], v[0], v[1]) for p, v in out.items()]


def declared_key(r):
    a, b, s, j = r
    # judgments rank above every scored pair and are ordered among themselves by pair key only
    return (0, 0.0, a, b) if j else (1, -s, a, b)


def union_find(nodes, ordered, cannot):
    parent = {k: k for k in nodes}
    members = {k: {k} for k in nodes}
    banned = {k: set() for k in nodes}          # root -> nodes cannot-linked to some member
    for a, b in cannot:
        banned[a].add(b)
        banned[b].add(a)

    def f(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    refused = []
    for a, b, *_ in ordered:
        ra, rb = f(a), f(b)
        if ra == rb:
            continue
        small, large = (ra, rb) if len(members[ra]) <= len(members[rb]) else (rb, ra)
        if banned[large] & members[small]:
            refused.append((min(a, b), max(a, b)))
            continue
        parent[small] = large
        members[large] |= members.pop(small)
        banned[large] |= banned.pop(small)
    return partition({k: f(k) for k in nodes}), sorted(refused)


def partition(label: dict) -> list:
    groups: dict = {}
    for k, r in label.items():
        groups.setdefault(r, []).append(k)
    return sorted(sorted(g) for g in groups.values())


def py_declared(nodes, must, cannot):
    return union_find(nodes, sorted(canonical(must), key=declared_key), cannot)


def py_arrival(nodes, must, cannot):
    return union_find(nodes, must, cannot)


# --- DuckDB ------------------------------------------------------------------------------------------

def tables(must, cannot, nodes):
    m = pa.table({"a": [r[0] for r in must], "b": [r[1] for r in must], "score": pa.array([r[2] for r in must], pa.float64()),
                  "judged": [r[3] for r in must]})
    c = pa.table({"a": [r[0] for r in cannot], "b": [r[1] for r in cannot]})
    n = pa.table({"k": list(nodes)})
    return m, c, n


PREP = """
CREATE OR REPLACE TEMP TABLE must AS
SELECT k1, k2, row_number() OVER (ORDER BY judged DESC, CASE WHEN judged THEN NULL ELSE score END DESC NULLS LAST, k1, k2) AS rnk
FROM (SELECT least(a, b) AS k1, greatest(a, b) AS k2, bool_or(judged) AS judged, max(score) AS score FROM must_in GROUP BY ALL);
CREATE OR REPLACE TEMP TABLE cannot AS SELECT DISTINCT least(a, b) AS k1, greatest(a, b) AS k2 FROM cannot_in;
CREATE OR REPLACE TEMP TABLE nodes AS SELECT DISTINCT k FROM nodes_in;
"""

SEQUENTIAL = """
WITH RECURSIVE st(node, comp, step) USING KEY (node) AS (
  SELECT * FROM (SELECT k AS node, k AS comp, 0 AS step FROM {nodes} UNION ALL SELECT '', '', 1)
  UNION
  SELECT * FROM (
    WITH f AS (SELECT step FROM st WHERE node = ''),
         e AS (SELECT m.k1, m.k2, f.step FROM f JOIN {must} m ON m.rnk = f.step),
         p AS (SELECT a.comp AS ca, b.comp AS cb, e.step FROM e JOIN recurring.st a ON a.node = e.k1 JOIN recurring.st b ON b.node = e.k2
               WHERE a.comp <> b.comp AND NOT EXISTS (
                 SELECT 1 FROM {cannot} c JOIN recurring.st x ON x.node = c.k1 JOIN recurring.st y ON y.node = c.k2
                 WHERE (x.comp = a.comp AND y.comp = b.comp) OR (x.comp = b.comp AND y.comp = a.comp)))
    SELECT r.node, least(p.ca, p.cb), p.step FROM p JOIN recurring.st r ON r.node <> '' AND r.comp IN (p.ca, p.cb)
    UNION ALL
    SELECT '', '', f.step + 1 FROM f WHERE f.step < (SELECT coalesce(max(rnk), 0) FROM {must}))
)
SELECT node, comp FROM st WHERE node <> ''
"""

COMPONENTS = """
WITH RECURSIVE cc(node, comp) USING KEY (node, min(comp)) AS (
  SELECT k, k FROM {nodes}
  UNION
  SELECT x.dst, cc.comp FROM cc JOIN (SELECT k1 AS src, k2 AS dst FROM {edges} UNION ALL SELECT k2, k1 FROM {edges}) x ON x.src = cc.node
)
SELECT node, comp FROM cc
"""


def duck(con, must, cannot, nodes):
    m, c, n = tables(must, cannot, nodes)
    con.register("must_in", m)
    con.register("cannot_in", c)
    con.register("nodes_in", n)
    con.execute(PREP)


def refused_from(con, label):
    lab = label
    return sorted((a, b) for a, b in con.sql("SELECT k1, k2 FROM must").fetchall() if lab[a] != lab[b])


def duck_sequential(con):
    label = dict(con.sql(SEQUENTIAL.format(nodes="nodes", must="must", cannot="cannot")).fetchall())
    return partition(label), refused_from(con, label)


def duck_components_antijoin(con):
    con.execute("CREATE OR REPLACE TEMP TABLE must_kept AS SELECT k1, k2 FROM must ANTI JOIN cannot USING (k1, k2)")
    label = dict(con.sql(COMPONENTS.format(nodes="nodes", edges="must_kept")).fetchall())
    inside = sum(1 for a, b in con.sql("SELECT k1, k2 FROM cannot").fetchall() if label[a] == label[b])
    return partition(label), refused_from(con, label), inside


def duck_hybrid(con):
    con.execute(f"CREATE OR REPLACE TEMP TABLE comp AS {COMPONENTS.format(nodes='nodes', edges='must')}")
    con.execute("CREATE OR REPLACE TEMP TABLE hot AS SELECT DISTINCT x.comp FROM cannot c JOIN comp x ON x.node = c.k1 JOIN comp y ON y.node = c.k2 WHERE x.comp = y.comp")
    con.execute("CREATE OR REPLACE TEMP TABLE hot_nodes AS SELECT node AS k FROM comp SEMI JOIN hot USING (comp)")
    con.execute("CREATE OR REPLACE TEMP TABLE hot_must AS SELECT k1, k2, row_number() OVER (ORDER BY rnk) AS rnk FROM must "
                "WHERE k1 IN (SELECT k FROM hot_nodes)")
    con.execute("CREATE OR REPLACE TEMP TABLE hot_cannot AS SELECT k1, k2 FROM cannot WHERE k1 IN (SELECT k FROM hot_nodes)")
    label = dict(con.sql("SELECT node, comp FROM comp ANTI JOIN hot USING (comp)").fetchall())
    hot_n = con.sql("SELECT count(*) FROM hot_nodes").fetchall()[0][0]
    if hot_n:
        label |= dict(con.sql(SEQUENTIAL.format(nodes="hot_nodes", must="hot_must", cannot="hot_cannot")).fetchall())
    return partition(label), refused_from(con, label), {"sequential_nodes": hot_n,
                                                        "sequential_edges": con.sql("SELECT count(*) FROM hot_must").fetchall()[0][0]}


def duck_hybrid_parallel(con):
    """As duck_hybrid, but the conflicting components advance together: each component's must-links are ranked
    within the component (same declared order), and iteration i applies every component's rank-i must-link.
    Components are disjoint, so the relabels of one iteration touch disjoint label sets. Iterations = the
    largest conflicting component's must-link count, not the total."""
    duck_hybrid(con)   # builds comp, hot, hot_nodes, hot_cannot
    con.execute("CREATE OR REPLACE TEMP TABLE hot_must_p AS SELECT m.k1, m.k2, row_number() OVER (PARTITION BY x.comp ORDER BY m.rnk) AS rnk "
                "FROM must m JOIN comp x ON x.node = m.k1 SEMI JOIN hot USING (comp)")
    label = dict(con.sql("SELECT node, comp FROM comp ANTI JOIN hot USING (comp)").fetchall())
    iters = con.sql("SELECT coalesce(max(rnk), 0) FROM hot_must_p").fetchall()[0][0]
    if iters:
        label |= dict(con.sql(SEQUENTIAL.format(nodes="hot_nodes", must="hot_must_p", cannot="hot_cannot")).fetchall())
    return partition(label), refused_from(con, label), {"iterations": iters}


# --- the run -----------------------------------------------------------------------------------------

def shuffled(must, cannot, rnd):
    m = [((b, a) if rnd.random() < 0.5 else (a, b)) + (s, j) for a, b, s, j in must]
    c = [(b, a) if rnd.random() < 0.5 else (a, b) for a, b in cannot]
    rnd.shuffle(m)
    rnd.shuffle(c)
    return m, c


def run_fixture(name, fx, shuffles, con, expected=None) -> dict:
    nodes = fx.get("nodes") or sorted({k for r in fx["must"] for k in r[:2]} | {k for r in fx["cannot"] for k in r})
    rnd = random.Random(sum(map(ord, name)))
    ref_part, ref_ref = py_declared(nodes, fx["must"], fx["cannot"])
    out = {"nodes": len(nodes), "must": len(fx["must"]), "cannot": len(fx["cannot"]), "refused_by_reference": len(ref_ref),
           "reference_partition_blocks": len(ref_part), "shuffles": shuffles}
    if expected is not None:
        out["reference_equals_hand_expectation"] = ref_part == sorted(sorted(g) for g in expected)
    distinct = {k: set() for k in ("py_declared", "py_arrival", "duck_sequential", "duck_components_antijoin", "duck_hybrid", "duck_hybrid_parallel")}
    eq = {k: 0 for k in ("duck_sequential", "duck_components_antijoin", "duck_hybrid", "duck_hybrid_parallel")}
    refused_eq = {k: 0 for k in eq}
    inside, times, hyb = [], {k: [] for k in distinct}, None
    for i in range(shuffles):
        m, c = shuffled(fx["must"], fx["cannot"], rnd) if i else (fx["must"], fx["cannot"])
        t0 = time.perf_counter()
        p, r = py_declared(nodes, m, c)
        times["py_declared"].append(time.perf_counter() - t0)
        distinct["py_declared"].add(json.dumps(p))
        t0 = time.perf_counter()
        pa_, _ = py_arrival(nodes, m, c)
        times["py_arrival"].append(time.perf_counter() - t0)
        distinct["py_arrival"].add(json.dumps(pa_))
        duck(con, m, c, nodes)
        for k, fn in (("duck_sequential", duck_sequential), ("duck_components_antijoin", duck_components_antijoin), ("duck_hybrid", duck_hybrid), ("duck_hybrid_parallel", duck_hybrid_parallel)):
            t0 = time.perf_counter()
            res = fn(con)
            times[k].append(time.perf_counter() - t0)
            dp, dr = res[0], res[1]
            distinct[k].add(json.dumps(dp))
            eq[k] += dp == ref_part
            refused_eq[k] += dr == ref_ref
            if k == "duck_components_antijoin":
                inside.append(res[2])
            if k == "duck_hybrid":
                hyb = res[2]
            if k == "duck_hybrid_parallel":
                hyb = (hyb or {}) | {"parallel_iterations": res[2]["iterations"]}
    out |= {"distinct_partitions_over_shuffles": {k: len(v) for k, v in distinct.items()},
            "equal_to_reference": {k: f"{v}/{shuffles}" for k, v in eq.items()},
            "refused_set_equal_to_reference": {k: f"{v}/{shuffles}" for k, v in refused_eq.items()},
            "antijoin_cannot_pairs_left_inside_a_component": max(inside), "hybrid_sequential_share": hyb,
            "median_ms": {k: round(statistics.median(v) * 1000, 2) for k, v in times.items()}}
    if expected is not None:
        out["arrival_partitions_seen"] = sorted(json.loads(x) for x in distinct["py_arrival"])
    return out


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("SET TimeZone = 'UTC'")
    res = {"versions": {"duckdb": duckdb.__version__, "pyarrow": pa.__version__}, "threads": con.sql("SELECT current_setting('threads')").fetchall()[0][0],
           "shuffles": SHUFFLES, "named": {}, "random": {}}
    for name, fx in NAMED.items():
        res["named"][name] = run_fixture(name, fx, SHUFFLES, con, fx["expected"]) | {"why": fx["why"], "expected": fx["expected"]}
        print(name, res["named"][name]["equal_to_reference"], res["named"][name]["distinct_partitions_over_shuffles"])
    specs = [(seed, 300, 600, 80) for seed in (1, 2, 3, 4, 5)] + [(11, 3000, 6000, 600)]
    fixtures = {}
    for seed, n, m, c in specs:
        fx = random_fixture(seed, n, m, c)
        name = f"random_s{seed}_n{n}_m{m}_c{c}"
        fixtures[name] = fx
        res["random"][name] = run_fixture(name, fx, SHUFFLES if n <= 300 else 5, con)
        print(name, res["random"][name]["equal_to_reference"], res["random"][name]["distinct_partitions_over_shuffles"], res["random"][name]["median_ms"])
    for seed, n in ((21, 3000), (22, 5000), (23, 25000)):
        fx = clustered_fixture(seed, n)
        name = f"clustered_s{seed}_n{n}_m{len(fx['must'])}_c{len(fx['cannot'])}"
        fixtures[name] = fx
        res["random"][name] = run_fixture(name, fx, 10 if n <= 5000 else 3, con)
        print(name, res["random"][name]["equal_to_reference"], res["random"][name]["distinct_partitions_over_shuffles"], res["random"][name]["median_ms"],
              res["random"][name]["hybrid_sequential_share"])
    # a single-thread check of the sequential form on one random fixture
    con1 = duckdb.connect(config={"threads": 1})
    fx = fixtures["random_s1_n300_m600_c80"]
    duck(con1, fx["must"], fx["cannot"], fx["nodes"])
    res["single_thread_sequential_equal"] = duck_sequential(con1)[0] == py_declared(fx["nodes"], fx["must"], fx["cannot"])[0]
    (OUT / "fixtures.json").write_text(json.dumps({"named": NAMED, "random_specs": specs, "clustered_specs": [(21, 3000), (22, 5000), (23, 25000)],
                                                   "random": {k: {"must": v["must"], "cannot": v["cannot"]} for k, v in fixtures.items()}}) + "\n")
    (OUT / "result.json").write_text(json.dumps(res, indent=1, ensure_ascii=False) + "\n")
    write_md(res)
    return 0


def write_md(res) -> None:
    L = ["# Q-7 merge order (generated by `q7_merge_order.py`)", "", f"DuckDB {res['versions']['duckdb']}, threads {res['threads']}; "
         f"{res['shuffles']} shuffles per fixture (5 for the 3,000-node random fixture, 10 for clustered up to 5,000 nodes, 3 at 25,000); single-thread sequential equal: {res['single_thread_sequential_equal']}.", "",
         "| fixture | nodes / must / cannot | refused (reference) | hand expectation | equal to reference: sequential / antijoin / hybrid / hybrid-parallel | distinct partitions: declared / arrival / sequential / antijoin / hybrid / hybrid-parallel | antijoin cannot pairs inside | hybrid sequential nodes/edges/parallel iterations | median ms: py / seq / antijoin / hybrid / hybrid-parallel |",
         "|---|---|---|---|---|---|---|---|---|"]
    for group in ("named", "random"):
        for k, v in res[group].items():
            e, d, t = v["equal_to_reference"], v["distinct_partitions_over_shuffles"], v["median_ms"]
            L.append(f"| {k} | {v['nodes']} / {v['must']} / {v['cannot']} | {v['refused_by_reference']} | {v.get('reference_equals_hand_expectation', '—')} | "
                     f"{e['duck_sequential']} / {e['duck_components_antijoin']} / {e['duck_hybrid']} / {e['duck_hybrid_parallel']} | "
                     f"{d['py_declared']} / {d['py_arrival']} / {d['duck_sequential']} / {d['duck_components_antijoin']} / {d['duck_hybrid']} / {d['duck_hybrid_parallel']} | "
                     f"{v['antijoin_cannot_pairs_left_inside_a_component']} | {v['hybrid_sequential_share']['sequential_nodes']}/{v['hybrid_sequential_share']['sequential_edges']}/{v['hybrid_sequential_share']['parallel_iterations']} | "
                     f"{t['py_declared']} / {t['duck_sequential']} / {t['duck_components_antijoin']} / {t['duck_hybrid']} / {t['duck_hybrid_parallel']} |")
    L += ["", "## Arrival-order partitions of the named fixtures", ""]
    for k, v in res["named"].items():
        L.append(f"- {k} ({v['why']}): expected {v['expected']}; arrival order produced {v['arrival_partitions_seen']}")
    (OUT / "result.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
