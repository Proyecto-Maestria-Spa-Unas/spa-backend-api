#!/usr/bin/env bash
# Se ejecuta UNA vez, al crear el volumen de la base local (docker-entrypoint-initdb.d).
# Aplica el mismo orden que el CI de spa-database: shim de Supabase → migraciones → seed.
set -euo pipefail

RAIZ=/spa-database
PSQL=(psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB")

if [ ! -d "$RAIZ/supabase/migrations" ]; then
  echo "ERROR: no se encontró spa-database en $RAIZ."
  echo "Clone spa-database al lado de este repositorio o defina SPA_DATABASE_DIR en .env"
  exit 1
fi

echo "→ Shim de Supabase (roles anon/authenticated/service_role, auth.uid())"
"${PSQL[@]}" -f "$RAIZ/scripts/ci/supabase_shim.sql"

for migracion in $(ls "$RAIZ"/supabase/migrations/*.sql | sort); do
  echo "→ Migración $(basename "$migracion")"
  "${PSQL[@]}" -f "$migracion"
done

if [ -f "$RAIZ/supabase/seed.sql" ]; then
  echo "→ Seed"
  "${PSQL[@]}" -f "$RAIZ/supabase/seed.sql"
fi
echo "✓ Base local lista con el esquema de spa-database"
