from pathlib import Path
from sqlalchemy.engine import make_url
import psycopg,json

pid=2806228
expected={'host':'127.0.0.1','port':57795,'system':'7711127031843004776'}
env=dict(e.split(b'=',1) for e in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in e)
url=make_url(env[b'CORPUS_DATABASE__MAINTENANCE_URL'].decode())
assert url.host==expected['host'] and url.port==expected['port']
with psycopg.connect(url.render_as_string(hide_password=False),autocommit=True) as c:
 assert c.execute('SELECT system_identifier::text FROM pg_control_system()').fetchone()[0]==expected['system']
 settings={name:c.execute('SELECT current_setting(%s)',(name,)).fetchone()[0] for name in ('pg_stat_statements.track','auto_explain.log_nested_statements','auto_explain.log_min_duration','log_parameter_max_length','log_parameter_max_length_on_error','auto_explain.log_parameter_max_length')}
 activity=c.execute("SELECT datname,usename,state,wait_event_type,wait_event,round(extract(epoch from clock_timestamp()-query_start),3),coalesce(substring(query from 'ops[.][a-z_]+'),'other') FROM pg_stat_activity WHERE datname LIKE 'cs_%' AND pid<>pg_backend_pid()").fetchall()
 print(json.dumps(dict(identity=expected,settings=settings,activity=activity),default=str))
 # The private cluster contains only this owned diagnostic selection and will be removed
 # by its managed supervisor. Enable nested execution plans for remaining work.
 for statement in ("ALTER SYSTEM SET auto_explain.log_parameter_max_length=0", "ALTER SYSTEM SET auto_explain.log_nested_statements=on", "ALTER SYSTEM SET auto_explain.log_analyze=on", "ALTER SYSTEM SET auto_explain.log_timing=off", "ALTER SYSTEM SET auto_explain.log_buffers=on", "ALTER SYSTEM SET auto_explain.log_min_duration='100ms'", "ALTER SYSTEM SET pg_stat_statements.track='all'"):
  c.execute(statement)
 c.execute('SELECT pg_reload_conf()')
