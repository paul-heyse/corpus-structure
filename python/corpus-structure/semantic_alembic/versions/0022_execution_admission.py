"""Fence composed-model instances until their required native enforcement is deployed."""

from alembic import op

revision = "semantic_0022"
down_revision = "semantic_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
    CREATE FUNCTION data.guard_execution_admission() RETURNS trigger
    LANGUAGE plpgsql SET search_path=pg_catalog,pg_temp AS $fn$
    BEGIN
      IF EXISTS (SELECT 1 FROM sem.release WHERE release_id=NEW.release_id
                 AND profile='semantic-2') THEN
        RAISE EXCEPTION 'required native execution enforcement is unavailable'
          USING ERRCODE='23514';
      END IF;
      RETURN NEW;
    END $fn$;
    REVOKE ALL ON FUNCTION data.guard_execution_admission() FROM PUBLIC;
    CREATE TRIGGER guard_execution_admission BEFORE INSERT OR UPDATE OF release_id
      ON data.realization FOR EACH ROW EXECUTE FUNCTION data.guard_execution_admission();
    """)


def downgrade() -> None:
    raise RuntimeError("execution admission downgrade refused; rebuild an owned database")
