"""Prepare the post148 current release without changing project defaults."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
from corpus_structure.semantic.regeneration import prepare_packs
from corpus_structure.semantic.releases import persist_release
from corpus_structure.semantic.identity import canonical_bytes
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--attempt',default='001');args=parser.parse_args()
    bundle,deps,profile,prepared=prepare_packs((Path('domains/statistics'),))
    with open_runtime_engine(Settings(),'automatic-definition-release',purpose='admit') as engine,engine.begin() as conn:
        persist_release(conn,bundle,deps,profile,prepared)
    output=dict(outcome='passed',release_id=prepared.release_id,scope='post148 release preparation/persistence only; no provider/native task qualification')
    target=Path(__file__).parent/f'raw/automatic-release-{args.attempt}.json'
    with target.open('xb') as out:out.write(canonical_bytes(output)+b'\n')
    print(json.dumps(output))
