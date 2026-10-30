"""Actual default CLI stdio initialization, tool discovery and queue-status request."""
import json
import select
import subprocess
from pathlib import Path

log = Path('build/pe1012/default-mcp.stderr').open('w')
process = subprocess.Popen(['uv','run','ci','mcp','serve'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=log,text=True)
responses=[]
def request(number, method, params):
    process.stdin.write(json.dumps({'jsonrpc':'2.0','id':number,'method':method,'params':params})+'\n')
    process.stdin.flush()
    if not select.select([process.stdout],[],[],60)[0]:
        raise TimeoutError(method)
    result=json.loads(process.stdout.readline())
    assert result['id']==number and 'result' in result,result
    responses.append(result)
    return result['result']
try:
    request(1,'initialize',{'protocolVersion':'2025-06-18','capabilities':{},'clientInfo':{'name':'production-adoption','version':'1'}})
    process.stdin.write(json.dumps({'jsonrpc':'2.0','method':'notifications/initialized'})+'\n');process.stdin.flush()
    tools=request(2,'tools/list',{})
    assert 'queue_status' in {t['name'] for t in tools['tools']}
    status=request(3,'tools/call',{'name':'queue_status','arguments':{}})
    assert not status.get('isError'),status
    print(json.dumps(responses,indent=2))
finally:
    process.stdin.close()
    try: process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill();process.wait()
    log.close()
