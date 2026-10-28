#!/usr/bin/env bash
# Provision the dedicated PostgreSQL 18 cluster 18/corpus (D3 §13). Idempotent; needs sudo.
#
# Creates the cluster with postgresql-common (port 5434, socket only), installs
# ops/postgresql/corpus.conf into its conf.d, restarts it when that file changed, and ensures the
# operator's login role (LOGIN, CREATEDB), the read-only role corpus_ro, the database `corpus` and
# the template cs_template with pg_textsearch, vector and pg_stat_statements. Never touches any
# other cluster. No backups or archiving yet (D3 §13).
#
# Usage: pg_provision.sh [status]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VER=18
NAME=corpus
PORT=5434
CONF_SRC="$ROOT/ops/postgresql/corpus.conf"
CONF_DST="/etc/postgresql/$VER/$NAME/conf.d/corpus.conf"
OWNER=${CORPUS_DB_OWNER:-$(id -un)}
TEMPLATE=cs_template

psql_pg() { sudo -u postgres psql -p "$PORT" -X -q -v ON_ERROR_STOP=1 -tA "$@"; }

exists() { pg_lsclusters -h | awk -v v="$VER" -v n="$NAME" '$1==v && $2==n {found=1} END {exit !found}'; }

status() {
  pg_lsclusters "$VER" "$NAME" 2>/dev/null || { echo "18/$NAME: not created (run just db-provision)"; return 1; }
  psql "postgresql:///corpus?host=/var/run/postgresql&port=$PORT" -X -tA \
    -c "select 'version ' || current_setting('server_version')" \
    -c "select 'template ' || string_agg(extname || ' ' || extversion, ', ' order by extname) from pg_extension" 2>/dev/null \
    || echo "18/$NAME: not reachable as $(id -un) (run just db-up / just db-provision)"
  echo "preload $(sudo -u postgres psql -p "$PORT" -X -tA -c 'show shared_preload_libraries' 2>/dev/null)"
  echo "checksums $(sudo -u postgres psql -p "$PORT" -X -tA -c 'show data_checksums' 2>/dev/null)"
}

provision() {
  if ! exists; then
    echo "pg_provision: creating cluster $VER/$NAME on port $PORT"
    sudo pg_createcluster "$VER" "$NAME" --port "$PORT" --start-conf auto --locale C.UTF-8 --encoding UTF8
  fi
  local restart=0
  if ! sudo cmp -s "$CONF_SRC" "$CONF_DST" 2>/dev/null; then
    echo "pg_provision: installing $CONF_DST"
    sudo install -o postgres -g postgres -m 644 "$CONF_SRC" "$CONF_DST"
    restart=1
  fi
  if ! pg_lsclusters -h "$VER" "$NAME" | grep -q online; then
    sudo pg_ctlcluster "$VER" "$NAME" start
  elif [ "$restart" = 1 ]; then
    echo "pg_provision: restarting $VER/$NAME for the new configuration"
    sudo pg_ctlcluster "$VER" "$NAME" restart
  fi

  psql_pg -d postgres <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$OWNER') THEN
    CREATE ROLE "$OWNER" LOGIN CREATEDB;
  ELSE
    ALTER ROLE "$OWNER" LOGIN CREATEDB;
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'corpus_ro') THEN
    CREATE ROLE corpus_ro NOLOGIN;
  END IF;
END \$\$;
GRANT pg_read_all_data TO corpus_ro;
GRANT corpus_ro TO "$OWNER";
SQL
  if [ -z "$(psql_pg -d postgres -c "SELECT 1 FROM pg_database WHERE datname = 'corpus'")" ]; then
    psql_pg -d postgres -c "CREATE DATABASE corpus OWNER \"$OWNER\""
  fi
  if [ -z "$(psql_pg -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$TEMPLATE'")" ]; then
    psql_pg -d postgres -c "CREATE DATABASE $TEMPLATE OWNER \"$OWNER\""
  fi
  for db in corpus "$TEMPLATE"; do
    psql_pg -d "$db" -c "SET client_min_messages = warning" \
      -c "CREATE EXTENSION IF NOT EXISTS pg_textsearch" \
      -c "CREATE EXTENSION IF NOT EXISTS vector" \
      -c "CREATE EXTENSION IF NOT EXISTS pg_stat_statements"
  done
  psql_pg -d postgres -c "ALTER DATABASE $TEMPLATE IS_TEMPLATE true"
  status
}

case "${1:-provision}" in
  provision) provision ;;
  status) status ;;
  *) echo "usage: pg_provision.sh [provision|status]" >&2; exit 2 ;;
esac
