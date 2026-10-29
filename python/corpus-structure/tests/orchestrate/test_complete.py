"""The production complete-mode driver seals real proposal work without an agent."""
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import text

from corpus_structure.core.method import MethodSettings
from corpus_structure.orchestrate import phase0, project
from corpus_structure.orchestrate.testing import run_to_completion

REPO = Path(__file__).resolve().parents[4]


def test_production_complete_driver_records_scope_and_pending_fates(committing_db: Any, tmp_path: Path):
    # A continue action that repeats the same configuration must not create duplicate work.
    pack = tmp_path / 'domains/statistics'
    shutil.copytree(REPO / 'domains/statistics', pack)
    (pack / 'policies.yaml').write_text("""version: 'test'
chains:
  propose:
    - key: first
      when: unit.claim_bearing and ran('ingest.html')
      do: {method: agent.opus/extract, then: continue}
    - key: repeat
      when: unit.claim_bearing and ran('ingest.html')
      do: {method: agent.opus/extract, then: stop}
""")
    registry = phase0.registry(pack)
    with committing_db.begin() as conn:
        project.init_project(conn, domain='statistics', name='driver',
            corpus=REPO / 'fixtures/trace/corpus', registry=registry, domains=pack.parent)
    url = committing_db.url.set(drivername='postgresql').render_as_string(hide_password=False)
    first = run_to_completion(committing_db, url=url, project_name='driver', slice='trace',
        method_settings=MethodSettings(data_dir=tmp_path,model_cache=tmp_path), domains=pack.parent)
    assert first.status == 'finished'
    with committing_db.connect() as conn:
        pending = conn.execute(text("SELECT unit_key FROM ops.task WHERE run_id=:r AND stage='propose' AND status='awaiting_agent' ORDER BY unit_key"),{'r':first.run_id}).scalars().all()
        assert len(pending) == 5
        assert conn.execute(text("SELECT count(*) FROM ops.task WHERE run_id=:r AND stage='propose' AND reason='scope'"),{'r':first.run_id}).scalar_one() > 0
        options, cut = conn.execute(text('SELECT options,cut_at FROM ops.run WHERE id=:r'),{'r':first.run_id}).one()
        assert options['scope']['name'] == 'trace'
        assert len(options['scope']['locators']) == 5
        assert cut is not None
        metrics = conn.execute(text("SELECT trigger_metrics FROM ops.task WHERE run_id=:r AND stage='propose' LIMIT 1"), {'r':first.run_id}).scalar_one()
        assert metrics['values']['phase'] == 0
        assert metrics['values']['unit.claim_bearing'] is True
