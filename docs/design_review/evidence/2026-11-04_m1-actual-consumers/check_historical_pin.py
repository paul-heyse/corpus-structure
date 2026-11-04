"""Re-read a retained run after a later result publishes, without moving defaults."""

import json
import subprocess

from run_consumers import HERE, REPO, dump

output = HERE / 'raw' / 'historical-11-after-14-001'
output.mkdir(exist_ok=False)
command = ['uv', 'run', 'ci', 'records', 'list', '--run', '11', '--limit', '2', '--json']
result = subprocess.run(command, cwd=REPO, capture_output=True, text=True)
dump(output / 'command.json', dict(command=command, exit_code=result.returncode))
(output / 'stdout.json').write_text(result.stdout)
(output / 'stderr.txt').write_text(result.stderr)
baseline = json.loads((HERE / 'raw/source-only-11-001/query-page.json').read_bytes())
actual = json.loads(result.stdout) if result.returncode == 0 else None
dump(output / 'summary.json', dict(
    outcome='passed' if actual == baseline else 'failed',
    prior_run=11, prior_cut=7, later_published_run=14, later_published_cut=13,
    complete_page_equal=actual == baseline,
    scope='retained nondefault historical result after later publication; no project/global selected-result change',
))
print(json.dumps(dict(exit_code=result.returncode, complete_page_equal=actual == baseline)))
