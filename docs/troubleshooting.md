# Troubleshooting

## Build fails with `ucc-gen` not found

Use the virtual environment binary directly:

```bash
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 2.1.1
```

## Build fails when `output/TA-MQTT` already exists

Stop Splunk container before deleting output folder:

```bash
docker compose stop splunk
rm -rf output/TA-MQTT
```

Then rebuild and start again.

## App does not appear in Splunk launcher

Verify the app visibility flag in `default/app.conf`:

```ini
[ui]
is_visible = 1
```

Using textual booleans can make Splunk REST report the app as non-visible.

## Add-on UI shows XML parse or REST handler errors

Check app Python path bootstrap in:

- `package/bin/import_declare_test.py`

Ensure the add-on `lib` path is included correctly.

## MQTT events do not appear in search

1. Confirm input is enabled in app UI.
2. Check broker reachability and credentials.
3. Verify sourcetype and index in input settings.
4. Search broader first:

```spl
index=* sourcetype="mqtt:message" earliest=-24h | stats count by index sourcetype
```

## MQTT input appears slow or drops messages

The modular input emits periodic runtime summary lines into the TA-specific log
file at `/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log`.
Look for messages starting with `MQTT runtime summary`.

Example local inspection:

```bash
docker compose exec -T --user 0 splunk bash -lc "tail -n 50 /opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log"
```

Useful fields:

- `recv_delta`: messages received from the broker during the summary window
- `written_delta`: messages successfully written to Splunk during the window
- `dropped_delta`: messages dropped because the in-memory queue was full
- `reconnect_delta`: reconnect attempts during the window
- `queue_depth`: queue depth at the moment of logging
- `queue_high_water`: highest observed queue depth since process start
- `lag_avg_ms`: average enqueue-to-write delay in milliseconds for the window
- `lag_max_ms`: worst enqueue-to-write delay in milliseconds for the window
- `idle_for_s`: seconds since the last successful event write
- `last_dropped_topic`: most recent topic name dropped due to queue pressure

How to interpret them:

- High `recv_delta` with lower `written_delta` means the writer path is falling behind.
- Rising `queue_high_water` means sustained pressure even if `dropped_delta` is still zero.
- Non-zero `dropped_delta` means the input has exceeded its current throughput capacity.
- High `lag_avg_ms` or `lag_max_ms` means events are waiting in the queue too long before being written.
- Repeated `reconnect_delta` increases suggest broker instability or connection churn.

If queue pressure is visible:

1. Reduce topic breadth or message volume for the stanza.
2. Spread load across more input stanzas or forwarders if operationally acceptable.
3. Check Splunk host CPU and I/O pressure before assuming the broker is the bottleneck.

## Input fails with broker not found

If the log shows an error similar to `Broker '<name>' not found in ta_mqtt_mqtt_broker.conf`,
the input stanza references a broker name that does not exist in the broker
configuration set.

Verify that:

1. The broker was created on `Configuration > MQTT Brokers`.
2. The input's `broker` field matches the broker stanza name exactly.
3. Local Docker test config under `.splunk-persist/TA-MQTT-local/` is consistent if you are bind-mounting local configs.

## Local Docker broker does not accept connections

The local Compose stack uses Mosquitto with configuration mounted from
`tools/mosquitto.conf`.

Check service state with:

```bash
docker compose ps
docker compose logs --tail 50 mosquitto
```

The expected local endpoint is `localhost:1883`.

## Duplicate fields like `field` and `field_`

This usually indicates overlapping extraction methods. TA-MQTT now uses a single
search-time path for payload extraction. Confirm active props:

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk btool props list mqtt:message --debug
```

If duplicates remain, run a fresh search window (`earliest=-15m`) to avoid stale
field discovery from old events.

## Quick runtime checks

```bash
docker exec -u splunk splunk /opt/splunk/bin/splunk btool props list mqtt:message --debug
```
