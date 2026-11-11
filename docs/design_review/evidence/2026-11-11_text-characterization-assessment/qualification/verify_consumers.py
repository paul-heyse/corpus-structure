"""Actual bounded retained consumers over the exact completed combined book pin.

Prepare only after final book-result. Live checks use the owning native API, installed
CLI and actual FastMCP server registration; no extraction/inference or gold reads.
Detached capture remains the installed ci review export owner. Replay authenticates
that delivered exact closure through its existing verifier before comparing responses.
"""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

from fastmcp import Client
from sqlalchemy import select

from corpus_structure.intervene.semantic_server import SemanticProjectSession, build_semantic_server
from corpus_structure.semantic.characterization_store import read_view
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.product_reference import ProductReference
from corpus_structure.semantic.query import read_snapshot
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.serve.characterization import CharacterizationRequest, inspect_characterization
from corpus_structure.serve.characterization_replay import CharacterizationReviewSelection, inspect_characterization_review, verify_characterization_review
from corpus_structure.settings import Settings

HERE=Path(__file__).resolve().parent
EVIDENCE=HERE.parent
PROJECT='nce-grinstead-snell-full-book'


def write(name,value):
    path=HERE/name;path.parent.mkdir(exist_ok=True,parents=True)
    path.write_bytes(canonical_bytes(value)+b'\n')


def digest(value):
    return sha256(canonical_bytes(value)).hexdigest()


def prepared_requests():
    payload=json.loads((HERE/'consumer-requests.json').read_bytes())
    final=json.loads((EVIDENCE/'book-result.json').read_bytes())
    if len(final)!=1 or payload['view']!=final[0]['view']:
        raise ValueError('consumer requests differ from exact final book result')
    return payload


def prepare(settings,export_max_bytes):
    final=json.loads((EVIDENCE/'book-result.json').read_bytes())
    if len(final)!=1:raise ValueError('one exact final combined book result is required')
    pin=ProductReference(**final[0]['view'])
    with open_runtime_engine(settings,'tc11-consumer-prepare',purpose='read') as engine,read_snapshot(engine) as conn:
        view=read_view(conn,pin)
        tasks,runs=table('ops.task'),table('ops.run')
        owner=conn.execute(select(tasks.c.run_id,runs.c.project_id).join(runs,runs.c.id==tasks.c.run_id).where(tasks.c.id==pin.task_id)).one()
        if owner.project_id!=PROJECT or len(view.payload['source_scope']['source_view_ids'])!=316:
            raise ValueError('consumer source differs from declared whole-book project/scope')
    base=dict(run_id=owner.run_id,**pin.values(),limit=2,max_bytes=1048576)
    requests={
        'summary':CharacterizationRequest(**base,view='summary'),
        'coverage':CharacterizationRequest(**base,view='coverage'),
        'native-annotations':CharacterizationRequest(**base,view='annotations',family='spacy.tokens'),
        'formal-annotations':CharacterizationRequest(**base,view='annotations',family='formal.math'),
    }
    output=EVIDENCE/'output-panel'/'manifest.json'
    if output.exists():
        manifest=json.loads(output.read_bytes())
        if manifest['view']!=pin.values():raise ValueError('selected outputs belong to another final view')
        for selected in manifest['selected']:
            ref=selected['output']
            if selected['facet']=='predicates_roles' and ref['collection']=='terms':
                requests['exact-predicate-term']=CharacterizationRequest(**base,view='terms',layer_key=ref['layer']['product_key'],annotation_id=ref['local_id'])
            if selected['facet']=='native_fidelity':
                container=ref['local_id'] if selected['retained_value'].get('kind')=='native.block' else selected['retained_value'].get('native_token',{}).get('container')
                if container:
                    requests['native-container-membership']=CharacterizationRequest(**base,view='membership',layer_key=ref['layer']['product_key'],annotation_id=container)
    body=dict(version='tc11-actual-consumer-requests-1',project=PROJECT,view=pin.values(),base_document=view.base_document.values(),run_id=owner.run_id,requests={name:r.model_dump(mode='json') for name,r in requests.items()},limit='Bounded retained consumer parity and exact closure; no semantic reference/grade or fresh inference.')
    write('consumer-requests.json',body)
    selection=CharacterizationReviewSelection(run_id=owner.run_id,**pin.values(),max_bytes=export_max_bytes,max_source_rows=316)
    write('review-selection.json',selection.model_dump(mode='json'))
    print(json.dumps(dict(view=pin.values(),run=owner.run_id,requests=list(requests),export_max_bytes=export_max_bytes)))


def cli_command(request):
    command=['uv','run','ci','source','enriched',str(request.run_id),'--producing-task',str(request.task_id),'--product',request.product_key,'--digest',request.content_digest,'--view',request.view,'--limit',str(request.limit),'--max-bytes',str(request.max_bytes),'--json']
    for field,option in (('layer_key','--layer'),('annotation_id','--annotation'),('family','--family'),('kind','--kind')):
        value=getattr(request,field)
        if value is not None:command.extend([option,value])
    return command


async def mcp_responses(engine,requests):
    session=SemanticProjectSession(engine,PROJECT)
    server=build_semantic_server(session,read_engine=engine)
    values={}
    async with Client(server) as client:
        for name,request in requests.items():
            try:
                result=await client.call_tool('inspect_enriched_document',{'request':request.model_dump(mode='json')})
                values[name]=dict(outcome='passed',response=result.structured_content,is_error=result.is_error)
            except Exception as error:
                values[name]=dict(outcome='failed',error_type=type(error).__name__,reason=str(error))
    return values


def live(settings):
    bound=prepared_requests()
    requests={name:CharacterizationRequest.model_validate(r) for name,r in bound['requests'].items()}
    outcomes={};native={}
    with open_runtime_engine(settings,'tc11-actual-consumer-live',purpose='read') as engine:
        for name,request in requests.items():
            try:
                with read_snapshot(engine) as conn:
                    response=inspect_characterization(conn,request).model_dump(mode='json')
                native[name]=response;write(f'raw/consumer-native-{name}.json',response)
                outcomes[name]=dict(native='passed',native_digest=digest(response),items=len(response['items']),coverage_total=response['coverage_total'],coverage_truncated=response['coverage_truncated'],continuation_present=response['continuation'] is not None)
            except Exception as error:
                outcomes[name]=dict(native='failed',error_type=type(error).__name__,reason=str(error))
            command=cli_command(request)
            result=subprocess.run(command,text=True,capture_output=True,check=False)
            write(f'raw/consumer-cli-{name}-receipt.json',dict(command=command,exit_code=result.returncode,stderr=result.stderr[-8000:]))
            try:
                if result.returncode:raise ValueError('installed CLI refused; see retained receipt')
                response=json.loads(result.stdout)
                write(f'raw/consumer-cli-{name}.json',response)
                equal=name in native and canonical_bytes(response)==canonical_bytes(native[name])
                outcomes[name].update(cli='passed' if equal else 'failed',cli_equals_native=equal)
            except Exception as error:
                outcomes[name].update(cli='failed',cli_error=str(error))
        mcp=asyncio.run(mcp_responses(engine,requests))
    for name,result in mcp.items():
        write(f'raw/consumer-mcp-{name}.json',result)
        equal=result['outcome']=='passed' and not result.get('is_error') and name in native and canonical_bytes(result['response'])==canonical_bytes(native[name])
        outcomes[name].update(mcp='passed' if equal else 'failed',mcp_equals_native=equal)
    summary=dict(version='tc11-actual-consumer-live-1',acquired_at=datetime.now(timezone.utc).isoformat(),view=bound['view'],run_id=bound['run_id'],outcomes=outcomes,qualification_limit='API/CLI/actual MCP retained response parity only; no language correctness, source completeness or full unpaginated population claim.')
    write('consumer-live.json',summary)
    print(json.dumps(summary))
    return all(row.get(channel)=='passed' for row in outcomes.values() for channel in ('native','cli','mcp'))


def replay(bundle,names):
    bound=prepared_requests()
    manifest=verify_characterization_review(bundle)
    if manifest['selection']['task_id']!=bound['view']['task_id'] or manifest['selection']['content_digest']!=bound['view']['content_digest']:
        raise ValueError('detached exact closure differs from final book pin')
    outcomes={}
    for name in names:
        request=CharacterizationRequest.model_validate(bound['requests'][name])
        response=inspect_characterization_review(bundle,request).model_dump(mode='json')
        write(f'raw/consumer-detached-{name}.json',response)
        native=json.loads((HERE/f'raw/consumer-native-{name}.json').read_bytes())
        equal=canonical_bytes(response)==canonical_bytes(native)
        outcomes[name]=dict(outcome='passed' if equal else 'failed',equals_native=equal,response_digest=digest(response))
    result=dict(version='tc11-actual-detached-consumer-1',acquired_at=datetime.now(timezone.utc).isoformat(),view=bound['view'],run_id=bound['run_id'],bundle=str(bundle),manifest_digest=sha256((bundle/'manifest.json').read_bytes()).hexdigest(),closure_verification='passed',manifest_completeness=manifest['completeness'],retained_layers=len(manifest['layers']),outcomes=outcomes,qualification_limit='Existing offline verifier authenticates exact retained view/layer/source/contract closure. Its original_source_completeness label means captured native document/companions, not complete language recognition or frozen-union source assurance.')
    write('consumer-detached.json',result)
    print(json.dumps(result))
    return all(row['outcome']=='passed' for row in outcomes.values())


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['prepare','live','replay'])
    parser.add_argument('--export-max-bytes',type=int,default=134217728)
    parser.add_argument('--bundle',type=Path)
    parser.add_argument('--request-name',action='append')
    args=parser.parse_args()
    if args.action=='prepare':prepare(Settings(),args.export_max_bytes)
    elif args.action=='live':raise SystemExit(0 if live(Settings()) else 1)
    elif args.bundle is None:parser.error('replay requires exact --bundle path')
    else:raise SystemExit(0 if replay(args.bundle,args.request_name or ['summary']) else 1)
