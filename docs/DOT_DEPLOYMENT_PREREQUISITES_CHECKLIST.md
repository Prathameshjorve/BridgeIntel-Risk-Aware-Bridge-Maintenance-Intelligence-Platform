# State DOT External Deployment Prerequisites & Operational Handoff Checklist

**Platform:** Risk-Aware Bridge Maintenance Intelligence Platform (BridgeIntel)  
**System Role:** Explainable decision-support platform for prioritizing bridge maintenance under limited budgets  
**Document Purpose:** Auditable handoff specification and preflight verification checklist for State Department of Transportation (DOT) infrastructure and engineering teams.  
**Platform Phase:** Phase 22J – External Deployment Handoff & Operational Acceptance  
**Production Champion:** Phase 17 (`backend/score_bridge_risk.py`)  
**Production Cutover Status:** **STRICTLY LOCKED (`BRIDGE_PRODUCTION_CUTOVER_ENABLED=false`)**  

---

## 1. Stakeholder Role & Responsibility Matrix

To maintain strict operational safety, data governance, and cryptographic auditability, external deployment responsibilities are partitioned across five formal stakeholder roles. No role may assume authority delegated to another:

| Stakeholder Role | Organizational Entity | Primary Handoff Responsibilities |
|---|---|---|
| **DOT IT Security Team** | State DOT Information Security Office | Provision, rotate, and manage `BRIDGE_INGEST_API_KEY` in state KMS/Vault; audit ingress TLS certificates; review API endpoint authorization policies; verify zero-secret exposure in system logs. |
| **DOT Network Administration** | State DOT Enterprise Infrastructure | Configure reverse-proxy routing, ingress firewalls, DNS records, and MTU/keep-alive timeouts (50ms budget); whitelist BridgeIntel scoring endpoints. |
| **DOT Bridge System Owners (BMS)** | State DOT Maintenance & Asset Engineering | Integrate agency bridge management software (e.g., AASHTOWare Bridge Management / Pontis) with `/api/score` and `/api/score/batch`; supply the mandatory 26-feature NBI schema; attach `X-Traffic-Source: LIVE_OPERATIONAL` headers. |
| **FHWA / DOT Inspection Data Owners** | Federal Highway Admin & DOT Bridge Inspection Branch | Conduct and certify biennial routine physical bridge deck inspections on the 0–9 NBI scale; publish validated evaluation datasets ($\text{DECK}_{2025} < \text{DECK}_{2023}$) for offline shadow calibration verification. |
| **Chief Bridge Engineer (or Approver)** | State DOT Chief Bridge Engineer / Delegated Statutory Authority | Review completed 30-day continuous shadow observation reports; audit incremental inspection workload and precision; issue written cutover authorization prior to any production promotion. |

---

## 2. Technical Deployment Architecture & Request Flow

The scoring gateway uses an isolated shadow-first architecture designed to guarantee that experimental or shadow candidate evaluation cannot delay, alter, or crash primary Phase 17 production scoring:

```
[ State DOT Bridge Management System (BMS) / Client Application ]
                                │
               HTTPS / TLS 1.3  │ (X-API-Key: <BRIDGE_INGEST_API_KEY>)
                                │ (X-Traffic-Source: LIVE_OPERATIONAL)
                                ▼
         [ Reverse Proxy / API Gateway (NGINX / Envoy / Cloud LB) ]
                                │
                                ▼
  [ Shadow Ingestion Gateway: backend/shadow_ingestion_adapter.py ]
         │
         ├──► 1. Authenticate Request & Classify Provenance:
         │      ├─ Valid DOT Operational Key ──► Authorized Operational Client (LIVE_OPERATIONAL)
         │      ├─ Test Key (test_*)          ──► Remapped to SYNTHETIC_TEST (Strict Clock Isolation)
         │      └─ Missing / Invalid Key     ──► 401 Unauthorized (Fail Closed)
         │
         ├──► 2. Primary Production Scorer (Phase 17 Champion):
         │      ├─ Validates 26-feature canonical schema
         │      ├─ Evaluates HistGradientBoosting + Phase 18B Platt Calibrator
         │      └─ ALWAYS returns authoritative production decision to caller
         │
         └──► 3. Guarded Shadow Evaluation (Phase 21B Candidate):
                ├─ Non-blocking / isolated execution (50ms timeout)
                ├─ Telemetry Validator & Durable Idempotency Cache (event_id_cache.txt)
                ├─ Live Observation Tracker (30-consecutive-day UTC clock; gap reset logic)
                └─ Failure Isolation: exceptions caught; zero impact on production response
```

---

## 3. Operational Secret Provisioning Protocol

In compliance with Federal Information Security Modernization Act (FISMA) and state government cybersecurity standards:

1. **Zero Hardcoded Credentials:** Real API keys, tokens, and database passwords must **never** be committed to source control, embedded in unit tests, or printed in terminal logs.
2. **Environment Variable Injection:** Operational secrets must be injected at runtime into the application container or host process environment using an enterprise secrets manager (e.g., AWS Secrets Manager, Azure Key Vault, HashiCorp Vault):
   ```bash
   export BRIDGE_INGEST_API_KEY="<DOT_PROVISIONED_CRYPTOGRAPHIC_SECRET_KEY>"
   export BRIDGE_REQUIRE_AUTH="true"
   ```
3. **Automated Secret Redaction:** All application loggers route output through `redact_sensitive_credentials()` in [`backend/shadow_ingestion_adapter.py`](file:///d:/sem%203/Deep%20Learning/project/backend/shadow_ingestion_adapter.py). Strings matching Authorization headers, Bearer tokens, or API keys are automatically masked to `[REDACTED_KEY]`.
4. **Key Rotation Policy:** State DOT IT Security may rotate `BRIDGE_INGEST_API_KEY` with zero downtime by performing a rolling process restart or updating container environment variables.

---

## 4. Preflight Deployment Verification Checklist

Each prerequisite item is audited with an explicit status:
- **`PASS`**: Code, configuration, or local artifact verified in the repository.
- **`BLOCKED`**: Action or credential pending external State DOT provisioning.
- **`NOT VERIFIED`**: Requires live network ingress and external traffic from state DOT BMS.

| Checklist Item | Scope & Description | Required Verification Command / Evidence | Status | Responsible Stakeholder |
|---|---|---|---|---|
| **CHK-01: Baseline Code Immutability** | `backend/score_bridge_risk.py` SHA-256 hash must match `b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61` byte-for-byte. | `python -c "import hashlib; assert hashlib.sha256(open('backend/score_bridge_risk.py','rb').read()).hexdigest() == 'b49055f0a2b9fbcb6afa046853730f83fb8c508ea161a540e0b48f2db2c3dc61'"` | **`PASS`** | BridgeIntel Engineering |
| **CHK-02: Frozen Phase 17 Artifacts** | All 11 files under `backend/results/phase17/` must match `serialization_manifest.json` checksums. | `python -m unittest backend/tests/test_phase22j_handoff_acceptance.py` (Test 1) | **`PASS`** | BridgeIntel Engineering |
| **CHK-03: Cutover Safety Lock** | `BRIDGE_PRODUCTION_CUTOVER_ENABLED=false` must remain locked at runtime; Phase 17 remains sole production champion. | Inspect `backend/shadow_scoring_service.py` line 93; `GET /api/onboarding/readiness` returns `"cutover_switch_enabled": false`. | **`PASS`** | BridgeIntel Engineering |
| **CHK-04: Full Test Suite with Escalation** | Full 154-test backend test suite must pass with zero failures and zero warnings under `-W error::UserWarning`. | `python -W error::UserWarning -m unittest discover -s backend/tests` (154/154 pass) | **`PASS`** | BridgeIntel Engineering |
| **CHK-05: Frontend Build & Lint** | Frontend must compile cleanly; production bundle generated in `frontend/dist/`. | `npm run lint` (0 errors); `npm run build` (Clean build in `frontend/`) | **`PASS`** | BridgeIntel Engineering |
| **CHK-06: Production API Key Provisioning** | State DOT IT Security must generate and assign an operational API key (`BRIDGE_INGEST_API_KEY`). | Secure transmission from DOT KMS/Vault into deployment host environment variable. | **`BLOCKED`** | DOT IT Security |
| **CHK-07: Enterprise Ingress Routing & TLS** | State DOT network administrators must route HTTPS traffic to the BridgeIntel server and terminate TLS 1.3. | `curl -vk https://<DOT_ASSIGNED_DOMAIN>/api/health` returns HTTP 200 with valid TLS cert. | **`BLOCKED`** | DOT Network Admin |
| **CHK-08: Firewall Whitelisting** | Client DOT network firewalls must permit outbound HTTPS requests to `/api/score` and `/api/score/batch`. | Network connectivity test from DOT bridge management host to scoring gateway. | **`BLOCKED`** | DOT Network Admin |
| **CHK-09: Live Operational Traffic Feed** | State DOT BMS must initiate bridge scoring requests with `X-Traffic-Source: LIVE_OPERATIONAL`. | `GET /api/onboarding/readiness` transitions to `AUTHENTIC_LIVE_TRAFFIC_CONFIRMED: true`. | **`NOT VERIFIED`** | DOT Bridge System Owners |
| **CHK-10: Daily Unique Coverage Satisfaction** | Live operational traffic must meet the minimum daily unique bridge coverage threshold ($\ge 1$, default). | `GET /api/onboarding/readiness` transitions to `OBSERVATION_STARTED: true`. | **`NOT VERIFIED`** | DOT Bridge System Owners |
| **CHK-11: 30-Day Consecutive Observation** | 30 continuous calendar days of live traffic without missing UTC days or unhandled crashes. | `LiveObservationTracker` registers `consecutive_days_elapsed: 30` with 0 gaps. | **`NOT VERIFIED`** | Platform Operator |
| **CHK-12: Biennial Inspection Ground Truth** | Certified routine biennial inspection ratings published by FHWA/DOT for evaluation linkage. | Offline ingestion of subsequent NBI release joining `DECK_2025` and `DECK_2023`. | **`BLOCKED`** | FHWA / DOT Inspection Branch |
| **CHK-13: Statutory Cutover Sign-Off** | Written authorization from the Chief Bridge Engineer approving candidate promotion. | Formal sign-off memo executed and filed in `docs/cutover_authorizations/`. | **`BLOCKED`** | Chief Bridge Engineer |

---

## 5. Rollback & Emergency Incident Procedures

If operational instability, network degradation, or anomalous candidate behavior occurs during the shadow observation period, operators must execute the following zero-downtime containment procedures:

### 5.1 Immediate Shadow Execution Deactivation (Level 1 Containment)
To immediately bypass shadow candidate scoring without restarting the service:
```bash
# Set environment variable and reload, or update configuration file
export BRIDGE_SHADOW_MODE_ENABLED="false"
```
- **Operational Effect:** All requests to `/api/score` and `/api/score/batch` continue to execute primary Phase 17 scoring without interruption. Shadow evaluation, candidate model inference, and telemetry logging are bypassed entirely.
- **Production Impact:** **Zero.** Phase 17 responses continue to return in ~10–12 ms with 100% availability.

### 5.2 Emergency Ingress Isolation (Level 2 Containment)
If external requests are malformed or flooding the gateway:
- Configure reverse proxy (NGINX/Envoy) to return HTTP 429 Too Many Requests or reject requests missing valid `X-API-Key` headers before reaching Python application workers.

### 5.3 Observation Continuity & Streak Reset Policy
- If shadow mode is disabled or traffic is interrupted for 1 or more UTC calendar days, the continuous observation streak breaks automatically.
- Upon re-enabling shadow mode and restoring live traffic, `LiveObservationTracker` logs a `STREAK_RESET_GAP_DETECTED` event and resets `consecutive_days_elapsed` to 1.
- Governance mandates forbid suppressing or circumventing streak resets.

---

## 6. Daily Evidence Record & Verification Contract

During the 30-day observation window, platform operators must capture an auditable daily evidence record via:
```http
GET /api/onboarding/daily-evidence?date=YYYY-MM-DD
```

### Approved Privacy-Safe Evidence Record Schema:
```json
{
  "evidence_record_version": "1.0-phase22j",
  "generated_at_utc": "2026-10-16T00:05:00.000000+00:00",
  "observation_calendar_date_utc": "2026-10-15",
  "coverage_evaluation": {
    "qualifying_live_records": 150,
    "unique_bridges_observed": 120,
    "min_daily_coverage_required": 1,
    "daily_coverage_threshold_met": true
  },
  "provenance_and_auth_status": {
    "operational_auth_configured": true,
    "operational_traffic_confirmed": true,
    "verified_operational_clients_count": 1,
    "total_live_records_all_time": 150,
    "total_synthetic_records_all_time": 0,
    "total_replay_records_all_time": 0
  },
  "observation_window_progress": {
    "consecutive_days_elapsed": 1,
    "target_consecutive_days": 30,
    "observation_status": "IN_PROGRESS",
    "monitoring_gaps_count": 0,
    "streak_resets_count": 0
  },
  "service_health_summary": {
    "shadow_mode_enabled": true,
    "active_production_champion": "Phase 17",
    "production_cutover_locked": true,
    "health_grade": "HEALTHY"
  },
  "state_persistence_integrity": {
    "primary_state_file_exists": true,
    "backup_state_file_exists": true,
    "durable_event_cache_active": true
  },
  "outcome_dependent_metrics": {
    "status": "PENDING_VERIFIED_GROUND_TRUTH",
    "precision": "PENDING_VERIFIED_GROUND_TRUTH",
    "recall": "PENDING_VERIFIED_GROUND_TRUTH",
    "false_positive_rate": "PENDING_VERIFIED_GROUND_TRUTH",
    "disclaimer": "Outcome metrics require certified biennial physical inspection ratings (DECK_2025 < DECK_2023)."
  }
}
```

---

## 7. Operational Contact & Incident Escalation Directory

*(Template: Operational placeholders to be populated with agency contacts prior to production traffic cutover)*

| Role Title | Primary Contact Name | Phone / Emergency Hotline | Secure Email / PGP Fingerprint | Secondary / Escalation Contact |
|---|---|---|---|---|
| **Platform Lead Engineer** | `[OPERATOR_ENGINEERING_LEAD]` | `+1 (XXX) XXX-XXXX` | `eng-lead@agency.dot.gov` | `[DEPUTY_ENGINEERING_LEAD]` |
| **DOT Security Operations (SOC)** | `[DOT_SOC_DUTY_OFFICER]` | `+1 (XXX) XXX-XXXX` | `soc@agency.dot.gov` | `[CHIEF_INFORMATION_SECURITY_OFFICER]` |
| **DOT Network Operations (NOC)** | `[DOT_NOC_DUTY_ENGINEER]` | `+1 (XXX) XXX-XXXX` | `noc@agency.dot.gov` | `[NETWORK_INFRASTRUCTURE_MANAGER]` |
| **BMS Application Admin** | `[BMS_SYSTEM_ADMINISTRATOR]` | `+1 (XXX) XXX-XXXX` | `bms-admin@agency.dot.gov` | `[BRIDGE_MANAGEMENT_SUPERVISOR]` |
| **Chief Bridge Engineer** | `[CHIEF_BRIDGE_ENGINEER_NAME]` | `+1 (XXX) XXX-XXXX` | `chief-bridge-eng@agency.dot.gov` | `[STATE_STRUCTURES_DIRECTOR]` |

---

## 8. Handoff Acceptance Sign-Off Sheet

*(Formal sign-off required before advancing to live observation cutover)*

- **Technical Readiness Status:** `READY` (Verified across 154 automated unit tests, 0 warnings, clean frontend build).
- **Operational Infrastructure Status:** `BLOCKED` (Awaiting DOT credentials and network routing).
- **Production Cutover Switch:** `LOCKED` (`BRIDGE_PRODUCTION_CUTOVER_ENABLED=false`).

```
[  ] State DOT IT Security: Credentials Provisioned & Tested
     Signature: ___________________________    Date: _______________

[  ] State DOT Network Admin: Routing, TLS & Firewall Verified
     Signature: ___________________________    Date: _______________

[  ] State DOT BMS System Owner: 26-Feature Live Feed Confirmed
     Signature: ___________________________    Date: _______________

[  ] Chief Bridge Engineer: 30-Day Observation Initiated
     Signature: ___________________________    Date: _______________
```
