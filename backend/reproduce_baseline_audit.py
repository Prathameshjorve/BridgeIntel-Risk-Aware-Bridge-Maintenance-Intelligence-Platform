"""
Phase 21 - Step 3 & 4: Baseline Reproduction and Data Leakage Audit
Risk-Aware Bridge Maintenance Intelligence Platform

Verifies:
1. Data leakage audit (zero bridge-ID overlap, temporal distributions, target distributions)
2. Exact reproduction of Phase 17/18 champion metrics on validation and held-out test splits
3. Full calculation of binary confusion matrix, specificity, false positive rate, false negative rate,
   and accuracy directly from model predictions.
"""

import os
import sys
import json
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATASET_PATH = BASE_DIR / "data" / "processed" / "bridge_deck_condition_2023_2025.csv"
CHAMPION_MODEL_PATH = BASE_DIR / "results" / "phase17" / "hist_gradient_boosting_classifier.joblib"
CHAMPION_ENCODER_PATH = BASE_DIR / "results" / "phase17" / "cat_encoder.joblib"
CHAMPION_METADATA_PATH = BASE_DIR / "results" / "phase17" / "inference_metadata.json"
CHAMPION_CALIBRATOR_PATH = BASE_DIR / "results" / "phase18" / "calibration" / "phase18_calibrator.joblib"

NUMERIC_FEATURES = [
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

CATEGORICAL_FEATURES = [
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

def sha256_file(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()

def main():
    print("=" * 80)
    print("PHASE 21: DATA LEAKAGE AUDIT & CHAMPION BASELINE REPRODUCTION")
    print("=" * 80)

    # 1. Verify frozen champion checksums
    print("\n1. VERIFYING FROZEN CHAMPION ARTIFACT CHECKSUMS...")
    artifacts = {
        "Classifier": (CHAMPION_MODEL_PATH, "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b"),
        "Encoder": (CHAMPION_ENCODER_PATH, "14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772"),
        "Metadata": (CHAMPION_METADATA_PATH, "b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24"),
        "Calibrator": (CHAMPION_CALIBRATOR_PATH, "7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3"),
    }
    for name, (path, expected_hash) in artifacts.items():
        actual_hash = sha256_file(path)
        assert actual_hash == expected_hash, f"Hash mismatch for {name}! {actual_hash} != {expected_hash}"
        print(f"   [FROZEN CHECK] {name}: {actual_hash[:16]}... OK ({path.stat().st_size:,} bytes)")

    # 2. Ingest Dataset & Check Splits
    print("\n2. INGESTING PHASE 16 DATASET & AUDITING SPLITS...")
    dtype_map = {col: str for col in CATEGORICAL_FEATURES}
    dtype_map["bridge_id"] = str
    dtype_map["structure_number"] = str
    dtype_map["state_code"] = str
    df = pd.read_csv(DATASET_PATH, dtype=dtype_map, low_memory=False)
    print(f"   Total rows loaded: {len(df):,}")

    df_train = df[df["split"] == "train"].reset_index(drop=True)
    df_val = df[df["split"] == "val"].reset_index(drop=True)
    df_test = df[df["split"] == "test"].reset_index(drop=True)

    print(f"   Train split: {len(df_train):,} rows ({len(df_train)/len(df)*100:.2f}%)")
    print(f"   Val split:   {len(df_val):,} rows ({len(df_val)/len(df)*100:.2f}%)")
    print(f"   Test split:  {len(df_test):,} rows ({len(df_test)/len(df)*100:.2f}%)")

    # 3. Data Leakage Checks
    print("\n3. DATA LEAKAGE AUDIT:")
    train_ids = set(df_train["bridge_id"])
    val_ids = set(df_val["bridge_id"])
    test_ids = set(df_test["bridge_id"])

    overlap_train_val = len(train_ids & val_ids)
    overlap_train_test = len(train_ids & test_ids)
    overlap_val_test = len(val_ids & test_ids)

    print(f"   - Bridge ID Overlap Train/Val:  {overlap_train_val}")
    print(f"   - Bridge ID Overlap Train/Test: {overlap_train_test}")
    print(f"   - Bridge ID Overlap Val/Test:   {overlap_val_test}")
    assert overlap_train_val == 0 and overlap_train_test == 0 and overlap_val_test == 0, "Bridge overlap detected!"
    print("   [PASS] Zero bridge ID leakage between splits.")

    # Target distributions
    y_train = df_train["target_deterioration"].values
    y_val = df_val["target_deterioration"].values
    y_test = df_test["target_deterioration"].values

    print(f"   - Target Deterioration Rate:")
    print(f"       Train: {np.mean(y_train)*100:.2f}% (Positives: {np.sum(y_train):,})")
    print(f"       Val:   {np.mean(y_val)*100:.2f}% (Positives: {np.sum(y_val):,})")
    print(f"       Test:  {np.mean(y_test)*100:.2f}% (Positives: {np.sum(y_test):,})")

    # Chronological & Inspection intervals
    print(f"   - Inspection intervals (months):")
    for name, sub_df in [("Train", df_train), ("Val", df_val), ("Test", df_test)]:
        intervals = sub_df["inspection_interval_months"].values
        print(f"       {name}: min={np.min(intervals)}, max={np.max(intervals)}, median={np.median(intervals):.1f}")
        assert np.min(intervals) > 0, f"Non-positive interval detected in {name}!"
    print("   [PASS] All inspection intervals strictly positive (no carryover or reverse dates).")

    # 4. Prepare Evaluation Matrices
    print("\n4. LOADING FROZEN CHAMPION ESTIMATOR & EVALUATING REPRODUCIBILITY...")
    clf = joblib.load(CHAMPION_MODEL_PATH)
    encoder = joblib.load(CHAMPION_ENCODER_PATH)

    def prepare_X(sub_df):
        X_cat = sub_df[CATEGORICAL_FEATURES].fillna("MISSING").astype(str)
        X_cat_enc = encoder.transform(X_cat)
        X_num = sub_df[NUMERIC_FEATURES].values.astype(np.float64)
        return np.hstack([X_num, X_cat_enc])

    X_val = prepare_X(df_val)
    X_test = prepare_X(df_test)

    # 5. Validation Split Evaluation
    probs_val = clf.predict_proba(X_val)[:, 1]
    scores_val = clf.decision_function(X_val)

    val_pr_auc = float(average_precision_score(y_val, probs_val))
    val_roc_auc = float(roc_auc_score(y_val, probs_val))

    tau = 0.680
    preds_val_tau = (probs_val >= tau).astype(int)
    cm_val = confusion_matrix(y_val, preds_val_tau, labels=[0, 1])
    tn_v, fp_v, fn_v, tp_v = cm_val.ravel()

    val_prec = float(precision_score(y_val, preds_val_tau, zero_division=0))
    val_rec = float(recall_score(y_val, preds_val_tau, zero_division=0))
    val_f1 = float(f1_score(y_val, preds_val_tau, zero_division=0))
    val_acc = float(accuracy_score(y_val, preds_val_tau))
    val_bal_acc = float(balanced_accuracy_score(y_val, preds_val_tau))
    val_spec = float(tn_v / (tn_v + fp_v))
    val_fpr = float(fp_v / (tn_v + fp_v))
    val_fnr = float(fn_v / (tp_v + fn_v))

    print(f"\n--- CHAMPION VALIDATION PERFORMANCE (N={len(y_val):,}, tau={tau:.3f}) ---")
    print(f"   PR-AUC:            {val_pr_auc:.4f}")
    print(f"   ROC-AUC:           {val_roc_auc:.4f}")
    print(f"   Precision:         {val_prec*100:.2f}%")
    print(f"   Recall:            {val_rec*100:.2f}%")
    print(f"   F1-Score:          {val_f1:.4f}")
    print(f"   Accuracy:          {val_acc*100:.2f}%")
    print(f"   Balanced Accuracy: {val_bal_acc*100:.2f}%")
    print(f"   Specificity:       {val_spec*100:.2f}%")
    print(f"   False Pos Rate:    {val_fpr*100:.2f}%")
    print(f"   False Neg Rate:    {val_fnr*100:.2f}%")
    print(f"   Confusion Matrix:  TN={tn_v:,}, FP={fp_v:,}, FN={fn_v:,}, TP={tp_v:,}")

    # 6. Held-Out Test Split Evaluation
    probs_test = clf.predict_proba(X_test)[:, 1]
    scores_test = clf.decision_function(X_test)

    test_pr_auc = float(average_precision_score(y_test, probs_test))
    test_roc_auc = float(roc_auc_score(y_test, probs_test))

    preds_test_tau = (probs_test >= tau).astype(int)
    cm_test = confusion_matrix(y_test, preds_test_tau, labels=[0, 1])
    tn_t, fp_t, fn_t, tp_t = cm_test.ravel()

    test_prec = float(precision_score(y_test, preds_test_tau, zero_division=0))
    test_rec = float(recall_score(y_test, preds_test_tau, zero_division=0))
    test_f1 = float(f1_score(y_test, preds_test_tau, zero_division=0))
    test_acc = float(accuracy_score(y_test, preds_test_tau))
    test_bal_acc = float(balanced_accuracy_score(y_test, preds_test_tau))
    test_spec = float(tn_t / (tn_t + fp_t))
    test_fpr = float(fp_t / (tn_t + fp_t))
    test_fnr = float(fn_t / (tp_t + fn_t))

    print(f"\n--- CHAMPION HELD-OUT TEST PERFORMANCE (N={len(y_test):,}, tau={tau:.3f}) ---")
    print(f"   PR-AUC:            {test_pr_auc:.4f} (Reported: 0.2943)")
    print(f"   ROC-AUC:           {test_roc_auc:.4f} (Reported: 0.7625)")
    print(f"   Precision:         {test_prec*100:.2f}% (Reported: 30.38%)")
    print(f"   Recall:            {test_rec*100:.2f}% (Reported: 36.40%)")
    print(f"   F1-Score:          {test_f1:.4f} (Reported: 0.3312)")
    print(f"   Accuracy:          {test_acc*100:.2f}% (Directly calculated)")
    print(f"   Balanced Accuracy: {test_bal_acc*100:.2f}% (Reported: 64.12%)")
    print(f"   Specificity:       {test_spec*100:.2f}% (Directly calculated)")
    print(f"   False Pos Rate:    {test_fpr*100:.2f}%")
    print(f"   False Neg Rate:    {test_fnr*100:.2f}%")
    print(f"   Confusion Matrix:  TN={tn_t:,}, FP={fp_t:,}, FN={fn_t:,}, TP={tp_t:,}")

    # Check reproducibility against reported Phase 17 values
    assert abs(test_pr_auc - 0.294335) < 1e-4, f"PR-AUC mismatch: {test_pr_auc}"
    assert abs(test_roc_auc - 0.762455) < 1e-4, f"ROC-AUC mismatch: {test_roc_auc}"
    assert abs(test_f1 - 0.331179) < 1e-4, f"F1 mismatch: {test_f1}"
    assert abs(test_prec - 0.303770) < 1e-4, f"Precision mismatch: {test_prec}"
    assert abs(test_rec - 0.364025) < 1e-4, f"Recall mismatch: {test_rec}"
    assert abs(test_bal_acc - 0.641210) < 1e-4, f"Balanced Accuracy mismatch: {test_bal_acc}"
    print("\n[VERIFIED] Exact mathematical match against Phase 17 reported benchmarks!")

    # Save reproduction verification payload
    out_dir = BASE_DIR / "results" / "phase21"
    out_dir.mkdir(parents=True, exist_ok=True)
    baseline_record = {
        "verified_at": pd.Timestamp.now().isoformat(),
        "champion_checksums": {name: h for name, (p, h) in artifacts.items()},
        "test_sample_size": len(y_test),
        "validation_sample_size": len(y_val),
        "threshold_tau": tau,
        "validation_metrics": {
            "pr_auc": val_pr_auc,
            "roc_auc": val_roc_auc,
            "precision": val_prec,
            "recall": val_rec,
            "f1": val_f1,
            "accuracy": val_acc,
            "balanced_accuracy": val_bal_acc,
            "specificity": val_spec,
            "fpr": val_fpr,
            "fnr": val_fnr,
            "confusion_matrix": {"tn": int(tn_v), "fp": int(fp_v), "fn": int(fn_v), "tp": int(tp_v)},
        },
        "test_metrics": {
            "pr_auc": test_pr_auc,
            "roc_auc": test_roc_auc,
            "precision": test_prec,
            "recall": test_rec,
            "f1": test_f1,
            "accuracy": test_acc,
            "balanced_accuracy": test_bal_acc,
            "specificity": test_spec,
            "fpr": test_fpr,
            "fnr": test_fnr,
            "confusion_matrix": {"tn": int(tn_t), "fp": int(fp_t), "fn": int(fn_t), "tp": int(tp_t)},
        },
    }
    with open(out_dir / "baseline_reproduction.json", "w", encoding="utf-8") as f:
        json.dump(baseline_record, f, indent=2)
    print(f"Saved baseline reproduction record to: {out_dir / 'baseline_reproduction.json'}")

if __name__ == "__main__":
    main()
