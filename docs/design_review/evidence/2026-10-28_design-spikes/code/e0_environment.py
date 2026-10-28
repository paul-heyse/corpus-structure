"""E0: record the spike environment and check that every library imports and loads.

Run from the evidence folder:
    UV_PROJECT_ENVIRONMENT=$REPO/build/spike-venv uv run python code/e0_environment.py
Writes results/environment.json. Exits non-zero if any check fails.
"""

from __future__ import annotations

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
    checks: dict[str, str] = {}
    for name in MODULES:
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

    record = {
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
    out = HERE / "results" / "environment.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    failed = {k: v for k, v in checks.items() if not v.startswith("passed")}
    print(json.dumps(failed or {"all checks": "passed"}, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
