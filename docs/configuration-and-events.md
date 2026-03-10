# Configuration and Events

This guide explains broker setup, input setup, and event structure.

## Configure a Broker

In Splunk Web:

1. Open the TA-MQTT app.
2. Go to Configuration > MQTT Brokers.
3. Add a broker stanza.

Typical fields:

- `broker_name`
- `host`
- `port`
- Optional auth: `username`, `password`
- Optional TLS: `use_tls`, `skip_verify`, `ca_cert`, `client_cert`, `client_key`

## Create an Input

In Inputs > MQTT Subscriber:

- Select a configured broker
- Set `topic` filter (supports wildcards)
- Set `qos` (0, 1, 2)
- Optionally set `mqtt_client_id` (empty means auto)
- Set `index` and `sourcetype` (`mqtt:message` by default)

## Event Shape

TA-MQTT writes JSON events with standard metadata plus payload:

```json
{
  "broker": "mc",
  "host": "192.168.1.21",
  "port": 1883,
  "topic": "home/devices/0123549ADEAA1D11EE/telemetry",
  "qos": 0,
  "retain": false,
  "payload": {
    "temperature_celsius": 26.4,
    "humidity_percent": 47.9,
    "pressure_millibar": 1013.1,
    "illuminance_lux": 19.4,
    "uv_index": 0.0,
    "timestamp": 1773137303,
    "v": 1
  },
  "temperature_celsius": 26.4,
  "humidity_percent": 47.9,
  "pressure_millibar": 1013.1,
  "illuminance_lux": 19.4,
  "uv_index": 0.0,
  "timestamp": 1773137303,
  "v": 1
}
```

If payload is valid JSON, payload keys are flattened to top-level fields for direct search.
If payload is not JSON, `payload` remains a string.

## Field Naming Notes

- For JSON payloads, both styles are available:
- Top-level flattened fields, for example `temperature_celsius`
- Namespaced payload fields, for example `payload.temperature_celsius`
- For scalar/non-JSON payloads, only `payload` is populated as a string.
- Top-level flattened fields do not overwrite reserved envelope keys (`broker`, `host`, `port`, `topic`, `qos`, `retain`, `payload`).

## Search Behavior Notes

- Depending on field extraction path, some fields may appear multivalue in results.
- To force single-value display, use `mvindex(field, 0)`.

## Search Examples

```spl
index=main sourcetype="mqtt:message"
| stats latest(temperature_celsius) as temperature latest(humidity_percent) as humidity by topic
```

```spl
index=main sourcetype="mqtt:message" topic="home/devices/0123549ADEAA1D11EE/telemetry"
| eval temperature_celsius=mvindex(temperature_celsius,0), humidity_percent=mvindex(humidity_percent,0)
| table _time topic temperature_celsius humidity_percent pressure_millibar illuminance_lux uv_index v
```

```spl
index=main sourcetype="mqtt:message" topic="verify/dedup"
| table _time topic payload.temp payload.humidity payload.ok payload.state payload.sensor_id
```
