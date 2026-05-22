    def test_create_daily_check_returns_201(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "2026-05-10", "timestamp": _utcnow(),
        }, headers=auth_admin)
        assert response.status_code == 201
        assert response.json()["status"] == "PASS"
        assert response.json()["performed_by"] == "Test Administrator"

    def test_create_daily_check_invalid_date_format_returns_422(self, client, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid,
            "check_date": "05/10/2026", "timestamp": _utcnow(),
        }, headers=auth_admin)
        assert response.status_code == 422

    def test_multiple_checks_same_vehicle_same_day_all_succeed(self, client, auth_admin):
        """
        Multiple checks for the same vehicle on the same calendar day are
        explicitly supported. Post-call restock checks, shift-start / shift-end
        checks, and any other station-specific cadence all require this.
        Each check must have a distinct timestamp — it is the natural
        discriminator for a check event within a day.
        """
        import time
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        payload_base = {"vehicle_id": vid, "station_id": sid, "check_date": "2026-06-15"}

        r1 = client.post("/api/v1/checks/daily", json={**payload_base, "timestamp": _utcnow(), "notes": "Shift-start check"}, headers=auth_admin)
        assert r1.status_code == 201, f"First check failed: {r1.json()}"

        time.sleep(0.01)  # ensure distinct timestamps
        r2 = client.post("/api/v1/checks/daily", json={**payload_base, "timestamp": _utcnow(), "notes": "Post-call restock check"}, headers=auth_admin)
        assert r2.status_code == 201, f"Second check failed: {r2.json()}"

        time.sleep(0.01)
        r3 = client.post("/api/v1/checks/daily", json={**payload_base, "timestamp": _utcnow(), "notes": "Shift-end check"}, headers=auth_admin)
        assert r3.status_code == 201, f"Third check failed: {r3.json()}"

        # All three are distinct records
        ids = {r1.json()["check_id"], r2.json()["check_id"], r3.json()["check_id"]}
        assert len(ids) == 3

    def test_create_daily_check_invalid_vehicle_returns_404(self, client, auth_admin):
        response = client.post("/api/v1/checks/daily", json={
            "vehicle_id": 99999999, "station_id": 1, "check_date": "2026-05-10", "timestamp": _utcnow(),
        }, headers=auth_admin)
        assert response.status_code == 404

    def test_daily_check_creates_audit_event(self, client, db, auth_admin):
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid, "check_date": "2026-07-01", "timestamp": _utcnow(),
        }, headers=auth_admin)
        event = db.query(AuditEvent).filter(
            AuditEvent.action == "CHECK_COMPLETED", AuditEvent.vehicle_id == vid,
        ).first()
        assert event is not None
        assert event.severity == "INFO"

    def test_station_compliance_today_returns_all_checks(self, client, auth_admin):
        """All checks for a vehicle today are returned — not just the first."""
        import time
        sid, vid = self._make_station_and_vehicle(client, auth_admin)
        today = datetime.now(timezone.utc).date().isoformat()
        client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid, "check_date": today, "timestamp": _utcnow(),
        }, headers=auth_admin)
        time.sleep(0.01)
        client.post("/api/v1/checks/daily", json={
            "vehicle_id": vid, "station_id": sid, "check_date": today, "timestamp": _utcnow(),
        }, headers=auth_admin)
        response = client.get(f"/api/v1/checks/daily/station/{sid}/today", headers=auth_admin)
        assert response.status_code == 200
        assert len(response.json()) == 2