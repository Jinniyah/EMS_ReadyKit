#!/bin/bash
# startup.sh
# Runs Alembic migrations then starts gunicorn via the Oryx antenv virtualenv.
#
# Oryx extracts the compressed build to a temp path ($APP_PATH) and runs
# startup.sh from there. However the permanent wwwroot copy at
# /home/site/wwwroot always has the full directory tree. We cd there so
# alembic.ini and the alembic/ scripts folder are always found.

set -e

echo "=== EMS ReadyKit startup ==="
echo "APP_PATH : ${APP_PATH:-not set}"
echo "PWD      : $(pwd)"

# ── Always work from the permanent wwwroot ────────────────────────────────────
# Oryx's tmp extraction path (/tmp/8dea.../) may not have all files present
# when startup.sh first runs. /home/site/wwwroot is always fully populated.
WWWROOT="/home/site/wwwroot"
if [ -d "$WWWROOT" ]; then
    echo "Switching to wwwroot: $WWWROOT"
    cd "$WWWROOT"
fi
echo "Working directory: $(pwd)"

# ── Activate the Oryx-managed virtualenv ──────────────────────────────────────
# Oryx extracts the build (including antenv) to APP_PATH.
# Try APP_PATH first, then fall back to local antenv/ in case CWD matches.
if [ -n "$APP_PATH" ] && [ -f "$APP_PATH/antenv/bin/activate" ]; then
    echo "Activating antenv from APP_PATH..."
    source "$APP_PATH/antenv/bin/activate"
elif [ -f "antenv/bin/activate" ]; then
    echo "Activating antenv from wwwroot..."
    source antenv/bin/activate
else
    echo "ERROR: antenv virtualenv not found."
    echo "APP_PATH contents:"
    ls -la "${APP_PATH:-$(pwd)}"
    exit 1
fi

echo "Using Python  : $(which python)"
echo "Using gunicorn: $(which gunicorn)"
echo "Using alembic : $(which alembic)"
echo "alembic.ini   : $(ls -la alembic.ini 2>/dev/null || echo NOT FOUND)"
echo "alembic dir   : $(ls -la alembic/ 2>/dev/null || echo NOT FOUND)"

# ── Run database migrations ────────────────────────────────────────────────────
echo "Running Alembic migrations..."
alembic upgrade head
echo "Migrations complete."

# ── Start gunicorn ─────────────────────────────────────────────────────────────
echo "Starting gunicorn..."
exec gunicorn \
    --bind=0.0.0.0:8000 \
    --workers=1 \
    --worker-class=uvicorn.workers.UvicornWorker \
    --timeout=120 \
    --access-logfile=- \
    --error-logfile=- \
    ems_readykit.main:app
