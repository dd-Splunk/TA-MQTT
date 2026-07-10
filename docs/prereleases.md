# Prerelease Policy (`build-<sha>`)

This document describes the **latest prerelease stream** published by CI on pushes to
`main`. For branch workflow and stable releases, see [Branching Policy](branching-policy.md).

## Purpose

Prereleases are **integration smoke artifacts**, not supported production builds.

- Validate that `main` produces a installable `.spl` after each merge.
- Let maintainers download a specific commit build without tagging a stable release.
- Operators and customers should install **[stable `vX.Y.Z` releases](https://github.com/dd-Splunk/TA-MQTT/releases/latest)** only.

## When CI publishes a prerelease

| Trigger | Publishes `build-<sha>`? |
|---------|--------------------------|
| Push to `main` | Yes |
| Push to `develop` | No (workflow artifacts only, 30-day retention) |
| Pull request | No |
| Tag `vX.Y.Z` on `main` | No — publishes **stable** release instead |

Workflow: `.github/workflows/build-and-release.yml` job `release_latest`.

## Naming and contents

| Field | Value |
|-------|--------|
| Git tag | `build-<shortsha>` (7-character commit SHA) |
| Release title | `latest (prerelease) - build-<shortsha>` |
| Asset | `TA-MQTT-<app.manifest version>.spl` |
| GitHub flag | `prerelease: true`, `make_latest: false` |

The tag is **immutable** and tied to one commit. The `.spl` filename reflects
`package/app.manifest` at build time (may match the current stable version until the
next version bump).

Release body includes:

- build tag
- full commit SHA
- app version from `package/app.manifest`

## Retention

| Stream | Retention |
|--------|-----------|
| Stable `v*` releases | Permanent — never auto-deleted |
| `build-*` prereleases | **10 most recent** on `main`; older tags/releases pruned automatically after each new prerelease |
| CI workflow artifacts | 30 days (GitHub Actions artifact retention) |

Pruning runs in CI immediately after publishing a new prerelease. Stable tags are never
touched.

## Installing a prerelease (lab only)

1. Open [GitHub Releases](https://github.com/dd-Splunk/TA-MQTT/releases).
2. Find the desired `build-<sha>` prerelease (newest listed first among prereleases).
3. Download `TA-MQTT-*.spl` and install on a **non-production** Splunk instance.

Do not reference prerelease tags in runbooks, customer docs, or Splunkbase listings.

## Stable vs prerelease

| | Prerelease `build-*` | Stable `vX.Y.Z` |
|--|----------------------|------------------|
| Trigger | Every `main` push | Annotated tag `v*` on `main` |
| Supported | No | Yes (see `SECURITY.md`) |
| Checksum file | No | Yes (`*.spl.sha256`) |
| `make_latest` on GitHub | false | true |

## Manual maintenance

Automatic pruning normally keeps the catalog at 10 prereleases. To list or delete
manually:

```bash
# List prerelease tags (newest first)
gh api repos/dd-Splunk/TA-MQTT/releases --paginate \
  --jq '.[] | select(.tag_name|startswith("build-")) | [.created_at,.tag_name]|@tsv' \
  | sort -r

# Delete one prerelease and its tag
gh release delete build-<sha> --repo dd-Splunk/TA-MQTT --yes --cleanup-tag
```

Never delete `v*` stable releases unless correcting a mistaken publish.
