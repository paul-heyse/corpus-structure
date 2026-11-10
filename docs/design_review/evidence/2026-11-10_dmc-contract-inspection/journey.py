"""Actual development reader/CLI/MCP journey; no write-side acquisition."""
from __future__ import annotations
import json
import subprocess
import sys
from pathlib import Path

import anyio
from fastmcp import Client
from corpus_structure.intervene.semantic_server import build_semantic_server


def cli(*args):
    result = subprocess.run(['uv', 'run', 'ci', *args, '--json'], capture_output=True, text=True, check=True)
    return json.loads(result.stdout)


async def main(release, candidate):
    request = dict(release=release, subject_kind='property', subject_id='Formula', property='language', view='detail')
    expected = cli('schema', 'inspect', '--release', release, '--subject-kind', 'property', '--subject', 'Formula', '--property', 'language', '--view', 'detail')
    assert expected['detail_status'] == 'available'
    language = next(e for e in expected['entries'] if e['category'] == 'property')
    assert language['required'] and any(c['path'] == 'classes/MathematicalExpression/attributes/language' for c in language['contributors'])
    frozen = cli('model', 'change', 'inspect-candidate', candidate, '--view', 'contract', '--subject-kind', 'property', '--subject', 'Formula', '--property', 'language', '--contract-view', 'detail')
    assert frozen == expected
    async with Client(build_semantic_server()) as client:
        tools = {t.name: t for t in await client.list_tools()}
        assert tools['inspect_contract'].annotations.read_only_hint
        answer = await client.call_tool('inspect_contract', request)
        assert not answer.is_error and answer.structured_content == expected
        good = json.dumps(dict(kind='formula', language='latex', expression='x'))
        bad = json.dumps(dict(kind='formula', expression='x'))
        for content, valid in ((good, True), (bad, False)):
            response = await client.call_tool('inspect_contract', dict(release=release, subject_kind='class', subject_id='Formula', view='detail', input_json=content, validation_purpose='structural'))
            assert not response.is_error
            value = response.structured_content
            assert bool(value['validation_report']['observations']) is not valid
            assert value['skeleton_json'] == '{}'
        operation = await client.call_tool('inspect_contract', dict(release=release, subject_kind='operation', subject_id='archive'))
        assert not operation.is_error and operation.structured_content['operation_explanation']['operation'] == 'archive'
    print(json.dumps(dict(outcome='passed', release=release, candidate=candidate,
        checks=['inherited-origin','frozen-candidate','cli-mcp-parity','valid-invalid-input','finite-skeleton','operation-explanation'])))


if __name__ == '__main__':
    anyio.run(main, *sys.argv[1:])
