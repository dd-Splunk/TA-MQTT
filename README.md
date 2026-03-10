# TA-MQTT

Splunk Technical Add-on to subscribe to MQTT topics and index messages as JSON events.

## What It Does

- Supports multiple broker definitions
- Supports anonymous, username/password, TLS, and mTLS connectivity
- Subscribes with QoS 0/1/2 and wildcard topics
- Writes MQTT messages to Splunk with sourcetype `mqtt:message`
- Flattens JSON payload keys so fields are searchable directly

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0
docker compose up -d
```

Then open Splunk Web on `http://localhost:8000`, configure a broker, and create an input.

## Documentation

- [Setup and Build](docs/setup-and-build.md)
- [Configuration and Events](docs/configuration-and-events.md)
- [Troubleshooting](docs/troubleshooting.md)

## License

Apache 2.0
