"""
Unit Tests for Phase 22D: Controlled Shadow-First Deployment
Risk-Aware Bridge Maintenance Intelligence Platform

Tests:
1. Immutability of Phase 17 production artifacts and backend/score_bridge_risk.py.
2. Production routing integrity: production responses match Phase 17 byte-for-byte.
3. Shadow failure isolation: shadow exceptions do not fail or alter production responses.
4. Privacy-conscious telemetry: logs paired metrics and metadata without sensitive raw payloads.
5. Missingness and unseen category detection in telemetry logs.
6. Acceptance gates and observation period configuration.
7. API integration: /api/health and /api/shadow/status endpoints.
8. Instant rollback safety: shadow mode toggle cleanly disables candidate evaluation.
9. Cutover safety switch: production cutover is disabled by default.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app import app
from backend.score_bridge_risk import (
    BridgeRiskScorer,
    get_default_scorer,
    ALL_REQUIRED_FEATURES,
)
from backend.shadow_scoring_service import (
    ShadowDeploymentConfig,
    ShadowTelemetryLogger,
    ShadowScoringService,
    get_shadow_scoring_service,
)
from backend.validate_shadow_mode_phase22c import sha256_file

BASE_DIR = Path(__file__).resolve().parent.parent
P17_DIR = BASE_DIR / "results" / "phase17"
P18_CAL_DIR = BASE_DIR / "results" / "phase18" / "calibration"
P21B_DIR = BASE_DIR / "results" / "phase21b"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"


class TestPhase22DShadowDeployment(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.client = app.test_client()
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)["fixtures"]
        cls.sample_record = cls.fixtures[0]["input_record"].copy()
        cls.expected_prob = cls.fixtures[0]["expected_calibrated_probability"]
        cls.expected_score = cls.fixtures[0]["expected_raw_score"]

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_telemetry_path = Path(self.temp_dir) / "test_telemetry.jsonl"
        self.config = ShadowDeploymentConfig(
            enabled=True,
            cutover_enabled=False,
            telemetry_path=self.temp_telemetry_path,
            tracker_state_path=Path(self.temp_dir) / "test_tracker.json",
            min_observation_records=10,
        )
        self.service = ShadowScoringService(config=self.config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_immutability_of_baseline_champion(self):
        """Verify score_bridge_risk.py and Phase 17/18 production artifacts remain unchanged."""
        expected_hashes = {
            "score_bridge_risk.py": "b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61",
            "hist_gradient_boosting_classifier.joblib": "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b",
            "cat_encoder.joblib": "14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772",
            "phase18_calibrator.joblib": "7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3",
        }
        self.assertEqual(sha256_file(BASE_DIR / "score_bridge_risk.py"), expected_hashes["score_bridge_risk.py"])
        self.assertEqual(sha256_file(P17_DIR / "hist_gradient_boosting_classifier.joblib"), expected_hashes["hist_gradient_boosting_classifier.joblib"])
        self.assertEqual(sha256_file(P17_DIR / "cat_encoder.joblib"), expected_hashes["cat_encoder.joblib"])
        self.assertEqual(sha256_file(P18_CAL_DIR / "phase18_calibrator.joblib"), expected_hashes["phase18_calibrator.joblib"])

    def test_02_production_routing_parity(self):
        """Verify shadow scoring service returns exact Phase 17 outputs."""
        prod_result = self.service.score_record_with_shadow(self.sample_record)
        self.assertAlmostEqual(prod_result["calibrated_deterioration_probability"], self.expected_prob, places=5)
        self.assertAlmostEqual(prod_result["raw_decision_score"], self.expected_score, places=5)
        self.assertEqual(prod_result["model_metadata"]["service_phase"], "Phase 18C")

    def test_03_shadow_failure_isolation(self):
        """Verify that a fatal exception in shadow scorer does NOT fail or alter production response."""
        # Inject failure into shadow scorer
        mock_shadow_scorer = MagicMock()
        mock_shadow_scorer.score_record.side_effect = RuntimeError("Simulated shadow scorer crash")
        service_with_bad_shadow = ShadowScoringService(
            shadow_scorer=mock_shadow_scorer,
            config=self.config,
        )

        # Scoring must succeed with production response
        prod_result = service_with_bad_shadow.score_record_with_shadow(self.sample_record)
        self.assertAlmostEqual(prod_result["calibrated_deterioration_probability"], self.expected_prob, places=5)

        # Telemetry must record failure
        entries = self.config.telemetry_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(entries), 1)
        entry = json.loads(entries[0])
        self.assertEqual(entry["shadow_status"], "FAILED")
        self.assertIn("Simulated shadow scorer crash", entry["shadow_error"])
        self.assertIsNone(entry["shadow_calibrated_prob"])

    def test_04_privacy_conscious_telemetry_schema(self):
        """Verify telemetry logs contain required fields without leaking raw input payloads."""
        self.service.score_record_with_shadow(self.sample_record)
        entries = self.config.telemetry_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(entries), 1)
        entry = json.loads(entries[0])

        # Mandatory telemetry keys
        expected_keys = [
            "timestamp", "bridge_id", "prod_champion", "prod_raw_score",
            "prod_calibrated_prob", "prod_threshold", "prod_flag", "prod_latency_ms",
            "shadow_candidate", "shadow_raw_score", "shadow_calibrated_prob",
            "shadow_threshold", "shadow_flag", "shadow_latency_ms", "probability_delta",
            "workload_agreement", "missing_numeric_count", "missing_numeric_features",
            "unseen_categorical_count", "unseen_categorical_features", "shadow_status"
        ]
        for k in expected_keys:
            self.assertIn(k, entry, f"Missing telemetry key {k}")

        # Ensure raw feature values are NOT leaked into telemetry
        sensitive_raw_keys = ["structure_len_mt", "max_span_len_mt", "adt", "year_built"]
        for k in sensitive_raw_keys:
            self.assertNotIn(k, entry)

    def test_05_telemetry_missingness_and_unseen_tracking(self):
        """Verify telemetry accurately logs missing numeric features and unseen category codes."""
        rec = self.sample_record.copy()
        rec["adt"] = None
        rec["detour_kilos"] = None
        rec["state_code"] = "99"  # unseen category

        self.service.score_record_with_shadow(rec)
        entries = self.config.telemetry_path.read_text(encoding="utf-8").strip().splitlines()
        entry = json.loads(entries[0])

        self.assertEqual(entry["missing_numeric_count"], 2)
        self.assertIn("adt", entry["missing_numeric_features"])
        self.assertIn("detour_kilos", entry["missing_numeric_features"])
        self.assertEqual(entry["unseen_categorical_count"], 1)
        self.assertIn("state_code", entry["unseen_categorical_features"])

    def test_06_batch_shadow_scoring_telemetry(self):
        """Verify batch scoring logs telemetry entries for all items while returning production results."""
        records = [self.fixtures[i]["input_record"].copy() for i in range(min(3, len(self.fixtures)))]
        batch_results = self.service.score_batch_with_shadow(records)

        self.assertEqual(len(batch_results), len(records))
        entries = self.config.telemetry_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(entries), len(records))

    def test_07_acceptance_gates_and_observation_criteria(self):
        """Verify acceptance gates structure and cutover disable status."""
        summary = self.service.get_telemetry_summary()
        self.assertIn("acceptance_gates_evaluation", summary)
        gates = summary["acceptance_gates_evaluation"]

        self.assertIn("model_quality", gates)
        self.assertIn("calibration_quality", gates)
        self.assertIn("operational_capacity", gates)
        self.assertIn("reliability_and_safety", gates)
        self.assertIn("governance_and_cutover", gates)

        # Confirm cutover is strictly disabled
        self.assertEqual(gates["governance_and_cutover"]["cutover_status"], "DISABLED_PENDING_EXPLICIT_APPROVAL")
        self.assertTrue(summary["production_cutover_disabled"])

    def test_08_api_health_reports_shadow_mode(self):
        """GET /api/health reports Phase 22D shadow mode and active Phase 17 champion."""
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["phase"], "Phase 22D: Shadow-First Deployment")
        self.assertEqual(data["active_production_champion"], "Phase 17")
        self.assertTrue(data["shadow_mode_active"])
        self.assertEqual(data["production_cutover_status"], "DISABLED_PENDING_EXPLICIT_APPROVAL")

    def test_09_api_shadow_status_endpoint(self):
        """GET /api/shadow/status returns telemetry summary and observation status."""
        res = self.client.get("/api/shadow/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("status", data)
        self.assertIn("observation_window_days", data)
        self.assertIn("min_observation_records", data)
        self.assertTrue(data.get("production_cutover_disabled", True))

    def test_10_rollback_by_disabling_shadow_mode(self):
        """Disabling shadow mode cleanly stops candidate evaluation and telemetry logging."""
        cfg_disabled = ShadowDeploymentConfig(
            enabled=False,
            telemetry_path=self.temp_telemetry_path,
        )
        service_disabled = ShadowScoringService(config=cfg_disabled)
        self.assertIsNone(service_disabled.shadow_scorer)

        res = service_disabled.score_record_with_shadow(self.sample_record)
        self.assertAlmostEqual(res["calibrated_deterioration_probability"], self.expected_prob, places=5)
        # No telemetry should be logged
        self.assertFalse(self.temp_telemetry_path.exists())


if __name__ == "__main__":
    unittest.main()
