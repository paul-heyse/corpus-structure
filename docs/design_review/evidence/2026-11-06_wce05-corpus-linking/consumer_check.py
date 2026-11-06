"""Actual fresh CLI subprocess and stdio MCP reads of retained WCE results.

Read-only tools only; no provider, producer, evaluator or publication operation runs.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

import anyio
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.serve.contributions import ContributionRequest
from corpus_structure.serve.structural_products import StructuralRequest
from corpus_structure.settings import Settings


def save(output, name, value):
    (output / name).write_bytes(canonical_bytes(value) + b'\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('attempt')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    output = Path(__file__).resolve().parent / args.attempt
    output.mkdir(exist_ok=False)
    command = str(Path(sys.executable).with_name('ci'))
    settings = Settings()
    database = settings.database
    env = {key: value for key, value in os.environ.items() if key.startswith('CORPUS_') or key in ('PATH', 'PYTHONPATH')}
    env.update(CORPUS_DATABASE__URL=database.url,
        CORPUS_DATABASE__MAINTENANCE_URL=database.maintenance_url,
        CORPUS_DATABASE__READER_URL=database.reader_url or '',
        CORPUS_DATABASE__EVALUATOR_URL=database.evaluator_url or '',
        CORPUS_DATABASE__ADMISSION_URL=database.admission_url or '')
    cases = (
        ('component', StructuralRequest(run_id=121, kind='definition_components', include_publication=True, include_support=True),
            ['structure', 'list', '--run', '121', '--kind', 'definition_components', '--include-publication', '--include-support', '--json'], 'structural_products'),
        ('relationship', ContributionRequest(run_id=127, method='retrieve.contextual', include_details=True, include_interpretation=True),
            ['contributions', 'list', '--run', '127', '--method', 'retrieve.contextual', '--include-details', '--include-interpretation', '--json'], 'contributions'),
        ('applicability', StructuralRequest(run_id=130, kind='definition_applicability'),
            ['structure', 'list', '--run', '130', '--kind', 'definition_applicability', '--json'], 'structural_products'),
    )
    manifests = []
    cli_values = {}
    try:
        for name, request, argv, tool in cases:
            record = dict(case=name, command=[command, *argv], cwd=str(root), request=request.model_dump(mode='json'), tool=tool)
            manifests.append(record)
            save(output, 'commands.json', manifests)
            with subprocess.Popen([command, *argv], cwd=root, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
                stdout, stderr = process.communicate(timeout=120)
                record.update(pid=process.pid, exit_code=process.returncode)
            (output / (name + '-cli-stdout.json')).write_bytes(stdout)
            (output / (name + '-cli-stderr.log')).write_bytes(stderr)
            save(output, 'commands.json', manifests)
            if record['exit_code'] != 0:
                raise RuntimeError(name + ' CLI subprocess failed')
            cli_values[name] = json.loads(stdout)
        assert cli_values['component']['reports'][0]['definition_components']['components'][0]['term']['text'] == 'The normal density function'
        assert cli_values['component']['public_assertions']
        assert 'defined-by' in json.dumps(cli_values['relationship'])
        assert cli_values['applicability']['reports'][0]['definition']['readings'][0]['outcome'] == 'applicable_definition'

        async def mcp_journey():
            for name, request, _, tool in cases:
                argv = ['mcp', 'serve', '--semantic-run', str(request.run_id)]
                save(output, name + '-mcp-command.json', dict(command=[command, *argv], cwd=str(root), keep_alive=False, request=request.model_dump(mode='json'), tool=tool))
                transport = StdioTransport(command=command, args=argv, env=env, cwd=str(root), keep_alive=False, log_file=output / (name + '-mcp-stderr.log'))
                async with Client(transport) as client:
                    tools = await client.list_tools()
                    save(output, name + '-mcp-tools.json', [item.model_dump(mode='json') for item in tools])
                    assert tool in {item.name for item in tools}
                    response = await client.call_tool(tool, {'request': request.model_dump(mode='json')})
                    save(output, name + '-mcp-response.json', dict(content=[item.model_dump(mode='json') for item in response.content], structured_content=response.structured_content, meta=response.meta, is_error=response.is_error))
                    assert not response.is_error
                    actual = dict(response.structured_content)
                    expected = dict(cli_values[name])
                    captures = {}
                    if 'binding' in expected and 'capture_id' in expected['binding']:
                        actual['binding'] = dict(actual['binding'])
                        expected['binding'] = dict(expected['binding'])
                        captures = dict(cli=expected['binding'].pop('capture_id'), mcp=actual['binding'].pop('capture_id'))
                        assert UUID(captures['cli']) != UUID(captures['mcp'])
                    assert actual == expected
                    save(output, name + '-parity.json', dict(outcome='passed', excluded_fields=['binding.capture_id'] if captures else [], independent_read_capture_ids=captures, comparison='all remaining binding, content and standing fields exact'))
        anyio.run(mcp_journey)
        save(output, 'result.json', dict(outcome='passed', scope='fresh CLI subprocess and actual stdio MCP source-bound reads',
            runs=[121, 127, 130], cli_mcp_structured_parity='exact apart from independent binding.capture_id; raw IDs retained', component_public_assertions=len(cli_values['component']['public_assertions']),
            provider_execution='not_run: retained results only', protected_cohort_capture='not_run', scientific_truth='not_established'))
    except BaseException as error:
        save(output, 'failure.json', dict(outcome='failed', error_type=type(error).__name__, reason=str(error)))
        raise


if __name__ == '__main__':
    main()
