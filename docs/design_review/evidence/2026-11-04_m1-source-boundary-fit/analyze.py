"""Summarize source-only representability, distinct causes and admission ceilings."""
import json
import argparse
from collections import Counter,defaultdict
from hashlib import sha256
from pathlib import Path

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',default='attempt-001')
args=parser.parse_args()
OUT=HERE/args.output
records=[json.loads(x) for x in (OUT/'record-mapping.jsonl').read_text().splitlines()]
budgets=[json.loads(x) for x in (OUT/'native-budgets.jsonl').read_text().splitlines()]
attempts=[json.loads(x) for x in (OUT/'mapping-attempts.jsonl').read_text().splitlines()]
budget_lookup={(b['variant'],b['segmentation'],b['source_view_id'],b['index'],b['family']):b for b in budgets}
summary=[]
for variant in ('original','expanded'):
    for segmentation in ('whitespace','codepoints'):
        rs=[r for r in records if r['variant']==variant and r['segmentation']==segmentation]
        if not rs:continue
        bs=[b for b in budgets if b['variant']==variant and b['segmentation']==segmentation]
        def permitted(r,primary=False):
            indices=r['primary_complete_contexts'] if primary else r['complete_contexts']
            return any((b:=budget_lookup[variant,segmentation,r['source_view_id'],i,r['family']])['facade_word_bound_pass'] and b['facade_subword_bound_pass'] for i in indices)
        cause_records=Counter()
        for r in rs:
            if not r['source_roles_exact']:
                cause_records.update(set(e['reason'] for e in (r['best_diagnostic'] or {}).get('errors',[])))
        widths=[s['token_width'] for a in attempts if a['variant']==variant and a['segmentation']==segmentation for s in a['successes']]
        summary.append(dict(variant=variant,segmentation=segmentation,records=len(rs),strict_exact=sum(r['baseline_strict_mappable'] for r in rs),source_exact=sum(r['source_roles_exact'] for r in rs),source_exact_but_classified_absent_gap=sum(r['source_roles_exact'] and bool(r['classified_absent_gaps']) for r in rs),strict_exact_with_old_facade=sum(permitted(r) for r in rs),primary_strict_exact=sum(r['primary_strict_mappable'] for r in rs),primary_strict_exact_with_old_facade=sum(permitted(r,True) for r in rs),distinct_record_causes=dict(cause_records),max_mapped_target_width_tokens=max(widths,default=0),request_counts=dict(total=len(bs),old_facade_both_pass=sum(b['facade_word_bound_pass'] and b['facade_subword_bound_pass'] for b in bs),source_word_overflow_contexts=len({(b['source_view_id'],b['index']) for b in bs if not b['facade_word_bound_pass']}),subword_overflow_contexts=len({(b['source_view_id'],b['index']) for b in bs if not b['facade_subword_bound_pass']}))))
sets={}
for variant in ('original','expanded'):
    for segmentation in ('whitespace','codepoints'):
        for primary in (False,True):
            sets[variant,segmentation,primary]={r['record_id'] for r in records if r['variant']==variant and r['segmentation']==segmentation and r['family']=='formula_context' and r['primary_strict_mappable' if primary else 'baseline_strict_mappable']}
unions=[]
for segmentation in ('whitespace','codepoints'):
    if not any(r['variant']=='expanded' and r['segmentation']==segmentation for r in records):continue
    nonformula={r['record_id'] for r in records if r['variant']=='original' and r['segmentation']==segmentation and r['family']!='formula_context' and r['baseline_strict_mappable']}
    for primary in (False,True):
        union=sets['original',segmentation,primary]|sets['expanded',segmentation,primary]
        unions.append(dict(segmentation=segmentation,require_primary_formula=primary,formula_union=len(union),all_family_union=len(union|nonformula),expanded_formula_gains=len(sets['expanded',segmentation,primary]-sets['original',segmentation,primary]),original_formula_lost_when_using_expanded_only=len(sets['original',segmentation,primary]-sets['expanded',segmentation,primary])))
expansions=[json.loads(x) for x in (OUT/'formula-expansion.jsonl').read_text().splitlines()]
budget_envelopes=[]
for variant in ('original','expanded'):
    for segmentation in ('whitespace','codepoints'):
        bs=[b for b in budgets if b['variant']==variant and b['segmentation']==segmentation]
        if not bs:continue
        largest=max(bs,key=lambda b:b['subwords'])
        budget_envelopes.append(dict(variant=variant,segmentation=segmentation,max_source_words=max(b['source_word_tokens'] for b in bs),max_prefix_tokens=max(b['prefix_tokens'] for b in bs),max_model_words=max(b['model_word_tokens'] for b in bs),max_subwords=max(b['subwords'] for b in bs),largest_subword_request=largest))
output=dict(outcome='passed',comparisons=summary,source_generated_context_union=unions,budget_envelopes=budget_envelopes,expansion_limits=dict(Counter(limit['reason'] for r in expansions for limit in r.get('limits',[]))),expansion_bounds=dict(max_chars=max(r.get('chars',0) for r in expansions),max_intervals=max(r.get('intervals',0) for r in expansions),max_whole_blocks=max(len(r.get('selected_blocks',[])) for r in expansions)),model_execution=False)
(OUT/'analysis.json').write_text(json.dumps(output,indent=2))
(OUT/'analysis-executed.py.txt').write_bytes(Path(__file__).read_bytes())
print(json.dumps(output,indent=2))
