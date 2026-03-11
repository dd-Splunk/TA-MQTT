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

- `mqtt-publisher-starter.jmx`: starter JMeter plan for MQTT publishing
- `mqtt-publisher-sustained.jmx`: higher-rate sustained publish plan for local throughput testing
- `local.properties.example`: example property values for local runs

## Local Smoke Test

Run this against the Mosquitto service from `compose.yml`:

```bash
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-starter.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost \
  -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -Jmqtt.clients=1 \
  -Jmqtt.loops=100 \
  -Jmqtt.payload_bytes=256 \
  -l artifacts/jmeter-mqtt-smoke.jtl
```

The starter plan currently pins JMeter's constant throughput timer to `600`
messages per minute, which is about `10 messages/second` across the full test.
JMeter loads that timer value as a numeric field during XML parsing, so it
cannot be overridden via `-J` in this starter file. If you need a different
fixed publish rate, open the plan in JMeter and save a variant with a different
timer value.

## Sustained Load Test

Run this when you want a fixed higher-rate scenario against the same local
topic and broker:

```bash
/opt/homebrew/bin/jmeter -n \
  -t tools/jmeter/mqtt-publisher-sustained.jmx \
  -q tools/jmeter/local.properties.example \
  -Jmqtt.host=localhost \
  -Jmqtt.port=1883 \
  -Jmqtt.topic=perf/ta-mqtt/test \
  -Jmqtt.clients=4 \
  -Jmqtt.loops=7500 \
  -Jmqtt.payload_bytes=512 \
  -l artifacts/jmeter-mqtt-sustained.jtl
```

The sustained plan pins JMeter's constant throughput timer to `30000` messages
per minute, which is about `500 messages/second` across the test.

## Notes

- The starter plan uses TCP and anonymous access by default.
- TLS and mTLS fields are present in the sampler, but the starter does not ship
  a certificate workflow yet.
- The plugin uses JMeter thread-local connection state, so the plan connects,
  publishes, and disconnects within the same thread group.
- The `mqtt.client_name` default is set to `hivemq`, which matches the factory
  name exposed by the currently installed plugin jar. If your plugin exposes a
  different factory name, override it with `-Jmqtt.client_name=...`.
