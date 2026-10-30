"""Exercise actual CLI consumers for an explicit completed run; never changes selection."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--run', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    base = ['uv', 'run', '--project', 'python/corpus-structure', 'ci']
    bound = ['--project', args.project, '--run', args.run, '--json']
    receipts = []

    def invoke(name: str, command: list[str]) -> dict:
        result = subprocess.run(base + command, text=True, capture_output=True, check=False)
        (args.out / f'{name}.json').write_text(result.stdout)
        (args.out / f'{name}.stderr').write_text(result.stderr)
        receipts.append({'command': base + command, 'returncode': result.returncode})
        (args.out / 'commands.json').write_text(json.dumps(receipts, indent=2))
        if result.returncode:
            raise RuntimeError(f'{name} failed; see retained receipts')
        return json.loads(result.stdout)

    claims = invoke('claims', ['query', 'claims', *bound])
    if not claims['rows']:
        raise RuntimeError('no claim available to exercise explanation')
    invoke('explain', ['explain', 'claim', claims['rows'][0]['fact']['fact_id'], *bound])
    for encoding in ('jsonl', 'parquet'):
        invoke(encoding, ['export', '--format', encoding, '--out', str(args.out / encoding), *bound])


if __name__ == '__main__':
    main()
