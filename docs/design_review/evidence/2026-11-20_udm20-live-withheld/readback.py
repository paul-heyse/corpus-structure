"""Read native completion and held-claim standing independently of the driver."""
import json
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from corpus_structure.semantic.data_operation_storage import DataOperationStorage

folder = Path(__file__).resolve().parent
registered = json.loads((folder / 'raw/registered.json').read_text())
withheld = json.loads((folder / 'raw/withheld.json').read_text())
engine = create_engine(URL.create('postgresql+psycopg', username='paul', database='corpus_structure_ddo_stage', query={'host':'/var/run/postgresql','port':'5434'}))
try:
    with engine.connect() as connection:
        project = dict(connection.execute(text('SELECT project_id, active_release_id, generation FROM data.project WHERE project_id=:project'), {'project':'udm20-live-withheld-region-v2'}).mappings().one())
        held = dict(connection.execute(text('SELECT id,status,attempt,lease_until FROM ops.task WHERE id=:task'), {'task':withheld['held']['task_id']}).mappings().one())
        native = DataOperationStorage(connection).read_demand_result({'demand_id': registered['demand'], 'limit':100})
    assert project['generation'] == 0 and project['active_release_id'] is None
    assert held['lease_until'] is None and held['status'] == 'done' and held['attempt']==2
    assert len(native['obligations'])==18 and {row['fate'] for row in native['obligations']}=={'fulfilled'}
    result={'project':project,'held':held,'fates':[(row['operation_id'],row['fate']) for row in native['obligations']]}
    (folder/'raw/independent-readback.json').write_text(json.dumps(result,indent=2,default=str)+'\n')
    print(json.dumps(result,default=str))
finally:
    engine.dispose()
