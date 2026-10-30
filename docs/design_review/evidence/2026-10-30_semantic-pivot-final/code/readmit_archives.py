"""Re-admit exact current archives after the reviewed0034 native deployment change.

Set an explicit fresh current target in CORPUS_DATABASE__URL. This does not activate releases,
select results, reinterpret archives or access the preserved historical0030 database.
"""
from sqlalchemy import select

from corpus_structure.semantic.metadata import table
from corpus_structure.semantic.publication import admit_release
from corpus_structure.semantic.releases import verify_release
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.settings import Settings


def main() -> None:
    with (
        open_runtime_engine(Settings(), 'ci-sp09-readmit', purpose='admit') as engine,
        engine.begin() as conn,
    ):
        releases = conn.execute(select(table('ops.run').c.release_id).distinct()).scalars().all()
        for release in releases:
            admit_release(verify_release(conn, release), connection=conn)
            print(release, flush=True)


if __name__ == '__main__':
    main()
