# Setup and Build

This guide covers local build and Docker-based testing for TA-MQTT.

## Prerequisites

- Python 3.13
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

The value passed to `--ta-version` must match `package/app.manifest`.

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

## CI/CD Build and Release

GitHub Actions workflow: `.github/workflows/build-and-release.yml`

- CI uses Python `3.13`.
- CI reads app version from `package/app.manifest`.
- CI builds and packages `dist/TA-MQTT-<version>.spl`.
- Pushes to `main` publish prereleases using immutable tags (`build-<shortsha>`).
- Pushes of semantic tags `vX.Y.Z` publish stable releases.

### Version and Changelog Enforcement

- `package/app.manifest` is the version source of truth.
- Build and publish versions must match exactly.
- If app version changes, `CHANGELOG.md` must be updated in the same PR/commit.
