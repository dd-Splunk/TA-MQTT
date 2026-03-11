# Changelog

All notable changes to TA-MQTT should be documented in this file.

## [1.2.0] - 2026-03-11

### Added in 1.2.0

- Added a local Mosquitto service in Docker Compose for repeatable add-on testing.
- Added an Ubuntu-friendly MQTT load generator and performance testing guide.

### Changed in 1.2.0

- Updated the load generator to use `paho-mqtt` callback API v2 to remove deprecation warnings.

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
