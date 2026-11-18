#!/usr/bin/env bash
# Restricted semantic-model principals on 18/corpus only. No databases are changed.
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
render() { uv run --project "$ROOT" --no-sync python -m corpus_structure.core.db.host_bootstrap "$@"; }

# Machine-readable inventory is safe even on hosts without PostgreSQL or sudo.
if [[ $# == 1 && "$1" == --principals ]]; then
  render principals
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

ROLE_OPTIONS=()
if "$FITTER_ONLY"; then ROLE_OPTIONS+=(--fitter-only); fi
ROLE_SQL=$(render semantic-sql "$OPERATOR" "${ROLE_OPTIONS[@]}")
HBA_LINE=$(render peer-hba "${ROLE_OPTIONS[@]}")
IDENT_LINES=$(render peer-ident "$OPERATOR" "${ROLE_OPTIONS[@]}")
pg -c "$ROLE_SQL"

# Prepend a dedicated include; preserve every existing authentication rule.
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT
if "$FITTER_ONLY"; then
  sudo cat "$CONF/semantic_hba.conf" >"$TASK_TMP/semantic_hba.conf"
  line=$HBA_LINE
  if ! grep -Fxq "$line" "$TASK_TMP/semantic_hba.conf"; then
    printf '%s\n' "$line" >>"$TASK_TMP/semantic_hba.conf"
  fi
else
  printf '%s\n' "$HBA_LINE" >"$TASK_TMP/semantic_hba.conf"
fi
sudo install -o postgres -g postgres -m 640 "$TASK_TMP/semantic_hba.conf" "$CONF/semantic_hba.conf"
if ! sudo grep -Fxq "include_if_exists semantic_hba.conf" "$CONF/pg_hba.conf"; then
  printf "include_if_exists semantic_hba.conf\n" >"$TASK_TMP/pg_hba.conf"
  sudo sed "/^include_if_exists 'semantic_hba.conf'$/d" "$CONF/pg_hba.conf" >>"$TASK_TMP/pg_hba.conf"
  sudo install -o postgres -g postgres -m 640 "$TASK_TMP/pg_hba.conf" "$CONF/pg_hba.conf"
fi
sudo cat "$CONF/pg_ident.conf" >"$TASK_TMP/pg_ident.conf"
while IFS= read -r line; do
  if ! grep -Fxq "$line" "$TASK_TMP/pg_ident.conf"; then
    printf '%s\n' "$line" >>"$TASK_TMP/pg_ident.conf"
  fi
done <<<"$IDENT_LINES"
sudo install -o postgres -g postgres -m 640 "$TASK_TMP/pg_ident.conf" "$CONF/pg_ident.conf"
RELOAD_SQL=$(render reload)
AUTH_CHECK_SQL=$(render auth-check)
pg -c "$RELOAD_SQL"
pg -c "$AUTH_CHECK_SQL"
echo 'semantic principals provisioned on 18/corpus:5434; database grants belong to deployment'
