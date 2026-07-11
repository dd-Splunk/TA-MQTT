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

### TLS / mTLS

Enable **Enable TLS/SSL** on the broker connection. Use port `8883` for typical TLS
brokers unless your environment uses another port.

| Field | Required | Notes |
| --- | --- | --- |
| `use_tls` | no | Encrypt the MQTT transport |
| `ca_cert` | no | PEM CA to verify the broker; empty uses the system trust store |
| `client_cert` / `client_key` | no | PEM pair for mutual TLS (mTLS); both required when using client auth |
| `skip_verify` | no | Skips server certificate validation; requires **Allow insecure TLS** under Configuration → Security (advanced) |

For lab brokers with self-signed certificates, enable **Allow insecure TLS** on the
Security tab before setting `skip_verify` on the broker.

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

- `KV_MODE=json` extracts fields from `_raw`.
- **JSON MQTT bodies** (HEC default): the input sends the parsed MQTT JSON as the HEC
  `event` body. Splunk indexes it as `_raw` and `KV_MODE=json` extracts keys such as
  `temperature_celsius`, `humidity_percent`, etc. Envelope metadata (`broker`, `topic`,
  `payload`, `mqtt_host`, …) is sent via HEC `fields` and indexed alongside.
- **Non-JSON bodies**: the full envelope dict is sent as the HEC `event`.
- **Legacy envelope events**: use `spath` at search time if needed:

```spl
| spath input=payload path=temperature_celsius
```

Reload `props.conf` / `transforms.conf` without restarting Splunk:

```text
http://localhost:8000/en-US/debug/refresh
```

CIM aliases in `props.conf` (search-time, app TA-MQTT) :

| Champ CIM | Source |
|-----------|--------|
| `dest` | FIELDALIAS ← `mqtt_host` |
| `dest_port` | FIELDALIAS ← `port` |
| `src`, `dvc` | 3ᵉ segment du topic (ingest HEC + EXTRACT fallback) |
| `app` | nom de connexion `broker` (ingest HEC) |
| `action` | 4ᵉ segment du topic (ingest HEC + EXTRACT fallback) |
| `transport` | constante `mqtt` (ingest HEC) |

## Search Examples

```spl
index=main sourcetype=mqtt:message
| stats latest(temperature_celsius) as temperature latest(humidity_percent) as humidity by topic
```

```spl
index=main sourcetype=mqtt:message
| table _time topic dvc temperature_celsius humidity_percent pressure_millibar illuminance_lux uv_index v
```

```spl
index=main sourcetype=mqtt:message
| table _time topic payload temp humidity state
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
