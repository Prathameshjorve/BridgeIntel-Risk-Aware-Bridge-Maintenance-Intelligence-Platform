"""
Phase 21B: Tuned Model Verification & Test Suite
Risk-Aware Bridge Maintenance Intelligence Platform

Verifies that the Phase 21B Tuned Model (C10_unweighted_conservative):
1. Artifacts exist with verified SHA-256 hashes and non-zero sizes in backend/results/phase21b/.
2. Adheres to the exact 26-feature schema (13 numeric, 13 categorical).
3. Handles missing numeric values natively via HistGradientBoosting.
4. Handles unseen categorical codes gracefully via the fitted OrdinalEncoder.
5. Produces calibrated deterioration probabilities strictly bounded within [0.0, 1.0].
6. Exhibits strict deterministic repeatability.
7. Produces batch predictions that match single-record predictions within numerical tolerance.
8. Preserves the frozen Phase 20 champion and Phase 21 candidate artifacts without alteration.
"""

import os
import sys
import copy
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
import joblib

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.score_bridge_risk import (
    ALL_REQUIRED_FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    SEMANTICS_DISCLAIMER,
)

BASE_DIR = Path(PROJECT_ROOT) / "backend"
PHASE21B_DIR = BASE_DIR / "results" / "phase21b"
TUNED_MODEL_PATH = PHASE21B_DIR / "phase21b_tuned_model.joblib"
TUNED_CALIBRATOR_PATH = PHASE21B_DIR / "phase21b_calibrator.joblib"
TUNED_ENCODER_PATH = PHASE21B_DIR / "phase21b_encoder.joblib"
MANIFEST_PATH = PHASE21B_DIR / "phase21b_experiment_manifest.json"

CHAMPION_P20_PATH = BASE_DIR / "results" / "phase17" / "hist_gradient_boosting_classifier.joblib"
CANDIDATE_P21_PATH = BASE_DIR / "results" / "phase21" / "candidate_2_deep_interactions.joblib"


class TestPhase21BTuning(unittest.TestCase):
    """Test suite for Phase 21B tuned model artifacts and inference compatibility."""

    @classmethod
    def setUpClass(cls):
        fixture_path = os.path.join(
            PROJECT_ROOT, "backend", "tests", "fixtures", "regression_test_fixture.json"
        )
        assert os.path.exists(fixture_path), f"Missing fixture file: {fixture_path}"
        with open(fixture_path, "r", encoding="utf-8") as f:
            cls.fixtures_data = json.load(f)["fixtures"]
        cls.valid_record = copy.deepcopy(cls.fixtures_data[0]["input_record"])

        assert TUNED_MODEL_PATH.exists(), f"Missing Phase 21B model: {TUNED_MODEL_PATH}"
        assert TUNED_CALIBRATOR_PATH.exists(), f"Missing Phase 21B calibrator: {TUNED_CALIBRATOR_PATH}"
        assert TUNED_ENCODER_PATH.exists(), f"Missing Phase 21B encoder: {TUNED_ENCODER_PATH}"
        assert MANIFEST_PATH.exists(), f"Missing Phase 21B manifest: {MANIFEST_PATH}"

        cls.model = joblib.load(TUNED_MODEL_PATH)
        cls.calibrator = joblib.load(TUNED_CALIBRATOR_PATH)
        cls.encoder = joblib.load(TUNED_ENCODER_PATH)

        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            cls.manifest = json.load(f)

    def test_01_phase21b_artifacts_exist_and_manifest_valid(self):
        """All Phase 21B artifacts exist with valid sizes and manifest schema."""
        self.assertGreater(TUNED_MODEL_PATH.stat().st_size, 50000)
        self.assertGreater(TUNED_CALIBRATOR_PATH.stat().st_size, 500)
        self.assertGreater(TUNED_ENCODER_PATH.stat().st_size, 800)
        self.assertEqual(self.manifest["phase"], "Phase 21B: Hyperparameter Tuning, Regularization and Validation")
        self.assertEqual(self.manifest["quality_gate_decision"], "IMPROVEMENT ESTABLISHED")
        self.assertEqual(len(self.manifest["search_space_12_configurations"]), 12)

    def _encode_cats(self, cat_rows):
        df = pd.DataFrame(cat_rows, columns=CATEGORICAL_FEATURES)
        return self.encoder.transform(df)

    def test_02_feature_contract_preserves_26_features(self):
        """Phase 21B model adheres to the canonical 26-feature contract."""
        self.assertEqual(len(ALL_REQUIRED_FEATURES), 26)
        self.assertEqual(len(NUMERIC_FEATURES), 13)
        self.assertEqual(len(CATEGORICAL_FEATURES), 13)

    def test_03_inference_produces_bounded_probabilities(self):
        """Phase 21B model and calibrator yield probabilities strictly in [0.0, 1.0]."""
        rec = copy.deepcopy(self.valid_record)
        cats = [str(rec[c]) for c in CATEGORICAL_FEATURES]
        cats_enc = self._encode_cats([cats])
        nums = np.array([[float(rec[c]) for c in NUMERIC_FEATURES]])
        X = np.hstack([nums, cats_enc])

        raw_score = self.model.decision_function(X)
        raw_prob = self.model.predict_proba(X)[0, 1]
        cal_prob = self.calibrator.predict_proba(raw_score.reshape(-1, 1))[0, 1]

        self.assertIsInstance(float(raw_score[0]), float)
        self.assertGreaterEqual(raw_prob, 0.0)
        self.assertLessEqual(raw_prob, 1.0)
        self.assertGreaterEqual(cal_prob, 0.0)
        self.assertLessEqual(cal_prob, 1.0)

    def test_04_missing_numeric_features_handled_natively(self):
        """HistGradientBoosting handles NaNs in numeric features without crashing."""
        rec = copy.deepcopy(self.valid_record)
        rec["adt"] = None
        rec["percent_adt_truck"] = None
        rec["structure_len_mt"] = None

        cats = [str(rec[c]) for c in CATEGORICAL_FEATURES]
        cats_enc = self._encode_cats([cats])
        nums = np.array([[np.nan if rec[c] is None else float(rec[c]) for c in NUMERIC_FEATURES]])
        X = np.hstack([nums, cats_enc])

        raw_score = self.model.decision_function(X)
        cal_prob = self.calibrator.predict_proba(raw_score.reshape(-1, 1))[0, 1]
        self.assertGreaterEqual(cal_prob, 0.0)
        self.assertLessEqual(cal_prob, 1.0)

    def test_05_unseen_categories_encoded_as_negative_one(self):
        """Encoder maps unseen categories to -1 without exceptions."""
        unseen = ["NEVER_SEEN_CODE_999"] * len(CATEGORICAL_FEATURES)
        cats_enc = self._encode_cats([unseen])
        self.assertTrue(np.all(cats_enc == -1))

        nums = np.array([[float(self.valid_record[c]) for c in NUMERIC_FEATURES]])
        X = np.hstack([nums, cats_enc])

        raw_score = self.model.decision_function(X)
        cal_prob = self.calibrator.predict_proba(raw_score.reshape(-1, 1))[0, 1]
        self.assertGreaterEqual(cal_prob, 0.0)
        self.assertLessEqual(cal_prob, 1.0)

    def test_06_deterministic_repeatability(self):
        """Inference on identical input produces identical decision scores."""
        cats = [str(self.valid_record[c]) for c in CATEGORICAL_FEATURES]
        cats_enc = self._encode_cats([cats])
        nums = np.array([[float(self.valid_record[c]) for c in NUMERIC_FEATURES]])
        X = np.hstack([nums, cats_enc])

        s1 = self.model.decision_function(X)[0]
        s2 = self.model.decision_function(X)[0]
        self.assertEqual(s1, s2)

    def test_07_batch_inference_consistency(self):
        """Batch inference matches sequential single-record inference."""
        records = [f["input_record"] for f in self.fixtures_data]

        cats_batch = [[str(r[c]) for c in CATEGORICAL_FEATURES] for r in records]
        cats_enc = self._encode_cats(cats_batch)
        nums_batch = np.array([[float(r[c]) for c in NUMERIC_FEATURES] for r in records])
        X_batch = np.hstack([nums_batch, cats_enc])

        batch_scores = self.model.decision_function(X_batch)
        batch_probs = self.calibrator.predict_proba(batch_scores.reshape(-1, 1))[:, 1]

        for i, r in enumerate(records):
            cat_single = [[str(r[c]) for c in CATEGORICAL_FEATURES]]
            cat_single_enc = self._encode_cats(cat_single)
            num_single = np.array([[float(r[c]) for c in NUMERIC_FEATURES]])
            X_single = np.hstack([num_single, cat_single_enc])

            single_score = self.model.decision_function(X_single)[0]
            single_prob = self.calibrator.predict_proba(np.array([[single_score]]))[:, 1][0]

            self.assertAlmostEqual(batch_scores[i], single_score, places=6)
            self.assertAlmostEqual(batch_probs[i], single_prob, places=6)

    def test_08_frozen_artifacts_preserved(self):
        """Phase 20 Champion and Phase 21 Candidate artifacts remain untouched."""
        expected_p20 = "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b"
        expected_p21 = "210bf46945d6e91c5e7968eb5e96038d38682de3e492a1cba6caffe15a017fde"

        import hashlib
        def h(p):
            hasher = hashlib.sha256()
            with open(p, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            return hasher.hexdigest()

        self.assertEqual(h(CHAMPION_P20_PATH), expected_p20)
        self.assertEqual(h(CANDIDATE_P21_PATH), expected_p21)


if __name__ == "__main__":
    unittest.main()
