#!/bin/zsh
set -euo pipefail

CERT_DIR="$(cd "$(dirname "$0")/certs/mosquitto" && pwd)"

CA_KEY="$CERT_DIR/local-ca.key"
CA_CRT="$CERT_DIR/local-ca.crt"
SERVER_KEY="$CERT_DIR/local-server.key"
SERVER_CSR="$CERT_DIR/local-server.csr"
SERVER_EXT="$CERT_DIR/local-server.ext"
SERVER_CRT="$CERT_DIR/local-server.crt"
CLIENT_KEY="$CERT_DIR/local-client.key"
CLIENT_CSR="$CERT_DIR/local-client.csr"
CLIENT_EXT="$CERT_DIR/local-client.ext"
CLIENT_CRT="$CERT_DIR/local-client.crt"

mkdir -p "$CERT_DIR"

openssl genrsa -out "$CA_KEY" 2048 >/dev/null 2>&1
openssl req -x509 -new -nodes \
  -key "$CA_KEY" \
  -sha256 -days 3650 \
  -subj "/CN=TA-MQTT Local CA" \
  -out "$CA_CRT" >/dev/null 2>&1

openssl genrsa -out "$SERVER_KEY" 2048 >/dev/null 2>&1
openssl req -new \
  -key "$SERVER_KEY" \
  -subj "/CN=localhost" \
  -out "$SERVER_CSR" >/dev/null 2>&1
printf 'subjectAltName=DNS:localhost,DNS:mosquitto,IP:127.0.0.1\n' > "$SERVER_EXT"
openssl x509 -req \
  -in "$SERVER_CSR" \
  -CA "$CA_CRT" \
  -CAkey "$CA_KEY" \
  -CAcreateserial \
  -out "$SERVER_CRT" \
  -days 3650 -sha256 \
  -extfile "$SERVER_EXT" >/dev/null 2>&1

openssl genrsa -out "$CLIENT_KEY" 2048 >/dev/null 2>&1
openssl req -new \
  -key "$CLIENT_KEY" \
  -subj "/CN=ta-mqtt-client" \
  -out "$CLIENT_CSR" >/dev/null 2>&1
printf 'extendedKeyUsage=clientAuth\n' > "$CLIENT_EXT"
openssl x509 -req \
  -in "$CLIENT_CSR" \
  -CA "$CA_CRT" \
  -CAkey "$CA_KEY" \
  -CAcreateserial \
  -out "$CLIENT_CRT" \
  -days 3650 -sha256 \
  -extfile "$CLIENT_EXT" >/dev/null 2>&1

chmod 600 "$CA_KEY" "$SERVER_KEY" "$CLIENT_KEY"
chmod 644 "$CA_CRT" "$SERVER_CRT" "$CLIENT_CRT"

echo "Regenerated Mosquitto TLS certs in: $CERT_DIR"
