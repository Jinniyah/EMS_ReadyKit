#!/bin/bash
# startup.sh
# Runs Alembic migrations then starts gunicorn via the Oryx antenv virtualenv.
#
# Oryx extracts the compressed build to APP_PATH (/tmp/8dea.../), which contains
# both the antenv virtualenv AND all app files (alembic.ini, alembic/, ems_readykit/).
# /home/site/wwwroot contains only the compressed tarball (output.tar.zst),
# NOT the extracted files — so we must work from APP_PATH, not wwwroot.

set -e

echo "=== EMS ReadyKit startup ==="
echo "APP_PATH : ${APP_PATH:-not set}"
echo "PWD      : $(pwd)"

# ── Use APP_PATH as the working directory ─────────────────────────────────────
# Oryx extracts the build to APP_PATH before running startup.sh.
# All app files live there: antenv/, alembic.ini, alembic/, ems_readykit/, etc.
# Do NOT cd to /home/site/wwwroot — it only has the compressed tarball.
if [ -n "$APP_PATH" ] && [ -d "$APP_PATH" ]; then
    echo "Switching to APP_PATH: $APP_PATH"
    cd "$APP_PATH"
else
    echo "APP_PATH not set or not found, staying in: $(pwd)"
fi
echo "Working directory: $(pwd)"

# ── Activate the Oryx-managed virtualenv ──────────────────────────────────────
# antenv/ is in APP_PATH alongside the app files.
if [ -f "antenv/bin/activate" ]; then
    echo "Activating antenv virtualenv..."
    source antenv/bin/activate
else
    echo "ERROR: antenv virtualenv not found at $(pwd)/antenv"
    echo "Contents of working directory:"
    ls -la
    exit 1
fi

echo "Using Python  : $(which python)"
echo "Using gunicorn: $(which gunicorn)"
echo "Using alembic : $(which alembic)"
echo "alembic.ini   : $(ls -la alembic.ini 2>/dev/null || echo NOT FOUND)"
echo "alembic dir   : $(ls -la alembic/ 2>/dev/null || echo NOT FOUND)"

# ── Pre-flight: confirm DB is reachable before running migrations ──────────────
# This surfaces a real error message if the DB is unreachable or the connection
# string is wrong, rather than letting alembic hang silently and starve the
# health check. connect_timeout=10 prevents an indefinite hang on network issues.
echo "Checking database connectivity..."
python -c "
from ems_readykit.core.config import get_settings, resolve_database_url
from sqlalchemy import create_engine, text

settings = get_settings()
url = resolve_database_url(settings)

# Use connect_args for PostgreSQL; SQLite ignores unknown args safely.
connect_args = {}
if url.startswith('postgresql'):
    connect_args['connect_timeout'] = 10

engine = create_engine(url, connect_args=connect_args)
with engine.connect() as conn:
    conn.execute(text('SELECT 1'))
print('Database reachable.')
" || { echo "ERROR: Database not reachable. Aborting startup."; exit 1; }

# ── Run database migrations ────────────────────────────────────────────────────
# Alembic reads alembic.ini from the current directory (APP_PATH).
# Safe to run on every startup — idempotent (no-op if already at head).
echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

# ── Auto-seed if the database is empty ────────────────────────────────────────
# Runs seed.py only when the stations table has zero rows.
# Safe on every deploy — seed.py uses get_or_create throughout.
if [ -f "seed.py" ]; then
    echo "Checking if database needs seeding..."
    STATION_COUNT=$(python -c "
from ems_readykit.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
result = db.execute(text('SELECT COUNT(*) FROM stations')).scalar()
db.close()
print(result)
" 2>/dev/null || echo "0")
    echo "Station count: $STATION_COUNT"

    MEMBER_COUNT=$(python -c "
from ems_readykit.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
try:
    result = db.execute(text('SELECT COUNT(*) FROM station_members')).scalar()
except Exception:
    result = 0
db.close()
print(result)
" 2>/dev/null || echo "0")
    echo "Member count: $MEMBER_COUNT"

    APP_ENV_LOWER=$(echo "${APP_ENV:-}" | tr '[:upper:]' '[:lower:]')
    if [ "$APP_ENV_LOWER" = "production" ]; then
        echo "APP_ENV=production — skipping seed."
    elif [ "$STATION_COUNT" = "0" ] || [ "$MEMBER_COUNT" = "0" ]; then
        echo "Database needs seeding (stations=$STATION_COUNT, members=$MEMBER_COUNT) — running seed..."
        python seed.py && echo "Seed complete." || echo "WARNING: Seed failed — continuing startup."
    else
        echo "Database already seeded ($STATION_COUNT stations, $MEMBER_COUNT members) — skipping."
    fi
else
    echo "seed.py not found — skipping auto-seed."
fi

# ── Start gunicorn ─────────────────────────────────────────────────────────────
# exec replaces this shell so gunicorn receives SIGTERM correctly.
echo "Starting gunicorn..."
exec gunicorn \
    --bind=0.0.0.0:8000 \
    --workers=1 \
    --worker-class=uvicorn.workers.UvicornWorker \
    --timeout=120 \
    --access-logfile=- \
    --error-logfile=- \
    ems_readykit.main:app
