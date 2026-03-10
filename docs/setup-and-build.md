# Setup and Build

This guide covers local build and Docker-based testing for TA-MQTT.

## Prerequisites

- Python 3.9+
- Docker Desktop (or Docker Engine) with Compose
- Build dependencies from `requirements-build.txt`

## Initial Local Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
```

## Build the Add-on

```bash
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0
```

Output is generated at `output/TA-MQTT/`.

## Start Splunk with Docker Compose

```bash
docker compose up -d
```

Default ports:

- Splunk Web: `8000`
- Splunk Management API: `8089`

Volume mounts used by `compose.yml`:

- `output/TA-MQTT` -> `/opt/splunk/etc/apps/TA-MQTT`
- `.splunk-persist/TA-MQTT-local` -> `/opt/splunk/etc/apps/TA-MQTT/local`

## Reliable Rebuild Cycle

Use this exact sequence after source changes:

```bash
docker compose stop splunk
rm -rf output/TA-MQTT
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0
docker compose up -d splunk
```

`ucc-gen build` expects a clean output directory. Rebuilding without removing
`output/TA-MQTT` can fail with `FileExistsError`.

## Health Checks

```bash
docker inspect -f '{{.State.Health.Status}}' splunk
```

Expected result: `healthy`.

Optional app visibility check:

```bash
curl -sk -u 'admin:<password>' 'https://localhost:8089/services/apps/local/TA-MQTT?output_mode=json'
```
