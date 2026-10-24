"""
Phase 22A & 22B: Out-of-Fold Calibrated Predictions, Reproducible Threshold Analysis & Workload Trade-Offs
Risk-Aware Bridge Maintenance Intelligence Platform

Mandatory Safeguards:
1. Strict preservation of backend/score_bridge_risk.py and backend/results/phase17/* byte-for-byte.
2. Checksums verified before and after execution.
3. 5-fold StratifiedKFold inside training partition (N=304,541, random_state=42).
   Strictly in-fold OrdinalEncoder fitting and in-fold early stopping.
4. Out-of-sample Platt calibration: no observation evaluated by a calibrator fitted on its own outcome.
5. Threshold optimization executed strictly on training out-of-fold calibrated probabilities (zero test leakage).
6. Operational policy evaluation: Max F1, Workload-constrained, High-Recall, High-Precision, and Origin 0.165.
7. Held-out test split (N=65,580) evaluated strictly with frozen thresholds as an audit benchmark.
8. All outputs stored under backend/results/phase22/. No production models promoted.
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd
import joblib

import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import OrdinalEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    brier_score_loss,
    log_loss,
)

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DATASET_PATH = BASE_DIR / "data" / "processed" / "bridge_deck_condition_2023_2025.csv"
OUTPUT_DIR = BASE_DIR / "results" / "phase22"

P17_DIR = BASE_DIR / "results" / "phase17"
P18_DIR = BASE_DIR / "results" / "phase18" / "calibration"
P21B_DIR = BASE_DIR / "results" / "phase21b"

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

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def sha256_file(filepath: Path) -> str:
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_ece_mce(y_true, y_prob, n_bins=10):
    bin_edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    mce = 0.0
    total = len(y_true)
    bin_details = []
    for m in range(n_bins):
        low, high = bin_edges[m], bin_edges[m + 1]
        mask = (y_prob >= low) & (y_prob <= high) if m == 0 else (y_prob > low) & (y_prob <= high)
        count = int(np.sum(mask))
        if count > 0:
            mean_pred = float(np.mean(y_prob[mask]))
            obs_freq = float(np.mean(y_true[mask]))
            abs_err = abs(obs_freq - mean_pred)
            ece += (count / total) * abs_err
            if abs_err > mce:
                mce = abs_err
        else:
            mean_pred = float((low + high) / 2.0)
            obs_freq = 0.0
            abs_err = 0.0
        bin_details.append({
            "bin": m + 1,
            "low": float(low),
            "high": float(high),
            "count": count,
            "mean_pred": round(mean_pred, 5),
            "obs_freq": round(obs_freq, 5),
            "err": round(abs_err, 5),
        })
    return ece, mce, bin_details


def evaluate_threshold_point(y_true, probs, tau: float):
    preds = (probs >= tau).astype(int)
    p = float(precision_score(y_true, preds, zero_division=0))
    r = float(recall_score(y_true, preds, zero_division=0))
    f = float(f1_score(y_true, preds, zero_division=0))
    acc = float(accuracy_score(y_true, preds))
    bal_acc = float(balanced_accuracy_score(y_true, preds))
    cm = confusion_matrix(y_true, preds, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    total = len(y_true)
    workload = float((tp + fp) / total)
    return {
        "tau": round(float(tau), 4),
        "precision": round(p, 5),
        "recall": round(r, 5),
        "f1": round(f, 5),
        "accuracy": round(acc, 5),
        "balanced_accuracy": round(bal_acc, 5),
        "specificity": round(spec, 5),
        "workload_pct": round(workload * 100, 2),
        "bridges_inspected": int(tp + fp),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }


def run_threshold_sweep(y_true, probs, threshold_grid):
    records = []
    best_f1 = -1.0
    best_tau = 0.5
    for tau in threshold_grid:
        res = evaluate_threshold_point(y_true, probs, tau)
        if res["f1"] > best_f1:
            best_f1 = res["f1"]
            best_tau = float(tau)
        records.append(res)
    return best_tau, best_f1, records


def main():
    start_time = time.time()
    print("=" * 80)
    print("PHASE 22A & 22B: CALIBRATED OUT-OF-FOLD PREDICTIONS & DECISION WORKLOAD ANALYSIS")
    print("=" * 80)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # STEP 1: PRE-RUN CHECKSUMS (IMMUTABILITY VERIFICATION)
    # -------------------------------------------------------------------------
    print("\n--- STEP 1: VERIFY IMMUTABLE PRE-RUN CHECKSUMS ---")
    score_bridge_risk_path = BASE_DIR / "score_bridge_risk.py"
    p17_model_path = P17_DIR / "hist_gradient_boosting_classifier.joblib"
    p17_encoder_path = P17_DIR / "cat_encoder.joblib"
    p17_meta_path = P17_DIR / "inference_metadata.json"
    p17_manifest_path = P17_DIR / "serialization_manifest.json"
    p18_cal_path = P18_DIR / "phase18_calibrator.joblib"

    p21b_model_path = P21B_DIR / "phase21b_tuned_model.joblib"
    p21b_cal_path = P21B_DIR / "phase21b_calibrator.joblib"
    p21b_encoder_path = P21B_DIR / "phase21b_encoder.joblib"
    p21b_manifest_path = P21B_DIR / "phase21b_experiment_manifest.json"

    pre_checksums = {
        "score_bridge_risk.py": sha256_file(score_bridge_risk_path),
        "phase17_model": sha256_file(p17_model_path),
        "phase17_encoder": sha256_file(p17_encoder_path),
        "phase17_metadata": sha256_file(p17_meta_path),
        "phase17_manifest": sha256_file(p17_manifest_path),
        "phase18_calibrator": sha256_file(p18_cal_path),
        "phase21b_model": sha256_file(p21b_model_path),
        "phase21b_calibrator": sha256_file(p21b_cal_path),
        "phase21b_encoder": sha256_file(p21b_encoder_path),
        "phase21b_manifest": sha256_file(p21b_manifest_path),
    }

    assert pre_checksums["phase17_model"] == "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b"
    assert pre_checksums["phase18_calibrator"] == "7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3"
    assert pre_checksums["phase21b_model"] == "aa806c8185db465fd02536d2d4310638c499d41560ac759e0ea15d4a60f98443"
    print("  [VERIFIED] Phase 17/18 and Phase 21B checksums match baseline.")

    # -------------------------------------------------------------------------
    # STEP 2: INGEST DATASET & VERIFY SPLITS
    # -------------------------------------------------------------------------
    print("\n--- STEP 2: INGEST DATASET & VERIFY PARTITION PREVALENCE ---")
    dtype_map = {col: str for col in CATEGORICAL_FEATURES}
    dtype_map["bridge_id"] = str
    dtype_map["structure_number"] = str
    dtype_map["state_code"] = str
    df = pd.read_csv(DATASET_PATH, dtype=dtype_map, low_memory=False)

    df_train = df[df["split"] == "train"].reset_index(drop=True)
    df_val = df[df["split"] == "val"].reset_index(drop=True)
    df_test = df[df["split"] == "test"].reset_index(drop=True)

    n_train = len(df_train)
    n_val = len(df_val)
    n_test = len(df_test)
    y_train = df_train["target_deterioration"].values
    y_val = df_val["target_deterioration"].values
    y_test = df_test["target_deterioration"].values

    print(f"  Train: N={n_train:,} (prevalence {y_train.mean()*100:.2f}%)")
    print(f"  Val:   N={n_val:,} (prevalence {y_val.mean()*100:.2f}%)")
    print(f"  Test:  N={n_test:,} (prevalence {y_test.mean()*100:.2f}%)")
    assert df_train["bridge_id"].nunique() == n_train, "Duplicate bridge IDs in training set!"

    # -------------------------------------------------------------------------
    # PHASE 22A: GENERATE OUT-OF-FOLD CALIBRATED PREDICTIONS
    # -------------------------------------------------------------------------
    print("\n--- PHASE 22A: REGENERATE LEAKAGE-SAFE OUT-OF-FOLD CALIBRATED PREDICTIONS ---")
    print("Executing 5-fold StratifiedKFold cross-fitting for Phase 21B winning architecture C10...")
    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    folds_indices = list(skf.split(df_train, y_train))

    c10_params = {
        "learning_rate": 0.05,
        "max_iter": 200,
        "max_leaf_nodes": 63,
        "min_samples_leaf": 60,
        "l2_regularization": 1.0,
        "class_weight": None,
        "early_stopping": True,
        "validation_fraction": 0.1,
        "n_iter_no_change": 10,
        "random_state": 42,
    }

    oof_scores_p21b = np.zeros(n_train, dtype=np.float64)
    oof_probs_uncal_p21b = np.zeros(n_train, dtype=np.float64)
    cat_indices = list(range(len(NUMERIC_FEATURES), len(ALL_FEATURES)))

    # Fit 5 folds
    t0_cv = time.time()
    for fold_num, (tr_idx, val_idx) in enumerate(folds_indices, 1):
        df_tr_fold = df_train.iloc[tr_idx]
        df_val_fold = df_train.iloc[val_idx]

        enc_fold = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
        X_cat_tr = enc_fold.fit_transform(df_tr_fold[CATEGORICAL_FEATURES].fillna("MISSING").astype(str))
        X_cat_val = enc_fold.transform(df_val_fold[CATEGORICAL_FEATURES].fillna("MISSING").astype(str))

        X_num_tr = df_tr_fold[NUMERIC_FEATURES].values.astype(np.float64)
        X_num_val = df_val_fold[NUMERIC_FEATURES].values.astype(np.float64)

        X_tr = np.hstack([X_num_tr, X_cat_tr])
        X_val = np.hstack([X_num_val, X_cat_val])

        y_tr = y_train[tr_idx]

        clf = HistGradientBoostingClassifier(categorical_features=cat_indices, **c10_params)
        clf.fit(X_tr, y_tr)

        oof_scores_p21b[val_idx] = clf.decision_function(X_val)
        oof_probs_uncal_p21b[val_idx] = clf.predict_proba(X_val)[:, 1]
        print(f"  Fold {fold_num}/5 complete (iterations: {clf.n_iter_})")

    cv_time = time.time() - t0_cv
    print(f"5-Fold CV model fits completed in {cv_time:.2f}s")

    # Cross-fit Platt calibrator across the 5 folds
    print("Cross-fitting Platt scaling across the 5 out-of-fold partitions...")
    oof_probs_cal_p21b = np.zeros(n_train, dtype=np.float64)
    calibrator_fold_params = []

    for f_idx, (tr_idx, val_idx) in enumerate(folds_indices, 1):
        scores_tr_sub = oof_scores_p21b[tr_idx].reshape(-1, 1)
        y_tr_sub = y_train[tr_idx]
        scores_val_sub = oof_scores_p21b[val_idx].reshape(-1, 1)

        platt = LogisticRegression(C=1.0, solver="lbfgs", random_state=42)
        platt.fit(scores_tr_sub, y_tr_sub)
        oof_probs_cal_p21b[val_idx] = platt.predict_proba(scores_val_sub)[:, 1]

        calibrator_fold_params.append({
            "fold": f_idx,
            "coef": float(platt.coef_[0][0]),
            "intercept": float(platt.intercept_[0]),
        })

    # Trace origin of threshold 0.165
    diff_uncal_cal = np.abs(oof_probs_uncal_p21b - oof_probs_cal_p21b)
    trace_origin = {
        "finding": "Threshold tau=0.165 originated in Phase 21B from a 181-point threshold sweep on uncalibrated out-of-fold probabilities.",
        "uncalibrated_scale": {
            "mean": float(oof_probs_uncal_p21b.mean()),
            "std": float(oof_probs_uncal_p21b.std()),
            "min": float(oof_probs_uncal_p21b.min()),
            "max": float(oof_probs_uncal_p21b.max()),
            "base_rate": float(y_train.mean()),
        },
        "calibrated_scale": {
            "mean": float(oof_probs_cal_p21b.mean()),
            "std": float(oof_probs_cal_p21b.std()),
            "min": float(oof_probs_cal_p21b.min()),
            "max": float(oof_probs_cal_p21b.max()),
            "brier_score": float(brier_score_loss(y_train, oof_probs_cal_p21b)),
            "ece_10_bins": float(compute_ece_mce(y_train, oof_probs_cal_p21b)[0]),
        },
        "scale_difference": {
            "mean_abs_diff": float(diff_uncal_cal.mean()),
            "max_abs_diff": float(diff_uncal_cal.max()),
            "correlation": float(np.corrcoef(oof_probs_uncal_p21b, oof_probs_cal_p21b)[0, 1]),
        },
    }

    print("\nThreshold 0.165 Origin & Scale Reconciliation:")
    print(f"  Uncalibrated OOF mean: {trace_origin['uncalibrated_scale']['mean']:.4f} (Base rate: {trace_origin['uncalibrated_scale']['base_rate']:.4f})")
    print(f"  Calibrated OOF mean:   {trace_origin['calibrated_scale']['mean']:.4f}")
    print(f"  Mean abs diff between scales: {trace_origin['scale_difference']['mean_abs_diff']:.5f}")
    print(f"  Correlation between scales:   {trace_origin['scale_difference']['correlation']:.6f}")

    # -------------------------------------------------------------------------
    # PHASE 22B: REPRODUCIBLE THRESHOLD ANALYSIS ON CALIBRATED PROBABILITIES
    # -------------------------------------------------------------------------
    print("\n--- PHASE 22B: REPRODUCIBLE THRESHOLD ANALYSIS (STRICTLY ON TRAINING OOF) ---")
    threshold_grid = np.linspace(0.01, 0.90, 446)  # step 0.002
    best_tau_cal, best_f1_cal, sweep_cal = run_threshold_sweep(y_train, oof_probs_cal_p21b, threshold_grid)
    best_tau_uncal, best_f1_uncal, sweep_uncal = run_threshold_sweep(y_train, oof_probs_uncal_p21b, threshold_grid)

    print(f"  Optimal Calibrated Max F1 Threshold:   tau* = {best_tau_cal:.4f} (F1 = {best_f1_cal:.4f})")
    print(f"  Optimal Uncalibrated Max F1 Threshold: tau* = {best_tau_uncal:.4f} (F1 = {best_f1_uncal:.4f})")

    # Define operational policy presets strictly from training OOF calibrated probabilities
    df_sweep = pd.DataFrame(sweep_cal)

    # 1. Max F1 Policy
    opt_f1_record = evaluate_threshold_point(y_train, oof_probs_cal_p21b, best_tau_cal)

    # 2. Origin tau=0.165 Policy (evaluated on calibrated scale)
    origin_cal_record = evaluate_threshold_point(y_train, oof_probs_cal_p21b, 0.165)
    origin_uncal_record = evaluate_threshold_point(y_train, oof_probs_uncal_p21b, 0.165)

    # 3. Workload-constrained presets: 5%, 10%, 12.5%, 15% of bridge inventory
    def find_nearest_workload(target_pct):
        idx = (df_sweep["workload_pct"] - target_pct).abs().idxmin()
        return float(df_sweep.loc[idx, "tau"])

    tau_wl_5 = find_nearest_workload(5.0)
    tau_wl_10 = find_nearest_workload(10.0)
    tau_wl_12_5 = find_nearest_workload(12.5)
    tau_wl_15 = find_nearest_workload(15.0)

    # 4. Recall-targeted presets: 60%, 70%, 80% recall
    def find_nearest_recall(target_recall):
        idx = (df_sweep["recall"] - target_recall).abs().idxmin()
        return float(df_sweep.loc[idx, "tau"])

    tau_rec_60 = find_nearest_recall(0.60)
    tau_rec_70 = find_nearest_recall(0.70)
    tau_rec_80 = find_nearest_recall(0.80)

    # 5. Precision-targeted presets: 35%, 40%, 50% precision
    def find_nearest_precision(target_prec):
        idx = (df_sweep["precision"] - target_prec).abs().idxmin()
        return float(df_sweep.loc[idx, "tau"])

    tau_prec_35 = find_nearest_precision(0.35)
    tau_prec_40 = find_nearest_precision(0.40)
    tau_prec_50 = find_nearest_precision(0.50)

    policy_presets_oof = {
        "max_f1_balanced": {
            "policy_name": "Maximum F1 Balanced Inspection",
            "threshold": best_tau_cal,
            "metrics": opt_f1_record,
            "rationale": "Optimizes harmonic balance between true detections and inspection budget.",
        },
        "origin_threshold_calibrated": {
            "policy_name": "Origin Threshold on Calibrated Scale (tau=0.165)",
            "threshold": 0.165,
            "metrics": origin_cal_record,
            "rationale": "Historical threshold from Phase 21B evaluated directly on the calibrated probability scale.",
        },
        "origin_threshold_uncalibrated": {
            "policy_name": "Origin Threshold on Uncalibrated Scale (tau=0.165)",
            "threshold": 0.165,
            "metrics": origin_uncal_record,
            "rationale": "Historical reference point matching the exact Phase 21B uncalibrated derivation.",
        },
        "workload_5_pct": {
            "policy_name": "Tight Budget Workload Cap (5% of Inventory)",
            "threshold": tau_wl_5,
            "metrics": evaluate_threshold_point(y_train, oof_probs_cal_p21b, tau_wl_5),
            "rationale": "Restricts physical inspections to the highest-risk 5% of the portfolio.",
        },
        "workload_10_pct": {
            "policy_name": "Standard Inspection Workload (10% of Inventory)",
            "threshold": tau_wl_10,
            "metrics": evaluate_threshold_point(y_train, oof_probs_cal_p21b, tau_wl_10),
            "rationale": "Targets an annual/biennial inspection capacity matching typical State DOT capacity (10%).",
        },
        "workload_12_5_pct": {
            "policy_name": "Expanded Maintenance Workload (12.5% of Inventory)",
            "threshold": tau_wl_12_5,
            "metrics": evaluate_threshold_point(y_train, oof_probs_cal_p21b, tau_wl_12_5),
            "rationale": "Enables proactive maintenance across 12.5% of the portfolio.",
        },
        "workload_15_pct": {
            "policy_name": "High-Capacity Inspection Workload (15% of Inventory)",
            "threshold": tau_wl_15,
            "metrics": evaluate_threshold_point(y_train, oof_probs_cal_p21b, tau_wl_15),
            "rationale": "Accommodates comprehensive inspection campaigns with expanded field teams.",
        },
        "recall_70_pct": {
            "policy_name": "Safety-Critical Policy (70% Recall Target)",
            "threshold": tau_rec_70,
            "metrics": evaluate_threshold_point(y_train, oof_probs_cal_p21b, tau_rec_70),
            "rationale": "Risk-averse policy designed to identify at least 70% of deteriorating structures.",
        },
        "precision_40_pct": {
            "policy_name": "High-Efficiency Policy (40% Precision Target)",
            "threshold": tau_prec_40,
            "metrics": evaluate_threshold_point(y_train, oof_probs_cal_p21b, tau_prec_40),
            "rationale": "Resource-conservative policy minimizing wasted inspections (2 out of 5 flags true).",
        },
    }

    print("\nPolicy Presets Derived from Training OOF Calibrated Probabilities:")
    for k, v in policy_presets_oof.items():
        m = v["metrics"]
        print(f"  {v['policy_name']:<48} | tau={v['threshold']:.4f} | F1={m['f1']:.4f} | Prec={m['precision']*100:.1f}% | Rec={m['recall']*100:.1f}% | Workload={m['workload_pct']:.1f}% ({m['bridges_inspected']:,} bridges)")

    # -------------------------------------------------------------------------
    # STEP 3: CONSISTENT TEST SET AUDIT COMPARISON (PHASE 21B VS PHASE 17)
    # -------------------------------------------------------------------------
    print("\n--- STEP 3: HELD-OUT TEST AUDIT COMPARISON (N=65,580) ---")
    print("Evaluating Phase 21B and Phase 17 under identical frozen policy presets...")

    # Load frozen production models & calibrators
    p17_model = joblib.load(p17_model_path)
    p17_encoder = joblib.load(p17_encoder_path)
    p18_calibrator = joblib.load(p18_cal_path)

    p21b_model = joblib.load(p21b_model_path)
    p21b_encoder = joblib.load(p21b_encoder_path)
    p21b_calibrator = joblib.load(p21b_cal_path)

    # Transform test set for Phase 17
    X_cat_test_p17 = p17_encoder.transform(df_test[CATEGORICAL_FEATURES].fillna("MISSING").astype(str))
    X_num_test_p17 = df_test[NUMERIC_FEATURES].values.astype(np.float64)
    X_test_p17 = np.hstack([X_num_test_p17, X_cat_test_p17])

    scores_test_p17 = p17_model.decision_function(X_test_p17)
    probs_uncal_test_p17 = p17_model.predict_proba(X_test_p17)[:, 1]
    probs_cal_test_p17 = p18_calibrator.predict_proba(scores_test_p17.reshape(-1, 1))[:, 1]

    # Transform test set for Phase 21B
    X_cat_test_p21b = p21b_encoder.transform(df_test[CATEGORICAL_FEATURES].fillna("MISSING").astype(str))
    X_num_test_p21b = df_test[NUMERIC_FEATURES].values.astype(np.float64)
    X_test_p21b = np.hstack([X_num_test_p21b, X_cat_test_p21b])

    scores_test_p21b = p21b_model.decision_function(X_test_p21b)
    probs_uncal_test_p21b = p21b_model.predict_proba(X_test_p21b)[:, 1]
    probs_cal_test_p21b = p21b_calibrator.predict_proba(scores_test_p21b.reshape(-1, 1))[:, 1]

    # Overall test calibration metrics
    brier_p17 = float(brier_score_loss(y_test, probs_cal_test_p17))
    brier_p21b = float(brier_score_loss(y_test, probs_cal_test_p21b))
    ece_p17 = float(compute_ece_mce(y_test, probs_cal_test_p17)[0])
    ece_p21b = float(compute_ece_mce(y_test, probs_cal_test_p21b)[0])
    prauc_p17 = float(average_precision_score(y_test, probs_cal_test_p17))
    prauc_p21b = float(average_precision_score(y_test, probs_cal_test_p21b))
    rocauc_p17 = float(roc_auc_score(y_test, probs_cal_test_p17))
    rocauc_p21b = float(roc_auc_score(y_test, probs_cal_test_p21b))

    print(f"  Test PR-AUC:  Phase 17 = {prauc_p17:.4f} | Phase 21B = {prauc_p21b:.4f} (Lift: +{prauc_p21b - prauc_p17:.4f})")
    print(f"  Test ROC-AUC: Phase 17 = {rocauc_p17:.4f} | Phase 21B = {rocauc_p21b:.4f} (Lift: +{rocauc_p21b - rocauc_p17:.4f})")
    print(f"  Test Brier:   Phase 17 = {brier_p17:.5f} | Phase 21B = {brier_p21b:.5f} (Superior: {brier_p21b < brier_p17})")
    print(f"  Test ECE:     Phase 17 = {ece_p17:.4f} | Phase 21B = {ece_p21b:.4f} (Superior: {ece_p21b < ece_p17})")

    # Evaluate Phase 17 baseline optimal threshold on its own validation set
    X_cat_val_p17 = p17_encoder.transform(df_val[CATEGORICAL_FEATURES].fillna("MISSING").astype(str))
    X_num_val_p17 = df_val[NUMERIC_FEATURES].values.astype(np.float64)
    scores_val_p17 = p17_model.decision_function(np.hstack([X_num_val_p17, X_cat_val_p17]))
    probs_cal_val_p17 = p18_calibrator.predict_proba(scores_val_p17.reshape(-1, 1))[:, 1]
    best_tau_p17_val_cal, best_f1_p17_val_cal, _ = run_threshold_sweep(y_val, probs_cal_val_p17, threshold_grid)
    print(f"  Phase 17 Validation Calibrated Max F1 Threshold: tau = {best_tau_p17_val_cal:.4f}")

    # Side-by-side comparison on test across key policy presets
    test_comparisons = {}

    # Policy 1: Max F1 Comparison (using respective validation/OOF optimal thresholds)
    test_comparisons["max_f1_optimal"] = {
        "policy_description": "Max F1 Optimal Operating Point (Tuned on validation/OOF)",
        "phase17": {
            "threshold": best_tau_p17_val_cal,
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p17, best_tau_p17_val_cal),
        },
        "phase21b": {
            "threshold": best_tau_cal,
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p21b, best_tau_cal),
        },
    }

    # Policy 2: Historical Thresholds Comparison (Phase 17 uncal tau=0.680 vs Phase 21B cal tau=0.165 vs uncal tau=0.165)
    test_comparisons["historical_operating_points"] = {
        "policy_description": "Historical Baseline Operational Points",
        "phase17_tau_680_uncal": {
            "threshold": 0.680,
            "metrics": evaluate_threshold_point(y_test, probs_uncal_test_p17, 0.680),
        },
        "phase21b_tau_165_cal": {
            "threshold": 0.165,
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p21b, 0.165),
        },
        "phase21b_tau_165_uncal": {
            "threshold": 0.165,
            "metrics": evaluate_threshold_point(y_test, probs_uncal_test_p21b, 0.165),
        },
    }

    # Policy 3: Equal Inspection Workload Benchmarks (10% and 12.5% of test inventory)
    # Find Phase 17 threshold that yields ~10% test workload and Phase 21B threshold that yields ~10% test workload
    # NOTE: To prevent test leakage, we use thresholds determined from validation/OOF!
    test_comparisons["fixed_workload_10pct"] = {
        "policy_description": "Fixed 10% Workload Budget (Thresholds frozen from validation/OOF)",
        "phase17": {
            "threshold": tau_wl_10,  # derived from training OOF
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p17, tau_wl_10),
        },
        "phase21b": {
            "threshold": tau_wl_10,  # derived from training OOF
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p21b, tau_wl_10),
        },
    }

    test_comparisons["fixed_workload_12_5pct"] = {
        "policy_description": "Fixed 12.5% Workload Budget (Thresholds frozen from validation/OOF)",
        "phase17": {
            "threshold": tau_wl_12_5,
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p17, tau_wl_12_5),
        },
        "phase21b": {
            "threshold": tau_wl_12_5,
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p21b, tau_wl_12_5),
        },
    }

    # Policy 4: Safety-Critical Target (70% Recall)
    test_comparisons["safety_critical_70pct_recall"] = {
        "policy_description": "Safety-Critical Target (70% Recall threshold frozen from OOF)",
        "phase17": {
            "threshold": tau_rec_70,
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p17, tau_rec_70),
        },
        "phase21b": {
            "threshold": tau_rec_70,
            "metrics": evaluate_threshold_point(y_test, probs_cal_test_p21b, tau_rec_70),
        },
    }

    # Print Comparison Table
    print("\n[SIDE-BY-SIDE TEST COMPARISON: PHASE 17 VS PHASE 21B]")
    print(f"{'Operational Policy':<32} | {'Model':<12} | {'Threshold':<10} | {'F1':<8} | {'Prec':<8} | {'Recall':<8} | {'Workload':<10} | {'True Pos':<8} | {'False Pos':<8}")
    print("-" * 118)

    for pol_key, comp in test_comparisons.items():
        pol_name = comp["policy_description"][:30]
        for m_key in comp.keys():
            if m_key == "policy_description":
                continue
            item = comp[m_key]
            m = item["metrics"]
            m_label = "P21B" if "phase21b" in m_key else "P17"
            print(f"{pol_name:<32} | {m_label:<12} | {item['threshold']:<10.4f} | {m['f1']:<8.4f} | {m['precision']*100:<7.1f}% | {m['recall']*100:<7.1f}% | {m['workload_pct']:<7.1f}% | {m['tp']:<8,d} | {m['fp']:<8,d}")

    # -------------------------------------------------------------------------
    # STEP 4: WORKLOAD SAVINGS & EFFICIENCY QUANTIFICATION
    # -------------------------------------------------------------------------
    m_p17_base = test_comparisons["historical_operating_points"]["phase17_tau_680_uncal"]["metrics"]
    m_p21b_opt = test_comparisons["max_f1_optimal"]["phase21b"]["metrics"]
    m_p21b_165 = test_comparisons["historical_operating_points"]["phase21b_tau_165_cal"]["metrics"]

    workload_quantification = {
        "test_total_bridges": n_test,
        "test_total_deteriorated": int(np.sum(y_test)),
        "baseline_p17_at_tau_680": m_p17_base,
        "phase21b_at_optimal_cal": m_p21b_opt,
        "phase21b_at_tau_165_cal": m_p21b_165,
        "improvements_at_optimal_f1": {
            "additional_true_detections": m_p21b_opt["tp"] - m_p17_base["tp"],
            "recall_absolute_gain_pct": round(m_p21b_opt["recall"]*100 - m_p17_base["recall"]*100, 2),
            "f1_gain": round(m_p21b_opt["f1"] - m_p17_base["f1"], 4),
            "false_negative_reduction": m_p17_base["fn"] - m_p21b_opt["fn"],
            "workload_delta_bridges": m_p21b_opt["bridges_inspected"] - m_p17_base["bridges_inspected"],
            "precision_delta_pct": round(m_p21b_opt["precision"]*100 - m_p17_base["precision"]*100, 2),
        },
        "improvements_at_tau_165_cal": {
            "additional_true_detections": m_p21b_165["tp"] - m_p17_base["tp"],
            "recall_absolute_gain_pct": round(m_p21b_165["recall"]*100 - m_p17_base["recall"]*100, 2),
            "f1_gain": round(m_p21b_165["f1"] - m_p17_base["f1"], 4),
            "false_negative_reduction": m_p17_base["fn"] - m_p21b_165["fn"],
            "workload_delta_bridges": m_p21b_165["bridges_inspected"] - m_p17_base["bridges_inspected"],
            "precision_delta_pct": round(m_p21b_165["precision"]*100 - m_p17_base["precision"]*100, 2),
        },
    }

    # -------------------------------------------------------------------------
    # STEP 5: EMIT MACHINE-READABLE RESULTS AND MANIFEST
    # -------------------------------------------------------------------------
    print("\n--- STEP 5: SERIALIZING PHASE 22 ARTIFACTS ---")
    manifest_data = {
        "phase": "Phase 22A & 22B: Out-of-Fold Calibrated Predictions and Threshold Analysis",
        "generated_at": datetime.now().isoformat(),
        "total_runtime_seconds": round(time.time() - start_time, 2),
        "pre_run_checksums": pre_checksums,
        "split_prevalence": {
            "train_n": n_train,
            "train_prev": float(y_train.mean()),
            "val_n": n_val,
            "val_prev": float(y_val.mean()),
            "test_n": n_test,
            "test_prev": float(y_test.mean()),
        },
        "threshold_origin_analysis": trace_origin,
        "policy_presets_training_oof": policy_presets_oof,
        "calibrator_fold_parameters": calibrator_fold_params,
        "test_audit_comparison": test_comparisons,
        "workload_quantification": workload_quantification,
    }

    manifest_out = OUTPUT_DIR / "phase22_threshold_manifest.json"
    with open(manifest_out, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2)

    # Detailed threshold sweep curve data
    sweep_out = OUTPUT_DIR / "phase22_calibrated_oof_analysis.json"
    with open(sweep_out, "w", encoding="utf-8") as f:
        json.dump({
            "threshold_sweep_calibrated_p21b": sweep_cal[::2],  # sample every other point for compact size
            "threshold_sweep_uncalibrated_p21b": sweep_uncal[::2],
        }, f, indent=2)

    # Workload trade-off tables
    workload_out = OUTPUT_DIR / "phase22_workload_tradeoffs.json"
    workload_summary = []
    for wl in [2.0, 5.0, 7.5, 10.0, 12.5, 15.0, 20.0, 25.0, 30.0]:
        t_val = find_nearest_workload(wl)
        workload_summary.append({
            "target_workload_pct": wl,
            "training_oof_metrics": evaluate_threshold_point(y_train, oof_probs_cal_p21b, t_val),
            "test_audit_metrics": evaluate_threshold_point(y_test, probs_cal_test_p21b, t_val),
        })
    with open(workload_out, "w", encoding="utf-8") as f:
        json.dump(workload_summary, f, indent=2)

    print(f"  Saved manifest:  {manifest_out.name} ({manifest_out.stat().st_size:,} bytes)")
    print(f"  Saved analysis:  {sweep_out.name} ({sweep_out.stat().st_size:,} bytes)")
    print(f"  Saved workloads: {workload_out.name} ({workload_out.stat().st_size:,} bytes)")

    # -------------------------------------------------------------------------
    # STEP 6: POST-RUN CHECKSUMS (VERIFY PRESERVATION OF PHASE 17 & SCORE SERVICE)
    # -------------------------------------------------------------------------
    print("\n--- STEP 6: VERIFY ZERO MUTATION OF PRODUCTION CODE & PHASE 17 ARTIFACTS ---")
    post_checksums = {
        "score_bridge_risk.py": sha256_file(score_bridge_risk_path),
        "phase17_model": sha256_file(p17_model_path),
        "phase17_encoder": sha256_file(p17_encoder_path),
        "phase17_metadata": sha256_file(p17_meta_path),
        "phase17_manifest": sha256_file(p17_manifest_path),
        "phase18_calibrator": sha256_file(p18_cal_path),
    }

    for k in post_checksums:
        assert post_checksums[k] == pre_checksums[k], f"BYTE-FOR-BYTE VIOLATION: {k} changed! {pre_checksums[k]} != {post_checksums[k]}"
        print(f"  [CONFIRMED BYTE-FOR-BYTE] {k}: {post_checksums[k][:16]}... UNCHANGED")

    print(f"\nPhase 22A & 22B completed successfully in {time.time() - start_time:.2f}s.")


if __name__ == "__main__":
    main()
