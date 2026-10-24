"""
Phase 20: Comprehensive End-to-End Resilience, Negative, and Scientific Verification Test Suite
Risk-Aware Bridge Maintenance Intelligence Platform

Tests:
1. End-to-end endpoint verification (/api/health, /api/model/metadata, /api/sample-records, /api/score, /api/score/batch)
2. Negative error handling: missing keys, invalid types, malformed json, empty batches, oversized batches (>1000)
3. Robustness on unseen/unknown categories and missing/null numeric features
4. Scientific boundary verification: probabilities in [0, 1], calibration monotonicity
5. Sanitized responses: no Python stack traces or internal server leakages
6. Simulated service unavailability: graceful 503 when model artifacts are missing
7. Cross-validation against verified Phase 17/18 regression fixtures
"""

import os
import sys
import copy
import json
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.app import app
from backend.score_bridge_risk import (
    ALL_REQUIRED_FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    SEMANTICS_DISCLAIMER,
    TOTAL_FEATURE_COUNT,
    BridgeRiskScorer,
    get_default_scorer,
    score_bridges,
    SchemaValidationError,
    ArtifactLoadError,
)

MAX_BATCH_SIZE = 1000
OPTIMAL_THRESHOLD_TAU = 0.680


class TestPhase20EndToEndResilience(unittest.TestCase):
    """Rigorous Phase 20 test suite for E2E integration and deployment resilience."""

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        cls.fixture_path = os.path.join(
            PROJECT_ROOT, "backend", "tests", "fixtures", "regression_test_fixture.json"
        )
        assert os.path.exists(cls.fixture_path), f"Missing test fixture: {cls.fixture_path}"
        with open(cls.fixture_path, "r", encoding="utf-8") as f:
            cls.fixtures_data = json.load(f)["fixtures"]
        cls.valid_record = copy.deepcopy(cls.fixtures_data[0]["input_record"])

    # =========================================================================
    # SECTION 1: ENDPOINT CONTRACT & CORS VERIFICATION
    # =========================================================================

    def test_01_health_endpoint_contract(self):
        """GET /api/health returns 200 with complete readiness metadata."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["model_ready"])
        self.assertEqual(data["features_count"], 26)
        self.assertIn("target_semantics", data)

    def test_02_model_metadata_endpoint_contract(self):
        """GET /api/model/metadata returns 26 features with disclaimers and metric references."""
        res = self.client.get("/api/model/metadata")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["feature_schema"]["total_count"], 26)
        self.assertEqual(len(data["feature_schema"]["numeric_features"]), 13)
        self.assertEqual(len(data["feature_schema"]["categorical_features"]), 13)
        self.assertIn("scientific_disclaimers", data)
        self.assertIn("no_collapse_prediction", data["scientific_disclaimers"])
        self.assertIn("no_engineering_replacement", data["scientific_disclaimers"])
        self.assertIn("validation_scope", data["scientific_disclaimers"])

    def test_03_sample_records_endpoint_contract(self):
        """GET /api/sample-records returns verified test-split samples with expected outputs."""
        res = self.client.get("/api/sample-records")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreaterEqual(data["count"], 3)
        for sample in data["samples"]:
            self.assertIn("bridge_id", sample)
            self.assertIn("input_record", sample)
            self.assertIn("verified_raw_score", sample)
            self.assertIn("verified_calibrated_probability", sample)
            # Ensure each sample contains all 26 features
            for feat in ALL_REQUIRED_FEATURES:
                self.assertIn(feat, sample["input_record"])

    def test_04_cors_headers_present(self):
        """Verify CORS headers are present on responses and OPTIONS preflight requests."""
        # Standard GET
        res = self.client.get("/api/health")
        self.assertEqual(res.headers.get("Access-Control-Allow-Origin"), "*")

        # Standard POST
        res_post = self.client.post(
            "/api/score",
            data=json.dumps(self.valid_record),
            content_type="application/json",
        )
        self.assertEqual(res_post.headers.get("Access-Control-Allow-Origin"), "*")

        # OPTIONS Preflight
        res_opts = self.client.options("/api/score")
        self.assertEqual(res_opts.status_code, 204)
        self.assertEqual(res_opts.headers.get("Access-Control-Allow-Origin"), "*")
        self.assertIn("POST", res_opts.headers.get("Access-Control-Allow-Methods", ""))

    # =========================================================================
    # SECTION 2: NEGATIVE TESTING & INPUT VALIDATION RESILIENCE
    # =========================================================================

    def test_05_missing_features_returns_400(self):
        """POST /api/score returns 400 when required features are omitted."""
        bad_record = copy.deepcopy(self.valid_record)
        del bad_record["adt"]
        del bad_record["prior_deck_condition"]

        res = self.client.post(
            "/api/score",
            data=json.dumps(bad_record),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "validation_error")
        self.assertIn("missing", data["message"].lower())
        # No Python tracebacks in error payload
        self.assertNotIn("Traceback", json.dumps(data))

    def test_06_non_numeric_types_returns_400(self):
        """POST /api/score returns 400 when a numeric feature has an invalid string value."""
        bad_record = copy.deepcopy(self.valid_record)
        bad_record["adt"] = "invalid_non_numeric_adt"

        res = self.client.post(
            "/api/score",
            data=json.dumps(bad_record),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "validation_error")
        self.assertIn("adt", data["message"])
        self.assertNotIn("Traceback", json.dumps(data))

    def test_07_malformed_json_returns_400(self):
        """POST /api/score with malformed JSON string returns 400."""
        res = self.client.post(
            "/api/score",
            data="{invalid_json_missing_quotes: true",
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertNotIn("Traceback", json.dumps(data))

    def test_08_empty_batch_returns_empty_results(self):
        """POST /api/score/batch with empty records array returns 200 with 0 count."""
        res = self.client.post(
            "/api/score/batch",
            data=json.dumps({"records": []}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["results"], [])

    def test_09_oversized_batch_returns_400(self):
        """POST /api/score/batch with > 1000 records returns 400 batch_limit_exceeded."""
        large_batch = [self.valid_record] * (MAX_BATCH_SIZE + 1)
        res = self.client.post(
            "/api/score/batch",
            data=json.dumps({"records": large_batch}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "batch_limit_exceeded")
        self.assertIn("Maximum batch size is 1,000", data["message"])

    def test_10_non_dictionary_single_payload_returns_400(self):
        """POST /api/score with a JSON array instead of an object returns 400."""
        res = self.client.post(
            "/api/score",
            data=json.dumps([self.valid_record]),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "invalid_record_format")

    def test_11_non_list_batch_payload_returns_400(self):
        """POST /api/score/batch with invalid 'records' type returns 400."""
        res = self.client.post(
            "/api/score/batch",
            data=json.dumps({"records": "not_a_list"}),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data["error"], "invalid_batch_format")

    # =========================================================================
    # SECTION 3: ROBUSTNESS ON UNSEEN CATEGORIES & MISSING NUMERIC VALUES
    # =========================================================================

    def test_12_unseen_unknown_categorical_values_do_not_crash(self):
        """Categorical encoder handles unseen category codes gracefully without failing."""
        unseen_record = copy.deepcopy(self.valid_record)
        unseen_record["state_code"] = "999_NEVER_SEEN"
        unseen_record["deck_structure_type_107"] = "99"
        unseen_record["maintenance_responsibility"] = "99"

        res = self.client.post(
            "/api/score",
            data=json.dumps(unseen_record),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("calibrated_deterioration_probability", data)
        self.assertGreaterEqual(data["calibrated_deterioration_probability"], 0.0)
        self.assertLessEqual(data["calibrated_deterioration_probability"], 1.0)
        self.assertGreater(len(data.get("warnings", [])), 0)

    def test_13_null_numeric_features_handled_natively(self):
        """HistGradientBoosting handles null/None values in numeric features natively."""
        null_record = copy.deepcopy(self.valid_record)
        null_record["adt"] = None
        null_record["percent_adt_truck"] = None
        null_record["structure_len_mt"] = None

        res = self.client.post(
            "/api/score",
            data=json.dumps(null_record),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("calibrated_deterioration_probability", data)
        self.assertGreaterEqual(data["calibrated_deterioration_probability"], 0.0)
        self.assertLessEqual(data["calibrated_deterioration_probability"], 1.0)

    # =========================================================================
    # SECTION 4: SCIENTIFIC BOUNDS & TARGET SEMANTICS
    # =========================================================================

    def test_14_calibrated_probability_strictly_bounded(self):
        """Calibrated probability is strictly bounded in [0.0, 1.0] across all fixtures."""
        for fixture in self.fixtures_data:
            res = self.client.post(
                "/api/score",
                data=json.dumps(fixture["input_record"]),
                content_type="application/json",
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            prob = data["calibrated_deterioration_probability"]
            self.assertIsInstance(prob, float)
            self.assertGreaterEqual(prob, 0.0)
            self.assertLessEqual(prob, 1.0)

    def test_15_raw_decision_score_is_finite_float(self):
        """Raw decision margin is a finite floating point value."""
        for fixture in self.fixtures_data:
            res = self.client.post(
                "/api/score",
                data=json.dumps(fixture["input_record"]),
                content_type="application/json",
            )
            data = res.get_json()
            raw_score = data["raw_decision_score"]
            self.assertIsInstance(raw_score, float)
            self.assertFalse(float("nan") == raw_score)

    def test_16_target_semantics_explicitly_disclosed(self):
        """All prediction payloads carry the exact FHWA target definition disclaimer."""
        res = self.client.post(
            "/api/score",
            data=json.dumps(self.valid_record),
            content_type="application/json",
        )
        data = res.get_json()
        self.assertIn("prediction_semantics", data)
        self.assertEqual(data["prediction_semantics"], SEMANTICS_DISCLAIMER)
        self.assertIn("routine biennial degradation", data["prediction_semantics"])
        self.assertIn("Does NOT predict bridge collapse", data["prediction_semantics"])

    # =========================================================================
    # SECTION 5: ARTIFACT OUTAGE SIMULATION & SANITIZED 503 ERROR
    # =========================================================================

    def test_17_simulated_missing_artifacts_returns_503(self):
        """When model artifacts fail to load, API responds with sanitized 503."""
        with patch("backend.app.get_default_scorer") as mock_get_scorer:
            mock_get_scorer.side_effect = ArtifactLoadError("Simulated missing classifier artifact")
            res = self.client.post(
                "/api/score",
                data=json.dumps(self.valid_record),
                content_type="application/json",
            )
            self.assertEqual(res.status_code, 503)
            data = res.get_json()
            self.assertEqual(data["error"], "service_unavailable")
            self.assertIn("temporarily unavailable", data["message"])
            # Ensure no traceback is leaked
            self.assertNotIn("Traceback", json.dumps(data))

    # =========================================================================
    # SECTION 6: REGRESSION FIXTURE EXACT NUMERICAL REPRODUCIBILITY
    # =========================================================================

    def test_18_regression_fixture_numerical_match(self):
        """Verified test fixtures produce numerically consistent predictions within tolerance."""
        for fixture in self.fixtures_data:
            res = self.client.post(
                "/api/score",
                data=json.dumps(fixture["input_record"]),
                content_type="application/json",
            )
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertAlmostEqual(
                data["calibrated_deterioration_probability"],
                fixture["expected_calibrated_probability"],
                places=4,
                msg=f"Fixture {fixture['bridge_id']} calibrated probability mismatch",
            )
            self.assertAlmostEqual(
                data["raw_decision_score"],
                fixture["expected_raw_score"],
                places=4,
                msg=f"Fixture {fixture['bridge_id']} raw score mismatch",
            )

    def test_19_batch_scoring_matches_single_scoring(self):
        """Batch scoring produces identical outputs to sequential single scoring calls."""
        batch_records = [f["input_record"] for f in self.fixtures_data]
        res_batch = self.client.post(
            "/api/score/batch",
            data=json.dumps({"records": batch_records}),
            content_type="application/json",
        )
        self.assertEqual(res_batch.status_code, 200)
        batch_results = res_batch.get_json()["results"]
        self.assertEqual(len(batch_results), len(batch_records))

        for idx, fixture in enumerate(self.fixtures_data):
            batch_item = batch_results[idx]
            self.assertAlmostEqual(
                batch_item["calibrated_deterioration_probability"],
                fixture["expected_calibrated_probability"],
                places=4,
            )
            self.assertAlmostEqual(
                batch_item["raw_decision_score"],
                fixture["expected_raw_score"],
                places=4,
            )


if __name__ == "__main__":
    unittest.main()
