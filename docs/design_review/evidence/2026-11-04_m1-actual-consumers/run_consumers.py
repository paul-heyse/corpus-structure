"""Actual pinned query/CLI/registered-MCP/export journeys; no quality oracle."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import traceback
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from fastmcp import Client

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.record_queries import read_completed_record_projection
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.serve.record_results import RecordRequest, serve_record_results
from corpus_structure.serve.record_support import serve_record_support
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RELEASE = 'release:bc69d3be658e27e079ae61d4c4fa2051eabf006326b80443f2d28a9e8662b5bd'


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def normalize(value):
    return json.loads(canonical_bytes(value))


class Journey:
    def __init__(self, output, run, product):
        self.output, self.run, self.product = output, run, product
        self.results = []

    def check(self, name, actual, detail=None):
        self.results.append(dict(name=name, outcome='passed' if actual else 'failed', detail=detail))

    def cli(self, name, arguments):
        command = ['uv', 'run', 'ci', 'records', *arguments, '--run', str(self.run), '--json']
        result = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
        dump(self.output / (name + '.command.json'), dict(command=command, exit_code=result.returncode))
        (self.output / (name + '.stdout')).write_text(result.stdout)
        (self.output / (name + '.stderr')).write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f'{name}: exit {result.returncode}: {result.stdout[-1000:]}')
        return json.loads(result.stdout)

    def source_cli(self, name, request):
        command = ['uv', 'run', 'ci', 'source', 'inspect', str(self.run), '--producing-task', str(request.task_id), '--product', request.product_key, '--native-digest', request.content_digest, '--native-view', request.view, '--limit', str(request.limit), '--max-rows', str(request.max_rows), '--max-bytes', str(request.max_bytes), '--json']
        for field, option in [('pointer', '--pointer'), ('section_pointer', '--section'), ('membership', '--membership'), ('cell_index', '--cell'), ('occurrence_id', '--occurrence'), ('artifact_digest', '--artifact-digest'), ('collection', '--collection'), ('cursor', '--cursor')]:
            value = getattr(request, field)
            if value is not None:
                command.extend((option, str(value)))
        result = subprocess.run(command, cwd=REPO, text=True, capture_output=True)
        dump(self.output / (name + '.command.json'), dict(command=command, exit_code=result.returncode))
        (self.output / (name + '.stdout')).write_text(result.stdout)
        (self.output / (name + '.stderr')).write_text(result.stderr)
        if result.returncode:
            raise RuntimeError(f'{name}: exit {result.returncode}: {result.stdout[-1000:]}')
        return json.loads(result.stdout)

    async def tool(self, client, name, request, label):
        wire = await client.call_tool_mcp(name, {'request': request.model_dump(mode='json')})
        encoded = wire.model_dump_json(by_alias=True, exclude_none=True).encode()
        (self.output / (label + '.mcp.json')).write_bytes(encoded)
        dump(self.output / (label + '.request.json'), request.model_dump(mode='json'))
        return wire, len(encoded)

    async def run_journey(self, engine):
        request = RecordRequest(run_id=self.run, limit=2)
        with read_snapshot(engine) as conn:
            page = serve_record_results(conn, request)
            support = serve_record_support(conn, request)
            projection = read_completed_record_projection(conn, run_id=self.run, include_diagnostics=False)
            identity = conn.exec_driver_sql('SELECT current_user,current_database(),inet_server_port()').one()
        dump(self.output / 'query-page.json', page.model_dump(mode='json'))
        dump(self.output / 'query-support.json', support.model_dump(mode='json'))
        dump(self.output / 'database-identity.json', list(identity))
        self.check('release_pin', page.binding['release_id'] == RELEASE, page.binding)
        self.check('query_support_same_page', support.page == page)
        self.check('scientific_comparison_unmodeled', support.scientific_support_opposition.availability == 'unmodeled')
        self.check('ordinary_diagnostics_omitted', all(row.diagnostics is None and not row.diagnostics_included for row in page.coverage), [dict(task=row.selected_task_id, origin=row.origin_task_id, available=row.diagnostics_available, included=row.diagnostics_included) for row in page.coverage])
        query_rows = {name: normalize([asdict(row) for row in rows]) for name, rows in projection.rows.items()}
        dump(self.output / 'query-relations.json', query_rows)
        self.check('cli_query_record_equality', self.cli('cli-list', ['list', '--limit', '2']) == page.model_dump(mode='json'))
        support_path = self.output / 'cli-support-export.json'
        cli_support = self.cli('cli-support', ['support', '--limit', '2', '--out', str(support_path)])
        self.check('cli_query_support_equality', cli_support == support.model_dump(mode='json'))
        self.check('support_export_equality', json.loads(support_path.read_bytes()) == cli_support)
        if page.records:
            selected = page.records[0].record
            detail_request = request.model_copy(update={'record_id': selected['record_id'], 'interpretation_id': selected['interpretation_id']})
            with read_snapshot(engine) as conn:
                detail_page = serve_record_results(conn, detail_request)
            self.check('cli_query_record_detail_equality', self.cli('cli-detail', ['list', '--limit', '2', '--record', selected['record_id'], '--interpretation', selected['interpretation_id']]) == detail_page.model_dump(mode='json'))

        server = build_semantic_server(session=SemanticAgentSession(engine, self.run))
        async with Client(server) as client:
            dump(self.output / 'registered-tools.json', [tool.name for tool in await client.list_tools()])
            for name, expected in [('records', page), ('record_support', support)]:
                wire, size = await self.tool(client, name, request, name)
                self.check(name + '_registered_equality', not wire.is_error and wire.structured_content == expected.model_dump(mode='json'), dict(envelope_bytes=size, budget=request.page_bytes))
                self.check(name + '_whole_envelope_within_budget', size <= request.page_bytes)
                # Admit the semantic page but refuse its full duplicated MCP envelope.
                body_size = len(expected.model_dump_json().encode())
                tight = request.model_copy(update={'page_bytes': max(body_size + 128, size - 1)})
                refused, refused_size = await self.tool(client, name, tight, name + '-envelope-refusal')
                self.check(name + '_whole_envelope_refusal', bool(refused.is_error), dict(response_bytes=refused_size, requested_budget=tight.page_bytes, semantic_bytes=body_size))

            gathered = list(page.records)
            cursor = page.next_cursor
            ordinal = 0
            while cursor is not None and ordinal < 50:
                ordinal += 1
                next_request = request.model_copy(update={'cursor': cursor})
                with read_snapshot(engine) as conn:
                    next_page = serve_record_results(conn, next_request)
                wire, _ = await self.tool(client, 'records', next_request, f'records-page-{ordinal:03d}')
                self.check(f'continuation_{ordinal}_query_mcp_equality', not wire.is_error and wire.structured_content == next_page.model_dump(mode='json'))
                self.check(f'continuation_{ordinal}_binding', next_page.binding == page.binding and next_page.cut_id == page.cut_id)
                gathered.extend(next_page.records)
                if ordinal == 1:
                    self.check('cli_query_record_continuation_equality', self.cli('cli-record-continuation', ['list', '--limit', '2', '--cursor', cursor]) == next_page.model_dump(mode='json'))
                    changed = next_request.model_copy(update={'family': 'measurement'})
                    refused, _ = await self.tool(client, 'records', changed, 'records-changed-selection-refusal')
                    self.check('record_continuation_changed_selection_refused', bool(refused.is_error))
                cursor = next_page.next_cursor
            identities = [(r.record['record_id'], r.record['interpretation_id']) for r in gathered]
            self.check('pagination_unique', len(set(identities)) == len(identities))
            self.results.append(dict(name='record_pagination', outcome='passed' if cursor is None else 'partial', pages=ordinal + 1, records=len(gathered), continuation_available=cursor is not None))

            for mode, values in [('small', dict(max_bytes=1024)), ('bounded', dict(max_bytes=32 * 1024**2))]:
                detailed = request.model_copy(update=dict(include_diagnostics=True, **values))
                try:
                    with read_snapshot(engine) as conn:
                        detail = serve_record_results(conn, detailed)
                    dump(self.output / f'query-diagnostics-{mode}.json', detail.model_dump(mode='json'))
                    self.results.append(dict(name='explicit_diagnostics_' + mode, outcome='passed', admitted=True, coverage_rows=len(detail.coverage)))
                except Exception as error:
                    dump(self.output / f'query-diagnostics-{mode}-refusal.json', dict(type=type(error).__name__, message=str(error), reason=getattr(error, 'reason', None)))
                    self.results.append(dict(name='explicit_diagnostics_' + mode, outcome='passed' if 'limit' in type(error).__name__.lower() else 'failed', admitted=False, type=type(error).__name__))
                    refused, _ = await self.tool(client, 'records', detailed, f'records-diagnostics-{mode}-refusal')
                    self.check(f'explicit_diagnostics_{mode}_registered_refusal', bool(refused.is_error))

            source_requests = []
            by_family = {}
            for record in gathered:
                by_family.setdefault(record.record['family'], record)
            selected_families = [name for name in ('table', 'formula_context', 'definition', 'measurement', 'assertion') if name in by_family]
            for family in selected_families:
                source_requests.extend(by_family[family].source_requests[:2])
            if not source_requests and self.product:
                source_requests.append(NativeSourceRequest(run_id=self.run, **self.product, limit=2, max_bytes=1024**2))
            seen = set()
            for number, source_request in enumerate(source_requests[:12]):
                # Selected retained cells can carry a large companion; the separate
                # custody probe preserves their valid default-budget refusals.
                source_request = source_request.model_copy(update={'limit': 2, 'max_bytes': (8 if gathered else 1) * 1024**2})
                key = source_request.model_dump_json()
                if key in seen:
                    continue
                seen.add(key)
                try:
                    with read_snapshot(engine) as conn:
                        source = inspect_native_source(conn, source_request)
                    dump(self.output / f'source-{number:03d}.query.json', source.model_dump(mode='json'))
                    wire, size = await self.tool(client, 'inspect_source', source_request, f'source-{number:03d}')
                    self.check(f'source_{number}_query_registered_equality', not wire.is_error and wire.structured_content == source.model_dump(mode='json'), dict(envelope_bytes=size, rows=len(source.rows), view=source_request.view))
                    self.check(f'source_{number}_query_cli_equality', self.source_cli(f'source-{number:03d}-cli', source_request) == source.model_dump(mode='json'))
                    if source.next_cursor:
                        following = source_request.model_copy(update={'cursor': source.next_cursor})
                        with read_snapshot(engine) as conn:
                            next_source = inspect_native_source(conn, following)
                        wire, _ = await self.tool(client, 'inspect_source', following, f'source-{number:03d}-next')
                        self.check(f'source_{number}_continuation_equality', not wire.is_error and wire.structured_content == next_source.model_dump(mode='json'))
                        changed = following.model_copy(update={'content_digest': '0' * 64})
                        refused, _ = await self.tool(client, 'inspect_source', changed, f'source-{number:03d}-changed-pin')
                        self.check(f'source_{number}_changed_pin_refused', bool(refused.is_error))
                except Exception:
                    (self.output / f'source-{number:03d}.failure.txt').write_text(traceback.format_exc())
                    self.results.append(dict(name=f'source_{number}', outcome='failed'))
        for format in ('jsonl', 'parquet'):
            destination = self.output / ('export-' + format)
            try:
                exported = self.cli('cli-export-' + format, ['export', '--format', format, '--out', str(destination)])
                manifest = json.loads((destination / 'manifest.json').read_bytes())
                self.check(format + '_export_return_manifest', exported['manifest'] == manifest)
                # A detached capture has its own capture UUID; compare semantic identity.
                semantic_keys = ('release_id', 'realization_id', 'data_revision')
                self.check(format + '_export_binding', all(manifest['binding'][key] == page.binding[key] for key in semantic_keys), manifest['binding'])
                exported_records = manifest['record_projection']
                self.check(format + '_export_completed_result_pin', exported_records['run_id'] == self.run and exported_records['cut_id'] == page.cut_id and exported_records['projection_digest'] == page.projection_digest)
                for name, expected in query_rows.items():
                    path = destination / manifest['relations'][name]['file']
                    if format == 'jsonl':
                        actual = [json.loads(line) for line in path.read_bytes().splitlines()]
                    else:
                        import pyarrow.parquet as pq
                        actual = pq.read_table(path).to_pylist()
                    self.check(format + '_relation_' + name, actual == expected, dict(rows=len(actual), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
                self.check(format + '_coverage_equality', manifest['record_projection']['coverage'] == normalize([asdict(row) for row in projection.coverage]))
            except Exception:
                (self.output / ('export-' + format + '.failure.txt')).write_text(traceback.format_exc())
                self.results.append(dict(name=format + '_export', outcome='failed'))
        self.summary = dict(run_id=self.run, binding=page.binding, cut_id=page.cut_id, records=len(projection.rows['source_record']), family_counts=dict(Counter(row.family for row in projection.rows['source_record'])), reports=len(page.reports), producer_coverage=len(page.coverage), source_handles_checked=len(seen), checks=self.results)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=int, required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--completed-receipt', type=Path)
    args = parser.parse_args()
    output = HERE / 'raw' / args.output
    output.mkdir(parents=True, exist_ok=False)
    product = json.loads(args.completed_receipt.read_bytes())['native_product'] if args.completed_receipt else None
    source_paths = [Path(__file__), *[(REPO / 'python/corpus-structure/src/corpus_structure' / name) for name in ['serve/record_results.py', 'serve/record_support.py', 'serve/native_source.py', 'serve/record_export.py', 'intervene/record_tools.py', 'intervene/semantic_server.py', 'semantic/record_queries.py']]]
    dump(output / 'context.json', dict(date_utc=datetime.now(timezone.utc).isoformat(), python=platform.python_version(), versions={p: importlib.metadata.version(p) for p in ['fastmcp', 'mcp', 'sqlalchemy', 'pyarrow']}, sources={str(path.relative_to(REPO)):hashlib.sha256(path.read_bytes()).hexdigest() for path in source_paths}, scope='live read principal; in-process registered MCP; actual subprocess CLI; detached JSONL/Parquet exports', scientific_quality='not_established', run_id=args.run, release_id=RELEASE))
    journey = Journey(output, args.run, product)
    try:
        with open_runtime_engine(Settings(), 'm1-actual-consumers', purpose='read') as engine:
            asyncio.run(journey.run_journey(engine))
    except Exception:
        (output / 'failure.txt').write_text(traceback.format_exc())
        journey.summary = dict(run_id=args.run, checks=journey.results, outcome='failed')
    dump(output / 'summary.json', journey.summary)
    print(json.dumps(journey.summary))


if __name__ == '__main__':
    main()
