"""
Phase 20: Comprehensive Evaluation Evidence and Artifact Audit Script
Risk-Aware Bridge Maintenance Intelligence Platform
"""

import os
import json
import hashlib
import joblib

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()

def main():
    print("=" * 80)
    print("PHASE 20: EVALUATION EVIDENCE & ARTIFACT RECOVERY AUDIT")
    print("=" * 80)

    # 1. Dataset Splits & Accounting
    p16_manifest = os.path.join(PROJECT_ROOT, "backend", "data", "processed", "modeling_dataset_manifest.json")
    with open(p16_manifest, "r", encoding="utf-8") as f:
        d16 = json.load(f)
    print("\n1. LONGITUDINAL MODELING DATASET PROVENANCE (Phase 16)")
    print(f"   Pipeline: {d16.get('pipeline_name')}")
    print(f"   Primary CSV: {d16.get('primary_dataset_csv')}")
    print(f"   Baseline: {d16.get('earlier_baseline_release')} -> Target: {d16.get('later_target_release')}")
    print(f"   Total Validated Records: {d16.get('total_records', 0):,}")
    print(f"   Split Strategy: {d16.get('split_strategy')}")
    splits = d16.get("split_distribution", {})
    for s_name, s_count in splits.items():
        print(f"   - Split '{s_name}': {s_count:,} records ({s_count/d16.get('total_records')*100:.2f}%)")

    # 2. Phase 17 Model Evaluation Metrics (Held-out Test Split, N=65,580)
    p17_metrics_path = os.path.join(PROJECT_ROOT, "backend", "results", "phase17", "model_metrics.json")
    with open(p17_metrics_path, "r", encoding="utf-8") as f:
        m17 = json.load(f)
    print("\n2. PHASE 17 BENCHMARK EVALUATION (HELD-OUT TEST SPLIT, N=65,580)")
    print("   Task 1: Future Deck Condition Rating (Ordinal 0-9)")
    for model_k, model_v in m17.get("task1_condition_prediction", {}).items():
        if isinstance(model_v, dict) and "name" in model_v:
            acc = model_v.get("exact_accuracy")
            acc_str = f"{acc*100:.2f}%" if acc is not None else "N/A"
            mae = model_v.get("ordinal_mae")
            mae_str = f"{mae:.4f}" if mae is not None else "N/A"
            rmse = model_v.get("rmse")
            rmse_str = f"{rmse:.4f}" if rmse is not None else "N/A"
            print(f"     * {model_v.get('name')}: Exact Accuracy={acc_str}, Ordinal MAE={mae_str}, RMSE={rmse_str}")

    print("\n   Task 2: Routine Deterioration Event (Binary, Base Rate = 8.91%)")
    for model_k, model_v in m17.get("task2_deterioration_prediction", {}).items():
        if isinstance(model_v, dict) and "name" in model_v:
            pr = model_v.get("test_pr_auc") or model_v.get("pr_auc")
            roc = model_v.get("test_roc_auc") or model_v.get("roc_auc")
            rec = model_v.get("test_recall") or model_v.get("recall")
            prec = model_v.get("test_precision") or model_v.get("precision")
            f1 = model_v.get("test_f1") or model_v.get("f1")
            bacc = model_v.get("test_balanced_accuracy") or model_v.get("balanced_accuracy")
            print(f"     * {model_v.get('name')}:")
            print(f"         PR-AUC:             {pr:.4f}" if pr is not None else "         PR-AUC: N/A")
            print(f"         ROC-AUC:            {roc:.4f}" if roc is not None else "         ROC-AUC: N/A")
            print(f"         Recall (tau=0.68):  {rec*100:.2f}%" if rec is not None else "         Recall: N/A")
            print(f"         Precision:          {prec*100:.2f}%" if prec is not None else "         Precision: N/A")
            print(f"         F1-Score:           {f1:.4f}" if f1 is not None else "         F1-Score: N/A")
            print(f"         Balanced Accuracy:  {bacc*100:.2f}%" if bacc is not None else "         Balanced Accuracy: N/A")

    # 3. Phase 18B Calibration Metrics (Disjoint Validation Assessment Partition, N=32,545)
    cal_comp_path = os.path.join(PROJECT_ROOT, "backend", "results", "phase18", "calibration", "calibration_comparison.json")
    with open(cal_comp_path, "r", encoding="utf-8") as f:
        c18 = json.load(f)
    print("\n3. PHASE 18B CALIBRATION METRICS (DISJOINT VALIDATION ASSESSMENT PARTITION, N=32,545)")
    for cand_k, cand_v in c18.get("candidates", {}).items():
        print(f"     * {cand_v.get('name')}:")
        print(f"         Brier Score:        {cand_v.get('brier_score'):.5f}")
        print(f"         Log Loss:           {cand_v.get('log_loss'):.5f}")
        print(f"         ECE (10 Bins):      {cand_v.get('expected_calibration_error'):.4f}")
        print(f"         MCE (Max Bin Err):  {cand_v.get('maximum_calibration_error'):.4f}")
        print(f"         Calibration Slope:  {cand_v.get('calibration_slope'):.4f}")
        print(f"         CITL (Bias):        {cand_v.get('calibration_in_the_large'):+.4f}")
        print(f"         ROC-AUC Preserved:  {cand_v.get('roc_auc'):.4f}")
        print(f"         PR-AUC Preserved:   {cand_v.get('pr_auc'):.4f}")

    # 4. Artifact Integrity & SHA-256 Checksums
    print("\n4. CRYPTOGRAPHIC PROVENANCE & ARTIFACT AUDIT")
    artifacts = [
        ("HistGradientBoosting Classifier", "backend/results/phase17/hist_gradient_boosting_classifier.joblib"),
        ("Categorical Encoder", "backend/results/phase17/cat_encoder.joblib"),
        ("Inference Metadata", "backend/results/phase17/inference_metadata.json"),
        ("Platt Calibrator", "backend/results/phase18/calibration/phase18_calibrator.joblib"),
        ("Validation Predictions", "backend/results/phase17/val_predictions.json"),
    ]
    for name, rel_path in artifacts:
        full_p = os.path.join(PROJECT_ROOT, rel_path)
        exists = os.path.exists(full_p)
        size = os.path.getsize(full_p) if exists else 0
        h_val = sha256(full_p) if exists else "MISSING"
        print(f"     * {name:<32} {size:>8,} bytes | SHA256: {h_val}")

    print("\nAudit successfully executed.")

if __name__ == "__main__":
    main()
