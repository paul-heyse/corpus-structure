"""E0/E4: record a spike environment and check that every library imports and loads.

Run from the evidence folder:
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/e0_environment.py [--name cpu]
Without --name it runs E0's module set and writes results/environment.json (record e0.environment).
With --name <env> it runs that environment's module set and checks and writes
results/environment-<env>.json (E4: `cpu` is record e4.env-cpu). Exits non-zero if any check fails.
"""

from __future__ import annotations

import argparse
import datetime
import importlib
import importlib.metadata as md
import json
import platform
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
HF = Path.home() / ".cache/huggingface/hub"
TOKENIZERS = {
    "qwen3.5-9b": "models--Qwen--Qwen3.5-9B",
    "gliner2.5-base-v1": "models--fastino--gliner2.5-base-v1",
}
MODULES = [
    "lxml.etree", "lxml.html", "lxml.html.html5parser", "lxml.cssselect", "html5lib",
    "cssselect", "cssselect2", "trafilatura", "pylatexenc.latexwalker", "pylatexenc.latex2text",
    "sympy", "sympy.parsing.latex", "lark", "spacy", "spacy_curated_transformers", "torch",
    "tokenizers", "pydantic", "linkml_runtime.utils.schemaview", "rapidfuzz", "scipy.optimize",
    "statsmodels.stats.inter_rater", "numpy", "yaml",
]
# E4 environments: name -> modules beyond E0's. `cpu` adds S4 (rules, schema oracle, GLiNER2
# dicts), S6 (PostgreSQL driver, pgvector adapter) and S5's solver.
ENVIRONMENTS = {
    "cpu": MODULES + [
        "rule_engine", "jsonschema", "z3", "psycopg", "pgvector", "pgvector.psycopg", "gliner2",
        "gliner2.inference.schema", "gliner2.inference.engine", "transformers", "corpus_evidence",
    ],
}


def extra_checks(name: str, checks: dict[str, str]) -> None:
    """Functional checks beyond imports for an E4 environment."""
    if name != "cpu":
        return
    try:
        import z3
        x, y = z3.Ints("x y")
        s = z3.Solver()
        s.add(x + y == 10, x - y == 4)
        ok = s.check() == z3.sat and s.model()[x].as_long() == 7 and s.model()[y].as_long() == 3
        checks["z3 trivial solve (x+y=10, x-y=4)"] = "passed (x=7, y=3)" if ok else f"failed: {s.check()}"
    except Exception as exc:
        checks["z3 trivial solve (x+y=10, x-y=4)"] = f"failed: {exc!r}"
    try:
        from gliner2 import Schema
        d = Schema().entities(["distribution", "parameter"]).to_dict()
        ok = Schema.from_dict(d).to_dict() == d
        checks["gliner2 Schema.from_dict(d).to_dict() == d (entities only)"] = "passed" if ok else f"failed: {d!r}"
    except Exception as exc:
        checks["gliner2 Schema.from_dict(d).to_dict() == d (entities only)"] = f"failed: {exc!r}"
    try:
        import psycopg
        impl = psycopg.pq.__impl__
        checks["psycopg libpq implementation"] = f"passed ({impl})" if impl == "binary" else f"failed: {impl}"
    except Exception as exc:
        checks["psycopg libpq implementation"] = f"failed: {exc!r}"
    try:
        import rule_engine
        rule = rule_engine.Rule("kind == 'definition' and size > 2")
        ok = rule.matches({"kind": "definition", "size": 3}) and not rule.matches({"kind": "theorem", "size": 3})
        checks["rule_engine trivial rule"] = "passed" if ok else "failed"
    except Exception as exc:
        checks["rule_engine trivial rule"] = f"failed: {exc!r}"


def snapshot(repo_dir: str) -> dict:
    base = HF / repo_dir
    snaps = sorted(p for p in (base / "snapshots").iterdir() if p.is_dir())
    ref = base / "refs" / "main"
    return {
        "revision": ref.read_text().strip() if ref.exists() else snaps[-1].name,
        "revision_source": "refs/main" if ref.exists() else "only snapshot present",
        "tokenizer_json": str(snaps[-1] / "tokenizer.json"),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", choices=sorted(ENVIRONMENTS), help="E4 environment; omit for E0")
    env = ap.parse_args().name
    checks: dict[str, str] = {}
    for name in ENVIRONMENTS[env] if env else MODULES:
        try:
            importlib.import_module(name)
            checks[f"import {name}"] = "passed"
        except Exception as exc:  # recorded, not raised: the record lists every failure
            checks[f"import {name}"] = f"failed: {exc!r}"

    from lxml import etree

    import spacy
    for model in ("en_core_web_sm", "en_core_web_trf"):
        try:
            nlp = spacy.load(model)
            doc = nlp("Suppose that X is normal. Then a + bX is normal.")
            checks[f"spacy.load {model}"] = f"passed ({len(list(doc.sents))} sentences)"
        except Exception as exc:
            checks[f"spacy.load {model}"] = f"failed: {exc!r}"

    from tokenizers import Tokenizer
    tok_info = {}
    for key, repo in TOKENIZERS.items():
        info = snapshot(repo)
        try:
            n = len(Tokenizer.from_file(info["tokenizer_json"]).encode(r"a + b \mu").ids)
            checks[f"tokenizer {key}"] = f"passed ({n} tokens for a probe string)"
        except Exception as exc:
            checks[f"tokenizer {key}"] = f"failed: {exc!r}"
        tok_info[key] = info

    import cssselect2
    import lxml.html
    root = lxml.html.document_fromstring("<html><body><div class='unit'><p class='dfn'>x</p></div></body></html>")
    wrapper = cssselect2.ElementWrapper.from_html_root(root)
    matched = list(wrapper.query_all("div.unit > p.dfn"))
    checks["cssselect2 over an lxml.html root"] = "passed" if len(matched) == 1 else f"failed: {len(matched)} matches"

    if env:
        extra_checks(env, checks)

    record = {
        **({"environment": env} if env else {}),
        "recorded": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        "python": sys.version,
        "platform": platform.platform(),
        "libxml2": ".".join(map(str, etree.LIBXML_VERSION)),
        "libxml2_compiled": ".".join(map(str, etree.LIBXML_COMPILED_VERSION)),
        "libxslt": ".".join(map(str, etree.LIBXSLT_VERSION)),
        "lxml": ".".join(map(str, etree.LXML_VERSION)),
        "spacy_models": {m: md.version(m) for m in ("en_core_web_sm", "en_core_web_trf")},
        "tokenizers": tok_info,
        "packages": dict(sorted((d.metadata["Name"].lower(), d.version) for d in md.distributions())),
        "checks": checks,
    }
    out = HERE / "results" / (f"environment-{env}.json" if env else "environment.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    failed = {k: v for k, v in checks.items() if not v.startswith("passed")}
    print(json.dumps(failed or {"all checks": "passed"}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
