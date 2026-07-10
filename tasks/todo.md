# TA-MQTT — Project Tasks

**Current release:** `v2.4.0` (2026-07-10)  
**Audit P1–P3:** branching policy, prerelease retention, local hygiene, TLS UI, `app.manifest` metadata — **done**.

---

## Remaining work (prioritized)

### P0 — TLS/mTLS validation (UI + runtime)

Prerequisite: enable **Configuration → Security (advanced) → Allow insecure TLS** for
lab tests that use `skip_verify` (not for production).

- [ ] **Plain MQTT smoke** — broker anonymous on port 1883, topic `#`, search `index=main sourcetype="mqtt:message"`
- [ ] **TLS + skip_verify** — Mosquitto or local broker on 8883, self-signed cert, `use_tls` + `skip_verify` via UI
- [ ] **TLS + custom CA** — paste broker CA PEM in **CA Certificate** field, `skip_verify` off
- [ ] **mTLS** — client cert + key PEM in UI; confirm connect and ingest
- [ ] **Temp-file hygiene** — after reconnect/stop, no stale `client_cert` / `client_key` temp files under `/tmp` (see `tasks/lessons.md` L-003)
- [ ] Update `docs/test-evidence-mqtt-tls-mtls.md` with v2.4.0 UI evidence (screenshots or command log)

### P1 — Configuration UI gaps

- [ ] Re-enable hidden **HEC advanced** input fields in `globalConfig.json` when ready (`hec_url`, `hec_token`, `hec_verify_tls`, batch tuning, etc.) — currently `display: false`
- [ ] Document operator guidance for when to use per-input HEC overrides vs defaults
- [ ] Move `app.manifest` `developmentStatus` from **Beta** → **Production** after P0 TLS validation and one full Docker lab cycle on `v2.4.0`

### P2 — Performance & load tooling

- [ ] Review queue backpressure under high-throughput topics (configurable queue size already implemented)
- [ ] JMeter: match Python `tools/mqtt_load_test.py` coverage for QoS, auth, TLS, mTLS
- [ ] Decide whether to run JMeter scenarios in CI (separate workflow) or keep manual/off-pipeline
- [ ] Remove `tools/mqtt_load_test.py` only after documented parity and contributor usability

### P3 — Production & distribution

- [ ] Splunk saved search / alert: `index=_internal sourcetype=splunkd ERROR ta-mqtt`
- [ ] Optional: `props.conf` / `INDEXED_EXTRACTIONS` for JSON payload sub-fields
- [ ] Splunkbase publication (optional) — privacy policy URL, support contact, package checklist
- [ ] Consider `check_for_updates = true` in `app.conf` once Splunkbase or release feed exists

### P4 — Repository process

- [ ] Route feature work through **`develop` → PR → `main`** per `docs/branching-policy.md` (stop admin-bypass direct pushes except hotfixes)
- [ ] Back-merge `main` into `develop` after each stable tag
- [ ] Phase 4 TLS lab: refresh `.splunk-persist/TA-MQTT-local/` only when needed; keep out of git

---

## Completed phases (archive)

### Phase 1 — Initial scaffold ✅

- [x] globalConfig.json — Broker Connections + MQTT Topic Subscriptions
- [x] Modular input, REST handlers, conf files, `additional_packaging.py`, build deps

### Phase 2 — Build & install (local checklist)

Use `docs/setup-and-build.md` — steps below are the standard new-developer path:

- [x] Documented venv + `ucc-gen build` + Docker Compose mount of `output/TA-MQTT/`
- [ ] Onboarding: run full checklist once on a clean machine (optional verification)

### Phase 3 — First broker test

Covered by **P0 — Plain MQTT smoke** above.

### Phase 3b — Broker TLS/mTLS UI ✅ (v2.4.0)

- [x] TLS/mTLS fields visible in Configuration
- [x] **Allow insecure TLS** on Security tab
- [x] TLS column on broker table
- [x] Operator docs updated

### Phase 6 — JMeter migration (partial) ✅

- [x] Repo-local JMeter assets, sustained-load plans, TLS/mTLS publisher templates
- [x] Reconcile JMeter publish counts with TA runtime summaries
- Remaining items → **P2** above

---

## Reference

- Branching: `docs/branching-policy.md`
- Prereleases: `docs/prereleases.md`
- TLS test plan: `docs/test-plan-mqtt-tls-mtls.md`
- Lessons: `tasks/lessons.md`
