## Migrations (app/alembic/versions/)

29 migrations applied (0001–0029, plus 0003a branch). Run automatically at startup via `startup.sh`.
To add a new migration: `cd app && alembic revision --autogenerate -m "description"`


| Migration | Description |
|-----------|-------------|
| 0001–0009 | Initial schema, stations, vehicles, checks, audit, items (ai_tags, alternate_names, barcode) |
| 0010 | `active` flag on par_levels |
| 0011 | `primary_color` on stations; `vehicle_color` on vehicles |
| 0012 | `call_sign` on stations |
| 0013 | `vehicle_id` nullable on daily_inventory_checks; `location_id` FK for portable checks |
| 0014 | `stock_transfers` table; backfills 4 default compartments for supply rooms with zero |
| 0015 | `priority_check` + `priority_question` on par_levels; `requires_full_check` on compartments |
| 0016 | `is_damaged` (bool) on check_line_items; batch mode |
| 0017 | `station_supply` (bool NOT NULL DEFAULT TRUE) on items; batch mode; SR-M1 |
| 0018 | Backfills STATION_SUPPLY_ROOM location + Shelf 1–4 compartments for active stations lacking one |
| 0019 | `ix_check_station_date` composite index on `daily_inventory_checks(station_id, check_date)` |
| 0020 | `usage_events` + `usage_event_items` tables; indexes on station_id and timestamp (Session N) |
| 0021 | UPDATE items: AED Pads Adult/Pediatric → `check_type = 'EXPIRY_DATE'`, `recurrence_days = NULL` (Session O) |
| 0022 | `allow_check_modification` Boolean column on `stations` (NOT NULL, server_default=True). Batch mode. (Session Q, B-M10) |
| 0023 | `retired_at`, `retired_by`, `retirement_reason` columns on `vehicles`, `inventory_locations`, `stations`, `stock_lots`. All nullable. Batch mode. (Session R, RET-M1/M2/M3) |
| 0024 | `deactivated_at` (DateTime, nullable) and `deactivation_reason` (String 500, nullable) on `par_levels`. Batch mode. (Session T, B-M6) |
| 0025 | check_date Date type fix; inline unnamed FK removed from batch_alter_table for SQLite + PostgreSQL compat (Session X/AB, CQ-B6, BUG-AB1) |
| 0026 | `check_date` `String(10)` → `Date` type (Session X, CQ-B6) |
| 0027 | `station_members` unique constraint changed to `(station_id, user_id, role)` — supports multiple roles per person (Session Z, ACC-B7) |
| 0028 | `items.station_id` FK (NOT NULL → stations); `uq_items_station_name(station_id, name)` replaces global unique on name. **Raw SQL** (not batch mode) — Alembic batch was re-carrying the inline UNIQUE from sqlite_master DDL through every table recreation; raw CREATE TABLE + INSERT SELECT + DROP + RENAME bypasses reflection entirely. (Session AG/AI, ITM-1) |
| 0029 | `items.category_group` VARCHAR(100) nullable; batch mode (Session AH, ITM-3) |