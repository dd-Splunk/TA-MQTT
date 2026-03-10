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
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0
docker compose up -d
```

Open Splunk Web at `http://localhost:8000`, then configure a broker and create
an input.

## Rebuild Workflow

When app files are bind-mounted into Docker, always rebuild using a clean output
directory:

```bash
docker compose stop splunk
rm -rf output/TA-MQTT
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0
docker compose up -d splunk
```

## Documentation

- [Setup and Build](docs/setup-and-build.md)
- [Configuration and Events](docs/configuration-and-events.md)
- [Troubleshooting](docs/troubleshooting.md)

## License

Apache 2.0
