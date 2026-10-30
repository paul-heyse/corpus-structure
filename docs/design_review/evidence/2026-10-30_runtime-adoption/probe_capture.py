"""Compare actual completed-result capture in separate resident/spooled processes."""
import argparse
import json
import resource
import time
from sqlalchemy import event
from corpus_structure.settings import Settings
from corpus_structure.semantic.runtime import open_runtime_engine
from corpus_structure.semantic.analytics import capture_packet, AnalysisScope

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mode', choices=['resident','spooled'],required=True)
args = parser.parse_args()
settings = Settings()
with open_runtime_engine(settings,'efficiency-completed-capture',purpose='read') as engine:
    active = set()
    event.listen(engine, "checkout", lambda connection, record, proxy: active.add(id(record)))
    event.listen(engine, "checkin", lambda connection, record: active.discard(id(record)))
    started = time.perf_counter()
    with capture_packet(engine,'result:production-efficiency:1',settings.database.url,mode=args.mode) as packet:
        assert not active
        assert packet.manifest is not None
        with AnalysisScope(packet) as scope:
            facts = scope.relation('fact').aggregate('count(*) as n').to_arrow_table()['n'][0].as_py()
        assert facts == packet.manifest['relations']['fact']['rows']
        result = {'mode':args.mode,'seconds':time.perf_counter()-started,'logical_digest':packet.logical_digest,'relations':{k:v['rows'] for k,v in packet.manifest['relations'].items()},'release_id':packet.binding.release_id,'data_revision':packet.binding.data_revision,'facts':facts,'snapshots_released':True,'max_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    print(json.dumps(result,indent=2))
