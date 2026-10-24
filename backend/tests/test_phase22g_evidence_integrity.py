"""
Phase 22G: Evidence Integrity Audit and Promotion Readiness Tests
Risk-Aware Bridge Maintenance Intelligence Platform

Tests:
1. Baseline artifact immutability (Phase 17 champion and score_bridge_risk.py).
2. Provenance segregation (offline replay and synthetic events cannot advance live streak).
3. Concurrency thread safety (multi-threaded concurrent validation and tracker updates).
4. Durable idempotency across restarts (persisted event ID cache rejects replayed events after reload).
5. Ring buffer eviction (bounded memory footprint with deterministic FIFO eviction).
6. Atomic persistence and recovery (automatic fallback to .bak upon JSON corruption).
7. UTC day-boundary and out-of-order event handling (past-day records update without breaking forward streak).
8. Candidate model, calibrator, and calibrated threshold (0.1680) contract verification.
9. Strict outcome-independence governance (precision, recall, FPR marked PENDING_VERIFIED_GROUND_TRUTH).
10. Zero fabrication & cutover safety lock (status is NOT_STARTED when live traffic is 0, cutover locked).
"""

import os
import sys
import json
import shutil
import tempfile
import threading
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
P21B_DIR = BASE_DIR / "results" / "phase21b"
P22_DIR = BASE_DIR / "results" / "phase22"
FIXTURES_PATH = BASE_DIR / "tests" / "fixtures" / "regression_test_fixture.json"


class TestPhase22GEvidenceIntegrity(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        with open(FIXTURES_PATH, "r", encoding="utf-8") as f:
            cls.fixtures = json.load(f)["fixtures"]
        cls.sample_record = cls.fixtures[0]["input_record"].copy()

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_telemetry_path = Path(self.temp_dir) / "telemetry.jsonl"
        self.temp_tracker_path = Path(self.temp_dir) / "tracker_state.json"
        self.temp_cache_path = Path(self.temp_dir) / "event_id_cache.txt"
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
        """Verify score_bridge_risk.py and all Phase 17 baseline files remain 100% byte-for-byte identical."""
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

    def test_02_provenance_clock_isolation(self):
        """Verify that offline replays and synthetic events cannot advance the live observation clock."""
        tracker = LiveObservationTracker(state_path=self.temp_tracker_path)
        self.assertFalse(tracker.live_traffic_started)
        self.assertEqual(tracker.consecutive_days_elapsed, 0)

        # Ingest 500 replay events across multiple simulated dates
        for day_offset in range(5):
            sim_date = (date(2026, 10, 1) + timedelta(days=day_offset)).isoformat()
            entry = {
                "traffic_source": TRAFFIC_SOURCE_REPLAY,
                "timestamp": f"{sim_date}T12:00:00+00:00",
                "bridge_id": f"bridge_replay_{day_offset}",
                "validation_status": "VALID_REPLAY",
            }
            tracker.record_event(entry)

        # Ingest 100 synthetic events
        for i in range(100):
            entry = {
                "traffic_source": TRAFFIC_SOURCE_SYNTHETIC,
                "timestamp": "2026-10-06T12:00:00+00:00",
                "bridge_id": f"bridge_synth_{i}",
                "validation_status": "VALID_SYNTHETIC",
            }
            tracker.record_event(entry)

        # Clock must remain NOT_STARTED, consecutive days 0
        summary = tracker.get_summary()
        self.assertFalse(summary["live_traffic_started"])
        self.assertEqual(summary["consecutive_days_elapsed"], 0)
        self.assertEqual(summary["observation_status"], "NOT_STARTED")
        self.assertEqual(summary["total_replay_records"], 5)
        self.assertEqual(summary["total_synthetic_records"], 100)

    def test_03_concurrency_thread_safety(self):
        """Verify multi-threaded concurrent requests maintain state consistency without deadlocks or corrupted writes."""
        tracker = LiveObservationTracker(state_path=self.temp_tracker_path)
        validator = TelemetryEventValidator(durable_cache_path=self.temp_cache_path)
        now_ts = "2026-10-15T10:00:00+00:00"
        num_threads = 10
        records_per_thread = 20
        errors = []

        def worker(thread_idx):
            try:
                for j in range(records_per_thread):
                    b_id = f"bridge_th{thread_idx}_{j}"
                    e_id = f"evt_th{thread_idx}_{j}"
                    v_status, _ = validator.validate_event(
                        event_id=e_id,
                        timestamp_str=now_ts,
                        bridge_id=b_id,
                        traffic_source=TRAFFIC_SOURCE_LIVE,
                        wall_clock_now=datetime.fromisoformat(now_ts),
                    )
                    entry = {
                        "event_id": e_id,
                        "timestamp": now_ts,
                        "bridge_id": b_id,
                        "traffic_source": TRAFFIC_SOURCE_LIVE,
                        "validation_status": v_status,
                        "prod_flag": bool(j % 2 == 0),
                        "shadow_flag": bool(j % 2 == 0),
                        "workload_agreement": True,
                    }
                    tracker.record_event(entry, wall_clock_now=datetime.fromisoformat(now_ts))
            except Exception as e:
                errors.append(f"Thread {thread_idx} error: {str(e)}")

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Thread errors: {errors}")
        summary = tracker.get_summary()
        expected_total = num_threads * records_per_thread
        self.assertEqual(summary["total_live_records"], expected_total)
        self.assertEqual(summary["consecutive_days_elapsed"], 1)
        self.assertTrue(summary["live_traffic_started"])

    def test_04_durable_idempotency_across_restarts(self):
        """Verify that event IDs persisted to durable cache are recognized as duplicates after process restart."""
        val1 = TelemetryEventValidator(durable_cache_path=self.temp_cache_path)
        e_id = "evt_persisted_test_123"
        ts = "2026-10-15T12:00:00+00:00"
        status1, _ = val1.validate_event(e_id, ts, "B001", TRAFFIC_SOURCE_LIVE, wall_clock_now=datetime.fromisoformat(ts))
        self.assertEqual(status1, "VALID_LIVE")

        # Simulate process termination and reboot by instantiating new validator with same cache path
        val2 = TelemetryEventValidator(durable_cache_path=self.temp_cache_path)
        status2, tags2 = val2.validate_event(e_id, ts, "B001", TRAFFIC_SOURCE_LIVE, wall_clock_now=datetime.fromisoformat(ts))
        self.assertEqual(status2, "REJECTED_DUPLICATE_EVENT")
        self.assertIn("DUPLICATE_EVENT_ID", tags2)

    def test_05_ring_buffer_bounded_eviction(self):
        """Verify bounded ring buffer evicts oldest event IDs when capacity is reached."""
        max_cap = 5
        validator = TelemetryEventValidator(max_seen_events=max_cap)
        ts = "2026-10-15T12:00:00+00:00"

        # Submit 5 unique events
        for i in range(5):
            status, _ = validator.validate_event(f"evt_{i}", ts, f"B{i}", TRAFFIC_SOURCE_LIVE, wall_clock_now=datetime.fromisoformat(ts))
            self.assertEqual(status, "VALID_LIVE")

        self.assertEqual(len(validator._seen_event_ids), 5)

        # Submit 6th event -> evt_0 should be evicted
        status6, _ = validator.validate_event("evt_5", ts, "B5", TRAFFIC_SOURCE_LIVE, wall_clock_now=datetime.fromisoformat(ts))
        self.assertEqual(status6, "VALID_LIVE")
        self.assertEqual(len(validator._seen_event_ids), 5)
        self.assertNotIn("evt_0", validator._seen_event_ids)
        self.assertIn("evt_5", validator._seen_event_ids)

    def test_06_atomic_persistence_and_bak_recovery(self):
        """Verify tracker recovers from .bak when primary state JSON is corrupted."""
        tracker = LiveObservationTracker(state_path=self.temp_tracker_path)
        ts1 = "2026-10-15T12:00:00+00:00"
        entry1 = {
            "traffic_source": TRAFFIC_SOURCE_LIVE,
            "timestamp": ts1,
            "bridge_id": "B_STATE_TEST",
            "validation_status": "VALID_LIVE",
        }
        tracker.record_event(entry1, wall_clock_now=datetime.fromisoformat(ts1))
        self.assertEqual(tracker.consecutive_days_elapsed, 1)

        # Trigger save to create .bak
        tracker.save_state()
        bak_path = self.temp_tracker_path.with_suffix(".bak")
        self.assertTrue(bak_path.exists())

        # Corrupt primary state file
        with open(self.temp_tracker_path, "w", encoding="utf-8") as f:
            f.write("{MALFORMED_JSON_CORRUPTED_DURING_POWER_LOSS")

        # Reload tracker: should successfully recover from .bak
        recovered_tracker = LiveObservationTracker(state_path=self.temp_tracker_path)
        self.assertTrue(recovered_tracker.live_traffic_started)
        self.assertEqual(recovered_tracker.consecutive_days_elapsed, 1)
        self.assertEqual(recovered_tracker.last_observed_date, "2026-10-15")

    def test_07_utc_day_boundary_and_out_of_order_past_events(self):
        """Verify out-of-order past events (e.g. network latency) update past date without breaking current streak."""
        tracker = LiveObservationTracker(state_path=self.temp_tracker_path)

        # Day 1: 2026-10-10
        ts1 = "2026-10-10T12:00:00+00:00"
        tracker.record_event({"traffic_source": TRAFFIC_SOURCE_LIVE, "timestamp": ts1, "bridge_id": "B10", "validation_status": "VALID_LIVE"}, wall_clock_now=datetime.fromisoformat(ts1))
        self.assertEqual(tracker.consecutive_days_elapsed, 1)

        # Day 2: 2026-10-11
        ts2 = "2026-10-11T12:00:00+00:00"
        tracker.record_event({"traffic_source": TRAFFIC_SOURCE_LIVE, "timestamp": ts2, "bridge_id": "B11", "validation_status": "VALID_LIVE"}, wall_clock_now=datetime.fromisoformat(ts2))
        self.assertEqual(tracker.consecutive_days_elapsed, 2)

        # Out-of-order event for Day 1 arriving on Day 2
        ts1_late = "2026-10-10T23:59:00+00:00"
        tracker.record_event({"traffic_source": TRAFFIC_SOURCE_LIVE, "timestamp": ts1_late, "bridge_id": "B10_late", "validation_status": "VALID_LIVE"}, wall_clock_now=datetime.fromisoformat(ts2))

        # Forward streak must remain 2, not reset!
        self.assertEqual(tracker.consecutive_days_elapsed, 2)
        self.assertEqual(tracker.last_observed_date, "2026-10-11")
        # Day 1 record count should be updated
        self.assertEqual(tracker.daily_records["2026-10-10"]["valid_records"], 2)

    def test_08_candidate_artifacts_and_threshold_contract(self):
        """Verify candidate model, calibrator, and calibrated threshold (0.1680) match approved Phase 22 artifacts."""
        expected_candidate_model_hash = "aa806c8185db465fd02536d2d4310638c499d41560ac759e0ea15d4a60f98443"
        expected_calibrator_hash = "cd9d2f3833112e9fd90b5bd355646a1e68f50ac5218b038a95f0d31766c5978f"

        self.assertEqual(sha256_file(P21B_DIR / "phase21b_tuned_model.joblib"), expected_candidate_model_hash)
        self.assertEqual(sha256_file(P21B_DIR / "phase21b_calibrator.joblib"), expected_calibrator_hash)

        # Verify threshold manifest contract
        manifest_path = P22_DIR / "phase22_threshold_manifest.json"
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        max_f1_policy = manifest["policy_presets_training_oof"]["max_f1_balanced"]
        self.assertEqual(max_f1_policy["threshold"], 0.168)
        self.assertEqual(max_f1_policy["policy_name"], "Maximum F1 Balanced Inspection")
        self.assertEqual(self.service.config.shadow_threshold, 0.1680)

    def test_09_outcome_metrics_governance_disclaimer(self):
        """Verify precision, recall, and FPR are marked PENDING_VERIFIED_GROUND_TRUTH."""
        summary = self.service.get_telemetry_summary()
        outcomes = summary.get("outcome_dependent_metrics", {})
        self.assertEqual(outcomes.get("precision"), "PENDING_VERIFIED_GROUND_TRUTH")
        self.assertEqual(outcomes.get("recall"), "PENDING_VERIFIED_GROUND_TRUTH")
        self.assertEqual(outcomes.get("false_positive_rate"), "PENDING_VERIFIED_GROUND_TRUTH")
        self.assertIn("DECK_2025 < DECK_2023", outcomes.get("disclaimer", ""))

    def test_10_zero_fabrication_and_cutover_safety_lock(self):
        """Verify platform truthfully reports NOT_STARTED when live traffic is 0 and cutover is locked."""
        summary = self.service.get_telemetry_summary()
        obs_prog = summary.get("observation_progress", {})
        self.assertIn("NOT_STARTED", obs_prog.get("temporal_status", ""))
        self.assertEqual(obs_prog.get("calendar_days_elapsed"), 0)
        self.assertFalse(obs_prog.get("temporal_window_completed"))
        self.assertFalse(self.service.config.cutover_enabled)
        self.assertEqual(summary.get("active_production_champion"), "Phase 17 (HistGradientBoostingClassifier + Phase 18B Platt Calibrator)")
        self.assertEqual(summary.get("overall_gate_readiness"), "OBSERVATION_IN_PROGRESS")


if __name__ == "__main__":
    unittest.main()
