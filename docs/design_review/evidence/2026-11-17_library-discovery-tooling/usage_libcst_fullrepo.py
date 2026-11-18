import time
from pathlib import Path
import libcst as cst
from libcst.metadata import FullRepoManager, FullyQualifiedNameProvider, QualifiedNameProvider, MetadataWrapper
root = Path("python/corpus-structure/src").resolve()
rel = sorted(str(p) for p in root.rglob("*.py") if "pydantic" in p.read_text())[:40]
t0 = time.perf_counter()
for s in rel: MetadataWrapper(cst.parse_module((root/s).read_bytes()), unsafe_skip_copy=True).resolve(QualifiedNameProvider)
t1 = time.perf_counter()
mgr = FullRepoManager(str(root), rel, {FullyQualifiedNameProvider})
fq = None
for s in rel:
    fq = mgr.get_metadata_wrapper_for_path(s).resolve(FullyQualifiedNameProvider)
t2 = time.perf_counter()
print(f"40 files: per-file QualifiedNameProvider {t1-t0:.2f}s; FullRepoManager+FullyQualifiedNameProvider {t2-t1:.2f}s")
print("sample FQN of relative import:", sorted({q.name for v in fq.values() for q in v if q.source.name=='IMPORT' and q.name.startswith('corpus_structure')})[:3])
