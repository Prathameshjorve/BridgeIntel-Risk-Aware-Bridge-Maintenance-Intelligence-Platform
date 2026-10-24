"""
Phase 22I: Live Observation Readiness & Operational Audit Test Suite
Risk-Aware Bridge Maintenance Intelligence Platform

Verifies:
1. Production baseline artifact immutability (score_bridge_risk.py and all Phase 17 artifacts).
2. Elimination of scikit-learn feature-name UserWarnings across production and shadow pipelines.
3. Feature order, count, and preprocessing consistency between Phase 17 and Phase 21B.
4. Strict test-credential and unauthenticated request isolation to synthetic provenance.
5. Authentic live operational traffic requirement for advancing consecutive-day observation streak.
6. Multi-state readiness progression (CONFIGURATION_READY, CONNECTION_VERIFIED, AUTHENTIC_LIVE_TRAFFIC_CONFIRMED, OBSERVATION_STARTED).
7. Gating of observation start on daily unique bridge coverage thresholds.
8. Strict enforcement of BRIDGE_PRODUCTION_CUTOVER_ENABLED=false.
9. Ground-truth outcome-dependent metrics remain PENDING_VERIFIED_GROUND_TRUTH.
"""

import os
import sys
import copy
import json
import shutil
import tempfile
import warnings
import unittest
from unittest import mock
from pathlib import Path
import numpy as np
import pandas as pd

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
from backend.validate_shadow_mode_phase22c import (
    ShadowBridgeRiskScorer,
    sha256_file,
    CATEGORICAL_FEATURES as SHADOW_CATS,
    NUMERIC_FEATURES as SHADOW_NUMS,
    ALL_REQUIRED_FEATURES as SHADOW_ALL,
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
    LiveObservationTracker,
    TRAFFIC_SOURCE_LIVE,
    TRAFFIC_SOURCE_SYNTHETIC,
    TRAFFIC_SOURCE_REPLAY,
)
from backend.app import app

BASE_DIR = Path(__file__).resolve().parent.parent
P17_DIR = BASE_DIR / "results" / "phase17"
P18_CAL_DIR = BASE_DIR / "results" / "phase18" / "calibration"
P21B_DIR = BASE_DIR / "results" / "phase21b"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"


class TestPhase22IReadinessAudit(unittest.TestCase):

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
            api_key_env_var="AUDIT_BRIDGE_INGEST_KEY",
            test_key_env_var="AUDIT_BRIDGE_TEST_KEY",
            require_auth=True,
            shadow_timeout_ms=50.0,
            max_persistence_retries=2,
            min_daily_coverage_records=2,
        )
        self.adapter_config.operational_api_key = "op_dot_key_verified_2026"
        self.adapter_config.test_api_key = "test_key_internal_qa"

        self.adapter = ShadowIngestionAdapter(
            config=self.adapter_config,
            shadow_service=self.shadow_service,
        )
        self.client = app.test_client()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_baseline_artifact_immutability(self):
        """Verify score_bridge_risk.py and all Phase 17 baseline files match exact cryptographic checksums."""
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

    def test_02_zero_feature_name_warnings(self):
        """Verify that score_record on both Phase 17 and Phase 21B emits zero scikit-learn UserWarnings."""
        with warnings.catch_warnings(record=True) as captured_warnings:
            warnings.simplefilter("always")
            prod_scorer = BridgeRiskScorer(verify_checksums=False)
            shadow_scorer = ShadowBridgeRiskScorer(verify_checksums=False)

            p_res = prod_scorer.score_record(self.sample_record)
            s_res = shadow_scorer.score_record(self.sample_record)

            self.assertIn("calibrated_deterioration_probability", p_res)
            self.assertIn("calibrated_deterioration_probability", s_res)

            user_warnings = [w for w in captured_warnings if issubclass(w.category, UserWarning)]
            self.assertEqual(len(user_warnings), 0, f"Expected 0 UserWarnings, got: {[str(w.message) for w in user_warnings]}")

    def test_03_feature_schema_and_order_identity(self):
        """Verify 26-feature schema, numeric/categorical split, and exact ordering match across models and manifests."""
        with open(P17_DIR / "inference_metadata.json") as f:
            p17_meta = json.load(f)["feature_schema"]

        with open(P21B_DIR / "phase21b_experiment_manifest.json") as f:
            p21b_manifest = json.load(f)

        self.assertEqual(NUMERIC_FEATURES, SHADOW_NUMS)
        self.assertEqual(CATEGORICAL_FEATURES, SHADOW_CATS)
        self.assertEqual(ALL_REQUIRED_FEATURES, SHADOW_ALL)
        self.assertEqual(NUMERIC_FEATURES, p17_meta["numeric_features"])
        self.assertEqual(CATEGORICAL_FEATURES, p17_meta["categorical_features"])
        self.assertEqual(ALL_REQUIRED_FEATURES, p17_meta["all_features_ordered"])
        self.assertEqual(len(ALL_REQUIRED_FEATURES), 26)
        self.assertEqual(len(NUMERIC_FEATURES), 13)
        self.assertEqual(len(CATEGORICAL_FEATURES), 13)

    def test_04_unauthenticated_and_test_traffic_isolated_to_synthetic(self):
        """Verify unauthenticated requests in open mode or requests with test keys cannot produce live operational evidence."""
        # 1. Test key with claimed live traffic source -> automatically mapped to SYNTHETIC_TEST
        headers = {"X-API-Key": "test_key_internal_qa", "X-Traffic-Source": "LIVE_OPERATIONAL"}
        self.adapter.route_single_score(self.sample_record, headers)

        summary = self.shadow_service.tracker.get_summary()
        self.assertEqual(summary["total_live_records"], 0)
        self.assertEqual(summary["total_synthetic_records"], 1)
        self.assertFalse(summary["live_traffic_started"])

        # 2. Open mode without operational key claiming LIVE_OPERATIONAL -> remapped to SYNTHETIC_TEST
        open_config = ShadowIngestionConfig(require_auth=False)
        open_adapter = ShadowIngestionAdapter(config=open_config, shadow_service=self.shadow_service)
        open_adapter.route_single_score(self.sample_record, {"X-Traffic-Source": "LIVE_OPERATIONAL"})

        summary2 = self.shadow_service.tracker.get_summary()
        self.assertEqual(summary2["total_live_records"], 0)
        self.assertEqual(summary2["total_synthetic_records"], 2)
        self.assertFalse(summary2["live_traffic_started"])

    def test_05_readiness_state_machine_and_coverage_gating(self):
        """Verify strict multi-stage readiness progression and gating on daily unique bridge coverage."""
        # Initial: CONNECTION_VERIFIED, NOT_STARTED
        r0 = self.adapter.get_readiness_assessment()
        self.assertTrue(r0["states"]["CONFIGURATION_READY"])
        self.assertTrue(r0["states"]["CONNECTION_VERIFIED"])
        self.assertFalse(r0["states"]["AUTHENTIC_LIVE_TRAFFIC_CONFIRMED"])
        self.assertFalse(r0["states"]["OBSERVATION_STARTED"])
        self.assertEqual(r0["onboarding_state"], "CONNECTION_VERIFIED")

        # Step 1: 1 authentic record with operational key (min required is 2)
        op_headers = {"X-API-Key": "op_dot_key_verified_2026", "X-Traffic-Source": "LIVE_OPERATIONAL"}
        self.adapter.route_single_score(self.sample_record, op_headers)

        r1 = self.adapter.get_readiness_assessment()
        self.assertTrue(r1["states"]["AUTHENTIC_LIVE_TRAFFIC_CONFIRMED"])
        self.assertFalse(r1["states"]["OBSERVATION_STARTED"])
        self.assertEqual(r1["onboarding_state"], "AUTHENTIC_LIVE_TRAFFIC_CONFIRMED")

        # Step 2: 2nd record with duplicate bridge ID -> still under unique coverage threshold
        self.adapter.route_single_score(self.sample_record, op_headers)
        r2 = self.adapter.get_readiness_assessment()
        self.assertFalse(r2["states"]["OBSERVATION_STARTED"])

        # Step 3: 2nd UNIQUE bridge record -> satisfies daily coverage -> OBSERVATION_STARTED
        rec2 = self.sample_record.copy()
        rec2["bridge_id"] = "BRIDGE_UNIQUE_042"
        self.adapter.route_single_score(rec2, op_headers)

        r3 = self.adapter.get_readiness_assessment()
        self.assertTrue(r3["states"]["OBSERVATION_STARTED"])
        self.assertEqual(r3["onboarding_state"], "OBSERVATION_STARTED")

    def test_06_cutover_safety_lock_strictly_enforced(self):
        """Verify BRIDGE_PRODUCTION_CUTOVER_ENABLED=false remains enforced across services."""
        self.assertFalse(self.shadow_service.config.cutover_enabled)
        readiness = self.adapter.get_readiness_assessment()
        self.assertFalse(readiness["cutover_switch_enabled"])
        self.assertEqual(readiness["active_production_champion"], "Phase 17")

    def test_07_outcome_dependent_metrics_strictly_pending(self):
        """Verify outcome metrics (precision, recall, FPR) remain PENDING_VERIFIED_GROUND_TRUTH."""
        readiness = self.adapter.get_readiness_assessment()
        self.assertEqual(readiness["outcome_dependent_metrics_status"], "PENDING_VERIFIED_GROUND_TRUTH")


if __name__ == "__main__":
    unittest.main()
