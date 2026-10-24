"""
Phase 18C: Inference-Only Bridge Deterioration Risk Scoring Service
Risk-Aware Bridge Maintenance Intelligence Platform

This service provides an inference-only interface for scoring bridge deck
deterioration risk using the Phase 17 trained HistGradientBoostingClassifier
and Phase 18B refitted Platt calibrator.

CRITICAL ENGINEERING & SCIENTIFIC SEMANTICS:
- The model outputs an empirical 2-year probability that a bridge's NBI deck condition
  rating will decrease by >= 1 point (routine biennial degradation on the 0-9 scale).
- It does NOT predict bridge collapse, catastrophic physical failure, or structural safety.
- It does NOT measure or certify maintenance efficacy.
- Model scores are kept strictly isolated from consequence scoring, network criticality,
  detour costs, and budget optimization logic.
"""

import os
import json
import hashlib
import warnings
from typing import Dict, List, Any, Optional, Union
import numpy as np
import pandas as pd
import joblib


# Canonical 26-feature schema
NUMERIC_FEATURES: List[str] = [
    "prior_deck_condition",
    "structure_len_mt",
    "max_span_len_mt",
    "deck_width_mt",
    "traffic_lanes_on",
    "adt",
    "percent_adt_truck",
    "detour_kilos",
    "year_built",
    "structure_age_at_inspection",
    "prior_inspect_month",
    "prior_inspect_year",
    "inspect_freq_months",
]

CATEGORICAL_FEATURES: List[str] = [
    "prior_superstructure_condition",
    "prior_substructure_condition",
    "prior_culvert_condition",
    "structure_kind_043a",
    "structure_type_043b",
    "deck_structure_type_107",
    "surface_type_108a",
    "membrane_type_108b",
    "deck_protection_108c",
    "functional_class",
    "maintenance_responsibility",
    "owner",
    "state_code",
]

ALL_REQUIRED_FEATURES: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES
TOTAL_FEATURE_COUNT: int = len(ALL_REQUIRED_FEATURES)  # 26

# 2-digit FHWA codes that require zero-padding if integer/single-digit passed
TWO_DIGIT_FHWA_FIELDS: set = {
    "structure_type_043b",
    "functional_class",
    "maintenance_responsibility",
    "owner",
    "state_code",
}

SEMANTICS_DISCLAIMER: str = (
    "Estimated 2-year probability that subsequent NBI deck condition rating drops "
    "below baseline rating (routine biennial degradation on NBI 0-9 scale). "
    "Does NOT predict bridge collapse, physical structural failure, or maintenance efficacy."
)


class BridgeScoringError(Exception):
    """Base exception for bridge deterioration scoring service."""
    pass


class ArtifactLoadError(BridgeScoringError):
    """Raised when model or calibrator artifacts cannot be found, loaded, or verified."""
    pass


class SchemaValidationError(BridgeScoringError):
    """Raised when incoming records violate required feature schema, types, or structure."""
    pass


class FeatureProcessingError(BridgeScoringError):
    """Raised when feature transformation fails on record values."""
    pass


class BridgeRiskScorer:
    """
    Inference-only scoring engine for biennial bridge deck deterioration risk.
    Loads and caches Phase 17 classifier and Phase 18B calibrator artifacts once.
    """

    def __init__(
        self,
        artifacts_dir: Optional[str] = None,
        calibration_dir: Optional[str] = None,
        verify_checksums: bool = True,
    ):
        """
        Initialize scorer with paths to Phase 17 and Phase 18 artifacts.
        
        Args:
            artifacts_dir: Path to Phase 17 results (classifier, encoder, metadata).
            calibration_dir: Path to Phase 18 calibration results (calibrator, manifest).
            verify_checksums: If True, validates SHA-256 hashes against manifests.
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.phase17_dir = artifacts_dir or os.path.join(project_root, "backend", "results", "phase17")
        self.phase18_cal_dir = calibration_dir or os.path.join(project_root, "backend", "results", "phase18", "calibration")
        
        self.classifier_path = os.path.join(self.phase17_dir, "hist_gradient_boosting_classifier.joblib")
        self.encoder_path = os.path.join(self.phase17_dir, "cat_encoder.joblib")
        self.metadata_path = os.path.join(self.phase17_dir, "inference_metadata.json")
        self.calibrator_path = os.path.join(self.phase18_cal_dir, "phase18_calibrator.joblib")
        self.p17_manifest_path = os.path.join(self.phase17_dir, "serialization_manifest.json")
        self.p18_manifest_path = os.path.join(self.phase18_cal_dir, "calibration_manifest.json")

        self.classifier = None
        self.encoder = None
        self.metadata = None
        self.calibrator = None
        self.known_categories_per_col = {}

        self._load_artifacts(verify_checksums)

    def _compute_sha256(self, filepath: str) -> str:
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _load_artifacts(self, verify_checksums: bool) -> None:
        """Loads and verifies all serialized artifacts."""
        for path, name in [
            (self.classifier_path, "Classifier"),
            (self.encoder_path, "Categorical Encoder"),
            (self.metadata_path, "Inference Metadata"),
            (self.calibrator_path, "Calibrator"),
        ]:
            if not os.path.exists(path):
                raise ArtifactLoadError(f"Required artifact not found: {name} at '{path}'")

        if verify_checksums:
            # Check Phase 17 manifest
            if os.path.exists(self.p17_manifest_path):
                try:
                    with open(self.p17_manifest_path, "r", encoding="utf-8") as f:
                        sm = json.load(f)
                    c_hash = self._compute_sha256(self.classifier_path)
                    e_hash = self._compute_sha256(self.encoder_path)
                    m_hash = self._compute_sha256(self.metadata_path)
                    
                    expected_c = sm.get("artifact_checksums_sha256", {}).get("hist_gradient_boosting_classifier.joblib")
                    expected_e = sm.get("artifact_checksums_sha256", {}).get("cat_encoder.joblib")
                    expected_m = sm.get("artifact_checksums_sha256", {}).get("inference_metadata.json")

                    if expected_c and c_hash != expected_c:
                        raise ArtifactLoadError(f"Classifier SHA-256 mismatch! Got {c_hash}, expected {expected_c}")
                    if expected_e and e_hash != expected_e:
                        raise ArtifactLoadError(f"Encoder SHA-256 mismatch! Got {e_hash}, expected {expected_e}")
                    if expected_m and m_hash != expected_m:
                        raise ArtifactLoadError(f"Metadata SHA-256 mismatch! Got {m_hash}, expected {expected_m}")
                except Exception as ex:
                    if isinstance(ex, ArtifactLoadError):
                        raise
                    warnings.warn(f"Warning: Could not verify Phase 17 manifest checksums: {ex}")

            # Check Phase 18 calibration manifest
            if os.path.exists(self.p18_manifest_path):
                try:
                    with open(self.p18_manifest_path, "r", encoding="utf-8") as f:
                        cm = json.load(f)
                    cal_hash = self._compute_sha256(self.calibrator_path)
                    expected_cal = cm.get("champion_calibrator", {}).get("sha256")
                    if expected_cal and cal_hash != expected_cal:
                        raise ArtifactLoadError(f"Calibrator SHA-256 mismatch! Got {cal_hash}, expected {expected_cal}")
                except Exception as ex:
                    if isinstance(ex, ArtifactLoadError):
                        raise
                    warnings.warn(f"Warning: Could not verify Phase 18 manifest checksums: {ex}")

        try:
            self.classifier = joblib.load(self.classifier_path)
            self.encoder = joblib.load(self.encoder_path)
            self.calibrator = joblib.load(self.calibrator_path)
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self.metadata = json.load(f)
        except Exception as e:
            raise ArtifactLoadError(f"Failed to load joblib/json artifacts: {e}") from e

        # Cache known categories for input warnings
        if hasattr(self.encoder, "categories_"):
            for idx, col in enumerate(CATEGORICAL_FEATURES):
                if idx < len(self.encoder.categories_):
                    self.known_categories_per_col[col] = set(self.encoder.categories_[idx])

    def _validate_record_schema(self, record: Dict[str, Any], record_idx: int = 0) -> List[str]:
        """
        Validates record keys and data types against the canonical 26-feature contract.
        Returns a list of non-fatal warnings.
        """
        if not isinstance(record, dict):
            raise SchemaValidationError(f"Record at index {record_idx} must be a dict, got {type(record).__name__}")

        missing_cols = [col for col in ALL_REQUIRED_FEATURES if col not in record]
        if missing_cols:
            raise SchemaValidationError(
                f"Record at index {record_idx} is missing {len(missing_cols)} required features: {missing_cols}"
            )

        warnings_list = []

        # Validate numeric features
        for col in NUMERIC_FEATURES:
            val = record[col]
            if val is not None and not pd.isna(val):
                try:
                    float(val)
                except (ValueError, TypeError):
                    raise SchemaValidationError(
                        f"Record {record_idx}: feature '{col}' must be numeric or null, got '{val}' (type {type(val).__name__})"
                    )

        # Validate categorical features
        for col in CATEGORICAL_FEATURES:
            val = record[col]
            if val is not None and not pd.isna(val):
                val_str = str(val).strip()
                # Check for zero-padding normalization
                if col in TWO_DIGIT_FHWA_FIELDS and len(val_str) == 1 and val_str.isdigit():
                    padded = val_str.zfill(2)
                    warnings_list.append(
                        f"Record {record_idx}: normalized single-digit FHWA code '{val_str}' to '{padded}' for '{col}'."
                    )
                    val_str = padded
                
                known = self.known_categories_per_col.get(col, set())
                if known and val_str not in known and val_str != "MISSING":
                    warnings_list.append(
                        f"Record {record_idx}: unobserved category '{val_str}' for feature '{col}'; mapped to unknown indicator (-1)."
                    )

        return warnings_list

    def _prepare_feature_matrix(self, records: List[Dict[str, Any]]) -> np.ndarray:
        """
        Transforms validated list of records into model-ready numpy array X with shape (N, 26).
        Columns 0..12: Numeric features.
        Columns 13..25: Encoded categorical features.
        """
        n_samples = len(records)
        X_num = np.zeros((n_samples, len(NUMERIC_FEATURES)), dtype=np.float64)
        cat_matrix = []

        for i, rec in enumerate(records):
            # Numeric values (None / NaN stays np.nan for HistGradientBoosting native handling)
            for j, col in enumerate(NUMERIC_FEATURES):
                val = rec[col]
                if val is None or pd.isna(val):
                    X_num[i, j] = np.nan
                else:
                    X_num[i, j] = float(val)

            # Categorical values
            row_cats = []
            for col in CATEGORICAL_FEATURES:
                val = rec[col]
                if val is None or pd.isna(val):
                    row_cats.append("MISSING")
                else:
                    val_str = str(val).strip()
                    if col in TWO_DIGIT_FHWA_FIELDS and len(val_str) == 1 and val_str.isdigit():
                        val_str = val_str.zfill(2)
                    row_cats.append(val_str)
            cat_matrix.append(row_cats)

        cat_df = pd.DataFrame(cat_matrix, columns=CATEGORICAL_FEATURES)
        X_cat_enc = self.encoder.transform(cat_df)

        X = np.hstack([X_num, X_cat_enc])
        return X

    def score_batch(self, records: Union[List[Dict[str, Any]], pd.DataFrame]) -> List[Dict[str, Any]]:
        """
        Scores a batch of bridge records.
        
        Args:
            records: List of dictionaries or pandas DataFrame containing the 26 required features.
            
        Returns:
            List of scoring result dictionaries.
        """
        if isinstance(records, pd.DataFrame):
            records_list = records.to_dict(orient="records")
        elif isinstance(records, list):
            records_list = records
        else:
            raise SchemaValidationError(f"Expected list of dicts or DataFrame, got {type(records).__name__}")

        if len(records_list) == 0:
            return []

        all_warnings = []
        for idx, rec in enumerate(records_list):
            rec_warnings = self._validate_record_schema(rec, record_idx=idx)
            all_warnings.append(rec_warnings)

        X = self._prepare_feature_matrix(records_list)

        # 1. Decision function gives raw uncalibrated margin / score z
        raw_scores = self.classifier.decision_function(X)

        # 2. Platt calibrator expects raw decision scores with shape (N, 1)
        raw_scores_reshaped = raw_scores.reshape(-1, 1)
        calibrated_probs = self.calibrator.predict_proba(raw_scores_reshaped)[:, 1]

        results = []
        for i, rec in enumerate(records_list):
            raw_s = float(raw_scores[i])
            cal_p = float(calibrated_probs[i])
            
            # Enforce probability bounds [0.0, 1.0]
            cal_p_bounded = max(0.0, min(1.0, cal_p))

            res = {
                "raw_decision_score": raw_s,
                "calibrated_deterioration_probability": cal_p_bounded,
                "prediction_semantics": SEMANTICS_DISCLAIMER,
                "model_metadata": {
                    "classifier_type": "HistGradientBoostingClassifier",
                    "calibrator_type": "Platt Scaling (LogisticRegression)",
                    "target_name": "target_deterioration",
                    "features_count": TOTAL_FEATURE_COUNT,
                    "service_phase": "Phase 18C",
                },
                "warnings": all_warnings[i],
            }
            if "bridge_id" in rec:
                res["bridge_id"] = str(rec["bridge_id"])

            results.append(res)

        return results

    def score_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Scores a single bridge record.
        
        Args:
            record: Dictionary containing the 26 required features.
            
        Returns:
            Scoring result dictionary.
        """
        results = self.score_batch([record])
        return results[0]


# Lazy module-level singleton instance
_GLOBAL_SCORER: Optional[BridgeRiskScorer] = None


def get_default_scorer(verify_checksums: bool = True) -> BridgeRiskScorer:
    """Returns the cached global BridgeRiskScorer singleton."""
    global _GLOBAL_SCORER
    if _GLOBAL_SCORER is None:
        _GLOBAL_SCORER = BridgeRiskScorer(verify_checksums=verify_checksums)
    return _GLOBAL_SCORER


def score_bridges(
    records: Union[Dict[str, Any], List[Dict[str, Any]], pd.DataFrame],
    scorer: Optional[BridgeRiskScorer] = None,
) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Main reusable functional entrypoint for scoring bridge deck deterioration risk.
    
    Args:
        records: Single record dict, list of record dicts, or pandas DataFrame.
        scorer: Optional BridgeRiskScorer instance (defaults to cached singleton).
        
    Returns:
        Single result dict (if dict passed) or list of result dicts.
    """
    engine = scorer or get_default_scorer()
    if isinstance(records, dict):
        return engine.score_record(records)
    return engine.score_batch(records)
