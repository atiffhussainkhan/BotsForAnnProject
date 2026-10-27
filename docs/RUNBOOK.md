# SRE Operational Runbook — Ann Reveals AI Manager (`ARAIM` v4.0)

**Maintainer:** Agent Echo (Agent 5 — SRE & Platform Operations)  
**Availability SLO:** ≥ 99.5% Monthly Uptime (`NFR-01`)  
**Hard Monthly Cost Ceiling:** £30.00 Total (£5.00 AI Sub-Cap + £7.00 Hosting) (`FR-050`, `NFR-07`)

---

## 1. Golden Signals & Service Level Objectives (SLOs)

| Metric | Target SLO | Warning Threshold | Critical Alert / Automated Action |
|---|---|---|---|
| **Service Availability** | `>= 99.5%` | `< 99.7%` (rolling 24h) | Restart container via healthcheck (`/api/health`); notify owner |
| **Webhook Ingestion Latency** | `p50 < 80ms`, `p95 < 250ms` | `p95 > 400ms` | Shed non-urgent background reconciliation; return 200 after queue write |
| **Duplicate Outbound Replies** | `0` (Strict Zero Tolerance) | `>= 1` | Immediate universal `EMERGENCY STOP` + lock outbound queue |
| **False Self-Purchase Claims** | `0` (Strict Zero Tolerance) | `>= 1` | Force all content packages to human sign-off |
| **Monthly Total Cloud + AI Spend** | `<= £16.00` routine / `<= £30.00` hard cap | `>= £24.00` (80% warning) | At `£30.00` total or `£5.00` AI sub-cap: auto-downgrade to `DRAFT` + deterministic templates |

---

## 2. Standard Incident Response Playbooks

### Playbook A: Universal Emergency Stop (`EMERGENCY STOP`)
**When to use:** Unexpected comment replies, suspected account compromise, or platform policy turbulence.
1. **PWA Action (Zero-CLI):** Tap the red **`EMERGENCY STOP`** button in the top bar of any screen.
2. **Automated System Effect (`KillSwitchController.trigger_emergency_stop`):**
   - Sets global `emergency_stop_active = True`.
   - Transitions both `tiktok` and `instagram` to `OFF`.
   - Drains 100% of queued outbound jobs into `DRAFT` within `<10ms`.
   - Records an immutable audit entry with timestamp and reason.
3. **Recovery:** Once verified safe, tap **"Release Emergency Stop"** on the Home screen. Platforms return safely to `DRAFT` mode (never directly back to `SAFE_AUTO` without explicit re-selection).

### Playbook B: OAuth `401 Unauthorized` / `403 Forbidden` / Scope Revocation
**Automated System Behavior (`NFR-10`):**
- `HealthAndDrillMonitor` and `KillSwitchController` automatically catch `401`/`403`, downgrade the affected platform to `PAUSED_BY_SYSTEM`, convert queued items to `DRAFT`, and set the status badge to **`Needs reconnect`**.
- **Resolution:** Open PWA -> **Settings & Connections** -> Tap **"Reconnect Instagram"** or **"Reconnect TikTok"** -> Complete official OAuth PKCE flow.

### Playbook C: Rate-Limit Spike (`HTTP 429`) or Upstream `5xx`
**Automated System Behavior (`NFR-02`, `NFR-03`):**
- Honors `Retry-After` header and applies jittered exponential backoff (`30s -> 60s -> 120s`).
- If `429` count exceeds threshold (5 consecutive), circuit breaker trips to `PAUSED_BY_SYSTEM` (`DRAFT` mode) for cooldown.
- If a request times out mid-flight, the comment is marked `RECONCILE_PENDING` so the worker checks existing replies on the post before ever attempting a resend.

### Playbook D: Monthly Budget Ceiling Reached (`£5.00` AI or `£30.00` Total)
**Automated System Behavior (`FR-050`, `NFR-07`):**
- `BudgetGuard` blocks paid LLM calls immediately.
- System switches to **Deterministic Seed Template Fallback** (1,000+ warm UK-English templates) and downgrades outbound mode to `DRAFT`.
- Comment ingestion, receipt vault, and compliance checks continue working at £0 marginal AI cost.

---

## 3. Backup, Verification & Disaster Recovery Procedures

### 3.1 Automated & On-Demand Encrypted Backup
Run from project root (also triggered automatically every 24h by the background scheduler):
```bash
python3 scripts/backup.py --source-dir ./data --output-dir ./backups
```
What this does:
1. Serializes database state, redacted receipt vault metadata, and configuration.
2. Computes SHA-256 checksums for every record in a signed manifest.
3. Encrypts the entire snapshot using `EnvelopeEncryptor` (`ARAIM-ENC-V1`) and writes a `.araim.bak` bundle.

### 3.2 Point-in-Time Restore with Integrity Verification
```bash
python3 scripts/restore.py --backup-file ./backups/latest.araim.bak --target-dir ./data_restored
```
What this does:
1. Verifies the outer HMAC-SHA256 authentication tag in constant time.
2. Decrypts the snapshot and verifies every file's SHA-256 hash against the manifest.
3. Atomically restores the state or aborts if any byte was corrupted.

---

## 4. Secret Rotation Procedure (`FR-044`)
1. Generate a new master encryption key (`ARAIM_MASTER_KEY_V2`).
2. Register the new key in `EnvelopeEncryptor.rotate_key(new_key_id="v2", new_master_key=...)`.
3. Re-seal stored OAuth tokens and receipt metadata envelopes; verify 100% readback check.
4. Remove the retired key from `.env` / cloud secret manager and restart service.
