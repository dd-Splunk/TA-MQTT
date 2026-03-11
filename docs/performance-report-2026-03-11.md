# TA-MQTT Performance Test Report (2026-03-11)

## Scope

This report summarizes high-throughput MQTT publisher testing performed on the local Docker stack and documents the bottlenecks found, the fixes applied, and the resulting throughput limits.

## Environment

- Host: macOS
- Broker: Mosquitto 2.x in Docker (`compose.yml`)
- Consumer path: Splunk + TA-MQTT (for end-to-end runs)
- Load tool: Apache JMeter 5.6.3 + XMeter MQTT plugin (`hivemq` client factory)

## Key Fixes Applied Before Final Measurements

1. **JMeter thread throughput mode**
   - `ConstantThroughputTimer.calcMode` changed to `0` (all active threads), replacing `1`.

2. **JMeter invocation parameters**
   - Explicitly passed `-Jmqtt.clients` and `-Jmqtt.loops` in runner usage to avoid defaults from `tools/jmeter/local.properties.example`.

3. **Connection stability settings**
   - `mqtt.conn_attampt_max` and `mqtt.reconn_attampt_max` increased to `3`.

4. **Broker tuning** (`tools/mosquitto.conf`)
   - `max_connections 50000`
   - `max_inflight_messages 200`
   - `max_queued_messages 10000`
   - `set_tcp_nodelay true`
   - `connection_messages false`
   - `sys_interval 0`
   - `persistence false`
   - logging reduced to warning/error

5. **Critical load-plan fix (largest impact)**
   - Restructured JMeter plans so each thread:
     - Connects once
     - Publishes in an inner loop
     - Disconnects once
   - This removed per-message connect/disconnect churn.

## Test Method

- Primary plan: `tools/jmeter/mqtt-publisher-2000mps.jmx`
- Pattern: connect-once publish loop
- Runs performed at 16, 32, and 64 threads with `10000` loops per thread.
- Topic for end-to-end: `perf/ta-mqtt/test`
- Topic for broker-only isolation: `perf/ta-mqtt/isolated`

## Final Results

### End-to-end (Splunk + TA path active)

| Threads | Samples | Duration | Throughput (msg/s) | Errors |
|---|---:|---:|---:|---:|
| 16 | 160,032 | 20s | 8,167.4/s | 0.00% |
| 32 | 320,064 | 30s | 10,786.7/s | 0.00% |
| 64 | 640,128 | 49s | 12,941.6/s | 0.00% |

Source logs:
- `artifacts/jmeter-stress-16t-10kl-connonce.log`
- `artifacts/jmeter-stress-32t-10kl-connonce.log`
- `artifacts/jmeter-stress-64t-10kl-connonce.log`

### Broker-only isolation (Splunk stopped)

| Threads | Samples | Duration | Throughput (msg/s) | Errors |
|---|---:|---:|---:|---:|
| 16 | 160,032 | 20s | 8,137.5/s | 0.00% |
| 32 | 320,064 | 30s | 10,778.4/s | 0.00% |
| 64 | 640,128 | 50s | 12,879.3/s | 0.00% |

Source logs:
- `artifacts/jmeter-brokeronly-16t-10kl.log`
- `artifacts/jmeter-brokeronly-32t-10kl.log`
- `artifacts/jmeter-brokeronly-64t-10kl.log`

### End-to-end vs broker-only delta

| Threads | End-to-end | Broker-only | Delta |
|---|---:|---:|---:|
| 16 | 8,167.4/s | 8,137.5/s | +0.4% |
| 32 | 10,786.7/s | 10,778.4/s | +0.1% |
| 64 | 12,941.6/s | 12,879.3/s | +0.5% |

Interpretation: Splunk/TA ingestion is **not** the dominant limiter for this workload profile.

## Bottleneck Findings

1. **Initial bottleneck (resolved): connection churn**
   - Per-message connect/disconnect behavior caused severe timeouts and throughput collapse.
   - Connect-once loop design removed this bottleneck completely (timeouts dropped to zero in final runs).

2. **Current bottleneck: diminishing scaling in publish path**
   - Throughput increases with more threads, but non-linearly:
     - 16 -> 32 threads: +32%
     - 32 -> 64 threads: +20%
   - This indicates saturation in the single-node localhost publish path (broker event loop + client/plugin pacing + local network/stack overhead), not ingestion backpressure.

3. **Practical ceiling observed on this setup**
   - Approximately **12.9k msg/s sustained** at 64 threads with zero errors.

## Recommendations

1. Run 96-thread and 128-thread soak tests to confirm curve flattening and establish hard ceiling.
2. If higher throughput is required, evaluate:
   - Multi-broker topology / horizontal partitioning by topic
   - Alternative high-throughput broker runtime/config profile
   - Separate load generator host from broker host to remove localhost coupling
3. Keep connect-once publish-loop structure as the default benchmark pattern.

## Changed Files During Tuning

- `tools/mosquitto.conf`
- `tools/jmeter/mqtt-publisher-1500mps.jmx`
- `tools/jmeter/mqtt-publisher-2000mps.jmx`
- `tools/run_perf_tests.sh`
