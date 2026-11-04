"""Continue the actual run14 census after the retained first102 interpretations."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pyarrow.parquet as pq
from fastmcp import Client

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.record_results import RecordRequest, serve_record_results
from corpus_structure.settings import Settings
from run_consumers import HERE, Journey, dump


def keys(records):
    return [(r['record']['record_id'], r['record']['interpretation_id']) for r in records]


async def census(engine, journey, earlier):
    first = json.loads((earlier / 'query-page.json').read_bytes())
    gathered = keys(first['records'])
    previous = first
    for path in sorted(earlier.glob('records-page-*.mcp.json')):
        wire = json.loads(path.read_bytes())
        if wire.get('isError'):
            raise ValueError(f'preceding census page refused: {path}')
        previous = wire['structuredContent']
        gathered.extend(keys(previous['records']))
    original_count = len(gathered)
    original = RecordRequest.model_validate(json.loads((earlier / 'records.request.json').read_bytes()))
    request = original.model_copy(update={'cursor': previous['next_cursor'], 'limit': 20, 'page_bytes': 8 * 1024**2})
    journey.check('starting_prefix_102', original_count == 102)
    journey.check('same_normalized_selection', request.filters() == original.filters())
    dump(journey.output / 'prefix-identities.json', gathered)
    dump(journey.output / 'prefix-binding.json', dict(binding=first['binding'], cut_id=first['cut_id'], projection_digest=first['projection_digest'], earlier=str(earlier.relative_to(HERE))))
    server = build_semantic_server(session=SemanticAgentSession(engine, journey.run))
    pages = 0
    async with Client(server) as client:
        while request.cursor is not None and pages < 100:
            pages += 1
            with read_snapshot(engine) as conn:
                page = serve_record_results(conn, request)
            dump(journey.output / f'page-{pages:03d}.query.json', page.model_dump(mode='json'))
            wire, size = await journey.tool(client, 'records', request, f'page-{pages:03d}')
            journey.check(f'page_{pages}_whole_envelope', not wire.is_error and size <= request.page_bytes, dict(envelope_bytes=size, budget=request.page_bytes))
            if wire.is_error:
                break
            journey.check(f'page_{pages}_query_mcp_equality', wire.structured_content == page.model_dump(mode='json'))
            journey.check(f'page_{pages}_binding', page.binding == first['binding'] and page.cut_id == first['cut_id'] and page.projection_digest == first['projection_digest'])
            if pages == 1:
                journey.check('first_continued_cli_equality', journey.cli('cli-continued', ['list', '--cursor', request.cursor, '--limit', '20', '--page-bytes', str(request.page_bytes)]) == page.model_dump(mode='json'))
            gathered.extend(keys(page.model_dump(mode='json')['records']))
            request = request.model_copy(update={'cursor': page.next_cursor})
    full = json.loads((earlier / 'query-relations.json').read_bytes())['source_record']
    expected = {(r['record_id'], r['interpretation_id']) for r in full}
    actual = set(gathered)
    journey.check('completed_continuation', request.cursor is None)
    journey.check('census_no_duplicates', len(gathered) == len(actual), dict(identities=len(gathered), unique=len(actual)))
    journey.check('census_exact_query_projection', actual == expected, dict(expected=len(expected), actual=len(actual), missing=sorted(expected - actual), unexpected=sorted(actual - expected)))
    for format in ('jsonl', 'parquet'):
        root = earlier / ('export-' + format)
        manifest = json.loads((root / 'manifest.json').read_bytes())
        path = root / manifest['relations']['source_record']['file']
        rows = [json.loads(row) for row in path.read_bytes().splitlines()] if format == 'jsonl' else pq.read_table(path).to_pylist()
        exported = {(r['record_id'], r['interpretation_id']) for r in rows}
        journey.check('census_exact_' + format + '_export', actual == exported and len(gathered) == len(rows), dict(exported=len(rows)))
    dump(journey.output / 'all-identities.json', gathered)
    summary = dict(run_id=journey.run, cut_id=first['cut_id'], binding=first['binding'], prefix_pages=51, prefix_interpretations=original_count, continued_pages=pages, continued_interpretations=len(gathered) - original_count, total_interpretations=len(gathered), complete=request.cursor is None, next_cursor=request.cursor, checks=journey.results, scope='actual candidate transport identity census; no accepted or five-family quality claim')
    dump(journey.output / 'summary.json', summary)
    print(json.dumps(summary))


def main():
    earlier = HERE / 'raw' / 'actual-gs-14-001'
    output = HERE / 'raw' / 'actual-gs-14-census-001'
    output.mkdir(exist_ok=False)
    journey = Journey(output, 14, None)
    with open_runtime_engine(Settings(), 'm1-actual-consumer-census', purpose='read') as engine:
        asyncio.run(census(engine, journey, earlier))


if __name__ == '__main__':
    main()
