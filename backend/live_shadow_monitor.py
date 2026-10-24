"""
Phase 22F: Live Shadow Monitoring and 30-Day Evidence Collection
Risk-Aware Bridge Maintenance Intelligence Platform

CRITICAL OPERATIONAL & GOVERNANCE CONSTRAINTS:
1. Phase 17 remains the sole active production champion.
2. Production cutover strictly locked (BRIDGE_PRODUCTION_CUTOVER_ENABLED=false).
3. Do NOT promote, retrain, replace, or cut over any model.
4. Distinguishes authentic live events from offline replay, synthetic tests, and duplicates.
5. Persistent 30-consecutive-calendar-day observation tracker that starts ONLY after
   verified live traffic begins; resets or flags gaps when daily continuity is broken.
6. Outcome-dependent metrics (precision, recall, FPR) remain explicitly marked PENDING
   until verified ground truth from biennial inspection is linked.
7. Zero fabrication: if real live traffic is unavailable, scaffolding is tested and
   observation status is reported as NOT_STARTED (0/30 days elapsed).
"""

import os
import sys
import json
import uuid
import time
import shutil
import logging
import threading
from collections import deque
from pathlib import Path
from datetime import datetime, date, timezone, timedelta
from typing import Dict, Any, List, Optional, Set, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("live_shadow_monitor")

BASE_DIR = Path(__file__).resolve().parent
P22_DIR = BASE_DIR / "results" / "phase22"
DEFAULT_TRACKER_STATE_PATH = P22_DIR / "observation_tracker_state.json"
DEFAULT_LIVE_TELEMETRY_PATH = P22_DIR / "live_shadow_telemetry.jsonl"

# Provenance definitions
TRAFFIC_SOURCE_LIVE = "LIVE_OPERATIONAL"
TRAFFIC_SOURCE_REPLAY = "OFFLINE_TEST_REPLAY"
TRAFFIC_SOURCE_SYNTHETIC = "SYNTHETIC_TEST"
TRAFFIC_SOURCE_UNKNOWN = "UNKNOWN"

VALID_TRAFFIC_SOURCES = {
    TRAFFIC_SOURCE_LIVE,
    TRAFFIC_SOURCE_REPLAY,
    TRAFFIC_SOURCE_SYNTHETIC,
    TRAFFIC_SOURCE_UNKNOWN,
}

# Model and calibrator version identifiers
PROD_MODEL_VERSION = "HistGradientBoostingClassifier-v17"
PROD_CALIBRATOR_VERSION = "PlattScaling-Phase18B"
SHADOW_MODEL_VERSION = "C10_unweighted_conservative-Phase21B"
SHADOW_CALIBRATOR_VERSION = "PlattScaling_5Fold_CrossFitted-Phase21B"


class TelemetryEventValidator:
    """
    Hardens telemetry collection against invalid clock data, stale timestamps,
    replay misclassification, and duplicate bridge submissions.
    Thread-safe and supports bounded ring-buffer eviction and durable idempotency.
    """

    def __init__(
        self,
        max_future_skew_seconds: float = 60.0,
        max_stale_seconds: float = 86400.0,  # 24 hours
        dedup_window_days: int = 1,
        max_seen_events: int = 100000,
        durable_cache_path: Optional[Path] = None,
    ):
        self._lock = threading.RLock()
        self.max_future_skew_seconds = max_future_skew_seconds
        self.max_stale_seconds = max_stale_seconds
        self.dedup_window_days = dedup_window_days
        self.max_seen_events = max_seen_events
        self.durable_cache_path = Path(durable_cache_path) if durable_cache_path else None
        self._seen_event_ids: Set[str] = set()
        self._seen_event_queue: deque = deque()
        # map of (bridge_id, date_str) to count
        self._seen_bridge_dates: Dict[Tuple[str, str], int] = {}

        if self.durable_cache_path:
            self._load_durable_cache()

    def _load_durable_cache(self) -> None:
        """Loads previously seen event IDs from durable cache to preserve idempotency across restarts."""
        with self._lock:
            if not self.durable_cache_path or not self.durable_cache_path.exists():
                return
            try:
                with open(self.durable_cache_path, "r", encoding="utf-8") as f:
                    for line in f:
                        eid = line.strip()
                        if eid and eid not in self._seen_event_ids:
                            self._seen_event_ids.add(eid)
                            self._seen_event_queue.append(eid)
                # Trim if exceeds max_seen_events
                while len(self._seen_event_queue) > self.max_seen_events:
                    evicted = self._seen_event_queue.popleft()
                    self._seen_event_ids.discard(evicted)
            except Exception as e:
                logger.warning("Failed to load durable event cache from %s: %s", self.durable_cache_path, str(e))

    def _append_durable_id(self, event_id: str) -> None:
        """Appends a new event ID to the durable cache."""
        if not self.durable_cache_path:
            return
        try:
            self.durable_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.durable_cache_path, "a", encoding="utf-8") as f:
                f.write(event_id + "\n")
        except Exception as e:
            logger.warning("Failed to append to durable event cache: %s", str(e))

    def generate_event_id(self) -> str:
        """Generates a privacy-safe unique event ID."""
        return f"evt_{uuid.uuid4().hex}"

    def validate_event(
        self,
        event_id: str,
        timestamp_str: str,
        bridge_id: str,
        traffic_source: str,
        wall_clock_now: Optional[datetime] = None,
    ) -> Tuple[str, List[str]]:
        """
        Validates telemetry event timestamp integrity, duplicate status, and traffic source.
        Returns: (validation_status, validation_tags)
        """
        with self._lock:
            tags: List[str] = []
            now_utc = wall_clock_now or datetime.now(timezone.utc)

            # 1. Traffic source classification
            if traffic_source not in VALID_TRAFFIC_SOURCES:
                traffic_source = TRAFFIC_SOURCE_UNKNOWN
                tags.append(f"INVALID_TRAFFIC_SOURCE_NORMALIZED_TO_{TRAFFIC_SOURCE}")

            if traffic_source != TRAFFIC_SOURCE_LIVE:
                tags.append(f"NON_LIVE_PROVENANCE:{traffic_source}")

            # 2. Parse Timestamp
            try:
                event_ts = datetime.fromisoformat(timestamp_str)
                if event_ts.tzinfo is None:
                    event_ts = event_ts.replace(tzinfo=timezone.utc)
            except Exception:
                tags.append("MALFORMED_TIMESTAMP")
                return "INVALID_TIMESTAMP", tags

            # 3. Future Clock Skew Check
            skew_seconds = (event_ts - now_utc).total_seconds()
            if skew_seconds > self.max_future_skew_seconds:
                tags.append(f"CLOCK_SKEW_FUTURE:{round(skew_seconds, 1)}s")
                return "REJECTED_CLOCK_SKEW", tags

            # 4. Stale Timestamp Check (for live traffic only)
            if traffic_source == TRAFFIC_SOURCE_LIVE:
                age_seconds = (now_utc - event_ts).total_seconds()
                if age_seconds > self.max_stale_seconds:
                    tags.append(f"STALE_TIMESTAMP:{round(age_seconds, 1)}s_OLD")
                    return "REJECTED_STALE_TIMESTAMP", tags

            # 5. Duplicate Event ID Check (Ring buffer with deterministic eviction)
            if event_id in self._seen_event_ids:
                tags.append("DUPLICATE_EVENT_ID")
                return "REJECTED_DUPLICATE_EVENT", tags

            self._seen_event_ids.add(event_id)
            self._seen_event_queue.append(event_id)
            if len(self._seen_event_queue) > self.max_seen_events:
                evicted = self._seen_event_queue.popleft()
                self._seen_event_ids.discard(evicted)

            if self.durable_cache_path:
                self._append_durable_id(event_id)

            # 6. Duplicate Bridge Submission in Same Day
            date_str = event_ts.date().isoformat()
            bridge_date_key = (bridge_id, date_str)
            prior_seen = self._seen_bridge_dates.get(bridge_date_key, 0)
            self._seen_bridge_dates[bridge_date_key] = prior_seen + 1
            if prior_seen > 0:
                tags.append(f"DUPLICATE_BRIDGE_SUBMISSION_COUNT:{prior_seen + 1}")

            # Final determination
            if traffic_source == TRAFFIC_SOURCE_LIVE:
                status = "VALID_LIVE"
            elif traffic_source == TRAFFIC_SOURCE_REPLAY:
                status = "VALID_REPLAY"
            elif traffic_source == TRAFFIC_SOURCE_SYNTHETIC:
                status = "VALID_SYNTHETIC"
            else:
                status = "VALID_NON_LIVE"

            return status, tags


class LiveObservationTracker:
    """
    Persistent 30-consecutive-calendar-day observation tracker.
    Thread-safe, crash-resilient with backup recovery, and handles out-of-order events.
    
    GOVERNANCE RULES:
    1. Observation starts ONLY after the first verified LIVE_OPERATIONAL record is processed.
    2. Daily eligible and scored counts are recorded per UTC calendar day.
    3. If 1 or more calendar days elapse without verified live traffic after observation has
       started, a monitoring gap is recorded and the consecutive streak is broken (consecutive_days_elapsed resets to 0).
    4. State is persisted atomically to JSON with .bak fallback to survive service crashes and power failures.
    5. Outcome-dependent metrics (precision, recall, FPR) are strictly marked PENDING until
       verified biennial NBI ground truth is available.
    """

    def __init__(
        self,
        state_path: Optional[Path] = None,
        target_consecutive_days: int = 30,
        min_daily_records: int = 1,
    ):
        self._lock = threading.RLock()
        self.state_path = Path(state_path or DEFAULT_TRACKER_STATE_PATH)
        self.target_consecutive_days = target_consecutive_days
        self.min_daily_records = min_daily_records

        # Tracker state fields
        self.observation_status: str = "NOT_STARTED"
        self.live_traffic_started: bool = False
        self.observation_start_date: Optional[str] = None
        self.last_observed_date: Optional[str] = None
        self.consecutive_days_elapsed: int = 0
        self.total_live_calendar_days: int = 0
        self.total_live_records_evaluated: int = 0
        self.total_live_valid_records: int = 0
        self.total_replay_records_evaluated: int = 0
        self.total_synthetic_records_evaluated: int = 0
        self.daily_records: Dict[str, Dict[str, Any]] = {}
        self.monitoring_gaps: List[Dict[str, Any]] = []
        self.streak_broken_history: List[Dict[str, Any]] = []

        # Load existing state if available
        self.load_state()

    def reset_tracker(self, reason: str = "Manual or Governance Reset") -> None:
        """Resets the observation tracker according to governance mandates."""
        with self._lock:
            logger.warning("Observation tracker reset: %s", reason)
            self.observation_status = "NOT_STARTED"
            self.live_traffic_started = False
            self.observation_start_date = None
            self.last_observed_date = None
            self.consecutive_days_elapsed = 0
            self.total_live_calendar_days = 0
            self.total_live_records_evaluated = 0
            self.total_live_valid_records = 0
            self.total_replay_records_evaluated = 0
            self.total_synthetic_records_evaluated = 0
            self.daily_records = {}
            self.monitoring_gaps = []
            self.streak_broken_history.append({
                "reset_timestamp": datetime.now(timezone.utc).isoformat(),
                "reason": reason,
            })
            self.save_state()

    def record_event(
        self,
        entry: Dict[str, Any],
        wall_clock_now: Optional[datetime] = None,
    ) -> None:
        """
        Records a telemetry event and updates consecutive observation metrics.
        Non-live events (replays, synthetic) are segregated and do NOT advance live streak.
        Thread-safe and supports out-of-order past events gracefully.
        """
        with self._lock:
            now_utc = wall_clock_now or datetime.now(timezone.utc)
            traffic_source = entry.get("traffic_source", TRAFFIC_SOURCE_LIVE)
            validation_status = entry.get("validation_status", "VALID")
            ts_str = entry.get("timestamp", now_utc.isoformat())

            try:
                event_date = datetime.fromisoformat(ts_str).date()
            except Exception:
                event_date = now_utc.date()

            date_str = event_date.isoformat()

            # Handle non-live events
            if traffic_source == TRAFFIC_SOURCE_REPLAY:
                self.total_replay_records_evaluated += 1
                self.save_state()
                return
            elif traffic_source == TRAFFIC_SOURCE_SYNTHETIC:
                self.total_synthetic_records_evaluated += 1
                self.save_state()
                return
            elif traffic_source != TRAFFIC_SOURCE_LIVE:
                return

            # It is a LIVE_OPERATIONAL event
            self.total_live_records_evaluated += 1
            if "REJECTED" in validation_status:
                self.save_state()
                return

            self.total_live_valid_records += 1

            # Check if this is the very first live operational event
            if not self.live_traffic_started:
                self.live_traffic_started = True
                self.observation_start_date = date_str
                self.last_observed_date = date_str
                self.consecutive_days_elapsed = 1
                self.total_live_calendar_days = 1
                self.observation_status = "IN_PROGRESS"
                self._init_daily_entry(date_str)
                self._update_daily_entry(date_str, entry)
                self.save_state()
                return

            # Check calendar continuity against last_observed_date
            last_date = datetime.fromisoformat(self.last_observed_date).date()
            date_diff = (event_date - last_date).days

            if date_diff == 0:
                # Same day: update daily statistics
                self._update_daily_entry(date_str, entry)
            elif date_diff == 1:
                # Exactly next consecutive day
                self.consecutive_days_elapsed += 1
                self.total_live_calendar_days += 1
                self.last_observed_date = date_str
                self._init_daily_entry(date_str)
                self._update_daily_entry(date_str, entry)

                if self.consecutive_days_elapsed >= self.target_consecutive_days:
                    self.observation_status = "TARGET_MET_PENDING_STAKEHOLDER_APPROVAL"
                else:
                    self.observation_status = "IN_PROGRESS"
            elif date_diff > 1:
                # GAP DETECTED: Break in consecutive monitoring days
                gap_info = {
                    "gap_start": (last_date + timedelta(days=1)).isoformat(),
                    "gap_end": (event_date - timedelta(days=1)).isoformat(),
                    "missing_calendar_days": date_diff - 1,
                    "detected_at": now_utc.isoformat(),
                    "streak_before_break": self.consecutive_days_elapsed,
                }
                self.monitoring_gaps.append(gap_info)
                self.streak_broken_history.append(gap_info)

                # Governance enforcement: Streak resets to 1 for the new day
                logger.warning(
                    "Live observation continuity broken: %d missing calendar days between %s and %s. Consecutive streak reset.",
                    date_diff - 1,
                    last_date,
                    event_date,
                )
                self.consecutive_days_elapsed = 1
                self.total_live_calendar_days += 1
                self.last_observed_date = date_str
                self.observation_status = "STREAK_RESET_GAP_DETECTED"
                self._init_daily_entry(date_str)
                self._update_daily_entry(date_str, entry)
            else:
                # Out-of-order past event (date_diff < 0): update past date without breaking current streak
                logger.info(
                    "Out-of-order past event received for date %s (current forward date is %s)",
                    date_str,
                    self.last_observed_date,
                )
                self._init_daily_entry(date_str)
                self._update_daily_entry(date_str, entry)

            self.save_state()

    def check_continuity_against_clock(self, wall_clock_now: Optional[datetime] = None) -> None:
        """
        Called periodically or upon audit to check if wall clock has advanced
        beyond last_observed_date without traffic (detecting active missing days).
        """
        with self._lock:
            if not self.live_traffic_started or not self.last_observed_date:
                return

            now_utc = wall_clock_now or datetime.now(timezone.utc)
            current_date = now_utc.date()
            last_date = datetime.fromisoformat(self.last_observed_date).date()
            date_diff = (current_date - last_date).days

            if date_diff > 1:
                # More than 1 full calendar day has passed with no traffic
                gap_info = {
                    "gap_start": (last_date + timedelta(days=1)).isoformat(),
                    "gap_end": (current_date - timedelta(days=1)).isoformat(),
                    "missing_calendar_days": date_diff - 1,
                    "detected_at": now_utc.isoformat(),
                    "streak_before_break": self.consecutive_days_elapsed,
                    "active_inactivity_gap": True,
                }
                if not any(g.get("gap_start") == gap_info["gap_start"] for g in self.monitoring_gaps):
                    self.monitoring_gaps.append(gap_info)
                    self.streak_broken_history.append(gap_info)
                    self.consecutive_days_elapsed = 0
                    self.observation_status = "STREAK_BROKEN_INACTIVITY"
                    self.save_state()

    def _init_daily_entry(self, date_str: str) -> None:
        if date_str not in self.daily_records:
            self.daily_records[date_str] = {
                "calendar_date": date_str,
                "eligible_records": 0,
                "scored_records": 0,
                "valid_records": 0,
                "unique_bridges": 0,
                "seen_bridges": [],
                "phase17_flagged": 0,
                "phase21b_flagged": 0,
                "decision_agreements": 0,
                "shadow_failures": 0,
                "state_breakdown": {},
            }

    def _update_daily_entry(self, date_str: str, entry: Dict[str, Any]) -> None:
        self._init_daily_entry(date_str)
        day = self.daily_records[date_str]
        day["eligible_records"] += 1
        day["scored_records"] += 1
        day["valid_records"] += 1

        if "seen_bridges" not in day or not isinstance(day["seen_bridges"], list):
            day["seen_bridges"] = []

        b_id = str(entry.get("bridge_id", "UNKNOWN"))
        if b_id not in day["seen_bridges"]:
            day["seen_bridges"].append(b_id)
            day["unique_bridges"] = len(day["seen_bridges"])

        if entry.get("prod_flag") is True:
            day["phase17_flagged"] += 1
        if entry.get("shadow_flag") is True:
            day["phase21b_flagged"] += 1
        if entry.get("workload_agreement") is True:
            day["decision_agreements"] += 1
        if entry.get("shadow_status") == "FAILED":
            day["shadow_failures"] += 1

        state_code = str(entry.get("state_code", "UNKNOWN"))
        if "state_breakdown" not in day or not isinstance(day["state_breakdown"], dict):
            day["state_breakdown"] = {}
        day["state_breakdown"][state_code] = day["state_breakdown"].get(state_code, 0) + 1

    def save_state(self) -> None:
        """Atomically saves tracker state to disk with automatic .bak backup preservation."""
        with self._lock:
            try:
                self.state_path.parent.mkdir(parents=True, exist_ok=True)
                temp_path = self.state_path.with_suffix(".tmp")
                backup_path = self.state_path.with_suffix(".bak")

                # Prune seen_bridges lists for compact serialization if very large, but preserve count
                serialized_daily = {}
                for d, data in self.daily_records.items():
                    copy_d = dict(data)
                    seen = copy_d.get("seen_bridges", [])
                    copy_d["unique_bridges"] = len(seen)
                    copy_d["seen_bridges"] = seen[:1000]  # Cap at 1,000 for storage efficiency
                    serialized_daily[d] = copy_d

                payload = {
                    "tracker_version": "2.1-phase22g",
                    "observation_window_days_target": self.target_consecutive_days,
                    "observation_status": self.observation_status,
                    "live_traffic_started": self.live_traffic_started,
                    "observation_start_date": self.observation_start_date,
                    "last_observed_date": self.last_observed_date,
                    "consecutive_days_elapsed": self.consecutive_days_elapsed,
                    "target_met": bool(self.consecutive_days_elapsed >= self.target_consecutive_days),
                    "total_live_calendar_days": self.total_live_calendar_days,
                    "total_live_records_evaluated": self.total_live_records_evaluated,
                    "total_live_valid_records": self.total_live_valid_records,
                    "total_replay_records_evaluated": self.total_replay_records_evaluated,
                    "total_synthetic_records_evaluated": self.total_synthetic_records_evaluated,
                    "daily_records": serialized_daily,
                    "monitoring_gaps": self.monitoring_gaps,
                    "streak_broken_history": self.streak_broken_history,
                    "last_state_update_utc": datetime.now(timezone.utc).isoformat(),
                    "governance_mandate": {
                        "active_production_champion": "Phase 17",
                        "production_cutover_enabled": False,
                        "target_semantics": "2-year routine deck rating degradation (DECK_2025 < DECK_2023)",
                        "outcome_metrics_status": "PENDING_VERIFIED_GROUND_TRUTH",
                    },
                }

                with open(temp_path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)

                # Maintain backup copy before replacing
                if self.state_path.exists():
                    try:
                        shutil.copy2(self.state_path, backup_path)
                    except Exception:
                        pass

                temp_path.replace(self.state_path)
            except Exception as e:
                logger.error("Failed to persist observation tracker state: %s", str(e))

    def load_state(self) -> None:
        """Loads tracker state from disk if present, with automatic fallback recovery from .bak."""
        with self._lock:
            if not self.state_path.exists():
                return
            data = None
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                logger.warning("Primary state file corrupted at %s: %s. Attempting recovery from backup.", self.state_path, str(e))
                backup_path = self.state_path.with_suffix(".bak")
                if backup_path.exists():
                    try:
                        with open(backup_path, "r", encoding="utf-8") as bf:
                            data = json.load(bf)
                        logger.info("Successfully recovered observation tracker state from %s", backup_path)
                    except Exception as be:
                        logger.error("Backup file also corrupted at %s: %s", backup_path, str(be))
                        return
                else:
                    return

            if not data:
                return

            self.target_consecutive_days = data.get("observation_window_days_target", self.target_consecutive_days)
            self.observation_status = data.get("observation_status", "NOT_STARTED")
            self.live_traffic_started = data.get("live_traffic_started", False)
            self.observation_start_date = data.get("observation_start_date")
            self.last_observed_date = data.get("last_observed_date")
            self.consecutive_days_elapsed = data.get("consecutive_days_elapsed", 0)
            self.total_live_calendar_days = data.get("total_live_calendar_days", 0)
            self.total_live_records_evaluated = data.get("total_live_records_evaluated", 0)
            self.total_live_valid_records = data.get("total_live_valid_records", 0)
            self.total_replay_records_evaluated = data.get("total_replay_records_evaluated", 0)
            self.total_synthetic_records_evaluated = data.get("total_synthetic_records_evaluated", 0)
            self.daily_records = data.get("daily_records", {})
            self.monitoring_gaps = data.get("monitoring_gaps", [])
            self.streak_broken_history = data.get("streak_broken_history", [])

    def get_summary(self) -> Dict[str, Any]:
        """Returns structured observation tracker progress."""
        with self._lock:
            progress_pct = round(
                min(100.0, (self.consecutive_days_elapsed / max(1, self.target_consecutive_days)) * 100.0),
                1,
            ) if self.live_traffic_started else 0.0

            return {
                "observation_status": self.observation_status,
                "live_traffic_started": self.live_traffic_started,
                "target_consecutive_days": self.target_consecutive_days,
                "consecutive_days_elapsed": self.consecutive_days_elapsed,
                "progress_pct": progress_pct,
                "target_met": bool(self.consecutive_days_elapsed >= self.target_consecutive_days),
                "observation_start_date": self.observation_start_date,
                "last_observed_date": self.last_observed_date,
                "total_live_records": self.total_live_records_evaluated,
                "total_live_valid_records": self.total_live_valid_records,
                "total_replay_records": self.total_replay_records_evaluated,
                "total_synthetic_records": self.total_synthetic_records_evaluated,
                "monitoring_gaps_count": len(self.monitoring_gaps),
                "monitoring_gaps": self.monitoring_gaps,
                "daily_summary": {
                    d: {
                        "eligible": v.get("eligible_records", 0),
                        "valid": v.get("valid_records", 0),
                        "unique_bridges": v.get("unique_bridges", 0),
                        "p17_flags": v.get("phase17_flagged", 0),
                        "p21_flags": v.get("phase21b_flagged", 0),
                        "shadow_failures": v.get("shadow_failures", 0),
                    }
                    for d, v in self.daily_records.items()
                },
            }


class OperationalHealthMonitor:
    """
    Computes operational health metrics, prediction distribution summaries,
    geographic disparities, and explicit pending-outcome statements.
    """

    def __init__(self, telemetry_entries: List[Dict[str, Any]]):
        self.entries = telemetry_entries

    def get_operational_health_summary(self) -> Dict[str, Any]:
        total = len(self.entries)
        if total == 0:
            return {
                "status": "NO_TELEMETRY",
                "total_records": 0,
                "availability_pct": 100.0,
                "shadow_failure_rate_pct": 0.0,
                "p95_latency_ms": 0.0,
                "prediction_distributions": {},
                "workload_and_geographic_disparities": {},
                "outcome_dependent_metrics": {
                    "precision": "PENDING_VERIFIED_GROUND_TRUTH",
                    "recall": "PENDING_VERIFIED_GROUND_TRUTH",
                    "false_positive_rate": "PENDING_VERIFIED_GROUND_TRUTH",
                    "disclaimer": "Ground truth deck degradation (DECK_2025 < DECK_2023) is unavailable for unverified live requests.",
                },
            }

        successful = [e for e in self.entries if e.get("shadow_status") == "SUCCESS"]
        failed = [e for e in self.entries if e.get("shadow_status") == "FAILED"]
        failure_rate = (len(failed) / total) * 100.0 if total > 0 else 0.0
        availability = 100.0 - failure_rate

        # Latencies
        shad_latencies = [
            e["shadow_latency_ms"]
            for e in successful
            if "shadow_latency_ms" in e and e["shadow_latency_ms"] is not None
        ]
        prod_latencies = [
            e["prod_latency_ms"]
            for e in self.entries
            if "prod_latency_ms" in e and e["prod_latency_ms"] is not None
        ]

        p95_shad = float(np.percentile(shad_latencies, 95)) if shad_latencies else 0.0
        p50_shad = float(np.percentile(shad_latencies, 50)) if shad_latencies else 0.0
        p95_prod = float(np.percentile(prod_latencies, 95)) if prod_latencies else 0.0

        # Calibrated prediction distributions
        p17_probs = [
            float(e["prod_calibrated_prob"])
            for e in self.entries
            if "prod_calibrated_prob" in e and e["prod_calibrated_prob"] is not None
        ]
        p21_probs = [
            float(e["shadow_calibrated_prob"])
            for e in successful
            if "shadow_calibrated_prob" in e and e["shadow_calibrated_prob"] is not None
        ]

        dist_p17 = self._compute_distribution_stats(p17_probs)
        dist_p21 = self._compute_distribution_stats(p21_probs)

        # Geographic & Workload Disparities
        geo_disparities: Dict[str, Dict[str, Any]] = {}
        total_p17_flags = sum(1 for e in self.entries if e.get("prod_flag") is True)
        total_p21_flags = sum(1 for e in successful if e.get("shadow_flag") is True)
        agreements = sum(1 for e in successful if e.get("workload_agreement") is True)

        for e in self.entries:
            st = str(e.get("state_code", "UNKNOWN"))
            if st not in geo_disparities:
                geo_disparities[st] = {
                    "evaluated_count": 0,
                    "phase17_flags": 0,
                    "phase21b_flags": 0,
                    "agreements": 0,
                }
            geo_disparities[st]["evaluated_count"] += 1
            if e.get("prod_flag") is True:
                geo_disparities[st]["phase17_flags"] += 1
            if e.get("shadow_flag") is True:
                geo_disparities[st]["phase21b_flags"] += 1
            if e.get("workload_agreement") is True:
                geo_disparities[st]["agreements"] += 1

        for st, data in geo_disparities.items():
            cnt = max(1, data["evaluated_count"])
            data["p17_workload_pct"] = round(data["phase17_flags"] / cnt * 100.0, 2)
            data["p21b_workload_pct"] = round(data["phase21b_flags"] / cnt * 100.0, 2)
            data["net_delta_flags"] = data["phase21b_flags"] - data["phase17_flags"]
            data["agreement_rate_pct"] = round(data["agreements"] / cnt * 100.0, 2)

        return {
            "status": "HEALTHY" if failure_rate <= 0.01 and p95_shad <= 15.0 else "DEGRADED",
            "total_telemetry_records": total,
            "successful_evaluations": len(successful),
            "failed_evaluations": len(failed),
            "availability_pct": round(availability, 3),
            "shadow_failure_rate_pct": round(failure_rate, 4),
            "latency_summary_ms": {
                "prod_p95": round(p95_prod, 2),
                "shadow_median": round(p50_shad, 2),
                "shadow_p95": round(p95_shad, 2),
                "sla_threshold_p95": 15.0,
                "sla_compliant": bool(p95_shad <= 15.0),
            },
            "overall_workload": {
                "prod_flagged_count": total_p17_flags,
                "prod_workload_pct": round((total_p17_flags / total) * 100.0, 2) if total > 0 else 0.0,
                "shadow_flagged_count": total_p21_flags,
                "shadow_workload_pct": round((total_p21_flags / len(successful)) * 100.0, 2) if successful else 0.0,
                "net_workload_difference": total_p21_flags - total_p17_flags,
                "decision_agreement_pct": round((agreements / len(successful)) * 100.0, 2) if successful else 0.0,
            },
            "prediction_distributions": {
                "phase17": dist_p17,
                "phase21b": dist_p21,
                "mean_probability_delta": round(dist_p21.get("mean", 0.0) - dist_p17.get("mean", 0.0), 5),
            },
            "geographic_disparities": geo_disparities,
            "outcome_dependent_metrics": {
                "precision": "PENDING_VERIFIED_GROUND_TRUTH",
                "recall": "PENDING_VERIFIED_GROUND_TRUTH",
                "false_positive_rate": "PENDING_VERIFIED_GROUND_TRUTH",
                "disclaimer": (
                    "Deterioration ground truth requires biennial FHWA inspection cycle (DECK_2025 < DECK_2023). "
                    "Unlabeled live operational predictions cannot produce verified precision or recall."
                ),
            },
        }

    def _compute_distribution_stats(self, values: List[float]) -> Dict[str, Any]:
        if not values:
            return {}
        arr = np.array(values, dtype=np.float64)
        p25 = float(np.percentile(arr, 25))
        p75 = float(np.percentile(arr, 75))
        return {
            "count": len(arr),
            "mean": round(float(np.mean(arr)), 5),
            "std": round(float(np.std(arr)), 5),
            "median": round(float(np.median(arr)), 5),
            "iqr": round(p75 - p25, 5),
            "p10": round(float(np.percentile(arr, 10)), 5),
            "p25": round(p25, 5),
            "p50": round(float(np.median(arr)), 5),
            "p75": round(p75, 5),
            "p90": round(float(np.percentile(arr, 90)), 5),
            "p95": round(float(np.percentile(arr, 95)), 5),
        }
