# Setup and Build

This guide covers local development, build, and containerized testing for TA-MQTT.

## Prerequisites

- Python 3.9+
- Docker + Docker Compose
- Splunk UCC build dependency from `requirements-build.txt`

## Local Build

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0
```

Build output is generated in `output/TA-MQTT/`.

## Run with Docker Compose

```bash
docker compose up -d
```

Default ports:

- Splunk Web: `8000`
- Splunk management API: `8089`

The compose file mounts:

- `output/TA-MQTT` -> app code in container
- `.splunk-persist/TA-MQTT-local` -> persistent app local config

## Rebuild Workflow

When app files are mounted, this sequence is reliable:

```bash
docker compose stop splunk
rm -rf output/TA-MQTT
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0
docker compose up -d splunk
```

## Verify Runtime Health

```bash
docker inspect -f '{{.State.Health.Status}}' splunk
```

Expected value: `healthy`.
