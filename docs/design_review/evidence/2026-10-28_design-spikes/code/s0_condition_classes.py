"""Classify full-tier condition failures against the reference by shape (S0-G, Sonnet runs).

For each core-matched pair whose full-tier failure includes ``conditions``: does the pass add a
condition tree the reference lacks, omit one, reference different premises, or differ only in
repeated restrictions (``member``/``cmp`` nodes)? Writes results/s0/condition_classes.tsv.
"""

import collections
import json
import re
from pathlib import Path

S0 = Path(__file__).resolve().parent.parent / "results" / "s0"
PASSES = {"ref_vs_a": "pass_a", "ref_vs_b": "pass_b", "ref_vs_sg": "pass_sg", "ref_vs_sp": "pass_sp",
          "ref_vs_h": "pass_h", "ref_vs_p": "pass_p"}
FAIL = re.compile(r"^  (\S+)~(\S+) full-tier failures \[[^\]]*'conditions'", re.M)


def nodes(c, out):
    if not c:
        return out
    out[c.get("op")] += 1
    if c.get("op") == "claim":
        out.setdefault("refs", []).append(c.get("ref"))
    for a in c.get("args") or []:
        nodes(a, out)
    if "arg" in c:
        nodes(c["arg"], out)
    return out


def classify(rc, pc, core):
    if not rc and pc:
        return "pass adds a condition tree the reference lacks"
    if rc and not pc:
        return "pass omits the condition tree"
    nr, np_ = nodes(rc, collections.Counter()), nodes(pc, collections.Counter())
    same = sorted(core.get(x, f"?{x}") for x in nr.get("refs", [])) == sorted(np_.get("refs", []))
    mr, mp = nr["member"] + nr["cmp"], np_["member"] + np_["cmp"]
    if same and mr > mp:
        return "same premises; reference repeats restrictions"
    if same and mr < mp:
        return "same premises; pass adds restrictions"
    if not same and mr == mp:
        return "different premise references"
    return "premises and restrictions both differ"


rows = []
for cmp, pdir in PASSES.items():
    txt = (S0 / "compare" / cmp / "alignment.txt").read_text()
    for blk in txt.split("# unit ")[1:]:
        u = blk.split("\n", 1)[0].strip()
        core = dict(eval(re.search(r"^core: (\[.*\])$", blk, re.M).group(1)))  # noqa: S307 - our own file
        ref = {c["local_ref"]: c for c in json.loads((S0 / "reference" / f"{u}.json").read_text())["claims"]}
        pas = {c["local_ref"]: c for c in json.loads((S0 / pdir / f"{u}.json").read_text())["claims"]}
        for a, b in FAIL.findall(blk):
            rc = (ref[a].get("qualifiers") or {}).get("conditions")
            pc = (pas[b].get("qualifiers") or {}).get("conditions")
            rows.append((cmp, u, a, b, ref[a]["predicate"], ref[a].get("statement_role") or "", classify(rc, pc, core)))

out = S0 / "condition_classes.tsv"
with out.open("w") as f:
    f.write("comparison\tunit\tref_claim\tpred_claim\tpredicate\tref_statement_role\tclass\n")
    for r in rows:
        f.write("\t".join(r) + "\n")
print(f"{len(rows)} rows -> {out}")
