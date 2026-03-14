# R1 Smoke Validation — 2026-03-14

## Scope

Quick functional smoke validation of the new egress mode switch in:

- `package/bin/input_module/mqtt_subscriber.py`

Validated paths:

1. `output_mode=modinput_single_event`
2. `output_mode=hec_batch`
3. Dockerized Splunk HEC endpoint availability and indexing check

## Test Method

Validation was executed in two stages:

1. Local Python harness checks for writer behavior.
2. Docker-backed Splunk HEC checks for real ingest/index verification.

A strict sequencing rule was enforced for the latest run:

- `ucc-gen build` had to succeed before smoke tests.

Harness file:

- `artifacts/r1_smoke_test.py`

What the harness does:

- Loads the module and builds writers via `_build_egress_writer(...)`.
- Uses fake helper/event-writer objects for single-event path.
- Starts an in-process local HTTP server to emulate HEC endpoint for batch path.
- Sends sample events and asserts key outputs from captured request payload and logs.

## Results

Execution output:

- `single_event_events_written= 1`
- `hec_received_auth= Splunk token-123`
- `hec_lines= 2`
- `hec_first_has_event= True`
- `hec_first_index= main`
- `helper_error_logs= 0`

Interpretation:

- Single-event writer path still writes events correctly.
- Batch writer sends newline-delimited HEC events.
- Authorization header is correctly set.
- Event envelope includes `event` object and expected metadata (`index=main`).
- No error logs produced in the smoke scenario.

## Docker Retry Results

Environment checks:

- `docker compose up -d` started both containers (`splunk`, `mosquitto`).
- Splunk container health reported `healthy`.

Real HEC checks performed:

1. Created HEC token `ta_mqtt_r1` via Splunk Management API (`https://localhost:8089`).
2. Sent event to HEC from within the Splunk container (`https://localhost:8088/services/collector/event`).
3. Queried indexing result with REST search export.

Observed outputs:

- HEC response: `{"text":"Success","code":0}`
- Verification search: `search index=main "r1_docker_hec_smoke" | stats count` -> `count=1`

Interpretation:

- Real Dockerized Splunk HEC ingestion path is functional.
- The retry objective (Docker-backed validation) is achieved for the HEC path.

## Rebuild-First Validation (post-build)

Rebuild cycle executed successfully before smoke tests:

1. `docker compose stop splunk`
2. `rm -rf output/TA-MQTT`
3. `ucc-gen build --python-binary-name ... --ta-version 1.2.0`

Build result:

- `globalConfig file is valid`
- Build completed with generated app artifacts and input code

Post-build smoke checks:

- `artifacts/r1_smoke_test.py` remained green:
	- `single_event_events_written= 1`
	- `hec_lines= 2`
	- `helper_error_logs= 0`
- Real HEC ingest with new token (`ta_mqtt_r1_postbuild`) succeeded:
	- HEC response: `{"text":"Success","code":0}`
	- Search verification: `search index=main "r1_postbuild_smoke" | stats count` -> `count=1`

Conclusion:

- Required order **build success -> smoke test** is satisfied.

## Limitations

Not covered by this smoke validation:

- High-load/soak behavior.
- Retry/backoff behavior against failing HEC responses.
- R1 UI fields were temporarily removed from `globalConfig.json` inputs to keep UCC build compatibility while validating runtime behavior.

## Next Validation Steps

1. Reintroduce R1 UI fields in a UCC-schema-compatible way without breaking `ucc-gen build`.
2. Add failure-path smoke cases (HTTP 5xx / HEC code != 0 / timeout).
3. Execute comparative throughput runs at identical publish rates.
