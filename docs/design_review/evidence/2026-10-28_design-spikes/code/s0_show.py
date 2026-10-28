"""Print a stored or model-facing batch compactly: one line per entity, statement and claim.

    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/s0_show.py BATCH.json [...]
"""

from __future__ import annotations

import json
import sys


def val(v) -> str:
    if isinstance(v, dict):
        if "ref" in v and "t" not in v:
            return f"→{v['ref']}"
        t = v.get("t")
        if t in ("formula", "set"):
            syms = ",".join(f"{k}:{b.get('bind')}{'='+(b.get('entity') or b.get('claim') or '') if (b.get('entity') or b.get('claim')) else ''}"
                            for k, b in (v.get("symbols") or {}).items())
            return f"{t}«{v.get('latex')}»" + (f"[{syms}]" if syms else "")
        if t == "enum":
            return f"{v.get('enum')}.{v.get('v')}"
        if t in ("number", "text", "bool", "date"):
            return f"{t}:{v.get('v')}{' '+v['unit'] if v.get('unit') else ''}"
        if "op" in v:
            return cond(v)
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def cond(c) -> str:
    if not isinstance(c, dict):
        return str(c)
    op = c.get("op")
    if op in ("and", "or"):
        return f"{op}(" + ", ".join(cond(a) for a in c["args"]) + ")"
    if op == "not":
        return f"not({cond(c['arg'])})"
    if op == "claim":
        return f"claim {c['ref']}"
    if op == "member":
        return f"{val(c['x']) if isinstance(c['x'], dict) else c['x']}∈{val(c['set']) if isinstance(c['set'], dict) else c['set']}"
    if op == "cmp":
        return f"{c['lhs']}{c['rel']}{c['rhs']}"
    if op == "pred":
        return f"{c['name']}(" + ", ".join(val(a) if isinstance(a, dict) else str(a) for a in c["args"]) + ")"
    if op == "forall":
        return f"∀{c['var']}∈{c['set']}:{cond(c['body'])}"
    return f"{op}«{c.get('text', '')[:40]}»"


def show(path: str) -> None:
    b = json.load(open(path))
    print(f"### {path}")
    for e in b.get("entities", []):
        print(f"  E {e['local_ref']}: {e['type']} '{e.get('label')}' {e['scope']}{'/'+e['extent'] if e.get('extent') else ''}"
              f"{' sym='+e['symbol'] if e.get('symbol') else ''}{' id='+json.dumps(e['identity'], ensure_ascii=False) if e.get('identity') else ''}")
    for s in b.get("statements", []):
        print(f"  S {s['local_ref']}: {s['kind']}")
    for c in b.get("claims", []):
        q = dict(c.get("qualifiers") or {})
        mod = q.pop("modality", "asserted")
        cd = q.pop("conditions", None)
        rest = " ".join(f"{k}={val(v) if not isinstance(v, dict) or 't' in v or 'op' in v else '{'+', '.join(f'{kk}:{val(vv)}' for kk, vv in v.items())+'}'}"
                        for k, v in q.items())
        print(f"  C {c['local_ref']}: {c['subject']} {c['predicate']} {val(c['object'])} [{mod}]"
              f"{' '+rest if rest else ''}{' | '+cond(cd) if cd else ''}"
              f"{' @'+str(c.get('statement'))+'/'+str(c.get('statement_role')) if c.get('statement') else ''}")
    for a in b.get("alternatives", []):
        print(f"  ALT {a['refs']}: {a['reason'][:80]}")
    for u in b.get("unsupported", []):
        print(f"  U {u.get('local_ref')}: «{(u.get('quote') or u.get('text') or '')[:70]}» — {u.get('reason', '')[:70]}")


if __name__ == "__main__":
    for p in sys.argv[1:]:
        show(p)
