"""Compare each native member against its independently requested singleton."""
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent

def difference(a,b,path=''):
    if isinstance(a,float) and isinstance(b,float):
        return [], abs(a-b)
    if type(a) is not type(b): return [path],0
    if isinstance(a,dict):
        if a.keys()!=b.keys(): return [path+'/keys'],0
        children=[difference(a[k],b[k],path+'/'+k) for k in a]
    elif isinstance(a,list):
        if len(a)!=len(b): return [path+'/length'],0
        children=[difference(x,y,path+'/'+str(i)) for i,(x,y) in enumerate(zip(a,b))]
    else: return ([] if a==b else [path]),0
    return [p for mismatches,_ in children for p in mismatches],max([n for _,n in children],default=0)

def rows(provider,call):
    if provider=='gliner': return [r['raw'] for r in call['reports']]
    reply=call['reply']
    if provider=='d1': return reply['batch']
    return [dict(preparation=reply['preparation'][i],native={k:v[i] for k,v in reply['native'].items()}) for i in range(len(call['members']))]

summary={}
for provider in ('hanlp','d1','gliner'):
    path=HERE/'raw'/(provider+'.json')
    if not path.exists():continue
    data=json.loads(path.read_text()); singles={}
    for call in data['calls']:
        if len(call['members'])==1:singles[call['members'][0]]=rows(provider,call)[0]
    comparisons=[]
    for call in data['calls']:
        for ordinal,(member,row) in enumerate(zip(call['members'],rows(provider,call))):
            mismatch,numeric=difference(singles[member],row)
            comparisons.append(dict(members=call['members'],ordinal=ordinal,member=member,discrete_mismatches=mismatch,max_float_abs_difference=numeric,exact=singles[member]==row))
    summary[provider]=dict(comparisons=comparisons,mixed_admission=data.get('mixed_admission'))
(HERE/'raw/summary.json').write_text(json.dumps(summary,indent=2))
for provider,data in summary.items():
 print(provider,'discrete_mismatch_count',sum(len(c['discrete_mismatches']) for c in data['comparisons']),'max_float_difference',max(c['max_float_abs_difference'] for c in data['comparisons']))
