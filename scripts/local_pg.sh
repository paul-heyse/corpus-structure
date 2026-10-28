#!/usr/bin/env bash
# The project-local PostgreSQL 18 cluster (D3 §3 interim instance; operator decision 2026-10-28).
#
# Built from the system's PG18 binaries under build/pg/: the developer is its superuser, it listens
# only on its own socket directory (no TCP), preloads pg_textsearch, and holds cs_template with the
# vector and pg_textsearch extensions, which the test databases and `ci db init` clone. It never
# touches the system cluster. Moving to the system instance later changes CORPUS_DATABASE__URL.
#
# Usage: local_pg.sh up | down | status | url [DATABASE]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
PGBIN=/usr/lib/postgresql/18/bin
BASE="$ROOT/build/pg"
DATA="$BASE/data"
SOCKET="$BASE/run"
LOG="$BASE/server.log"
PORT=5440
TEMPLATE=cs_template

url() { echo "postgresql:///${1:-corpus}?host=$SOCKET&port=$PORT"; }

running() { "$PGBIN/pg_ctl" -D "$DATA" status >/dev/null 2>&1; }

sql() { "$PGBIN/psql" -h "$SOCKET" -p "$PORT" -X -q -v ON_ERROR_STOP=1 -tA "$@"; }

init_cluster() {
  [ -x "$PGBIN/initdb" ] || { echo "local_pg: $PGBIN/initdb not found (PostgreSQL 18 binaries)" >&2; exit 1; }
  mkdir -p "$BASE"
  echo "local_pg: initializing $DATA"
  "$PGBIN/initdb" -D "$DATA" --encoding=UTF8 --locale=C.UTF-8 --auth-local=peer \
    --auth-host=reject >"$BASE/initdb.log"
  cat >>"$DATA/postgresql.conf" <<EOF

# local_pg.sh (corpus-structure)
listen_addresses = ''
port = $PORT
unix_socket_directories = '$SOCKET'
shared_preload_libraries = 'pg_textsearch'
default_text_search_config = 'pg_catalog.english'
EOF
}

ensure_template() {
  if [ -z "$(sql -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$TEMPLATE'")" ]; then
    echo "local_pg: creating $TEMPLATE"
    sql -d postgres -c "CREATE DATABASE $TEMPLATE"
  fi
  sql -d "$TEMPLATE" -c "SET client_min_messages = warning" \
    -c "CREATE EXTENSION IF NOT EXISTS vector" \
    -c "CREATE EXTENSION IF NOT EXISTS pg_textsearch"
  sql -d postgres -c "ALTER DATABASE $TEMPLATE IS_TEMPLATE true"
}

up() {
  [ -f "$DATA/PG_VERSION" ] || init_cluster
  mkdir -p "$SOCKET"
  if ! running; then
    "$PGBIN/pg_ctl" -D "$DATA" -l "$LOG" -w -s start
  fi
  ensure_template
  echo "local_pg: up on $(url)"
}

down() {
  if [ -f "$DATA/PG_VERSION" ] && running; then
    "$PGBIN/pg_ctl" -D "$DATA" -m fast -w -s stop
    echo "local_pg: stopped"
  else
    echo "local_pg: not running"
  fi
}

status() {
  if [ ! -f "$DATA/PG_VERSION" ]; then
    echo "local_pg: not initialized (run \`just db-up\`)"
    return 1
  fi
  if ! running; then
    echo "local_pg: stopped (run \`just db-up\`)"
    return 1
  fi
  echo "local_pg: running on $(url)"
  echo "version: $(sql -d postgres -c 'SHOW server_version')"
  echo "preload: $(sql -d postgres -c 'SHOW shared_preload_libraries')"
  local ext
  ext=$(sql -d postgres -c "SELECT 1 FROM pg_database WHERE datname = '$TEMPLATE'")
  if [ -n "$ext" ]; then
    ext=$(sql -d "$TEMPLATE" -c "SELECT string_agg(extname || ' ' || extversion, ', ' ORDER BY extname) FROM pg_extension WHERE extname IN ('vector', 'pg_textsearch')")
    echo "$TEMPLATE: ${ext:-no extensions}"
  else
    echo "$TEMPLATE: missing (run \`just db-up\`)"
  fi
  echo "databases: $(sql -d postgres -c "SELECT string_agg(datname, ' ' ORDER BY datname) FROM pg_database WHERE NOT datname IN ('postgres', 'template0', 'template1')")"
}

case "${1:-}" in
  up) up ;;
  down) down ;;
  status) status ;;
  url) url "${2:-}" ;;
  *) echo "usage: local_pg.sh up | down | status | url [DATABASE]" >&2; exit 2 ;;
esac
