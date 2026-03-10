# Troubleshooting

## Build fails with `ucc-gen` not found

Use the virtual environment binary directly:

```bash
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0
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
