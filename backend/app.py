"""
Phase 19: Bridge Deterioration Risk Scoring API Service
Risk-Aware Bridge Maintenance Intelligence Platform

This module exposes a RESTful HTTP API for scoring bridge deck deterioration risk
using the pre-trained Phase 17 HistGradientBoostingClassifier and Phase 18B Platt calibrator.

STRICT SAFETY & SEMANTIC CONTRACTS:
- Predicts 2-year probability of routine NBI deck rating decline (DECK_2025 < DECK_2023).
- NEVER describes outputs as bridge collapse probability or structural safety certification.
- Discloses that external geographical and temporal validation has not been established.
- Model scores are kept strictly separated from consequence scoring, detour costs,
  maintenance costs, priority ranking, and knapsack budget optimization.
- Does NOT expose stack traces or raw sensitive records in error responses.
"""

import os
import sys
import json
import logging
from typing import Dict, Any, List, Optional
from flask import Flask, request, jsonify, Response

# Add project root to sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from backend.score_bridge_risk import (
    BridgeRiskScorer,
    get_default_scorer,
    score_bridges,
    BridgeScoringError,
    SchemaValidationError,
    ArtifactLoadError,
    ALL_REQUIRED_FEATURES,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
    SEMANTICS_DISCLAIMER,
)
from backend.shadow_scoring_service import get_shadow_scoring_service
from backend.shadow_ingestion_adapter import get_shadow_ingestion_adapter
from backend.explainability import get_default_explainer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bridge_scoring_api")

app = Flask(__name__)

# Sample verified records path for testing / demonstration
FIXTURES_PATH = os.path.join(
    PROJECT_ROOT, "backend", "tests", "fixtures", "regression_test_fixture.json"
)


@app.after_request
def add_cors_headers(response: Response) -> Response:
    """Adds standard CORS headers to allow cross-origin requests from frontend."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


@app.route("/api/health", methods=["GET"])
def health_check():
    """Health check endpoint providing service status and model readiness."""
    try:
        scorer = get_default_scorer(verify_checksums=False)
        model_ready = scorer.classifier is not None and scorer.calibrator is not None
        status = "healthy" if model_ready else "degraded"
        status_code = 200 if model_ready else 503
    except Exception as e:
        logger.error("Health check failure loading scorer: %s", str(e))
        return jsonify({
            "status": "unhealthy",
            "service": "Bridge Deterioration Risk Scoring API",
            "model_ready": False,
            "error": "Failed to initialize model scorer"
        }), 503

    shadow_service = get_shadow_scoring_service()
    shadow_active = shadow_service.config.enabled

    return jsonify({
        "status": status,
        "service": "Bridge Deterioration Risk Scoring API",
        "phase": "Phase 22D: Shadow-First Deployment",
        "model_ready": model_ready,
        "classifier_type": "HistGradientBoostingClassifier (Phase 17)",
        "calibrator_type": "Platt Scaling LogisticRegression (Phase 18B)",
        "active_production_champion": "Phase 17",
        "shadow_mode_active": shadow_active,
        "production_cutover_status": "DISABLED_PENDING_EXPLICIT_APPROVAL",
        "features_count": len(ALL_REQUIRED_FEATURES),
        "target_semantics": "2-year routine NBI deck rating reduction (DECK_2025 < DECK_2023)"
    }), status_code


@app.route("/api/model/metadata", methods=["GET"])
def model_metadata():
    """Returns detailed model schema, target definition, and scientific disclaimers."""
    try:
        scorer = get_default_scorer(verify_checksums=False)
        metadata = scorer.metadata or {}
    except Exception as e:
        logger.error("Failed to retrieve model metadata: %s", str(e))
        metadata = {}

    return jsonify({
        "model_type": "HistGradientBoostingClassifier with Platt Calibrator",
        "target_name": "target_deterioration",
        "target_semantics": (
            "1 if later NBI deck-condition rating < earlier rating (routine biennial degradation on 0-9 scale), "
            "0 otherwise."
        ),
        "scientific_disclaimers": {
            "no_collapse_prediction": (
                "This model outputs an empirical probability of a subsequent lower NBI deck condition rating. "
                "It does NOT predict bridge collapse, catastrophic structural failure, or human safety risk."
            ),
            "no_engineering_replacement": (
                "This is an AI-assisted decision-support prototype for research and planning. "
                "It does NOT certify structural safety or replace qualified bridge inspection engineers."
            ),
            "validation_scope": (
                "Probability calibration was validated on an internal held-out 50% partition of historical FHWA NBI "
                "validation predictions. External geographical and temporal validation has not yet been established."
            ),
            "separation_of_concerns": (
                "Deterioration probabilities are kept strictly separate from public consequence, detour costs, "
                "maintenance costs, priority ranking, and knapsack budget optimization."
            )
        },
        "feature_schema": {
            "all_features_ordered": ALL_REQUIRED_FEATURES,
            "total_count": len(ALL_REQUIRED_FEATURES),
            "numeric_features": NUMERIC_FEATURES,
            "categorical_features": CATEGORICAL_FEATURES,
        },
        "service_version": "Phase 19"
    }), 200


@app.route("/api/sample-records", methods=["GET"])
def sample_records():
    """Returns verified non-test FHWA sample bridge records from regression fixtures."""
    if not os.path.exists(FIXTURES_PATH):
        return jsonify({"error": "fixtures_not_found", "message": "Regression fixtures unavailable"}), 404

    try:
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        samples = data.get("fixtures", [])
        return jsonify({
            "count": len(samples),
            "samples": [
                {
                    "bridge_id": s.get("bridge_id"),
                    "input_record": s.get("input_record"),
                    "verified_raw_score": s.get("expected_raw_score"),
                    "verified_calibrated_probability": s.get("expected_calibrated_probability")
                }
                for s in samples
            ]
        }), 200
    except Exception as e:
        logger.error("Error reading fixtures: %s", str(e))
        return jsonify({"error": "server_error", "message": "Failed to read sample fixtures"}), 500


@app.route("/api/score", methods=["POST", "OPTIONS"])
def score_single_bridge():
    """Scores a single bridge record containing the 26 required NBI features."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        payload = request.get_json(silent=True)
    except Exception:
        return jsonify({
            "error": "malformed_request",
            "message": "Request body must be valid JSON"
        }), 400

    if payload is None:
        return jsonify({
            "error": "missing_payload",
            "message": "Request body must be a valid non-empty JSON object"
        }), 400

    # Accept either direct record dict or { "record": { ... } }
    record = payload.get("record", payload) if isinstance(payload, dict) and "record" in payload else payload

    if not isinstance(record, dict):
        return jsonify({
            "error": "invalid_record_format",
            "message": "Bridge record must be a JSON object containing the required 26 features"
        }), 400

    try:
        adapter = get_shadow_ingestion_adapter()
        scorer = get_default_scorer()
        adapter.shadow_service.prod_scorer = scorer
        result = adapter.route_single_score(record, dict(request.headers))
        
        # Include optional inline explainability if requested
        include_explanation = request.args.get("explain", "").lower() in ("true", "1") or payload.get("explain") is True
        if include_explanation:
            try:
                explainer = get_default_explainer()
                result["explanation"] = explainer.explain_record(record)
            except Exception as ex_err:
                logger.warning("Explainability generation failed: %s", str(ex_err))

        return jsonify(result), 200
    except PermissionError as pe:
        logger.warning("Authentication failure on /api/score: %s", str(pe))
        return jsonify({
            "error": "unauthorized",
            "message": str(pe)
        }), 401
    except SchemaValidationError as sve:
        logger.warning("Validation error on /api/score: %s", str(sve))
        return jsonify({
            "error": "validation_error",
            "message": str(sve)
        }), 400
    except ArtifactLoadError as ale:
        logger.error("Artifact load error: %s", str(ale))
        return jsonify({
            "error": "service_unavailable",
            "message": "Model scoring service is temporarily unavailable due to artifact loading failure."
        }), 503
    except Exception as e:
        logger.error("Unexpected error scoring bridge record: %s", str(e))
        return jsonify({
            "error": "internal_scoring_error",
            "message": "An internal error occurred while processing the bridge scoring request."
        }), 500


@app.route("/api/score/batch", methods=["POST", "OPTIONS"])
def score_batch_bridges():
    """Scores a batch of bridge records."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        payload = request.get_json(silent=True)
    except Exception:
        return jsonify({
            "error": "malformed_request",
            "message": "Request body must be valid JSON"
        }), 400

    if payload is None:
        return jsonify({
            "error": "missing_payload",
            "message": "Request body must be a valid JSON object with a 'records' list or a JSON array"
        }), 400

    if isinstance(payload, list):
        records = payload
    elif isinstance(payload, dict) and "records" in payload:
        records = payload["records"]
    else:
        return jsonify({
            "error": "invalid_batch_format",
            "message": "Payload must be a JSON array of records or an object with a 'records' key"
        }), 400

    if not isinstance(records, list):
        return jsonify({
            "error": "invalid_batch_format",
            "message": "'records' must be a JSON array"
        }), 400

    if len(records) == 0:
        return jsonify({"results": [], "count": 0}), 200

    if len(records) > 1000:
        return jsonify({
            "error": "batch_limit_exceeded",
            "message": f"Maximum batch size is 1,000 records; received {len(records)}"
        }), 400

    try:
        adapter = get_shadow_ingestion_adapter()
        scorer = get_default_scorer()
        adapter.shadow_service.prod_scorer = scorer
        results = adapter.route_batch_score(records, dict(request.headers))
        return jsonify({
            "count": len(results),
            "results": results
        }), 200
    except PermissionError as pe:
        logger.warning("Authentication failure on /api/score/batch: %s", str(pe))
        return jsonify({
            "error": "unauthorized",
            "message": str(pe)
        }), 401
    except SchemaValidationError as sve:
        logger.warning("Validation error on /api/score/batch: %s", str(sve))
        return jsonify({
            "error": "validation_error",
            "message": str(sve)
        }), 400
    except ArtifactLoadError as ale:
        logger.error("Artifact load error in batch: %s", str(ale))
        return jsonify({
            "error": "service_unavailable",
            "message": "Model scoring service is temporarily unavailable due to artifact loading failure."
        }), 503
    except Exception as e:
        logger.error("Unexpected error in batch scoring: %s", str(e))
        return jsonify({
            "error": "internal_scoring_error",
            "message": "An internal error occurred while processing the batch scoring request."
        }), 500


@app.route("/api/explain", methods=["POST", "OPTIONS"])
def explain_bridge_risk():
    """Returns local counterfactual feature attributions and risk drivers for a single bridge."""
    if request.method == "OPTIONS":
        return "", 204

    try:
        payload = request.get_json(silent=True)
    except Exception:
        return jsonify({"error": "malformed_request", "message": "Request body must be valid JSON"}), 400

    if payload is None:
        return jsonify({"error": "missing_payload", "message": "Request body must be a valid JSON object"}), 400

    record = payload.get("record", payload) if isinstance(payload, dict) and "record" in payload else payload

    if not isinstance(record, dict):
        return jsonify({"error": "invalid_record_format", "message": "Bridge record must be a JSON object"}), 400

    try:
        explainer = get_default_explainer()
        explanation = explainer.explain_record(record)
        return jsonify(explanation), 200
    except SchemaValidationError as sve:
        return jsonify({"error": "validation_error", "message": str(sve)}), 400
    except Exception as e:
        logger.error("Error explaining bridge prediction: %s", str(e))
        return jsonify({"error": "internal_explainer_error", "message": str(e)}), 500


@app.route("/api/model/feature-importance", methods=["GET"])
def model_feature_importance():
    """Returns global permutation feature importance rankings from Phase 17."""
    try:
        explainer = get_default_explainer()
        features = explainer.get_global_importances()
        return jsonify({
            "model": "HistGradientBoostingClassifier (Phase 17)",
            "methodology": "Permutation Importance (Held-Out Test Set)",
            "count": len(features),
            "features": features
        }), 200
    except Exception as e:
        logger.error("Error getting feature importances: %s", str(e))
        return jsonify({"error": "feature_importance_unavailable", "message": str(e)}), 500


@app.route("/api/onboarding/readiness", methods=["GET"])
def onboarding_readiness():
    """Returns Phase 22H onboarding readiness state, prerequisite verification, and configuration status."""
    try:
        adapter = get_shadow_ingestion_adapter()
        readiness = adapter.get_readiness_assessment()
        return jsonify(readiness), 200
    except Exception as e:
        logger.error("Failed to retrieve onboarding readiness: %s", str(e))
        return jsonify({
            "error": "onboarding_readiness_unavailable",
            "message": str(e)
        }), 500


@app.route("/api/onboarding/daily-evidence", methods=["GET"])
def onboarding_daily_evidence():
    """Returns an auditable, privacy-safe daily observation evidence record for a given UTC date."""
    try:
        date_param = request.args.get("date")
        adapter = get_shadow_ingestion_adapter()
        evidence = adapter.get_daily_evidence_record(target_date_str=date_param)
        return jsonify(evidence), 200
    except Exception as e:
        logger.error("Failed to retrieve daily evidence: %s", str(e))
        return jsonify({
            "error": "daily_evidence_unavailable",
            "message": str(e)
        }), 500


@app.route("/api/shadow/status", methods=["GET"])
def shadow_status():
    """Returns shadow deployment observation progress, telemetry summary, and gate evaluation."""
    try:
        shadow_service = get_shadow_scoring_service()
        summary = shadow_service.get_telemetry_summary()
        return jsonify(summary), 200
    except Exception as e:
        logger.error("Failed to retrieve shadow telemetry status: %s", str(e))
        return jsonify({
            "error": "shadow_telemetry_unavailable",
            "message": str(e)
        }), 500


@app.errorhandler(404)
def not_found_handler(e):
    return jsonify({
        "error": "not_found",
        "message": "The requested API endpoint was not found on this server."
    }), 404


@app.errorhandler(405)
def method_not_allowed_handler(e):
    return jsonify({
        "error": "method_not_allowed",
        "message": "HTTP method not allowed for this endpoint."
    }), 405


@app.errorhandler(500)
def server_error_handler(e):
    return jsonify({
        "error": "internal_server_error",
        "message": "An unexpected server error occurred."
    }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    logger.info("Starting Bridge Deterioration Risk Scoring API on %s:%d...", host, port)
    app.run(host=host, port=port, debug=False)
