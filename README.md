# TA-MQTT

TA-MQTT is a Splunk Technical Add-on that subscribes to MQTT topics and writes
messages into Splunk with sourcetype `mqtt:message`.

Performance testing is migrating toward a repo-local JMeter MQTT publisher
workflow under `tools/jmeter/`. The repository currently keeps
`tools/mqtt_load_test.py` as a fallback tool for parity checks and quick local
smoke tests.

The current implementation uses one modular-input process per stanza. Each
stanza runs its own MQTT client, receives messages on paho-mqtt's network
thread, buffers them through a bounded in-memory queue, and writes events to
Splunk from a single writer path in the main thread.

## Features

- Multiple broker definitions
- Anonymous, username/password, TLS, and mTLS connectivity
- QoS 0/1/2 subscriptions with wildcard topics
- JSON event envelope with consistent metadata (`broker`, `mqtt_host`, `topic`, etc.)
- Search-time payload field extraction for common telemetry keys
- Periodic runtime health metrics for queue depth, lag, drops, reconnects, and throughput
- Local Docker test stack with Splunk and Mosquitto for repeatable validation

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.2.0
docker compose up -d
```

Local development and CI builds are pinned to Python 3.13.

Open Splunk Web at `http://localhost:8000`, then configure a broker and create
an input. The bundled local Docker Compose stack also exposes a Mosquitto broker
on `localhost:1883` for development and performance testing.

## Current Architecture

- One Splunk modular-input process per `mqtt_subscriber` stanza.
- One paho-mqtt client per stanza using a background network thread.
- One bounded queue (`maxsize=10000`) between the MQTT callback thread and the Splunk writer path.
- Blocking queue reads with bounded draining instead of fixed polling sleeps.
- Runtime health logs emitted every 60 seconds with throughput, lag, and queue metrics.

The primary source implementation lives in `package/bin/input_module/mqtt_subscriber.py`.
Generated runtime files are produced under `output/TA-MQTT/` by `ucc-gen build`.

## Rebuild Workflow

When app files are bind-mounted into Docker, always rebuild using a clean output
directory:

```bash
docker compose stop splunk
rm -rf output/TA-MQTT
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.2.0
docker compose up -d splunk
```

## Repository Layout

- `package/`: source of truth for the add-on's code, defaults, and manifest
- `globalConfig.json`: UCC UI schema for broker and input configuration
- `output/TA-MQTT/`: generated build output mounted into the Splunk container
- `tools/`: local development utilities, including the JMeter starter assets, the fallback Python load generator, and Mosquitto config
- `docs/`: operator and developer documentation

## Documentation

- [Setup and Build](docs/setup-and-build.md)
- [Configuration and Events](docs/configuration-and-events.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Performance Testing](docs/performance-testing.md)
- [JMeter Migration Status](docs/jmeter-migration.md)

## CI/CD and Releases

GitHub Actions workflow: `.github/workflows/build-and-release.yml`

- Builds run on every push to `main` and `develop`, and on pull requests to those branches.
- Python is pinned to `3.13` in CI.
- Build version is read from `package/app.manifest` and passed to `ucc-gen build --ta-version`.
- Output is packaged as `TA-MQTT-<version>.spl`.
- On `main` pushes, CI publishes a prerelease stream with immutable per-commit tags (`build-<shortsha>`).
- On semantic tags `vX.Y.Z`, CI publishes a stable GitHub Release.

### Version Integrity Rules

- `package/app.manifest` is the single source of truth for version.
- Build version, `.spl` version, and release version must match.
- If `package/app.manifest` version changes, `CHANGELOG.md` must be updated in the same change.

## License

Apache 2.0
