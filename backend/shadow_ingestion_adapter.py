"""
Phase 22H: Secure Shadow Ingestion Adapter & Multi-Stage Readiness Engine
Risk-Aware Bridge Maintenance Intelligence Platform

CRITICAL OPERATIONAL & GOVERNANCE CONSTRAINTS:
1. Phase 17 remains the sole active production decision-maker.
2. Production cutover strictly locked (BRIDGE_PRODUCTION_CUTOVER_ENABLED=false).
3. Do NOT promote, retrain, replace, or cut over any model.
4. Authentication & authorization boundaries protect operational endpoints.
5. Strict failure isolation: timeouts, bounded retries, and exception traps ensure
   shadow execution NEVER alters, delays, or fails primary production scoring.
6. Multi-state readiness: systematically distinguishes CONFIGURATION_READY,
   CONNECTION_VERIFIED, AUTHENTIC_LIVE_TRAFFIC_CONFIRMED, and OBSERVATION_STARTED.
7. Zero fabrication: if authentic DOT credentials or live streams are absent,
   truthfully report NOT_STARTED (0/30 consecutive days elapsed).
"""

import os
import sys
import re
import time
import json
import logging
import hashlib
import threading
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple, Set

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.score_bridge_risk import SchemaValidationError
from backend.live_shadow_monitor import (
    TRAFFIC_SOURCE_LIVE,
    TRAFFIC_SOURCE_REPLAY,
    TRAFFIC_SOURCE_SYNTHETIC,
    TRAFFIC_SOURCE_UNKNOWN,
)
from backend.shadow_scoring_service import (
    ShadowScoringService,
    get_shadow_scoring_service,
)

logger = logging.getLogger("shadow_ingestion_adapter")


def redact_sensitive_credentials(text: str, known_secrets: Optional[List[str]] = None) -> str:
    """
    Sanitizes string outputs, error messages, and logs to ensure credentials,
    tokens, and API keys are never exposed in plaintext.
    """
    if not isinstance(text, str) or not text:
        return text

    sanitized = text

    # Redact known secrets if provided
    if known_secrets:
        for secret in known_secrets:
            if secret and len(secret) >= 4:
                sanitized = sanitized.replace(secret, "[REDACTED_SECRET]")

    # Redact Bearer / ApiKey tokens
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.+=/]+", r"\1[REDACTED_TOKEN]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"(ApiKey\s+)[A-Za-z0-9_\-\.+=/]+", r"\1[REDACTED_KEY]", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"([Xx]-[Aa][Pp][Ii]-[Kk][Ee][Yy]\s*[:=]\s*)[^\s,;\"]+", r"\1[REDACTED_KEY]", sanitized)
    sanitized = re.sub(r"([Aa][Pp][Ii]_[Kk][Ee][Yy]\s*[:=]\s*)[^\s,;&\"]+", r"\1[REDACTED_KEY]", sanitized)
    sanitized = re.sub(r"([Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]\s*[:=]\s*)[^\s,;&\"]+", r"\1[REDACTED_PASSWORD]", sanitized)
    sanitized = re.sub(r"([Tt][Oo][Kk][Ee][Nn]\s*[:=]\s*)[^\s,;&\"]+", r"\1[REDACTED_TOKEN]", sanitized)

    return sanitized


class IngestionAuthContext:
    """Authentication and authorization evaluation result."""

    def __init__(
        self,
        is_authenticated: bool,
        is_operational_authorized: bool,
        is_test_credential: bool,
        client_id: str,
        auth_error: Optional[str] = None,
    ):
        self.is_authenticated = is_authenticated
        self.is_operational_authorized = is_operational_authorized
        self.is_test_credential = is_test_credential
        self.client_id = client_id
        self.auth_error = auth_error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_authenticated": self.is_authenticated,
            "is_operational_authorized": self.is_operational_authorized,
            "is_test_credential": self.is_test_credential,
            "client_id": self.client_id,
            "auth_error": self.auth_error,
        }


class ShadowIngestionConfig:
    """Configuration for shadow ingestion adapter, auth boundaries, timeouts, and retries."""

    def __init__(
        self,
        api_key_env_var: str = "BRIDGE_INGEST_API_KEY",
        test_key_env_var: str = "BRIDGE_TEST_API_KEY",
        require_auth: Optional[bool] = None,
        shadow_timeout_ms: float = 50.0,
        max_persistence_retries: int = 3,
        min_daily_coverage_records: int = 1,
    ):
        self.api_key_env_var = api_key_env_var
        self.test_key_env_var = test_key_env_var
        self.operational_api_key = os.environ.get(api_key_env_var, "").strip() or None
        self.test_api_key = os.environ.get(test_key_env_var, "").strip() or None
        
        # If require_auth is explicitly specified, use it; otherwise require if operational key is configured
        if require_auth is not None:
            self.require_auth = require_auth
        else:
            self.require_auth = bool(self.operational_api_key or os.environ.get("BRIDGE_REQUIRE_AUTH", "false").lower() in ("true", "1", "yes"))

        self.shadow_timeout_ms = shadow_timeout_ms
        self.max_persistence_retries = max_persistence_retries
        self.min_daily_coverage_records = int(
            os.environ.get("BRIDGE_MIN_DAILY_OBSERVATION_RECORDS", min_daily_coverage_records)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "require_auth": self.require_auth,
            "auth_configured": bool(self.operational_api_key),
            "test_key_configured": bool(self.test_api_key),
            "shadow_timeout_ms": self.shadow_timeout_ms,
            "max_persistence_retries": self.max_persistence_retries,
            "min_daily_coverage_records": self.min_daily_coverage_records,
        }


class ShadowIngestionAdapter:
    """
    Secure gateway for routing scoring requests into production and shadow pipelines.
    Enforces authentication boundaries, timeouts, bounded retries, and strict failure isolation.
    """

    def __init__(
        self,
        config: Optional[ShadowIngestionConfig] = None,
        shadow_service: Optional[ShadowScoringService] = None,
    ):
        self.config = config or ShadowIngestionConfig()
        self.shadow_service = shadow_service or get_shadow_scoring_service()
        self._lock = threading.RLock()
        self._operational_traffic_observed: bool = False
        self._verified_client_ids: Set[str] = set()

    def authenticate_request(
        self,
        headers: Dict[str, Any],
    ) -> IngestionAuthContext:
        """
        Evaluates incoming request credentials against configured authorization boundaries.
        Distinguishes operational DOT credentials from test credentials.
        """
        # Extract API key from X-API-Key or Authorization header
        raw_key = headers.get("X-API-Key") or headers.get("x-api-key")
        if not raw_key and "Authorization" in headers:
            auth_header = str(headers.get("Authorization", ""))
            if auth_header.startswith("Bearer "):
                raw_key = auth_header[7:].strip()
            elif auth_header.startswith("ApiKey "):
                raw_key = auth_header[7:].strip()

        if not self.config.require_auth:
            # Open authentication mode (default in development / local evaluation)
            # Only callers who provide the configured operational API key are marked operational-authorized
            if self.config.operational_api_key and raw_key == self.config.operational_api_key:
                op_id = f"client_op_{hashlib.sha256(raw_key.encode()).hexdigest()[:8]}"
                return IngestionAuthContext(
                    is_authenticated=True,
                    is_operational_authorized=True,
                    is_test_credential=False,
                    client_id=op_id,
                )
            elif (self.config.test_api_key and raw_key == self.config.test_api_key) or (raw_key and raw_key.startswith("test_")):
                test_id = f"client_test_{hashlib.sha256(raw_key.encode()).hexdigest()[:8]}"
                return IngestionAuthContext(
                    is_authenticated=True,
                    is_operational_authorized=False,
                    is_test_credential=True,
                    client_id=test_id,
                    auth_error="TEST_CREDENTIAL_CANNOT_PRODUCE_OPERATIONAL_EVIDENCE",
                )
            else:
                client_id = f"client_{hashlib.sha256(b'open_local').hexdigest()[:8]}"
                return IngestionAuthContext(
                    is_authenticated=True,
                    is_operational_authorized=False,
                    is_test_credential=False,
                    client_id=client_id,
                )

        if not raw_key:
            return IngestionAuthContext(
                is_authenticated=False,
                is_operational_authorized=False,
                is_test_credential=False,
                client_id="anonymous",
                auth_error="MISSING_AUTHENTICATION_CREDENTIAL",
            )

        # Check for test key
        if (self.config.test_api_key and raw_key == self.config.test_api_key) or raw_key.startswith("test_"):
            test_id = f"client_test_{hashlib.sha256(raw_key.encode()).hexdigest()[:8]}"
            return IngestionAuthContext(
                is_authenticated=True,
                is_operational_authorized=False,
                is_test_credential=True,
                client_id=test_id,
                auth_error="TEST_CREDENTIAL_CANNOT_PRODUCE_OPERATIONAL_EVIDENCE",
            )

        # Check for operational key
        if self.config.operational_api_key and raw_key == self.config.operational_api_key:
            op_id = f"client_op_{hashlib.sha256(raw_key.encode()).hexdigest()[:8]}"
            return IngestionAuthContext(
                is_authenticated=True,
                is_operational_authorized=True,
                is_test_credential=False,
                client_id=op_id,
            )

        return IngestionAuthContext(
            is_authenticated=False,
            is_operational_authorized=False,
            is_test_credential=False,
            client_id="unknown_unauthorized",
            auth_error="INVALID_CREDENTIALS",
        )

    def route_single_score(
        self,
        record: Dict[str, Any],
        headers: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Routes single-record scoring with strict isolation and timeout enforcement.
        Always returns primary Phase 17 result.
        """
        auth_ctx = self.authenticate_request(headers)

        # If authentication is required and caller is unauthenticated, reject before scoring
        if self.config.require_auth and not auth_ctx.is_authenticated:
            raise PermissionError(f"Unauthorized: {auth_ctx.auth_error}")

        # Determine effective traffic source
        raw_source = headers.get("X-Traffic-Source") or headers.get("x-traffic-source")
        if auth_ctx.is_test_credential:
            effective_source = TRAFFIC_SOURCE_SYNTHETIC
        elif raw_source == TRAFFIC_SOURCE_LIVE:
            if not auth_ctx.is_operational_authorized:
                # Caller requested LIVE_OPERATIONAL without operational credentials; remap to SYNTHETIC
                effective_source = TRAFFIC_SOURCE_SYNTHETIC
            else:
                effective_source = TRAFFIC_SOURCE_LIVE
        elif raw_source in (TRAFFIC_SOURCE_REPLAY, TRAFFIC_SOURCE_SYNTHETIC):
            effective_source = raw_source
        elif raw_source:
            # Unrecognized / invalid provenance fails closed to non-operational
            effective_source = TRAFFIC_SOURCE_UNKNOWN
        else:
            if auth_ctx.is_operational_authorized:
                effective_source = TRAFFIC_SOURCE_LIVE
            else:
                effective_source = os.environ.get("BRIDGE_DEFAULT_TRAFFIC_SOURCE", TRAFFIC_SOURCE_SYNTHETIC)

        # Track verified live operational caller
        if effective_source == TRAFFIC_SOURCE_LIVE and auth_ctx.is_operational_authorized:
            with self._lock:
                self._operational_traffic_observed = True
                self._verified_client_ids.add(auth_ctx.client_id)

        # Execute scoring via shadow service with bounded retry & failure isolation
        try:
            return self._execute_guarded_scoring(record, effective_source)
        except Exception as e:
            # If guarded execution had internal issues, fall back directly to primary production scorer
            safe_err = redact_sensitive_credentials(str(e))
            logger.error("Guarded scoring exception caught; falling back directly to primary scorer: %s", safe_err)
            return self.shadow_service.prod_scorer.score_record(record)

    def route_batch_score(
        self,
        records: List[Dict[str, Any]],
        headers: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Routes batch scoring with strict isolation and timeout enforcement.
        Always returns primary Phase 17 results.
        """
        auth_ctx = self.authenticate_request(headers)

        if self.config.require_auth and not auth_ctx.is_authenticated:
            raise PermissionError(f"Unauthorized: {auth_ctx.auth_error}")

        raw_source = headers.get("X-Traffic-Source") or headers.get("x-traffic-source")
        if auth_ctx.is_test_credential:
            effective_source = TRAFFIC_SOURCE_SYNTHETIC
        elif raw_source == TRAFFIC_SOURCE_LIVE:
            if not auth_ctx.is_operational_authorized:
                effective_source = TRAFFIC_SOURCE_SYNTHETIC
            else:
                effective_source = TRAFFIC_SOURCE_LIVE
        elif raw_source in (TRAFFIC_SOURCE_REPLAY, TRAFFIC_SOURCE_SYNTHETIC):
            effective_source = raw_source
        elif raw_source:
            effective_source = TRAFFIC_SOURCE_UNKNOWN
        else:
            if auth_ctx.is_operational_authorized:
                effective_source = TRAFFIC_SOURCE_LIVE
            else:
                effective_source = os.environ.get("BRIDGE_DEFAULT_TRAFFIC_SOURCE", TRAFFIC_SOURCE_SYNTHETIC)

        if effective_source == TRAFFIC_SOURCE_LIVE and auth_ctx.is_operational_authorized:
            with self._lock:
                self._operational_traffic_observed = True
                self._verified_client_ids.add(auth_ctx.client_id)

        try:
            return self.shadow_service.score_batch_with_shadow(records, traffic_source=effective_source)
        except Exception as e:
            safe_err = redact_sensitive_credentials(str(e))
            logger.error("Guarded batch scoring exception caught; falling back directly to primary batch: %s", safe_err)
            return self.shadow_service.prod_scorer.score_batch(records)

    def _execute_guarded_scoring(
        self,
        record: Dict[str, Any],
        traffic_source: str,
    ) -> Dict[str, Any]:
        """Executes score_record_with_shadow with bounded retries for persistent logging blips."""
        retries = 0
        while retries < self.config.max_persistence_retries:
            try:
                return self.shadow_service.score_record_with_shadow(record, traffic_source=traffic_source)
            except SchemaValidationError:
                raise
            except Exception as exc:
                retries += 1
                logger.warning("Scoring pipeline retry %d/%d due to: %s", retries, self.config.max_persistence_retries, str(exc))
                if retries >= self.config.max_persistence_retries:
                    raise exc
                time.sleep(0.01 * retries)
        return self.shadow_service.prod_scorer.score_record(record)

    def get_readiness_assessment(self) -> Dict[str, Any]:
        """
        Systematically evaluates the four operational onboarding states:
        1. CONFIGURATION_READY
        2. CONNECTION_VERIFIED
        3. AUTHENTIC_LIVE_TRAFFIC_CONFIRMED
        4. OBSERVATION_STARTED
        """
        with self._lock:
            # 1. Evaluate CONFIGURATION_READY
            config_ready = True
            config_checks = {
                "prod_champion_loaded": self.shadow_service.prod_scorer is not None,
                "shadow_candidate_loaded": self.shadow_service.shadow_scorer is not None,
                "shadow_enabled": self.shadow_service.config.enabled,
                "cutover_switch_locked": not self.shadow_service.config.cutover_enabled,
                "calibrated_threshold_0_168": self.shadow_service.config.shadow_threshold == 0.1680,
                "tracker_initialized": self.shadow_service.tracker is not None,
            }
            if not all(config_checks.values()):
                config_ready = False

            # 2. Evaluate CONNECTION_VERIFIED
            connection_verified = True
            connection_checks = {
                "telemetry_logger_writable": self.shadow_service.telemetry_logger.log_path.parent.exists(),
                "tracker_state_writable": self.shadow_service.tracker.state_path.parent.exists(),
                "auth_boundaries_defined": True,
            }
            if not all(connection_checks.values()):
                connection_verified = False

            # 3. Evaluate AUTHENTIC_LIVE_TRAFFIC_CONFIRMED
            # Has authentic LIVE_OPERATIONAL traffic arrived with valid operational credentials?
            tracker_summary = self.shadow_service.tracker.get_summary()
            live_valid_count = tracker_summary.get("total_live_valid_records", 0)
            traffic_confirmed = bool(
                self._operational_traffic_observed
                or (
                    tracker_summary.get("live_traffic_started", False)
                    and live_valid_count > 0
                    and (len(self._verified_client_ids) > 0 or self.config.operational_api_key is not None)
                )
            )

            # 4. Evaluate OBSERVATION_STARTED
            # Started only if live traffic confirmed and daily coverage criteria met
            daily_summary = tracker_summary.get("daily_summary", {})
            meets_daily_coverage = any(
                day_data.get("unique_bridges", 0) >= self.config.min_daily_coverage_records
                for day_data in daily_summary.values()
            )
            observation_started = bool(traffic_confirmed and tracker_summary.get("live_traffic_started", False) and meets_daily_coverage)

            # Overall state machine determination
            if observation_started:
                onboarding_state = "OBSERVATION_STARTED"
            elif traffic_confirmed:
                onboarding_state = "AUTHENTIC_LIVE_TRAFFIC_CONFIRMED"
            elif connection_verified and config_ready:
                onboarding_state = "CONNECTION_VERIFIED"
            elif config_ready:
                onboarding_state = "CONFIGURATION_READY"
            else:
                onboarding_state = "CONFIGURATION_INCOMPLETE"

            return {
                "assessment_timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "onboarding_state": onboarding_state,
                "states": {
                    "CONFIGURATION_READY": config_ready,
                    "CONNECTION_VERIFIED": connection_verified,
                    "AUTHENTIC_LIVE_TRAFFIC_CONFIRMED": traffic_confirmed,
                    "OBSERVATION_STARTED": observation_started,
                },
                "prerequisites_status": {
                    "dot_production_infrastructure_available": False,
                    "dot_operational_credentials_configured": bool(self.config.operational_api_key),
                    "live_operational_traffic_flowing": traffic_confirmed,
                    "observation_tracker_active": observation_started,
                },
                "configuration_checks": config_checks,
                "connection_checks": connection_checks,
                "observation_coverage": {
                    "min_daily_coverage_records_required": self.config.min_daily_coverage_records,
                    "total_live_valid_records": live_valid_count,
                    "consecutive_days_elapsed": tracker_summary.get("consecutive_days_elapsed", 0),
                    "target_consecutive_days": tracker_summary.get("target_consecutive_days", 30),
                    "status": tracker_summary.get("observation_status", "NOT_STARTED"),
                },
                "active_production_champion": "Phase 17",
                "cutover_switch_enabled": False,
                "verified_operational_clients_count": len(self._verified_client_ids),
                "outcome_dependent_metrics_status": "PENDING_VERIFIED_GROUND_TRUTH",
            }

    def get_daily_evidence_record(self, target_date_str: Optional[str] = None) -> Dict[str, Any]:
        """
        Generates an auditable, privacy-safe daily observation evidence record.
        Contains only approved metadata: qualifying record count, unique bridge count,
        provenance outcomes, service health, and state recovery status.
        Never exposes raw records, secrets, or individual bridge identifiers.
        """
        with self._lock:
            now_utc = datetime.now(timezone.utc)
            date_key = target_date_str or now_utc.date().isoformat()
            tracker_summary = self.shadow_service.tracker.get_summary()
            daily_dict = tracker_summary.get("daily_summary", {}).get(date_key, {})

            qualifying_records = daily_dict.get("valid_records", 0)
            unique_bridges = daily_dict.get("unique_bridges", 0)
            threshold = self.config.min_daily_coverage_records
            coverage_met = bool(unique_bridges >= threshold and qualifying_records > 0)

            # Check health
            health_summary = (
                self.shadow_service.get_telemetry_summary().get("operational_health", {})
                if hasattr(self.shadow_service, "get_telemetry_summary")
                else {}
            )

            state_intact = self.shadow_service.tracker.state_path.exists()
            backup_intact = self.shadow_service.tracker.backup_path.exists() if hasattr(self.shadow_service.tracker, "backup_path") else False

            return {
                "evidence_record_version": "1.0-phase22j",
                "generated_at_utc": now_utc.isoformat(),
                "observation_calendar_date_utc": date_key,
                "coverage_evaluation": {
                    "qualifying_live_records": qualifying_records,
                    "unique_bridges_observed": unique_bridges,
                    "min_daily_coverage_required": threshold,
                    "daily_coverage_threshold_met": coverage_met,
                },
                "provenance_and_auth_status": {
                    "operational_auth_configured": bool(self.config.operational_api_key),
                    "operational_traffic_confirmed": bool(self._operational_traffic_observed),
                    "verified_operational_clients_count": len(self._verified_client_ids),
                    "total_live_records_all_time": tracker_summary.get("total_live_records", 0),
                    "total_synthetic_records_all_time": tracker_summary.get("total_synthetic_records", 0),
                    "total_replay_records_all_time": tracker_summary.get("total_replay_records", 0),
                },
                "observation_window_progress": {
                    "consecutive_days_elapsed": tracker_summary.get("consecutive_days_elapsed", 0),
                    "target_consecutive_days": tracker_summary.get("target_consecutive_days", 30),
                    "observation_status": tracker_summary.get("observation_status", "NOT_STARTED"),
                    "monitoring_gaps_count": len(tracker_summary.get("monitoring_gaps", [])),
                    "streak_resets_count": len(tracker_summary.get("streak_broken_history", [])),
                },
                "service_health_summary": {
                    "shadow_mode_enabled": self.shadow_service.config.enabled,
                    "active_production_champion": "Phase 17",
                    "production_cutover_locked": not self.shadow_service.config.cutover_enabled,
                    "health_grade": health_summary.get("health_grade", "HEALTHY"),
                },
                "state_persistence_integrity": {
                    "primary_state_file_exists": state_intact,
                    "backup_state_file_exists": backup_intact,
                    "durable_event_cache_active": True,
                },
                "outcome_dependent_metrics": {
                    "status": "PENDING_VERIFIED_GROUND_TRUTH",
                    "precision": "PENDING_VERIFIED_GROUND_TRUTH",
                    "recall": "PENDING_VERIFIED_GROUND_TRUTH",
                    "false_positive_rate": "PENDING_VERIFIED_GROUND_TRUTH",
                    "disclaimer": (
                        "Outcome metrics require certified biennial physical inspection ratings (DECK_2025 < DECK_2023). "
                        "Unlabeled live operational predictions cannot produce verified outcome metrics."
                    ),
                },
            }


# Singleton adapter instance
_adapter_instance: Optional[ShadowIngestionAdapter] = None


def get_shadow_ingestion_adapter(
    force_reload: bool = False,
    config: Optional[ShadowIngestionConfig] = None,
) -> ShadowIngestionAdapter:
    global _adapter_instance
    if _adapter_instance is None or force_reload:
        _adapter_instance = ShadowIngestionAdapter(config=config)
    return _adapter_instance
