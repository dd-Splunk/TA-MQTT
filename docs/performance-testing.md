# Performance Testing

This guide covers two things:

- the preferred JMeter-based workflow for generating MQTT publish load
- which Splunk dashboard panels to use when diagnosing TA-MQTT performance issues

The current local development stack already includes a Mosquitto broker in
`docker compose`, so the default local target for smoke and load testing is
`localhost:1883`.

The repository is transitioning away from using the bundled Python load
generator as the primary tool. The preferred direction is an external JMeter
test plan that uses an MQTT publisher plugin, while `tools/mqtt_load_test.py`
remains available as a fallback for parity checks and quick local smoke tests.

## Latest Report

For the latest measured throughput, bottlenecks, and tuning deltas, see
`docs/performance-report-2026-03-11.md`.

## Current Runtime Model

The performance metrics in this guide map directly to the implemented runtime:

- one modular-input process per stanza
- one paho-mqtt client per stanza
- one bounded in-memory queue between MQTT callbacks and Splunk writes
- blocking queue reads with bounded drain batches
- 60-second runtime summary logs emitted by the input process

## Preferred JMeter Publisher Workflow

The preferred load generator is a JMeter test plan that uses an MQTT publisher
plugin. The current implementation target is the EMQX/XMeter `mqtt-jmeter`
plugin, which provides MQTT Connect and Pub samplers with support for
username/password authentication, SSL/TLS, dual SSL authentication, QoS, topic
selection, and variable payload generation.

This repository now includes two repo-local JMeter plans:

- `tools/jmeter/mqtt-publisher-10mps.jmx` — smoke/starter, 10 msg/s
- `tools/jmeter/mqtt-publisher-500mps.jmx` — sustained baseline, 500 msg/s
- `tools/jmeter/mqtt-publisher-1000mps.jmx` — high-throughput, 1000 msg/s
- `tools/jmeter/mqtt-publisher-1500mps.jmx` — high-throughput, 1500 msg/s
- `tools/jmeter/mqtt-publisher-2000mps.jmx` — high-throughput, 2000 msg/s
- `tools/jmeter/mqtt-publisher-tls.jmx` — server-auth TLS validation
- `tools/jmeter/mqtt-publisher-mtls.jmx` — dual-auth mTLS validation

The repository still does not bundle JMeter binaries or plugin JARs into the
add-on build.

Recommended prerequisites:

- Java 11 or later
- Apache JMeter 5.x
- EMQX/XMeter `mqtt-jmeter` plugin JARs copied into `$JMETER_HOME/lib/ext`
- one of the repo-local plans in `tools/jmeter/` or a derivative plan built
  from them

Recommended plan structure:

- one Thread Group that represents publishing clients
- one MQTT Connect sampler per virtual user
- one MQTT Pub sampler driven by JMeter timers or throughput controls
- one Disconnect sampler for clean teardown
- user-defined variables for host, port, topic, QoS, payload bytes, username,
  password, TLS paths, and duration

Example non-GUI command for the local Compose stack:

```bash
$JMETER_HOME/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-10mps.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=127.0.0.1 \
  -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -Jmqtt.clients=1 \
  -Jmqtt.loops=100 \
  -Jmqtt.payload_bytes=256 \
  -Jmqtt.qos=0 \
  -l artifacts/jmeter-mqtt-10mps.jtl
```

The property names above are repository conventions used by the starter plan,
not built-in JMeter conventions. The current starter file keeps a fixed
Constant Throughput Timer value because JMeter parses that field as numeric at
XML load time.

For a fixed higher-rate run, use the sustained plan:

```bash
$JMETER_HOME/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-500mps.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=127.0.0.1 \
  -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -Jmqtt.clients=4 \
  -Jmqtt.loops=7500 \
  -Jmqtt.payload_bytes=512 \
  -l artifacts/jmeter-mqtt-500mps.jtl
```

That sustained plan pins the constant throughput timer to `30000`
messages/minute, which is about `500 messages/second` across the test.

For local validation, the first JMeter smoke run should target:

- host `localhost`
- port `1883`
- topic `perf/ta-mqtt/test`
- one publishing client
- low publish rate such as `10 msgs/s`
- short duration such as `10 seconds`

See `tools/jmeter/README.md` for the current local Homebrew installation layout
and starter-plan usage notes.

TLS and mTLS runs use the same property model and require providing certificate
material through:

- `mqtt.keystore_file_path`
- `mqtt.keystore_password`
- `mqtt.clientcert_file_path`
- `mqtt.clientcert_password`

## Fallback Python Publisher

Use [tools/mqtt_load_test.py](../tools/mqtt_load_test.py) when you need a quick
local smoke test or when validating feature parity against the JMeter path.

The script supports:

- configurable client count, rate, duration, payload size, and QoS
- username/password authentication
- TLS and mTLS options
- JSON or text payload generation
- periodic progress reporting plus a final summary

Prerequisites on Ubuntu:

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv
python3 -m pip install --user paho-mqtt
```

Example burst test:

```bash
python3 tools/mqtt_load_test.py \
  --host 127.0.0.1 \
  --port 1883 \
  --topic perf/ta-mqtt/test \
  --clients 4 \
  --rate 500 \
  --duration 60 \
  --payload-bytes 512 \
  --qos 0
```

Example TLS test:

```bash
python3 tools/mqtt_load_test.py \
  --host mqtt.example.local \
  --port 8883 \
  --topic perf/ta-mqtt/tls \
  --clients 2 \
  --rate 100 \
  --duration 120 \
  --payload-bytes 1024 \
  --tls \
  --ca-file ca.pem
```

What the script reports:

- `attempted`: publish attempts made by all clients
- `published`: publishes that returned success from the client library
- `publish_errors`: publish calls that failed
- `connect_errors`: clients that failed initial connection
- `disconnects`: unexpected disconnects observed during the run
- `actual_rate_msgs_per_s`: achieved publish rate across all clients

For the bundled local Compose stack, a basic smoke test looks like this:

```bash
python3 tools/mqtt_load_test.py \
  --host localhost \
  --port 1883 \
  --topic perf/ta-mqtt/test \
  --clients 1 \
  --rate 10 \
  --duration 10
```

## Recommended Dashboard

Build one dashboard from `_internal` logs for TA runtime health and one panel from indexed MQTT data for end-to-end confirmation.

Base search for runtime health:

```spl
index=_internal source="/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log" "MQTT runtime summary"
```

Field extraction block:

```spl
index=_internal source="/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log" "MQTT runtime summary"
| rex "broker=(?<broker>'[^']+'|\"[^\"]+\"|\\S+)"
| rex "recv_delta=(?<recv_delta>\d+)"
| rex "written_delta=(?<written_delta>\d+)"
| rex "dropped_delta=(?<dropped_delta>\d+)"
| rex "reconnect_delta=(?<reconnect_delta>\d+)"
| rex "queue_depth=(?<queue_depth>-?\d+)"
| rex "queue_high_water=(?<queue_high_water>\d+)"
| rex "lag_avg_ms=(?<lag_avg_ms>[0-9.]+)"
| rex "lag_max_ms=(?<lag_max_ms>[0-9.]+)"
| eval broker=trim(replace(broker,"^['\"]|['\"]$",""))
| eval recv_delta=tonumber(recv_delta), written_delta=tonumber(written_delta), dropped_delta=tonumber(dropped_delta), reconnect_delta=tonumber(reconnect_delta), queue_depth=tonumber(queue_depth), queue_high_water=tonumber(queue_high_water), lag_avg_ms=tonumber(lag_avg_ms), lag_max_ms=tonumber(lag_max_ms)
| eval backlog_delta=recv_delta-written_delta
```

Recommended panels:

1. Broker Health Table

```spl
index=_internal source="/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log" "MQTT runtime summary"
| rex "broker=(?<broker>'[^']+'|\"[^\"]+\"|\\S+)"
| rex "recv_delta=(?<recv_delta>\d+)"
| rex "written_delta=(?<written_delta>\d+)"
| rex "dropped_delta=(?<dropped_delta>\d+)"
| rex "reconnect_delta=(?<reconnect_delta>\d+)"
| rex "queue_depth=(?<queue_depth>-?\d+)"
| rex "queue_high_water=(?<queue_high_water>\d+)"
| rex "lag_avg_ms=(?<lag_avg_ms>[0-9.]+)"
| rex "lag_max_ms=(?<lag_max_ms>[0-9.]+)"
| eval broker=trim(replace(broker,"^['\"]|['\"]$",""))
| eval recv_delta=tonumber(recv_delta), written_delta=tonumber(written_delta), dropped_delta=tonumber(dropped_delta), reconnect_delta=tonumber(reconnect_delta), queue_depth=tonumber(queue_depth), queue_high_water=tonumber(queue_high_water), lag_avg_ms=tonumber(lag_avg_ms), lag_max_ms=tonumber(lag_max_ms)
| eval backlog_delta=recv_delta-written_delta
| stats sum(recv_delta) as recv sum(written_delta) as written sum(backlog_delta) as backlog sum(dropped_delta) as dropped sum(reconnect_delta) as reconnects max(queue_high_water) as max_queue_high_water avg(lag_avg_ms) as avg_lag_ms max(lag_max_ms) as max_lag_ms by broker
| eval backlog_ratio=if(recv>0, round(backlog/recv, 3), 0)
| eval health=case(
    dropped>0, "critical",
    reconnects>0, "critical",
    backlog_ratio>=0.05, "high",
    max_queue_high_water>=100, "high",
    max_lag_ms>=1000, "high",
    avg_lag_ms>=250, "warning",
    true(), "ok"
  )
| sort 0 - dropped - reconnects - backlog_ratio - max_lag_ms
```

1. Throughput vs Backlog Timechart

```spl
index=_internal source="/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log" "MQTT runtime summary"
| rex "recv_delta=(?<recv_delta>\d+)"
| rex "written_delta=(?<written_delta>\d+)"
| eval recv_delta=tonumber(recv_delta), written_delta=tonumber(written_delta)
| eval backlog_delta=recv_delta-written_delta
| timechart span=1m sum(recv_delta) as recv sum(written_delta) as written sum(backlog_delta) as backlog
```

1. Queue Pressure Timechart

```spl
index=_internal source="/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log" "MQTT runtime summary"
| rex "queue_depth=(?<queue_depth>-?\d+)"
| rex "queue_high_water=(?<queue_high_water>\d+)"
| eval queue_depth=tonumber(queue_depth), queue_high_water=tonumber(queue_high_water)
| timechart span=1m max(queue_depth) as queue_depth max(queue_high_water) as queue_high_water
```

1. Lag Timechart

```spl
index=_internal source="/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log" "MQTT runtime summary"
| rex "lag_avg_ms=(?<lag_avg_ms>[0-9.]+)"
| rex "lag_max_ms=(?<lag_max_ms>[0-9.]+)"
| eval lag_avg_ms=tonumber(lag_avg_ms), lag_max_ms=tonumber(lag_max_ms)
| timechart span=1m avg(lag_avg_ms) as lag_avg_ms max(lag_max_ms) as lag_max_ms
```

1. Drops and Reconnects Timechart

```spl
index=_internal source="/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log" "MQTT runtime summary"
| rex "dropped_delta=(?<dropped_delta>\d+)"
| rex "reconnect_delta=(?<reconnect_delta>\d+)"
| eval dropped_delta=tonumber(dropped_delta), reconnect_delta=tonumber(reconnect_delta)
| timechart span=1m sum(dropped_delta) as dropped sum(reconnect_delta) as reconnects
```

1. End-to-End Indexed Event Volume

```spl
index=* sourcetype="mqtt:message" earliest=-15m
| timechart span=1m count as indexed_events by topic limit=10
```

## Suggested Thresholds

For aggressive performance tests, treat the following as failure indicators:

- any `dropped_delta > 0`
- any `reconnect_delta > 0` unless the test intentionally restarts the broker
- `backlog_ratio >= 0.05`
- `lag_max_ms >= 1000`
- `avg_lag_ms >= 250`
- `queue_high_water >= 100`

## Test Workflow

1. Start Splunk and enable the TA-MQTT input.
2. Start the Ubuntu load generator.
3. Watch the dashboard during the run.
4. Compare the script's achieved publish rate with TA runtime `written` rate.
5. Record lag, queue growth, and any drops or reconnects.
6. Repeat with increasing `--rate`, `--clients`, and `--payload-bytes` until the first failure signal appears.
