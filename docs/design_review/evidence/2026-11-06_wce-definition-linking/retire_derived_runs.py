"""One-off design-phase retirement of obsolete structural runs, with FK closure.

Dry-run by default. Sources are an explicit refusal boundary. Commit only after the
replacement is qualified; immutable-row guards are suspended transactionally for
exact planned tables while PostgreSQL foreign keys remain enforced.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def quoted(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def retire(*, commit: bool, receipt: Path) -> None:
    with open_runtime_engine(Settings(), 'wce-derived-retirement', purpose='maintenance') as engine:
        with engine.connect() as conn:
            transaction = conn.begin()
            try:
                conn.execute(text('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ'))
                database = conn.execute(text('select current_database()')).scalar_one()
                if database != 'corpus_structure_dev':
                    raise ValueError('retirement is restricted to corpus_structure_dev')
                source_counts = {name: conn.execute(text('select count(*) from '+name)).scalar_one() for name in ('ops.source_build','ops.native_source_frame','kb.source_view','kb.source_artifact')}
                conn.execute(text('create temporary table wce_retire_rows(rel oid, tid tid, primary key(rel,tid)) on commit drop'))
                conn.execute(text("""insert into wce_retire_rows select 'ops.run'::regclass,idtable.ctid
                    from ops.run idtable where idtable.id in (
                    select t.run_id from ops.task t join ops.task_result r on r.task_id=t.id
                    where r.body->'structural_product'->>'version'='structural-product-1')"""))
                # A run with actual native source production cannot be retired as a unit.
                native = conn.execute(text("""select t.id from ops.task t join ops.run r on r.id=t.run_id
                    join wce_retire_rows p on p.rel='ops.run'::regclass and p.tid=r.ctid
                    where t.unit_type<>'run'""")).all()
                if native:
                    raise ValueError('selected run contains source/non-run tasks')
                conn.execute(text("""insert into wce_retire_rows select 'ops.task'::regclass,t.ctid
                    from ops.task t join ops.task_result r on r.task_id=t.id
                    where jsonb_path_exists(r.body, '$.contribution_operations[*].contextual_enrichment.version ? (@ == "contextual-enrichment-1")') on conflict do nothing"""))
                conn.execute(text("""insert into wce_retire_rows select 'eval.structural_reference_set'::regclass,s.ctid
                    from eval.structural_reference_set s where s.frame->>'protocol' in
                    ('structural-evaluation-frame-1','structural-evaluation-frame-2') on conflict do nothing"""))
                foreign_keys = conn.execute(text("""select c.conrelid child,c.confrelid parent,
                    nc.nspname child_schema,cc.relname child_name,np.nspname parent_schema,cp.relname parent_name,
                    array_agg(ac.attname order by keys.n) child_columns,array_agg(ap.attname order by keys.n) parent_columns
                    from pg_constraint c join pg_class cc on cc.oid=c.conrelid join pg_namespace nc on nc.oid=cc.relnamespace
                    join pg_class cp on cp.oid=c.confrelid join pg_namespace np on np.oid=cp.relnamespace
                    cross join lateral unnest(c.conkey,c.confkey) with ordinality keys(child_key,parent_key,n)
                    join pg_attribute ac on ac.attrelid=c.conrelid and ac.attnum=keys.child_key
                    join pg_attribute ap on ap.attrelid=c.confrelid and ap.attnum=keys.parent_key
                    where c.contype='f' group by c.oid,nc.nspname,cc.relname,np.nspname,cp.relname""")).mappings().all()
                while True:
                    added = 0
                    for fk in foreign_keys:
                        child = quoted(fk['child_schema']) + '.' + quoted(fk['child_name'])
                        parent = quoted(fk['parent_schema']) + '.' + quoted(fk['parent_name'])
                        matches = ' and '.join('ch.'+quoted(a)+'=pa.'+quoted(b) for a,b in zip(fk['child_columns'],fk['parent_columns'],strict=True))
                        statement = f'insert into wce_retire_rows select :child,ch.ctid from {child} ch join {parent} pa on {matches} join wce_retire_rows p on p.rel=:parent and p.tid=pa.ctid on conflict do nothing'
                        added += conn.execute(text(statement),dict(child=fk['child'],parent=fk['parent'])).rowcount
                    if not added:
                        break
                plan = [dict(r) for r in conn.execute(text("""select p.rel,n.nspname schema,c.relname name,count(*) rows
                    from wce_retire_rows p join pg_class c on c.oid=p.rel join pg_namespace n on n.oid=c.relnamespace
                    group by p.rel,n.nspname,c.relname order by n.nspname,c.relname""")).mappings()]
                protected = {'source_build','native_source_frame','native_region_artifact','pdf_product','pdf_product_body','pdf_frozen_build','source_view','document','source'}
                if any(r['name'] in protected or r['name'].startswith(('pdf_', 'native_source_')) or (r['schema']=='kb' and r['name'].startswith('source_') and not r['name'].startswith('source_contribution')) or r['schema'] not in {'ops','data','kb','eval'} for r in plan):
                    raise ValueError('dependency closure reaches protected source or unrelated schema')
                result = dict(database=database,mode='commit' if commit else 'dry_run',plan=plan,foreign_keys_enforced=True,protected_source_counts=source_counts)
                receipt.write_text(json.dumps(result,indent=2)+'\n')
                if not commit:
                    transaction.rollback()
                    return
                triggers = conn.execute(text("""select n.nspname schema,c.relname name,t.tgname trigger,t.tgenabled mode
                    from pg_trigger t join pg_class c on c.oid=t.tgrelid join pg_namespace n on n.oid=c.relnamespace
                    where not t.tgisinternal and t.tgrelid in (select rel from wce_retire_rows)""")).mappings().all()
                for row in plan:
                    conn.execute(text('alter table '+quoted(row['schema'])+'.'+quoted(row['name'])+' disable trigger user'))
                pending = list(plan)
                while pending:
                    progress = False
                    for row in pending[:]:
                        try:
                            with conn.begin_nested():
                                conn.execute(text('delete from '+quoted(row['schema'])+'.'+quoted(row['name'])+' where ctid in (select tid from wce_retire_rows where rel=:rel)'),dict(rel=row['rel']))
                        except IntegrityError:
                            continue
                        pending.remove(row)
                        progress = True
                    if not progress:
                        raise ValueError('foreign-key deletion order unresolved; transaction rolled back')
                for row in triggers:
                    action = {'O':'enable','D':'disable','R':'enable replica','A':'enable always'}[row['mode']]
                    conn.execute(text('alter table '+quoted(row['schema'])+'.'+quoted(row['name'])+' '+action+' trigger '+quoted(row['trigger'])))
                after = {name: conn.execute(text('select count(*) from '+name)).scalar_one() for name in source_counts}
                if after != source_counts:
                    raise ValueError('protected source population changed; rolling back')
                transaction.commit()
                result['outcome']='passed'
                receipt.write_text(json.dumps(result,indent=2)+'\n')
            except BaseException:
                transaction.rollback()
                raise


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit',action='store_true')
    parser.add_argument('--receipt',type=Path,required=True)
    args=parser.parse_args()
    retire(commit=args.commit,receipt=args.receipt)
