# TA-MQTT

TA-MQTT is a Splunk Technical Add-on that subscribes to MQTT topics and writes
messages into Splunk with sourcetype `mqtt:message`.

This README is intentionally brief. Detailed operational and developer guidance
lives under `docs/`.

## Features

- Multiple broker connection definitions (host, port, username/password)
- Topic subscriptions per broker with QoS 0/1/2 and wildcard filters
- JSON event envelope with consistent metadata (`broker`, `mqtt_host`, `topic`, etc.)
- Configurable queue capacity, reconnect backoff/cooldown resilience, and runtime health metrics
- HEC batch egress with per-input token lifecycle management
- Broker TLS/mTLS in Configuration UI (`use_tls`, CA/client PEM, `skip_verify` gated by Security settings)
- Local Docker test stack with Splunk and Mosquitto for repeatable validation

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
APP_VERSION=$(python3 -c 'import json; print(json.load(open("package/app.manifest", encoding="utf-8"))["info"]["id"]["version"])')
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version "$APP_VERSION" --overwrite
docker compose up -d
```

Local development and CI builds are pinned to Python 3.13.

## Repository Layout

- `package/`: source of truth for the add-on's code, defaults, and manifest
- `globalConfig.json`: UCC UI schema for broker and input configuration
- `output/TA-MQTT/`: generated build output mounted into the Splunk container
- `tools/`: local development utilities, including the JMeter starter assets, the fallback Python load generator, and Mosquitto config
- `docs/`: operator and developer documentation

## Documentation

- [Setup and Build](docs/setup-and-build.md)
- [Branching Policy](docs/branching-policy.md)
- [Prerelease Policy](docs/prereleases.md)
- [Configuration and Events](docs/configuration-and-events.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Performance Testing](docs/performance-testing.md)
- [JMeter Migration Status](docs/jmeter-migration.md)
- [TLS/mTLS Test Plan](docs/test-plan-mqtt-tls-mtls.md)
- [TLS/mTLS Test Evidence](docs/test-evidence-mqtt-tls-mtls.md)

## CI/CD and Releases

GitHub Actions workflow: `.github/workflows/build-and-release.yml`

Branching model: see [Branching Policy](docs/branching-policy.md) (`develop` = integration, `main` = release line).

Prerelease stream (`build-<shortsha>` on `main` pushes): see [Prerelease Policy](docs/prereleases.md). Only the **10 most recent** prereleases are kept.

- Builds run on every push to `main` and `develop`, and on pull requests targeting those branches.
- Python is pinned to `3.13` in CI.
- Build version is read from `package/app.manifest` and passed to `ucc-gen build --ta-version`.
- UCC framework is pinned in `requirements-build.txt` (currently `6.5.0`).
- `ucc-gen validate` runs on the built add-on before packaging (AppInspect).
- Output is packaged as `TA-MQTT-<version>.spl`.
- On `main` pushes, CI publishes a prerelease stream with immutable per-commit tags (`build-<shortsha>`); see [Prerelease Policy](docs/prereleases.md) for retention (10 builds).
- On semantic tags `vX.Y.Z`, CI publishes a stable GitHub Release.

### Version Integrity Rules

- `package/app.manifest` is the single source of truth for version.
- Build version, `.spl` version, and release version must match.
- If `package/app.manifest` version changes, `CHANGELOG.md` must be updated in the same change.

## License

Apache 2.0
