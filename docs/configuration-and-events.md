# Configuration and Events

This guide explains broker setup, input setup, event format, and field behavior.

## Configure a Broker

In Splunk Web:

1. Open the TA-MQTT app.
2. Go to `Configuration > MQTT Brokers`.
3. Create a broker entry.

Common fields:

- `broker_name`
- `host`
- `port`
- Optional credentials: `username`, `password`
- Optional TLS settings: `use_tls`, `skip_verify`, `ca_cert`, `client_cert`, `client_key`

## Create an Input

In `Inputs > MQTT Subscriber`:

- Select `broker`
- Set `topic` (wildcards supported)
- Set `qos` (0, 1, or 2)
- Optional `mqtt_client_id` (empty or `auto` generates one)
- Set `index`
- Keep `sourcetype` as `mqtt:message` unless you have a custom pipeline

## Event Format

TA-MQTT writes a JSON envelope for each MQTT message. The `payload` value is
stored as a string exactly as received from MQTT.

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

## Field Extraction Behavior

For `sourcetype=mqtt:message`:

- `KV_MODE=json` extracts top-level envelope fields.
- `EVAL-... = spath(payload, "...")` extracts selected payload keys at search time.

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
