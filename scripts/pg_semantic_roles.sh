#!/usr/bin/env bash
# Restricted semantic-model principals on 18/corpus only. No databases are changed.
set -euo pipefail

readonly PUBLISHER=corpus_sem_publisher
readonly WRITER=corpus_sem_writer
readonly READER=corpus_sem_reader
readonly EVALUATOR=corpus_sem_evaluator
readonly FITTER=corpus_sem_fitter
readonly ADMITTER=corpus_sem_admitter

# Machine-readable inventory is safe even on hosts without PostgreSQL or sudo.
if [[ $# == 1 && "$1" == --principals ]]; then
  printf '%s %s\n' publisher "$PUBLISHER" write "$WRITER" read "$READER" evaluate "$EVALUATOR" fit "$FITTER" admit "$ADMITTER"
  exit 0
fi
FITTER_ONLY=false
if [[ $# == 1 && "$1" == --fitter-only ]]; then
  FITTER_ONLY=true
elif [[ $# != 0 ]]; then
  echo 'usage: pg_semantic_roles.sh [--principals|--fitter-only]' >&2
  exit 2
fi

PORT=5434
CONF=/etc/postgresql/18/corpus
OPERATOR=$(id -un)
[[ "$OPERATOR" =~ ^[a-z_][a-z0-9_-]*$ ]] || { echo 'unsupported operator name' >&2; exit 1; }
pg_lsclusters -h | awk '$1==18 && $2=="corpus" && $3==5434 {found=1} END {exit !found}'
pg() { sudo -n -u postgres psql -p "$PORT" -X -q -v ON_ERROR_STOP=1 -d postgres "$@"; }

if "$FITTER_ONLY"; then
  pg <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${FITTER}') THEN
    CREATE ROLE ${FITTER} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
      NOREPLICATION NOBYPASSRLS;
  END IF;
  IF EXISTS (SELECT FROM pg_roles WHERE rolname='${FITTER}' AND
             (NOT rolcanlogin OR rolinherit OR rolsuper OR rolcreatedb OR rolcreaterole
              OR rolreplication OR rolbypassrls))
     OR EXISTS (SELECT FROM pg_auth_members WHERE member='${FITTER}'::regrole) THEN
    RAISE EXCEPTION 'existing fitting role differs from restricted provisioning contract';
  END IF;
END \$\$;
SQL
else
  pg <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${PUBLISHER}') THEN
    CREATE ROLE ${PUBLISHER} NOLOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${WRITER}') THEN
    CREATE ROLE ${WRITER} LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${READER}') THEN
    CREATE ROLE ${READER} LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${ADMITTER}') THEN
    CREATE ROLE ${ADMITTER} LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${EVALUATOR}') THEN
    CREATE ROLE ${EVALUATOR} LOGIN;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='${FITTER}') THEN
    CREATE ROLE ${FITTER} LOGIN NOINHERIT;
  END IF;
END \$\$;
ALTER ROLE ${PUBLISHER} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE ${WRITER} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE ${READER} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE ${ADMITTER} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE ${EVALUATOR} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
ALTER ROLE ${FITTER} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
DO \$\$ BEGIN
  IF EXISTS (SELECT FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member
             WHERE r.rolname IN ('${WRITER}','${READER}','${EVALUATOR}','${FITTER}','${ADMITTER}','${PUBLISHER}')) THEN
    RAISE EXCEPTION 'semantic principals must not inherit any role';
  END IF;
END \$\$;
GRANT ${PUBLISHER} TO "$OPERATOR" WITH INHERIT FALSE, SET TRUE;
SQL
fi

# Prepend a dedicated include; preserve every existing authentication rule.
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT
if "$FITTER_ONLY"; then
  sudo cat "$CONF/semantic_hba.conf" >"$TASK_TMP/semantic_hba.conf"
  line="local all $FITTER peer map=corpus_semantic"
  if ! grep -Fxq "$line" "$TASK_TMP/semantic_hba.conf"; then
    printf '%s\n' "$line" >>"$TASK_TMP/semantic_hba.conf"
  fi
  AUTH_PRINCIPALS=("$FITTER")
else
  printf 'local all %s peer map=corpus_semantic\n' "$WRITER,$READER,$EVALUATOR,$FITTER,$ADMITTER" >"$TASK_TMP/semantic_hba.conf"
  AUTH_PRINCIPALS=("$WRITER" "$READER" "$EVALUATOR" "$FITTER" "$ADMITTER")
fi
sudo install -o postgres -g postgres -m 640 "$TASK_TMP/semantic_hba.conf" "$CONF/semantic_hba.conf"
if ! sudo grep -Fxq "include_if_exists semantic_hba.conf" "$CONF/pg_hba.conf"; then
  printf "include_if_exists semantic_hba.conf\n" >"$TASK_TMP/pg_hba.conf"
  sudo sed "/^include_if_exists 'semantic_hba.conf'$/d" "$CONF/pg_hba.conf" >>"$TASK_TMP/pg_hba.conf"
  sudo install -o postgres -g postgres -m 640 "$TASK_TMP/pg_hba.conf" "$CONF/pg_hba.conf"
fi
sudo cat "$CONF/pg_ident.conf" >"$TASK_TMP/pg_ident.conf"
for principal in "${AUTH_PRINCIPALS[@]}"; do
  line="corpus_semantic $OPERATOR $principal"
  if ! grep -Fxq "$line" "$TASK_TMP/pg_ident.conf"; then
    printf '%s\n' "$line" >>"$TASK_TMP/pg_ident.conf"
  fi
done
sudo install -o postgres -g postgres -m 640 "$TASK_TMP/pg_ident.conf" "$CONF/pg_ident.conf"
pg -c 'SELECT pg_reload_conf()'
pg -c "DO \$\$ BEGIN IF EXISTS (SELECT FROM pg_hba_file_rules WHERE error IS NOT NULL) OR EXISTS (SELECT FROM pg_ident_file_mappings WHERE error IS NOT NULL) THEN RAISE EXCEPTION 'invalid authentication configuration'; END IF; END \$\$;"
echo 'semantic principals provisioned on 18/corpus:5434; database grants belong to deployment'
