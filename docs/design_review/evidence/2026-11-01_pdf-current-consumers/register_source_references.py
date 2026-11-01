"""Register retained independent source-only authors through evaluator-owned operations.

Run only after the exact source-bound extraction is completed. This script never
changes the six expected source facts or reads prediction content to author a pass.
"""
from __future__ import annotations

import argparse
import json
from hashlib import sha256
from pathlib import Path

from corpus_structure.evaluate.semantic import (
    agreement,
    create_reference_set,
    record_pass,
    split_documents,
)
from corpus_structure.semantic.proposals import native_frame_from_dict
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('retain the previous registration receipt')
    directory = args.input
    manifest = json.loads((directory / 'manifest.json').read_bytes())
    for name, digest in manifest['input_digests'].items():
        if sha256((directory / name).read_bytes()).hexdigest() != digest:
            raise ValueError('prepared independent reference input changed: ' + name)
    sources = json.loads((directory / 'sources.json').read_bytes())
    for kind in ('A', 'B', 'C'):
        validation = json.loads((directory / f'{kind}.validation.json').read_bytes())
        if validation['outcome'] != 'passed':
            raise ValueError('every independent pass requires successful rich/citation admission')
    frames = {key: native_frame_from_dict(source['frame']) for key, source in sources.items()}
    with open_runtime_engine(Settings(), 'ci-independent-pdf-reference-registration', purpose='evaluate') as engine:
        with engine.begin() as conn:
            split = split_documents(conn, manifest['project_id'], release_id=manifest['release_id'])
            created = create_reference_set(
                conn, project_id=manifest['project_id'], source_run_id=manifest['run_id'],
                label=f"pdf-source-independent-{manifest['run_id']}", split='dev',
                size=len(frames), forced=tuple(frame.unit_ref for frame in frames.values()),
            )
            passes = []
            agreements = {}
            for key, frame in frames.items():
                unit = created['units'][frame.unit_ref]
                for kind in ('A', 'B', 'C'):
                    invocation = json.loads((directory / f'{kind}.invocation.json').read_bytes())
                    identity = record_pass(
                        conn, unit_id=unit, pass_kind=kind,
                        actor=f"claude-cli:{invocation['model']}:{invocation['session_id']}:{kind}",
                        authored=(directory / f'{kind}.{key}.authored.json').read_bytes(), frame=frame,
                    )
                    passes.append(dict(source_case=key, unit_id=unit, pass_kind=kind, pass_id=identity))
                agreements[key] = agreement(conn, unit)
    report = dict(outcome='passed', scope=manifest['scope'], run_id=manifest['run_id'],
                  project_id=manifest['project_id'], set_id=created['set_id'],
                  split=split, passes=passes, independent_author_agreement=agreements)
    with args.output.open('x') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, default=str)
        stream.write('\n')
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))


if __name__ == '__main__':
    main()
