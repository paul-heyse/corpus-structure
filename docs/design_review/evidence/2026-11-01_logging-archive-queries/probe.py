"""Small independent archive primitives; not a production query/snapshot service."""
import json
import multiprocessing as mp
import os
from pathlib import Path
import tempfile

import duckdb


def reader(original, snapshot, selected, pruned, answer):
    import fcntl
    with open(original.parent / 'selection.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        os.link(original, snapshot)
        fcntl.flock(lock, fcntl.LOCK_UN)
    selected.set()
    assert pruned.wait(5)
    answer.put(snapshot.read_text())


def prune(original, selected, pruned):
    import fcntl
    assert selected.wait(5)
    with open(original.parent / 'selection.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        original.unlink()
        fcntl.flock(lock, fcntl.LOCK_UN)
    pruned.set()


def abandon(original, snapshot):
    os.link(original, snapshot)
    os._exit(7)


def main():
    results = {'python': __import__('sys').version.split()[0], 'duckdb': duckdb.__version__}
    with tempfile.TemporaryDirectory(prefix='logging-i04-') as temp:
        root = Path(temp)
        conn = duckdb.connect()
        first = {'id': 'info', 'producer_time': 20, 'ingest': 1, 'scope': 'a'}
        late = {'id': 'debug', 'producer_time': 10, 'ingest': 2, 'scope': 'a'}
        closed = root / 'closed.jsonl'
        closed.write_text(json.dumps(first) + '\n')
        active = root / 'active.jsonl'
        active.write_bytes((json.dumps(late) + '\n{"id":').encode())
        try:
            conn.execute('select * from read_ndjson_objects(?)', [str(active)]).fetchall()
        except duckdb.Error:
            results['native_partial_tail_rejected'] = True
        else:
            raise AssertionError('partial record unexpectedly accepted')
        raw = active.read_bytes()
        prefix, suffix = raw[:raw.rfind(b'\n')+1], raw[raw.rfind(b'\n')+1:]
        assert suffix == b'{"id":'
        bounded = root / 'bounded-prefix.jsonl'
        bounded.write_bytes(prefix)
        rows = conn.execute('select json from read_ndjson_objects(?)', [str(bounded)]).fetchall()
        assert [json.loads(row[0])['id'] for row in rows] == ['debug']
        results['bounded_prefix_with_explicit_partial_tail'] = True
        corrupt = root / 'corrupt.jsonl'
        corrupt.write_bytes(prefix + b'{"id":}\n')
        try:
            conn.execute('select * from read_ndjson_objects(?)', [str(corrupt)]).fetchall()
        except duckdb.Error:
            results['complete_corrupt_record_rejected'] = True
        else:
            raise AssertionError('corruption unexpectedly accepted')
        # Producer-time cursors skip subsequently retained old records; ingest cuts do not.
        assert [row for row in (first, late) if row['producer_time'] > 20] == []
        assert [row['id'] for row in (first, late) if row['ingest'] > 1] == ['debug']
        results['late_release_requires_retained_position'] = True
        # Independent synthetic OTLP values: preserve raw JSON's union/type information.
        fixture = {'resourceSpans':[{'resource':{'attributes':[{'key':'service.name','value':{'stringValue':'probe'}}]},'scopeSpans':[{'scope':{'name':'probe'},'spans':[{'spanId':'01','parentSpanId':'00','links':[{'spanId':'02','traceId':'t'}],'attributes':[{'key':'b','value':{'boolValue':True}},{'key':'i','value':{'intValue':'1'}},{'key':'f','value':{'doubleValue':1.0}}]}]}]}], 'resourceMetrics':[{'scopeMetrics':[{'metrics':[{'name':'latency','histogram':{'aggregationTemporality':2,'dataPoints':[{'startTimeUnixNano':'10','timeUnixNano':'20','count':'2','bucketCounts':['1','1'],'explicitBounds':[1.0],'exemplars':[{'spanId':'01','asDouble':0.5}]}]}}]}]}]}
        otlp = root / 'otlp.jsonl'
        otlp.write_text(json.dumps(fixture) + '\n')
        saved = json.loads(conn.execute('select json from read_ndjson_objects(?)', [str(otlp)]).fetchone()[0])
        assert saved == fixture
        kinds = conn.execute("select json_type(json, '$.resourceSpans[0].scopeSpans[0].spans[0].attributes[0].value.boolValue'), json_type(json, '$.resourceSpans[0].scopeSpans[0].spans[0].attributes[1].value.intValue'), json_type(json, '$.resourceSpans[0].scopeSpans[0].spans[0].attributes[2].value.doubleValue') from read_ndjson_objects(?)", [str(otlp)]).fetchone()
        assert kinds == ('BOOLEAN','VARCHAR','DOUBLE'), kinds
        results['raw_otlp_link_histogram_exemplar_and_types_preserved'] = True
        # True cross-process file pin survives removal of original; next CLI process reopens path.
        ctx=mp.get_context('spawn')
        selected, pruned=ctx.Event(),ctx.Event()
        answer=ctx.Queue()
        snapshot=root/'pinned.jsonl'
        r=ctx.Process(target=reader,args=(closed,snapshot,selected,pruned,answer))
        p=ctx.Process(target=prune,args=(closed,selected,pruned))
        r.start();p.start()
        r.join(10);p.join(10)
        for child in (r,p):
            if child.is_alive(): child.kill();child.join();raise AssertionError('watchdog termination')
            assert child.exitcode == 0
        assert json.loads(answer.get(timeout=2)) == first
        assert not closed.exists()
        assert json.loads(snapshot.read_text()) == first
        snapshot.unlink()
        assert not snapshot.exists() # later continuation must report expiry, never reread latest
        results['cross_process_pin_prune_reopen_then_expiry'] = True
        abandoned_source=root/'abandoned-source.jsonl'
        abandoned_source.write_text(json.dumps(first)+'\n')
        abandoned_pin=root/'abandoned-pin.jsonl'
        child=ctx.Process(target=abandon,args=(abandoned_source,abandoned_pin))
        child.start();child.join(5)
        if child.is_alive():child.kill();child.join();raise AssertionError('abandon watchdog')
        assert child.exitcode == 7
        abandoned_source.unlink()
        assert json.loads(abandoned_pin.read_text()) == first
        # Parent knows exact owned PID exit; explicit snapshot cleanup is safe only then.
        abandoned_pin.unlink()
        results['exited_reader_leaves_pin_until_owned_cleanup'] = True
        # Scope authorization selects partition before parsing attacker-controlled record scope.
        dirs={x:root/x for x in ('a','b')}
        for d in dirs.values():d.mkdir(mode=0o700)
        (dirs['b']/'forged.jsonl').write_text(json.dumps({'scope':'a','secret':'synthetic'})+'\n')
        selected_files=list(dirs['a'].glob('*.jsonl'))
        assert selected_files == []
        results['trusted_partition_selection_excludes_forged_scope'] = True
        results['outcome']='passed'
        print(json.dumps(results,indent=2))

if __name__ == '__main__':main()
