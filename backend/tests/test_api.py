"""
Unit Tests for Phase 19 Bridge Deterioration Risk Scoring API
Risk-Aware Bridge Maintenance Intelligence Platform
"""

import os
import sys
import copy
import json
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app import app


class TestScoringAPI(unittest.TestCase):
    """Test suite for Flask API endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.fixture_path = os.path.join(
            PROJECT_ROOT, "backend", "tests", "fixtures", "regression_test_fixture.json"
        )
        assert os.path.exists(cls.fixture_path), f"Missing test fixture: {cls.fixture_path}"
        with open(cls.fixture_path, "r", encoding="utf-8") as f:
            cls.fixtures_data = json.load(f)["fixtures"]

    def test_01_health_check(self):
        """GET /api/health returns 200 with model ready status."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["model_ready"])
        self.assertEqual(data["features_count"], 26)

    def test_02_model_metadata(self):
        """GET /api/model/metadata returns feature schema and disclaimers."""
        res = self.client.get("/api/model/metadata")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["feature_schema"]["total_count"], 26)
        self.assertIn("scientific_disclaimers", data)
        self.assertIn("no_collapse_prediction", data["scientific_disclaimers"])
        self.assertIn("validation_scope", data["scientific_disclaimers"])

    def test_03_sample_records(self):
        """GET /api/sample-records returns verified authentic records."""
        res = self.client.get("/api/sample-records")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreater(data["count"], 0)
        self.assertIn("input_record", data["samples"][0])

    def test_04_score_single_valid_record(self):
        """POST /api/score returns calibrated probability and raw score matching verified fixture."""
        sample = self.fixtures_data[0]
        payload = sample["input_record"]
        res = self.client.post("/api/score", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertAlmostEqual(data["raw_decision_score"], sample["expected_raw_score"], places=5)
        self.assertAlmostEqual(
            data["calibrated_deterioration_probability"],
            sample["expected_calibrated_probability"],
            places=5,
        )
        self.assertIn("prediction_semantics", data)
        self.assertIn("model_metadata", data)
        self.assertEqual(data["model_metadata"]["features_count"], 26)

    def test_05_score_wrapped_record_format(self):
        """POST /api/score accepts wrapped { record: { ... } } format."""
        sample = self.fixtures_data[0]
        payload = {"record": sample["input_record"]}
        res = self.client.post("/api/score", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertAlmostEqual(data["raw_decision_score"], sample["expected_raw_score"], places=5)

    def test_06_score_missing_required_features_fails(self):
        """POST /api/score returns 400 when required features are missing."""
        bad_payload = copy.deepcopy(self.fixtures_data[0]["input_record"])
        del bad_payload["prior_deck_condition"]
        del bad_payload["adt"]

        res = self.client.post("/api/score", json=bad_payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "validation_error")
        self.assertIn("prior_deck_condition", data["message"])
        self.assertIn("adt", data["message"])

    def test_07_score_wrong_data_type_fails(self):
        """POST /api/score returns 400 when numeric feature receives non-numeric string."""
        bad_payload = copy.deepcopy(self.fixtures_data[0]["input_record"])
        bad_payload["adt"] = "invalid_not_a_number"

        res = self.client.post("/api/score", json=bad_payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "validation_error")
        self.assertIn("adt", data["message"])

    def test_08_score_empty_or_non_json_fails(self):
        """POST /api/score returns 400 on malformed or non-JSON payloads."""
        res1 = self.client.post("/api/score", data="not json", content_type="text/plain")
        self.assertEqual(res1.status_code, 400)

        res2 = self.client.post("/api/score", json="not a dict")
        self.assertEqual(res2.status_code, 400)

    def test_09_score_unknown_categorical_generates_warnings(self):
        """POST /api/score handles unknown categories and returns warnings."""
        payload = copy.deepcopy(self.fixtures_data[0]["input_record"])
        payload["state_code"] = "99"  # unobserved state code
        res = self.client.post("/api/score", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreater(len(data["warnings"]), 0)
        self.assertIn("unobserved category '99'", data["warnings"][0])

    def test_10_score_batch_valid(self):
        """POST /api/score/batch processes multiple records."""
        records = [f["input_record"] for f in self.fixtures_data]
        res = self.client.post("/api/score/batch", json={"records": records})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], len(records))
        for i in range(len(records)):
            self.assertAlmostEqual(
                data["results"][i]["raw_decision_score"],
                self.fixtures_data[i]["expected_raw_score"],
                places=5,
            )

    def test_11_score_batch_empty(self):
        """POST /api/score/batch handles empty array gracefully."""
        res = self.client.post("/api/score/batch", json={"records": []})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_12_cors_headers(self):
        """Verifies that CORS headers are attached to responses."""
        res = self.client.get("/api/health")
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "*")

    def test_13_options_method(self):
        """OPTIONS request returns 204 No Content."""
        res = self.client.options("/api/score")
        self.assertEqual(res.status_code, 204)

    def test_14_not_found_endpoint(self):
        """Invalid route returns 404 with standard error JSON."""
        res = self.client.get("/api/non_existent_route")
        self.assertEqual(res.status_code, 404)
        data = res.get_json()
        self.assertEqual(data["error"], "not_found")


if __name__ == "__main__":
    unittest.main()
