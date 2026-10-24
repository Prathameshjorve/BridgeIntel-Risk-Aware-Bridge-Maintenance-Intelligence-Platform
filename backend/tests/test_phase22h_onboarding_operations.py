"""
Phase 22H: Live Deployment Onboarding and Observation Operations Tests
Risk-Aware Bridge Maintenance Intelligence Platform

Tests:
1. Baseline artifact immutability (Phase 17 champion and score_bridge_risk.py).
2. Multi-state readiness progression (CONFIGURATION_READY, CONNECTION_VERIFIED, AUTHENTIC_LIVE_TRAFFIC_CONFIRMED, OBSERVATION_STARTED).
3. Authentication and authorization boundaries (unauthorized, test credential, operational credential).
4. Automated remapping of test credentials to SYNTHETIC_TEST provenance.
5. Daily coverage requirements gating (tracker advances only when minimum daily volume is satisfied).
6. Ingestion endpoint integration (/api/onboarding/readiness returns 200 with structured status).
7. Strict failure isolation (adapter traps shadow errors; primary scoring response always succeeds).
8. Bounded retries on transient logging failures.
9. Emergency rollback & safe shutdown behavior (BRIDGE_SHADOW_MODE_ENABLED=false).
10. Truthful reporting when live traffic is absent (NOT_STARTED, 0/30 days, cutover locked).
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from datetime import datetime, date, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.score_bridge_risk import (
    BridgeRiskScorer,
    get_default_scorer,
    ALL_REQUIRED_FEATURES,
)
from backend.shadow_scoring_service import (
    ShadowDeploymentConfig,
    ShadowTelemetryLogger,
    ShadowScoringService,
)
from backend.shadow_ingestion_adapter import (
    ShadowIngestionConfig,
    ShadowIngestionAdapter,
    IngestionAuthContext,
)
from backend.live_shadow_monitor import (
    TelemetryEventValidator,
    LiveObservationTracker,
    TRAFFIC_SOURCE_LIVE,
    TRAFFIC_SOURCE_REPLAY,
    TRAFFIC_SOURCE_SYNTHETIC,
)
from backend.validate_shadow_mode_phase22c import sha256_file
from backend.app import app

BASE_DIR = Path(__file__).resolve().parent.parent
P17_DIR = BASE_DIR / "results" / "phase17"
P18_CAL_DIR = BASE_DIR / "results" / "phase18" / "calibration"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"


class TestPhase22HOnboardingOperations(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)["fixtures"]
        cls.sample_record = cls.fixtures[0]["input_record"].copy()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_telemetry_path = Path(self.temp_dir) / "telemetry.jsonl"
        self.temp_tracker_path = Path(self.temp_dir) / "tracker_state.json"
        self.temp_cache_path = Path(self.temp_dir) / "event_id_cache.txt"

        self.shadow_config = ShadowDeploymentConfig(
            enabled=True,
            cutover_enabled=False,
            telemetry_path=self.temp_telemetry_path,
            tracker_state_path=self.temp_tracker_path,
            observation_window_days=30,
            min_observation_records=10,
        )
        self.shadow_service = ShadowScoringService(config=self.shadow_config)

        self.adapter_config = ShadowIngestionConfig(
            api_key_env_var="MOCK_BRIDGE_INGEST_KEY",
            test_key_env_var="MOCK_BRIDGE_TEST_KEY",
            require_auth=True,
            shadow_timeout_ms=50.0,
            max_persistence_retries=2,
            min_daily_coverage_records=2,
        )
        self.adapter_config.operational_api_key = "secret_op_key_dot_2026"
        self.adapter_config.test_api_key = "secret_test_key_internal"

        self.adapter = ShadowIngestionAdapter(
            config=self.adapter_config,
            shadow_service=self.shadow_service,
        )
        self.client = app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_baseline_immutability(self):
        """Verify score_bridge_risk.py and all Phase 17 baseline files remain 100% byte-for-byte identical."""
        expected_hashes = {
            "score_bridge_risk.py": "b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61",
            "hist_gradient_boosting_classifier.joblib": "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b",
            "cat_encoder.joblib": "14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772",
            "inference_metadata.json": "b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24",
            "serialization_manifest.json": "fedf43153bb898aafb2b1890873b2b65c9df7e1ef2a16292b2af75ecfc4d253e",
            "phase18_calibrator.joblib": "7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3",
        }
        self.assertEqual(sha256_file(BASE_DIR / "score_bridge_risk.py"), expected_hashes["score_bridge_risk.py"])
        self.assertEqual(sha256_file(P17_DIR / "hist_gradient_boosting_classifier.joblib"), expected_hashes["hist_gradient_boosting_classifier.joblib"])
        self.assertEqual(sha256_file(P17_DIR / "cat_encoder.joblib"), expected_hashes["cat_encoder.joblib"])
        self.assertEqual(sha256_file(P17_DIR / "inference_metadata.json"), expected_hashes["inference_metadata.json"])
        self.assertEqual(sha256_file(P17_DIR / "serialization_manifest.json"), expected_hashes["serialization_manifest.json"])
        self.assertEqual(sha256_file(P18_CAL_DIR / "phase18_calibrator.joblib"), expected_hashes["phase18_calibrator.joblib"])

    def test_02_readiness_state_progression(self):
        """Verify readiness states: starts at CONNECTION_VERIFIED; transitions after authentic live traffic."""
        readiness = self.adapter.get_readiness_assessment()
        self.assertTrue(readiness["states"]["CONFIGURATION_READY"])
        self.assertTrue(readiness["states"]["CONNECTION_VERIFIED"])
        self.assertFalse(readiness["states"]["AUTHENTIC_LIVE_TRAFFIC_CONFIRMED"])
        self.assertFalse(readiness["states"]["OBSERVATION_STARTED"])
        self.assertEqual(readiness["onboarding_state"], "CONNECTION_VERIFIED")

        # Ingest 1 record with operational auth
        headers = {
            "X-API-Key": "secret_op_key_dot_2026",
            "X-Traffic-Source": "LIVE_OPERATIONAL",
        }
        self.adapter.route_single_score(self.sample_record, headers)

        # Still need 2 unique records for min_daily_coverage_records=2
        readiness2 = self.adapter.get_readiness_assessment()
        self.assertTrue(readiness2["states"]["AUTHENTIC_LIVE_TRAFFIC_CONFIRMED"])
        self.assertFalse(readiness2["states"]["OBSERVATION_STARTED"])
        self.assertEqual(readiness2["onboarding_state"], "AUTHENTIC_LIVE_TRAFFIC_CONFIRMED")

        # Ingest 2nd unique bridge record
        rec2 = self.sample_record.copy()
        rec2["bridge_id"] = "BRIDGE_UNIQUE_002"
        self.adapter.route_single_score(rec2, headers)

        # Now OBSERVATION_STARTED must be True
        readiness3 = self.adapter.get_readiness_assessment()
        self.assertTrue(readiness3["states"]["OBSERVATION_STARTED"])
        self.assertEqual(readiness3["onboarding_state"], "OBSERVATION_STARTED")

    def test_03_authentication_and_authorization_boundaries(self):
        """Verify missing/invalid keys are rejected with PermissionError, while valid keys succeed."""
        # 1. Missing Key
        with self.assertRaises(PermissionError):
            self.adapter.route_single_score(self.sample_record, {})

        # 2. Invalid Key
        with self.assertRaises(PermissionError):
            self.adapter.route_single_score(self.sample_record, {"X-API-Key": "completely_wrong_key"})

        # 3. Valid Operational Key
        res = self.adapter.route_single_score(
            self.sample_record,
            {"X-API-Key": "secret_op_key_dot_2026"}
        )
        self.assertIn("calibrated_deterioration_probability", res)
        self.assertEqual(res["model_metadata"]["classifier_type"], "HistGradientBoostingClassifier")

    def test_04_test_credential_remapping_to_synthetic(self):
        """Verify that requests using test credentials have traffic_source automatically mapped to SYNTHETIC_TEST."""
        headers = {
            "X-API-Key": "secret_test_key_internal",
            "X-Traffic-Source": "LIVE_OPERATIONAL",  # Claiming live, but using test key!
        }
        self.adapter.route_single_score(self.sample_record, headers)

        # Tracker must have 0 live records and 1 synthetic record
        summary = self.shadow_service.tracker.get_summary()
        self.assertEqual(summary["total_live_records"], 0)
        self.assertEqual(summary["total_synthetic_records"], 1)
        self.assertFalse(summary["live_traffic_started"])

    def test_05_daily_coverage_requirements_gating(self):
        """Verify observation clock does not advance until documented minimum unique bridges threshold is satisfied."""
        # Config requires min 2 unique bridges per day
        self.assertEqual(self.adapter.config.min_daily_coverage_records, 2)
        headers = {"X-API-Key": "secret_op_key_dot_2026", "X-Traffic-Source": "LIVE_OPERATIONAL"}

        # First bridge
        self.adapter.route_single_score(self.sample_record, headers)
        readiness = self.adapter.get_readiness_assessment()
        self.assertFalse(readiness["states"]["OBSERVATION_STARTED"])

        # Second submission of SAME bridge (not unique)
        self.adapter.route_single_score(self.sample_record, headers)
        readiness = self.adapter.get_readiness_assessment()
        self.assertFalse(readiness["states"]["OBSERVATION_STARTED"])

        # Submission of SECOND UNIQUE bridge
        rec2 = self.sample_record.copy()
        rec2["bridge_id"] = "BRIDGE_UNIQUE_009"
        self.adapter.route_single_score(rec2, headers)
        readiness = self.adapter.get_readiness_assessment()
        self.assertTrue(readiness["states"]["OBSERVATION_STARTED"])

    def test_06_endpoint_onboarding_readiness(self):
        """Verify GET /api/onboarding/readiness returns 200 with complete readiness schema."""
        response = self.client.get("/api/onboarding/readiness")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIn("onboarding_state", data)
        self.assertIn("states", data)
        self.assertIn("CONFIGURATION_READY", data["states"])
        self.assertIn("CONNECTION_VERIFIED", data["states"])
        self.assertIn("AUTHENTIC_LIVE_TRAFFIC_CONFIRMED", data["states"])
        self.assertIn("OBSERVATION_STARTED", data["states"])
        self.assertEqual(data["active_production_champion"], "Phase 17")
        self.assertFalse(data["cutover_switch_enabled"])

    def test_07_failure_isolation(self):
        """Verify that if shadow candidate scorer raises an exception, primary scoring response still succeeds."""
        # Intentionally break shadow scorer
        self.shadow_service.shadow_scorer.score_record = mock.MagicMock(
            side_effect=RuntimeError("Simulated catastrophic shadow scorer crash")
        )
        headers = {"X-API-Key": "secret_op_key_dot_2026", "X-Traffic-Source": "LIVE_OPERATIONAL"}
        result = self.adapter.route_single_score(self.sample_record, headers)
        self.assertIn("calibrated_deterioration_probability", result)
        self.assertEqual(result["model_metadata"]["classifier_type"], "HistGradientBoostingClassifier")

    def test_08_bounded_retries(self):
        """Verify adapter bounded retry logic executes and succeeds on transient error."""
        call_count = [0]
        original_score = self.shadow_service.score_record_with_shadow

        def transient_failure(record, traffic_source=None):
            call_count[0] += 1
            if call_count[0] == 1:
                raise OSError("Simulated transient I/O lock blip")
            return original_score(record, traffic_source=traffic_source)

        self.shadow_service.score_record_with_shadow = transient_failure
        headers = {"X-API-Key": "secret_op_key_dot_2026"}
        res = self.adapter.route_single_score(self.sample_record, headers)
        self.assertEqual(call_count[0], 2)
        self.assertIn("calibrated_deterioration_probability", res)

    def test_09_emergency_rollback_safe_shutdown(self):
        """Verify disabling shadow mode via config/env immediately bypasses candidate evaluation."""
        self.shadow_service.config.enabled = False
        headers = {"X-API-Key": "secret_op_key_dot_2026"}
        res = self.adapter.route_single_score(self.sample_record, headers)
        self.assertIn("calibrated_deterioration_probability", res)
        # Telemetry should be empty because shadow mode was disabled
        self.assertFalse(self.temp_telemetry_path.exists())

    def test_10_truthful_unstarted_observation(self):
        """Verify that when no live traffic has been routed, status reports NOT_STARTED and cutover locked."""
        readiness = self.adapter.get_readiness_assessment()
        self.assertFalse(readiness["states"]["OBSERVATION_STARTED"])
        self.assertEqual(readiness["observation_coverage"]["consecutive_days_elapsed"], 0)
        self.assertFalse(readiness["cutover_switch_enabled"])
        self.assertEqual(readiness["outcome_dependent_metrics_status"], "PENDING_VERIFIED_GROUND_TRUTH")


if __name__ == "__main__":
    unittest.main()
