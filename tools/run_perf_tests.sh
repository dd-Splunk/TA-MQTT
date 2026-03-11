#!/bin/zsh
# Sequential performance test runner: 1000/1500/2000 mps
# Results written to artifacts/perf-results.txt

export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
export JAVA_HOME="/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home"

SPLUNK_URL="https://localhost:8089"
SPLUNK_AUTH="admin:Splunk4Me!"
OUT="artifacts/perf-results.txt"

splunk_query() {
  local label=$1 earliest=$2 latest=$3

  local SEARCH="search index=default sourcetype=\"mqtt:message\" earliest=${earliest} latest=${latest} | stats count as total_events, min(_time) as first_event, max(_time) as last_event | eval duration_s=round(last_event-first_event,1) | eval avg_eps=round(total_events/duration_s,1) | table total_events duration_s avg_eps first_event last_event"

  local SID
  SID=$(curl -sk -u "$SPLUNK_AUTH" "$SPLUNK_URL/services/search/jobs" \
    --data-urlencode "search=$SEARCH" \
    -d "exec_mode=blocking" \
    -d "timeout=120" \
    | grep -oP '(?<=<sid>)[^<]+' | head -1)

  echo "[$label] Splunk SID: $SID"

  local RESULT
  RESULT=$(curl -sk -u "$SPLUNK_AUTH" \
    "$SPLUNK_URL/services/search/jobs/$SID/results?output_mode=json&count=5")
  echo "$RESULT"
}

splunk_timechart() {
  local label=$1 earliest=$2 latest=$3

  local SEARCH="search index=default sourcetype=\"mqtt:message\" earliest=${earliest} latest=${latest} | timechart span=5s count as events_per_5s | eval eps=round(events_per_5s/5,1)"

  local SID
  SID=$(curl -sk -u "$SPLUNK_AUTH" "$SPLUNK_URL/services/search/jobs" \
    --data-urlencode "search=$SEARCH" \
    -d "exec_mode=blocking" \
    -d "timeout=120" \
    | grep -oP '(?<=<sid>)[^<]+' | head -1)

  curl -sk -u "$SPLUNK_AUTH" \
    "$SPLUNK_URL/services/search/jobs/$SID/results?output_mode=json&count=100"
}

run_test() {
  local label=$1
  local plan="tools/jmeter/mqtt-publisher-${label}.jmx"

  echo ""
  echo "########################################"
  echo "# TEST: $label"
  echo "# START: $(date)"
  echo "########################################"

  local T_START T_END
  T_START=$(date +%s)

  /opt/homebrew/bin/jmeter -n \
    -t "$plan" \
    -q tools/jmeter/local.properties.example \
    -Jmqtt.host=localhost \
    -Jmqtt.port=1883 \
    -Jmqtt.topic=perf/ta-mqtt/test \
    -Jmqtt.clients=8 \
    -Jmqtt.loops=7500 \
    -l "artifacts/jmeter-mqtt-${label}.jtl" \
    2>&1 | tee "artifacts/jmeter-${label}.log"

  T_END=$(date +%s)
  local DURATION=$(( T_END - T_START ))

  echo ""
  echo "[$label] JMeter finished. Wall time: ${DURATION}s  ($(date))"
  echo "[$label] Waiting 45s for Splunk ingestion..."
  sleep 45

  local Q_EARLIEST=$(( T_START - 10 ))
  local Q_LATEST=$(( T_END + 90 ))

  echo ""
  echo "[$label] === Splunk aggregate stats ==="
  splunk_query "$label" "$Q_EARLIEST" "$Q_LATEST"

  echo ""
  echo "[$label] === Splunk 5-second timechart ==="
  splunk_timechart "$label" "$Q_EARLIEST" "$Q_LATEST"

  # Persist summary line
  local JTL_SUMMARY
  JTL_SUMMARY=$(grep -E "^summary" "artifacts/jmeter-${label}.log" 2>/dev/null | tail -1)
  echo "[$label] JTL: $JTL_SUMMARY" >> "$OUT"
}

echo "=== TA-MQTT JMeter Performance Run: $(date) ===" > "$OUT"

run_test "1000mps" 2>&1 | tee -a "$OUT"
run_test "1500mps" 2>&1 | tee -a "$OUT"
run_test "2000mps" 2>&1 | tee -a "$OUT"

echo "" >> "$OUT"
echo "=== ALL TESTS COMPLETE: $(date) ===" >> "$OUT"
echo "=== ALL TESTS COMPLETE ==="
