"""
Unit Tests for Phase 22F: Live Shadow Monitoring and 30-Day Evidence Collection
Risk-Aware Bridge Maintenance Intelligence Platform

Tests:
1. Baseline artifact immutability (Phase 17 champion and score_bridge_risk.py).
2. Replay segregation and rejection (offline replay does NOT count toward live streak).
3. Duplicate detection (same-day duplicate bridge submissions and duplicate event IDs).
4. Timestamp integrity (future clock skew, stale timestamps, malformed ISO strings).
5. State persistence and reload across service restarts.
6. Missing days and continuity break handling (gap detection, streak reset).
7. Empty traffic handling (clean zero-traffic reporting, no division-by-zero).
8. Privacy-conscious telemetry (sensitive engineering features never logged).
9. Rollback safety (disabling shadow mode immediately stops candidate evaluation).
10. Unlabeled metrics pending ground truth (precision/recall/FPR marked pending).
11. Prediction distributions and geographic disparities tracking.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, date, timezone, timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.score_bridge_risk import (
    BridgeRiskScorer,
    get_default_scorer,
    ALL_REQUIRED_FEATURES,
)
from backend.shadow_scoring_service import (
    ShadowDeploymentConfig,
    ShadowTelemetryLogger,
    ShadowScoringService,
)
from backend.live_shadow_monitor import (
    TelemetryEventValidator,
    LiveObservationTracker,
    OperationalHealthMonitor,
    TRAFFIC_SOURCE_LIVE,
    TRAFFIC_SOURCE_REPLAY,
    TRAFFIC_SOURCE_SYNTHETIC,
    TRAFFIC_SOURCE_UNKNOWN,
)
from backend.validate_shadow_mode_phase22c import sha256_file

BASE_DIR = Path(__file__).resolve().parent.parent
P17_DIR = BASE_DIR / "results" / "phase17"
P18_CAL_DIR = BASE_DIR / "results" / "phase18" / "calibration"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"


class TestPhase22FLiveShadowMonitoring(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)["fixtures"]
        cls.sample_record = cls.fixtures[0]["input_record"].copy()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_telemetry_path = Path(self.temp_dir) / "live_telemetry.jsonl"
        self.temp_tracker_path = Path(self.temp_dir) / "tracker_state.json"
        self.config = ShadowDeploymentConfig(
            enabled=True,
            cutover_enabled=False,
            telemetry_path=self.temp_telemetry_path,
            tracker_state_path=self.temp_tracker_path,
            observation_window_days=30,
            min_observation_records=10,
        )
        self.service = ShadowScoringService(config=self.config)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_01_baseline_immutability(self):
        """Verify score_bridge_risk.py and Phase 17 production artifacts remain byte-for-byte identical."""
        expected_hashes = {
            "score_bridge_risk.py": "b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61",
            "hist_gradient_boosting_classifier.joblib": "e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b",
            "cat_encoder.joblib": "14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772",
            "inference_metadata.json": "b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24",
            "serialization_manifest.json": "fedf43153bb898aafb2b1890873b2b65c9df7e1ef2a16292b2af75ecfc4d253e",
            "phase18_calibrator.joblib": "7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3",
        }
        self.assertEqual(sha256_file(BASE_DIR / "score_bridge_risk.py"), expected_hashes["score_bridge_risk.py"])
        self.assertEqual(sha256_file(P17_DIR / "hist_gradient_boosting_classifier.joblib"), expected_hashes["hist_gradient_boosting_classifier.joblib"])
        self.assertEqual(sha256_file(P17_DIR / "cat_encoder.joblib"), expected_hashes["cat_encoder.joblib"])
        self.assertEqual(sha256_file(P17_DIR / "inference_metadata.json"), expected_hashes["inference_metadata.json"])
        self.assertEqual(sha256_file(P17_DIR / "serialization_manifest.json"), expected_hashes["serialization_manifest.json"])
        self.assertEqual(sha256_file(P18_CAL_DIR / "phase18_calibrator.joblib"), expected_hashes["phase18_calibrator.joblib"])

    def test_02_replay_segregation_and_rejection(self):
        """Replayed offline test batches do NOT advance the live consecutive observation streak."""
        tracker = LiveObservationTracker(state_path=self.temp_tracker_path)

        # Record replay events
        for i in range(50):
            entry = {
                "bridge_id": f"bridge_{i}",
                "traffic_source": TRAFFIC_SOURCE_REPLAY,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "validation_status": "VALID_REPLAY",
            }
            tracker.record_event(entry)

        self.assertEqual(tracker.total_replay_records_evaluated, 50)
        self.assertFalse(tracker.live_traffic_started)
        self.assertEqual(tracker.consecutive_days_elapsed, 0)
        self.assertEqual(tracker.observation_status, "NOT_STARTED")

    def test_03_duplicate_detection(self):
        """Duplicate event IDs are rejected and same-day duplicate bridges are tagged."""
        validator = TelemetryEventValidator()
        event_id = validator.generate_event_id()
        now_ts = datetime.now(timezone.utc).isoformat()

        # First submission
        status1, tags1 = validator.validate_event(event_id, now_ts, "BRIDGE_001", TRAFFIC_SOURCE_LIVE)
        self.assertEqual(status1, "VALID_LIVE")

        # Duplicate event ID submission
        status2, tags2 = validator.validate_event(event_id, now_ts, "BRIDGE_001", TRAFFIC_SOURCE_LIVE)
        self.assertEqual(status2, "REJECTED_DUPLICATE_EVENT")
        self.assertIn("DUPLICATE_EVENT_ID", tags2)

        # Same bridge with new event ID on same day
        event_id_new = validator.generate_event_id()
        status3, tags3 = validator.validate_event(event_id_new, now_ts, "BRIDGE_001", TRAFFIC_SOURCE_LIVE)
        self.assertEqual(status3, "VALID_LIVE")
        self.assertTrue(any("DUPLICATE_BRIDGE_SUBMISSION_COUNT" in t for t in tags3))

    def test_04_timestamp_integrity(self):
        """Future clock skew and stale timestamps are detected and rejected."""
        validator = TelemetryEventValidator(max_future_skew_seconds=60.0, max_stale_seconds=86400.0)
        wall_clock = datetime(2026, 10, 15, 12, 0, 0, tzinfo=timezone.utc)

        # 1. Valid current timestamp
        valid_ts = (wall_clock - timedelta(seconds=10)).isoformat()
        st, _ = validator.validate_event(validator.generate_event_id(), valid_ts, "B1", TRAFFIC_SOURCE_LIVE, wall_clock_now=wall_clock)
        self.assertEqual(st, "VALID_LIVE")

        # 2. Future timestamp (> 60s ahead)
        future_ts = (wall_clock + timedelta(seconds=300)).isoformat()
        st_future, tags_future = validator.validate_event(validator.generate_event_id(), future_ts, "B2", TRAFFIC_SOURCE_LIVE, wall_clock_now=wall_clock)
        self.assertEqual(st_future, "REJECTED_CLOCK_SKEW")
        self.assertTrue(any("CLOCK_SKEW_FUTURE" in t for t in tags_future))

        # 3. Stale timestamp (> 24 hours behind)
        stale_ts = (wall_clock - timedelta(days=2)).isoformat()
        st_stale, tags_stale = validator.validate_event(validator.generate_event_id(), stale_ts, "B3", TRAFFIC_SOURCE_LIVE, wall_clock_now=wall_clock)
        self.assertEqual(st_stale, "REJECTED_STALE_TIMESTAMP")
        self.assertTrue(any("STALE_TIMESTAMP" in t for t in tags_stale))

        # 4. Malformed timestamp
        st_bad, tags_bad = validator.validate_event(validator.generate_event_id(), "not-a-timestamp", "B4", TRAFFIC_SOURCE_LIVE, wall_clock_now=wall_clock)
        self.assertEqual(st_bad, "INVALID_TIMESTAMP")

    def test_05_tracker_persistence_across_restarts(self):
        """Tracker accurately serializes state and recovers progress across service restarts."""
        tracker1 = LiveObservationTracker(state_path=self.temp_tracker_path)
        event_entry = {
            "bridge_id": "TEST_B1",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "timestamp": "2026-10-15T10:00:00+00:00",
            "validation_status": "VALID_LIVE",
            "prod_flag": False,
            "shadow_flag": True,
            "workload_agreement": False,
            "shadow_status": "SUCCESS",
            "state_code": "01",
        }
        tracker1.record_event(event_entry)

        self.assertTrue(tracker1.live_traffic_started)
        self.assertEqual(tracker1.consecutive_days_elapsed, 1)
        self.assertEqual(tracker1.observation_start_date, "2026-10-15")

        # Instantiate brand-new tracker pointing to the saved state file
        tracker2 = LiveObservationTracker(state_path=self.temp_tracker_path)
        self.assertTrue(tracker2.live_traffic_started)
        self.assertEqual(tracker2.consecutive_days_elapsed, 1)
        self.assertEqual(tracker2.observation_start_date, "2026-10-15")
        self.assertIn("2026-10-15", tracker2.daily_records)
        self.assertEqual(tracker2.daily_records["2026-10-15"]["scored_records"], 1)

    def test_06_missing_days_continuity_break(self):
        """Missing calendar days in monitoring trigger gap detection and reset the consecutive streak."""
        tracker = LiveObservationTracker(state_path=self.temp_tracker_path, target_consecutive_days=30)

        # Day 1: 2026-10-01
        tracker.record_event({
            "bridge_id": "B1",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "timestamp": "2026-10-01T12:00:00+00:00",
            "validation_status": "VALID_LIVE",
        })
        self.assertEqual(tracker.consecutive_days_elapsed, 1)

        # Day 2: 2026-10-02 (consecutive)
        tracker.record_event({
            "bridge_id": "B2",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "timestamp": "2026-10-02T12:00:00+00:00",
            "validation_status": "VALID_LIVE",
        })
        self.assertEqual(tracker.consecutive_days_elapsed, 2)

        # Day 4: 2026-10-04 (GAP: 2026-10-03 missing)
        tracker.record_event({
            "bridge_id": "B3",
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "timestamp": "2026-10-04T12:00:00+00:00",
            "validation_status": "VALID_LIVE",
        })

        # Governance rule: Continuity broken! Gap recorded, streak reset to 1
        self.assertEqual(len(tracker.monitoring_gaps), 1)
        gap = tracker.monitoring_gaps[0]
        self.assertEqual(gap["missing_calendar_days"], 1)
        self.assertEqual(gap["gap_start"], "2026-10-03")
        self.assertEqual(gap["streak_before_break"], 2)
        self.assertEqual(tracker.consecutive_days_elapsed, 1)
        self.assertEqual(tracker.observation_status, "STREAK_RESET_GAP_DETECTED")

    def test_07_empty_traffic_handling(self):
        """Service cleanly handles zero-traffic state without NaN or division errors."""
        summary = self.service.get_telemetry_summary()
        self.assertEqual(summary["total_records_evaluated"], 0)
        self.assertIn("outcome_dependent_metrics", summary)
        self.assertEqual(summary["outcome_dependent_metrics"]["precision"], "PENDING_VERIFIED_GROUND_TRUTH")
        self.assertEqual(summary["observation_progress"]["live_observation_tracker"]["observation_status"], "NOT_STARTED")
        self.assertFalse(summary["observation_progress"]["live_observation_tracker"]["live_traffic_started"])

    def test_08_privacy_conscious_telemetry(self):
        """Telemetry logs omit raw sensitive bridge engineering features."""
        rec = self.sample_record.copy()
        rec["structure_len_mt"] = 125.5
        rec["deck_width_mt"] = 14.2
        rec["adt"] = 45000
        rec["year_built"] = 1978

        self.service.score_record_with_shadow(rec, traffic_source=TRAFFIC_SOURCE_LIVE)

        lines = self.temp_telemetry_path.read_text(encoding="utf-8").strip().splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])

        # Allowed metadata keys
        self.assertIn("event_id", entry)
        self.assertIn("timestamp", entry)
        self.assertIn("traffic_source", entry)
        self.assertIn("validation_status", entry)
        self.assertIn("bridge_id", entry)
        self.assertIn("state_code", entry)

        # Prohibited raw engineering keys
        prohibited = ["structure_len_mt", "deck_width_mt", "adt", "year_built", "detour_kilos"]
        for p in prohibited:
            self.assertNotIn(p, entry)

    def test_09_rollback_safety(self):
        """Disabling shadow mode cleanly stops candidate evaluation and telemetry logging."""
        cfg = ShadowDeploymentConfig(
            enabled=False,
            telemetry_path=self.temp_telemetry_path,
            tracker_state_path=self.temp_tracker_path,
        )
        service_disabled = ShadowScoringService(config=cfg)
        self.assertIsNone(service_disabled.shadow_scorer)

        res = service_disabled.score_record_with_shadow(self.sample_record)
        self.assertIn("calibrated_deterioration_probability", res)
        self.assertEqual(res["model_metadata"]["service_phase"], "Phase 18C")
        self.assertFalse(self.temp_telemetry_path.exists())

    def test_10_unlabeled_metrics_remain_pending(self):
        """Precision, recall, and false-positive rates must not be claimed on unlabeled live data."""
        # Score a record
        self.service.score_record_with_shadow(self.sample_record, traffic_source=TRAFFIC_SOURCE_LIVE)
        summary = self.service.get_telemetry_summary()

        outcomes = summary.get("outcome_dependent_metrics", {})
        self.assertEqual(outcomes["precision"], "PENDING_VERIFIED_GROUND_TRUTH")
        self.assertEqual(outcomes["recall"], "PENDING_VERIFIED_GROUND_TRUTH")
        self.assertEqual(outcomes["false_positive_rate"], "PENDING_VERIFIED_GROUND_TRUTH")
        self.assertIn("disclaimer", outcomes)

    def test_11_prediction_distribution_and_geographic_disparities(self):
        """OperationalHealthMonitor generates probability distributions and geographic disparity breakdowns."""
        rec1 = self.sample_record.copy()
        rec1["state_code"] = "01"
        rec2 = self.sample_record.copy()
        rec2["state_code"] = "06"

        self.service.score_record_with_shadow(rec1, traffic_source=TRAFFIC_SOURCE_LIVE)
        self.service.score_record_with_shadow(rec2, traffic_source=TRAFFIC_SOURCE_LIVE)

        summary = self.service.get_telemetry_summary()
        health = summary.get("operational_health", {})
        self.assertIn("prediction_distributions", health)
        self.assertIn("phase17", health["prediction_distributions"])
        self.assertIn("phase21b", health["prediction_distributions"])

        geo = health.get("geographic_disparities", {})
        self.assertIn("01", geo)
        self.assertIn("06", geo)
        self.assertEqual(geo["01"]["evaluated_count"], 1)
        self.assertEqual(geo["06"]["evaluated_count"], 1)


if __name__ == "__main__":
    unittest.main()
