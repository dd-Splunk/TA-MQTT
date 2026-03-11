# JMeter MQTT Publisher Starter

This directory contains a repo-local starter plan for driving the TA-MQTT local
Mosquitto broker with the locally installed JMeter MQTT Publisher plugin.

## Expected Local Installation

This starter was written against the current macOS Homebrew JMeter layout:

- JMeter launcher: `/opt/homebrew/bin/jmeter`
- JMeter home: `/opt/homebrew/opt/jmeter/libexec`
- JMeter plugin directory: `/opt/homebrew/opt/jmeter/libexec/lib/ext`

The local installation already contains these MQTT plugin JARs:

- `mqtt-jmeter-0.0.1-SNAPSHOT.jar`
- `mqtt-xmeter-2.0.2-jar-with-dependencies.jar`

The installed plugin exposes these sampler classes used by the starter plan:

- `net.xmeter.samplers.ConnectSampler`
- `net.xmeter.samplers.PubSampler`
- `net.xmeter.samplers.DisConnectSampler`

## Included Files

- `mqtt-publisher-10mps.jmx`: smoke/starter plan, 10 msg/s (600 msg/min)
- `mqtt-publisher-500mps.jmx`: sustained baseline plan, 500 msg/s (30 000 msg/min)
- `mqtt-publisher-1000mps.jmx`: high-throughput plan, 1000 msg/s (60 000 msg/min)
- `mqtt-publisher-1500mps.jmx`: high-throughput plan, 1500 msg/s (90 000 msg/min)
- `mqtt-publisher-2000mps.jmx`: high-throughput plan, 2000 msg/s (120 000 msg/min)
- `mqtt-publisher-tls.jmx`: server-auth TLS publish plan template
- `mqtt-publisher-mtls.jmx`: dual-auth mTLS publish plan template
- `local.properties.example`: example property values for local runs

## Local Smoke Test

Run this against the Mosquitto service from `compose.yml`:

```bash
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-10mps.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost \
  -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -Jmqtt.clients=1 \
  -Jmqtt.loops=100 \
  -Jmqtt.payload_bytes=256 \
  -l artifacts/jmeter-mqtt-10mps.jtl
```

The 10mps plan pins JMeter's constant throughput timer to `600`
messages per minute, which is about `10 messages/second` across the full test.
JMeter loads that timer value as a numeric field during XML parsing, so it
cannot be overridden via `-J` in this starter file. If you need a different
fixed publish rate, open the plan in JMeter and save a variant with a different
timer value.

## 500 msg/s Baseline Load Test

Run this when you want the validated sustained baseline scenario:

```bash
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-500mps.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost \
  -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -Jmqtt.clients=4 \
  -Jmqtt.loops=7500 \
  -Jmqtt.payload_bytes=512 \
  -l artifacts/jmeter-mqtt-sustained.jtl
```

The 500mps plan pins JMeter's constant throughput timer to `30000` messages
per minute, which is about `500 messages/second` across the test.

## Notes

- The starter plan uses TCP and anonymous access by default.
- TLS and mTLS use dedicated plan templates in this directory.
- The plugin uses JMeter thread-local connection state, so the plan connects,
  publishes, and disconnects within the same thread group.
- The `mqtt.client_name` default is set to `hivemq`, which matches the factory
  name exposed by the currently installed plugin jar. If your plugin exposes a
  different factory name, override it with `-Jmqtt.client_name=...`.

## TLS Server-Auth Test

Run this against a TLS-enabled broker and provide trust material through the
plugin's keystore path fields:

```bash
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-tls.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost \
  -Jmqtt.port=8883 \
  -Jmqtt.protocol=SSL \
  -Jmqtt.topic=perf/ta-mqtt/tls \
  -Jmqtt.qos=1 \
  -Jmqtt.keystore_file_path=/absolute/path/to/ca-or-truststore \
  -Jmqtt.keystore_password=changeit \
  -l artifacts/jmeter-mqtt-tls.jtl
```

## mTLS Dual-Auth Test

Run this when the broker requires client certificates in addition to server
certificate validation:

```bash
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-mtls.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost \
  -Jmqtt.port=8883 \
  -Jmqtt.protocol=SSL \
  -Jmqtt.topic=perf/ta-mqtt/mtls \
  -Jmqtt.qos=1 \
  -Jmqtt.keystore_file_path=/absolute/path/to/ca-or-truststore \
  -Jmqtt.keystore_password=changeit \
  -Jmqtt.clientcert_file_path=/absolute/path/to/client-keystore \
  -Jmqtt.clientcert_password=changeit \
  -l artifacts/jmeter-mqtt-mtls.jtl
```

The current XMeter plugin maps TLS and client-certificate material through the
Connect sampler fields `mqtt.keystore_file_path` and
`mqtt.clientcert_file_path`.

## High-Throughput Stepped Plans

Three fixed-rate plans step up from the sustained baseline (500 msg/s) through
1000, 1500, and 2000 msg/s. Each runs 8 clients with 7500 loops and a 5 s
ramp. Increase `mqtt.clients` and `mqtt.loops` to extend the test window.

```bash
# 1000 msg/s
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-1000mps.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -l artifacts/jmeter-mqtt-1000mps.jtl

# 1500 msg/s
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-1500mps.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -l artifacts/jmeter-mqtt-1500mps.jtl

# 2000 msg/s
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-2000mps.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -l artifacts/jmeter-mqtt-2000mps.jtl
```

> **Note:** The ConstantThroughputTimer is a best-effort ceiling — actual
> throughput depends on host CPU, JVM GC, and broker capacity. For Mosquitto
> running in Docker on the local machine, broker and subscriber saturation
> typically becomes the bottleneck before 2000 msg/s.
