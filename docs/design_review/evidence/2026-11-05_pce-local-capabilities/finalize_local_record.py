"""Finalize only the accepted PCE04–08 result; preserve every earlier attempt."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / 'raw'

def read(name):
    return json.loads((RAW / name).read_bytes())

output = read('parser-output-grade-002.json')
publication = read('contextual-local-publication-003-result.json')
retained = read('whitespace-retained-002.json')
assert output['diagnostic_counts'] == dict(ambiguous=2, misidentified=2, supported=9, unassessed=11)
assert publication['run_id'] == 45 and publication['admitted_semantic_claims'] == 16
assert all(row['status'] == 'reused' for row in publication['method_inventory'])
assert sum(retained['contribution_counts'].values()) == 7868
inputs = [
    'parser-source-input-002.json', 'output-author-brief.md',
    'raw/runtime-local-009.json', 'raw/contextual-source-author-packet-001.json',
    'raw/contextual-author-A-001.json', 'raw/contextual-author-B-001.json', 'raw/contextual-author-C-001.json',
    'raw/parser-source-wrappers-001.json', 'raw/parser-output-selection-002.json',
    'raw/parser-output-selection-002-author-source-packet.json',
    'raw/parser-output-author-A-002.json', 'raw/parser-output-author-B-002.json', 'raw/parser-output-author-C-002.json',
    'raw/parser-output-author-A-003.json', 'raw/parser-output-author-B-003.json', 'raw/parser-output-author-C-003.json',
    'raw/parser-output-wrappers-005-driver.py', 'raw/parser-output-grade-002-driver.py',
    'contextual_corpus_native_preflight.py', 'contribution_v3_transport_current.py',
    'migrate_local_011.py', 'native144-candidate-001/native_operations.json',
]
outputs = [
    'raw/root-final-functional-001.log', 'raw/root-final-native-144-001.log',
    'f27-batch-validation/pytest-native144-003.log', 'f27-batch-validation/rollback-002.log',
    'raw/local-migrate-working-011.json', 'raw/contextual-comparison-001.json',
    'raw/contextual-corpus-e5-expanded-001-result.json', 'raw/contextual-e5-grade-002.json',
    'raw/contextual-qwen-grade-001.json', 'raw/contextual-e5-grade-004.json',
    'raw/contextual-local-publication-003-result.json', 'raw/contribution-v3-transport-002.json',
    'raw/contribution-v3-transport-002-export', 'raw/contribution-transport-current-001.json',
    'raw/parser-corpus-003-readonly-recovery-002.json', 'raw/whitespace-retained-002.json',
    'raw/parser-source-paired-001.json', 'raw/parser-output-wrappers-005.json',
    'raw/parser-output-register-002.json', 'raw/parser-output-grade-002.json',
    'raw/parser-output-serialization-007.log', 'raw/parser-local-refusal-survival-002.json',
    'raw/owned-source-budgets-001.log', 'raw/normal-source-budget-native-read-001.log',
    'raw/types-009.log', 'raw/ruff-009.log', 'raw/ready-003.log',
    'raw/final-docs-check-001.log', 'raw/final-adr-lint-001.log', 'raw/final-deps-001.log',
    'raw/final-lint-agents-001.log', 'raw/final-rules-scan-001.log', 'raw/final-rules-test-001.log',
    'raw/final-turn-end-001.log',
]
record = dict(schema_version=1, id='pce.local-04-08',
    title='Qualified local contributions, contextual retrieval and granular parser assessment',
    group='PCE', package='PCE-04–08', finalized='2026-11-05', status='current',
    supersedes=[], superseded_by=None,
    question='Do selected progressive local contributions survive incomplete assembly, support protected granular assessment and independently qualified publication through actual common consumers?',
    answers=[f'PCE-{i:02}' for i in range(4,9)],
    method='Additive native134–144, owned actual CPU encoders and bounded GLiNER/spaCy/Lark consumers, complete typed replay, fresh source-only A/B/C, exact protected paired source/output grading, common atomic source/semantic publication and real CLI/external MCP/selected JSONL export.',
    commands=[
        'uv run pytest <the 22 selected functional owner files recorded in the coordinator/evidence; --basetemp=build/test-receipts/pce-local-functional-001>',
        'uv run pytest <the 12 final native/assessment owner files recorded in the coordinator/evidence; --basetemp=build/test-receipts/pce-local-native-144-001>',
        'uv run pytest python/corpus-structure/tests/semantic/test_local_semantic_admission_native.py -q -x',
        'uv run pytest docs/design_review/evidence/2026-11-05_pce-local-capabilities/test_pce07_output_serialization.py --basetemp=build/test-receipts/pce-output-serialization-final-003 -q',
        'uv run python docs/design_review/evidence/2026-11-05_pce-local-capabilities/migrate_local_011.py',
        'uv run python docs/design_review/evidence/2026-11-05_pce-local-capabilities/pce07_paired_assessment.py retained --release release:1bf171f3667ef76260b78179f46d15dd4fbed8bcb6a8bb6587e4cd08878abce5 --realization pce-local-input:release:1bf171f3667ef76260b78179f46d15dd4fbed8bcb6a8bb6587e4cd08878abce5 --runtime runtime:761f21fb0d06167211e86aa107d760ca712d9526eb457670c04b64d51129634c --retained-tasks 122 --receipt whitespace-retained-002',
        'uv run python docs/design_review/evidence/2026-11-05_pce-local-capabilities/pce07_paired_assessment.py grade --registration parser-source-register-001.json --baseline-run 31 --prediction-run 43 --receipt parser-source-paired-001',
        'uv run python docs/design_review/evidence/2026-11-05_pce-local-capabilities/pce07_paired_assessment.py output-grade --registration parser-output-register-002.json --receipt parser-output-grade-002',
        'uv run python docs/design_review/evidence/2026-11-05_pce-local-capabilities/contribution_v3_transport_current.py',
        'uv run python docs/design_review/evidence/2026-11-05_pce-local-capabilities/contribution_transport_current.py',
        'just types', 'just ruff', 'just ready', 'just docs-check', 'just adr-lint',
        'just deps', 'just lint-agents', 'just rules-scan', 'just rules-test', 'just turn-end',
    ],
    agents=[dict(role=f'fresh {population} reference {kind}', model='gpt-6.1-sol/high',
        brief='output-author-brief.md' if population=='output-first' else None,
        separation='A/B see only source/rubric, no producer values/scores/targets or old truth; C sees source plus independent A/B. Raw answers and format-only revisions remain; literals, contextual evidence, semantic values and evaluability stay distinct.')
        for population in ('contextual-source','output-first') for kind in 'ABC'],
    inputs=[dict(path=path,role='accepted input',sha256=None) for path in inputs],
    outputs=[dict(path=path,role='selected actual receipt',sha256=None) for path in outputs],
    depends_on=['2026-11-05_pce-foundations/pce.foundations-00-03'],
    results=[dict(name=name,value=value,of=None,unit=unit,note=note) for name,value,unit,note in [
        ('Selected functional suite',418,'tests','Final parser/encoder/numerical code at runtime008; later publication-only changes covered by native144/actual45.'),
        ('Selected final144 native union',158,'tests','Not summed with overlapping suites.'),
        ('Complete semantic admission144 file',21,'tests','Independent stale/foreign/malformed/multi-witness controls.'),
        ('Evidence-wrapper controls',21,'tests','Expected literals/source context not metadata; exact independent fields; no gap concatenation.'),
        ('Preserved archive/data/run/reference tables',28,'tables','Before/after final144 hashes equal.'),
        ('Source-first facets',92,'facets','Same source/question/version/rubric across baseline31 and replay43.'),
        ('Source supported',30,'facets','Fourteen newly captured;58 uncaptured/unsupported;4 unassessed.'),
        ('Newly captured source facets',14,'facets','13 positive header associations plus1 literal, no observed regression.'),
        ('Output-first facets',24,'facets','Outcome-blind capability-selected002, separate denominator.'),
        ('Output supported',9,'facets','Predicate/ordered endpoints do not establish captured qualifiers/full scientific statement.'),
        ('Output role errors',2,'facets','Private defined_term predictions where independent source supports mentioned_term.'),
        ('Output ambiguous',2,'facets',None),('Output unassessed',11,'facets','Includes item-only exact-literal applicability; source fact remains.'),
        ('Retained producer products',7530,'products','No extraction rerun for replay43.'),
        ('Retained products plus private derived attachments',7868,'products','338 added private associations; not independent evidence votes.'),
        ('Public denotation claims',16,'claims','Actual45 cached origin130/evaluation20; zero complete records.'),
        ('Public source events',33,'events','17 distinct physical occurrences, not33 independent sources.'),
        ('Reused original target vectors',20,'vectors','Actual inventory20→21; fresh queries/new target and rebuilt lists.'),
    ]],
    outcome='passed',
    conclusion='PCE-04–08 selected functional/native/provider/consumer and independent review obligations pass within the declared bounded scope. Actual source92 gains14 captured facets; output24 retains9 supported,2 genuine role errors,2 ambiguous,11 unassessed. Complete typed products survive assembly/no-factor failures; exact current independent denotations publish without complete records. Failed/interrupted attempts, insufficient selection001 and invalid literal grade001 remain, superseded by corrected immutable references/grades. No held-out truth, historical label upcast, population accuracy, calibration, scientific truth, full-corpus/portable-review/default adoption or untriggered solver efficacy is established. Semantic release1bf survives operational repairs; exact runtime009 differs, defaults remain null/null/0, old rows preserved and no auxiliary worktrees remain. PCE-09–11 retain remaining scope.',
    consumed_by=[f'PCE-{i:02}' for i in range(4,9)]+['ADR-0064'],
)
# Persist the exact executable selections, not placeholder recipe names.
functional = ['methods/test_contribution_adapter.py','methods/test_m1_readings.py','methods/test_gliner.py',
 'methods/test_m1_producer.py','methods/test_m1_source_preparation.py','methods/test_m1_annotation_selection.py',
 'methods/test_contextual_candidates.py','methods/test_local_interpretation.py','methods/test_m1_cli.py',
 'ingest/test_annotations.py','semantic/test_record_interpretation.py','semantic/test_local_interpretation.py',
 'semantic/test_local_admission.py','semantic/test_local_semantic_admission.py','semantic/test_contextual_enrichment.py',
 'semantic/test_contribution_journey.py','semantic/test_contribution_transport.py','semantic/test_contributions.py',
 'semantic/test_retained_source_budgets.py','semantic/test_analysis_contracts.py','semantic/test_operation_reporting.py','db/test_outcomes.py']
native = ['evaluate/test_operation_assessment.py','evaluate/test_operation_assessment_native.py',
 'semantic/test_local_semantic_admission.py','semantic/test_local_admission_native.py','semantic/test_contributions_native.py',
 'semantic/test_contribution_selectors_native.py','semantic/test_private_records.py','semantic/test_record_publication_native.py',
 'semantic/test_record_support_native.py','semantic/test_alembic_array_types.py',
 'semantic/test_contextual_enrichment_native.py','semantic/test_local_attribute_native.py']
for index,files,scratch in [(0,functional,'pce-local-functional-001'),(1,native,'pce-local-native-144-001')]:
    record['commands'][index]='uv run pytest '+' '.join('python/corpus-structure/tests/'+name for name in files)+' --basetemp=build/test-receipts/'+scratch
for path in [*inputs,*outputs]:
    if not (HERE/path).exists():raise FileNotFoundError(path)
(HERE/'records').mkdir(exist_ok=True)
with (HERE/'records/pce.local-04-08.json').open('x') as stream:
    json.dump(record,stream,indent=2,ensure_ascii=False);stream.write('\n')
print('accepted PCE04–08 record written; hashes are finalized by existing evidence owner')
