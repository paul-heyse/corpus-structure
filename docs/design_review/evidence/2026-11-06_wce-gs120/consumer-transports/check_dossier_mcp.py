"""Fresh external MCP bounded dossier pages, exact CLI parity and custody refusals."""
import argparse
import json
import sys
from pathlib import Path
import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport
from corpus_structure.semantic.identity import canonical_bytes

HERE=Path(__file__).resolve().parent

def retain(path,value):
 with path.open('xb') as stream:stream.write(canonical_bytes(value)+b'\n')

async def main(args):
 out=HERE/args.attempt;out.mkdir(exist_ok=False)
 transport=StdioTransport(command=str(Path(sys.executable).with_name('ci')),args=['mcp','serve','--semantic-run',str(args.run)],cwd=str(HERE.parents[4]),log_file=out/'server.log')
 request=dict(run_id=args.run,task_id=args.task,cut_id=args.cut,limit=3,max_bytes=1_000_000)
 try:
  async with Client(transport,timeout=180) as client:
   inventory=await client.list_tools();retain(out/'tools.json',[t.model_dump(mode='json') for t in inventory]);assert 'dossier_representation' in {t.name for t in inventory}
   pages=[];cursor=None;seen=[]
   while True:
    selected={**request,**({'continuation':cursor} if cursor else {})}
    result=await client.call_tool('dossier_representation',{'request':selected},raise_on_error=False)
    if result.is_error or not isinstance(result.structured_content,dict):raise ValueError('actual dossier MCP delivery failed: '+str(result))
    page=result.structured_content;retain(out/f'page-{len(pages)+1:03}.json',page)
    if not pages and canonical_bytes(page)!=canonical_bytes(json.loads(args.cli.read_bytes())):raise ValueError('CLI/MCP first bounded page differs')
    assert page['run_id']==args.run and page['task_id']==args.task and page['cut_id']==args.cut
    assert len(page['members'])<=3 and len(canonical_bytes(page))<=request['max_bytes']
    seen.extend(m['member_id'] for m in page['members']);pages.append(page)
    cursor=page.get('continuation')
    if cursor is None:break
    if len(pages)>100:raise ValueError('unexpected continuation loop')
   assert len(seen)==len(set(seen)) and len({(p['product_id'],p['membership_digest'],p['facet_digest'],p['full_member_count']) for p in pages})==1
   controls={}
   first=pages[0]
   if first.get('continuation'):
    forged={**first['continuation'],'membership_digest':'0'*64}
    controls['substituted_membership']=('dossier_representation',{'request':{**request,'continuation':forged}})
   controls['foreign_cut']=('dossier_representation',{'request':{**request,'cut_id':args.cut+1}})
   controls['interactive_limit']=('dossier_representation',{'request':{**request,'max_bytes':8_000_001}})
   controls['oversized_full_report']=('structural_products',{'request':dict(run_id=args.run,cut_id=args.cut,kind='dossier',max_bytes=8_000_000)})
   refusals=[]
   for name,(tool,body) in controls.items():
    result=await client.call_tool(tool,body,raise_on_error=False)
    if not result.is_error:raise ValueError('expected exact native/transport refusal: '+name)
    refusal=dict(name=name,is_error=result.is_error,content=[c.model_dump(mode='json') for c in result.content]);retain(out/(name+'.json'),refusal);refusals.append(name)
   retain(out/'result.json',dict(outcome='passed',run_id=args.run,cut_id=args.cut,task_id=args.task,fresh_stdio_handshake=True,cli_exact_parity=True,pages=len(pages),selected_members=len(seen),full_member_count=first['full_member_count'],membership_digest=first['membership_digest'],facet_digest=first['facet_digest'],refusals=refusals,scope='Actual bounded representative delivery and refusal identity; full membership retained in separately budgeted files, source semantic correctness not inferred'))
 except BaseException as error:
  retain(out/'failure.json',dict(outcome='failed',type=type(error).__name__,message=str(error)));raise

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('attempt');p.add_argument('--run',type=int,required=True);p.add_argument('--task',type=int,required=True);p.add_argument('--cut',type=int,required=True);p.add_argument('--cli',type=Path,required=True);anyio.run(main,p.parse_args())
