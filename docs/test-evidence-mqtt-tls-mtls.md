# MQTT TLS/mTLS Test Evidence Matrix

Execution branch: `testplan/tls-mtls-broker-validation`
Date:
Tester:
Environment:

| ID | Scenario | Broker Stanza | Input Stanza | Marker | Expected | Observed | Search Result | Pass/Fail | Notes |
|---|---|---|---|---|---|---|---|---|---|
| C1 | TLS positive (server cert validate) | mc_tls | tls_server_validate | tls-positive-001 | Connect + ingest |  |  |  |  |
| C2 | mTLS positive (server + client cert) | mc_mtls | tls_client_validate | mtls-positive-001 | Connect + ingest |  |  |  |  |
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
