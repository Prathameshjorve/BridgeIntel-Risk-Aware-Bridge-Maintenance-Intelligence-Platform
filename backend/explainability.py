"""
Explainability Engine for Bridge Deterioration Risk Scoring
Risk-Aware Bridge Maintenance Intelligence Platform

Computes:
1. Global feature importances (from Phase 17 Permutation Importance).
2. Local feature attributions (marginal perturbation delta against empirical median/mode baselines).
3. Risk factor contribution categorizations (Structural, Exposure/Traffic, Age/Inspection, Geography/Governance).
"""

import os
import json
from typing import Dict, Any, List, Optional
import numpy as np

# Empirical reference baseline values computed from historical FHWA training cohort medians and modes
FEATURE_BASELINES: Dict[str, Any] = {
    "prior_deck_condition": 6.0,
    "structure_len_mt": 41.5,
    "max_span_len_mt": 11.0,
    "deck_width_mt": 9.3,
    "traffic_lanes_on": 2.0,
    "adt": 710.5,
    "percent_adt_truck": 5.0,
    "detour_kilos": 10.0,
    "year_built": 1976.0,
    "structure_age_at_inspection": 46.0,
    "prior_inspect_month": 6.0,
    "prior_inspect_year": 2022.0,
    "inspect_freq_months": 24.0,
    "prior_superstructure_condition": "7",
    "prior_substructure_condition": "7",
    "prior_culvert_condition": "N",
    "structure_kind_043a": "1",
    "structure_type_043b": "02",
    "deck_structure_type_107": "1",
    "surface_type_108a": "0",
    "membrane_type_108b": "0",
    "deck_protection_108c": "0",
    "functional_class": "09",
    "maintenance_responsibility": "02",
    "owner": "02",
    "state_code": "01",
}

FEATURE_METADATA: Dict[str, Dict[str, str]] = {
    "prior_deck_condition": {"label": "Prior Deck Condition", "category": "Structural", "unit": "0-9 rating"},
    "prior_superstructure_condition": {"label": "Superstructure Rating", "category": "Structural", "unit": "0-9 rating"},
    "prior_substructure_condition": {"label": "Substructure Rating", "category": "Structural", "unit": "0-9 rating"},
    "prior_culvert_condition": {"label": "Culvert Rating", "category": "Structural", "unit": "code"},
    "structure_kind_043a": {"label": "Structure Material Kind", "category": "Structural", "unit": "FHWA code"},
    "structure_type_043b": {"label": "Structure Design Type", "category": "Structural", "unit": "FHWA code"},
    "deck_structure_type_107": {"label": "Deck Structure Type", "category": "Structural", "unit": "FHWA code"},
    "surface_type_108a": {"label": "Deck Wearing Surface", "category": "Structural", "unit": "FHWA code"},
    "membrane_type_108b": {"label": "Deck Membrane Type", "category": "Structural", "unit": "FHWA code"},
    "deck_protection_108c": {"label": "Deck Protection System", "category": "Structural", "unit": "FHWA code"},
    "structure_len_mt": {"label": "Structure Length", "category": "Structural", "unit": "meters"},
    "max_span_len_mt": {"label": "Max Span Length", "category": "Structural", "unit": "meters"},
    "deck_width_mt": {"label": "Deck Out-to-Out Width", "category": "Structural", "unit": "meters"},
    "adt": {"label": "Average Daily Traffic (ADT)", "category": "Traffic", "unit": "vehicles/day"},
    "percent_adt_truck": {"label": "Truck Traffic Share", "category": "Traffic", "unit": "%"},
    "traffic_lanes_on": {"label": "Traffic Lanes On Structure", "category": "Traffic", "unit": "lanes"},
    "detour_kilos": {"label": "Detour Length", "category": "Network", "unit": "km"},
    "year_built": {"label": "Construction Year", "category": "Aging", "unit": "year"},
    "structure_age_at_inspection": {"label": "Bridge Age at Inspection", "category": "Aging", "unit": "years"},
    "prior_inspect_year": {"label": "Prior Inspection Year", "category": "Aging", "unit": "year"},
    "prior_inspect_month": {"label": "Prior Inspection Month", "category": "Aging", "unit": "month"},
    "inspect_freq_months": {"label": "Inspection Frequency", "category": "Aging", "unit": "months"},
    "state_code": {"label": "State Jurisdiction", "category": "Governance", "unit": "FIPS code"},
    "functional_class": {"label": "Highway Functional Class", "category": "Governance", "unit": "FHWA code"},
    "maintenance_responsibility": {"label": "Maintenance Custodian", "category": "Governance", "unit": "FHWA code"},
    "owner": {"label": "Bridge Owner", "category": "Governance", "unit": "FHWA code"},
}


class BridgeExplainabilityService:
    """
    Computes local feature attributions and global model explanations
    for Phase 17 HistGradientBoosting deterioration predictions.
    """

    def __init__(self, scorer=None, project_root: Optional[str] = None):
        self.project_root = project_root or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self._scorer = scorer
        self._global_importances = None
        self._load_global_importances()

    def _load_global_importances(self):
        imp_path = os.path.join(self.project_root, "backend", "results", "phase17", "feature_importances.json")
        if os.path.exists(imp_path):
            try:
                with open(imp_path, "r", encoding="utf-8") as f:
                    self._global_importances = json.load(f)
            except Exception:
                self._global_importances = []
        else:
            self._global_importances = []

    def get_global_importances(self) -> List[Dict[str, Any]]:
        """Returns sorted list of features with importance means and categories."""
        res = []
        for item in (self._global_importances or []):
            feat = item.get("feature")
            meta = FEATURE_METADATA.get(feat, {"label": feat, "category": "General", "unit": ""})
            res.append({
                "feature": feat,
                "label": meta["label"],
                "category": meta["category"],
                "unit": meta["unit"],
                "importance_mean": float(item.get("importance_mean", 0.0)),
                "importance_std": float(item.get("importance_std", 0.0)),
            })
        return res

    def explain_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Computes local feature attributions for a single bridge scoring record.
        Uses counterfactual marginal perturbation:
        Delta_j = Prob(x) - Prob(x with feature j replaced by empirical baseline)
        """
        from backend.score_bridge_risk import (
            get_default_scorer,
            ALL_REQUIRED_FEATURES,
        )

        scorer = self._scorer or get_default_scorer(verify_checksums=False)
        clf = scorer.classifier
        cal = scorer.calibrator

        # 1. Base prediction for the record
        target_X = scorer._prepare_feature_matrix([record])
        target_raw = float(clf.decision_function(target_X)[0])
        target_prob = float(cal.predict_proba([[target_raw]])[0, 1])

        # 2. Reference baseline prediction
        ref_X = scorer._prepare_feature_matrix([FEATURE_BASELINES])
        ref_raw = float(clf.decision_function(ref_X)[0])
        ref_prob = float(cal.predict_proba([[ref_raw]])[0, 1])

        # 3. Marginal perturbations for all 26 features in a single batch
        perturb_records = []
        for feat in ALL_REQUIRED_FEATURES:
            rec_perturbed = dict(record)
            rec_perturbed[feat] = FEATURE_BASELINES.get(feat)
            perturb_records.append(rec_perturbed)

        X_perturb = scorer._prepare_feature_matrix(perturb_records)
        perturb_raws = clf.decision_function(X_perturb)
        perturb_probs = cal.predict_proba(perturb_raws.reshape(-1, 1))[:, 1]

        attributions = []
        category_sums: Dict[str, float] = {
            "Structural": 0.0,
            "Traffic": 0.0,
            "Aging": 0.0,
            "Network": 0.0,
            "Governance": 0.0,
        }

        total_abs_prob_delta = 0.0

        for i, feat in enumerate(ALL_REQUIRED_FEATURES):
            delta_score = target_raw - float(perturb_raws[i])
            delta_prob = target_prob - float(perturb_probs[i])
            meta = FEATURE_METADATA.get(feat, {"label": feat, "category": "General", "unit": ""})
            cat = meta["category"]

            total_abs_prob_delta += abs(delta_prob)
            if cat in category_sums:
                category_sums[cat] += max(0.0, delta_prob)

            attributions.append({
                "feature": feat,
                "label": meta["label"],
                "category": cat,
                "unit": meta["unit"],
                "actual_value": record.get(feat),
                "baseline_value": FEATURE_BASELINES.get(feat),
                "delta_score": round(delta_score, 4),
                "delta_prob": round(delta_prob, 5),
                "direction": "INCREASES_RISK" if delta_prob > 0.0001 else ("DECREASES_RISK" if delta_prob < -0.0001 else "NEUTRAL"),
            })

        # Rank by absolute impact on deterioration probability
        attributions.sort(key=lambda x: abs(x["delta_prob"]), reverse=True)

        # Normalize relative contribution percentages
        sum_cat = sum(category_sums.values())
        category_breakdown = []
        for cat, val in category_sums.items():
            pct = (val / sum_cat * 100.0) if sum_cat > 0 else 20.0
            category_breakdown.append({
                "category": cat,
                "contribution_pct": round(pct, 1),
                "risk_contribution": round(val, 5),
            })
        category_breakdown.sort(key=lambda x: x["contribution_pct"], reverse=True)

        return {
            "bridge_id": record.get("bridge_id"),
            "target_prediction": {
                "calibrated_deterioration_probability": round(target_prob, 4),
                "raw_decision_score": round(target_raw, 4),
            },
            "baseline_reference": {
                "calibrated_deterioration_probability": round(ref_prob, 4),
                "raw_decision_score": round(ref_raw, 4),
            },
            "category_breakdown": category_breakdown,
            "top_drivers": attributions[:8],
            "all_attributions": attributions,
            "methodology": {
                "algorithm": "Counterfactual Marginal Perturbation",
                "calibrator": "Platt Scaling LogisticRegression",
                "baseline_type": "Empirical National Medians & Modes",
                "interpretation": (
                    "Positive delta_prob indicates that the observed feature value increases "
                    "the 2-year deck deterioration probability above the national reference cohort."
                ),
            },
        }


_GLOBAL_EXPLAINER: Optional[BridgeExplainabilityService] = None


def get_default_explainer() -> BridgeExplainabilityService:
    global _GLOBAL_EXPLAINER
    if _GLOBAL_EXPLAINER is None:
        _GLOBAL_EXPLAINER = BridgeExplainabilityService()
    return _GLOBAL_EXPLAINER
