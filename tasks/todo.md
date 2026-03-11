# TA-MQTT — Project Tasks

## Phase 1 — Initial scaffold ✅

- [x] globalConfig.json — MQTT Brokers configuration tab + MQTT Subscriber input
- [x] package/app.manifest
- [x] package/bin/mqtt_subscriber.py (entry point)
- [x] package/bin/import_declare_test.py (sys.path bootstrap)
- [x] package/bin/input_module/mqtt_subscriber.py (core logic)
- [x] package/default/app.conf
- [x] package/default/inputs.conf
- [x] package/default/props.conf
- [x] package/default/transforms.conf
- [x] package/default/ta_mqtt_settings.conf
- [x] package/lib/requirements.txt (paho-mqtt==1.6.1)
- [x] package/metadata/default.meta
- [x] additional_packaging.py (pip hook)
- [x] requirements-build.txt
- [x] README.md

## Phase 2 — Build & install

- [ ] Run `pip install -r requirements-build.txt` in a virtual env
- [ ] Run `ucc-gen build` from the repo root
- [ ] Copy/sideload `output/TA-MQTT/` to `$SPLUNK_HOME/etc/apps/`
- [ ] Restart Splunk: `splunk restart`
- [ ] Confirm UI loads at Settings → Data inputs → MQTT Subscriber

## Phase 3 — First broker test

- [ ] Navigate to Apps → MQTT Broker Add-on → Configuration → MQTT Brokers
- [ ] Add a broker (e.g. test.mosquitto.org, port 1883, anonymous)
- [ ] Navigate to Inputs → New Input → MQTT Subscriber
- [ ] Subscribe to topic `#`, index `main`
- [ ] Run search: `index=main sourcetype="mqtt:message"` — should see events

## Phase 4 — TLS / mTLS test

- [ ] Add a TLS broker: enable TLS, set port 8883
- [ ] Test with `skip_verify=true` against a broker with self-signed cert
- [ ] Test with custom CA cert (paste PEM into CA Certificate field)
- [ ] Test full mTLS: paste client cert + client key
- [ ] Verify no cert temp-files leak on disk after reconnect

## Phase 5 — Production hardening

- [ ] Add Splunk alert for `index=_internal sourcetype=splunkd ERROR ta-mqtt`
- [ ] Review queue backpressure behaviour under high-throughput topics
- [ ] Consider extracting payload JSON sub-fields with a custom props.conf
- [ ] Publish to Splunkbase (optional)

## Phase 6 — JMeter migration

- [x] Stand up repo-local JMeter starter assets using the EMQX/XMeter MQTT plugin
- [x] Validate JMeter publish load against the local Mosquitto service in `compose.yml`
- [x] Add a fixed sustained-load JMeter scenario alongside the smoke plan
- [x] Reconcile sustained-run JMeter publish counts with TA runtime summaries in Splunk
- [x] Add dedicated JMeter plan templates for TLS and mTLS publisher validation
- [ ] Match Python load-generator coverage for QoS, auth, TLS, and mTLS
- [ ] Decide whether to automate the JMeter path outside the current add-on CI pipeline
- [ ] Remove `tools/mqtt_load_test.py` only after documented parity and contributor usability are confirmed
