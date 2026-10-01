"""Unit tests for the leave-request API. Run: python -m unittest -v"""
import os
import tempfile
import unittest

from app import create_app, decide


class LeaveApiTests(unittest.TestCase):
    def setUp(self):
        os.environ.pop("API_KEY", None)
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.client = create_app(self.db_path).test_client()

    def tearDown(self):
        os.remove(self.db_path)

    def post(self, **overrides):
        body = {"student_id": "21CS1001", "days": 2, "from_date": "2026-10-10", "reason": "Fever"}
        body.update(overrides)
        return self.client.post("/leave-requests", json=body)

    def test_decide_rules(self):
        self.assertEqual(decide(1)[0], "APPROVED")
        self.assertEqual(decide(2)[0], "APPROVED")
        self.assertEqual(decide(3)[0], "PENDING_HOD_APPROVAL")
        self.assertEqual(decide(5)[0], "PENDING_HOD_APPROVAL")
        self.assertEqual(decide(6)[0], "ESCALATED")

    def test_short_leave_is_auto_approved(self):
        res = self.post(days=1)
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.get_json()["status"], "APPROVED")
        self.assertEqual(res.get_json()["request_id"], "LR-0001")

    def test_medium_leave_needs_hod(self):
        self.assertEqual(self.post(days=4).get_json()["status"], "PENDING_HOD_APPROVAL")

    def test_long_leave_is_escalated(self):
        self.assertEqual(self.post(days=10).get_json()["status"], "ESCALATED")

    def test_get_status_roundtrip(self):
        rid = self.post(days=3).get_json()["request_id"]
        res = self.client.get(f"/leave-requests/{rid.lower()}")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()["status"], "PENDING_HOD_APPROVAL")

    def test_unknown_request_is_404(self):
        self.assertEqual(self.client.get("/leave-requests/LR-9999").status_code, 404)

    def test_bad_request_id_is_400(self):
        self.assertEqual(self.client.get("/leave-requests/abc").status_code, 400)

    def test_validation_errors(self):
        self.assertEqual(self.post(days=0).status_code, 400)
        self.assertEqual(self.post(days=31).status_code, 400)
        self.assertEqual(self.post(days="two").status_code, 400)
        self.assertEqual(self.post(from_date="10/10/2026").status_code, 400)
        self.assertEqual(self.post(student_id="x").status_code, 400)
        self.assertEqual(self.post(reason="").status_code, 400)
        self.assertEqual(self.client.post("/leave-requests", data="nope").status_code, 400)

    def test_api_key_enforced_when_configured(self):
        os.environ["API_KEY"] = "secret"
        try:
            self.assertEqual(self.client.get("/leave-requests/LR-0001").status_code, 401)
            self.assertEqual(self.client.get("/health").status_code, 200)
            res = self.client.get("/leave-requests/LR-0001", headers={"X-API-Key": "secret"})
            self.assertEqual(res.status_code, 404)  # authorised, just not found
        finally:
            os.environ.pop("API_KEY", None)


if __name__ == "__main__":
    unittest.main()
