import time, collections, sys
from pathlib import Path
import libcst as cst
from libcst.metadata import MetadataWrapper, QualifiedNameProvider, PositionProvider, ScopeProvider, FullyQualifiedNameProvider, FullRepoManager
FAMILY = sys.argv[1] if len(sys.argv) > 1 else "pydantic"
root = Path("python/corpus-structure/src")
files = sorted(root.rglob("*.py"))
t0 = time.perf_counter(); mods = {}; fails = {}
for p in files:
    try: mods[p] = cst.parse_module(p.read_bytes())
    except Exception as e: fails[str(p)] = type(e).__name__ + ": " + str(e)[:80]
t1 = time.perf_counter()
print(f"libcst parse: {len(mods)}/{len(files)} ok, {len(fails)} failures, {t1-t0:.2f}s"); [print("  FAIL", k, v) for k, v in list(fails.items())[:5]]

class Census(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (QualifiedNameProvider, PositionProvider)
    def __init__(self): self.calls = collections.Counter(); self.kw = collections.Counter(); self.bases = collections.Counter(); self.decos = collections.Counter(); self.unres = 0
    def _q(self, node):
        return {q.name for q in self.get_metadata(QualifiedNameProvider, node, set())}
    def visit_Call(self, node):
        qs = [q for q in self._q(node.func) if q.split(".")[0] == FAMILY]
        for q in qs:
            self.calls[q] += 1
            for a in node.args:
                if a.keyword: self.kw[(q, a.keyword.value)] += 1
    def visit_ClassDef(self, node):
        for b in node.bases:
            for q in self._q(b.value):
                if q.split(".")[0] == FAMILY: self.bases[q] += 1
    def visit_Decorator(self, node):
        d = node.decorator.func if isinstance(node.decorator, cst.Call) else node.decorator
        for q in self._q(d):
            if q.split(".")[0] == FAMILY: self.decos[q] += 1

# Prefilter: only files that textually mention the family (cheap pass), as layering would do
hit = {p: m for p, m in mods.items() if FAMILY in m.code}
t2 = time.perf_counter(); c = Census()
for p, m in hit.items():
    MetadataWrapper(m, unsafe_skip_copy=True).visit(c)
t3 = time.perf_counter()
print(f"per-file QualifiedNameProvider on {len(hit)} hit files: {t3-t2:.2f}s")
t4 = time.perf_counter(); c2 = Census()
for p, m in mods.items():
    MetadataWrapper(m, unsafe_skip_copy=True).visit(c2)
t5 = time.perf_counter()
print(f"per-file QualifiedNameProvider on ALL {len(mods)} files: {t5-t4:.2f}s; same calls? {c.calls == c2.calls}")
print("calls:", c.calls.most_common(8)); print("kw:", c.kw.most_common(8)); print("bases:", c.bases.most_common(5)); print("decos:", c.decos.most_common(5))
# FullRepoManager on subset
sub = [str(p) for p in list(hit)[:40]]
t6 = time.perf_counter()
mgr = FullRepoManager("python/corpus-structure/src", sub, {FullyQualifiedNameProvider})
for s in sub:
    w = mgr.get_metadata_wrapper_for_path(s); w.resolve(FullyQualifiedNameProvider)
t7 = time.perf_counter()
print(f"FullRepoManager+FullyQualifiedNameProvider on {len(sub)} files: {t7-t6:.2f}s")
