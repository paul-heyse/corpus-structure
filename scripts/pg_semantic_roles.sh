#!/usr/bin/env bash
# Restricted semantic-model principals on 18/corpus only. No databases are changed.
set -euo pipefail

PORT=5434
CONF=/etc/postgresql/18/corpus
OPERATOR=$(id -un)
[[ "$OPERATOR" =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo 'unsupported operator name' >&2; exit 1; }
pg_lsclusters -h | awk '$1==18 && $2=="corpus" && $3==5434 {found=1} END {exit !found}'
pg() { sudo -n -u postgres psql -p "$PORT" -X -q -v ON_ERROR_STOP=1 -d postgres "$@"; }

pg <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='corpus_sem_publisher') THEN
    CREATE ROLE corpus_sem_publisher NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='corpus_sem_writer') THEN
    CREATE ROLE corpus_sem_writer LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='corpus_sem_reader') THEN
    CREATE ROLE corpus_sem_reader LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='corpus_sem_admitter') THEN
    CREATE ROLE corpus_sem_admitter LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='corpus_sem_evaluator') THEN
    CREATE ROLE corpus_sem_evaluator LOGIN;
  END IF;
END \$\$;
ALTER ROLE corpus_sem_publisher NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE corpus_sem_writer LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE corpus_sem_reader LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE corpus_sem_admitter LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE corpus_sem_evaluator LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
DO \$\$ BEGIN
  IF EXISTS (SELECT FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
             WHERE r.rolname IN ('corpus_sem_writer','corpus_sem_reader','corpus_sem_evaluator','corpus_sem_admitter','corpus_sem_publisher')) THEN
    RAISE EXCEPTION 'semantic principals must not inherit any role';
  END IF;
END \$\$;
GRANT corpus_sem_publisher TO "$OPERATOR" WITH INHERIT FALSE, SET TRUE;
SQL

# Prepend a dedicated include; preserve every existing authentication rule.
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT
printf 'local all corpus_sem_writer,corpus_sem_reader,corpus_sem_evaluator,corpus_sem_admitter peer map=corpus_semantic\n' >"$TASK_TMP/semantic_hba.conf"
sudo install -o postgres -g postgres -m 640 "$TASK_TMP/semantic_hba.conf" "$CONF/semantic_hba.conf"
if ! sudo grep -Fxq "include_if_exists semantic_hba.conf" "$CONF/pg_hba.conf"; then
  printf "include_if_exists semantic_hba.conf\n" >"$TASK_TMP/pg_hba.conf"
  sudo sed "/^include_if_exists 'semantic_hba.conf'$/d" "$CONF/pg_hba.conf" >>"$TASK_TMP/pg_hba.conf"
  sudo install -o postgres -g postgres -m 640 "$TASK_TMP/pg_hba.conf" "$CONF/pg_hba.conf"
fi
sudo cat "$CONF/pg_ident.conf" >"$TASK_TMP/pg_ident.conf"
for principal in corpus_sem_writer corpus_sem_reader corpus_sem_evaluator corpus_sem_admitter; do
  line="corpus_semantic $OPERATOR $principal"
  if ! grep -Fxq "$line" "$TASK_TMP/pg_ident.conf"; then
    printf '%s\n' "$line" >>"$TASK_TMP/pg_ident.conf"
  fi
done
sudo install -o postgres -g postgres -m 640 "$TASK_TMP/pg_ident.conf" "$CONF/pg_ident.conf"
pg -c 'SELECT pg_reload_conf()'
pg -c "DO \$\$ BEGIN IF EXISTS (SELECT FROM pg_hba_file_rules WHERE error IS NOT NULL) OR EXISTS (SELECT FROM pg_ident_file_mappings WHERE error IS NOT NULL) THEN RAISE EXCEPTION 'invalid authentication configuration'; END IF; END \$\$;"
echo 'semantic principals provisioned on 18/corpus:5434; database grants belong to deployment'
