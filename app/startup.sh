#!/bin/bash
# startup.sh
# Runs Alembic migrations then starts gunicorn via the Oryx antenv virtualenv.
#
# Oryx extracts the compressed build to APP_PATH (/tmp/8dea.../), which contains
# both the antenv virtualenv AND all app files (alembic.ini, alembic/, ems_readykit/).
# /home/site/wwwroot contains only the compressed tarball (output.tar.zst),
# NOT the extracted files — so we must work from APP_PATH, not wwwroot.
#
# Seed strategy (two independent passes):
#
#   Pass 1 — Operational seed (dev/staging only, skipped in production):
#     Runs seed.py when the real operational stations (Newberg Township Station
#     and Marcellus Township Station) do not both already exist. Creates those
#     two stations plus the Newberg Training Station and TEST STATION.
#     Skipped in production because real station data is entered by the admin
#     after first login, not auto-seeded.
#
#     IMPORTANT — do NOT gate this on a generic "is the stations table empty"
#     row count. Pass 2 (training seed) always runs and always creates exactly
#     one station (Newberg Training Station), so after the first successful
#     boot the stations table is never empty again — a row-count gate would
#     then skip Pass 1 forever, on every future boot, even immediately after a
#     full database wipe, depending purely on which pass's restart cycle
#     reaches the table first. This caused operational stations (Newberg,
#     Marcellus) to silently never get seeded after a DB reset on 2026-06-21.
#     Checking for the two operational stations BY NAME avoids this — Pass 2
#     creating the training station can never satisfy this check.
#
#   Pass 2 — Training seed (always runs, including production):
#     Calls seed_training.py to ensure the Newberg Training Station exists.
#     seed_training.py is idempotent — safe to run on every deploy.
#     Survives a full database teardown and recreate: training data is
#     restored automatically on the next startup without manual intervention.

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

# ── Pass 1: Operational seed (dev/staging only) ────────────────────────────────
# Runs seed.py only when at least one of the two real operational stations is
# missing, AND APP_ENV != production. In production, real station data is
# entered by the administrator after first login — not auto-seeded. The TEST
# STATION and Newberg/Marcellus operational data should never appear in
# production.
if [ -f "seed.py" ]; then
    APP_ENV_LOWER=$(echo "${APP_ENV:-}" | tr '[:upper:]' '[:lower:]')

    if [ "$APP_ENV_LOWER" = "production" ]; then
        echo "Pass 1: APP_ENV=production — skipping operational seed."
    else
        echo "Pass 1: Checking if operational seed is needed..."
        # Check for the two operational stations BY NAME, not a row count.
        # See the comment block at the top of this file for why a row count
        # is wrong here: Pass 2 always creates exactly one station (Newberg
        # Training Station), so the table is never empty after the first
        # successful boot.
        #
        # core/database.py sets engine echo=True whenever APP_ENV !=
        # production, which prints the full SQL log to stdout — same as the
        # earlier station-count check, so the extraction needs the same
        # trailing-digit-only approach via grep -oE '[0-9]+$'.
        OPERATIONAL_COUNT=$(python -c "
from ems_readykit.core.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
result = db.execute(text(
    \"SELECT COUNT(*) FROM stations WHERE name IN \"
    \"('Newberg Township Station', 'Marcellus Township Station')\"
)).scalar()
db.close()
print(result)
" 2>/dev/null | grep -oE '[0-9]+$' | tail -n 1)
        OPERATIONAL_COUNT="${OPERATIONAL_COUNT:-0}"
        echo "  Operational stations present: $OPERATIONAL_COUNT / 2"

        if [ "$OPERATIONAL_COUNT" = "2" ]; then
            echo "  Both operational stations already exist — skipping operational seed."
        else
            echo "  One or both operational stations missing — running operational seed..."
            python seed.py && echo "  Operational seed complete." \
                || echo "  WARNING: Operational seed failed — continuing startup."
        fi
    fi
else
    echo "Pass 1: seed.py not found — skipping."
fi

# ── Pass 2: Training station seed (always runs, including production) ──────────
# seed_training.py ensures the Newberg Training Station exists with both
# training ambulances and jump bags. Fully idempotent — runs on every startup
# and is a no-op if the training station already exists.
#
# This survives a full database teardown: if the DB is wiped and recreated,
# the training station is automatically restored on the next deploy without
# any manual intervention.
if [ -f "seed_training.py" ]; then
    echo "Pass 2: Ensuring training station exists..."
    python seed_training.py && echo "  Training seed complete." \
        || echo "  WARNING: Training seed failed — continuing startup."
else
    echo "Pass 2: seed_training.py not found — skipping."
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
