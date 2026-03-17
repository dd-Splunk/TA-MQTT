# MQTT TLS/mTLS Validation Plan

Branch scope: `testplan/tls-mtls-broker-validation`

## Objective

Validate that TA-MQTT can connect to an MQTT broker over TLS with:

1. Server certificate validation enabled
2. Mutual TLS enabled (server + client certificate)

Also validate failure behavior when certificates are invalid or missing.

## Preconditions

- Splunk + TA-MQTT running
- Broker reachable at `192.168.1.21`
- TLS listener available on broker (typically `8883`)
- Test CA, broker cert/key, and client cert/key prepared
- Admin credentials for Splunk management API

## Test markers

Use unique payload markers for each scenario so ingestion checks are deterministic.

Recommended markers:

- `tls-positive-001`
- `tls-negative-wrong-ca-001`
- `tls-negative-hostname-001`
- `mtls-positive-001`
- `mtls-negative-missing-client-cert-001`
- `mtls-negative-bad-client-key-001`

## Phase A — Broker stanzas

Create two broker stanzas in TA-MQTT configuration:

### A1. TLS server-validated stanza

- name: `mc_tls`
- host: `192.168.1.21`
- port: `8883`
- use_tls: `1`
- skip_verify: `0`
- ca_cert: `<PEM CA certificate>`
- client_cert: empty
- client_key: empty

### A2. mTLS stanza

- name: `mc_mtls`
- host: `192.168.1.21`
- port: `8883`
- use_tls: `1`
- skip_verify: `0`
- ca_cert: `<PEM CA certificate>`
- client_cert: `<PEM client certificate>`
- client_key: `<PEM client key>`

## Phase B — Input stanzas

Create isolated input stanzas:

### B1. TLS input

- name: `tls_server_validate`
- broker: `mc_tls`
- topic: `home/devices/+/telemetry`
- batch_mode: `1`
- index: `main`
- sourcetype: `mqtt:message`

### B2. mTLS input

- name: `tls_client_validate`
- broker: `mc_mtls`
- topic: `home/devices/+/telemetry`
- batch_mode: `1`
- index: `main`
- sourcetype: `mqtt:message`

## Phase C — Positive tests

### C1. TLS positive

Publish to broker with marker `tls-positive-001`:

- topic: `home/devices/lab1/telemetry`
- expected: input `tls_server_validate` connects and event is indexed

Validate:

- Runtime log shows connect/subscribe success
- Splunk search finds marker

### C2. mTLS positive

Publish to broker with marker `mtls-positive-001` using valid client cert/key.

Validate:

- Runtime log shows connect/subscribe success for `tls_client_validate`
- Splunk search finds marker

## Phase D — Negative tests (TLS)

### D1. Wrong CA

Set `mc_tls.ca_cert` to a CA that did not issue the broker certificate.

Expected:

- TLS handshake fails
- Connection not established
- No indexed event for marker `tls-negative-wrong-ca-001`

### D2. Hostname mismatch

Connect by host that does not match broker cert SAN/CN while verification is enabled.

Expected:

- Connection rejected due to cert validation
- No indexed event for marker `tls-negative-hostname-001`

## Phase E — Negative tests (mTLS)

### E1. Missing client cert

Clear `client_cert` and `client_key` on `mc_mtls`.

Expected:

- Broker rejects client auth
- No indexed event for marker `mtls-negative-missing-client-cert-001`

### E2. Invalid client key pair

Use client certificate with non-matching private key.

Expected:

- TLS/auth failure before message flow
- No indexed event for marker `mtls-negative-bad-client-key-001`

## Optional control (non-production)

Set `skip_verify=1` on TLS stanza and re-test with untrusted server cert.

Expected:

- Connection may succeed
- Must be recorded as non-compliant for production

## Evidence to capture per test

- Broker stanza used
- Input stanza used
- Published marker value
- Result of search for marker
- Key runtime log lines from `ta_mqtt_mqtt_subscriber.log`
- Pass/Fail and notes

Use the template in `docs/test-evidence-mqtt-tls-mtls.md`.

## Exit criteria

- Both positive paths pass (`C1`, `C2`)
- All negative paths fail safely with no ingestion (`D1`, `D2`, `E1`, `E2`)
- Evidence recorded for all scenarios
- Recommended production settings documented:
  - `use_tls=1`
  - `skip_verify=0`
  - trusted `ca_cert`
  - client cert/key only where mTLS is required
