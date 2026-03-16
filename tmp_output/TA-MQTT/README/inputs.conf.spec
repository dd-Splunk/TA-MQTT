[mqtt_subscriber://<name>]
batch_mode = This input uses buffered HEC batch egress (always enabled). (Default: 1)
broker = Select a broker connection defined on the Configuration page.
hec_batch_max_bytes = Flush when buffered HEC payload bytes reach this threshold. (Default: 1048576)
hec_batch_max_events = Flush when this many events are buffered in hec_batch mode. (Default: 500)
hec_endpoint = HTTP Event Collector endpoint used when Batch Output Mode is set to HEC batch writer. (Default: https://localhost:8088/services/collector/event)
hec_flush_interval_ms = Flush interval used in hec_batch mode when event and byte thresholds are not reached. (Default: 250)
hec_retry_backoff_ms = Initial retry delay for HEC failures. The delay doubles on each subsequent retry. (Default: 200)
hec_retry_max_attempts = Retry attempts for failed HEC POST operations before dropping the batch. (Default: 5)
hec_token = Auto-generated per-input HEC token. Hidden on create/edit forms and shown read-only in the expanded input details.
hec_verify_tls = Verify the HEC server TLS certificate. Disable only for self-signed development endpoints. (Default: true)
index = (Default: default)
interval = How long (in seconds) to wait before attempting to reconnect after an unexpected disconnection. (Default: 30)
mqtt_client_id = Optional static MQTT client ID. Leave as AUTO (or empty) to auto-generate a unique ID per input stanza. Must be unique across all clients connected to the broker. (Default: AUTO)
qos = MQTT delivery guarantee. QoS 0 = fire-and-forget, QoS 1 = at least once, QoS 2 = exactly once. (Default: 0)
sourcetype = Splunk sourcetype applied to every MQTT message event. (Default: mqtt:message)
topic = MQTT topic filter. Use '#' to capture all topics, '+' as a single-level wildcard (e.g. 'sensors/+/temperature'). (Default: #)
