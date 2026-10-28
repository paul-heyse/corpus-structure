"""S0-D: the root's adjudication of pass A against pass B into the S0 reference.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0d_reference.py

Each unit starts from one pass's model-facing batch (BASE) and applies the decisions in
DECISIONS, each with its kind (S0 plan §4.4) and a one-line reason. Writes the model-facing
reference to results/s0/reference_model/, the decision record to results/s0/adjudication.md and
the contested items (claims A and B did not agree on at the full tier, by the aligner's
a_vs_b run) to results/s0/reference_model/contested.json. Then convert and validate:
    code/s0_check.py results/s0/reference_model --out results/s0/reference
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent
EVIDENCE = CODE.parent
S0 = EVIDENCE / "results" / "s0"
OUT = S0 / "reference_model"

UNITS = ["T1", "T2", "T3", "T4", "U5", "U6", "U7", "U8", "U9", "U10", "U11", "U12"]
BASE = {"T1": "a", "T2": "b", "T3": "a", "T4": "a", "U5": "a", "U6": "b", "U7": "b", "U8": "b",
        "U9": "a", "U10": "a", "U11": "a", "U12": "a"}


def claim(b, ref):
    return next(c for c in b["claims"] if c["local_ref"] == ref)


def set_q(ref, **kv):
    def f(b, other):
        c = claim(b, ref)
        for k, v in kv.items():
            if k == "statement_role":
                c["statement_role"] = v
            elif v is None:
                c.setdefault("qualifiers", {}).pop(k, None)
            else:
                c.setdefault("qualifiers", {})[k] = v
    return f


def drop_condition_claim(ref, cited):
    def f(b, other):
        q = claim(b, ref)["qualifiers"]
        cond = q.get("conditions")
        if cond and cond.get("op") == "and":
            cond["args"] = [a for a in cond["args"] if not (a.get("op") == "claim" and a.get("ref") == cited)]
            if len(cond["args"]) == 1:
                q["conditions"] = cond["args"][0]
    return f


def take_unsupported_from_other(refs=None, add=True):
    def f(b, other):
        items = [copy.deepcopy(u) for u in other.get("unsupported", []) if refs is None or u["local_ref"] in refs]
        b["unsupported"] = (b.get("unsupported", []) if add else []) + items
    return f


def add_from_other(claim_ref, refmap):
    """Copy a claim from the other pass, translating its local refs through refmap."""
    def f(b, other):
        c = copy.deepcopy(claim(other, claim_ref))
        s = json.dumps(c)
        for x, y in sorted(refmap.items(), key=lambda kv: -len(kv[0])):
            s = s.replace(f'"{x}"', f'"{y}"')
        b["claims"].append(json.loads(s))
    return f


def drop_claims(*refs):
    def f(b, other):
        b["claims"] = [c for c in b["claims"] if c["local_ref"] not in refs]
    return f


def drop_entities(*refs):
    def f(b, other):
        b["entities"] = [e for e in b["entities"] if e["local_ref"] not in refs]
    return f


def add_unsupported_from(pass_letter, ref):
    def f(b, other):
        src = json.loads((S0 / f"pass_{pass_letter}" / f"{UNIT[0]}.json").read_text())
        b.setdefault("unsupported", []).append(copy.deepcopy(next(u for u in src["unsupported"] if u["local_ref"] == ref)))
    return f


UNIT = [""]  # current unit, for add_unsupported_from

# (unit, id, kind, decision, reason, edit or None)
DECISIONS = [
    ("T1", "r1", "guideline-gap", "X defined_as: modality `defined`, role `definiens` (A, trace)",
     "G2: \"let X = …\" inside a definition stipulates the defined construction's variable; B's `supposed` premise reading follows §10.6's \"let\" literally", None),
    ("T1", "r2", "guideline-gap", "X defined_as: no `claim` condition on Z's section premise (B, trace)",
     "G3: premise `claim` nodes belong to conclusions (§10.7); a definiens is not one", drop_condition_claim("c_X_def", "c_Z_values")),
    ("T1", "r3", "guideline-gap", "`defines`: modality `asserted` (B, trace)", "G4: structural claims are asserted", set_q("c_defines", modality=None)),
    ("T1", "r4", "trace-corrected", "`parameter_role` claims kept (A and B)", "§10.3 asks a definition's roles (trace diff d8)", None),
    ("T1", "r5", "unsupported", "B's three unsupported items replace A's one", "B separates the probability space, its components and Z's relation to it; each is an expressible-later fact", take_unsupported_from_other(add=False)),
    ("T2", "r6", "guideline-gap", "Statement kind `remark`; identities with role `conclusion` (B, trace)",
     "The paragraph states a result about the parameters; §10.3 gives no remark/narrative criterion", None),
    ("T2", "r7", "guideline", "No `has_parameter` claims (A and B agree)", "§10.3 keeps only explicit claims in remarks; the trace's C2, C3 are not stated as such (trace diff d12, defensible)", None),
    ("T3", "r8", "guideline", "a + b X defined_as: role `definiens` (A, trace)", "§10.3 lists derived variables in theorems; B omitted the role", None),
    ("T4", "r9", "guideline-gap", "`defines` (LN, standard LN): modality `asserted` (B)", "G4", None),
    ("T4", "r10", "guideline-gap", "`parameter_role scale` for the scale parameter added (B)",
     "§10.3: the source names the role (\"the scale parameter\"); kept even though the canonical name says it, as in T1",
     add_from_other("c_scale_role", {"e_ln_scale": "p_scale", "st_def": "st1"})),
    ("T4", "r11", "trace-corrected", "s5 (standard normal → standard lognormal) annotated (A and B)", "The unit includes the second paragraph (trace diff d17)", None),
    ("U5", "r12", "guideline-gap", "Indexed premise as one claim on X_i with `member(i, {1, 2})`; conclusions `and(claim premise, independent(X_1, X_2))` (A)",
     "B's `forall i ∈ {1, 2}: claim premise` says the same; A's form is the simpler one and is used for U9 and U11 too", None),
    ("U6", "r13", "guideline-gap", "Two statements: the recalled definition (`remark`) and the corollary (B)",
     "s2 is introduced as \"a corollary of the last result\"; A's single narrative statement loses the claim-bearing kind", None),
    ("U6", "r14", "unsupported", "Both unsupported items kept: \"standard deviation σ > 0\" (A) and \"is the standard score of X\" (B)",
     "Each records a different gap: the schema has no standard-deviation-value predicate, and no standard-score relation", add_unsupported_from("a", "u1")),
    ("U6", "r15", "guideline-gap", "The \"last result\" is a local Statement stand-in (A and B, B's label)", "§10.2 does not say how to cite a statement outside the unit; both annotators made the same stand-in", None),
    ("U7", "r16", "guideline-gap", "No `refers_to` claims or stand-in statements for the bracketed cross-references (B)",
     "The facts about [14]…[26] are unsupported in both passes; links to statements whose targets are outside the unit add no claim", None),
    ("U8", "r17", "unsupported", "Means and sds as plain numbers; the unit cm and the setup sentence as unsupported items (B)",
     "A's \"1 cm\" as a formula would read c·m as symbols; `param_values` cannot carry units (witness_diff limit 1)", None),
    ("U9", "r18", "guideline-gap", "Indexed premise with `member(i, {1, …, n})`; conclusion with `claim` premise, `n ∈ ℕ₊`, `independent(X_1, X_2, X_n)` and the where-equalities (A)", "As r12", None),
    ("U10", "r19", "guideline-gap", "`defines`: modality `asserted` (B)", "G4", set_q("c_defines", modality=None)),
    ("U11", "r20", "guideline-gap", "Indexed premise and conclusions in A's form", "As r12", None),
    ("T4", "r21", "guideline-gap", "`defines`: set to asserted in the A-based batch", "G4 (applies r9)", None),
]


def t4_defines(b, other):
    for c in b["claims"]:
        if c["predicate"] == "defines":
            c.setdefault("qualifiers", {}).pop("modality", None)


EXTRA = {"T4": [t4_defines]}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for u in UNITS:
        UNIT[0] = u
        base = BASE[u]
        b = json.loads((S0 / f"pass_{base}" / f"{u}.json").read_text())
        other = json.loads((S0 / f"pass_{'b' if base == 'a' else 'a'}" / f"{u}.json").read_text())
        for du, _, _, _, _, edit in DECISIONS:
            if du == u and edit:
                edit(b, other)
        for f in EXTRA.get(u, []):
            f(b, other)
        (OUT / f"{u}.json").write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n")
    # contested: A claims not matched at the full tier with B in the aligner's a_vs_b run
    ab = (S0 / "compare" / "a_vs_b" / "alignment.txt").read_text().split("# unit ")[1:]
    contested = {}
    for block in ab:
        unit = block.split("\n", 1)[0].strip()
        lines = block.splitlines()
        core = eval(next(x for x in lines if x.startswith("core:"))[5:])  # noqa: S307 - our own output
        full = eval(next(x for x in lines if x.startswith("full:"))[5:])  # noqa: S307
        contested[unit] = {"a_core_not_full": sorted(a for a, _ in core if (a, _) not in full),
                           "note": "plus every claim that one pass has and the other lacks"}
    (OUT / "contested.json").write_text(json.dumps(contested, indent=1) + "\n")
    lines = ["# S0-D · Adjudication of passes A and B into the reference", "",
             "**Done:** 2026-10-28 by the root (Claude Opus 5.5), from the aligner's `compare/a_vs_b`",
             "run (after the instrument review's fixes) and `trace_diff.md`. Built by",
             "`code/s0d_reference.py`, which holds the same table; base pass per unit: " +
             ", ".join(f"{u} {BASE[u].upper()}" for u in UNITS) + ".", "",
             "Kinds: guideline (v0 decides it) · guideline-gap (v0 does not; the root chose; G1–G5 are",
             "the proposed rules in `trace_diff.md`) · trace-corrected · alternative · unsupported.", "",
             "| Unit | Id | Kind | Decision | Reason |", "|---|---|---|---|---|"]
    for u, i, k, d, r, _ in DECISIONS:
        lines.append(f"| {u} | {i} | {k} | {d} | {r} |")
    counts = {}
    for _, _, k, *_ in DECISIONS:
        counts[k] = counts.get(k, 0) + 1
    lines += ["", "Counts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".",
              "No difference was kept as an `alternatives` group: none was a reading of the text the",
              "other annotator would reject; all were representational choices the guideline leaves open.", ""]
    (S0 / "adjudication.md").write_text("\n".join(lines))
    print("wrote", OUT, "and adjudication.md;", counts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
