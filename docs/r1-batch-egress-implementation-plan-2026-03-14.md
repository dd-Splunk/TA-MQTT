# R1 Implementation Plan — Optional Batch Egress Mode

Date: 2026-03-14  
Branch: `feature/r1-batch-egress-planning`

## Goal

Add an optional per-input batch mode that sends events in batches to Splunk HEC, while preserving the current modular-input single-event path for backward compatibility.

## Scope (R1 only)

In scope:

- Add a per-input `batch_mode` selector for MQTT inputs.
- Implement HEC batch sender with size/time-based flush.
- Add retries/backoff and failure telemetry for batch mode.
- Preserve existing event envelope and stanza-driven metadata semantics.

Out of scope:

- Rewriting payload schema.
- Multi-writer parallel egress.
- Infra/AWS benchmark orchestration changes.

## Proposed Target Behavior

Default behavior remains unchanged:

- `batch_mode=0` (current path, `ew.write_event` per event)

New optional behavior:

- `batch_mode=1`
- MQTT callback still enqueues quickly.
- Writer loop aggregates events and flushes to HEC when any threshold is met:
  - `hec_batch_max_events`
  - `hec_batch_max_bytes`
  - `hec_flush_interval_ms`

## Configuration Design

### Input-level fields (UCC `inputs > mqtt_subscriber`)

Add fields to `globalConfig.json` service entity:

- `batch_mode` (singleSelect): `0` = modular-input single-event writer, `1` = HEC batch writer
- `hec_endpoint` (text): default `https://localhost:8088/services/collector/event`
- `hec_token` (text, encrypted)
- `hec_verify_tls` (checkbox, default true)
- `hec_batch_max_events` (text/int, default 500)
- `hec_batch_max_bytes` (text/int, default 1048576)
- `hec_flush_interval_ms` (text/int, default 250)
- `hec_retry_max_attempts` (text/int, default 5)
- `hec_retry_backoff_ms` (text/int, default 200)

Notes:

- Keep fields optional unless `batch_mode=1`.
- Validation must enforce HEC fields when batch mode is selected.

Implementation note:

- The UCC schema uses `batch_mode` because `output_mode` collides with reserved naming constraints in the generated UI contract.
- Runtime configuration is now `batch_mode`-only for mode selection, with per-input HEC fields used when `batch_mode=1`.

### Default stanza values

Update `package/default/inputs.conf` with safe defaults for new keys.

## Runtime Architecture Changes

## A) Add egress strategy abstraction

In `package/bin/input_module/mqtt_subscriber.py`:

- Introduce an internal `EgressWriter` interface with two implementations:
  - `ModInputSingleEventWriter` (current behavior)
  - `HecBatchWriter` (new)

Minimal interface:

- `write(enqueued_at, event_dict)`
- `flush(force=False)`
- `close()`

## B) HEC payload mapping

Map existing envelope to HEC event body without schema change:

- `event`: existing MQTT JSON envelope object
- `time`: optional current timestamp (or omit for index-time assignment parity)
- `host`, `source`, `sourcetype`, `index`: preserved from stanza/runtime logic

## C) Flush policy

Flush when any condition is met:

- queued events >= `hec_batch_max_events`
- buffered bytes >= `hec_batch_max_bytes`
- elapsed >= `hec_flush_interval_ms`

Also flush on:

- reconnect cycle transitions
- graceful shutdown

## D) Error handling

For HEC send failures:

- Retry with bounded exponential backoff
- Track counters: `hec_batches_sent`, `hec_batches_failed`, `hec_events_sent`, `hec_events_failed`, `hec_retries`
- On final failure, apply explicit policy for this phase:
  - log error + drop batch (default for R1 planning)

Rationale:

- Avoid blocking callback ingestion indefinitely.
- Keep behavior deterministic for benchmark conditions.

## E) Telemetry additions

Extend runtime summary logs with batch mode fields:

- `batch_mode`
- `hec_batch_size_avg`
- `hec_flush_count`
- `hec_retry_count_delta`
- `hec_failed_batches_delta`

## Validation & Test Plan

## Unit/logic checks (local)

1. `validate_input` rejects `batch_mode=1` when token/endpoint invalid.
2. Batch thresholds trigger flush correctly (events/bytes/time).
3. Retry/backoff stops at configured max attempts.
4. Forced flush on shutdown empties remaining buffer.

## Integration checks (docker compose)

1. Baseline parity: `batch_mode=0` preserves unchanged single-event behavior.
2. Batch mode smoke: `batch_mode=1` events arrive with expected metadata.
3. Failure simulation: invalid token/cert path emits expected errors and counters.
4. Throughput comparison under identical publisher load.

## Validation Status

### 2026-03-16 milestone (post-normalization)

- `ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.2.0` succeeded with valid `globalConfig.json`.
- `artifacts/r1_smoke_test.py` passed all covered scenarios (happy path, retry/drop on HTTP 500 and HEC code!=0, time-based flush).
- Docker-backed HEC ingest/index verification passed after schema normalization:
  - HEC response `{"text":"Success","code":0}`
  - verification marker `r1_postnorm_smoke_1773665288`
  - search count `1`
- Detailed evidence is captured in `docs/r1-smoke-validation-2026-03-14.md` under the post-normalization rerun section.
- Fresh-build reconfirmation details are captured in `docs/r1-smoke-validation-2026-03-14.md` under **Fresh rebuild rerun (2026-03-16)**.

### 2026-03-16 performance retest milestone (post-fix)

- End-to-end performance retest completed at `5000 msgs/s` for `60s` using topic `home/devices/load5000r2/telemetry`.
- Publisher result: `300442` published, `0` publish/connect/disconnect errors, final script-reported throughput `4917.16 msgs/s` over `61.1s`.
- Splunk indexed result for the exact test topic: `300442` (`100.00%` coverage).
- Runtime summary rollup reported `recv_total=300451`, `written_total=300451`, `dropped_total=0`.
- Root-cause note for earlier false-negative run: broker stanza `mc` initially pointed to external `192.168.1.21:1883`; repointing to `mosquitto:1883` restored valid end-to-end measurement.

## Rollout Strategy

1. Land config schema + defaults + no-op runtime parsing.
2. Add egress abstraction with existing writer only.
3. Add HEC batch writer behind per-input feature flag (`batch_mode`).
4. Add telemetry and docs.
5. Run parity + load tests before enabling batch mode broadly.

## Risks and Mitigations

- HEC auth/config complexity  
  Mitigation: strict validation + clear setup docs.

- Behavior drift from current sourcetype/index semantics  
  Mitigation: reuse existing metadata mapping as-is.

- Hidden buffering side effects during failures  
  Mitigation: explicit bounded buffer and clear drop policy telemetry.

## Open Decisions (Owner approval needed)

1. Should HEC batch become default later, or remain opt-in long-term?
2. Preferred failure policy after max retries: drop, block, or fallback to modular-input writer?
3. Required ordering guarantees under retry conditions.
