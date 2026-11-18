import ast, sys, time, tokenize, collections, symtable
from pathlib import Path
from importlib import metadata
root = Path("python/corpus-structure/src")
files = sorted(root.rglob("*.py"))
t0 = time.perf_counter()
top = collections.Counter(); fails = {}; lazy_local = collections.Counter(); dyn = collections.Counter(); n_imp = 0
for p in files:
    try:
        with tokenize.open(p) as f: src = f.read()
        tree = ast.parse(src, filename=str(p))
    except (SyntaxError, UnicodeError, OSError) as e:
        fails[str(p)] = type(e).__name__; continue
    # parent depth: module-level vs nested
    for node in tree.body:
        pass
    mod_level = {id(n) for n in tree.body}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names: top[a.name.split(".")[0]] += 1
            n_imp += 1
            if id(node) not in mod_level: lazy_local["nested"] += 1
        elif isinstance(node, ast.ImportFrom):
            n_imp += 1
            if node.level == 0 and node.module: top[node.module.split(".")[0]] += 1
            else: top["<relative>"] += 1
            if id(node) not in mod_level: lazy_local["nested"] += 1
        elif isinstance(node, ast.Call):
            f = node.func
            name = ast.unparse(f) if isinstance(f, (ast.Name, ast.Attribute)) else None
            if name in ("importlib.import_module", "import_module", "__import__", "getattr", "importlib.util.find_spec"):
                dyn[name] += 1
t1 = time.perf_counter()
print(f"ast: {len(files)} files, {n_imp} import stmts, {len(fails)} parse failures, {t1-t0:.2f}s")
print("nested (non-module-level) imports:", lazy_local["nested"])
print("dynamic-reference calls:", dict(dyn))
print("top import roots:", top.most_common(25))
t2 = time.perf_counter(); pd = metadata.packages_distributions(); t3 = time.perf_counter()
print(f"packages_distributions: {len(pd)} import names in {t3-t2:.3f}s")
for k in ["typer","rich","pydantic","yaml","libcst","ast_grep_py","tree_sitter","google","corpus_structure","psycopg","sqlalchemy","_cffi_backend"]:
    print(" ", k, "->", pd.get(k))
d = metadata.distribution("typer")
print("typer extras:", d.metadata.get_all("Provides-Extra"), "requires:", (d.requires or [])[:6])
print("typer entry points:", sorted((e.group, e.name) for e in d.entry_points))
# symtable sample
st = symtable.symtable(Path("python/corpus-structure/src/corpus_structure/schema/model_discovery.py").read_text(), "m.py", "exec")
print("symtable imported at module scope:", sorted(s.get_name() for s in st.get_symbols() if s.is_imported()))
