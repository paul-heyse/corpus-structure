"""Actual external stdio journey over caller-selected retained PDF evidence."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import shutil

from fastmcp import Client
from fastmcp.client.transports import StdioTransport


async def exercise(selection: dict, database: str, root: Path, output: Path) -> None:
    command=shutil.which('uv')
    if command is None:
        raise RuntimeError('uv is required for the actual application entry point')
    transport=StdioTransport(command=command,
        args=['run','ci','mcp','serve','--semantic-run',str(selection['run_id'])],
        cwd=str(root),keep_alive=False,
        env={'CORPUS_DATABASE__URL':database,
             'PYTHONPATH':str(root/'python/corpus-structure/src')},
        log_file=output.with_suffix('.server.log'))
    receipts=[]
    partial=output.with_suffix('.partial.json')
    if output.exists() or partial.exists():
        raise FileExistsError('retain the existing journey; select a fresh output path')
    def checkpoint():
        partial.write_text(json.dumps({'outcome':'partial','selection':selection,'calls':receipts},ensure_ascii=False,indent=2)+'\n')
    checkpoint()
    pin={key:selection[key] for key in ('run_id','task_id','product_key','content_digest')}
    async with Client(transport) as client:
        tools={tool.name:tool for tool in await client.list_tools()}
        assert {'inspect_source','render_source_region','queue_status','find'} <= tools.keys()
        receipts.append({'operation':'list_tools','tools':sorted(tools)})
        checkpoint()
        found=await client.call_tool('find',{'request':dict(run_id=selection['run_id'],text='normal distribution',limit=2)})
        assert found.structured_content and found.structured_content['rows']
        assert all(row['selection']['content_digest']==selection['content_digest'] for row in found.structured_content['rows'])
        receipts.append({'operation':'find','result':found.structured_content})
        checkpoint()
        requests=[dict(pin,version=3,view='sections',limit=5),
            dict(pin,version=3,view='formula',pointer=selection['formula_pointer']),
            dict(pin,version=3,view='cell',pointer=selection['table_pointer'],cell_index=selection['cell_index']),
            dict(pin,version=3,view='trace',pointer=selection['formula_pointer']),
            dict(pin,version=3,view='companion',pointer=selection['formula_pointer']),
            dict(pin,version=3,view='manifest',collection='coverage',limit=5)]
        for request in requests:
            response=await client.call_tool('inspect_source',{'request':request})
            value=response.structured_content
            assert value is not None
            receipts.append({'operation':'inspect_source','request':request,'result':value})
            checkpoint()
        image=await client.call_tool('render_source_region',dict(run_id=selection['run_id'],
            source_view_id=selection['source_view_id'],pointer=selection['formula_pointer'],region_index=0))
        assert any(part.type=='image' for part in image.content)
        receipts.append({'operation':'render_source_region','result':image.structured_content,
            'content_types':[part.type for part in image.content]})
        checkpoint()
        wrong=dict(pin,version=3,view='items',content_digest='0'*64)
        try:
            await client.call_tool('inspect_source',{'request':wrong})
        except Exception as error:
            assert 'digest' in str(error) or 'pin' in str(error), str(error)
            receipts.append({'operation':'wrong_digest','outcome':'refused','detail':str(error)})
            checkpoint()
        else:
            raise AssertionError('wrong native product digest was accepted')
        queue=await client.call_tool('queue_status',{})
        receipts.append({'operation':'queue_status','result':queue.structured_content})
        checkpoint()
    with output.open('x') as target:
        json.dump({'outcome':'passed','selection':selection,'calls':receipts},target,ensure_ascii=False,indent=2)
        target.write('\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--selection',type=Path,required=True)
    parser.add_argument('--database',required=True)
    parser.add_argument('--output',type=Path,required=True)
    arguments=parser.parse_args()
    asyncio.run(exercise(json.loads(arguments.selection.read_bytes()),arguments.database,
                         Path(__file__).resolve().parents[4],arguments.output))
