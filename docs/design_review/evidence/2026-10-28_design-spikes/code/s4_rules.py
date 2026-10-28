"""S4-C: compile the pack's rules and guideline warnings; run them at both call sites; seed one
violation per rule; compare the guideline group with S0-R2's Python checker (brief steps 6 and 7).

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run --locked python code/s4_rules.py

Inputs: the pack (results/s4/schema/), the v1 model-facing reference and the worked examples in their
canonical shape (code/s4/sidetable.canonicalize), code/s0r2_rules.py, and the math grammar through the
I-R2 instruments (code/instruments/values.py) for the finalize reader. Writes results/s4/rules.tsv,
results/s4/rules_compile.json and results/s4/rules_seeds.json.
"""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import time
from pathlib import Path

CODE = Path(__file__).resolve().parent
sys.path.insert(0, str(CODE))
from s4 import paths  # noqa: E402
from s4 import rules as R  # noqa: E402
from s4.pack import Pack  # noqa: E402
from s4.sidetable import canonicalize  # noqa: E402

import s0r2_rules  # noqa: E402

OUT = paths.RES


def batches(dirs=("reference_model_v1", "examples")) -> dict[str, dict]:
    out = {}
    for d in dirs:
        for f in sorted((paths.R2 / d).glob("*.json")):
            if f.stem[0] in "TUE" and f.stem[1:].isdigit():
                out[f.stem] = canonicalize(paths.load_batch(f)[0])[0]
    return out


def grammar_reader():
    """The finalize reader: the math grammar's status under the slot kind, and the kind it reads."""
    try:
        from instruments.values import math_parse
    except Exception as e:  # noqa: BLE001
        return None, f"blocked: math grammar not importable ({e})"

    def read(latex: str, slot: str) -> tuple[str, str | None]:
        r = math_parse(latex, "set_expr" if slot == "set" else "formula")
        if r.status in ("ok", "partial"):
            return ("ok" if r.status == "ok" else r.status), slot
        any_ = math_parse(latex, "any_value")
        kind = {"set_expr": "set", "formula": "formula"}.get(any_.kind, any_.kind) if any_.status != "failed" else None
        return r.status, kind

    files = sorted((CODE / "mathgrammar").glob("*")) + [CODE / "instruments" / "values.py"]
    h = hashlib.sha256(b"".join(f.read_bytes() for f in files if f.is_file())).hexdigest()
    return read, f"code/mathgrammar + instruments/values.py sha256 {h}"


def attach_parse(cs: R.CandidateSet, read) -> int:
    n = 0
    for c in cs.candidates:
        if c.value and c.value.get("t") in ("formula", "set"):
            cs.parse_info[(c.id, c.value["latex"])] = read(c.value["latex"], c.value["t"])
            n += 1
    return n


def run_site(pack, rules, bs: dict[str, dict], site: str, read=None) -> list[dict]:
    vb = R.ViewBuilder(pack)
    if site == "batch":
        rows = []
        for u, b in bs.items():
            for r in R.run(rules, vb.build(R.from_batch(b, scope=u)), "batch"):
                rows.append({**r, "unit": u})
        return rows
    cs = R.from_pool(bs, pack)
    if read:
        attach_parse(cs, read)
    return [{**r, "unit": r["scope"]} for r in R.run(rules, vb.build(cs), "finalize")]


# ---------------------------------------------------------------------------------- negative compiles


NEGATIVE = {
    "misspelled attribute": "claim.qualifers.modality == 'asserted'",
    "attribute access on a nullable value": "claim.object.label == 'x'",
    "wrong function argument type": "$is_a(claim.evidence_count, 'Entity')",
    "unknown root symbol": "clam.predicate == 'x'",
    "nondeterministic builtin $now": "$now > $today",
    "D2 §7.4's earlier form: all(...) is not a symbol": "all([k in claim.family_params for k in claim.qualifiers.param_values.keys])",
    "keyword argument in a call (D6 §7.3's earlier form)": "$is_a(claim.subject.type, target='Entity')",
}


def negative_compiles(lang) -> list[dict]:
    out = []
    for name, expr in NEGATIVE.items():
        try:
            lang.compile(expr)
            out.append({"case": name, "expr": expr, "outcome": "compiled (unexpected)"})
        except Exception as e:  # noqa: BLE001
            out.append({"case": name, "expr": expr, "outcome": f"rejected: {type(e).__name__}: {str(e)[:160]}"})
    return out


# ------------------------------------------------------------------------------------------- seeds


def find(b, pred=None, role=None, f=None):
    for c in b["claims"]:
        if (pred is None or c["predicate"] == pred) and (role is None or c.get("statement_role") == role) and (f is None or f(c)):
            return c
    raise LookupError((pred, role))


def _formula_with(b, bind):
    for c in b["claims"]:
        for v in [c["object"], *((c.get("qualifiers") or {}).get("param_values") or {}).values()]:
            for s, x in (v.get("symbols") or {}).items() if isinstance(v, dict) else []:
                if x["bind"] == bind:
                    return c, v, s
    raise LookupError(bind)


def seeds(bs: dict[str, dict]) -> list[dict]:
    """(rule, site, unit, claim local ref, mutation) per rule; each mutation copies one batch."""
    out = []

    def add(rule, site, unit, desc, mutate):
        b = copy.deepcopy(bs[unit])
        ref = mutate(b)
        out.append({"rule": rule, "site": site, "unit": unit, "claim": ref, "mutation": desc, "batch": b})

    def m_structural(b):
        c = find(b, "proves")
        c["statement_role"] = "conclusion"
        return c["local_ref"]

    def m_role(b):
        c = find(b, "has_distribution", "premise")
        c["statement_role"] = "example_value"
        return c["local_ref"]

    def m_modality(b):
        c = find(b, "has_distribution", "premise")
        c["qualifiers"]["modality"] = "asserted"
        return c["local_ref"]

    def m_struct_cond(b):
        c = find(b, "proves")
        c["qualifiers"]["conditions"] = {"op": "claim", "ref": find(b, "has_distribution", "premise")["local_ref"]}
        return c["local_ref"]

    def m_premise_cond(b):
        c = find(b, "has_distribution", "premise")
        c["qualifiers"]["conditions"] = {"op": "member", "x": {"t": "formula", "latex": "a", "symbols": {}},
                                         "set": {"t": "set", "latex": "\\R", "symbols": {}}}
        return c["local_ref"]

    def m_form_claim(b):
        c = find(b, "defined_as", "definiens")
        c["qualifiers"]["conditions"] = {"op": "claim", "ref": find(b, "has_distribution", "premise")["local_ref"]}
        return c["local_ref"]

    def m_premise_ref(b):
        c = find(b, "has_distribution", "conclusion")
        c["qualifiers"].pop("conditions", None)
        return c["local_ref"]

    def m_param_role(b):
        c = find(b, "parameter_role")
        e = next(e for e in b["entities"] if e["local_ref"] == c["subject"])
        e["identity"]["canonical_name"] = c["object"]["v"]
        return c["local_ref"]

    def m_formula_var(b):
        c = find(b, "defined_as", "definiens")
        c["object"]["latex"] = "X = " + c["object"]["latex"]
        return c["local_ref"]

    def m_backslash(b):
        c, v, s = _formula_with(b, "param_of")
        v["symbols"] = {("\\" + k if k == s else k): x for k, x in v["symbols"].items()}
        return c["local_ref"]

    def m_priority(b):
        c, v, s = _formula_with(b, "param_of")
        v["symbols"][s] = {"bind": "free"}
        return c["local_ref"]

    def m_param_keys(b):
        c = find(b, "has_distribution", "premise")
        c["qualifiers"]["param_values"]["kurtosis"] = {"t": "formula", "latex": "3", "symbols": {}}
        return c["local_ref"]

    def m_one_dist(b):
        c = find(b, "has_distribution", "conclusion")
        d = copy.deepcopy(c)
        d["local_ref"] = c["local_ref"] + "_dup"
        b["claims"].append(d)
        return c["local_ref"]

    def m_domain(b):
        c = find(b, "parameter_domain")
        c["object"]["latex"] = "\\frac{"
        return c["local_ref"]

    def m_no_family(b):
        c = find(b, "has_parameter")
        c["subject"] = next(e["local_ref"] for e in b["entities"] if e["type"] == "RandomVariable")
        return c["local_ref"]

    def m_value_kind(b):
        c = find(b, "defined_as", "definiens")
        c["object"]["latex"] = "x \\in \\R"
        return c["local_ref"]

    add("guideline.structural_role_modality", "batch", "T3", "a proves claim given statement_role conclusion", m_structural)
    add("guideline.role_by_kind", "batch", "T3", "a theorem premise given role example_value", m_role)
    add("guideline.modality_by_role", "batch", "T3", "a premise given modality asserted", m_modality)
    add("guideline.structural_no_conditions", "batch", "T3", "a proves claim given a claim node", m_struct_cond)
    add("guideline.premise_conditions_index_only", "batch", "T3", "a premise given a restriction a ∈ ℝ", m_premise_cond)
    add("guideline.no_claim_nodes_on_form", "batch", "T3", "a defined_as definiens given a claim node", m_form_claim)
    add("guideline.references_a_premise", "batch", "T3", "a conclusion's conditions removed", m_premise_ref)
    add("guideline.parameter_role_differs", "batch", "T4", "the parameter's canonical name set to its stated role", m_param_role)
    add("guideline.formula_excludes_defined_variable", "batch", "T3", "a defined_as formula written with 'X ='", m_formula_var)
    add("guideline.symbol_keys_no_backslash", "batch", "T3", "a binding key written with a backslash", m_backslash)
    add("guideline.binding_priority", "batch", "T3", "a param_of binding rewritten as free", m_priority)
    add("stat.param_keys_known", "finalize", "T3", "a param_values key 'kurtosis' added", m_param_keys)
    add("stat.one_distribution_per_statement", "batch", "T3", "a conclusion has_distribution duplicated", m_one_dist)
    add("stat.domain_is_set", "finalize", "T1", "a parameter_domain set rewritten as '\\frac{'", m_domain)
    add("stat.no_family_on_variable", "batch", "T1", "has_parameter given a random variable as subject", m_no_family)
    add("core.value_kind_matches_slot", "finalize", "T3", "a defined_as formula rewritten as a membership x ∈ ℝ", m_value_kind)
    return out


def main() -> int:
    pack = Pack()
    lang = R.Language(pack)
    t0 = time.perf_counter()
    rules = R.compile_rules(pack, lang)
    compile_ms = (time.perf_counter() - t0) * 1000
    read, reader_note = grammar_reader()
    bs = batches()
    pool_units = {u: b for u, b in bs.items() if u[0] in "TU"}

    t0 = time.perf_counter()
    rows = run_site(pack, rules, bs, "batch") + run_site(pack, rules, pool_units, "finalize", read)
    run_ms = (time.perf_counter() - t0) * 1000
    for r in rows:
        r["expected"] = "pass"
        r["seed"] = ""

    # function form of the pack view (OPEN-D2-3): stat.param_keys_known with $family_params(id)
    flang = R.Language(pack, function_form=True)
    cs = R.from_pool(pool_units, pack)
    views = R.ViewBuilder(pack).build(cs)
    by_id = {v.id: v for v in views}
    calls = {"n": 0}

    def family_params(fid: str):
        calls["n"] += 1
        return tuple(sorted({v.object.identity.get("canonical_name") for v in views
                             if v._candidate.predicate == "has_parameter" and v.subject.id == fid and v.object is not None} - {None}))

    fexpr = ("$all([k in $family_params(claim.object&.id ?? '') or k in $enums['ParameterRole'] "
             "for k in (claim.qualifiers.param_values ?? {}).keys])")
    frule = flang.compile(fexpr, pool_fn=family_params)
    arule = next(r for r in rules if r.id == "stat.param_keys_known")
    agree = []
    for v in views:
        if v._candidate.predicate == "has_distribution":
            fv = frule.matches({"claim": V2(v)})
            av = arule.check.matches({"claim": v})
            agree.append(fv == av)

    # seeds
    seed_rows = []
    for s in seeds(bs):
        target = s["rule"]
        if s["site"] == "batch":
            got = R.run(rules, R.ViewBuilder(pack).build(R.from_batch(s["batch"], scope=s["unit"])), "batch")
            hit = [g for g in got if g["rule"] == target and g["claim"] == s["claim"] and g["result"] == "fire"]
            others = sorted({g["rule"] for g in got if g["result"] == "fire" and g["rule"] != target})
        else:
            pool = dict(pool_units, **{s["unit"]: s["batch"]})
            cs2 = R.from_pool(pool, pack)
            if read:
                attach_parse(cs2, read)
            got = R.run(rules, R.ViewBuilder(pack).build(cs2), "finalize")
            key = f"clm:{s['unit']}:{s['claim']}"
            hit = [g for g in got if g["rule"] == target and g["claim"] == key and g["result"] == "fire"]
            others = sorted({g["rule"] for g in got if g["result"] == "fire" and g["rule"] != target})
        py = s0r2_rules.rule_warnings(s["batch"]) if target.startswith("guideline.") else None
        seed_rows.append({"rule": target, "site": s["site"], "unit": s["unit"], "claim": s["claim"], "mutation": s["mutation"],
                          "caught": bool(hit), "also_fired": others, "s0r2_rules_warns": None if py is None else bool(py)})
        rows.append({"rule": target, "grp": next(r.grp for r in rules if r.id == target), "severity": next(r.severity for r in rules if r.id == target),
                     "site": s["site"], "claim": s["claim"], "scope": s["unit"], "unit": s["unit"],
                     "result": "fire" if hit else "pass", "expected": "fire", "seed": s["mutation"]})

    # parity with the Python checker on the unseeded batches
    parity = {u: {"s0r2_rules": len(s0r2_rules.rule_warnings(b)),
                  "rule_engine_guideline": sum(1 for r in rows if r["unit"] == u and r["site"] == "batch" and not r["seed"]
                                               and r["grp"] == "guideline" and r["result"] == "fire")} for u, b in bs.items()}

    cols = ["rule", "grp", "site", "unit", "claim", "expected", "result", "seed"]
    (OUT / "rules.tsv").write_text("\t".join(cols) + "\n" + "".join("\t".join(str(r.get(c, "")) for c in cols) + "\n" for r in rows))
    summary = {
        "rules_compiled": len(rules), "by_group": {g: sum(r.grp == g for r in rules) for g in ("rules", "guideline")},
        "compile_ms": round(compile_ms, 1), "run_ms": round(run_ms, 1),
        "evaluations": sum(1 for r in rows if not r["seed"]),
        "unexpected_fires": [r for r in rows if not r["seed"] and r["result"] == "fire"],
        "seeds": len(seed_rows), "seeds_caught": sum(s["caught"] for s in seed_rows),
        "guideline_seeds_s0r2_warns": sum(1 for s in seed_rows if s["s0r2_rules_warns"]),
        "guideline_seeds": sum(1 for s in seed_rows if s["s0r2_rules_warns"] is not None),
        "parity": parity, "parity_ok": all(v["s0r2_rules"] == v["rule_engine_guideline"] == 0 for v in parity.values()),
        "function_form": {"expr": fexpr, "compiled": True, "has_distribution_claims": len(agree), "agree_with_attribute_form": sum(agree),
                          "function_calls": calls["n"]},
        "negative_compiles": negative_compiles(lang),
        "finalize_reader": reader_note,
        "pool": {"units": sorted(pool_units), "claims": len(cs.candidates)},
    }
    (OUT / "rules_compile.json").write_text(json.dumps(summary, indent=1, ensure_ascii=False, sort_keys=True) + "\n")
    (OUT / "rules_seeds.json").write_text(json.dumps(seed_rows, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps({k: v for k, v in summary.items() if k not in ("parity",)}, indent=1, ensure_ascii=False)[:4000])
    for s in seed_rows:
        print(s["caught"], s["rule"], s["also_fired"], s["s0r2_rules_warns"])
    return 0


def V2(v):
    """The same view without the pack-view attribute, as the function form's context declares it."""
    w = copy.copy(v)
    w.__dict__.pop("family_params", None)
    return w


if __name__ == "__main__":
    sys.exit(main())
