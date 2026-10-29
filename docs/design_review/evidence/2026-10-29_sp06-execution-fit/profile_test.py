"""One scoped timing diagnosis; no production instrumentation or acceptance thresholds."""
from __future__ import annotations

import functools
import importlib
import json
import time
from collections import defaultdict
from pathlib import Path

START = time.perf_counter()
HERE = Path(__file__).resolve().parent
phases = defaultdict(lambda: {'calls': 0, 'inclusive_seconds': 0.0, 'exclusive_seconds': 0.0})
stack = []


def wrap(owner, name, label):
    original = getattr(owner, name)

    @functools.wraps(original)
    def measured(*args, **kwargs):
        started = time.perf_counter()
        frame = [0.0]
        stack.append(frame)
        try:
            return original(*args, **kwargs)
        finally:
            elapsed = time.perf_counter() - started
            stack.pop()
            if stack:
                stack[-1][0] += elapsed
            stat = phases[label]
            stat['calls'] += 1
            stat['inclusive_seconds'] += elapsed
            stat['exclusive_seconds'] += elapsed - frame[0]

    setattr(owner, name, measured)
    return original, measured


modules = {name: importlib.import_module('corpus_structure.semantic.' + name)
           for name in ('prepare', 'proposals', 'releases', 'ontology', 'domain_operations', 'query', 'migrations')}
original, measured = wrap(modules['prepare'], 'prepare_release', 'prepare_release')
for name in ('proposals', 'releases'):
    if getattr(modules[name], 'prepare_release', None) is original:
        modules[name].prepare_release = measured
package = importlib.import_module('corpus_structure.semantic')
if getattr(package, 'prepare_release', None) is original:
    package.prepare_release = measured
original, measured = wrap(modules['releases'], 'load_release', 'load_release')
for name in ('query', 'domain_operations'):
    if getattr(modules[name], 'load_release', None) is original:
        modules[name].load_release = measured
for owner, name, label in [
    (modules['ontology'], 'build_graph_artifacts', 'build_graph_artifacts'),
    (modules['proposals'], 'proposal_inputs', 'proposal_inputs'),
    (modules['releases'], 'persist_release', 'persist_release'),
    (modules['domain_operations'], 'consolidate_cut', 'consolidate_cut'),
    (modules['migrations'], 'upgrade', 'migrations.upgrade'),
    (modules['query'].ReadSession, 'query', 'ReadSession.query'),
]:
    wrap(owner, name, label)

from sqlalchemy import Engine, event
sql = defaultdict(lambda: {'calls': 0, 'seconds': 0.0})


@event.listens_for(Engine, 'before_cursor_execute')
def before(conn, cursor, statement, parameters, context, executemany):
    context._diagnostic_started = time.perf_counter()


@event.listens_for(Engine, 'after_cursor_execute')
def after(conn, cursor, statement, parameters, context, executemany):
    # SQL parameters and connection URLs are deliberately not collected.
    key = ' '.join(statement.split())[:180]
    sql[key]['calls'] += 1
    sql[key]['seconds'] += time.perf_counter() - context._diagnostic_started


import pytest


class Timings:
    def __init__(self):
        self.reports = []

    def pytest_runtest_logreport(self, report):
        self.reports.append({'phase': report.when, 'seconds': report.duration, 'outcome': report.outcome})


plugin = Timings()
imports_seconds = time.perf_counter() - START
result = pytest.main([
    'python/corpus-structure/tests/semantic/test_statistics_cut.py', '--tb=short', '--durations=10',
], plugins=[plugin])
report = {'exit_code': result, 'wall_seconds': time.perf_counter() - START,
          'instrumentation_import_seconds': imports_seconds, 'pytest': plugin.reports,
          'phases': dict(phases),
          'sql': sorted(({'statement': k, **v} for k, v in sql.items()), key=lambda v: -v['seconds'])[:30]}
(HERE / 'raw' / 'timings.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report, indent=2))
raise SystemExit(result)
