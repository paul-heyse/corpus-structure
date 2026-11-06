"""Generate reviewable patch text only; never mutates package or database."""
from pathlib import Path
import difflib
ROOT=Path('/home/paul/corpus-structure')
HERE=Path(__file__).resolve().parent
base=ROOT/'python/corpus-structure/src/corpus_structure/semantic'
p=base/'sql/dossier_contributions.sql';old=p.read_text()
helper=old[old.index('-- Private membership retains'):]
helper=helper.replace('ops.dossier_contribution_member(inputs jsonb,ref jsonb)', 'ops.dossier_contribution_member_from_retained(inputs jsonb,ref jsonb,retained_rows jsonb,retained_sources jsonb,dependency_index jsonb)')
helper=helper.replace('DECLARE retained jsonb;root_ jsonb;', 'DECLARE root_ jsonb;')
helper=helper.replace("IF NOT inputs->'dependencies' ? (ref->>'contribution_id')", "IF NOT dependency_index ? (ref->>'contribution_id')")
helper=helper.replace(' retained:=ops.resolve_retained_source_contribution(ref);\n','')
helper=helper.replace("retained->'contributions'",'retained_rows').replace("retained->'sources'",'retained_sources')
helper=helper.replace('ops.dossier_contribution_member(jsonb,jsonb)', 'ops.dossier_contribution_member_from_retained(jsonb,jsonb,jsonb,jsonb,jsonb)')
resolver_wrapper='''
-- Existing Reader API delegates to the single current custody-validation owner.
CREATE OR REPLACE FUNCTION ops.resolve_retained_source_contribution(ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE result_ jsonb;
BEGIN
 SELECT jsonb_build_object('contributions',r.contributions,'sources',r.sources) INTO STRICT result_
 FROM ops.resolve_retained_source_contributions(jsonb_build_array(ref))r;
 RETURN result_;
EXCEPTION WHEN no_data_found OR too_many_rows THEN
 RAISE EXCEPTION 'retained contribution cannot resolve exact selected origin' USING ERRCODE='23514';
END $$;
REVOKE ALL ON FUNCTION ops.resolve_retained_source_contribution(jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION ops.resolve_retained_source_contribution(jsonb) TO corpus_sem_reader,corpus_sem_writer;
'''
member_wrapper='''
-- Ordinary one-reference membership keeps its authenticated resolver route.
CREATE OR REPLACE FUNCTION ops.dossier_contribution_member(inputs jsonb,ref jsonb)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
DECLARE retained jsonb;
BEGIN
 retained:=ops.resolve_retained_source_contribution(ref);
 RETURN ops.dossier_contribution_member_from_retained(inputs,ref,
  retained->'contributions',retained->'sources',inputs->'dependencies');
END $$;
REVOKE ALL ON FUNCTION ops.dossier_contribution_member(jsonb,jsonb) FROM PUBLIC;
'''
batch_projection='''
-- Dependency membership is indexed once; raw rows remain owned by the batch resolver.
CREATE OR REPLACE FUNCTION ops.dossier_contribution_members(inputs jsonb,refs jsonb)
RETURNS SETOF jsonb LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog,pg_temp AS $$
 WITH dependency_index AS MATERIALIZED (
  SELECT COALESCE(jsonb_object_agg(d,true),'{}') value FROM jsonb_array_elements_text(inputs->'dependencies')d)
 SELECT ops.dossier_contribution_member_from_retained(inputs,r.reference,r.contributions,r.sources,d.value)
 FROM ops.resolve_retained_source_contributions(refs)r CROSS JOIN dependency_index d
$$;
REVOKE ALL ON FUNCTION ops.dossier_contribution_members(jsonb,jsonb) FROM PUBLIC;
'''
new=(HERE/'batch-resolver.sql.txt').read_text()+resolver_wrapper+helper+member_wrapper+batch_projection
(HERE/'proposed-dossier-contributions.sql.txt').write_text(new)
changes=[('python/corpus-structure/src/corpus_structure/semantic/sql/dossier_contributions.sql',old,new)]
p=base/'sql/structural_products.sql';old=p.read_text()
needle=""" FOR reference IN SELECT value FROM jsonb_array_elements(COALESCE(config->'contribution_predecessors','[]')) LOOP
  member_:=ops.dossier_contribution_member(inputs,reference);members:=members||jsonb_build_array(member_);
 END LOOP;
"""
replacement=""" -- Aggregate full source membership once; never append to the growing dossier per row.
 SELECT members||COALESCE(jsonb_agg(source_member.value),'[]') INTO members
 FROM ops.dossier_contribution_members(inputs,COALESCE(config->'contribution_predecessors','[]')) AS source_member(value);
"""
assert old.count(needle)==1
new=old.replace(needle,replacement)
changes.append(('python/corpus-structure/src/corpus_structure/semantic/sql/structural_products.sql',old,new))
p=base/'native_candidate.py';old=p.read_text()
needle='    for name in ("resolve_retained_source_contribution", "dossier_contribution_member"):'
replacement='''    for name in (
        "resolve_retained_source_contributions",
        "resolve_retained_source_contribution",
        "dossier_contribution_member_from_retained",
        "dossier_contribution_member",
        "dossier_contribution_members",
    ):'''
assert old.count(needle)==1
new=old.replace(needle,replacement)
changes.append(('python/corpus-structure/src/corpus_structure/semantic/native_candidate.py',old,new))
(HERE/'native-batch-members.patch').write_text(''.join(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='a/'+name,tofile='b/'+name)) for name,a,b in changes))
print('wrote patch text only',len((HERE/'native-batch-members.patch').read_bytes()))
