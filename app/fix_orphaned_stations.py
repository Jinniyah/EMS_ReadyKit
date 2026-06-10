"""
fix_orphaned_stations.py
One-time script to add station membership rows for any station that has
no members at all — i.e. stations created before the create_station auto-
membership bug was fixed.

Adds both jinniyah@gmail.com (real admin) and test-administrator@ems.local
(dev test admin) as Administrators to every station missing those memberships.

Usage:
    cd app
    python fix_orphaned_stations.py

Safe to run multiple times — all inserts are idempotent.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")

from sqlalchemy.orm import Session

from ems_readykit.core.database import SessionLocal
from ems_readykit.models.station import Station
from ems_readykit.models.station_member import StationMember

ADMINS = [
    ("jinniyah@gmail.com",             "Jinni Allen"),
    ("test-administrator@ems.local",   "Test Administrator"),
]

ASSIGNED_BY = "fix_orphaned_stations.py"


def fix(db: Session) -> None:
    stations = db.query(Station).filter(Station.active).all()
    print(f"Found {len(stations)} active station(s).\n")

    for station in stations:
        print(f"Station [{station.station_id}]: {station.name}")

        for user_id, preferred_name in ADMINS:
            existing = db.query(StationMember).filter(
                StationMember.station_id == station.station_id,
                StationMember.user_id    == user_id,
            ).first()

            if existing and existing.active:
                print(f"  ✓ {user_id} — already a member, skipping")
            elif existing and not existing.active:
                existing.active = True
                print(f"  ↺ {user_id} — re-activated")
            else:
                db.add(StationMember(
                    station_id     = station.station_id,
                    user_id        = user_id,
                    preferred_name = preferred_name,
                    role           = "Administrator",
                    assigned_by    = ASSIGNED_BY,
                    active         = True,
                ))
                print(f"  + {user_id} — added as Administrator")

    db.commit()
    print("\nDone. All orphaned stations now have admin membership rows.")
    print("Refresh the admin screen in the browser to see them.")


if __name__ == "__main__":
    db: Session = SessionLocal()
    try:
        fix(db)
    except Exception as e:
        db.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        db.close()
