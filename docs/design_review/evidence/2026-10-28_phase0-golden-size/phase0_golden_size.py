"""Size of the phase0-golden slice under D7 §3.1's split and dev sampler, simulated on S1's
annotation units (evaluation-and-goldens worker, 2026-10-28). Read-only over the corpus index and
the tracked S1 results; prints medians and 5-95 % ranges over 500 seeds.

Simulated rules (D7 §3.1): reserved page special/Weibull.html; forced-dev pages = the four spike
pages + Pareto + ChiSquare; the other first-pass pages ordered per chapter by
sha256(page + seed), every fifth (0-based index % 5 == 4) to test. Dev set: 40 units; the 13
trace/core12 locators forced; strata = statement kind (markup hint, else narrative) x math-share
tercile over the dev pool; proportional allocation, at least one per non-empty stratum (largest
remainder), forced units count towards their strata (excess taken from the most over-allocated
strata); within a stratum, order sha256(unit + seed). Unit keys are S1 segment keys here, not
product locators, so the figures are a distribution, not the exact count.
Run: python3 -I phase0_golden_size.py
"""
import csv, hashlib, json, statistics
from collections import defaultdict
from pathlib import Path

REPO = Path("/home/paul/corpus-structure")
IDX = REPO / "docs/statistics_corpus/index/siegrist_sections.tsv"
S1 = REPO / "docs/design_review/evidence/2026-10-28_design-spikes/results/s1"
RESERVED = {"special/Weibull.html"}
SPIKE = {"special/LocationScale.html", "special/Normal.html", "special/LogNormal.html", "special/Gamma.html"}
FORCED_DEV = SPIKE | {"special/Pareto.html", "special/ChiSquare.html"}
N = 40


def h(s):
    return hashlib.sha256(s.encode()).hexdigest()


pages = {r["path"]: r["chapter"] for r in csv.DictReader(open(IDX), delimiter="\t") if r["first_pass"] == "yes"}
units = defaultdict(list)  # page -> [(segment, statement kind, math share)]
for r in csv.DictReader(open(S1 / "sizes.tsv"), delimiter="\t"):
    units[r["page"]].append((r["segment"], r["hint"] or "narrative", float(r["math_share"])))
assert set(units) == set(pages)
forced = {v["segments"][0] for v in json.load(open(S1 / "locators.json")).values()}


def split(seed):
    out, by_ch = {}, defaultdict(list)
    for p, ch in pages.items():
        if p in RESERVED:
            out[p] = "reserved"
        elif p in FORCED_DEV:
            out[p] = "dev"
        else:
            by_ch[ch].append(p)
    for ps in by_ch.values():
        for i, p in enumerate(sorted(ps, key=lambda p: h(p + str(seed)))):
            out[p] = "test" if i % 5 == 4 else "dev"
    return out


def sample(sp, seed):
    pool = [(p, *u) for p, s in sp.items() if s == "dev" for u in units[p]]
    ms = sorted(u[3] for u in pool)
    t1, t2 = ms[len(ms) // 3], ms[2 * len(ms) // 3]
    stratum = lambda u: (u[2], 0 if u[3] < t1 else (1 if u[3] < t2 else 2))  # noqa: E731
    strata = defaultdict(list)
    for u in pool:
        strata[stratum(u)].append(u)
    exact = {k: N * len(v) / len(pool) for k, v in strata.items()}
    quota = {k: max(1, int(x)) for k, x in exact.items()}
    for k in sorted(strata, key=lambda k: -(exact[k] - int(exact[k])))[: max(0, N - sum(quota.values()))]:
        quota[k] += 1
    chosen = {u[1]: u for u in pool if u[1] in forced}
    fc = defaultdict(int)
    for u in chosen.values():
        fc[stratum(u)] += 1
    quota = {k: max(q, fc[k]) for k, q in quota.items()}
    while sum(quota.values()) > N:
        k = max((k for k in quota if quota[k] > max(1, fc[k])), key=lambda k: quota[k] - exact[k])
        quota[k] -= 1
    for k, v in strata.items():
        need = quota[k] - fc[k]
        for u in sorted(v, key=lambda u: h(u[1] + str(seed))):
            if need <= 0:
                break
            if u[1] not in chosen:
                chosen[u[1]] = u
                need -= 1
    return chosen


def report(name, xs):
    q = statistics.quantiles(xs, n=20)
    print(f"{name}: median {statistics.median(xs):.0f}, 5-95 % {q[0]:.0f}-{q[-1]:.0f}, range {min(xs)}-{max(xs)}")


rows = defaultdict(list)
for seed in range(500):
    sp = split(seed)
    ch = sample(sp, seed)
    gp = FORCED_DEV | {u[0] for u in ch.values()}
    rows["dev golden units"].append(len(ch))
    rows["whole golden pages: pages"].append(len(gp))
    rows["whole golden pages: packets"].append(sum(len(units[p]) for p in gp))
    rows["spike pages whole + golden units: packets"].append(
        sum(len(units[p]) for p in SPIKE) + sum(1 for u in ch.values() if u[0] not in SPIKE))
    rows["non-test, non-reserved units"].append(sum(len(units[p]) for p, s in sp.items() if s == "dev"))
print("first-pass pages", len(pages), "annotation units", sum(map(len, units.values())),
      "spike-page units", sum(len(units[p]) for p in SPIKE), "forced units found", len(forced & {u[0] for v in units.values() for u in v}))
for k, v in rows.items():
    report(k, v)
