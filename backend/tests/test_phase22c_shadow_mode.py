"""
Unit Tests for Phase 22C: Pre-Production Validation and Shadow-Mode Readiness
Risk-Aware Bridge Maintenance Intelligence Platform

Tests:
1. Immutability of Phase 17 artifacts and backend/score_bridge_risk.py.
2. Verified presence and integrity of Phase 21B and Phase 22 artifacts.
3. Exact Max-F1 workload arithmetic decomposition:
   - Phase 17: 2,092 TP + 4,685 FP = 6,777 flags (10.33%)
   - Phase 21B: 2,480 TP + 5,918 FP = 8,398 flags (12.81%)
   - Net difference: +1,621 flags (+388 TP, +1,233 FP, -388 FN)
4. Budget-neutral ~10% capacity workload savings verification.
5. Shadow scorer resilience against missing numeric features and unseen categories.
6. Single-digit FHWA code zero-padding normalization.
7. Strict rejection of malformed schemas and non-numeric inputs.
8. Output determinism across multiple runs.
9. Verification that Phase 17 remains active production champion (zero cutover).
"""

import os
import sys
import json
import hashlib
import unittest
from pathlib import Path
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.score_bridge_risk import (
    BridgeRiskScorer,
    get_default_scorer,
    SchemaValidationError,
    ArtifactLoadError,
    ALL_REQUIRED_FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)
from backend.validate_shadow_mode_phase22c import ShadowBridgeRiskScorer, sha256_file

BASE_DIR = Path(__file__).resolve().parent.parent
P17_DIR = BASE_DIR / "results" / "phase17"
P18_CAL_DIR = BASE_DIR / "results" / "phase18" / "calibration"
P21B_DIR = BASE_DIR / "results" / "phase21b"
P22_DIR = BASE_DIR / "results" / "phase22"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"


class TestPhase22CShadowMode(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)["fixtures"]
        cls.sample_record = cls.fixtures[0]["input_record"].copy()

        cls.manifest_path = P22_DIR / "phase22_threshold_manifest.json"
        with open(cls.manifest_path, "r", encoding="utf-8") as f:
            cls.threshold_manifest = json.load(f)

        cls.summary_path = P22_DIR / "phase22c_shadow_validation_summary.json"
        with open(cls.summary_path, "r", encoding="utf-8") as f:
            cls.shadow_summary = json.load(f)

    def test_01_baseline_immutability(self):
        """Verify Phase 17 artifacts and score_bridge_risk.py remain byte-for-byte identical."""
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

    def test_02_phase21b_candidate_integrity(self):
        """Verify Phase 21B candidate model and calibrator artifacts match expected checksums."""
        expected_21b = {
            "phase21b_tuned_model.joblib": "aa806c8185db465fd02536d2d4310638c499d41560ac759e0ea15d4a60f98443",
            "phase21b_calibrator.joblib": "cd9d2f3833112e9fd90b5bd355646a1e68f50ac5218b038a95f0d31766c5978f",
            "phase21b_encoder.joblib": "14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772",
        }
        for fname, h in expected_21b.items():
            self.assertEqual(sha256_file(P21B_DIR / fname), h, f"Checksum mismatch on {fname}")

    def test_03_max_f1_workload_arithmetic_audit(self):
        """Verify exact Max-F1 workload arithmetic and decomposition."""
        p17 = self.threshold_manifest["test_audit_comparison"]["max_f1_optimal"]["phase17"]["metrics"]
        p21 = self.threshold_manifest["test_audit_comparison"]["max_f1_optimal"]["phase21b"]["metrics"]

        # Phase 17 verification
        self.assertEqual(p17["tp"], 2092)
        self.assertEqual(p17["fp"], 4685)
        self.assertEqual(p17["bridges_inspected"], 6777)
        self.assertEqual(p17["fn"], 3751)
        self.assertEqual(p17["tn"], 55052)
        self.assertEqual(p17["tp"] + p17["fp"], p17["bridges_inspected"])

        # Phase 21B verification
        self.assertEqual(p21["tp"], 2480)
        self.assertEqual(p21["fp"], 5918)
        self.assertEqual(p21["bridges_inspected"], 8398)
        self.assertEqual(p21["fn"], 3363)
        self.assertEqual(p21["tn"], 53819)
        self.assertEqual(p21["tp"] + p21["fp"], p21["bridges_inspected"])

        # Differences
        diff_inspections = p21["bridges_inspected"] - p17["bridges_inspected"]
        diff_tp = p21["tp"] - p17["tp"]
        diff_fp = p21["fp"] - p17["fp"]
        diff_fn = p21["fn"] - p17["fn"]

        self.assertEqual(diff_inspections, 1621, "Net workload increase must be exactly +1,621 bridges")
        self.assertEqual(diff_tp, 388, "True positive detections must increase by exactly +388")
        self.assertEqual(diff_fp, 1233, "False positives must increase by exactly +1,233")
        self.assertEqual(diff_fn, -388, "Missed deteriorations must decrease by exactly -388")
        self.assertEqual(diff_tp + diff_fp, diff_inspections, "TP delta + FP delta must equal total inspection delta")

    def test_04_budget_neutral_tradeoffs(self):
        """Verify that at equal ~10% capacity, Phase 21B detects more deteriorations with fewer inspections."""
        audit_10 = self.shadow_summary["budget_neutral_10pct_comparison"]
        self.assertGreater(audit_10["tp_gain_at_equal_tau"], 0)
        self.assertGreater(audit_10["inspection_savings_at_equal_tau"], 0)
        self.assertGreater(audit_10["fp_reduction_at_equal_tau"], 0)

        # Exact values at tau=0.1920:
        self.assertEqual(audit_10["phase17_inspections"], 6916)
        self.assertEqual(audit_10["phase21b_inspections"], 6692)
        self.assertEqual(audit_10["inspection_savings_at_equal_tau"], 224)
        self.assertEqual(audit_10["tp_gain_at_equal_tau"], 30)
        self.assertEqual(audit_10["fp_reduction_at_equal_tau"], 254)

    def test_05_shadow_scorer_missing_numeric_resilience(self):
        """Verify shadow scorer handles NaN/None in numeric features cleanly."""
        scorer = ShadowBridgeRiskScorer(threshold=0.1680, verify_checksums=True)
        rec = self.sample_record.copy()
        rec["adt"] = None
        rec["detour_kilos"] = np.nan
        rec["structure_len_mt"] = None

        res = scorer.score_record(rec)
        self.assertIn("calibrated_deterioration_probability", res)
        self.assertTrue(0.0 <= res["calibrated_deterioration_probability"] <= 1.0)
        self.assertIn("deterioration_flag", res)
        self.assertEqual(res["operational_threshold"], 0.1680)

    def test_06_shadow_scorer_unseen_category_resilience(self):
        """Verify shadow scorer maps unseen categorical features to -1 indicator with warning."""
        scorer = ShadowBridgeRiskScorer(threshold=0.1680, verify_checksums=True)
        rec = self.sample_record.copy()
        rec["state_code"] = "99"
        rec["functional_class"] = "UNKNOWN_FC"

        res = scorer.score_record(rec)
        self.assertTrue(0.0 <= res["calibrated_deterioration_probability"] <= 1.0)
        self.assertTrue(any("unobserved category" in w for w in res["warnings"]))

    def test_07_fhwa_normalization(self):
        """Verify single-digit FHWA codes are padded to two digits."""
        scorer = ShadowBridgeRiskScorer(threshold=0.1680, verify_checksums=True)
        rec = self.sample_record.copy()
        rec["state_code"] = 1
        rec["functional_class"] = "2"

        res = scorer.score_record(rec)
        self.assertTrue(any("normalized single-digit FHWA code" in w for w in res["warnings"]))

    def test_08_schema_validation_rejections(self):
        """Verify missing features and malformed types raise SchemaValidationError."""
        scorer = ShadowBridgeRiskScorer(threshold=0.1680, verify_checksums=True)
        
        # Missing feature
        bad_rec = self.sample_record.copy()
        del bad_rec["adt"]
        with self.assertRaises(SchemaValidationError):
            scorer.score_record(bad_rec)

        # Non-numeric string in numeric feature
        bad_rec2 = self.sample_record.copy()
        bad_rec2["traffic_lanes_on"] = "five_lanes"
        with self.assertRaises(SchemaValidationError):
            scorer.score_record(bad_rec2)

    def test_09_scoring_determinism(self):
        """Verify identical repeated predictions on batch input."""
        scorer = ShadowBridgeRiskScorer(threshold=0.1680, verify_checksums=True)
        records = [f["input_record"] for f in self.fixtures]
        
        run1 = scorer.score_batch(records)
        run2 = scorer.score_batch(records)

        for r1, r2 in zip(run1, run2):
            self.assertEqual(r1["calibrated_deterioration_probability"], r2["calibrated_deterioration_probability"])
            self.assertEqual(r1["raw_decision_score"], r2["raw_decision_score"])
            self.assertEqual(r1["deterioration_flag"], r2["deterioration_flag"])

    def test_10_production_champion_status(self):
        """Confirm that Phase 17 remains the active production champion and default scorer."""
        prod_scorer = get_default_scorer(verify_checksums=True)
        self.assertEqual(prod_scorer.metadata.get("model_type"), "HistGradientBoostingClassifier")
        
        # Check that score_record output still reflects Phase 18C service phase
        prod_res = prod_scorer.score_record(self.sample_record)
        self.assertEqual(prod_res["model_metadata"]["service_phase"], "Phase 18C")


if __name__ == "__main__":
    unittest.main()
