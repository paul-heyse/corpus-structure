"""Actual read-only retained run11/run14 ordinary-budget source inspection."""

from __future__ import annotations

import asyncio
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from fastmcp import Client

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.query import ReadLimit, read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.settings import Settings

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE.parent
REPO = EVIDENCE.parents[3]
EARLIER = EVIDENCE.parent / '2026-11-04_m1-actual-consumers/raw'


def dump(path, value):
    path.write_bytes(canonical_bytes(value))


def identities(rows):
    return {canonical_bytes(row) for row in rows}


def source_hashes():
    return {name:hashlib.sha256((REPO / 'python/corpus-structure/src/corpus_structure' / name).read_bytes()).hexdigest() for name in ['serve/native_source.py', 'semantic/native_analysis.py', 'semantic/source_views.py', 'semantic/operations.py', 'semantic/pdf_record_reader.py']}


async def main():
    output = HERE / 'raw' / sys.argv[1]
    output.mkdir(exist_ok=False)
    checks = []

    def check(name, condition, **details):
        checks.append(dict(name=name, outcome='passed' if condition else 'failed', **details))

    initial_hashes = source_hashes()
    dump(output / 'sources.json', initial_hashes)
    samples = [
        (11, 'formula', EARLIER / 'native-custody-gs-002/selected-002.query.json'),
        (11, 'cell', EARLIER / 'native-custody-gs-002/selected-000.query.json'),
        (14, 'formula', EARLIER / 'native-custody-gs-002/selected-002.query.json'),
        (14, 'cell', EARLIER / 'actual-gs-14-001/source-001.query.json'),
    ]
    with open_runtime_engine(Settings(), 'm1-scoped-native-live', purpose='read') as engine:
        for run_id in (11, 14):
            server = build_semantic_server(SemanticAgentSession(engine, run_id))
            async with Client(server) as client:
                for selected_run, kind, path in samples:
                    if selected_run != run_id:
                        continue
                    label = f'run-{run_id}-{kind}'
                    baseline = json.loads(path.read_bytes())
                    request = NativeSourceRequest.model_validate(baseline['selection']).model_copy(update={'run_id':run_id, 'max_bytes':1048576})
                    dump(output / (label + '.request.json'), request.model_dump(mode='json'))
                    with read_snapshot(engine) as conn:
                        response = inspect_native_source(conn, request)
                    query = response.model_dump(mode='json')
                    dump(output / (label + '.query.json'), query)
                    wire = await client.call_tool_mcp('inspect_source', {'request':request.model_dump(mode='json')})
                    content = wire.model_dump_json(by_alias=True, exclude_none=True).encode()
                    (output / (label + '.mcp.json')).write_bytes(content)
                    check(label + '_query_mcp', not wire.is_error and wire.structured_content == query, envelope_bytes=len(content), budget=request.max_bytes)
                    check(label + '_complete_envelope', len(content) <= request.max_bytes)
                    command = ['uv','run','ci','source','inspect',str(run_id),'--producing-task',str(request.task_id),'--product',request.product_key,'--native-digest',request.content_digest,'--pointer',request.pointer,'--native-view',kind,'--max-bytes',str(request.max_bytes),'--limit',str(request.limit),'--json']
                    if request.cell_index is not None:
                        command.extend(('--cell',str(request.cell_index)))
                    cli = subprocess.run(command,cwd=REPO,capture_output=True,text=True)
                    dump(output / (label + '.command.json'),dict(command=command,exit_code=cli.returncode))
                    (output / (label + '.stdout')).write_text(cli.stdout)
                    (output / (label + '.stderr')).write_text(cli.stderr)
                    check(label + '_query_cli', cli.returncode == 0 and json.loads(cli.stdout) == query)
                    check(label + '_source_health', query['health'] == baseline['health'])
                    if kind == 'formula':
                        for field in ('pointer','original_text','recognized_latex','recognition','inline_alignment_reports','regions'):
                            check(label + '_preserved_' + field, query['rows'][0][field] == baseline['rows'][0][field])
                        check(label + '_companion_preserved', query['companion'] == baseline['companion'])
                        if run_id == 11:
                            check(label + '_analysis_preserved', query['rows'][0]['interpretation'] == baseline['rows'][0]['interpretation'])
                    else:
                        check(label + '_cell_value_preserved', query['rows'] == baseline['rows'])
                        companion = query['companion']
                        selected_ids = {request.pointer, request.pointer + '/data/table_cells/' + str(request.cell_index)}
                        check(label + '_exact_cell_parent', {r['occurrence_id'] for r in companion['occurrences']} == selected_ids)
                        own = request.task_id,request.product_key,request.content_digest
                        expected_relations = [r for r in baseline['companion']['relations'] if any(e['occurrence_id'] in selected_ids and (e['target_task_id'],e['target_product_key'],e['target_content_digest']) == own for e in r['endpoints'])]
                        check(label + '_complete_selected_relations', identities(companion['relations']) == identities(expected_relations))
                        for family in ('occurrences','inputs','coverage','mapping_reports'):
                            check(label + '_retained_' + family, identities(companion[family]) <= identities(baseline['companion'][family]))
                        check(label + '_coverage_preserved', identities(companion['coverage']) == identities(baseline['companion']['coverage']))
                        check(label + '_companion_smaller', len(canonical_bytes(companion)) < len(canonical_bytes(baseline['companion'])), before_bytes=len(canonical_bytes(baseline['companion'])), after_bytes=len(canonical_bytes(companion)))
                    tight = request.model_copy(update={'max_bytes':1024})
                    with read_snapshot(engine) as conn:
                        try:
                            inspect_native_source(conn,tight)
                        except ReadLimit as error:
                            check(label + '_work_refusal', True, reason=error.reason, message=str(error))
                        else:
                            check(label + '_work_refusal', False)
                    refused = await client.call_tool_mcp('inspect_source', {'request':tight.model_dump(mode='json')})
                    (output / (label + '.work-refusal.mcp.json')).write_text(refused.model_dump_json(by_alias=True,exclude_none=True))
                    check(label + '_registered_work_refusal', bool(refused.is_error))
    final_hashes = source_hashes()
    dump(output / 'sources-end.json', final_hashes)
    check('source_files_stable', initial_hashes == final_hashes)
    dump(output / 'summary.json', dict(checks=checks,scope='actual reader principal; old pinned run11/run14; query/CLI/registered in-process MCP; ordinary 1MiB work and whole-response budgets; no model or reference-quality claim'))
    print(json.dumps(checks))


if __name__ == '__main__':
    asyncio.run(main())
