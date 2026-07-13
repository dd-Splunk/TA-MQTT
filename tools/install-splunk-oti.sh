#!/usr/bin/env bash
# Install Splunk OT Intelligence (Splunkbase app 5180) into the running Compose Splunk container.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

SPLUNK_USER="${SPLUNK_USER:-admin}"
SPLUNK_PASSWORD="${SPLUNK_PASSWORD:?Set SPLUNK_PASSWORD in .env}"
OTI_APP_ID="${OTI_APP_ID:-5180}"
OTI_VERSION="${OTI_VERSION:-4.13.2}"
OTI_URL="${SPLUNK_OTI_APPS_URL:-https://splunkbase.splunk.com/app/${OTI_APP_ID}/release/${OTI_VERSION}/download}"
LOCAL_TGZ="${ROOT}/tools/splunk-apps/splunk-ot-intelligence-${OTI_VERSION}.tgz"
CONTAINER_TGZ="/tmp/splunk-apps/splunk-ot-intelligence-${OTI_VERSION}.tgz"

splunkbase_token_from_login() {
  local username="$1"
  local password="$2"
  local response http_code body token

  response="$(
    curl -sS -w $'\n%{http_code}' -X POST 'https://splunkbase.splunk.com/api/account:login/' \
      --data-urlencode "username=${username}" \
      --data-urlencode "password=${password}"
  )"
  http_code="${response##*$'\n'}"
  body="${response%$'\n'*}"

  if [[ "${http_code}" != "200" ]]; then
    echo "Splunkbase login failed (HTTP ${http_code})." >&2
    echo "Verify SPLUNKBASE_USERNAME / SPLUNKBASE_PASSWORD in .env (splunk.com account)." >&2
    echo "Accounts with MFA may need a manual .tgz in tools/splunk-apps/ or SPLUNKBASE_AUTH_TOKEN." >&2
    return 1
  fi

  token="$(
    printf '%s' "${body}" | python3 -c 'import re, sys; m = re.search(r"<id>(.*?)</id>", sys.stdin.read(), re.I); print(m.group(1) if m else "")'
  )"
  if [[ -z "${token}" ]]; then
    echo "Splunkbase login returned HTTP 200 but no <id> session token." >&2
    echo "Response preview:" >&2
    printf '%s\n' "${body}" | head -c 200 >&2
    echo >&2
    return 1
  fi

  printf '%s' "${token}"
}

splunkbase_download_with_token() {
  local token="$1"
  local output="$2"
  curl -fsSL \
    -H "X-Auth-Token: ${token}" \
    -o "${output}" \
    "https://api.splunkbase.splunk.com/api/v2/apps/${OTI_APP_ID}/releases/${OTI_VERSION}/download/?origin=sb"
}

splunkbase_download_with_cookies() {
  local sid="$1"
  local ssoid="$2"
  local output="$3"
  curl -fsSL \
    --cookie "sid=${sid}; SSOID=${ssoid}" \
    -L -o "${output}" \
    "${OTI_URL}"
}

install_via_splunk_rest() {
  local token="$1"
  local http_code

  http_code="$(
    docker compose exec -T -u splunk splunk curl -sk -w '%{http_code}' -o /dev/null \
      -u "${SPLUNK_USER}:${SPLUNK_PASSWORD}" \
      --data-urlencode "name=${OTI_URL}" \
      --data-urlencode "update=true" \
      --data-urlencode "filename=true" \
      --data-urlencode "auth=${token}" \
      "https://127.0.0.1:8089/services/apps/local"
  )"

  if [[ "${http_code}" != "200" && "${http_code}" != "201" ]]; then
    echo "Splunk REST app install failed (HTTP ${http_code})." >&2
    return 1
  fi
}

if docker compose exec -T -u splunk splunk bash -lc 'ls /opt/splunk/etc/apps' 2>/dev/null \
  | grep -qiE 'edge_hub|ot_intelligence|splunk_ot'; then
  echo "OT Intelligence already installed under /opt/splunk/etc/apps."
  exit 0
fi

if [[ -f "${LOCAL_TGZ}" ]]; then
  echo "Installing OT Intelligence from local package: ${LOCAL_TGZ}"
  docker compose exec -T -u splunk splunk /opt/splunk/bin/splunk install app "${CONTAINER_TGZ}" -update 1 -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}"
else
  token="${SPLUNKBASE_AUTH_TOKEN:-}"

  if [[ -z "${token}" && -n "${SPLUNKBASE_USERNAME:-}" && -n "${SPLUNKBASE_PASSWORD:-}" ]]; then
    echo "Authenticating to Splunkbase..."
    token="$(splunkbase_token_from_login "${SPLUNKBASE_USERNAME}" "${SPLUNKBASE_PASSWORD}")"
  fi

  if [[ -n "${token}" ]]; then
    echo "Installing OT Intelligence ${OTI_VERSION} via Splunk REST (Splunkbase token)..."
    if ! install_via_splunk_rest "${token}"; then
      echo "REST install failed; downloading package with Splunkbase token..."
      mkdir -p "${ROOT}/tools/splunk-apps"
      splunkbase_download_with_token "${token}" "${LOCAL_TGZ}"
      docker compose exec -T -u splunk splunk /opt/splunk/bin/splunk install app "${CONTAINER_TGZ}" -update 1 -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}"
    fi
  elif [[ -n "${SPLUNKBASE_SID:-}" && -n "${SPLUNKBASE_SSOID:-}" ]]; then
    echo "Downloading OT Intelligence ${OTI_VERSION} with Splunkbase session cookies..."
    mkdir -p "${ROOT}/tools/splunk-apps"
    splunkbase_download_with_cookies "${SPLUNKBASE_SID}" "${SPLUNKBASE_SSOID}" "${LOCAL_TGZ}"
    docker compose exec -T -u splunk splunk /opt/splunk/bin/splunk install app "${CONTAINER_TGZ}" -update 1 -auth "${SPLUNK_USER}:${SPLUNK_PASSWORD}"
  else
    echo "Missing Splunkbase authentication." >&2
    echo "Set one of the following in .env:" >&2
    echo "  SPLUNKBASE_USERNAME + SPLUNKBASE_PASSWORD" >&2
    echo "  SPLUNKBASE_AUTH_TOKEN (from api/account:login <id> value)" >&2
    echo "  SPLUNKBASE_SID + SPLUNKBASE_SSOID (browser cookies after splunkbase login)" >&2
    echo "Or place: ${LOCAL_TGZ}" >&2
    exit 1
  fi
fi

docker compose exec -T -u splunk splunk /opt/splunk/bin/splunk restart
echo "OT Intelligence install complete."
