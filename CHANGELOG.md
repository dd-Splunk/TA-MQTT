# Changelog

All notable changes to TA-MQTT should be documented in this file.

## [1.0.1] - 2026-03-10

### Changed

- Updated author metadata to Cisco identity (name: Dominique Dessy, email: `dodessy@cisco.com`, company: Cisco).
- Improved CI `.spl` packaging and root-folder validation compatibility in GitHub Actions.

## [1.0.0] - 2026-03-10

### Added

- Initial release of TA-MQTT with multi-broker MQTT subscription support.
- Anonymous, username/password, TLS, and mTLS connectivity options.
- GitHub Actions CI/CD for build, .spl packaging, and release automation.

## Versioning Policy

- `package/app.manifest` is the single source of truth for app version.
- Any change to `package/app.manifest` version must include a `CHANGELOG.md` update in the same commit/PR.
- The version used by `ucc-gen build --ta-version` must match the published `.spl` artifact and release version.
