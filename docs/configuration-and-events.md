# Configuration and Events

TA-MQTT uses a two-step configuration model:

1. **Broker connections** (`Configuration → Broker Connections`) — how to reach an
   MQTT broker (host, port, optional credentials).
2. **Topic subscriptions** (`Inputs → MQTT Topic Subscription`) — which broker to
   use and which topic filter to subscribe to (wildcards supported).

Each subscription runs as its own modular-input process. It opens one MQTT
connection using the selected broker definition and subscribes to the configured
topic filter.

## Step 1 — Configure a Broker Connection

In Splunk Web:

1. Open the TA-MQTT app.
2. Go to `Configuration → Broker Connections`.
3. Create a broker entry.

Fields:

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | Unique identifier referenced by subscriptions |
| `host` | yes | Hostname or IP |
| `port` | yes | Default `1883` (plain MQTT) |
| `username` | no | Leave empty for anonymous access |
| `password` | no | Leave empty for anonymous access; stored encrypted |

Broker names must start with a letter and contain only letters, digits, and
underscores.

### TLS / mTLS (planned)

TLS and mutual TLS broker settings exist in the schema and runtime code but are
**not yet exposed in the Configuration UI**. See `tasks/todo.md` — phase
*Broker TLS/mTLS UI*.

## Step 2 — Create a Topic Subscription

In `Inputs → MQTT Topic Subscription`:

| Field | Required | Notes |
| --- | --- | --- |
| `name` | yes | Subscription name |
| `broker` | yes | Broker connection name from step 1 |
| `topic` | yes | MQTT topic filter (`#`, `+` wildcards) |
| `qos` | yes | `0`, `1`, or `2` |
| `index` | yes | Splunk destination index |
| `sourcetype` | no | Defaults to `mqtt:message` |

### Enable or disable a subscription

Each row shows a **Status** column (`Enabled` / `Disabled`). Click the status to
toggle the subscription without deleting it. When disabled, Splunk does not
launch the modular-input process — no MQTT connection and no message consumption.

## Runtime Architecture

Each `mqtt_subscriber` stanza runs as its own modular-input process.

- Loads broker connection settings from `ta_mqtt_mqtt_broker.conf`.
- Connects to the broker and subscribes to the configured topic filter.
- The MQTT client receives messages on paho-mqtt's network thread.
- Messages are queued into a bounded in-memory queue.
- The main thread drains that queue and sends batched NDJSON payloads to Splunk
  HEC (`batch_mode=1`, the default for all inputs).
- Per-input HEC tokens are provisioned automatically when a subscription is
  created.
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
- `index`: subscription-configurable, defaults to `default`

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
