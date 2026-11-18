import collections, time
from pathlib import Path
from ast_grep_py import SgRoot
files = sorted(Path("python/corpus-structure/src").rglob("*.py"))
kwrule = {"rule": {"kind": "keyword_argument",
  "inside": {"kind": "argument_list", "inside": {"kind": "call", "has": {"field": "function", "regex": r"^(Field|pydantic\.Field)$"}}}}}
pat = {"rule": {"pattern": "Field($$$ARGS)"}}
kw = collections.Counter(); n = 0; t0=time.perf_counter()
for p in files:
    r = SgRoot(p.read_text(), "python").root()
    for k in r.find_all(kwrule): kw[k.field("name").text()] += 1
    for m in r.find_all(pat):
        n += 1; m.get_multiple_matches("ARGS")
print(f"{time.perf_counter()-t0:.2f}s Field(...) pattern hits={n}; keywords:", kw.most_common(8))
r = SgRoot("def f[T: int = str](): ...\n", "python").root()
print("PEP696 ERROR node in ast-grep-py:", r.find(kind="ERROR") is not None)
m = SgRoot("x = Field(1, alias='y')\n", "python").root().find(pattern="Field($$$ARGS)")
print("$$$ARGS kinds:", [a.kind() for a in m.get_multiple_matches("ARGS")])
for lang in ["markdown", "html", "json", "bash"]:
    try: SgRoot("# x\n", lang); print(lang, "ok")
    except BaseException as e: print(lang, type(e).__name__, isinstance(e, Exception))
