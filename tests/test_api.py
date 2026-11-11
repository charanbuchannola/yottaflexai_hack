"""FastAPI REST endpoint integration tests covering traceability, transitions, and exceptions."""

from fastapi.testclient import TestClient

from voc_intel.api.app import create_app


def test_api_endpoints_traceability_anomalies_and_fsm_transitions(starter_pipeline) -> None:
    root, _res = starter_pipeline
    db_url = f"sqlite:///{(root / 'data' / 'voc_intelligence.db').as_posix()}"
    app = create_app(database_url=db_url, exports_dir=root / "exports")
    with TestClient(app) as client:
        # 1. Health
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["record_counts"]["reviews"] == 600

        # 2. Recurring themes & sentiment shifts
        themes = client.get("/api/v1/themes")
        assert themes.status_code == 200
        assert len(themes.json()) == 12

        shifts = client.get("/api/v1/shifts", params={"significant_only": "true"})
        assert shifts.status_code == 200
        assert len(shifts.json()) == 3

        # 3. Priorities + source record traceability
        prios = client.get("/api/v1/priorities")
        assert prios.status_code == 200
        items = prios.json()
        assert len(items) > 0
        top_action_id = items[0]["action_id"]

        trace = client.get(f"/api/v1/priorities/{top_action_id}/traceability")
        assert trace.status_code == 200
        trace_body = trace.json()
        assert trace_body["total_evidence_count"] == items[0]["mention_count"]
        assert len(trace_body["sample_evidence"]) > 0
        assert len(trace_body["lifecycle_history"]) >= 2

        # 4. Append-only FSM transition (valid & invalid)
        bad_tx = client.post(
            f"/api/v1/priorities/{top_action_id}/transition",
            json={"to_state": "IDENTIFIED", "actor": "analyst", "reason": "Invalid backward step"},
        )
        assert bad_tx.status_code == 422

        next_target = "IN_PROGRESS" if items[0]["lifecycle_state"] in ("TRIAGED", "ESCALATED") else "VERIFIED"
        good_tx = client.post(
            f"/api/v1/priorities/{top_action_id}/transition",
            json={"to_state": next_target, "actor": "analyst", "reason": "Verified remediation plan"},
        )
        assert good_tx.status_code == 200
        assert good_tx.json()["to_state"] == next_target

        trace_after = client.get(f"/api/v1/priorities/{top_action_id}/traceability").json()
        assert len(trace_after["lifecycle_history"]) == len(trace_body["lifecycle_history"]) + 1

        # 5. Live anomaly detection & reports
        anomalies = client.get("/api/v1/anomalies")
        assert anomalies.status_code == 200
        assert len(anomalies.json()) == 15

        val_rep = client.get("/api/v1/reports/validation")
        assert val_rep.status_code == 200
        assert val_rep.json()["overall_passed"] is True

        eval_rep = client.get("/api/v1/reports/evaluation")
        assert eval_rep.status_code == 200
        assert eval_rep.json()["anomaly_detection_metrics"]["overall"]["f1"] == 1.0
