# TA-MQTT Static Analysis (2026-03-14)

## Scope

Static review of the current TA runtime path for MQTT ingestion into Splunk.

Reviewed sources:

- `package/bin/mqtt_subscriber.py`
- `package/bin/input_module/mqtt_subscriber.py`
- `docs/performance-report-2026-03-11.md`

## Architecture Map (as implemented)

1. Splunk launches one modular-input process per `mqtt_subscriber` stanza (`use_single_instance = False`).
2. Each process creates one paho MQTT client and subscribes to the configured topic filter.
3. paho callback thread (`on_message`) decodes payload and enqueues events into a bounded in-memory queue (`maxsize=10_000`).
4. Main thread drains queue in bounded batches (`_QUEUE_DRAIN_BATCH_SIZE = 200`).
5. For each item, TA builds a JSON envelope (`json.dumps`) and writes one Splunk event (`ew.write_event`).
6. Runtime health metrics are emitted every 60s (received/written/dropped/reconnects/queue/lag).

## Throughput-Relevant Bottlenecks

### P0 — Single-writer egress path

The output path is strictly per-event and sequential (`new_event` + `ew.write_event` in a Python loop).

Why it matters:

- Throughput is capped by one writer path per stanza.
- CPU overhead is paid for every message in Python on the hot path.

### P0 — Bounded queue with explicit drop behavior

Ingress can outpace egress. When queue is full, `on_message` drops incoming messages (`queue.Full` -> drop counter/log warning).

Why it matters:

- Under high load, this is the direct break mechanism.
- For zero-drop benchmark criteria, queue saturation defines the failure threshold.

### P1 — Per-message serialization in writer loop

`json.dumps(event_dict, ensure_ascii=False)` executes for each event in the write loop.

Why it matters:

- Adds CPU pressure exactly where throughput needs to be highest.

### P1 — Fixed queue/drain constants

`maxsize=10_000` and drain size `200` are hardcoded.

Why it matters:

- Limits tuning flexibility for different workload profiles (latency vs burst absorption).

### P2 — Reconnect strategy is fixed-delay only

Reconnect sleeps are fixed (`time.sleep(interval)`) without backoff/jitter.

Why it matters:

- Mostly resilience concern, but can amplify recovery turbulence during broker/network instability.

## Optimization Recommendations

## R1 (P0): Add optional batch egress mode

Introduce a configurable egress strategy:

- `modinput_single_event` (current behavior, default for compatibility)
- `hec_batch` (new mode with size/time-based flush + retry policy)

Expected impact:

- Largest throughput improvement potential by reducing per-event output overhead.

## R2 (P0): Shift/precompute serialization work

Reduce writer-loop CPU by moving more formatting work out of the final write section.

Implementation options:

- Precompute compact event payload at enqueue time.
- Minimize repeated dict/object construction in write path.

Expected impact:

- Meaningful improvement under sustained high EPS.

## R3 (P1): Expose queue and drain tuning settings

Make queue capacity and drain batch size configurable through TA settings.

Expected impact:

- Better control of burst handling and lag/drop trade-offs by environment.

## R4 (P1): Evaluate safe parallel write design

Only if Splunk writer semantics allow it, evaluate multi-worker write pipelines.

Expected impact:

- Medium to high potential, but depends on thread-safety and Splunk modinput guarantees.

## R5 (P2): Improve saturation telemetry

Add richer pressure signals (e.g., queue occupancy ratio bands, lag percentiles, flush timing) to speed root-cause analysis.

Expected impact:

- Better operability and faster tuning cycles.

## Suggested Execution Order

1. Implement R1 + R2 first.
2. Add R3 for environment-level tuning.
3. Evaluate R4 only after validating runtime safety constraints.
4. Add R5 to harden observability for benchmarking and operations.

## Conclusion

Current TA-MQTT design is robust and observable, but throughput is primarily constrained by the sequential per-event write path and bounded queue saturation behavior. The highest-value next step is introducing an optional batch-oriented egress mode plus hot-path CPU reduction.
