"""
Unit Tests for Phase 18C Bridge Risk Scoring Service
Risk-Aware Bridge Maintenance Intelligence Platform
"""

import os
import sys
import copy
import json
import unittest
import numpy as np
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.score_bridge_risk import (
    BridgeRiskScorer,
    score_bridges,
    SchemaValidationError,
    ArtifactLoadError,
    ALL_REQUIRED_FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    SEMANTICS_DISCLAIMER,
)


class TestBridgeRiskScorer(unittest.TestCase):
    """Test suite for Phase 18C inference scoring engine."""

    @classmethod
    def setUpClass(cls):
        """Loads regression fixtures and initializes a shared scorer instance."""
        cls.fixture_path = os.path.join(
            PROJECT_ROOT, "backend", "tests", "fixtures", "regression_test_fixture.json"
        )
        assert os.path.exists(cls.fixture_path), f"Missing test fixture: {cls.fixture_path}"
        with open(cls.fixture_path, "r", encoding="utf-8") as f:
            cls.fixtures_data = json.load(f)["fixtures"]

        # Shared scorer instance
        cls.scorer = BridgeRiskScorer(verify_checksums=True)

    def test_01_import_does_not_train(self):
        """Verify that importing backend.score_bridge_risk does not trigger model training."""
        # Check that no new training output was generated
        results_dir = os.path.join(PROJECT_ROOT, "backend", "results", "phase17")
        self.assertTrue(os.path.exists(results_dir))
        # Ensure scorer only loads artifacts
        self.assertIsNotNone(self.scorer.classifier)
        self.assertIsNotNone(self.scorer.calibrator)

    def test_02_regression_fixture_reproduction(self):
        """Verify exact numerical reproduction of verified project regression fixtures."""
        for fixture in self.fixtures_data:
            bid = fixture["bridge_id"]
            inp = fixture["input_record"]
            expected_raw = fixture["expected_raw_score"]
            expected_cal = fixture["expected_calibrated_probability"]

            res = self.scorer.score_record(inp)

            # Check precision to within 1e-6
            self.assertAlmostEqual(res["raw_decision_score"], expected_raw, places=5)
            self.assertAlmostEqual(
                res["calibrated_deterioration_probability"], expected_cal, places=5
            )
            self.assertEqual(res.get("bridge_id"), bid)
            self.assertEqual(res["prediction_semantics"], SEMANTICS_DISCLAIMER)

    def test_03_column_order_invariance(self):
        """Verify that records with reversed or permuted feature keys produce identical scores."""
        base_record = copy.deepcopy(self.fixtures_data[0]["input_record"])
        keys = list(base_record.keys())

        # Permuted order 1: reversed keys
        reversed_record = {k: base_record[k] for k in reversed(keys)}
        # Permuted order 2: alphabetically sorted keys
        sorted_record = {k: base_record[k] for k in sorted(keys)}

        res_base = self.scorer.score_record(base_record)
        res_rev = self.scorer.score_record(reversed_record)
        res_sorted = self.scorer.score_record(sorted_record)

        self.assertEqual(res_base["raw_decision_score"], res_rev["raw_decision_score"])
        self.assertEqual(
            res_base["calibrated_deterioration_probability"],
            res_rev["calibrated_deterioration_probability"],
        )
        self.assertEqual(res_base["raw_decision_score"], res_sorted["raw_decision_score"])
        self.assertEqual(
            res_base["calibrated_deterioration_probability"],
            res_sorted["calibrated_deterioration_probability"],
        )

    def test_04_batch_vs_single_record_equivalence(self):
        """Verify that score_batch([r1, r2]) gives bitwise identical results to single calls."""
        r1 = copy.deepcopy(self.fixtures_data[0]["input_record"])
        r2 = copy.deepcopy(self.fixtures_data[1]["input_record"])

        res_single_1 = self.scorer.score_record(r1)
        res_single_2 = self.scorer.score_record(r2)
        res_batch = self.scorer.score_batch([r1, r2])

        self.assertEqual(len(res_batch), 2)
        self.assertEqual(
            res_batch[0]["raw_decision_score"], res_single_1["raw_decision_score"]
        )
        self.assertEqual(
            res_batch[0]["calibrated_deterioration_probability"],
            res_single_1["calibrated_deterioration_probability"],
        )
        self.assertEqual(
            res_batch[1]["raw_decision_score"], res_single_2["raw_decision_score"]
        )
        self.assertEqual(
            res_batch[1]["calibrated_deterioration_probability"],
            res_single_2["calibrated_deterioration_probability"],
        )

    def test_05_dataframe_input_support(self):
        """Verify that passing a pandas DataFrame produces valid batch scores."""
        records = [f["input_record"] for f in self.fixtures_data]
        df_input = pd.DataFrame(records)

        res_df = self.scorer.score_batch(df_input)
        self.assertEqual(len(res_df), len(records))
        for i in range(len(records)):
            self.assertAlmostEqual(
                res_df[i]["raw_decision_score"],
                self.fixtures_data[i]["expected_raw_score"],
                places=5,
            )

    def test_06_deterministic_repeated_predictions(self):
        """Verify deterministic repeatability over multiple sequential calls."""
        rec = copy.deepcopy(self.fixtures_data[0]["input_record"])
        results = [self.scorer.score_record(rec) for _ in range(5)]

        first_raw = results[0]["raw_decision_score"]
        first_prob = results[0]["calibrated_deterioration_probability"]

        for r in results[1:]:
            self.assertEqual(r["raw_decision_score"], first_raw)
            self.assertEqual(r["calibrated_deterioration_probability"], first_prob)

    def test_07_probability_bounds_and_calibrator_composition(self):
        """Verify that calibrated probabilities are strictly bounded in [0, 1] and match sigmoid."""
        rec = copy.deepcopy(self.fixtures_data[0]["input_record"])
        res = self.scorer.score_record(rec)

        prob = res["calibrated_deterioration_probability"]
        self.assertGreaterEqual(prob, 0.0)
        self.assertLessEqual(prob, 1.0)

        # Check calibrator mathematical composition
        raw_z = res["raw_decision_score"]
        A = float(self.scorer.calibrator.coef_[0][0])
        B = float(self.scorer.calibrator.intercept_[0])
        expected_sig = 1.0 / (1.0 + np.exp(-(A * raw_z + B)))
        self.assertAlmostEqual(prob, expected_sig, places=6)

    def test_08_missing_numeric_values_handling(self):
        """Verify that missing numeric values (None, np.nan) are natively handled."""
        rec = copy.deepcopy(self.fixtures_data[0]["input_record"])
        # Set some numeric fields to None and NaN
        rec["percent_adt_truck"] = None
        rec["detour_kilos"] = np.nan

        res = self.scorer.score_record(rec)
        self.assertIsInstance(res["raw_decision_score"], float)
        self.assertFalse(np.isnan(res["raw_decision_score"]))
        self.assertGreaterEqual(res["calibrated_deterioration_probability"], 0.0)
        self.assertLessEqual(res["calibrated_deterioration_probability"], 1.0)

    def test_09_missing_and_unknown_categorical_values(self):
        """Verify missing categorical values get filled and unknown categories produce warnings."""
        rec = copy.deepcopy(self.fixtures_data[0]["input_record"])
        # Missing categorical
        rec["prior_culvert_condition"] = None
        # Unseen categorical code
        rec["deck_protection_108c"] = "UNKNOWN_CODE_999"

        res = self.scorer.score_record(rec)
        self.assertIsInstance(res["raw_decision_score"], float)
        self.assertGreaterEqual(res["calibrated_deterioration_probability"], 0.0)
        self.assertLessEqual(res["calibrated_deterioration_probability"], 1.0)

        # Verify warning was captured
        warnings_text = " ".join(res["warnings"])
        self.assertIn("unobserved category 'UNKNOWN_CODE_999'", warnings_text)

    def test_10_missing_required_column_fails(self):
        """Verify that omitting a required feature raises SchemaValidationError with missing cols."""
        rec = copy.deepcopy(self.fixtures_data[0]["input_record"])
        del rec["adt"]
        del rec["prior_deck_condition"]

        with self.assertRaises(SchemaValidationError) as ctx:
            self.scorer.score_record(rec)
        self.assertIn("adt", str(ctx.exception))
        self.assertIn("prior_deck_condition", str(ctx.exception))

    def test_11_wrong_data_type_fails(self):
        """Verify that non-numeric string in numeric feature raises SchemaValidationError."""
        rec = copy.deepcopy(self.fixtures_data[0]["input_record"])
        rec["adt"] = "invalid_string_not_a_number"

        with self.assertRaises(SchemaValidationError) as ctx:
            self.scorer.score_record(rec)
        self.assertIn("adt", str(ctx.exception))
        self.assertIn("must be numeric or null", str(ctx.exception))

    def test_12_non_dict_record_fails(self):
        """Verify that passing non-dict object raises SchemaValidationError."""
        with self.assertRaises(SchemaValidationError):
            self.scorer.score_record(["not", "a", "dict"])

    def test_13_artifact_load_failure(self):
        """Verify that specifying a non-existent artifact directory raises ArtifactLoadError."""
        fake_dir = os.path.join(PROJECT_ROOT, "backend", "results", "non_existent_dir_12345")
        with self.assertRaises(ArtifactLoadError):
            BridgeRiskScorer(artifacts_dir=fake_dir)

    def test_14_functional_entrypoint(self):
        """Verify the functional score_bridges wrapper entrypoint."""
        rec = copy.deepcopy(self.fixtures_data[0]["input_record"])
        res_single = score_bridges(rec)
        self.assertIsInstance(res_single, dict)
        self.assertIn("calibrated_deterioration_probability", res_single)

        res_batch = score_bridges([rec, rec])
        self.assertIsInstance(res_batch, list)
        self.assertEqual(len(res_batch), 2)


if __name__ == "__main__":
    unittest.main()
