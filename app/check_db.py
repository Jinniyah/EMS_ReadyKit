"""
check_db.py — one-time diagnostic script.
Run from the app directory: python check_db.py

Prints:
  - Current Alembic version in the DB
  - Whether the color/call_sign columns exist on stations and vehicles
"""
import sys

sys.path.insert(0, ".")

import os
import sqlite3

db_path = "ems_readykit_dev.db"

if not os.path.exists(db_path):
    print(f"ERROR: {db_path} not found in {os.getcwd()}")
    sys.exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()

# Alembic version
cur.execute("SELECT version_num FROM alembic_version")
rows = cur.fetchall()
print(f"alembic_version rows: {rows}")

# stations columns
cur.execute("PRAGMA table_info(stations)")
station_cols = [r[1] for r in cur.fetchall()]
print(f"\nstations columns: {station_cols}")
print(f"  primary_color present: {'primary_color' in station_cols}")
print(f"  call_sign     present: {'call_sign' in station_cols}")

# vehicles columns
cur.execute("PRAGMA table_info(vehicles)")
vehicle_cols = [r[1] for r in cur.fetchall()]
print(f"\nvehicles columns: {vehicle_cols}")
print(f"  vehicle_color present: {'vehicle_color' in vehicle_cols}")

# par_levels columns
cur.execute("PRAGMA table_info(par_levels)")
par_cols = [r[1] for r in cur.fetchall()]
print(f"\npar_levels columns: {par_cols}")
print(f"  active present: {'active' in par_cols}")

conn.close()
