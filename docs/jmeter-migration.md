# JMeter Migration Status

This note tracks the migration from the bundled Python MQTT load generator to a
JMeter-based MQTT publisher workflow.

## Current Direction

- Preferred load generator: repo-local JMeter assets under `tools/jmeter/`
- Current plugin target: EMQX/XMeter `mqtt-jmeter`
- Repository role: keep smoke and sustained JMX plans and document how to run them against TA-MQTT
- Temporary fallback: `tools/mqtt_load_test.py`
- TLS/mTLS status: dedicated JMX templates now exist (`mqtt-publisher-tls.jmx` and `mqtt-publisher-mtls.jmx`) and need broker-specific cert material to execute

## Why JMeter Still Stays Out of the Add-on Build

- TA-MQTT build and packaging are Python-only today.
- The add-on CI pipeline does not provision Java or JMeter.
- JMeter plugin JARs do not belong in the Splunk add-on package.
- Test plans evolve independently from the add-on runtime code.

## Required Parity Before Python Removal

- Publish to the same brokers and topics used by the current Python script.
- Support client-count and publish-rate driven load tests.
- Support QoS 0, 1, and 2 publishing.
- Support username/password authentication.
- Support TLS and mutual TLS flows used by TA-MQTT validation.
- Produce an artifact trail that is usable in CI or local investigations.

## Current Starter Plan Contract

The repo-local JMX plans under `tools/jmeter/` expose properties for:

- `mqtt.host`
- `mqtt.port`
- `mqtt.topic`
- `mqtt.clients`
- `mqtt.payload_bytes`
- `mqtt.qos`
- `mqtt.username`
- `mqtt.password`
- `mqtt.loops`
- `mqtt.ramp_up`
- `mqtt.client_name`
- `mqtt.client_id_prefix`
- `mqtt.keep_alive`
- `mqtt.keystore_file_path`
- `mqtt.keystore_password`
- `mqtt.clientcert_file_path`
- `mqtt.clientcert_password`

The current local plugin advertises `hivemq` as the default MQTT factory name.

These names are a repository convention for the migration, not a built-in
requirement of JMeter or the plugin.

## Exit Criteria

The Python script can be removed only after all of the following are true:

1. The JMeter publisher runs successfully against the local `docker compose`
   Mosquitto broker.
2. Equivalent smoke and burst scenarios have been compared with the Python
   baseline.
3. The Splunk searches in [docs/performance-testing.md](./performance-testing.md)
   remain valid under JMeter-generated load.
4. Contributors can run the JMeter workflow from documented prerequisites
   without manual trial-and-error.

## Branch Scope

This branch is intentionally limited to migration guidance and repo-facing
starter assets. It does not bundle JMeter binaries or plugin JARs.
