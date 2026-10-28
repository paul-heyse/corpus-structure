"""S0-R2: the reference conformed to guideline v1 (s0r2/guideline_v1.md) for the twelve core units.

    python3 code/s0r2_reference.py

Copies results/s0/reference_model/ to results/s0r2/reference_model_v1/ and applies the root's v1
decisions, each listed in DECISIONS with the rule it applies; everything else is unchanged. Convert
and validate with S0_SAMPLE=results/s0r2/sample.json code/s0_check.py ... --out results/s0r2/reference_v1.
"""

import json
import shutil
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent.parent
SRC = EVIDENCE / "results" / "s0" / "reference_model"
OUT = EVIDENCE / "results" / "s0r2" / "reference_model_v1"
DECISIONS = [
    ("T2", "c_X_normal", "§10.7 rule 1: a premise carries no restrictions; its conclusions are family-structure claims (rule 2), so the restrictions are not repeated"),
    ("U6", "c_Z_def", "§10.7 rule 2: a formula claim carries no claim nodes; its own restriction (σ > 0) stays"),
    ("U6", "c_score_formula", "§10.7 rule 2, as c_Z_def"),
    ("U6", "c_X_mean", "§10.7 rule 1: no condition references the premise any more, so it carries scope: statement"),
    ("U10", "b in c_X_def, c_X_gamma", "§10.7 bindings row 4: b first appears in the restriction 'if b ∈ (0, ∞)' and the definition names it the gamma's scale parameter, so family_param"),
    ("T1", "c_role_loc, c_role_scale (removed)", "§10.4: as T4 c_scale_role; the parameters are named location and scale"),
    ("T4", "c_scale_role (removed)", "§10.4: a parameter_role claim is added only when the role differs from the canonical name; p_scale is already named scale"),
    ("U12", "c_X_stdgamma (new)", "§10.2 context premise: the supposition in standing context c1 recorded once as an assumption statement; §10.7 rule 3: the conclusions reference it and repeat k ∈ (0, ∞); k binds param_of it"),
]


def claim(batch, ref):
    return next(c for c in batch["claims"] if c["local_ref"] == ref)


def drop_claim_nodes(tree):
    args = [a for a in tree.get("args", []) if a.get("op") != "claim"]
    return args[0] if len(args) == 1 else {**tree, "args": args}


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    shutil.copytree(SRC, OUT, ignore=shutil.ignore_patterns("contested.json"))
    load = lambda u: json.loads((OUT / f"{u}.json").read_text())  # noqa: E731
    save = lambda u, b: (OUT / f"{u}.json").write_text(json.dumps(b, indent=1, ensure_ascii=False) + "\n")  # noqa: E731

    b = load("T2")
    claim(b, "c_X_normal")["qualifiers"].pop("conditions", None)
    save("T2", b)

    b = load("U6")
    for r in ("c_Z_def", "c_score_formula"):
        q = claim(b, r)["qualifiers"]
        q["conditions"] = drop_claim_nodes(q["conditions"])
    claim(b, "c_X_mean")["qualifiers"]["scope"] = "statement"
    save("U6", b)

    b = load("U10")
    fp = {"bind": "family_param", "entity": "pG_scale"}

    def rebind(o):
        if isinstance(o, dict):
            if isinstance(o.get("symbols"), dict) and "b" in o["symbols"]:
                o["symbols"]["b"] = dict(fp)
            for v in o.values():
                rebind(v)
        elif isinstance(o, list):
            for v in o:
                rebind(v)
    for r in ("c_X_def", "c_X_gamma"):
        rebind(claim(b, r))
    save("U10", b)

    b = load("T4")
    b["claims"] = [c for c in b["claims"] if c["local_ref"] != "c_scale_role"]
    save("T4", b)

    b = load("T1")
    b["claims"] = [c for c in b["claims"] if c["local_ref"] not in ("c_role_loc", "c_role_scale")]
    save("T1", b)

    b = load("U12")
    b["statements"].insert(0, {"local_ref": "st0", "kind": "assumption", "anchor": ["c1"]})
    b["entities"].append({"local_ref": "SG", "type": "DistributionFamily", "label": "standard gamma distribution",
                          "scope": "global", "aliases": [], "identity": {}})
    k_free = {"t": "formula", "latex": "k", "symbols": {"k": {"bind": "free"}}}
    b["claims"].insert(0, {
        "local_ref": "c_X_stdgamma", "predicate": "has_distribution", "subject": "X", "object": {"ref": "SG"},
        "qualifiers": {"modality": "supposed", "param_values": {"shape": k_free}},
        "statement": "st0", "statement_role": "premise",
        "evidence": [{"sentence": "c1", "quote": "\\( X \\) has the standard gamma distribution with shape parameter \\( k \\in (0, \\infty) \\)",
                      "role": "primary"}]})
    k_of = {"t": "formula", "latex": "k", "symbols": {"k": {"bind": "param_of", "claim": "c_X_stdgamma", "param": "shape"}}}
    for r in ("c_X_mean", "c_X_var"):
        c = claim(b, r)
        c["object"] = k_of
        c["qualifiers"]["conditions"] = {"op": "and", "args": [
            {"op": "claim", "ref": "c_X_stdgamma"},
            {"op": "member", "x": k_of, "set": {"t": "set", "latex": "(0, \\infty)", "symbols": {}}}]}
    save("U12", b)
    (OUT / "decisions_v1.json").write_text(json.dumps(
        [{"unit": u, "item": i, "decision": d} for u, i, d in DECISIONS], indent=1, ensure_ascii=False) + "\n")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
