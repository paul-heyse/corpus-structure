"""Read-only size inventory of the exact captured source population; no NLP."""
import json
from pathlib import Path

from sqlalchemy import text

from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

root = Path(__file__).resolve().parent
with open_runtime_engine(Settings(), 'bep-source-size-inventory', purpose='read') as engine:
    with engine.connect() as conn:
        rows = [dict(row) for row in conn.execute(text('''
            SELECT s.run_id,v.id,v.section_pointer,v.membership,v.analysis_eligible,
                   v.native_task_id,v.native_product_key,v.native_content_digest,
                   char_length(v.projection->>'text') AS text_chars,
                   octet_length(v.projection->>'text') AS text_utf8_bytes,
                   jsonb_array_length(v.projection->'pieces') AS pieces,
                   jsonb_array_length(v.projection->'items') AS items
            FROM ops.run_source_view s JOIN kb.source_view v ON v.id=s.source_view_id
            WHERE s.run_id IN (496,610)
              AND NOT EXISTS (SELECT FROM ops.run_source_view newer
                              WHERE newer.run_id=s.run_id AND newer.supersedes_source_view_id=v.id)
            ORDER BY s.run_id,text_chars DESC,v.id
        ''')).mappings()]
        result = {'date':'2026-11-11','filter':'effective selected source views in source capture run496 and failed enrichment run610; no superseded selections','runs':{}}
        for run_id in (496,610):
            population=[row for row in rows if row['run_id']==run_id]
            exact=[row for row in population if row['native_task_id']==1627 and row['native_product_key']=='integrated' and row['native_content_digest']=='35f4384ea386e630448d804621c0767881650937c45cd4294182cb0dd91ce8fb']
            result['runs'][str(run_id)]={'selected_views':len(population),'exact_product_views':len(exact),'total_text_chars':sum(row['text_chars'] for row in exact),'maximum_text_chars':max((row['text_chars'] for row in exact),default=None),'failed_view480_rank_by_chars':next((index+1 for index,row in enumerate(exact) if row['id']==480),None),'top5_by_text_chars':exact[:5]}
        (root/'raw/source-size-inventory.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps(result,indent=2))
