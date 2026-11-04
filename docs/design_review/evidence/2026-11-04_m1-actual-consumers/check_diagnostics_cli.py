"""Retain the actual explicit-diagnostics CLI refusal on the completed CPU run."""

import json
import subprocess

from run_consumers import HERE, REPO, dump

output = HERE / 'raw' / 'diagnostics-cli-14-001'
output.mkdir(exist_ok=False)
command = ['uv', 'run', 'ci', 'records', 'list', '--run', '14', '--include-diagnostics', '--json']
result = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
dump(output / 'command.json', dict(command=command, exit_code=result.returncode))
(output / 'stdout.json').write_text(result.stdout)
(output / 'stderr.txt').write_text(result.stderr)
response = json.loads(result.stdout) if result.stdout else {}
dump(output / 'summary.json', dict(
    outcome='passed' if result.returncode != 0 and 'byte budget' in json.dumps(response) else 'failed',
    observed_exit_code=result.returncode,
    scope='explicit full diagnostics refusal at default interactive response budget; ordinary diagnostics omission tested separately',
    response=response,
))
print(json.dumps(dict(exit_code=result.returncode, response=response)))
