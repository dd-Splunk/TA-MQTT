# Branching Policy

This document defines how git branches are used in TA-MQTT and how they map to CI,
releases, and Splunk add-on versioning.

## Branches

| Branch | Role | Who merges | CI on push | Releases |
|--------|------|------------|------------|----------|
| `main` | Production line; tagged stable releases | Maintainer via PR only | Build, Security, CodeQL | Prerelease `build-<sha>` + stable `v*` tags |
| `develop` | Integration line for the next release | Maintainer (direct push or PR) | Build, Security, CodeQL | None (artifacts in workflow run only) |
| `feature/*`, `fix/*`, `chore/*` | Short-lived topic branches | Author via PR → `develop` | On pull request | None |

`main` is the **default branch** on GitHub. Installers and operators should use
[GitHub Releases](https://github.com/dd-Splunk/TA-MQTT/releases) built from `main`
tags (`vX.Y.Z`), not raw branch checkouts.

## Workflow

```text
feature/fix branch ──PR──► develop ──PR──► main ──tag vX.Y.Z──► stable release
```

1. **Start work** from `develop` (or rebase your branch on latest `develop`).
2. **Open a PR** into `develop`. Required checks: Build, Security (Gitleaks), CodeQL.
3. **Integrate** on `develop` until the change set is ready to ship.
4. **Promote to `main`** with a PR from `develop` → `main` when releasing:
   - bump `package/app.manifest` version (and matching `app.conf` / `globalConfig.json`),
   - update `CHANGELOG.md` for that version,
   - ensure CI is green on the PR.
5. **Tag** `vX.Y.Z` on `main` after merge. CI publishes `TA-MQTT-X.Y.Z.spl` and
   `TA-MQTT-X.Y.Z.spl.sha256`.

Do **not** tag stable releases from `develop`.

## Protection rules (GitHub)

### `main`

- Pull request required before merge
- At least **1** approving review
- Required checks: `Build and Release TA-MQTT / Build and Package`,
  `Security / Secret scan`, `CodeQL / Analyze`
- Force push disabled
- Conversation resolution required

### `develop`

- Required checks: same three workflows as `main`
- Force push disabled
- Direct pushes allowed for maintainers (no mandatory review on `develop`)
- Promotion to `main` always goes through a PR with review

## Version and changelog

- `package/app.manifest` is the single source of truth for the add-on version.
- Version bumps and `CHANGELOG.md` updates belong on the PR that merges into `main`
  (release promotion), not on every feature PR to `develop`.
- `develop` may carry `[Unreleased]` changelog entries until promotion.

## Hotfixes

For urgent fixes on the current production line:

1. Branch from `main` (e.g. `fix/2.3.1-hec-flush`).
2. PR into `main` with patch version bump and changelog.
3. Tag `vX.Y.Z` on `main`.
4. Back-merge `main` into `develop` so integration does not regress.

## CI scope by branch

| Event | `develop` | `main` |
|-------|-----------|--------|
| PR / push build + AppInspect | Yes | Yes |
| Gitleaks + CodeQL | Yes | Yes |
| Prerelease `build-<sha>` publish | No | Yes |
| Stable release on `v*` tag | No | Yes |
