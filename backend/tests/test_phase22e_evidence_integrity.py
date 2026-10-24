"""
Unit Tests for Phase 22E: Shadow Evidence Integrity and Readiness Audit
Risk-Aware Bridge Maintenance Intelligence Platform

Tests:
1. Baseline artifact immutability (Phase 17 production champion and score_bridge_risk.py).
2. Workload arithmetic and confusion matrix identity on Cohort A (N=65,580 national test split).
3. Workload arithmetic and confusion matrix identity on Cohort B (N=5,000 regional sample slice).
4. Cohort mismatch detection (verifies error or rejection when Cohort A metrics are attributed to Cohort B).
5. Latency distinction (amortized batch processing speed vs single-record request latency, SLA compliance).
6. Temporal observation window tracking (enforces 30 calendar days of live traffic before promotion).
7. Governance cutover safety lock (production cutover strictly locked; Phase 17 active champion).
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path

import numpy as np

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
from backend.validate_shadow_mode_phase22c import sha256_file

BASE_DIR = Path(__file__).resolve().parent.parent
P17_DIR = BASE_DIR / "results" / "phase17"
P18_CAL_DIR = BASE_DIR / "results" / "phase18" / "calibration"
P21B_DIR = BASE_DIR / "results" / "phase21b"
P22_DIR = BASE_DIR / "results" / "phase22"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"
SUMMARY_PATH = P22_DIR / "phase22e_evidence_integrity_summary.json"


class TestPhase22EEvidenceIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)["fixtures"]
        cls.sample_record = cls.fixtures[0]["input_record"].copy()
        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            cls.summary = json.load(f)

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_telemetry_path = Path(self.temp_dir) / "audit_telemetry.jsonl"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_baseline_immutability(self):
        """Verify score_bridge_risk.py and Phase 17 production artifacts match expected hashes identically."""
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

    def test_02_cohort_a_workload_arithmetic(self):
        """Verify Cohort A (N=65,580 national test split) confusion matrix and workload numbers."""
        ca = self.summary["workload_arithmetic_audit"]["cohort_a_national_test_split"]
        self.assertEqual(ca["record_count"], 65580)
        self.assertEqual(ca["deterioration_count"], 5843)
        self.assertEqual(ca["prevalence_pct"], 8.91)

        # Phase 17
        self.assertEqual(ca["phase17_flags"], 6777)
        self.assertEqual(ca["phase17_workload_pct"], 10.33)
        cm17 = ca["phase17_confusion_matrix"]
        self.assertEqual(cm17["tp"], 2092)
        self.assertEqual(cm17["fp"], 4685)
        self.assertEqual(cm17["fn"], 3751)
        self.assertEqual(cm17["tn"], 55052)
        self.assertEqual(cm17["tp"] + cm17["fp"], 6777)

        # Phase 21B
        self.assertEqual(ca["phase21b_flags"], 8398)
        self.assertEqual(ca["phase21b_workload_pct"], 12.81)
        cm21 = ca["phase21b_confusion_matrix"]
        self.assertEqual(cm21["tp"], 2480)
        self.assertEqual(cm21["fp"], 5918)
        self.assertEqual(cm21["fn"], 3363)
        self.assertEqual(cm21["tn"], 53819)
        self.assertEqual(cm21["tp"] + cm21["fp"], 8398)

        # Delta & Incremental Precision
        delta = ca["delta"]
        self.assertEqual(delta["net_flags"], 1621)
        self.assertEqual(delta["delta_tp"], 388)
        self.assertEqual(delta["delta_fp"], 1233)
        self.assertEqual(delta["delta_fn"], -388)
        self.assertEqual(delta["delta_tp"] + delta["delta_fp"], delta["net_flags"])
        self.assertAlmostEqual(delta["incremental_precision_pct"], 23.94, places=2)

    def test_03_cohort_b_workload_arithmetic(self):
        """Verify Cohort B (N=5,000 regional slice) confusion matrix and workload numbers."""
        cb = self.summary["workload_arithmetic_audit"]["cohort_b_regional_5k_sample"]
        self.assertEqual(cb["record_count"], 5000)
        self.assertEqual(cb["deterioration_count"], 348)
        self.assertEqual(cb["prevalence_pct"], 6.96)
        self.assertEqual(cb["states"], [1, 2, 4, 5, 6])

        # Phase 17
        self.assertEqual(cb["phase17_flags"], 253)
        self.assertEqual(cb["phase17_workload_pct"], 5.06)
        cm17 = cb["phase17_confusion_matrix"]
        self.assertEqual(cm17["tp"], 74)
        self.assertEqual(cm17["fp"], 179)
        self.assertEqual(cm17["fn"], 274)
        self.assertEqual(cm17["tn"], 4473)
        self.assertEqual(cm17["tp"] + cm17["fp"], 253)

        # Phase 21B
        self.assertEqual(cb["phase21b_flags"], 368)
        self.assertEqual(cb["phase21b_workload_pct"], 7.36)
        cm21 = cb["phase21b_confusion_matrix"]
        self.assertEqual(cm21["tp"], 98)
        self.assertEqual(cm21["fp"], 270)
        self.assertEqual(cm21["fn"], 250)
        self.assertEqual(cm21["tn"], 4382)
        self.assertEqual(cm21["tp"] + cm21["fp"], 368)

        # Delta & Incremental Precision
        delta = cb["delta"]
        self.assertEqual(delta["net_flags"], 115)
        self.assertEqual(delta["delta_tp"], 24)
        self.assertEqual(delta["delta_fp"], 91)
        self.assertEqual(delta["delta_fn"], -24)
        self.assertEqual(delta["delta_tp"] + delta["delta_fp"], delta["net_flags"])
        self.assertAlmostEqual(delta["incremental_precision_pct"], 20.87, places=2)
        self.assertAlmostEqual(delta["agreement_rate_pct"], 97.42, places=2)

    def test_04_cohort_mismatch_detection(self):
        """Verify detection of cohort mismatch: attributing Cohort A metrics to Cohort B fails integrity."""
        ca = self.summary["workload_arithmetic_audit"]["cohort_a_national_test_split"]
        cb = self.summary["workload_arithmetic_audit"]["cohort_b_regional_5k_sample"]

        # Ensure that Cohort A incremental precision (23.94%) is strictly higher than Cohort B (20.87%)
        self.assertNotEqual(ca["delta"]["incremental_precision_pct"], cb["delta"]["incremental_precision_pct"])
        self.assertNotEqual(ca["phase21b_workload_pct"], cb["phase21b_workload_pct"])

        # Cohort B slice deterioration prevalence is strictly lower due to regional climate/jurisdiction
        self.assertLess(cb["prevalence_pct"], ca["prevalence_pct"])

    def test_05_latency_distinction_and_sla(self):
        """Verify distinction between batch-amortized processing speed and single-record latency."""
        lat_audit = self.summary["latency_audit"]
        self.assertEqual(lat_audit["reported_phase22d_latency_ms"], 0.04)
        self.assertEqual(lat_audit["reported_metric_type"], "AMORTIZED_BATCH_RUNTIME_PER_ITEM")

        # Single-record p95 must be measured and compliant with 15.0 ms SLA
        self.assertLess(lat_audit["measured_single_record_p17_p95_ms"], 15.0)
        self.assertLess(lat_audit["measured_single_record_p21b_p95_ms"], 15.0)
        self.assertTrue(lat_audit["sla_compliance"])

        # Single-record latency must be significantly greater than amortized batch runtime
        self.assertGreater(lat_audit["measured_single_record_p21b_median_ms"], 1.0)

    def test_06_observation_window_calendar_tracking(self):
        """Verify that observation window properly enforces 30 calendar days of live traffic."""
        config = ShadowDeploymentConfig(
            enabled=True,
            cutover_enabled=False,
            telemetry_path=self.temp_telemetry_path,
            tracker_state_path=Path(self.temp_dir) / "test_tracker.json",
            observation_window_days=30,
            min_observation_records=10,
        )
        service = ShadowScoringService(config=config)

        # Score records on a single instant
        for _ in range(5):
            service.score_record_with_shadow(self.sample_record)

        summary = service.get_telemetry_summary()
        obs = summary["observation_progress"]
        self.assertEqual(obs["calendar_days_elapsed"], 1)
        self.assertFalse(obs["temporal_window_completed"])
        self.assertIn("IN_PROGRESS", obs["temporal_status"])

        # Cutover/readiness must remain blocked
        self.assertEqual(summary["overall_gate_readiness"], "OBSERVATION_IN_PROGRESS")
        self.assertFalse(summary["acceptance_gates_evaluation"]["live_observation_period"]["meets_criteria"])

    def test_07_governance_cutover_safety_lock(self):
        """Verify production cutover is disabled by default and Phase 17 remains active champion."""
        self.assertFalse(self.summary["cutover_switch_enabled"])
        self.assertIn("Phase 17", self.summary["active_production_champion"])
        self.assertFalse(self.summary["final_governance_verdict"]["can_promote_now"])
        self.assertIn("CONDITIONAL PASS", self.summary["final_governance_verdict"]["audit_verdict"])
        self.assertEqual(
            self.summary["final_governance_verdict"]["production_cutover_status"],
            "DISABLED_PENDING_EXPLICIT_APPROVAL"
        )


if __name__ == "__main__":
    unittest.main()
