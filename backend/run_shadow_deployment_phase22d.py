"""
Phase 22D: Shadow Deployment Execution & Acceptance Gates Validation
Risk-Aware Bridge Maintenance Intelligence Platform

CRITICAL SAFEGUARDS:
1. Validation and shadow execution only, NOT production cutover.
2. Phase 17 remains the active production champion.
3. Byte-for-byte immutability of backend/score_bridge_risk.py and backend/results/phase17/*
   verified before and after execution.
4. Reports actual measured telemetry results only. Zero fabricated traffic or approvals.
5. Emits backend/results/phase22/phase22d_shadow_deployment_summary.json.
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.score_bridge_risk import (
    ALL_REQUIRED_FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)
from backend.shadow_scoring_service import (
    ShadowDeploymentConfig,
    ShadowScoringService,
)
from backend.validate_shadow_mode_phase22c import sha256_file

BASE_DIR = Path(__file__).resolve().parent
P17_DIR = BASE_DIR / "results" / "phase17"
P18_CAL_DIR = BASE_DIR / "results" / "phase18" / "calibration"
P21B_DIR = BASE_DIR / "results" / "phase21b"
P22_DIR = BASE_DIR / "results" / "phase22"
DATASET_PATH = BASE_DIR / "data" / "processed" / "bridge_deck_condition_2023_2025.csv"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"


def run_shadow_deployment_audit():
    print("=" * 80)
    print("PHASE 22D: CONTROLLED SHADOW-FIRST DEPLOYMENT AUDIT & ACCEPTANCE GATES")
    print("=" * 80)
    start_time = time.time()

    # -------------------------------------------------------------------------
    # STEP 1: PRE-EXECUTION CHECKSUM VERIFICATION
    # -------------------------------------------------------------------------
    print("\n[STEP 1: PRE-EXECUTION CHECKSUM AUDIT]")
    trusted_manifest_hashes = {
        "score_bridge_risk.py": "b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61",
        "hist_gradient_boosting_classifier.joblib": "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b",
        "cat_encoder.joblib": "14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772",
        "inference_metadata.json": "b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24",
        "serialization_manifest.json": "fedf43153bb898aafb2b1890873b2b65c9df7e1ef2a16292b2af75ecfc4d253e",
        "phase18_calibrator.joblib": "7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3",
        "phase21b_tuned_model.joblib": "aa806c8185db465fd02536d2d4310638c499d41560ac759e0ea15d4a60f98443",
        "phase21b_encoder.joblib": "14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772",
        "phase21b_calibrator.joblib": "cd9d2f3833112e9fd90b5bd355646a1e68f50ac5218b038a95f0d31766c5978f",
        "phase21b_experiment_manifest.json": "2270546e2d471f17da3f2838c7a9ac71e13123452e1be631c1e02bdaf106da9c",
        "phase22_threshold_manifest.json": "79c53545d966740a6bed59eb25c7624ec3868ce6a6eeb951ac372d98d696c8dc",
        "phase22_workload_tradeoffs.json": "82a8a664e56e6dede42c01e226716d023d92eb014a2836e3c5a1250b669905ea",
    }

    file_paths = {
        "score_bridge_risk.py": BASE_DIR / "score_bridge_risk.py",
        "hist_gradient_boosting_classifier.joblib": P17_DIR / "hist_gradient_boosting_classifier.joblib",
        "cat_encoder.joblib": P17_DIR / "cat_encoder.joblib",
        "inference_metadata.json": P17_DIR / "inference_metadata.json",
        "serialization_manifest.json": P17_DIR / "serialization_manifest.json",
        "phase18_calibrator.joblib": P18_CAL_DIR / "phase18_calibrator.joblib",
        "phase21b_tuned_model.joblib": P21B_DIR / "phase21b_tuned_model.joblib",
        "phase21b_encoder.joblib": P21B_DIR / "phase21b_encoder.joblib",
        "phase21b_calibrator.joblib": P21B_DIR / "phase21b_calibrator.joblib",
        "phase21b_experiment_manifest.json": P21B_DIR / "phase21b_experiment_manifest.json",
        "phase22_threshold_manifest.json": P22_DIR / "phase22_threshold_manifest.json",
        "phase22_workload_tradeoffs.json": P22_DIR / "phase22_workload_tradeoffs.json",
    }

    for fname, expected_hash in trusted_manifest_hashes.items():
        actual_hash = sha256_file(file_paths[fname])
        assert actual_hash == expected_hash, f"PRE-RUN CHECKSUM MISMATCH on {fname}!"
        print(f"  [VERIFIED] {fname:<42}: {actual_hash[:16]}...")

    # -------------------------------------------------------------------------
    # STEP 2: CONFIGURE AND INITIALIZE SHADOW SERVICE
    # -------------------------------------------------------------------------
    print("\n[STEP 2: INITIALIZING SHADOW-FIRST SERVICE]")
    telemetry_file = P22_DIR / "phase22d_shadow_telemetry.jsonl"
    if telemetry_file.exists():
        telemetry_file.unlink()  # Start fresh for Phase 22D execution

    shadow_cfg = ShadowDeploymentConfig(
        enabled=True,
        cutover_enabled=False,  # HARD SAFETY GATE: Cutover strictly disabled
        prod_threshold=0.1940,
        shadow_threshold=0.1680,
        telemetry_path=telemetry_file,
        observation_window_days=30,
        min_observation_records=5000,
    )
    service = ShadowScoringService(config=shadow_cfg)
    print(f"  Shadow Mode Enabled: {service.config.enabled}")
    print(f"  Production Cutover Enabled: {service.config.cutover_enabled} (STRICTLY DISABLED)")
    print(f"  Active Production Champion: {service.config.production_champion}")
    print(f"  Shadow Candidate: {service.config.shadow_candidate}")
    print(f"  Telemetry Log Destination: {service.config.telemetry_path}")

    # -------------------------------------------------------------------------
    # STEP 3: RUN SHADOW SCORING ON AUTHENTIC NBI AUDIT BATCH (N=5,000)
    # -------------------------------------------------------------------------
    print("\n[STEP 3: EXECUTING SHADOW EVALUATION ON AUTHENTIC NBI STREAM (N=5,000)]")
    dtype_map = {col: str for col in CATEGORICAL_FEATURES}
    dtype_map["bridge_id"] = str
    dtype_map["state_code"] = str
    df = pd.read_csv(DATASET_PATH, dtype=dtype_map, low_memory=False)

    # Ingest 5,000 authentic records from test split for realistic shadow observation
    test_df = df[df["split"] == "test"].head(5000)
    records_to_score = test_df.to_dict(orient="records")
    eval_count = len(records_to_score)
    assert eval_count == 5000, f"Expected 5,000 records, got {eval_count}"

    t_batch_start = time.perf_counter()
    # Batch scoring with shadow path
    prod_results = service.score_batch_with_shadow(records_to_score)
    total_eval_time = time.perf_counter() - t_batch_start

    assert len(prod_results) == eval_count
    # Verify production results format
    assert "calibrated_deterioration_probability" in prod_results[0]
    assert prod_results[0]["model_metadata"]["service_phase"] == "Phase 18C"
    print(f"  Scored {eval_count:,} records in {total_eval_time:.2f}s ({eval_count/total_eval_time:,.0f} records/sec).")

    # -------------------------------------------------------------------------
    # STEP 4: ANALYZE TELEMETRY AND EVALUATE ACCEPTANCE GATES
    # -------------------------------------------------------------------------
    print("\n[STEP 4: EVALUATING SHADOW TELEMETRY & ACCEPTANCE GATES]")
    summary = service.get_telemetry_summary()

    print(f"  Total Telemetry Entries Logged: {summary['total_records_evaluated']:,}")
    print(f"  Successful Shadow Evaluations:  {summary['successful_shadow_evaluations']:,}")
    print(f"  Failed Shadow Evaluations:      {summary['failed_shadow_evaluations']}")
    print(f"  Shadow Failure Rate:            {summary['shadow_failure_rate']*100:.3f}%")
    print(f"  Phase 17 Flags (Workload):      {summary['workload_statistics']['prod_flagged_count']:,} ({summary['workload_statistics']['prod_flagged_pct']}%)")
    print(f"  Phase 21B Flags (Workload):     {summary['workload_statistics']['shadow_flagged_count']:,} ({summary['workload_statistics']['shadow_flagged_pct']}%)")
    print(f"  Decision Agreement Rate:        {summary['workload_statistics']['decision_agreement_rate_pct']}%")
    print(f"  Median Production Latency:      {summary['latency_summary_ms']['prod_median']:.2f} ms")
    print(f"  Median Shadow Latency:          {summary['latency_summary_ms']['shadow_median']:.2f} ms (p95: {summary['latency_summary_ms']['shadow_p95']:.2f} ms)")
    print(f"  Records with Missing Numerics:  {summary['feature_anomalies_detected']['records_with_missing_numeric']}")
    print(f"  Records with Unseen Categories: {summary['feature_anomalies_detected']['records_with_unseen_categories']}")
    print(f"  Observation Progress:           {summary['observation_progress']['progress_pct']}% (Target: {summary['observation_progress']['min_observation_records']:,} records)")

    print("\n  [ACCEPTANCE GATES STATUS]:")
    for gate_name, gate_data in summary["acceptance_gates_evaluation"].items():
        res_str = "MEETS CRITERIA" if gate_data["meets_criteria"] else "ACTION REQUIRED"
        status_val = gate_data.get("status", gate_data.get("cutover_status", "UNKNOWN"))
        print(f"    - {gate_name:<24}: {status_val} [{res_str}]")

    print(f"\n  OVERALL GATE READINESS: {summary['overall_gate_readiness']}")
    print(f"  PRODUCTION CUTOVER:     DISABLED (Phase 17 remains active champion)")

    # -------------------------------------------------------------------------
    # STEP 5: POST-EXECUTION IMMUTABILITY AUDIT
    # -------------------------------------------------------------------------
    print("\n[STEP 5: POST-EXECUTION IMMUTABILITY AUDIT]")
    for fname, expected_hash in trusted_manifest_hashes.items():
        actual_hash = sha256_file(file_paths[fname])
        assert actual_hash == expected_hash, f"POST-RUN CHECKSUM MISMATCH on {fname}!"
        print(f"  [UNTOUCHED] {fname}")

    # -------------------------------------------------------------------------
    # STEP 6: SERIALIZE MACHINE-READABLE VALIDATION SUMMARY
    # -------------------------------------------------------------------------
    print("\n[STEP 6: SERIALIZING PHASE 22D VALIDATION SUMMARY]")
    validation_summary = {
        "phase": "Phase 22D: Controlled Shadow-First Deployment",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_runtime_seconds": round(time.time() - start_time, 2),
        "pre_and_post_checksums_verified": True,
        "artifact_checksums": trusted_manifest_hashes,
        "deployment_architecture": {
            "mode": "SHADOW_FIRST_EXECUTION",
            "production_champion": "Phase 17 (HistGradientBoostingClassifier + Phase 18B Platt Calibrator)",
            "shadow_candidate": "Phase 21B (C10 Tuned HistGradientBoosting + Cross-Fitted Platt Calibrator)",
            "routing_rule": "100% of operational scoring decisions served by Phase 17",
            "failure_isolation": "Guaranteed. Shadow exceptions are swallowed and logged without production impact",
            "cutover_switch": "DISABLED_PENDING_EXPLICIT_APPROVAL",
        },
        "telemetry_metrics_actual": {
            "records_evaluated": summary["total_records_evaluated"],
            "successful_evaluations": summary["successful_shadow_evaluations"],
            "failed_evaluations": summary["failed_shadow_evaluations"],
            "shadow_failure_rate": summary["shadow_failure_rate"],
            "prod_inspections_flagged": summary["workload_statistics"]["prod_flagged_count"],
            "prod_workload_pct": summary["workload_statistics"]["prod_flagged_pct"],
            "shadow_inspections_flagged": summary["workload_statistics"]["shadow_flagged_count"],
            "shadow_workload_pct": summary["workload_statistics"]["shadow_flagged_pct"],
            "decision_agreement_rate_pct": summary["workload_statistics"]["decision_agreement_rate_pct"],
            "net_workload_difference": summary["workload_statistics"]["net_workload_difference"],
            "latency_ms": summary["latency_summary_ms"],
            "records_with_missing_numeric": summary["feature_anomalies_detected"]["records_with_missing_numeric"],
            "records_with_unseen_categories": summary["feature_anomalies_detected"]["records_with_unseen_categories"],
        },
        "observation_window": summary["observation_progress"],
        "acceptance_gates": summary["acceptance_gates_evaluation"],
        "governance_verdict": {
            "deployment_status": "SHADOW_MODE_DEPLOYED_AND_ACTIVE",
            "production_champion": "Phase 17",
            "cutover_authorized": False,
            "next_step": "Awaiting formal stakeholder sign-off on observation metrics before Phase 22E production promotion",
        },
    }

    out_file = P22_DIR / "phase22d_shadow_deployment_summary.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(validation_summary, f, indent=2)
    print(f"  Machine-readable summary written to: {out_file}")

    print("\n" + "=" * 80)
    print("PHASE 22D AUDIT COMPLETE: FINISHED IN SHADOW MODE (Zero cutover executed).")
    print("=" * 80)


if __name__ == "__main__":
    run_shadow_deployment_audit()
