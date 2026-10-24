"""
Phase 19: End-to-End Frontend-Backend Integration & Smoke Test Suite
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
from backend.score_bridge_risk import (
    ALL_REQUIRED_FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    SEMANTICS_DISCLAIMER,
)


class TestFrontendBackendIntegrationSmoke(unittest.TestCase):
    """End-to-end integration and smoke tests verifying the frontend-backend contract."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.fixture_path = os.path.join(
            PROJECT_ROOT, "backend", "tests", "fixtures", "regression_test_fixture.json"
        )
        assert os.path.exists(cls.fixture_path), f"Missing test fixture: {cls.fixture_path}"
        with open(cls.fixture_path, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)["fixtures"]

    def test_01_health_contract_matches_frontend_types(self):
        """Verify GET /api/health matches frontend HealthCheckResponse interface."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        # Check required fields
        self.assertIn("status", data)
        self.assertIn(data["status"], ["healthy", "degraded", "unhealthy"])
        self.assertIn("service", data)
        self.assertIn("phase", data)
        self.assertIn("model_ready", data)
        self.assertIsInstance(data["model_ready"], bool)
        self.assertIn("features_count", data)
        self.assertEqual(data["features_count"], 26)
        self.assertIn("target_semantics", data)

    def test_02_model_metadata_matches_frontend_types(self):
        """Verify GET /api/model/metadata matches frontend ModelMetadataResponse interface."""
        res = self.client.get("/api/model/metadata")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("model_type", data)
        self.assertIn("target_name", data)
        self.assertIn("scientific_disclaimers", data)
        disclaimers = data["scientific_disclaimers"]
        self.assertIn("no_collapse_prediction", disclaimers)
        self.assertIn("no_engineering_replacement", disclaimers)
        self.assertIn("validation_scope", disclaimers)
        self.assertIn("separation_of_concerns", disclaimers)

        self.assertIn("feature_schema", data)
        schema = data["feature_schema"]
        self.assertEqual(schema["total_count"], 26)
        self.assertEqual(len(schema["numeric_features"]), 13)
        self.assertEqual(len(schema["categorical_features"]), 13)

    def test_03_sample_records_contract_matches_frontend(self):
        """Verify GET /api/sample-records provides authentic non-test records."""
        res = self.client.get("/api/sample-records")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertIn("count", data)
        self.assertGreaterEqual(data["count"], 3)
        self.assertIn("samples", data)

        for s in data["samples"]:
            self.assertIn("bridge_id", s)
            self.assertIn("input_record", s)
            self.assertIn("verified_raw_score", s)
            self.assertIn("verified_calibrated_probability", s)
            inp = s["input_record"]
            for col in ALL_REQUIRED_FEATURES:
                self.assertIn(col, inp, f"Missing feature {col} in sample record")

    def test_04_smoke_flow_verified_records_end_to_end(self):
        """Smoke test: execute inference on all verified sample records and check output schema."""
        for sample in self.fixtures:
            bid = sample["bridge_id"]
            inp = sample["input_record"]
            expected_raw = sample["expected_raw_score"]
            expected_cal = sample["expected_calibrated_probability"]

            res = self.client.post("/api/score", json=inp)
            self.assertEqual(res.status_code, 200, f"Scoring failed for bridge {bid}")
            data = res.get_json()

            # Output schema check
            self.assertIn("raw_decision_score", data)
            self.assertIn("calibrated_deterioration_probability", data)
            self.assertIn("prediction_semantics", data)
            self.assertIn("model_metadata", data)
            self.assertIn("warnings", data)

            # Precision check
            self.assertAlmostEqual(data["raw_decision_score"], expected_raw, places=5)
            self.assertAlmostEqual(
                data["calibrated_deterioration_probability"], expected_cal, places=5
            )

            # Bounds check
            self.assertGreaterEqual(data["calibrated_deterioration_probability"], 0.0)
            self.assertLessEqual(data["calibrated_deterioration_probability"], 1.0)

            # Semantic statement check
            self.assertEqual(data["prediction_semantics"], SEMANTICS_DISCLAIMER)

    def test_05_error_payload_security_no_traceback_leakage(self):
        """Verify error payloads return safe structured JSON without python stack traces."""
        # Test 1: missing required column
        bad_inp = copy.deepcopy(self.fixtures[0]["input_record"])
        del bad_inp["prior_deck_condition"]
        res = self.client.post("/api/score", json=bad_inp)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertIn("message", data)
        self.assertNotIn("Traceback", json.dumps(data))
        self.assertNotIn("File \"", json.dumps(data))

        # Test 2: non-numeric type
        bad_inp2 = copy.deepcopy(self.fixtures[0]["input_record"])
        bad_inp2["structure_len_mt"] = "not_a_number_abc"
        res2 = self.client.post("/api/score", json=bad_inp2)
        self.assertEqual(res2.status_code, 400)
        data2 = res2.get_json()
        self.assertIn("error", data2)
        self.assertNotIn("Traceback", json.dumps(data2))

    def test_06_batch_scoring_smoke_flow(self):
        """Verify batch scoring flow with all authentic records."""
        records = [f["input_record"] for f in self.fixtures]
        res = self.client.post("/api/score/batch", json={"records": records})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()

        self.assertEqual(data["count"], len(records))
        self.assertEqual(len(data["results"]), len(records))

        for idx, item in enumerate(data["results"]):
            expected = self.fixtures[idx]
            self.assertAlmostEqual(
                item["raw_decision_score"], expected["expected_raw_score"], places=5
            )
            self.assertAlmostEqual(
                item["calibrated_deterioration_probability"],
                expected["expected_calibrated_probability"],
                places=5,
            )

    def test_07_cors_and_options_smoke(self):
        """Verify CORS headers and OPTIONS preflight for browser frontend."""
        res_options = self.client.options("/api/score")
        self.assertEqual(res_options.status_code, 204)
        self.assertEqual(res_options.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("POST", res_options.headers.get("Access-Control-Allow-Methods", ""))

        res_post = self.client.post("/api/score", json=self.fixtures[0]["input_record"])
        self.assertEqual(res_post.headers.get("Access-Control-Allow-Origin"), "*")

    def test_08_frontend_typescript_contract_alignment(self):
        """Verify that frontend/src/types/scoring.ts declares all 26 required features."""
        ts_path = os.path.join(PROJECT_ROOT, "frontend", "src", "types", "scoring.ts")
        self.assertTrue(os.path.exists(ts_path), f"Missing {ts_path}")
        with open(ts_path, "r", encoding="utf-8") as f:
            ts_code = f.read()

        for feat in ALL_REQUIRED_FEATURES:
            self.assertIn(feat, ts_code, f"Feature {feat} missing from TypeScript contract!")


if __name__ == "__main__":
    unittest.main()
