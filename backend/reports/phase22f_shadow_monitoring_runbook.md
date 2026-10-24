# Phase 22F: Live Shadow Monitoring and 30-Day Evidence Collection Runbook

**Project:** Risk-Aware Bridge Maintenance Intelligence Platform  
**Target Definition:** Routine Biennial Deck Condition Degradation ($\text{DECK}_{2025} < \text{DECK}_{2023}$)  
**Active Production Champion:** Phase 17 HistGradientBoostingClassifier + Phase 18B Platt Calibrator (`backend/score_bridge_risk.py`)  
**Shadow Candidate:** Phase 21B Tuned Model (`C10_unweighted_conservative`) + Cross-Fitted Platt Calibrator (`\tau^*_{\text{cal}} = 0.1680`)  
**Production Cutover Status:** **STRICTLY DISABLED (`BRIDGE_PRODUCTION_CUTOVER_ENABLED=false`)**  
**Live Observation Window Target:** 30 Consecutive Calendar Days (UTC)  
**Current Observation Status:** **NOT_STARTED (Awaiting verified LIVE_OPERATIONAL bridge scoring traffic; 0/30 consecutive days elapsed)**  

---

## 1. Executive Summary & Purpose

This operational runbook establishes the formal operating procedures, engineering standards, and governance protocols for **Phase 22F: Live Shadow Monitoring and 30-Day Evidence Collection** for the Risk-Aware Bridge Maintenance Intelligence Platform.

Phase 22F provides production-grade, zero-risk evaluation of candidate model improvements without altering live bridge maintenance decisions, risking platform downtime, or violating safety baselines:
1. **Zero Production Risk:** Phase 17 remains the sole production decision maker. All decisions returned to end users and API clients originate strictly from Phase 17.
2. **Hardened Dual Telemetry:** Every incoming scoring event is validated, pseudonymized, and simultaneously evaluated through Phase 17 and Phase 21B pipelines.
3. **Strict Provenance Segregation:** Traffic source headers explicitly segregate `LIVE_OPERATIONAL` traffic from `OFFLINE_TEST_REPLAY` and `SYNTHETIC_TEST` batches. Only genuine live operational events advance the 30-day monitoring tracker.
4. **Consecutive Day Continuity Enforcement:** The observation tracker requires 30 unbroken consecutive calendar days in UTC. Any calendar day with zero valid live operational events triggers a gap detection and resets the consecutive streak to zero.
5. **Zero Fabrication Guarantee:** If real-world DOT client traffic has not yet commenced, the system truthfully reports `NOT_STARTED` (0/30 days). No historical or synthetic events are counted toward live operational observation.
6. **Strict Outcome-Independence Governance:** Routine bridge deck degradation ($\text{DECK}_{2025} < \text{DECK}_{2023}$) requires physical biennial inspections by certified DOT bridge inspectors. Because live operational scoring events have no immediate ground truth labels, all outcome-dependent metrics (precision, recall, FPR) are strictly prohibited from live telemetry and are recorded as `PENDING_VERIFIED_GROUND_TRUTH`.

---

## 2. Cryptographic Checksum Register (Baseline Immutability)

Baseline production scoring logic and historical artifacts remain immutable. Verification against trusted manifests was conducted prior to and immediately following Phase 22F implementation:

| Artifact Path | Description | Expected SHA-256 Checksum | Status |
|---|---|---|---|
| `backend/score_bridge_risk.py` | Production inference scoring interface | `b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61` | **UNTOUCHED** |
| `backend/results/phase17/hist_gradient_boosting_classifier.joblib` | Production champion classifier | `e2b4e2ec334c18b343a55b1bc26395b3684f76678cfa80d4ccc9edf588b6da0b` | **UNTOUCHED** |
| `backend/results/phase17/cat_encoder.joblib` | Production categorical encoder | `14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772` | **UNTOUCHED** |
| `backend/results/phase17/inference_metadata.json` | Production inference metadata | `b48922c28ee102d65f5af55fd6be446586bcc358e564e652455f8c1b8bedea24` | **UNTOUCHED** |
| `backend/results/phase17/serialization_manifest.json` | Phase 17 serialization manifest | `fedf43153bb898aafb2b1890873b2b65c9df7e1ef2a16292b2af75ecfc4d253e` | **UNTOUCHED** |
| `backend/results/phase18/calibration/phase18_calibrator.joblib` | Production Platt calibrator | `7fb7915aefc952c87a17b347004bd2f3f6061f1ad9172e3a9f6f41e2732cfbd3` | **UNTOUCHED** |
| `backend/results/phase21b/phase21b_tuned_model.joblib` | Candidate tuned model (C10) | `aa806c8185db465fd02536d2d4310638c499d41560ac759e0ea15d4a60f98443` | **VERIFIED** |
| `backend/results/phase21b/phase21b_encoder.joblib` | Candidate categorical encoder | `14fe2087570446889226640ebb8508e7e832be9b2241c9f92407f9a3f10c6772` | **VERIFIED** |
| `backend/results/phase21b/phase21b_calibrator.joblib` | Candidate cross-fitted calibrator | `cd9d2f3833112e9fd90b5bd355646a1e68f50ac5218b038a95f0d31766c5978f` | **VERIFIED** |
| `backend/results/phase22/phase22_threshold_manifest.json` | Master threshold manifest | `79c53545d966740a6bed59eb25c7624ec3868ce6a6eeb951ac372d98d696c8dc` | **VERIFIED** |
| `backend/results/phase22/phase22_workload_tradeoffs.json` | Workload trade-off matrix | `82a8a664e56e6dede42c01e226716d023d92eb014a2836e3c5a1250b669905ea` | **VERIFIED** |
| `backend/results/phase22/observation_tracker_state.json` | Live observation tracker state | Newly initialized production tracker state | **INITIALIZED** |

---

## 3. Architecture & Telemetry Ingestion Contract

### 3.1 Dual-Scoring Shadow Ingestion Flow

```
Incoming Request (Client / DOT Inspection Workflow)
   │
   ├─► Headers: [X-Traffic-Source: LIVE_OPERATIONAL], [X-Event-ID: evt_uuid]
   │
   ▼
Flask API Endpoints (/api/score, /api/score/batch)
   │
   ├─► Primary Production Scorer (backend/score_bridge_risk.py)
   │     │
   │     ├─► Phase 17 HistGradientBoosting (Baseline)
   │     ├─► Phase 18B Platt Calibrator (Threshold = 0.1940)
   │     │
   │     └─► [IMMEDIATE CLIENT RESPONSE: 100% Phase 17 Output]
   │
   └─► Asynchronous Shadow Execution (backend/shadow_scoring_service.py)
         │ (Isolated try/except block; zero failure propagation)
         │
         ├─► Telemetry Event Validator (backend/live_shadow_monitor.py)
         │     ├─ Validate Event ID (evt_<uuid4>)
         │     ├─ Timestamp Clock Skew Check (< 60s future)
         │     ├─ Timestamp Freshness Check (< 24h stale)
         │     └─ Duplicate Event Ring Buffer (100,000 entries)
         │
         ├─► Shadow Candidate Scorer
         │     ├─ Phase 21B Tuned Model (C10)
         │     └─ Cross-Fitted Platt Calibrator (Threshold = 0.1680)
         │
         ├─► Live Observation Tracker (30-day streak manager)
         │     ├─ Ingest ONLY valid LIVE_OPERATIONAL events
         │     └─ Update observation_tracker_state.json atomically
         │
         └─► Structured Append-Only Telemetry (shadow_telemetry.jsonl)
```

### 3.2 HTTP Request Ingestion Headers

Clients submitting scoring requests can provide the following optional headers:

| Header Name | Type | Allowed Values | Default Value | Description |
|---|---|---|---|---|
| `X-Traffic-Source` | String | `LIVE_OPERATIONAL`, `OFFLINE_TEST_REPLAY`, `SYNTHETIC_TEST` | `LIVE_OPERATIONAL` | Declares the provenance of the request. Non-live requests are recorded in telemetry but strictly excluded from advancing the 30-day observation window. |
| `X-Event-ID` | String | Format: `evt_<uuid4>` or alphanumeric | Auto-generated `evt_<uuid4>` | Unique identifier for request deduplication and distributed tracing. |

### 3.3 Privacy & Data Protection Safeguards

To prevent leaking sensitive infrastructure asset identifiers or operational inspection identities:
- Raw bridge identifiers are pseudonymized using SHA-256 (`rec_<hash[:12]>`).
- Telemetry records log only structural feature vectors, calibrated probabilities, binary flags, execution latency, and validated UTC timestamps.
- No personal inspector information, raw bridge coordinates, or agency credentials are ever logged.

---

## 4. Continuity & Streak Enforcement Rules

The platform enforces strict rules to prevent artificial or fragmentary observation claims:

### 4.1 Calendar Day Definition
- An observation day is defined strictly as **UTC 00:00:00 to 23:59:59**.
- A calendar day is credited as observed if and only if **$\ge 1$ valid `LIVE_OPERATIONAL` record** is successfully evaluated during that UTC day.

### 4.2 Continuity Streak Progression
- **Initiation:** The tracker remains in `NOT_STARTED` status until the very first valid `LIVE_OPERATIONAL` record arrives.
- **Active Streak:** When consecutive days receive traffic, `consecutive_days_elapsed` increments by 1 for each contiguous day, and status becomes `ACTIVE_MONITORING`.
- **Target Completion:** Upon reaching `consecutive_days_elapsed == 30`, status transitions to `COMPLETED_AWAITING_REVIEW`.

### 4.3 Gap Detection & Streak Breaking
- **Streak Break Trigger:** If the tracker encounters a calendar date gap $> 1$ day between observed dates (e.g., traffic observed on day $T$ and next traffic arrives on day $T+2$, skipping day $T+1$):
  1. A gap event is logged in `monitoring_gaps` recording `gap_start_date`, `gap_end_date`, and `gap_days`.
  2. The broken streak information is recorded in `streak_broken_history` (`broken_at_days`, `last_observed_date`, `reset_timestamp_utc`).
  3. `consecutive_days_elapsed` is **immediately reset to 1** (starting fresh from the new traffic date).
  4. Status transitions to `GAP_DETECTED`.

---

## 5. Operational Health Monitoring & SLA Thresholds

The shadow scoring monitor computes live health indicators across rolling operational windows:

### 5.1 Service Level Agreements (SLAs)

| Operational Dimension | Metric | SLA Threshold | Enforcement Action |
|---|---|---|---|
| **Production Availability** | Primary API success rate | $\ge 99.9\%$ | Any shadow failure is silently caught and logged; primary response is never impacted. |
| **Shadow Execution Latency** | Single-record $p_{95}$ latency | $\le 15.0\text{ ms}$ | Monitored in real-time. If rolling $p_{95} > 15.0\text{ ms}$, an alert is raised in health status. |
| **Shadow Reliability** | Shadow scoring failure rate | $\le 0.01\%$ | Failures increment `failure_count`. If $> 0.01\%$, shadow pipeline is flagged for inspection. |
| **Model Agreement** | Prediction agreement rate | Expected $95.0\% - 98.0\%$ | Disagreements are tracked to monitor divergence between Phase 17 and Phase 21B. |

### 5.2 Drift and Distribution Tracking

The platform tracks statistical distribution metrics for both models without requiring ground truth labels:
- **Calibrated Probability Quantiles:** $p_{10}, p_{25}, p_{50}\text{ (median)}, p_{75}, p_{90}, p_{95}$ and Interquartile Range (IQR).
- **Inspection Workload Fraction:** Percentage of incoming records flagged for deck condition decline.
- **Geographic Disparity Tracking:** Flagging rates broken down by state code to detect regional bias or localized distribution shift.

---

## 6. Ground Truth Linking & Biennial Inspection Cycle Protocol

### 6.1 Target Semantics & Outcome-Independence Principle
The target variable is defined as:
$$\text{target\_deterioration} = \begin{cases} 1 & \text{if } \text{DECK}_{2025} < \text{DECK}_{2023} \\ 0 & \text{otherwise} \end{cases}$$

This target measures whether a bridge deck condition rating declines across a two-year routine inspection cycle under the FHWA National Bridge Inventory (NBI) standard. It does **not** predict bridge collapse, catastrophic structural failure, or sudden fracture.

### 6.2 Prohibition of Premature Outcome Metrics
- Live operational traffic has **zero instantaneous ground truth**. A bridge scored today will undergo certified inspection according to its biennial inspection schedule.
- Therefore, calculating precision, recall, false positive rates, or Brier scores from live operational telemetry is mathematically impossible and methodologically forbidden.
- All telemetry and summary reports must explicitly designate outcome-dependent metrics as **`PENDING_VERIFIED_GROUND_TRUTH`**.

### 6.3 Biennial Ground Truth Linking Procedure
1. **Telemetry Preservation:** Every shadow scoring event records its pseudonymized record key (`rec_<hash>`), evaluation timestamp, model probabilities, and feature snapshot in `shadow_telemetry.jsonl`.
2. **NBI Inspection Release Ingestion:** Upon release of the biennial NBI dataset update (e.g., 2025/2026 inspection cycles), bridge records are matched by state and structure key against the logged pseudonymized keys.
3. **Verification & Audit:** Verified inspectors' ratings are joined with the historical shadow predictions to compute true out-of-sample operational precision, recall, and false positive rates.

---

## 7. Emergency Rollback & Incident Response Procedures

### 7.1 Instant Shadow Disablement (Zero Restart Required)
If the shadow scoring service degrades system resources, encounters unhandled exceptions, or if an immediate decommissioning is required:

1. **Environment Variable Switch:**
   Set the environment variable:
   ```bash
   BRIDGE_SHADOW_MODE_ENABLED=false
   ```
2. **Behavior:**
   `backend/shadow_scoring_service.py` immediately bypasses all shadow execution, validation, and disk logging. Calls to `score_record_with_shadow` return the primary Phase 17 result instantaneously without overhead.
3. **Hot Disablement via Configuration:**
   Alternatively, toggle `shadow_enabled: false` via application config without stopping the API service.

### 7.2 Production Cutover Lockout
- Promotion of Phase 21B to primary production status requires:
  1. Completion of 30 consecutive calendar days of verified `LIVE_OPERATIONAL` traffic.
  2. Zero continuity gaps during the 30-day window.
  3. $p_{95}$ latency strictly $\le 15.0\text{ ms}$ and error rate $\le 0.01\%$.
  4. Written authorization from State DOT bridge engineering stakeholders.
  5. Setting `BRIDGE_PRODUCTION_CUTOVER_ENABLED=true` in deployment environment.
- In all other circumstances, `BRIDGE_PRODUCTION_CUTOVER_ENABLED=false` remains enforced by system invariants.

---

## 8. Summary of Active Governance Status

| Governance Dimension | Status | Notes |
|---|---|---|
| **Production Champion** | **Phase 17** | Active for 100% of live operational bridge decisions |
| **Production Cutover Switch** | **LOCKED (`false`)** | Automated or premature cutover is strictly prohibited |
| **Live Observation Window** | **NOT_STARTED** | 0/30 consecutive days elapsed; awaiting live DOT traffic |
| **Outcome Metrics** | **PENDING_VERIFIED_GROUND_TRUTH** | No fabrication of unobserved ground truth labels |
| **SLA Compliance** | **100% COMPLIANT** | $p_{95} \le 15.0\text{ ms}$; zero production service impact |

---

## 9. Operator Onboarding & Daily Operations Manual (Phase 22H)

### 9.1 Infrastructure & Credential Prerequisites
Before live operational traffic can be accepted or credited toward the 30-day observation window, verify the following prerequisites:

| Prerequisite Item | Environment / Configuration | Status |
|---|---|---|
| **Primary Scoring Engine** | [`backend/score_bridge_risk.py`](file:///d:/sem%203/Deep%20Learning/project/backend/score_bridge_risk.py) | **READY (Checksum Verified)** |
| **Shadow Candidate Scorer** | `phase21b_tuned_model.joblib` + calibrator | **READY (Checksum Verified)** |
| **Ingestion Gateway** | [`backend/shadow_ingestion_adapter.py`](file:///d:/sem%203/Deep%20Learning/project/backend/shadow_ingestion_adapter.py) | **DEPLOYED** |
| **DOT Ingestion API Key** | `BRIDGE_INGEST_API_KEY` | **PENDING DOT ALLOCATION** |
| **DOT Test API Key** | `BRIDGE_TEST_API_KEY` | **PENDING DOT ALLOCATION** |
| **Daily Coverage Requirement** | $\ge 1$ (or `BRIDGE_MIN_DAILY_OBSERVATION_RECORDS`) | **CONFIGURED** |
| **Readiness Check Endpoint** | `GET /api/onboarding/readiness` | **ACTIVE** |

### 9.2 Multi-State Readiness Progression
The platform tracks 4 distinct operational lifecycle states:
1. `CONFIGURATION_READY`: Model artifacts, encoders, calibrators, and baseline checksums are loaded and validated.
2. `CONNECTION_VERIFIED`: Ingest endpoints (`/api/score`, `/api/score/batch`, `/api/shadow/status`) are reachable and returning 200 OK.
3. `AUTHENTIC_LIVE_TRAFFIC_CONFIRMED`: Genuine `LIVE_OPERATIONAL` traffic with valid operational credentials has been received (test credentials and replays are segregated).
4. `OBSERVATION_STARTED`: The persistent 30-consecutive-calendar-day tracker has officially commenced following verified live coverage meeting daily thresholds.

### 9.3 Client Onboarding & Ingestion Contract
External DOT bridge inspection systems must configure HTTP clients with the following headers:
```http
POST /api/score HTTP/1.1
Host: api.bridge-maintenance.transportation.gov
Content-Type: application/json
X-API-Key: <SECURE_OPERATIONAL_INGEST_KEY>
X-Traffic-Source: LIVE_OPERATIONAL
X-Event-ID: evt_<uuid4>
```

> [!IMPORTANT]
> If `X-API-Key` matches `BRIDGE_TEST_API_KEY` or starts with `test_`, the ingestion adapter automatically maps the traffic source to `SYNTHETIC_TEST`. Test credentials can NEVER advance the live observation clock.

### 9.4 Daily Evidence Review Protocol (Operator Checklist)
Platform operators must execute the following review daily at **UTC 00:05:00**:
1. **Query Shadow Status:**
   ```bash
   curl -s http://127.0.0.1:5000/api/shadow/status | jq .observation_progress
   ```
2. **Verify Calendar Continuity:**
   Check `observation_tracker_state.json`: confirm `consecutive_days_elapsed` incremented and `monitoring_gaps` has no new entries.
3. **Verify SLA Metrics:**
   Confirm `shadow_p95_latency_ms <= 15.0 ms` and `shadow_failure_rate <= 0.0001` ($0.01\%$).
4. **Inspect Geographic Distribution:**
   Check `geographic_disparities` to ensure no individual state FIPS code is experiencing unexpected scoring divergences.

### 9.5 Alert Handling & Escalation Matrix

| Alert Trigger | Severity | Immediate Action | Escalation Path |
|---|---|---|---|
| **Missing Calendar Day (Gap)** | High | Tracker automatically logs gap and resets streak. Contact DOT data engineering to investigate pipeline disruption. | Lead MLOps Engineer |
| **Latency $p_{95} > 15.0\text{ ms}$** | Medium | Check server CPU/memory load and thread contention. Validate batch sizing. | Backend Infrastructure |
| **Shadow Error Rate $> 0.01\%$** | High | Inspect `shadow_telemetry.jsonl` for `shadow_error`. If candidate errors persist, toggle `BRIDGE_SHADOW_MODE_ENABLED=false`. | ML Modeling Team |
| **Primary Scorer Error** | Critical | Primary Phase 17 failure affects DOT users. Roll back deployment immediately. | Incident Commander |

### 9.6 Safe Emergency Shutdown
To instantly disable shadow scoring without downtime:
```bash
# Set environment variable:
export BRIDGE_SHADOW_MODE_ENABLED=false
# The adapter immediately bypasses candidate evaluation and returns Phase 17 results in < 12ms.
```

---

## 10. External Deployment Handoff & Operational Acceptance Runbook (Phase 22J)

### 10.1 Technical Deployment Architecture & Request Flow
The platform implements a guarded, reverse-proxy shadow architecture to ensure that candidate model evaluation cannot fail or delay production scoring:

```
[ State DOT BMS Client (e.g. AASHTOWare Pontis) ]
                    │
   HTTPS / TLS 1.3  │ (X-API-Key: <BRIDGE_INGEST_API_KEY>)
                    │ (X-Traffic-Source: LIVE_OPERATIONAL)
                    ▼
[ Reverse Proxy / Ingress Controller (NGINX / Envoy / Cloud LB) ]
                    │
                    ▼
[ ShadowIngestionAdapter (backend/shadow_ingestion_adapter.py) ]
    │
    ├─► 1. Authentication & Provenance Classification:
    │     ├─ Operational DOT Key ──► LIVE_OPERATIONAL (Eligible for 30-day streak)
    │     ├─ Test Key (test_*)   ──► SYNTHETIC_TEST (Strictly excluded from streak)
    │     └─ Missing/Invalid     ──► 401 Unauthorized (Fail Closed)
    │
    ├─► 2. Primary Production Scorer (Phase 17 Champion):
    │     ├─ Validates canonical 26-feature schema
    │     ├─ Evaluates HistGradientBoosting + Phase 18B Platt Calibrator
    │     └─ ALWAYS returns authoritative production decision to client
    │
    └─► 3. Guarded Shadow Evaluation (Phase 21B Candidate):
          ├─ Timeout enforcement (50ms execution budget)
          ├─ Telemetry Logger & Durable Event Cache (event_id_cache.txt)
          ├─ Live Observation Tracker (30-consecutive-day UTC streak)
          └─ Failure Isolation: exceptions caught; zero impact on primary response
```

### 10.2 Role & Responsibility Matrix

| Role | Organization | Responsibilities |
|---|---|---|
| **DOT IT Security** | State DOT Information Security | Provision/rotate `BRIDGE_INGEST_API_KEY` via State KMS/Vault; audit TLS certificates; review API endpoint authorization policies; verify zero-secret exposure. |
| **DOT Network Administration** | State DOT Infrastructure | Configure reverse-proxy routing, ingress firewalls, DNS records, MTU timeouts; whitelist BridgeIntel scoring endpoints. |
| **DOT Bridge System Owners (BMS)** | State DOT Asset Management | Integrate agency bridge management software (AASHTOWare/Pontis) with `/api/score`; supply 26-feature NBI records; attach `X-Traffic-Source: LIVE_OPERATIONAL`. |
| **FHWA / DOT Inspection Data Owners** | Federal Highway Admin & Inspection Branch | Conduct and certify biennial routine physical bridge deck inspections (0–9 scale); provide verified ground-truth ratings ($\text{DECK}_{2025} < \text{DECK}_{2023}$) for offline linkage. |
| **Chief Bridge Engineer** | State DOT Executive Engineering | Review completed 30-day continuous shadow observation reports; audit incremental inspection workload; issue written cutover authorization. |

### 10.3 Secure Credential Management & Secret Redaction
1. **Zero Secret Hardcoding:** API keys and credentials must never be committed to source code or configuration files.
2. **Environment Variable Injection:** Credentials must be injected at runtime via enterprise secret managers:
   ```bash
   export BRIDGE_INGEST_API_KEY="<DOT_PROVISIONED_API_KEY>"
   export BRIDGE_REQUIRE_AUTH="true"
   ```
3. **Automated Secret Redaction:** String logs, error messages, and telemetry entries are sanitized via `redact_sensitive_credentials()` in `shadow_ingestion_adapter.py`. Tokens matching `Bearer <token>`, `x-api-key: <key>`, or known secrets are masked to `[REDACTED_KEY]`.
4. **Key Rotation:** Keys may be rotated dynamically with zero downtime by updating environment variables and performing a rolling worker restart.

### 10.4 Network, Firewall, TLS, DNS & Health Verification Protocols
1. **TLS / Network Verification:**
   ```bash
   # Verify TLS 1.3 handshake and endpoint reachability
   curl -vk https://<DOT_ASSIGNED_DOMAIN>/api/health
   ```
2. **Readiness State Inspection:**
   ```bash
   # Inspect multi-stage operational readiness status
   curl -s https://<DOT_ASSIGNED_DOMAIN>/api/onboarding/readiness | jq .
   ```
3. **Daily Evidence Query:**
   ```bash
   # Query privacy-safe daily evidence record for a specific UTC date
   curl -s "https://<DOT_ASSIGNED_DOMAIN>/api/onboarding/daily-evidence?date=$(date -u +%Y-%m-%d)" | jq .
   ```

### 10.5 Deployment Preflight Checklist Summary

| Checklist Item | Scope & Description | Status | Evidence |
|---|---|---|---|
| **CHK-01: Baseline Code Immutability** | `backend/score_bridge_risk.py` SHA-256 hash | **PASS** | Verified hash `b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61` |
| **CHK-02: Frozen Phase 17 Artifacts** | All 11 files in `backend/results/phase17/` | **PASS** | Verified hashes match `serialization_manifest.json` |
| **CHK-03: Cutover Safety Lock** | `BRIDGE_PRODUCTION_CUTOVER_ENABLED=false` | **PASS** | Cutover switch disabled in code, config, and runtime |
| **CHK-04: Test Suite with Escalation** | Full 154-test backend test suite | **PASS** | 154/154 pass under `-W error::UserWarning` |
| **CHK-05: Frontend Build & Lint** | Compilation & linting | **PASS** | 0 lint errors; Vite production bundle built |
| **CHK-06: Operational Key Provisioning** | State DOT secret manager provisioning | **BLOCKED** | Pending State DOT IT Security action |
| **CHK-07: Ingress Network Routing** | Reverse proxy, DNS, TLS 1.3 configuration | **BLOCKED** | Pending State DOT Network Admin action |
| **CHK-08: Firewall Whitelisting** | Outbound traffic from BMS to platform | **BLOCKED** | Pending State DOT Network Admin action |
| **CHK-09: Live Operational Traffic Feed** | BMS sends `X-Traffic-Source: LIVE_OPERATIONAL` | **NOT VERIFIED** | Awaiting State DOT live stream |
| **CHK-10: Daily Unique Coverage** | $\ge 1$ unique bridge records per UTC calendar day | **NOT VERIFIED** | Awaiting State DOT live stream |
| **CHK-11: 30-Day Consecutive Window** | 30 continuous calendar days without gap or reset | **NOT VERIFIED** | Clock starts upon first qualifying live event |
| **CHK-12: Biennial Inspection Release** | FHWA biennial inspection dataset | **BLOCKED** | Awaiting FHWA 2025/2026 data publication |
| **CHK-13: Statutory Cutover Sign-Off** | Chief Bridge Engineer written authorization | **BLOCKED** | Awaiting completion of 30-day observation window |

### 10.6 Incident Response & Emergency Containment
1. **Level 1 Containment (Instant Shadow Bypass):**
   ```bash
   export BRIDGE_SHADOW_MODE_ENABLED="false"
   ```
   Primary Phase 17 scoring continues without interruption. Shadow evaluation, candidate inference, and telemetry logging are bypassed entirely.
2. **Level 2 Containment (Ingress Traffic Rate Limiting):**
   Configure reverse proxy to reject abusive clients or unauthenticated requests before hitting Python application processes.
3. **Observation Streak Recovery:**
   If live traffic is interrupted for 1 or more UTC calendar days, the observation streak automatically resets to 1 upon resumption. Bypassing or suppressing streak resets is prohibited by governance directives.

### 10.7 Operational Acceptance & Cutover Sign-Off Protocol
Production cutover is **strictly prohibited** until all of the following conditions are met:
1. 30 consecutive calendar days of verified `LIVE_OPERATIONAL` traffic logged with zero gap resets.
2. Candidate shadow error rate $\le 0.0001$ ($0.01\%$) and latency $p_{95} \le 15.0\text{ ms}$.
3. Offline linkage to certified biennial NBI inspection ratings confirming candidate precision and recall gains.
4. Formal written cutover authorization signed by the Chief Bridge Engineer and archived in `docs/cutover_authorizations/`.

### 10.8 Incident Escalation & Operational Contact Directory

*(Template: Placeholders to be populated by the State DOT during operational onboarding)*

| Role Title | Contact Name | Emergency Phone | Secure Email | Secondary / Escalation |
|---|---|---|---|---|
| **Platform Engineering Lead** | `[OPERATOR_ENGINEERING_LEAD]` | `+1 (XXX) XXX-XXXX` | `eng-lead@agency.dot.gov` | `[DEPUTY_ENGINEERING_LEAD]` |
| **DOT Security Operations (SOC)** | `[DOT_SOC_DUTY_OFFICER]` | `+1 (XXX) XXX-XXXX` | `soc@agency.dot.gov` | `[CHIEF_INFORMATION_SECURITY_OFFICER]` |
| **DOT Network Operations (NOC)** | `[DOT_NOC_DUTY_ENGINEER]` | `+1 (XXX) XXX-XXXX` | `noc@agency.dot.gov` | `[NETWORK_INFRASTRUCTURE_MANAGER]` |
| **BMS System Administrator** | `[BMS_SYSTEM_ADMINISTRATOR]` | `+1 (XXX) XXX-XXXX` | `bms-admin@agency.dot.gov` | `[BRIDGE_MANAGEMENT_SUPERVISOR]` |
| **Chief Bridge Engineer** | `[CHIEF_BRIDGE_ENGINEER_NAME]` | `+1 (XXX) XXX-XXXX` | `chief-bridge-eng@agency.dot.gov` | `[STATE_STRUCTURES_DIRECTOR]` |


