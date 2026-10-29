"""Timing of release preparation for CBO-003 (statistics pack): acquire, then cold/second preparation with phase timers.

Usage: probe_prepare_timing.py acquire <inputs.pkl> | probe_prepare_timing.py time <inputs.pkl>
"""
import time, sys, pickle
T={}
def wrap(mod, name):
    f=getattr(mod,name)
    def w(*a,**k):
        t=time.perf_counter()
        try: return f(*a,**k)
        finally: T[name]=T.get(name,0)+time.perf_counter()-t
    setattr(mod,name,w)
t0=time.perf_counter()
from corpus_structure.schema.pack import DOMAINS
from corpus_structure.semantic.regeneration import prepare_pack
from corpus_structure.semantic import prepare, ontology
import corpus_structure.semantic.prepare as P
t_imp=time.perf_counter()-t0
mode=sys.argv[1]
if mode=="acquire":
    b,d,p,r=prepare_pack(DOMAINS/"statistics")
    pickle.dump((b,d,p),open(sys.argv[2],"wb")); print("acquire+prepare", round(time.perf_counter()-t0,2)); sys.exit()
b,d,p=pickle.load(open(sys.argv[2],"rb"))
import corpus_structure.semantic.ontology as O
wrap(O,"build_graph_artifacts"); wrap(P,"_view_and_vocabularies"); wrap(P,"compile_conditional_rules")
import corpus_structure.semantic.composed as C
wrap(C,"execution_model_from_dependencies")
t1=time.perf_counter()
r=P.prepare_release(b,d,p)
t2=time.perf_counter()
print("import",round(t_imp,2),"cold prepare_release",round(t2-t1,2),{k:round(v,2) for k,v in T.items()})
T.clear(); t3=time.perf_counter(); P._prepare_release_uncached(b,d,p,P._compiler_stack()); print("second uncached",round(time.perf_counter()-t3,2),{k:round(v,2) for k,v in T.items()})
