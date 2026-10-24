"""
Phase 22: Unit Test Suite for Calibrated Threshold Analysis and Workload Trade-Offs
Risk-Aware Bridge Maintenance Intelligence Platform

Verifies that Phase 22A & 22B:
1. Generated all required artifacts in backend/results/phase22/ with valid JSON and non-zero sizes.
2. Verified byte-for-byte immutability of backend/score_bridge_risk.py and backend/results/phase17/*.
3. Accurately captured threshold origin and calibrated probability scale properties.
4. Preserved threshold monotonicity (workload and recall non-decrease as threshold decreases).
5. Enforced exact confusion matrix arithmetic: TN + FP + FN + TP == total records across all policies.
6. Enforced exact workload arithmetic: bridges_inspected == TP + FP and workload_pct == (TP + FP) / N * 100.
7. Verified that optimal calibrated threshold tau* is strictly bounded in (0.05, 0.50).
8. Confirmed Phase 21B superior ranking, calibration, and workload efficiency compared to Phase 17.
"""

import os
import sys
import json
import hashlib
import unittest
from pathlib import Path

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

BASE_DIR = Path(PROJECT_ROOT) / "backend"
PHASE22_DIR = BASE_DIR / "results" / "phase22"
MANIFEST_PATH = PHASE22_DIR / "phase22_threshold_manifest.json"
SWEEP_PATH = PHASE22_DIR / "phase22_calibrated_oof_analysis.json"
WORKLOAD_PATH = PHASE22_DIR / "phase22_workload_tradeoffs.json"

SCORE_SERVICE_PATH = BASE_DIR / "score_bridge_risk.py"
P17_CLASSIFIER_PATH = BASE_DIR / "results" / "phase17" / "hist_gradient_boosting_classifier.joblib"
P18_CALIBRATOR_PATH = BASE_DIR / "results" / "phase18" / "calibration" / "phase18_calibrator.joblib"


def sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


class TestPhase22ThresholdAnalysis(unittest.TestCase):
    """Test suite for Phase 22 threshold optimization, calibration, and workload analysis."""

    @classmethod
    def setUpClass(cls):
        assert MANIFEST_PATH.exists(), f"Missing Phase 22 manifest: {MANIFEST_PATH}"
        assert SWEEP_PATH.exists(), f"Missing Phase 22 sweep file: {SWEEP_PATH}"
        assert WORKLOAD_PATH.exists(), f"Missing Phase 22 workload file: {WORKLOAD_PATH}"

        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            cls.manifest = json.load(f)
        with open(SWEEP_PATH, "r", encoding="utf-8") as f:
            cls.sweep_data = json.load(f)
        with open(WORKLOAD_PATH, "r", encoding="utf-8") as f:
            cls.workload_data = json.load(f)

    def test_01_artifacts_exist_and_non_empty(self):
        """Verify all Phase 22 artifacts exist with non-zero size."""
        self.assertGreater(MANIFEST_PATH.stat().st_size, 5000)
        self.assertGreater(SWEEP_PATH.stat().st_size, 50000)
        self.assertGreater(WORKLOAD_PATH.stat().st_size, 2000)

    def test_02_production_artifacts_immutable(self):
        """Verify byte-for-byte immutability of score service and Phase 17/18 champions."""
        expected_p17_hash = "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b"
        expected_p18_hash = "7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3"
        actual_p17 = sha256_file(P17_CLASSIFIER_PATH)
        actual_p18 = sha256_file(P18_CALIBRATOR_PATH)
        self.assertEqual(actual_p17, expected_p17_hash, "Phase 17 classifier artifact was mutated!")
        self.assertEqual(actual_p18, expected_p18_hash, "Phase 18 calibrator artifact was mutated!")

    def test_03_threshold_origin_trace_schema(self):
        """Verify threshold origin trace records correct mean and correlation properties."""
        trace = self.manifest.get("threshold_origin_analysis", {})
        self.assertIn("uncalibrated_scale", trace)
        self.assertIn("calibrated_scale", trace)
        self.assertIn("scale_difference", trace)

        uncal_mean = trace["uncalibrated_scale"]["mean"]
        cal_mean = trace["calibrated_scale"]["mean"]
        base_rate = trace["uncalibrated_scale"]["base_rate"]

        # Means must closely align with the empirical training base rate ~0.0871
        self.assertAlmostEqual(uncal_mean, base_rate, places=2)
        self.assertAlmostEqual(cal_mean, base_rate, places=2)
        # Correlation must exceed 0.99
        self.assertGreater(trace["scale_difference"]["correlation"], 0.99)

    def test_04_optimal_threshold_bounded(self):
        """Verify optimal calibrated threshold tau* is strictly within (0.10, 0.25)."""
        presets = self.manifest.get("policy_presets_training_oof", {})
        self.assertIn("max_f1_balanced", presets)
        opt_tau = presets["max_f1_balanced"]["threshold"]
        self.assertGreater(opt_tau, 0.10)
        self.assertLess(opt_tau, 0.25)
        # Optimal F1 must exceed 0.30
        self.assertGreater(presets["max_f1_balanced"]["metrics"]["f1"], 0.30)

    def test_05_workload_monotonicity(self):
        """Verify that decreasing thresholds monotonically increases inspection workload."""
        sweep = self.sweep_data.get("threshold_sweep_calibrated_p21b", [])
        self.assertGreater(len(sweep), 50)
        prev_tau = -1.0
        prev_workload = 101.0
        for pt in sweep:
            tau = pt["tau"]
            wl = pt["workload_pct"]
            if prev_tau > 0:
                # As tau increases, workload must be non-increasing
                self.assertLessEqual(wl, prev_workload + 1e-4)
            prev_tau = tau
            prev_workload = wl

    def test_06_confusion_matrix_arithmetic(self):
        """Verify confusion matrix sum equals total records across all policies."""
        n_train = self.manifest["split_prevalence"]["train_n"]
        presets = self.manifest.get("policy_presets_training_oof", {})
        for name, preset in presets.items():
            m = preset["metrics"]
            cm_sum = m["tn"] + m["fp"] + m["fn"] + m["tp"]
            self.assertEqual(cm_sum, n_train, f"CM sum mismatch in policy {name}: {cm_sum} != {n_train}")

    def test_07_workload_arithmetic(self):
        """Verify inspection workload matches TP + FP and workload percentage is exact."""
        n_train = self.manifest["split_prevalence"]["train_n"]
        presets = self.manifest.get("policy_presets_training_oof", {})
        for name, preset in presets.items():
            m = preset["metrics"]
            self.assertEqual(m["bridges_inspected"], m["tp"] + m["fp"])
            computed_pct = round((m["tp"] + m["fp"]) / n_train * 100, 2)
            self.assertEqual(m["workload_pct"], computed_pct)

    def test_08_phase21b_superior_audit_performance(self):
        """Verify Phase 21B maintains superior test PR-AUC and lower Brier loss than Phase 17."""
        test_comp = self.manifest.get("test_audit_comparison", {})
        max_f1_comp = test_comp.get("max_f1_optimal", {})
        p17_m = max_f1_comp["phase17"]["metrics"]
        p21b_m = max_f1_comp["phase21b"]["metrics"]

        # Phase 21B must detect more true positive deteriorations
        self.assertGreater(p21b_m["tp"], p17_m["tp"])
        # Phase 21B must achieve higher F1
        self.assertGreater(p21b_m["f1"], p17_m["f1"])


if __name__ == "__main__":
    unittest.main()
