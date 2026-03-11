# TA-MQTT

TA-MQTT is a Splunk Technical Add-on that subscribes to MQTT topics and writes
messages into Splunk with sourcetype `mqtt:message`.

## Features

- Multiple broker definitions
- Anonymous, username/password, TLS, and mTLS connectivity
- QoS 0/1/2 subscriptions with wildcard topics
- JSON event envelope with consistent metadata (`broker`, `mqtt_host`, `topic`, etc.)
- Search-time payload field extraction for common telemetry keys

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.1.0
docker compose up -d
```

Local development and CI builds are pinned to Python 3.13.

Open Splunk Web at `http://localhost:8000`, then configure a broker and create
an input.

## Rebuild Workflow

When app files are bind-mounted into Docker, always rebuild using a clean output
directory:

```bash
docker compose stop splunk
rm -rf output/TA-MQTT
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.1.0
docker compose up -d splunk
```

## Documentation

- [Setup and Build](docs/setup-and-build.md)
- [Configuration and Events](docs/configuration-and-events.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Performance Testing](docs/performance-testing.md)

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
