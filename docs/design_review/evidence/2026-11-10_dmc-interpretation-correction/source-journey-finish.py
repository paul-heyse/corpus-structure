"""Finish the existing genuine source journey with read-only installed consumers."""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import anyio
from fastmcp import Client

from corpus_structure.intervene.semantic_server import build_semantic_server
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.portable_interpretation import export_interpretation_contract
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.releases import open_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

HERE=Path(__file__).parent
RAW=HERE/'raw'/(sys.argv[1] if len(sys.argv)>1 else 'source-journey-finish')
RAW.mkdir(exist_ok=False)
spec=importlib.util.spec_from_file_location('journey',HERE/'source-journey.py')
journey=importlib.util.module_from_spec(spec)
spec.loader.exec_module(journey)
journey.RAW=RAW
prior=HERE/'raw/source-journey-05'
receipts=json.loads((prior/'source-journey-runs.json').read_bytes())
release=receipts[0]['release_id']
config=json.loads((prior/'normal-authored-input.json').read_bytes())
settings=Settings(runtime={'default_project':config['source']['project_id']})

async def main():
    comparison=journey.cli_answer('pinned-exclusion-comparison','research','compare-exclusions',
        '--before-run',487,'--after-run',487,'--max-rows',10000,'--max-bytes',8*1024**2)
    async with Client(build_semantic_server(settings=settings)) as client:
        reply=await client.call_tool('compare_identity_exclusions',dict(before_run=487,after_run=487,max_rows=10000,max_bytes=8*1024**2))
        (RAW/'pinned-exclusion-comparison-mcp.json').write_bytes(canonical_bytes(reply.structured_content))
        def stable_facts(value):
            facts=json.loads(canonical_bytes(value))
            for side in ('before','after'):
                facts['comparison'][side]['binding'].pop('capture_id')
            return facts
        assert not reply.is_error and stable_facts(reply.structured_content)==stable_facts(comparison)
        grouped=await client.call_tool('group_measurement_interpretations',dict(source_run=493,review_run=495,review_cut=612))
        expected=json.loads((prior/'measurement-groups.json').read_bytes())
        assert not grouped.is_error and grouped.structured_content['body']==expected
        (RAW/'measurement-mcp-groups.json').write_bytes(canonical_bytes(grouped.structured_content))
    with open_runtime_engine(settings,'dmc-independent-contract-export',purpose='read') as engine,read_snapshot(engine) as conn:
        prepared=open_release(conn,release)
        exported=export_interpretation_contract(prepared,RAW/'offline-contract')
    instance=dict(kind='proposal',semantic_type='terminology.interpretation',effect='retain_private',
        assessment_event='local-contribution-1',question='interpret.terminology',value=config['reviews'][0])
    path=RAW/'offline-input.json';path.write_bytes(canonical_bytes(instance))
    script=HERE.parents[3]/'examples/offline_interpretation.py'
    completed=subprocess.run([sys.executable,'-I',str(script),str(RAW/'offline-contract'),str(path),
        '--expected-digest',exported['manifest_digest']],capture_output=True,text=True)
    (RAW/'offline-preflight.stdout.json').write_text(completed.stdout)
    (RAW/'offline-preflight.stderr.txt').write_text(completed.stderr)
    assert completed.returncode==0 and json.loads(completed.stdout)['outcome']=='passed'
    result=dict(outcome='passed',release=release,source_run=487,source_cut=604,
        receipts=receipts,source_sentence='A company buys 100 lightbulbs, each of which has an exponential lifetime of 1000 hours.',
        quantity_role='unresolved',basis='unknown',numerical_equivalence='unassessed',
        checks=['normal-and-variance-filter','retained-review-cli-mcp-parity','bound-known-use-surveys',
                'ordinary-genuine-hours-record','original-coordinate-and-later-record-custody',
                'recognized-hour-time-group-cli-mcp-parity','independent-archived-schema-preflight',
                'pinned-exclusion-cli-mcp-parity','protected-project-and-original-run-pre-post-assertions'],
        limitations=['structural offline preflight only','external unit identifiers remain descriptive/DRAFT/unchecked',
                     'no numeric role, empirical status, conversion or numerical equivalence inferred',
                     'empty genuine exclusion population does not establish positive source coverage'])
    (RAW/'source-journey-result.json').write_bytes(canonical_bytes(result))
    print(json.dumps(result))

anyio.run(main)
