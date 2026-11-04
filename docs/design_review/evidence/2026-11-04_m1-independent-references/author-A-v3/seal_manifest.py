"""Hash only this author's exact artifacts after serialization and validation."""
import pathlib,json,hashlib,collections
root=pathlib.Path(__file__).resolve().parent
p=root/'manifest.json';d=json.loads(p.read_text())
d['validation']={'outcome':'passed','receipt':'validation-07.log','command':'uv run python docs/design_review/evidence/2026-11-04_m1-independent-references/author-A-v3/validate.py','date':'2026-11-04','scope':'Exact eleven authored batches against archived release and authenticated retained-source coordinates; no extraction grade.'}
d['output_artifacts']={str(x.relative_to(root)):hashlib.sha256(x.read_bytes()).hexdigest()for x in sorted(root.rglob('*'))if x.is_file() and x!=p}
d['accepted_records_total']=sum(sum(v.values())for v in d['counts'].values())
p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
