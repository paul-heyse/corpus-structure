"""Bounded retained-native custody inspection, separate from record quality."""

from __future__ import annotations

import argparse
import asyncio
import json
import traceback
from collections import Counter
from pathlib import Path

from fastmcp import Client

from corpus_structure.intervene.semantic_server import SemanticAgentSession, build_semantic_server
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.native_source import NativeSourceRequest, inspect_native_source
from corpus_structure.settings import Settings
from run_consumers import HERE, Journey, dump


async def inspect(engine, journey, max_bytes):
    request = NativeSourceRequest(run_id=journey.run, **journey.product, limit=1000, max_bytes=8 * 1024**2)
    scanned = []
    for number in range(3):
        with read_snapshot(engine) as conn:
            result = inspect_native_source(conn, request)
        dump(journey.output / f'item-inventory-{number:03d}.json', result.model_dump(mode='json'))
        scanned.extend(result.rows)
        if not result.next_cursor:
            break
        request = request.model_copy(update={'cursor': result.next_cursor})
    dump(journey.output / 'inventory-summary.json', dict(scanned_rows=len(scanned), labels=dict(Counter(r['label'] for r in scanned)), continuation_available=result.next_cursor is not None, max_pages=3))
    selected = []
    for label, view in [('table', 'cell'), ('formula', 'formula')]:
        matches = [r for r in scanned if r['label'] == label][:2]
        for row in matches:
            selected.append(NativeSourceRequest(run_id=journey.run, **journey.product, view=view, pointer=row['pointer'], cell_index=0 if view == 'cell' else None, max_bytes=max_bytes))
            selected.append(NativeSourceRequest(run_id=journey.run, **journey.product, view='trace', pointer=row['pointer'], max_bytes=max_bytes))
    server = build_semantic_server(session=SemanticAgentSession(engine, journey.run))
    async with Client(server) as client:
        for number, request in enumerate(selected):
            try:
                with read_snapshot(engine) as conn:
                    source = inspect_native_source(conn, request)
                dump(journey.output / f'selected-{number:03d}.query.json', source.model_dump(mode='json'))
                wire, size = await journey.tool(client, 'inspect_source', request, f'selected-{number:03d}')
                journey.check(f'selected_{number}_mcp_equality', not wire.is_error and wire.structured_content == source.model_dump(mode='json'), dict(view=request.view, pointer=request.pointer, envelope_bytes=size))
                journey.check(f'selected_{number}_cli_equality', journey.source_cli(f'selected-{number:03d}-cli', request) == source.model_dump(mode='json'))
            except Exception:
                (journey.output / f'selected-{number:03d}.failure.txt').write_text(traceback.format_exc())
                journey.results.append(dict(name=f'selected_{number}', outcome='failed'))
    dump(journey.output / 'summary.json', dict(run_id=journey.run, native_product=journey.product, max_bytes=max_bytes, scope='retained source custody only; no record-to-native handoff or source quality established', selected_reads=len(selected), checks=journey.results))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--completed-receipt', type=Path, required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--max-bytes', type=int, default=1024**2)
    args = parser.parse_args()
    receipt = json.loads(args.completed_receipt.read_bytes())
    output = HERE / 'raw' / args.output
    output.mkdir(parents=True, exist_ok=False)
    journey = Journey(output, receipt['source_run_id'], receipt['native_product'])
    with open_runtime_engine(Settings(), 'm1-actual-consumer-native', purpose='read') as engine:
        asyncio.run(inspect(engine, journey, args.max_bytes))
    print(json.dumps(journey.results))


if __name__ == '__main__':
    main()
