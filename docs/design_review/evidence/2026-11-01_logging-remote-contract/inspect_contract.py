"""Exact installed-source and local transport qualification; no remote backend requests."""
import ast
import inspect
import json
import os
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx
from logfire import query_client

ROOT = Path(__file__).parent
source = Path(inspect.getfile(query_client)).read_text()
(ROOT / 'raw/query_client.py.txt').write_text(source)
methods = {}
for node in ast.walk(ast.parse(source)):
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {'__init__', 'query_json_rows', 'query_arrow', 'query_csv', 'info', '_query_v2'}:
        methods.setdefault(node.name, []).append({'line': node.lineno, 'arguments': ast.unparse(node.args)})
requests = []
def handler(request):
    requests.append({'path': request.url.path, 'body': json.loads(request.content) if request.content else None})
    if request.url.path == '/v1/read-token-info':
        return httpx.Response(200, json={'project_name': 'synthetic', 'organization_name': 'synthetic'})
    body = json.loads(request.content)
    if body['sql'] == 'rate':
        return httpx.Response(429, headers={'retry-after': '2'}, text='synthetic rate limit')
    return httpx.Response(200, json={'schema': {'fields': [{'name': 'trace_id', 'data_type': 'Utf8', 'nullable': False}]}, 'data': [{'trace_id': 'synthetic-trace'}]})
with query_client.LogfireQueryClient(read_token='synthetic-token', base_url='https://synthetic.invalid', transport=httpx.MockTransport(handler), timeout=httpx.Timeout(1)) as client:
    assert client.info()['project_name'] == 'synthetic'
    result = client.query_json_rows('select trace_id from records', min_timestamp=datetime(2026, 11, 1, tzinfo=UTC), max_timestamp=datetime(2026, 11, 2, tzinfo=UTC), limit=1)
    assert result['rows'] == [{'trace_id': 'synthetic-trace'}]
    assert result['columns'][0]['datatype'] == 'Utf8'
    try:
        client.query_json_rows('rate', min_timestamp=datetime(2026, 11, 1, tzinfo=UTC))
    except query_client.QueryRateLimitedError as error:
        assert error.retry_after == 2
    else:
        raise AssertionError('429 not classified')
    try:
        client.query_json_rows('select 1')
    except TypeError:
        pass
    else:
        raise AssertionError('missing time window accepted')
assert len(requests) == 3, 'unexpected retry or backend request'
report = {'versions': {n: version(n) for n in ('logfire', 'logfire-sdk', 'httpx')}, 'python': sys.version, 'methods': methods, 'local_requests': requests,
    'credential_presence_only': {k: bool(os.environ.get(k)) for k in ('LOGFIRE_TOKEN', 'LOGFIRE_READ_TOKEN', 'LOGFIRE_BASE_URL', 'OTEL_EXPORTER_OTLP_ENDPOINT')},
    'live_read': 'blocked: no authorized endpoint, read token and known test scope supplied',
    'local_transport': 'passed: time window, v2 body, row mapping, 429 retry-after, no automatic retries',
    'remote_requests': 'not_run; MockTransport only; CSV/Arrow and live auth/retention/ingestion remain untested'}
(ROOT / 'raw/contract.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'local_transport': report['local_transport'], 'live_read': report['live_read']}))
