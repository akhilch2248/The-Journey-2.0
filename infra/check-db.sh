#!/usr/bin/env bash
# Quick look inside the Postgres container: tables, users, weights, ownership.
set -euo pipefail

docker exec -i thejourney-db psql -U journey -d journey_db <<'SQL'
\dt
TABLE users;
TABLE weights;
TABLE goals;
SELECT u.id AS user_id, u.provider, u.provider_id, w.date, w.weight_kg
FROM users u LEFT JOIN weights w ON w.user_id = u.id
ORDER BY u.id, w.date;
SQL
