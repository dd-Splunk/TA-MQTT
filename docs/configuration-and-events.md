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
  "topic": "home/devices/abc/telemetry",
  "qos": 0,
  "retain": false,
  "payload": {
    "temperature_celsius": 26.1,
    "humidity_percent": 49.0
  },
  "temperature_celsius": 26.1,
  "humidity_percent": 49.0
}
```

If payload is valid JSON, payload keys are flattened to top-level fields for direct search.
If payload is not JSON, `payload` remains a string.

## Search Examples

```spl
index=main sourcetype="mqtt:message"
| stats latest(temperature_celsius) as temperature latest(humidity_percent) as humidity by topic
```

```spl
index=main sourcetype="mqtt:message" topic="verify/dedup"
| table _time topic temp humidity ok state sensor_id
```
