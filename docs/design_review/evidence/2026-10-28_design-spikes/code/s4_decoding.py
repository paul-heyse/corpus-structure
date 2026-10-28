"""S4-D (decoding part): compile the decoding form in vLLM 0.31's structured-output backend, xgrammar
0.2.7, offline on CPU, with the served model's tokenizer; check that the grammar accepts the 15
canonical model-facing batches and rejects seeded invalid ones (D2 §7.3; variant V3).

    cd results/s4/xgrammar-env && UV_PROJECT_ENVIRONMENT=$REPO/build/spike-xgrammar-venv uv sync --locked && cd ../../..
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-xgrammar-venv uv run --project results/s4/xgrammar-env --locked python code/s4_decoding.py

Runs in the side environment (no linkml, no spike packages): reads only
results/s4/compiled/batch.decoding.schema.json and results/s4/compiled/decoding_inputs/*.json.
Writes results/s4/decoding.json. Backend log output (xgrammar warns on stderr when it downgrades a
oneOf it cannot prove disjoint, or ignores a keyword) is captured at the file-descriptor level.
"""

from __future__ import annotations

import json
import os
import resource
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

EV = Path(__file__).resolve().parent.parent
COMPILED = EV / "results" / "s4" / "compiled"
QWEN = Path.home() / ".cache/huggingface/hub/models--Qwen--Qwen3.5-9B/snapshots/c202236235762e1c871ad0ccb60c8ee5ba337b9a"


@contextmanager
def captured_stderr():
    buf = tempfile.TemporaryFile(mode="w+b")
    saved = os.dup(2)
    os.dup2(buf.fileno(), 2)
    out = {"text": ""}
    try:
        yield out
    finally:
        sys.stderr.flush()
        os.dup2(saved, 2)
        os.close(saved)
        buf.seek(0)
        out["text"] = buf.read().decode("utf-8", "replace")
        buf.close()


def main() -> int:
    import importlib.metadata as md

    import xgrammar as xgr
    from transformers import AutoTokenizer

    schema_text = (COMPILED / "batch.decoding.schema.json").read_text()
    schema = json.loads(schema_text)
    out: dict = {"versions": {p: md.version(p) for p in ("xgrammar", "torch", "transformers", "tokenizers", "apache-tvm-ffi")},
                 "tokenizer": {"repo": "Qwen/Qwen3.5-9B", "revision": QWEN.name},
                 "schema_bytes": len(schema_text.encode())}

    tok = AutoTokenizer.from_pretrained(str(QWEN))
    ti = xgr.TokenizerInfo.from_huggingface(tok)
    out["vocab_size"] = ti.vocab_size

    # backend-level grammar (tokenizer independent) and its warnings
    with captured_stderr() as err:
        t0 = time.perf_counter()
        g = xgr.Grammar.from_json_schema(schema_text)
        out["grammar_from_json_schema_s"] = round(time.perf_counter() - t0, 3)
    out["grammar_warnings"] = [l for l in err["text"].splitlines() if l.strip()]
    out["ebnf_bytes"] = len(str(g).encode())

    rss0 = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with captured_stderr() as err:
        comp = xgr.GrammarCompiler(ti, cache_enabled=True)
        t0 = time.perf_counter()
        cg = comp.compile_json_schema(schema_text)
        t1 = time.perf_counter()
        comp.compile_json_schema(schema_text)
        t2 = time.perf_counter()
        comp_nc = xgr.GrammarCompiler(ti, cache_enabled=False)
        t3 = time.perf_counter()
        comp_nc.compile_json_schema(schema_text)
        t4 = time.perf_counter()
    out["compile"] = {"outcome": "passed", "first_s": round(t1 - t0, 3), "cached_s": round(t2 - t1, 4),
                      "uncached_again_s": round(t4 - t3, 3), "memory_bytes": cg.memory_size_bytes if hasattr(cg, "memory_size_bytes") else None,
                      "max_rss_delta_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss - rss0,
                      "warnings": [l for l in err["text"].splitlines() if l.strip()]}

    def accepts(text: str, any_order: bool = False) -> bool:
        grammar = g if not any_order else xgr.Grammar.from_json_schema(schema_text, any_order=True)
        return xgr.testing._is_grammar_accept_string(grammar, text)

    acc = {}
    for f in sorted((COMPILED / "decoding_inputs").glob("*.json")):
        b = json.loads(f.read_text())
        acc[f.stem] = {"compact": accepts(json.dumps(b, ensure_ascii=False, separators=(",", ":"))),
                       "indented": accepts(json.dumps(b, ensure_ascii=False, indent=1))}
    out["accepts"] = acc
    out["accepted"] = sum(v["compact"] and v["indented"] for v in acc.values())
    out["batches"] = len(acc)

    # matcher on token ids: one batch end to end through the compiled (tokenized) grammar
    b = json.loads((COMPILED / "decoding_inputs" / "T3.json").read_text())
    ids = tok.encode(json.dumps(b, ensure_ascii=False, separators=(",", ":")), add_special_tokens=False)
    m = xgr.GrammarMatcher(cg)
    t0 = time.perf_counter()
    ok = all(m.accept_token(i) for i in ids)
    out["matcher_T3"] = {"tokens": len(ids), "accepted": ok, "completed": m.is_completed() if hasattr(m, "is_completed") else None,
                         "s": round(time.perf_counter() - t0, 3)}

    base = json.loads((COMPILED / "decoding_inputs" / "T3.json").read_text())

    def seed(name, mutate):
        x = json.loads(json.dumps(base))
        mutate(x)
        return {"seed": name, "accepted": accepts(json.dumps(x, ensure_ascii=False, separators=(",", ":")))}

    out["seeded"] = [
        seed("unknown predicate", lambda x: x["claims"][0].__setitem__("predicate", "has_distrib")),
        seed("modality not in enum", lambda x: x["claims"][0].setdefault("qualifiers", {}).__setitem__("modality", "assumed")),
        seed("bare LaTeX string in a formula position", lambda x: next(c for c in x["claims"] if c["object"].get("t") == "formula").__setitem__("object", "a + b \\mu")),
        seed("entity as a value (V1)", lambda x: x["claims"][0].__setitem__("object", {"t": "entity", "ref": "X"})),
        seed("null for an absent field", lambda x: x["claims"][0].__setitem__("statement_role", None)),
        seed("Statement in entities[] (V2)", lambda x: x["entities"].append({"local_ref": "st9", "type": "Statement", "label": "r", "scope": "local", "extent": "section"})),
        seed("qualifier of another predicate", lambda x: x["claims"][0].setdefault("qualifiers", {}).__setitem__("transform", {"t": "formula", "latex": "e^Y"})),
    ]
    out["seeded_rejected"] = sum(not s["accepted"] for s in out["seeded"])
    # the author key order (not the schema's) is accepted only with any_order
    raw = json.loads((COMPILED / "decoding_inputs" / "T1.json").read_text())
    reordered = {k: raw[k] for k in ("unit_ref", "statements", "entities", "claims", "alternatives", "unsupported") if k in raw}
    out["key_order"] = {"author_order_default": accepts(json.dumps(reordered)), "author_order_any_order": accepts(json.dumps(reordered), any_order=True)}
    # which oneOf the backend cannot prove disjoint: each oneOf alone (with the $defs) compiled
    def oneofs(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "oneOf":
                    yield path, node
                yield from oneofs(v, f"{path}/{k}")
        elif isinstance(node, list):
            for i, v in enumerate(node):
                yield from oneofs(v, f"{path}/{i}")

    diag = []
    for path, node in oneofs(schema, "#"):
        sub = {"$defs": schema["$defs"], "oneOf": node["oneOf"]}
        # a separate process per oneOf, because the backend's log lines are not flushed per call
        import subprocess

        r = subprocess.run([sys.executable, "-c", "import sys,xgrammar as x; x.Grammar.from_json_schema(sys.stdin.read())"],
                           input=json.dumps(sub), capture_output=True, text=True)
        err = {"text": r.stderr + r.stdout}
        tags = []
        for br in node["oneOf"]:
            b = schema["$defs"][br["$ref"].split("/")[-1]] if "$ref" in br else br
            tags.append({p: (s.get("const", s.get("enum"))) for p, s in (b.get("properties") or {}).items() if "const" in s or "enum" in s})
        diag.append({"path": path, "branches": len(node["oneOf"]), "downgraded": "falling back to anyOf" in err["text"],
                     "tag_properties": sorted({k for t_ in tags for k in t_})})
    out["oneof_diagnosis"] = diag
    (EV / "results" / "s4" / "decoding.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n")
    print(json.dumps(out, indent=1, ensure_ascii=False)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
