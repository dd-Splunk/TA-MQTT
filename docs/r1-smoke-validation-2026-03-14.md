# R1 Smoke Validation — 2026-03-14

## Scope

Quick functional smoke validation of the new per-input batch-mode switch in:

- `package/bin/input_module/mqtt_subscriber.py`

Validated paths:

1. `batch_mode=0`
2. `batch_mode=1`
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

## Post-Normalization Rerun (2026-03-16)

After the per-input schema normalization (`batch_mode` + per-input HEC fields), the rebuild and smoke sequence was rerun.

Execution order:

1. `ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.2.0`
2. `python artifacts/r1_smoke_test.py`
3. Docker-backed HEC ingest/index verification via Splunk container

Observed outputs:

- Build: `globalConfig file is valid` and app artifacts regenerated successfully.
- Local harness: all scenarios passed (happy path, 500 retry/drop, HEC code!=0 retry/drop, time-based flush).
- Docker-backed verification:
  - `HEC_RESPONSE={"text":"Success","code":0}`
  - `SEARCH_MARKER=r1_postnorm_smoke_1773665288`
  - `SEARCH_COUNT=1`

Interpretation:

- The required rebuild-first flow has now been reconfirmed with the normalized configuration model.
- Dockerized end-to-end HEC ingest and indexing remain functional post-normalization.

### Fresh rebuild rerun (2026-03-16)

After a full clean rebuild (`rm -rf output/TA-MQTT` + `ucc-gen build`), Docker-backed smoke was rerun.

Observed outputs:

- `TOKEN_NAME=ta_mqtt_r1_freshbuild_1773666616`
- `HEC_RESPONSE={"text":"Success","code":0}`
- `SEARCH_MARKER=r1_freshbuild_smoke_1773666617`
- `SEARCH_COUNT=1`
- `SEARCH_FOUND=1`

Interpretation:

- Freshly generated output artifacts preserve end-to-end HEC ingest and indexing behavior.

## Performance Retest — 5000 msgs/s for 60s (2026-03-16)

This retest was run after resolving the configuration-page breakage and rebuilding the TA.

Run setup:

- Publisher script: `tools/mqtt_load_test.py`
- Target rate: `5000 msgs/s`
- Duration: `60s`
- Clients: `20`
- Topic: `home/devices/load5000r2/telemetry`
- Artifact log: `artifacts/loadtest_5000ms_60s_20260316_145718.log`

Key results:

- Published: `300442`
- Publish errors: `0`
- Connect errors: `0`
- Disconnects: `0`
- Final publisher throughput: `4917.16 msgs/s` over `61.1s`
- Indexed count for test topic: `300442`
- End-to-end indexing coverage: `100.00%`
- Indexed EPS over 60s: `5007.37`

Subscriber-side runtime summary rollup (`index=_internal`):

- `recv_total=300451`
- `written_total=300451`
- `dropped_total=0`

Important test-context note:

- An earlier 5000 msgs/s run showed `0` indexed because the active input broker was pointing to an external host (`192.168.1.21`) instead of local `mosquitto`.
- After repointing broker stanza `mc` to `mosquitto:1883` and restarting Splunk, the retest above produced full end-to-end coverage.

## Next Validation Steps

1. Add explicit failure-path coverage for timeout/network interruption (in addition to current 500 and HEC code!=0 harness checks).
2. Execute comparative throughput runs at 1000/2000/5000 msgs/s with the same local broker target and capture percentile lag from runtime summaries.
