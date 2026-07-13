# Changelog

All notable changes to TA-MQTT should be documented in this file.

## [Unreleased]

## [2.4.2] - 2026-07-11

### Added in 2.4.2

- HEC event model: JSON MQTT bodies indexed as `_raw` with `KV_MODE=json`; envelope metadata sent via HEC `fields`.
- CIM envelope fields at ingest (`src`, `dvc`, `app`, `action`, `transport`) plus `FIELDALIAS` `dest`/`dest_port` and topic `EXTRACT` fallbacks.
- `transforms.conf` topic parsing; Search view shows CIM and telemetry columns.
- Declared **Interprocess Messaging** and **Network Traffic** CIMs in `app.manifest`.

### Changed in 2.4.2

- Non-JSON MQTT payloads continue to use the full envelope dict as the HEC `event`.
- Updated event indexing and CIM alias documentation in `docs/configuration-and-events.md`.

## [2.4.1] - 2026-07-11

### Fixed in 2.4.1

- Fixed Configuration **unknown error** when the broker table rendered the `use_tls` checkbox without a value mapping (UCC table requires `mapping` for boolean columns).
- Normalized lab broker stanzas to `use_tls=0` / `skip_verify=0` instead of string `false`.

## [2.4.0] - 2026-07-10

### Added in 2.4.0

- Broker TLS/mTLS fields in Configuration → Broker Connections (`use_tls`, CA/client PEM, `skip_verify`).
- TLS column on the broker connections table.
- **Allow insecure TLS** visible under Configuration → Security (advanced); required for `skip_verify` and HEC TLS bypass.

### Changed in 2.4.0

- Split UCC post-build hooks: `cleanup_output_files()` (bytecode) and `additional_packaging()` (dashboard patches) per UCC documentation.
- Updated `app.manifest` classification (Beta, IoT/IT Operations audience) and release metadata.

### Documentation

- Build docs now derive `--ta-version` from `package/app.manifest` instead of a hardcoded release.
- Documented `allow_insecure_tls` gate for lab TLS/HEC testing in troubleshooting and `tasks/todo.md`.
- Updated `SECURITY.md` supported versions for 2.4.x.
- Added `docs/branching-policy.md` and created protected `develop` integration branch.
- Added `docs/prereleases.md`; CI prunes `build-*` prereleases beyond the 10 most recent.
- Documented local workspace hygiene in `docs/setup-and-build.md`; removed stale `tmp_output/`, local `artifacts/` logs, and old `dist/*.spl`.
- Documented broker TLS/mTLS configuration in `docs/configuration-and-events.md`.

## [2.3.0] - 2026-07-10

### Changed in 2.3.0

- Migrated bundled MQTT client from **paho-mqtt 1.6.1** to **2.1.0** with `CallbackAPIVersion.VERSION2` callbacks in the modular input.
- Fixed `ta_mqtt_settings.conf` precedence so `local/` overrides `default/` for `allow_insecure_tls` and other settings.

### Security

- Added CodeQL static analysis workflow for Python (`package/bin/`) with documented suppressions for Splunk localhost REST TLS.
- Gated `skip_verify` and `hec_verify_tls=0` behind `allow_insecure_tls` in `ta_mqtt_settings.conf` (default off).
- Set `chmod 0o600` on temporary mTLS certificate/key files.
- Stable releases now publish a companion `TA-MQTT-x.y.z.spl.sha256` checksum file.
- Added `SECURITY.md` vulnerability disclosure policy.
- Added Dependabot for pip (`/`, `package/lib`) and GitHub Actions.
- Added Gitleaks secret scanning workflow on pull requests and branch pushes.
- Pinned all GitHub Actions to immutable commit SHAs in CI workflows.
- Fixed Gitleaks PR scans by using full git history (`fetch-depth: 0`) in the Security workflow.

## [2.2.0] - 2026-07-10

### Added in 2.2.0

- Added a classic Splunk **Search** dashboard (`sourcetype=mqtt:message`) with time picker and 60s refresh.
- Added **Search** row action on MQTT topic subscriptions.
- Post-build dashboard patching: single global time token (`global_time`), duplicate tab pickers removed, 60s panel refresh.

### Changed in 2.2.0

- Monitoring dashboard now exposes **one** time picker that drives all panels across Overview and tab views via `form.global_time.*` URL tokens.
- Configuration UI labels clarified (Brokers / Subscriptions); broker TLS/mTLS and advanced HEC fields hidden until a follow-up release.
- `additional_packaging.py` removes AppInspect-rejected bytecode and patches UCC dashboard JSON (no fragile JS bundle edits).
- CI pins UCC `6.5.0`, runs `ucc-gen validate`, and documents `--overwrite` rebuild flow.
- Stopped tracking generated `tmp_output/TA-MQTT/` build artifacts in git.

### Fixed in 2.2.0

- Fixed Monitoring dashboard **unknown error** caused by invalid post-build JavaScript patches.
- Fixed empty **Search** navigation view (UCC React route had no mounted component).

## [2.1.1] - 2026-03-17

### Changed in 2.1.1

- Improved HEC batch writer shutdown with idempotent close behavior and deterministic close-summary metrics.
- Improved non-UTF payload handling with explicit decode-fallback metadata and base64 preservation.
- Improved reconnect resilience with exponential backoff, cooldown behavior, and additional reconnect health metrics.
- Added configurable per-input MQTT event queue capacity with UI, REST validation, and runtime wiring.

## [2.1.0] - 2026-03-17

### Added in 2.1.0

- Added robust per-input Splunk HEC token lifecycle management in both REST hooks and modular input runtime.

### Fixed in 2.1.0

- Fixed runtime stanza-name handling so full input names are used for client IDs and token mapping.
- Fixed runtime token self-heal persistence by updating `inputs.conf` through Splunk's conf API.
- Fixed `Telemetrie` broker targeting by aligning `mc` with `192.168.1.21:1883` in local validation config.

## [2.0.1] - 2026-03-16

### Fixed in 2.0.1

- Fixed input name validation to allow dashes (e.g., `dd-auto-hec`).
- Hidden `batch_mode` field from input create/edit forms (always HEC batch writer).
- Fixed REST handler class configuration to properly invoke auto-token generation hooks.

## [2.0.0] - 2026-03-16

### Added in 2.0.0

- Added per-input `batch_mode` configuration (`0` single-event writer, `1` HEC batch writer).
- Added per-input HEC controls for endpoint, token, TLS verification, batch thresholds, and retry/backoff settings.
- Added post-build output cleanup hook to remove Python cache/bytecode artifacts.

### Changed in 2.0.0

- Introduced optional HEC batch egress strategy while preserving current single-event path as default (`batch_mode=0`).
- Removed legacy runtime/default-config compatibility path based on `output_mode`.
- Strengthened HEC token validation in both UI schema and runtime (`1-64` chars, `[A-Za-z0-9-]`).
- Hardened modular-input entrypoint to avoid bytecode writes in runtime environments.
- Updated R1 implementation/smoke documentation to match the current architecture and validation state.

### Validated in 2.0.0

- Build and smoke flow validated after major changes.
- End-to-end performance retest validated at `5000 msgs/s` for `60s` with full indexing coverage in local Docker stack.

## [1.2.0] - 2026-03-11

### Added in 1.2.0

- Added a local Mosquitto service in Docker Compose for repeatable add-on testing.
- Added an Ubuntu-friendly MQTT load generator and performance testing guide.
- Added repo-local JMeter MQTT publisher assets (`tools/jmeter/`) with starter and sustained non-GUI plans.
- Added dedicated JMeter TLS and mTLS publisher plan templates for Phase 6 parity work.

### Changed in 1.2.0

- Updated the load generator to use `paho-mqtt` callback API v2 to remove deprecation warnings.
- Updated performance and setup documentation to make JMeter the preferred load path while keeping the Python generator as fallback.

## [1.1.0] - 2026-03-11

### Changed in 1.1.0

- Added MQTT runtime summary instrumentation for queue depth, lag, drops, reconnects, and write throughput visibility.
- Replaced the fixed 50 ms local queue polling loop with blocking queue reads and bounded draining to reduce idle overhead.

## [1.0.1] - 2026-03-10

### Changed in 1.0.1

- Updated author metadata to Cisco identity (name: Dominique Dessy, email: `dodessy@cisco.com`, company: Cisco).
- Improved CI `.spl` packaging and root-folder validation compatibility in GitHub Actions.

## [1.0.0] - 2026-03-10

### Added in 1.0.0

- Initial release of TA-MQTT with multi-broker MQTT subscription support.
- Anonymous, username/password, TLS, and mTLS connectivity options.
- GitHub Actions CI/CD for build, .spl packaging, and release automation.

## Versioning Policy

- `package/app.manifest` is the single source of truth for app version.
- Any change to `package/app.manifest` version must include a `CHANGELOG.md` update in the same commit/PR.
- The version used by `ucc-gen build --ta-version` must match the published `.spl` artifact and release version.
