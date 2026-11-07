#!/usr/bin/env bash
# Provision the dedicated PostgreSQL 18 cluster 18/corpus (D3 §13). Idempotent; needs sudo.
#
# Creates the cluster with postgresql-common (socket only, on the port ops/postgresql/corpus.conf
# sets), installs that file into its conf.d, restarts the cluster when the file changed, and ensures
# the operator's login role (LOGIN, SUPERUSER, CREATEDB, CREATEROLE), the read-only role corpus_ro,
# the database `corpus`
# and the template cs_template. Both databases get each extension of ops/postgresql/extensions.txt
# at its expected version (`CREATE EXTENSION … VERSION`, then `ALTER EXTENSION … UPDATE TO`), and a
# version that differs afterwards fails the run (DA-018). Never touches any other cluster. No
# backups or archiving yet (D3 §13).
#
# Usage: pg_provision.sh [provision|status]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VER=18
NAME=corpus
CONF_SRC="$ROOT/ops/postgresql/corpus.conf"
CONF_DST="/etc/postgresql/$VER/$NAME/conf.d/corpus.conf"
EXT_RECORD="$ROOT/ops/postgresql/extensions.txt"
PORT=$(sed -nE 's/^[[:space:]]*port[[:space:]]*=[[:space:]]*([0-9]+).*/\1/p' "$CONF_SRC")
[ -n "$PORT" ] || { echo "pg_provision: no port in $CONF_SRC" >&2; exit 1; }
OWNER=${CORPUS_DB_OWNER:-$(id -un)}
TEMPLATE=cs_template
DATABASES=(corpus "$TEMPLATE")

# The record as `name version` lines, comments and blank lines dropped.
expected() { sed -E 's/#.*//' "$EXT_RECORD" | awk 'NF == 2 {print $1, $2} NF != 0 && NF != 2 {exit 1}'; }

psql_pg() { sudo -u postgres psql -p "$PORT" -X -q -v ON_ERROR_STOP=1 -tA "$@"; }

exists() { pg_lsclusters -h | awk -v v="$VER" -v n="$NAME" '$1==v && $2==n {found=1} END {exit !found}'; }

# `name version` of each record extension as installed in database $1 ("-" when absent).
installed() {
  local db=$1 name version got
  while read -r name version; do
    got=$(psql_db "$db" -c "SELECT extversion FROM pg_extension WHERE extname = '$name'" 2>/dev/null) || got=
    echo "$name ${got:--}"
  done < <(expected)
}

psql_db() { psql "postgresql:///$1?host=/var/run/postgresql&port=$PORT&connect_timeout=5" -X -w -q -v ON_ERROR_STOP=1 -tA "${@:2}"; }

# Fail (status 1) when database $1's record extensions differ from the record.
verify() {
  local db=$1 diff
  diff=$(diff <(expected) <(installed "$db")) || {
    echo "pg_provision: $db extension versions differ from $EXT_RECORD (< expected, > installed):" >&2
    echo "$diff" | grep '^[<>]' >&2
    return 1
  }
}

status() {
  exists || { echo "18/$NAME: not created (run ci host provision)"; return 1; }
  pg_lsclusters "$VER" "$NAME" 2>/dev/null || { echo "18/$NAME: not created (run ci host provision)"; return 1; }
  if ! psql_db corpus -c "select 'version ' || current_setting('server_version')" 2>/dev/null; then
    echo "18/$NAME: not reachable as $(id -un) (run ci host up or ci host provision)"
    return 1
  fi
  echo "expected extensions $(expected | paste -sd, - | sed 's/,/, /g') ($EXT_RECORD)"
  local db extensions preload checksums failed=0
  for db in "${DATABASES[@]}"; do
    if ! extensions=$(psql_db "$db" -c \
      "select string_agg(extname || ' ' || extversion, ', ' order by extname) from pg_extension" 2>/dev/null); then
      echo "$db: extension health unavailable (run ci host provision)"
      failed=1
      continue
    fi
    printf '%s extensions %s' "$db" "$extensions"
    if verify "$db" 2>/dev/null; then
      echo " (as expected)"
    else
      echo " (MISMATCH: run ci host provision)"
      failed=1
    fi
  done
  if preload=$(psql_db corpus -c 'show shared_preload_libraries' 2>/dev/null) &&
     checksums=$(psql_db corpus -c 'show data_checksums' 2>/dev/null); then
    printf 'preload %s\nchecksums %s\n' "$preload" "$checksums"
  else
    echo "18/$NAME: server settings unavailable to this principal"
    failed=1
  fi
  return "$failed"
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
    CREATE ROLE "$OWNER" LOGIN SUPERUSER CREATEDB CREATEROLE;
  ELSE
    ALTER ROLE "$OWNER" LOGIN SUPERUSER CREATEDB CREATEROLE;
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
  expected >/dev/null || { echo "pg_provision: $EXT_RECORD: expected '<extension> <version>' lines" >&2; exit 1; }
  local db name version
  for db in "${DATABASES[@]}"; do
    while read -r name version; do
      psql_pg -d "$db" -c "SET client_min_messages = warning" \
        -c "CREATE EXTENSION IF NOT EXISTS $name VERSION '$version'" \
        -c "ALTER EXTENSION $name UPDATE TO '$version'"
    done < <(expected)
  done
  psql_pg -d postgres -c "ALTER DATABASE $TEMPLATE IS_TEMPLATE true"
  local failed=0
  for db in "${DATABASES[@]}"; do verify "$db" || failed=1; done
  status
  return "$failed"
}

case "${1:-provision}" in
  provision) provision ;;
  status) status ;;
  *) echo "usage: pg_provision.sh [provision|status]" >&2; exit 2 ;;
esac
