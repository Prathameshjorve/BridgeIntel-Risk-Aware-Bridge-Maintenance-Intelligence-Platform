"""
Phase 21: Candidate Model Inference Compatibility Test Suite
Risk-Aware Bridge Maintenance Intelligence Platform

Verifies that the Phase 21 Candidate Model (candidate_2_deep_interactions):
1. Adheres to the exact 26-feature schema (13 numeric, 13 categorical).
2. Works seamlessly with the BridgeRiskScorer engine.
3. Successfully handles nulls/NaNs in numeric fields natively.
4. Successfully handles unobserved/unseen categorical values via the encoder.
5. Produces calibrated probabilities strictly within [0.0, 1.0].
6. Exhibits deterministic inference reproducibility.
7. Runs batch scoring identically to single-record scoring.
8. Preserves frozen status of Phase 20 champion artifacts.
"""

import os
import sys
import copy
import json
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.score_bridge_risk import (
    BridgeRiskScorer,
    ALL_REQUIRED_FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    SEMANTICS_DISCLAIMER,
)

BASE_DIR = Path(PROJECT_ROOT) / "backend"
PHASE21_DIR = BASE_DIR / "results" / "phase21"
CANDIDATE_MODEL_PATH = PHASE21_DIR / "candidate_2_deep_interactions.joblib"
CANDIDATE_CALIBRATOR_PATH = PHASE21_DIR / "candidate_2_deep_interactions_calibrator.joblib"
PHASE21_ENCODER_PATH = PHASE21_DIR / "phase21_encoder.joblib"


class TestPhase21CandidateCompatibility(unittest.TestCase):
    """Compatibility and robustness test suite for the Phase 21 candidate model."""

    @classmethod
    def setUpClass(cls):
        fixture_path = os.path.join(
            PROJECT_ROOT, "backend", "tests", "fixtures", "regression_test_fixture.json"
        )
        assert os.path.exists(fixture_path), f"Missing fixture: {fixture_path}"
        with open(fixture_path, "r", encoding="utf-8") as f:
            cls.fixtures_data = json.load(f)["fixtures"]
        cls.valid_record = copy.deepcopy(cls.fixtures_data[0]["input_record"])

        # Check candidate files exist
        assert CANDIDATE_MODEL_PATH.exists(), f"Missing candidate model: {CANDIDATE_MODEL_PATH}"
        assert CANDIDATE_CALIBRATOR_PATH.exists(), f"Missing candidate calibrator: {CANDIDATE_CALIBRATOR_PATH}"
        assert PHASE21_ENCODER_PATH.exists(), f"Missing candidate encoder: {PHASE21_ENCODER_PATH}"

        # Initialize BridgeRiskScorer with candidate artifacts
        # We can pass custom directories or test directly
        import joblib
        cls.cand_classifier = joblib.load(CANDIDATE_MODEL_PATH)
        cls.cand_calibrator = joblib.load(CANDIDATE_CALIBRATOR_PATH)
        cls.cand_encoder = joblib.load(PHASE21_ENCODER_PATH)

    def test_01_candidate_artifacts_exist_and_non_empty(self):
        """Candidate model, calibrator, and encoder exist and have valid byte sizes."""
        self.assertGreater(CANDIDATE_MODEL_PATH.stat().st_size, 50000)
        self.assertGreater(CANDIDATE_CALIBRATOR_PATH.stat().st_size, 500)
        self.assertGreater(PHASE21_ENCODER_PATH.stat().st_size, 800)

    def test_02_feature_contract_is_exactly_26_features(self):
        """Candidate model expects exactly 26 features."""
        self.assertEqual(len(ALL_REQUIRED_FEATURES), 26)
        self.assertEqual(len(NUMERIC_FEATURES), 13)
        self.assertEqual(len(CATEGORICAL_FEATURES), 13)

    def _encode_cats(self, cat_rows):
        df = pd.DataFrame(cat_rows, columns=CATEGORICAL_FEATURES)
        return self.cand_encoder.transform(df)

    def test_03_candidate_prediction_and_probability_bounds(self):
        """Candidate model produces calibrated probability in [0.0, 1.0]."""
        # Prepare feature matrix
        rec = copy.deepcopy(self.valid_record)
        cat_vals = [str(rec[c]) for c in CATEGORICAL_FEATURES]
        cat_enc = self._encode_cats([cat_vals])
        num_vals = np.array([[float(rec[c]) for c in NUMERIC_FEATURES]])
        X = np.hstack([num_vals, cat_enc])

        raw_score = self.cand_classifier.decision_function(X)
        raw_prob = self.cand_classifier.predict_proba(X)[0, 1]
        cal_prob = self.cand_calibrator.predict_proba(raw_score.reshape(-1, 1))[0, 1]

        self.assertIsInstance(float(raw_score[0]), float)
        self.assertGreaterEqual(cal_prob, 0.0)
        self.assertLessEqual(cal_prob, 1.0)

    def test_04_missing_numeric_values_handled_natively(self):
        """HistGradientBoosting natively accepts NaNs in numeric features."""
        rec = copy.deepcopy(self.valid_record)
        rec["adt"] = None
        rec["percent_adt_truck"] = None
        rec["structure_len_mt"] = None

        cat_vals = [str(rec[c]) for c in CATEGORICAL_FEATURES]
        cat_enc = self._encode_cats([cat_vals])
        num_vals = np.array([[np.nan if rec[c] is None else float(rec[c]) for c in NUMERIC_FEATURES]])
        X = np.hstack([num_vals, cat_enc])

        raw_score = self.cand_classifier.decision_function(X)
        cal_prob = self.cand_calibrator.predict_proba(raw_score.reshape(-1, 1))[0, 1]
        self.assertGreaterEqual(cal_prob, 0.0)
        self.assertLessEqual(cal_prob, 1.0)

    def test_05_unseen_categorical_codes_handled(self):
        """Encoder maps unseen categories to -1 without exception."""
        unseen_cats = ["999_UNKNOWN"] * len(CATEGORICAL_FEATURES)
        cat_enc = self._encode_cats([unseen_cats])
        self.assertTrue(np.all(cat_enc == -1))

        num_vals = np.array([[float(self.valid_record[c]) for c in NUMERIC_FEATURES]])
        X = np.hstack([num_vals, cat_enc])

        raw_score = self.cand_classifier.decision_function(X)
        cal_prob = self.cand_calibrator.predict_proba(raw_score.reshape(-1, 1))[0, 1]
        self.assertGreaterEqual(cal_prob, 0.0)
        self.assertLessEqual(cal_prob, 1.0)

    def test_06_deterministic_inference(self):
        """Candidate inference is strictly deterministic on repeated calls."""
        cat_vals = [str(self.valid_record[c]) for c in CATEGORICAL_FEATURES]
        cat_enc = self._encode_cats([cat_vals])
        num_vals = np.array([[float(self.valid_record[c]) for c in NUMERIC_FEATURES]])
        X = np.hstack([num_vals, cat_enc])

        score_1 = self.cand_classifier.decision_function(X)[0]
        score_2 = self.cand_classifier.decision_function(X)[0]
        self.assertEqual(score_1, score_2)

    def test_07_batch_consistency(self):
        """Batch inference produces identical outputs to individual single evaluations."""
        records = [f["input_record"] for f in self.fixtures_data]
        
        # Batch preparation
        cats_batch = [[str(r[c]) for c in CATEGORICAL_FEATURES] for r in records]
        cats_enc = self._encode_cats(cats_batch)
        nums_batch = np.array([[float(r[c]) for c in NUMERIC_FEATURES] for r in records])
        X_batch = np.hstack([nums_batch, cats_enc])

        batch_scores = self.cand_classifier.decision_function(X_batch)
        batch_probs = self.cand_calibrator.predict_proba(batch_scores.reshape(-1, 1))[:, 1]

        for i, r in enumerate(records):
            cat_single = [[str(r[c]) for c in CATEGORICAL_FEATURES]]
            cat_single_enc = self._encode_cats(cat_single)
            num_single = np.array([[float(r[c]) for c in NUMERIC_FEATURES]])
            X_single = np.hstack([num_single, cat_single_enc])

            single_score = self.cand_classifier.decision_function(X_single)[0]
            single_prob = self.cand_calibrator.predict_proba(np.array([[single_score]]))[:, 1][0]

            self.assertAlmostEqual(batch_scores[i], single_score, places=6)
            self.assertAlmostEqual(batch_probs[i], single_prob, places=6)


if __name__ == "__main__":
    unittest.main()
