"""Assemble the applicable union without relabelling the failed original campaign."""
from pathlib import Path
import collections
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
u = json.loads((HERE / 'classified-current-union.json').read_text())
assert u['required_node_coverage']['status'] == 'covered' and not u['required_unresolved']
original, affected, fault = u['receipts']
assert affected['status'] == fault['status'] == 'passed'
assert not affected['worker_loss'] and not fault['worker_loss']
assert affected['native_provenance']['status'] == fault['native_provenance']['status'] == 'complete'
events = [json.loads(line) for line in next((HERE / 'test-receipts/ordinary-attempt003').glob('events-gw0-*.jsonl')).open()]
aliases = next(e['nodeid_aliases'] for e in events if e.get('event') == 'collection_finish')
history = {aliases.get(e['nodeid'], e['nodeid']) for e in events if e.get('event') == 'logstart'}
unresolved = {n for n, v in original['nodes'].items() if v['status'] != 'passed'}
assert len(history) == 228 and len(unresolved) == 20
assert all(affected['nodes'][n]['status'] == 'passed' for n in history | unresolved)
sha = hashlib.sha256((ROOT / 'python/corpus-structure/src/corpus_structure/serve/review_bundle.py').read_bytes()).hexdigest()
assert sha == 'f473bf0f5ac181147f910087873710e003536bb29a4b6f6a1717a8927bf59928'
native = set()
for label in ('ordinary-attempt003', 'affected-current004', 'native-faults001'):
    for path in (HERE / 'test-receipts' / label).glob('events-*.jsonl'):
        found = [json.loads(line) for line in path.open() if 'collection_finish' in line]
        found = [e for e in found if e.get('event') == 'collection_finish']
        if found:
            native.update(found[0].get('native_required', []))
            break
result = dict(
    protocol='wce-final-applicable-qualification-union-1', date='2026-11-06', outcome='passed',
    scope='Selected functional/native/provider/consumer/nonfunctional union over the SAME120 exposed Grinstead–Snell pages',
    product_source_commit='3552edf69', validation_harness_commit='83d0c295d', verifier_sha256=sha,
    semantic_release='release:cb08727ec668c048998c82db31ef0e1242d714ca23e2b0f2a223eb88c6061a29',
    native_revision='semantic_wce_batch_20261106',
    required_nodes=len(u['required']), ordinary_required_nodes=len(u['required'])-len(fault['selected']),
    exclusive_fault_required_nodes=len(fault['selected']), native_required_nodes=len(native),
    required_node_coverage='covered', required_unresolved=[],
    original_campaign=dict(status=original['status'], selected=len(original['selected']),
        node_statuses=dict(collections.Counter(v['status'] for v in original['nodes'].values())),
        worker_loss=original['worker_loss'], retained='test-receipts/ordinary-attempt003'),
    healthy_current_rerun=dict(status=affected['status'], passed=len(affected['selected']),
        original_crashed_worker_cases_replaced=len(history), original_unresolved_replaced=len(unresolved),
        worker_loss=[], native_provenance='complete', retained='test-receipts/affected-current004'),
    exclusive_fault_lane=dict(status=fault['status'], passed=len(fault['selected']),
        native_provenance='complete', retained='test-receipts/native-faults001'),
    applicability=dict(machine_source_contexts_differ=u['source_contexts_differ'],
        judgment='Product/semantic/native code remains unchanged after3552edf69. Only registry expectation, positive test transport budget, fatal-worker pytest policy/probe and documentation/evidence changed. Whole modified test files, all20 unresolved nodes and every228 case from the crashed worker have healthy current parallel passes. Other original passes came from separate unaffected workers. The new harness probe is included in the required union. Failed/interrupted records stay failed.'),
    nonfunctional=dict(hygiene='passed: just hygiene', model='passed: just model check, revision0.6.5',
        readiness='passed: just ready', evidence='0 errors;40 preexisting out-of-scope warnings'),
    actual_corpus=dict(outcome='passed', portable_bundles=25, model_tasks=97, sources=48, pages=120,
        dossier_full_selected_members=8280, dossier_display_budget=12, greedy_supported_role_facets=4,
        source_id_control_supported_role_facets=0, existing_supported_attachments=2,
        meaning_account='../assessment/benefit-account/README.md'),
    native_gc=dict(diagnostic_outcome='partial', cause='unestablished; not reproduced',
        normal_history_nodes=30, debug_allocator_history_nodes=30, both_diagnostics='passed with clean process/report/native health',
        recovery='All228 original crashed-worker cases and all20 unresolved cases passed current-nauto rerun. Documented max-worker-restart=0 naturally terminates fatal attempts; actual two-worker probe verifies error/queued not_run and no survivor. Shutdown is repaired; no native-GC fix is claimed.',
        trigger='Recurrence, core or allocator evidence triggers broader lifetime/dependency investigation. No speculative dependency/GC/backend change.',
        detail='interpreter-crash/README.md'),
    rust=dict(outcome='not_run', reason='Zero selected Rust functional tests; separate Clippy/dependency/format checks passed',
        version='rustc1.101.0-nightly(2d20b42b8 2026-11-04)'),
    limits=dict(meaning='Partial bounded source/model/downstream assessment; complete knowledge/scientific truth/calibration/whole-corpus quality unestablished',
        operation_fit='unavailable/not_run: no matching emitted events or protected operation grades',
        native_interpreter_stability='Original unexplained fault retained; selected healthy reruns do not certify absence of all native faults'),
    concurrent_work='Operator process/role/AGENTS/library documentation edits preserved; task product/harness claims are bounded to named commits.'
)
(HERE / 'final-union.json').write_text(json.dumps(result, indent=2) + '\n')
print(f"covered {result['required_nodes']} unique required nodes; {len(history)} crashed-worker cases and {len(unresolved)} unresolved nodes replaced")
