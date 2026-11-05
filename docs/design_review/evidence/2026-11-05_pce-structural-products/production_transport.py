"""Actual CLI/fresh external MCP and detached structural review, with no model calls."""
from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

HERE=Path(__file__).resolve().parent
RAW=HERE/'raw'
RUN=47


def cli(args,name):
    result=subprocess.run(['uv','run','ci',*args],capture_output=True,text=True)
    with (RAW/(name+'.stdout')).open('x') as out:out.write(result.stdout)
    with (RAW/(name+'.stderr')).open('x') as out:out.write(result.stderr)
    result.check_returncode()
    return json.loads(result.stdout)


async def main():
    expected=cli(['structure','list','--run',str(RUN),'--json'],'production-transport-005-cli')
    assert expected['task_ids']==[137,138,139,140]
    assert len(expected['reports'])==4
    assert expected['standing']=='private_proposals'
    async with Client(StdioTransport(command='uv',args=['run','ci','mcp','serve','--semantic-run',str(RUN)])) as client:
        result=await client.call_tool('structural_products',{'request':{'run_id':RUN}})
        assert not result.is_error and result.structured_content is not None
        actual=result.structured_content
        assert actual==expected
        first=await client.call_tool('structural_products',{'request':{'run_id':RUN,'limit':1}})
        assert first.structured_content is not None
        assert first.structured_content['next_after_task_id']==137
        wrong=await client.call_tool('structural_products',{'request':{'run_id':RUN,'cut_id':58}},raise_on_error=False)
        assert wrong.is_error
    selection=RAW/'production-review-selection-005.json'
    with selection.open('x') as out:json.dump({'structural_selections':[{'run_id':RUN}]},out)
    destination=RAW/'production-review-bundle-005'
    manifest=cli(['review','export',str(selection),str(destination),'--json'],'production-transport-005-export')
    verified=cli(['review','verify',str(destination),'--json'],'production-transport-005-offline-verify')
    inspected=cli(['review','inspect',str(destination),'--json'],'production-transport-005-offline-inspect')
    report={'outcome':'passed','run_id':RUN,'cut_id':59,'actual_cli':True,'fresh_external_mcp':True,'same_page':True,'paging':True,'wrong_cut_refusal':True,'manifest':manifest,'offline_verification':verified,'offline_inspection':inspected,'source_or_model_execution':False,'protected_labels_read':False,'public_admission':'not_run','defaults_activated':False}
    with (RAW/'production-transport-005.json').open('x') as out:json.dump(report,out,indent=2)
    print(json.dumps(report),flush=True)


if __name__=='__main__':asyncio.run(main())
