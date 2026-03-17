# MQTT TLS/mTLS Test Evidence Matrix

Execution branch: `testplan/tls-mtls-broker-validation`
Date: 2026-03-17
Tester: Copilot + dodessy
Environment: Docker local stack (`mosquitto`, `splunk`)

| ID | Scenario | Broker Stanza | Input Stanza | Marker | Expected | Observed | Search Result | Pass/Fail | Notes |
|---|---|---|---|---|---|---|---|---|---|
| C1 | TLS positive (server cert validate) | mc_tls | tls_server_validate | tls-positive-002-local | Connect + ingest | Connected to `mosquitto:8883`, marker indexed | `search index=* "tls-positive-002-local"` returned event with source `mqtt://mosquitto:8883/home/devices/lab1/telemetry` | Pass | Local Mosquitto TLS listener (`8883`) validated |
| C2 | mTLS positive (server + client cert) | mc_mtls | tls_client_validate | mtls-positive-001-local | Connect + ingest | Input process starts, then exits with `ssl.SSLError: [SSL] PEM lib (_ssl.c:4127)` before connect | No marker found | Blocked | `client_key` handling for multiline encrypted textarea appears incompatible with runtime PEM loading |
| D1 | TLS negative: wrong CA | mc_tls | tls_server_validate | tls-negative-wrong-ca-001 | Reject + no ingest |  |  |  |  |
| D2 | TLS negative: hostname mismatch | mc_tls | tls_server_validate | tls-negative-hostname-001 | Reject + no ingest |  |  |  |  |
| E1 | mTLS negative: missing client cert/key | mc_mtls | tls_client_validate | mtls-negative-missing-client-cert-001 | Reject + no ingest |  |  |  |  |
| E2 | mTLS negative: bad client key pair | mc_mtls | tls_client_validate | mtls-negative-bad-client-key-001 | Reject + no ingest |  |  |  |  |

## Splunk search template

Use this base search and replace marker value:

`search index=* "<marker-value>" | head 5`

## Runtime log evidence

Capture relevant lines from:

`/opt/splunk/var/log/splunk/ta_mqtt_mqtt_subscriber.log`

Minimum evidence fields:

- starting input stanza
- broker host:port
- connect/subscribe success OR TLS/auth failure
- batch send outcome for positive cases
