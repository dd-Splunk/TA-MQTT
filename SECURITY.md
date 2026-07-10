# Security Policy

## Supported Versions

| Version | Supported |
| ------- | --------- |
| 2.2.x   | Yes       |
| < 2.2   | No        |

Security fixes are delivered in patch or minor releases on the `main` branch and published as tagged stable releases (`v*`).

## Reporting a Vulnerability

**Please do not open public GitHub issues for security vulnerabilities.**

Report security issues privately using one of the following channels:

1. **GitHub Security Advisories (preferred):**  
   https://github.com/dd-Splunk/TA-MQTT/security/advisories/new

2. **Email:**  
   dodessy@cisco.com  
   Subject: `[TA-MQTT Security]`

Include:

- Affected version(s)
- Steps to reproduce
- Impact assessment (confidentiality, integrity, availability)
- Proof of concept, if available

### What to Expect

| Stage | Target timeline |
| ----- | ---------------- |
| Acknowledgement | 2 business days |
| Initial triage | 5 business days |
| Fix or mitigation plan | 15 business days (severity-dependent) |
| Coordinated disclosure | After fix is available on `main` and in a stable release |

We may request additional information and will keep reporters informed of status.

## Scope

In scope:

- `package/` add-on source code shipped in releases
- GitHub Actions workflows and release artifacts (`.spl`)
- Credential handling (MQTT passwords, TLS keys, HEC tokens)
- TLS/mTLS configuration paths

Out of scope:

- Splunk platform vulnerabilities (report to Splunk)
- Third-party MQTT broker misconfiguration
- Local development compose stacks unless they introduce a defect in the add-on itself

## Secure Usage Notes

- Do not enable `skip_verify` or disable HEC TLS verification in production.
- Store broker credentials and client private keys in Splunk credential storage; never commit them to source control.
- Install add-ons only from official [GitHub Releases](https://github.com/dd-Splunk/TA-MQTT/releases) and verify the published SHA-256 digest when provided.

## Security Hardening in This Repository

- AppInspect validation blocks failing builds in CI
- Gitleaks secret scanning on pull requests
- Dependabot monitoring for Python and GitHub Actions dependencies
- GitHub Actions pinned to immutable commit SHAs
