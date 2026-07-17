#!/usr/bin/env bash
# Dump the Postgres database to infra/backups/journey_<timestamp>.sql.gz
# Usage: ./backup-db.sh          (keeps the 14 most recent backups)
set -euo pipefail

cd "$(dirname "$0")"
mkdir -p backups
STAMP=$(date +%Y%m%d_%H%M%S)
FILE="backups/journey_${STAMP}.sql.gz"

docker exec thejourney-db pg_dump -U journey journey_db | gzip > "$FILE"
echo "Backup written: $FILE ($(du -h "$FILE" | cut -f1))"

# Retention: keep the newest 14
ls -t backups/journey_*.sql.gz 2>/dev/null | tail -n +15 | xargs -r rm --
