import time, collections, json
from pathlib import Path
from ast_grep_py import SgRoot
import tree_sitter_python as tsp
from tree_sitter import Language, Parser
FAM = "pydantic"
files = sorted(Path("python/corpus-structure/src").rglob("*.py"))
srcs = {p: p.read_text(encoding="utf-8") for p in files}
imports = {"rule": {"any": [
    {"kind": "import_statement", "has": {"kind": "dotted_name", "regex": rf"^{FAM}(\.|$)", "stopBy": "end"}},
    {"kind": "import_from_statement", "has": {"field": "module_name", "regex": rf"^{FAM}(\.|$)"}},
]}}
# call sites through a locally bound name or attribute rooted at family alias; keywords captured
calls = {"rule": {"kind": "call", "has": {"field": "function", "regex": r"^(Field|BaseModel|ConfigDict|model_validator|field_validator|pydantic\.)"}}}
kwrule = {"rule": {"kind": "keyword_argument", "inside": {"kind": "call", "has": {"field": "function", "regex": r"^(Field|pydantic\.Field)$"}}},
          }
t0 = time.perf_counter(); n_imp = n_call = 0; kw = collections.Counter(); err_files = []
for p, s in srcs.items():
    r = SgRoot(s, "python").root()
    n_imp += len(r.find_all(imports)); n_call += len(r.find_all(calls))
    for k in r.find_all(kwrule): kw[k.field("name").text()] += 1
    if r.find(kind="ERROR"): err_files.append(str(p))
t1 = time.perf_counter()
print(f"ast-grep-py: {len(files)} files, {n_imp} {FAM} import stmts, {n_call} candidate calls, ERROR-kind files={len(err_files)}, {t1-t0:.2f}s")
print("Field(...) keywords:", kw.most_common(10))
# tree-sitter: has_error / MISSING across repo
lang = Language(tsp.language()); parser = Parser(lang)
t2 = time.perf_counter(); bad = []
for p, s in srcs.items():
    tree = parser.parse(s.encode())
    if tree.root_node.has_error: bad.append(str(p))
t3 = time.perf_counter()
print(f"tree-sitter: has_error files={len(bad)} in {t3-t2:.2f}s", bad[:5])
print("grammar:", lang.name, lang.semantic_version, "abi", lang.abi_version)
# Python 3.14 syntax checks
for code in ['t"hi {x}"\n', 'try:\n  pass\nexcept A, B:\n  pass\n', 'def f[T: int = str](): ...\n', 'lazy import x\n']:
    tr = parser.parse(code.encode()); 
    try: SgRoot(code, "python").root(); sg="ok"
    except Exception as e: sg=repr(e)
    import ast
    try: ast.parse(code); a="ok"
    except SyntaxError as e: a="SyntaxError"
    import libcst
    try: libcst.parse_module(code); c="ok"
    except Exception as e: c=type(e).__name__
    print(repr(code[:24]), "ts.has_error=", tr.root_node.has_error, "ast:", a, "libcst:", c)
# non-Python languages in ast-grep-py
for lang_name, code in [("yaml","a: {b: 1}\n"),("toml","[a]\nb=1\n"),("markdown","# x\n`typer.Option`\n"),("json","{}"),("bash","echo")]:
    try: SgRoot(code, lang_name).root(); print("ast-grep-py lang", lang_name, "ok")
    except Exception as e: print("ast-grep-py lang", lang_name, "->", str(e)[:70])
