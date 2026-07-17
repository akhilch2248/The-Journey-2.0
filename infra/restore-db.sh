#!/usr/bin/env bash
# Restore a backup produced by backup-db.sh.
# Usage: ./restore-db.sh backups/journey_20260716_090000.sql.gz
set -euo pipefail

if [ $# -ne 1 ] || [ ! -f "$1" ]; then
  echo "Usage: $0 <backups/journey_YYYYmmdd_HHMMSS.sql.gz>" >&2
  exit 1
fi

read -r -p "This OVERWRITES journey_db. Continue? [y/N] " ans
[ "$ans" = "y" ] || exit 1

gunzip -c "$1" | docker exec -i thejourney-db psql -U journey -d journey_db
echo "Restore complete."
