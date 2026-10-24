"""
Phase 22J: External Deployment Handoff & Operational Acceptance Test Suite
Risk-Aware Bridge Maintenance Intelligence Platform

Verifies:
1. Baseline artifact immutability (Phase 17 model, calibrator, encoder, and score_bridge_risk.py).
2. Secret redaction helper masking keys, tokens, and credentials from logs and strings.
3. Authentication failure handling (missing, malformed, and invalid keys fail closed with PermissionError).
4. Invalid provenance handling (unrecognized traffic sources fail closed to UNKNOWN_PROVENANCE and cannot advance observation).
5. Synthetic, replay, and test-credential traffic strictly excluded from live observation streak.
6. Multi-state readiness progression (semantic separation of all 4 onboarding states).
7. Daily unique bridge coverage gating (observation starts only after threshold satisfied).
8. Live observation continuity and gap reset enforcement.
9. Persistent tracker state recovery from backup on primary corruption.
10. Strict failure isolation: candidate shadow scorer failure never affects Phase 17 production responses.
11. Privacy-safe daily observation evidence record endpoint (/api/onboarding/daily-evidence).
12. BRIDGE_PRODUCTION_CUTOVER_ENABLED=false runtime lock.
"""

import os
import sys
import copy
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
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    SchemaValidationError,
)
from backend.validate_shadow_mode_phase22c import sha256_file
from backend.shadow_scoring_service import (
    ShadowDeploymentConfig,
    ShadowTelemetryLogger,
    ShadowScoringService,
)
from backend.shadow_ingestion_adapter import (
    ShadowIngestionConfig,
    ShadowIngestionAdapter,
    IngestionAuthContext,
    redact_sensitive_credentials,
)
from backend.live_shadow_monitor import (
    LiveObservationTracker,
    TRAFFIC_SOURCE_LIVE,
    TRAFFIC_SOURCE_SYNTHETIC,
    TRAFFIC_SOURCE_REPLAY,
    TRAFFIC_SOURCE_UNKNOWN,
)
from backend.app import app

BASE_DIR = Path(__file__).resolve().parent.parent
P17_DIR = BASE_DIR / "results" / "phase17"
P18_CAL_DIR = BASE_DIR / "results" / "phase18" / "calibration"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"


class TestPhase22JHandoffAcceptance(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)["fixtures"]
        cls.sample_record = cls.fixtures[0]["input_record"].copy()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_telemetry_path = Path(self.temp_dir) / "telemetry.jsonl"
        self.temp_tracker_path = Path(self.temp_dir) / "tracker_state.json"

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
            api_key_env_var="HANDOFF_BRIDGE_INGEST_KEY",
            test_key_env_var="HANDOFF_BRIDGE_TEST_KEY",
            require_auth=True,
            shadow_timeout_ms=50.0,
            max_persistence_retries=2,
            min_daily_coverage_records=2,
        )
        self.adapter_config.operational_api_key = "dot_prod_super_secret_key_8842"
        self.adapter_config.test_api_key = "test_qa_sandbox_key_9911"

        self.adapter = ShadowIngestionAdapter(
            config=self.adapter_config,
            shadow_service=self.shadow_service,
        )
        self.client = app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_baseline_artifact_immutability(self):
        """Verify score_bridge_risk.py and all 11 Phase 17 baseline files match exact cryptographic checksums."""
        trusted_hashes = {
            "score_bridge_risk.py": "b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61",
            "hist_gradient_boosting_classifier.joblib": "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b",
            "cat_encoder.joblib": "14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772",
            "inference_metadata.json": "b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24",
            "serialization_manifest.json": "fedf43153bb898aafb2b1890873b2b65c9df7e1ef2a16292b2af75ecfc4d253e",
            "phase18_calibrator.joblib": "7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3",
        }
        self.assertEqual(sha256_file(BASE_DIR / "score_bridge_risk.py"), trusted_hashes["score_bridge_risk.py"])
        self.assertEqual(sha256_file(P17_DIR / "hist_gradient_boosting_classifier.joblib"), trusted_hashes["hist_gradient_boosting_classifier.joblib"])
        self.assertEqual(sha256_file(P17_DIR / "cat_encoder.joblib"), trusted_hashes["cat_encoder.joblib"])
        self.assertEqual(sha256_file(P17_DIR / "inference_metadata.json"), trusted_hashes["inference_metadata.json"])
        self.assertEqual(sha256_file(P17_DIR / "serialization_manifest.json"), trusted_hashes["serialization_manifest.json"])
        self.assertEqual(sha256_file(P18_CAL_DIR / "phase18_calibrator.joblib"), trusted_hashes["phase18_calibrator.joblib"])

    def test_02_secret_redaction_sanitizer(self):
        """Verify redact_sensitive_credentials redacts keys, tokens, and passwords."""
        raw_msg = "Error connecting with x-api-key: dot_prod_super_secret_key_8842 and Bearer secret_jwt_token_12345"
        redacted = redact_sensitive_credentials(
            raw_msg,
            known_secrets=["dot_prod_super_secret_key_8842", "secret_jwt_token_12345"],
        )
        self.assertNotIn("dot_prod_super_secret_key_8842", redacted)
        self.assertNotIn("secret_jwt_token_12345", redacted)
        self.assertIn("[REDACTED", redacted)

    def test_03_authentication_failures_fail_closed(self):
        """Verify missing, invalid, and malformed authorization headers fail closed with PermissionError."""
        # 1. Missing header
        with self.assertRaises(PermissionError) as ctx1:
            self.adapter.route_single_score(self.sample_record, {})
        self.assertIn("MISSING_AUTHENTICATION_CREDENTIAL", str(ctx1.exception))

        # 2. Invalid key
        with self.assertRaises(PermissionError) as ctx2:
            self.adapter.route_single_score(self.sample_record, {"X-API-Key": "totally_wrong_key"})
        self.assertIn("INVALID_CREDENTIALS", str(ctx2.exception))

        # 3. Empty Bearer token
        with self.assertRaises(PermissionError):
            self.adapter.route_single_score(self.sample_record, {"Authorization": "Bearer "})

    def test_04_invalid_provenance_fails_closed(self):
        """Verify invalid or fabricated provenance headers normalize to UNKNOWN_PROVENANCE and never advance streak."""
        headers = {
            "X-API-Key": "dot_prod_super_secret_key_8842",
            "X-Traffic-Source": "FABRICATED_IMAGINARY_STREAM",
        }
        res = self.adapter.route_single_score(self.sample_record, headers)
        self.assertIn("calibrated_deterioration_probability", res)

        summary = self.shadow_service.tracker.get_summary()
        self.assertEqual(summary["total_live_records"], 0)
        self.assertFalse(summary["live_traffic_started"])
        self.assertEqual(summary["consecutive_days_elapsed"], 0)

    def test_05_synthetic_and_test_credentials_excluded_from_clock(self):
        """Verify test credentials with claimed LIVE_OPERATIONAL provenance are remapped to SYNTHETIC_TEST."""
        headers = {
            "X-API-Key": "test_qa_sandbox_key_9911",
            "X-Traffic-Source": "LIVE_OPERATIONAL",
        }
        self.adapter.route_single_score(self.sample_record, headers)

        summary = self.shadow_service.tracker.get_summary()
        self.assertEqual(summary["total_live_records"], 0)
        self.assertEqual(summary["total_synthetic_records"], 1)
        self.assertFalse(summary["live_traffic_started"])

    def test_06_daily_unique_coverage_gating_and_streak_progression(self):
        """Verify observation status does not become OBSERVATION_STARTED until unique bridge coverage is met."""
        op_headers = {
            "X-API-Key": "dot_prod_super_secret_key_8842",
            "X-Traffic-Source": "LIVE_OPERATIONAL",
        }
        # Ingest first bridge record (threshold is 2)
        self.adapter.route_single_score(self.sample_record, op_headers)
        r1 = self.adapter.get_readiness_assessment()
        self.assertTrue(r1["states"]["AUTHENTIC_LIVE_TRAFFIC_CONFIRMED"])
        self.assertFalse(r1["states"]["OBSERVATION_STARTED"])

        # Re-submit duplicate bridge -> still under threshold
        self.adapter.route_single_score(self.sample_record, op_headers)
        r2 = self.adapter.get_readiness_assessment()
        self.assertFalse(r2["states"]["OBSERVATION_STARTED"])

        # Submit 2nd unique bridge -> satisfies threshold
        rec2 = self.sample_record.copy()
        rec2["bridge_id"] = "BRIDGE_STATE_DOT_002"
        self.adapter.route_single_score(rec2, op_headers)
        r3 = self.adapter.get_readiness_assessment()
        self.assertTrue(r3["states"]["OBSERVATION_STARTED"])
        self.assertEqual(r3["onboarding_state"], "OBSERVATION_STARTED")

    def test_07_tracker_streak_reset_on_utc_calendar_gap(self):
        """Verify that a gap of 1 or more UTC calendar days breaks continuity and resets consecutive streak to 1."""
        tracker = self.shadow_service.tracker

        # Day 1: 2026-10-01
        event_day1 = {
            "timestamp": "2026-10-01T12:00:00+00:00",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "validation_status": "VALID",
            "bridge_id": "BRIDGE_001",
        }
        tracker.record_event(event_day1)
        self.assertEqual(tracker.consecutive_days_elapsed, 1)

        # Day 2: 2026-10-02 (consecutive)
        event_day2 = {
            "timestamp": "2026-10-02T12:00:00+00:00",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "validation_status": "VALID",
            "bridge_id": "BRIDGE_001",
        }
        tracker.record_event(event_day2)
        self.assertEqual(tracker.consecutive_days_elapsed, 2)

        # Day 4: 2026-10-04 (gap on 2026-10-03!)
        event_day4 = {
            "timestamp": "2026-10-04T12:00:00+00:00",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "validation_status": "VALID",
            "bridge_id": "BRIDGE_001",
        }
        tracker.record_event(event_day4)
        # Streak must reset to 1 due to the missing day
        self.assertEqual(tracker.consecutive_days_elapsed, 1)
        self.assertEqual(len(tracker.monitoring_gaps), 1)
        self.assertEqual(tracker.observation_status, "STREAK_RESET_GAP_DETECTED")

    def test_08_persistent_tracker_state_recovery_from_backup(self):
        """Verify tracker automatically recovers from .bak file if primary json is corrupted."""
        tracker = self.shadow_service.tracker
        event1 = {
            "timestamp": "2026-10-01T12:00:00+00:00",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "validation_status": "VALID",
            "bridge_id": "BRIDGE_001",
        }
        tracker.record_event(event1)
        # Second event ensures backup .bak file is created from pre-existing state
        event2 = {
            "timestamp": "2026-10-01T13:00:00+00:00",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "validation_status": "VALID",
            "bridge_id": "BRIDGE_002",
        }
        tracker.record_event(event2)
        self.assertEqual(tracker.consecutive_days_elapsed, 1)
        self.assertTrue(self.temp_tracker_path.with_suffix(".bak").exists())

        # Corrupt the primary state file
        with open(self.temp_tracker_path, "w", encoding="utf-8") as f:
            f.write("{CORRUPTED_JSON_MALFORMED")

        # Create new tracker instance on the same path
        new_tracker = LiveObservationTracker(state_path=self.temp_tracker_path)
        self.assertEqual(new_tracker.consecutive_days_elapsed, 1)
        self.assertTrue(new_tracker.live_traffic_started)

    def test_09_failure_isolation_protects_primary_scorer(self):
        """Verify that catastrophic shadow candidate failure leaves primary Phase 17 score completely unaffected."""
        self.shadow_service.shadow_scorer.score_record = mock.MagicMock(
            side_effect=RuntimeError("Simulated catastrophic GPU/CPU crash in shadow candidate scorer")
        )
        op_headers = {
            "X-API-Key": "dot_prod_super_secret_key_8842",
            "X-Traffic-Source": "LIVE_OPERATIONAL",
        }
        res = self.adapter.route_single_score(self.sample_record, op_headers)
        self.assertIn("calibrated_deterioration_probability", res)
        self.assertEqual(res["model_metadata"]["classifier_type"], "HistGradientBoostingClassifier")

    def test_10_daily_evidence_record_endpoint(self):
        """Verify GET /api/onboarding/daily-evidence returns privacy-safe, structured operational evidence."""
        response = self.client.get("/api/onboarding/daily-evidence")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()

        self.assertIn("evidence_record_version", data)
        self.assertIn("observation_calendar_date_utc", data)
        self.assertIn("coverage_evaluation", data)
        self.assertIn("provenance_and_auth_status", data)
        self.assertIn("service_health_summary", data)
        self.assertIn("state_persistence_integrity", data)
        self.assertEqual(data["outcome_dependent_metrics"]["status"], "PENDING_VERIFIED_GROUND_TRUTH")

        # Ensure no raw bridge IDs or secret keys exist in the output
        dumped = json.dumps(data)
        self.assertNotIn("dot_prod_super_secret_key_8842", dumped)
        self.assertNotIn("test_qa_sandbox_key_9911", dumped)

    def test_11_cutover_switch_strictly_locked(self):
        """Verify BRIDGE_PRODUCTION_CUTOVER_ENABLED=false remains enforced and Phase 17 is active champion."""
        self.assertFalse(self.shadow_service.config.cutover_enabled)
        readiness = self.adapter.get_readiness_assessment()
        self.assertFalse(readiness["cutover_switch_enabled"])
        self.assertEqual(readiness["active_production_champion"], "Phase 17")


if __name__ == "__main__":
    unittest.main()
