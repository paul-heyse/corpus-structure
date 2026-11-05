"""Compile current PL/pgSQL in the operator working database, rollback all definitions."""
import json
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from corpus_structure.settings import Settings

if __name__=='__main__':
    engine=create_engine(make_url(Settings().database.sqlalchemy_url).set(username='paul'))
    source=Path('python/corpus-structure/src/corpus_structure/semantic/sql/source_contributions.sql')
    with engine.connect() as conn:
        transaction=conn.begin()
        try:
            conn.exec_driver_sql(source.read_text())
            print(json.dumps({'outcome':'passed','scope':'PL/pgSQL CREATE compilation only; rolled back; execution guards separately tested'}))
        finally:
            transaction.rollback()
    engine.dispose()
