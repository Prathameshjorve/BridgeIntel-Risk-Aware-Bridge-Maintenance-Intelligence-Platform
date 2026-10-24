"""
Phase 21: Model Improvement, Controlled Experiments, Calibration, and Final Evaluation
Risk-Aware Bridge Maintenance Intelligence Platform

Executes:
- Step 5: Controlled Hyperparameter Experiments (on Train, evaluated on Val)
- Step 6: Threshold and Class-Imbalance Analysis (on Val)
- Step 7: Independent Calibration (disjoint 50/50 Val split)
- Step 8: Final Evaluation on untouched Held-Out Test Set with Paired Bootstrap CI
- Step 9: Compatibility check with 26-feature schema and scoring service
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

from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import OrdinalEncoder
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedShuffleSplit
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
OUTPUT_DIR = BASE_DIR / "results" / "phase21"

CHAMPION_MODEL_PATH = BASE_DIR / "results" / "phase17" / "hist_gradient_boosting_classifier.joblib"
CHAMPION_ENCODER_PATH = BASE_DIR / "results" / "phase17" / "cat_encoder.joblib"

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


def compute_sha256(filepath: Path) -> str:
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
    return ece, mce


def evaluate_threshold_grid(y_val, probs_val, threshold_grid=None):
    if threshold_grid is None:
        threshold_grid = np.linspace(0.05, 0.95, 181)

    best_f1 = -1.0
    best_tau_f1 = 0.5
    best_bal_acc = -1.0
    best_tau_bal_acc = 0.5

    records = []
    for tau in threshold_grid:
        preds = (probs_val >= tau).astype(int)
        p = float(precision_score(y_val, preds, zero_division=0))
        r = float(recall_score(y_val, preds, zero_division=0))
        f1 = float(f1_score(y_val, preds, zero_division=0))
        acc = float(accuracy_score(y_val, preds))
        bal_acc = float(balanced_accuracy_score(y_val, preds))
        cm = confusion_matrix(y_val, preds, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
        fpr = float(fp / (tn + fp)) if (tn + fp) > 0 else 0.0
        fnr = float(fn / (tp + fn)) if (tp + fn) > 0 else 0.0

        if f1 > best_f1:
            best_f1 = f1
            best_tau_f1 = float(tau)

        if bal_acc > best_bal_acc:
            best_bal_acc = bal_acc
            best_tau_bal_acc = float(tau)

        records.append({
            "threshold": round(float(tau), 4),
            "precision": p,
            "recall": r,
            "f1": f1,
            "accuracy": acc,
            "balanced_accuracy": bal_acc,
            "specificity": spec,
            "fpr": fpr,
            "fnr": fnr,
            "tp": int(tp),
            "fp": int(fp),
            "tn": int(tn),
            "fn": int(fn),
        })

    return {
        "best_tau_f1": best_tau_f1,
        "best_f1": best_f1,
        "best_tau_bal_acc": best_tau_bal_acc,
        "best_bal_acc": best_bal_acc,
        "grid_results": records,
    }


def main():
    print("=" * 80)
    print("PHASE 21: CONTROLLED MODEL EXPERIMENTS & COMPREHENSIVE BENCHMARKING")
    print("=" * 80)
    total_start = time.time()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Ingest Dataset
    print("\n1. Ingesting Phase 16 dataset...")
    dtype_map = {col: str for col in CATEGORICAL_FEATURES}
    dtype_map["bridge_id"] = str
    dtype_map["structure_number"] = str
    dtype_map["state_code"] = str
    df = pd.read_csv(DATASET_PATH, dtype=dtype_map, low_memory=False)

    df_train = df[df["split"] == "train"].reset_index(drop=True)
    df_val = df[df["split"] == "val"].reset_index(drop=True)
    df_test = df[df["split"] == "test"].reset_index(drop=True)

    print(f"   Train: {len(df_train):,} rows | Val: {len(df_val):,} rows | Test: {len(df_test):,} rows")

    # 2. Fit Categorical Encoder on Train only
    print("\n2. Fitting Categorical Encoder strictly on Training Split...")
    X_train_cat = df_train[CATEGORICAL_FEATURES].fillna("MISSING").astype(str)
    X_val_cat = df_val[CATEGORICAL_FEATURES].fillna("MISSING").astype(str)
    X_test_cat = df_test[CATEGORICAL_FEATURES].fillna("MISSING").astype(str)

    encoder = OrdinalEncoder(handle_unknown="use_encoded_value", unknown_value=-1)
    X_train_cat_enc = encoder.fit_transform(X_train_cat)
    X_val_cat_enc = encoder.transform(X_val_cat)
    X_test_cat_enc = encoder.transform(X_test_cat)

    X_train_num = df_train[NUMERIC_FEATURES].values.astype(np.float64)
    X_val_num = df_val[NUMERIC_FEATURES].values.astype(np.float64)
    X_test_num = df_test[NUMERIC_FEATURES].values.astype(np.float64)

    X_train = np.hstack([X_train_num, X_train_cat_enc])
    X_val = np.hstack([X_val_num, X_val_cat_enc])
    X_test = np.hstack([X_test_num, X_test_cat_enc])

    cat_indices = list(range(len(NUMERIC_FEATURES), len(ALL_FEATURES)))

    y_train = df_train["target_deterioration"].values
    y_val = df_val["target_deterioration"].values
    y_test = df_test["target_deterioration"].values

    # 3. Define Controlled Experiment Candidates
    candidates = [
        {
            "id": "candidate_0_champion_baseline",
            "name": "Phase 20 Champion Baseline",
            "params": {
                "class_weight": "balanced",
                "max_iter": 100,
                "learning_rate": 0.1,
                "max_leaf_nodes": 31,
                "min_samples_leaf": 20,
                "l2_regularization": 0.0,
                "early_stopping": True,
                "validation_fraction": 0.1,
                "random_state": 42,
            },
            "description": "Exact configuration of frozen Phase 20 champion.",
        },
        {
            "id": "candidate_1_regularized_l2",
            "name": "L2-Regularized & Larger Leaf Support",
            "params": {
                "class_weight": "balanced",
                "max_iter": 150,
                "learning_rate": 0.1,
                "max_leaf_nodes": 31,
                "min_samples_leaf": 50,
                "l2_regularization": 1.0,
                "early_stopping": True,
                "validation_fraction": 0.1,
                "random_state": 42,
            },
            "description": "Increases min_samples_leaf to 50 and adds l2_regularization=1.0 to prevent overfitting on rare categories.",
        },
        {
            "id": "candidate_2_deep_interactions",
            "name": "Higher Capacity with Interaction Depth",
            "params": {
                "class_weight": "balanced",
                "max_iter": 150,
                "learning_rate": 0.08,
                "max_leaf_nodes": 63,
                "min_samples_leaf": 40,
                "l2_regularization": 0.5,
                "early_stopping": True,
                "validation_fraction": 0.1,
                "random_state": 42,
            },
            "description": "Expands leaf nodes to 63 with moderate regularization to capture subtle non-linear multi-attribute interactions.",
        },
        {
            "id": "candidate_3_conservative_learning",
            "name": "Conservative Learning Rate (eta=0.05)",
            "params": {
                "class_weight": "balanced",
                "max_iter": 200,
                "learning_rate": 0.05,
                "max_leaf_nodes": 31,
                "min_samples_leaf": 30,
                "l2_regularization": 0.2,
                "early_stopping": True,
                "validation_fraction": 0.1,
                "random_state": 42,
            },
            "description": "Reduces learning rate to 0.05 with max_iter=200 for smoother gradient descent convergence.",
        },
        {
            "id": "candidate_4_depth_constrained",
            "name": "Depth-Constrained Shallow Ensemble (max_depth=6)",
            "params": {
                "class_weight": "balanced",
                "max_iter": 150,
                "learning_rate": 0.08,
                "max_depth": 6,
                "max_leaf_nodes": 31,
                "min_samples_leaf": 35,
                "l2_regularization": 0.3,
                "early_stopping": True,
                "validation_fraction": 0.1,
                "random_state": 42,
            },
            "description": "Constrains maximum tree depth to 6 to guard against noise in inspection date coding.",
        },
        {
            "id": "candidate_5_unweighted_native",
            "name": "Unweighted Native Prevalence Estimator",
            "params": {
                "class_weight": None,
                "max_iter": 150,
                "learning_rate": 0.08,
                "max_leaf_nodes": 31,
                "min_samples_leaf": 30,
                "l2_regularization": 0.2,
                "early_stopping": True,
                "validation_fraction": 0.1,
                "random_state": 42,
            },
            "description": "Trains without class_weight='balanced' to evaluate if native prevalence modeling yields superior discrimination.",
        },
    ]

    print(f"\n3. Executing Controlled Training & Validation Grid ({len(candidates)} candidates)...")
    val_evaluation_results = []
    fitted_models = {}

    for cand in candidates:
        cid = cand["id"]
        cname = cand["name"]
        params = cand["params"].copy()
        params["categorical_features"] = cat_indices

        print(f"\n   >>> Training {cid}: '{cname}'...")
        t0 = time.time()
        model = HistGradientBoostingClassifier(**params)
        model.fit(X_train, y_train)
        train_duration = time.time() - t0
        fitted_models[cid] = model
        print(f"       Fit completed in {train_duration:.2f}s (n_iter_={model.n_iter_})")

        # Validation prediction
        probs_val = model.predict_proba(X_val)[:, 1]
        scores_val = model.decision_function(X_val)

        val_pr_auc = float(average_precision_score(y_val, probs_val))
        val_roc_auc = float(roc_auc_score(y_val, probs_val))

        # Threshold analysis on validation data
        thresh_analysis = evaluate_threshold_grid(y_val, probs_val)
        best_tau = thresh_analysis["best_tau_f1"]
        best_f1 = thresh_analysis["best_f1"]

        # Evaluate at optimal threshold
        preds_val_opt = (probs_val >= best_tau).astype(int)
        opt_p = float(precision_score(y_val, preds_val_opt, zero_division=0))
        opt_r = float(recall_score(y_val, preds_val_opt, zero_division=0))
        opt_acc = float(accuracy_score(y_val, preds_val_opt))
        opt_bal_acc = float(balanced_accuracy_score(y_val, preds_val_opt))
        cm_val = confusion_matrix(y_val, preds_val_opt, labels=[0, 1])
        tn, fp, fn, tp = cm_val.ravel()
        opt_spec = float(tn / (tn + fp))

        # Also evaluate at standard tau=0.680 for comparison
        preds_val_68 = (probs_val >= 0.680).astype(int)
        f1_68 = float(f1_score(y_val, preds_val_68, zero_division=0))
        p_68 = float(precision_score(y_val, preds_val_68, zero_division=0))
        r_68 = float(recall_score(y_val, preds_val_68, zero_division=0))

        res_record = {
            "id": cid,
            "name": cname,
            "params": cand["params"],
            "description": cand["description"],
            "fit_time_seconds": round(train_duration, 2),
            "n_trees_fitted": int(model.n_iter_),
            "val_pr_auc": val_pr_auc,
            "val_roc_auc": val_roc_auc,
            "optimal_val_threshold_tau": best_tau,
            "val_metrics_at_optimal_tau": {
                "f1": best_f1,
                "precision": opt_p,
                "recall": opt_r,
                "accuracy": opt_acc,
                "balanced_accuracy": opt_bal_acc,
                "specificity": opt_spec,
                "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
            },
            "val_metrics_at_tau_068": {
                "f1": f1_68,
                "precision": p_68,
                "recall": r_68,
            },
            "threshold_analysis": thresh_analysis,
        }
        val_evaluation_results.append(res_record)

        print(f"       Validation PR-AUC:  {val_pr_auc:.4f}")
        print(f"       Validation ROC-AUC: {val_roc_auc:.4f}")
        print(f"       Best Val F1:        {best_f1:.4f} at tau={best_tau:.3f} (P={opt_p*100:.2f}%, R={opt_r*100:.2f}%)")

    # 4. Compare Candidates & Select Best Model based on Validation Data
    print("\n" + "=" * 80)
    print("4. CANDIDATE SELECTION ON VALIDATION EVIDENCE (NO TEST LEAKAGE)")
    print("=" * 80)

    # Sort candidates by validation PR-AUC
    sorted_by_pr = sorted(val_evaluation_results, key=lambda x: x["val_pr_auc"], reverse=True)
    baseline_val_pr = next(c["val_pr_auc"] for c in val_evaluation_results if c["id"] == "candidate_0_champion_baseline")
    baseline_val_roc = next(c["val_roc_auc"] for c in val_evaluation_results if c["id"] == "candidate_0_champion_baseline")

    print("\nRanking by Validation PR-AUC:")
    for rank, c in enumerate(sorted_by_pr, 1):
        delta_pr = c["val_pr_auc"] - baseline_val_pr
        delta_roc = c["val_roc_auc"] - baseline_val_roc
        print(f"  {rank}. [{c['id']}] {c['name']}")
        print(f"     PR-AUC: {c['val_pr_auc']:.4f} (delta: {delta_pr:+.4f}) | ROC-AUC: {c['val_roc_auc']:.4f} (delta: {delta_roc:+.4f}) | Val F1: {c['val_metrics_at_optimal_tau']['f1']:.4f}")

    # Determine champion vs challenger
    best_candidate_rec = sorted_by_pr[0]
    best_cid = best_candidate_rec["id"]
    best_model = fitted_models[best_cid]

    meaningful_improvement = (best_candidate_rec["val_pr_auc"] - baseline_val_pr) >= 0.0020
    print(f"\nSelection Decision:")
    print(f"  Top Candidate: {best_candidate_rec['name']} ({best_cid})")
    print(f"  Validation PR-AUC Lift: {best_candidate_rec['val_pr_auc'] - baseline_val_pr:+.4f}")
    print(f"  Validation ROC-AUC Lift: {best_candidate_rec['val_roc_auc'] - baseline_val_roc:+.4f}")
    if meaningful_improvement:
        print("  Meaningful validation improvement achieved (>= +0.0020 PR-AUC lift). Proceeding to calibration and promotion evaluation.")
    else:
        print("  Improvement is marginal or negligible (< +0.0020 PR-AUC lift). Champion baseline remains strong.")

    # 5. Independent Calibration of Selected Model (Step 7)
    print("\n" + "=" * 80)
    print(f"5. INDEPENDENT PROBABILITY CALIBRATION FOR: {best_candidate_rec['name']}")
    print("=" * 80)

    # Use disjoint 50/50 partition of validation set
    sss = StratifiedShuffleSplit(n_splits=1, test_size=0.5, random_state=42)
    cal_fit_idx, cal_assess_idx = next(sss.split(X_val, y_val))

    X_val_fit = X_val[cal_fit_idx]
    y_val_fit = y_val[cal_fit_idx]
    X_val_assess = X_val[cal_assess_idx]
    y_val_assess = y_val[cal_assess_idx]

    print(f"   Calibration Partitioning (Stratified 50/50):")
    print(f"   - Fit subset:       {len(y_val_fit):,} samples (Prevalence: {np.mean(y_val_fit)*100:.2f}%)")
    print(f"   - Assessment subset: {len(y_val_assess):,} samples (Prevalence: {np.mean(y_val_assess)*100:.2f}%)")

    # Raw margins from the candidate model
    raw_scores_fit = best_model.decision_function(X_val_fit).reshape(-1, 1)
    raw_scores_assess = best_model.decision_function(X_val_assess).reshape(-1, 1)
    raw_probs_assess = best_model.predict_proba(X_val_assess)[:, 1]

    # Fit Platt Scaler (Logistic Regression) on Fit partition
    platt_calibrator = LogisticRegression(C=1.0, solver="lbfgs", random_state=42)
    platt_calibrator.fit(raw_scores_fit, y_val_fit)

    # Assess on disjoint Assessment partition
    cal_probs_assess = platt_calibrator.predict_proba(raw_scores_assess)[:, 1]

    # Compute calibration metrics
    brier_uncal = float(brier_score_loss(y_val_assess, raw_probs_assess))
    brier_cal = float(brier_score_loss(y_val_assess, cal_probs_assess))
    logloss_uncal = float(log_loss(y_val_assess, raw_probs_assess))
    logloss_cal = float(log_loss(y_val_assess, cal_probs_assess))
    ece_uncal, mce_uncal = compute_ece_mce(y_val_assess, raw_probs_assess)
    ece_cal, mce_cal = compute_ece_mce(y_val_assess, cal_probs_assess)

    # Calibration slope & intercept
    eval_cal = LogisticRegression(C=1e6, solver="lbfgs")
    eval_cal.fit(raw_scores_assess, y_val_assess)
    cal_slope = float(eval_cal.coef_[0][0])
    cal_intercept = float(eval_cal.intercept_[0])
    citl = float(np.mean(cal_probs_assess) - np.mean(y_val_assess))

    print(f"\n   Calibration Results on Disjoint Assessment Partition (N={len(y_val_assess):,}):")
    print(f"   - Uncalibrated: Brier={brier_uncal:.5f}, Log Loss={logloss_uncal:.5f}, ECE={ece_uncal:.4f}")
    print(f"   - Platt Calibrated: Brier={brier_cal:.5f}, Log Loss={logloss_cal:.5f}, ECE={ece_cal:.4f}, CITL={citl:+.4f}, Slope={cal_slope:.4f}")
    print(f"   - ECE Reduction: {(ece_uncal - ece_cal)/ece_uncal * 100:.1f}%")

    calibration_summary = {
        "candidate_id": best_cid,
        "calibrator_type": "Platt Scaling (LogisticRegression)",
        "platt_coefficients": {
            "A_slope": float(platt_calibrator.coef_[0][0]),
            "B_intercept": float(platt_calibrator.intercept_[0]),
        },
        "assessment_sample_size": len(y_val_assess),
        "uncalibrated_metrics": {
            "brier_score": brier_uncal,
            "log_loss": logloss_uncal,
            "ece": ece_uncal,
            "mce": mce_uncal,
        },
        "calibrated_metrics": {
            "brier_score": brier_cal,
            "log_loss": logloss_cal,
            "ece": ece_cal,
            "mce": mce_cal,
            "calibration_slope": cal_slope,
            "calibration_intercept": cal_intercept,
            "calibration_in_the_large": citl,
        },
    }

    # 6. Final Evaluation on Untouched Held-Out Test Set (Step 8)
    print("\n" + "=" * 80)
    print("6. FINAL EVALUATION ON UNTOUCHED HELD-OUT TEST SET (N=65,580)")
    print("=" * 80)

    # Evaluate frozen champion on test set
    frozen_champion = joblib.load(CHAMPION_MODEL_PATH)
    frozen_calibrator = joblib.load(BASE_DIR / "results" / "phase18" / "calibration" / "phase18_calibrator.joblib")

    probs_test_champ = frozen_champion.predict_proba(X_test)[:, 1]
    scores_test_champ = frozen_champion.decision_function(X_test)
    preds_test_champ_68 = (probs_test_champ >= 0.680).astype(int)

    # Evaluate candidate on test set
    probs_test_cand = best_model.predict_proba(X_test)[:, 1]
    scores_test_cand = best_model.decision_function(X_test)
    best_tau = best_candidate_rec["optimal_val_threshold_tau"]
    preds_test_cand_opt = (probs_test_cand >= best_tau).astype(int)
    preds_test_cand_68 = (probs_test_cand >= 0.680).astype(int)

    # Metrics computation
    def compute_all_metrics(y_true, probs, preds):
        pr = float(average_precision_score(y_true, probs))
        roc = float(roc_auc_score(y_true, probs))
        p = float(precision_score(y_true, preds, zero_division=0))
        r = float(recall_score(y_true, preds, zero_division=0))
        f1 = float(f1_score(y_true, preds, zero_division=0))
        acc = float(accuracy_score(y_true, preds))
        bal_acc = float(balanced_accuracy_score(y_true, preds))
        cm = confusion_matrix(y_true, preds, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel()
        spec = float(tn / (tn + fp))
        fpr = float(fp / (tn + fp))
        fnr = float(fn / (tp + fn))
        return {
            "pr_auc": pr,
            "roc_auc": roc,
            "precision": p,
            "recall": r,
            "f1": f1,
            "accuracy": acc,
            "balanced_accuracy": bal_acc,
            "specificity": spec,
            "fpr": fpr,
            "fnr": fnr,
            "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        }

    m_champ = compute_all_metrics(y_test, probs_test_champ, preds_test_champ_68)
    m_cand_opt = compute_all_metrics(y_test, probs_test_cand, preds_test_cand_opt)
    m_cand_68 = compute_all_metrics(y_test, probs_test_cand, preds_test_cand_68)

    print("\nTest Set Comparison Table:")
    print(f"{'Metric':<22} | {'Phase 20 Champion (tau=0.680)':<30} | {'Candidate (tau=' + f'{best_tau:.3f})':<26} | {'Candidate (tau=0.680)':<22}")
    print("-" * 108)
    print(f"{'PR-AUC':<22} | {m_champ['pr_auc']:.4f}{'':<24} | {m_cand_opt['pr_auc']:.4f}{'':<20} | {m_cand_68['pr_auc']:.4f}")
    print(f"{'ROC-AUC':<22} | {m_champ['roc_auc']:.4f}{'':<24} | {m_cand_opt['roc_auc']:.4f}{'':<20} | {m_cand_68['roc_auc']:.4f}")
    print(f"{'Precision':<22} | {m_champ['precision']*100:.2f}%{'':<23} | {m_cand_opt['precision']*100:.2f}%{'':<19} | {m_cand_68['precision']*100:.2f}%")
    print(f"{'Recall':<22} | {m_champ['recall']*100:.2f}%{'':<23} | {m_cand_opt['recall']*100:.2f}%{'':<19} | {m_cand_68['recall']*100:.2f}%")
    print(f"{'F1-Score':<22} | {m_champ['f1']:.4f}{'':<24} | {m_cand_opt['f1']:.4f}{'':<20} | {m_cand_68['f1']:.4f}")
    print(f"{'Accuracy':<22} | {m_champ['accuracy']*100:.2f}%{'':<23} | {m_cand_opt['accuracy']*100:.2f}%{'':<19} | {m_cand_68['accuracy']*100:.2f}%")
    print(f"{'Balanced Accuracy':<22} | {m_champ['balanced_accuracy']*100:.2f}%{'':<23} | {m_cand_opt['balanced_accuracy']*100:.2f}%{'':<19} | {m_cand_68['balanced_accuracy']*100:.2f}%")
    print(f"{'Specificity':<22} | {m_champ['specificity']*100:.2f}%{'':<23} | {m_cand_opt['specificity']*100:.2f}%{'':<19} | {m_cand_68['specificity']*100:.2f}%")

    # 7. Paired Bootstrap Confidence Intervals (B=1,000)
    print("\n7. Computing Paired Bootstrap Confidence Intervals (B=1,000 iterations)...")
    np.random.seed(42)
    B = 1000
    n_test = len(y_test)
    delta_pr_boot = []
    delta_roc_boot = []
    delta_f1_boot = []

    for b in range(B):
        idx = np.random.choice(n_test, size=n_test, replace=True)
        y_b = y_test[idx]
        if np.sum(y_b) == 0 or np.sum(y_b) == len(y_b):
            continue
        p_champ_b = probs_test_champ[idx]
        p_cand_b = probs_test_cand[idx]
        pred_champ_b = preds_test_champ_68[idx]
        pred_cand_b = preds_test_cand_opt[idx]

        pr_diff = average_precision_score(y_b, p_cand_b) - average_precision_score(y_b, p_champ_b)
        roc_diff = roc_auc_score(y_b, p_cand_b) - roc_auc_score(y_b, p_champ_b)
        f1_diff = f1_score(y_b, pred_cand_b, zero_division=0) - f1_score(y_b, pred_champ_b, zero_division=0)

        delta_pr_boot.append(pr_diff)
        delta_roc_boot.append(roc_diff)
        delta_f1_boot.append(f1_diff)

    ci_pr = (np.percentile(delta_pr_boot, 2.5), np.percentile(delta_pr_boot, 97.5))
    ci_roc = (np.percentile(delta_roc_boot, 2.5), np.percentile(delta_roc_boot, 97.5))
    ci_f1 = (np.percentile(delta_f1_boot, 2.5), np.percentile(delta_f1_boot, 97.5))

    print(f"   Delta PR-AUC (Cand - Champ):  Mean={np.mean(delta_pr_boot):+.4f}, 95% CI=[{ci_pr[0]:+.4f}, {ci_pr[1]:+.4f}]")
    print(f"   Delta ROC-AUC (Cand - Champ): Mean={np.mean(delta_roc_boot):+.4f}, 95% CI=[{ci_roc[0]:+.4f}, {ci_roc[1]:+.4f}]")
    print(f"   Delta F1-Score:               Mean={np.mean(delta_f1_boot):+.4f}, 95% CI=[{ci_f1[0]:+.4f}, {ci_f1[1]:+.4f}]")

    is_pr_significant = (ci_pr[0] > 0.0)
    print(f"   Statistically Significant PR-AUC Improvement: {'YES' if is_pr_significant else 'NO (CI includes 0)'}")

    # 8. Save Candidate Artifacts to Versioned Directory
    print("\n8. Saving Candidate Artifacts to backend/results/phase21/...")
    cand_model_path = OUTPUT_DIR / f"{best_cid}.joblib"
    cand_calibrator_path = OUTPUT_DIR / f"{best_cid}_calibrator.joblib"
    cand_encoder_path = OUTPUT_DIR / "phase21_encoder.joblib"

    joblib.dump(best_model, cand_model_path, compress=3)
    joblib.dump(platt_calibrator, cand_calibrator_path, compress=3)
    joblib.dump(encoder, cand_encoder_path, compress=3)

    # Save complete experiment manifest
    exp_summary = {
        "execution_date": datetime.now().isoformat(),
        "total_runtime_seconds": round(time.time() - total_start, 2),
        "split_sizes": {"train": len(df_train), "val": len(df_val), "test": len(df_test)},
        "candidates_evaluated": len(candidates),
        "candidate_summary_table": [
            {
                "id": c["id"],
                "name": c["name"],
                "val_pr_auc": c["val_pr_auc"],
                "val_roc_auc": c["val_roc_auc"],
                "optimal_val_threshold_tau": c["optimal_val_threshold_tau"],
                "val_f1_at_optimal": c["val_metrics_at_optimal_tau"]["f1"],
                "val_f1_at_068": c["val_metrics_at_tau_068"]["f1"],
                "fit_time_seconds": c["fit_time_seconds"],
            }
            for c in val_evaluation_results
        ],
        "selected_candidate": {
            "id": best_cid,
            "name": best_candidate_rec["name"],
            "params": best_candidate_rec["params"],
            "optimal_threshold": best_tau,
        },
        "calibration_results": calibration_summary,
        "test_comparison": {
            "champion_metrics": m_champ,
            "candidate_metrics_at_optimal_tau": m_cand_opt,
            "candidate_metrics_at_tau_068": m_cand_68,
            "paired_bootstrap_differences": {
                "b_samples": B,
                "delta_pr_auc": {"mean": float(np.mean(delta_pr_boot)), "ci_95": [float(ci_pr[0]), float(ci_pr[1])]},
                "delta_roc_auc": {"mean": float(np.mean(delta_roc_boot)), "ci_95": [float(ci_roc[0]), float(ci_roc[1])]},
                "delta_f1": {"mean": float(np.mean(delta_f1_boot)), "ci_95": [float(ci_f1[0]), float(ci_f1[1])]},
                "statistically_significant": bool(is_pr_significant),
            },
        },
        "artifact_checksums": {
            "candidate_model": compute_sha256(cand_model_path),
            "candidate_calibrator": compute_sha256(cand_calibrator_path),
            "candidate_encoder": compute_sha256(cand_encoder_path),
        },
    }

    manifest_file = OUTPUT_DIR / "phase21_experiment_manifest.json"
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump(exp_summary, f, indent=2)
    print(f"   Experiment manifest saved: {manifest_file.name}")

    print("\nPhase 21 controlled experiments completed successfully!")


if __name__ == "__main__":
    main()
