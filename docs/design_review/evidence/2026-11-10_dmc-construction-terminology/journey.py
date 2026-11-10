"""Read-only live vocabulary inspection against the admitted development release."""
import json
import subprocess
import sys

import anyio
from fastmcp import Client
from corpus_structure.intervene.semantic_server import build_semantic_server


def cli(*args):
    result = subprocess.run(['uv','run','ci',*args,'--json'],capture_output=True,text=True,check=True)
    return json.loads(result.stdout)


async def main(release, candidate):
    args = ['--subject-kind','property','--subject','StatisticalTerminologyFields','--property','distribution_attribute']
    expected = cli('schema','inspect','--release',release,*args,'--view','detail')
    rows = [r for r in expected['entries'] if r['category']=='vocabulary_member']
    variance = next(json.loads(r['metadata_json']) for r in rows if r['name'].endswith('/variance'))
    assert variance['detail_status'] == 'available'
    assert variance['meaning'] == 'STATO:0000693'
    assert variance['detail']['definitions']
    assert any(r['path'].endswith('/permissible_values/variance') for r in variance['enum_provenance']['contributors'])
    frozen = cli('model','change','inspect-candidate',candidate,'--view','contract',*args,'--contract-view','detail')
    assert frozen == expected
    async with Client(build_semantic_server()) as client:
        result = await client.call_tool('inspect_contract',dict(release=release,subject_kind='property',subject_id='StatisticalTerminologyFields',property='distribution_attribute',view='detail'))
        assert not result.is_error and result.structured_content == expected
        for raw,valid in (('{"distribution_attribute":"variance"}',True),('{"distribution_attribute":"sample_variance"}',False)):
            answer = await client.call_tool('inspect_contract',dict(release=release,subject_kind='class',subject_id='StatisticalTerminologyFields',input_json=raw,validation_purpose='structural'))
            assert not answer.is_error
            assert bool(answer.structured_content['validation_report']['observations']) is not valid
    old = cli('schema','inspect','--release','release:4b5fd49b3879d7628e80a5feb78607b3cdc327ce223e37a5827f517f44d822f3','--subject-kind','property','--subject','Formula','--property','language','--view','detail')
    assert old['detail_status']=='available' and old['entries'][0]['required']
    print(json.dumps(dict(outcome='passed',release=release,candidate=candidate,checks=['vocabulary-definitions','enum-pv-origin','cli-mcp-capsule-parity','controlled-field-valid-invalid','compiler20-read'])))


if __name__=='__main__':
    anyio.run(main,*sys.argv[1:])
