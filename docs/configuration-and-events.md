# Configuration and Events

This guide explains the current broker configuration model, input fields, event
envelope, and search-time field behavior.

## Configure a Broker

In Splunk Web:

1. Open the TA-MQTT app.
2. Go to `Configuration > MQTT Brokers`.
3. Create a broker entry.

Common fields:

- `name`
- `host`
- `port`
- Optional credentials: `username`, `password`
- Optional TLS settings: `use_tls`, `skip_verify`, `ca_cert`, `client_cert`, `client_key`

Broker names are referenced by inputs through the `broker` field. They must be
unique and use letters, digits, and underscores.

## Create an Input

In `Inputs > MQTT Subscriber`:

- Select `broker`
- Set `topic` (wildcards supported)
- Set `qos` (0, 1, or 2)
- Optional `mqtt_client_id` (empty or `AUTO` generates one)
- Set `index`
- Optional `sourcetype` (defaults to `mqtt:message`)
- Optional `interval` for reconnect delay after unexpected disconnects

Current input field names in the UCC schema are:

- `name`
- `broker`
- `topic`
- `qos`
- `mqtt_client_id`
- `index`
- `sourcetype`
- `interval`

If `mqtt_client_id` is left empty or set to `AUTO`, the add-on generates a
deterministic client ID based on the stanza name.

## Runtime Architecture

Each `mqtt_subscriber` stanza runs as its own modular-input process.

- The MQTT client receives messages on paho-mqtt's network thread.
- Messages are queued into a bounded in-memory queue.
- The main thread drains that queue and calls `ew.write_event()`.
- Runtime health summaries are logged every 60 seconds.

## Event Format

TA-MQTT writes a JSON envelope for each MQTT message. The `payload` value is
stored as a string exactly as received from MQTT. The add-on does not parse the
payload into indexed fields during ingestion.

```json
{
  "broker": "mc",
  "mqtt_host": "192.168.1.21",
  "port": 1883,
  "topic": "home/devices/0123549ADEAA1D11EE/telemetry",
  "qos": 0,
  "retain": false,
  "payload": "{\"uv_index\":8.0,\"timestamp\":1773147645,\"v\":1}"
}
```

Additional event metadata is set outside the JSON payload when the event is
written to Splunk:

- `host`: broker host
- `source`: `mqtt://<host>:<port>/<topic>`
- `sourcetype`: `mqtt:message` by default
- `index`: input-configurable, defaults to `default`

## Field Extraction Behavior

For `sourcetype=mqtt:message`:

- `KV_MODE=json` extracts top-level envelope fields.
- `EVAL-... = spath(payload, "...")` extracts selected payload keys at search time.
- Raw event data is not rewritten by these extractions.

Currently extracted payload keys:

- `temperature_celsius`
- `humidity_percent`
- `pressure_millibar`
- `illuminance_lux`
- `uv_index`
- `timestamp`
- `v`
- `temp`
- `humidity`
- `ok`
- `state`
- `sensor_id`

If a payload key is not in the list above, use `spath` directly in searches.

Current CIM-oriented aliases also map:

- `mqtt_host` -> `dest`
- `port` -> `dest_port`

## Search Examples

```spl
index=main sourcetype=mqtt:message
| stats latest(temperature_celsius) as temperature latest(humidity_percent) as humidity by topic
```

```spl
index=main sourcetype=mqtt:message topic="home/devices/0123549ADEAA1D11EE/telemetry"
| table _time topic temperature_celsius humidity_percent pressure_millibar illuminance_lux uv_index v
```

```spl
index=main sourcetype=mqtt:message
| eval payload_temp=spath(payload, "temp")
| table _time topic payload payload_temp
```

## Runtime Health Logging

The input also emits periodic health summaries into the internal log stream.
These are not MQTT events; they are operational metrics for troubleshooting and
performance testing.

Important fields include:

- `recv_delta`
- `written_delta`
- `dropped_delta`
- `reconnect_delta`
- `queue_depth`
- `queue_high_water`
- `lag_avg_ms`
- `lag_max_ms`
- `idle_for_s`
- `last_dropped_topic` when applicable
