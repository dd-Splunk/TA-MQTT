# TA-MQTT — MQTT Broker Add-on for Splunk

Multi-broker MQTT subscriber add-on built with the
[Splunk UCC Framework](https://splunk.github.io/addonfactory-ucc-generator/).

## Features

| Capability | Detail |
|---|---|
| **Multiple brokers** | Define unlimited named broker connections on the Configuration page and reference them from any number of inputs. |
| **Anonymous access** | Leave username/password empty — the add-on connects without credentials. |
| **Port selection** | Configurable per broker (default 1883 for plain TCP, 8883 for TLS). |
| **Plain TLS** | Enable TLS and optionally provide a custom CA certificate (PEM). |
| **Skip TLS verify** | Connect to an mTLS-enabled broker over TLS without verifying its certificate — useful for self-signed or internal CAs. |
| **mTLS** | Paste a client certificate and encrypted client private key to authenticate with a mutual-TLS broker. |
| **MQTT QoS 0/1/2** | Per-input quality-of-service selection. |
| **Wildcard topics** | Subscribe to `#` (all), `+` (single level), or any filter string. |
| **JSON events** | Every message is forwarded as a structured JSON event with `broker`, `host`, `port`, `topic`, `qos`, `retain`, and `payload` fields. |

## Prerequisites

- Python 3.7+
- Splunk Enterprise or Splunk Cloud 8.x / 9.x
- `splunk-add-on-ucc-framework >= 5.35` (build only)

## Build

```bash
# 1. Create + use a virtualenv (recommended on macOS)
python3 -m venv .venv
source .venv/bin/activate

# 2. Install build tools
python -m pip install -r requirements-build.txt

# 3. Generate the add-on
./.venv/bin/ucc-gen build --python-binary-name ./.venv/bin/python --ta-version 1.0.0

# 4. The installable add-on is in:
ls output/TA-MQTT/
```

## Install

```bash
cp -r output/TA-MQTT/ $SPLUNK_HOME/etc/apps/
splunk restart
```

Or use Splunk Web: **Apps → Manage Apps → Install app from file**.

## Configuration

### 1. Define a broker

Navigate to **Apps → MQTT Broker Add-on → Configuration → MQTT Brokers → Add**.

| Field | Required | Notes |
|---|---|---|
| Broker Name | ✅ | Unique alphanumeric identifier |
| Host | ✅ | Hostname or IP |
| Port | ✅ | Default: 1883 |
| Username | — | Empty = anonymous |
| Password | — | Stored encrypted |
| Enable TLS/SSL | — | Activates TLS transport |
| Skip TLS Cert Verification | — | Bypass server cert check (⚠️ insecure) |
| CA Certificate (PEM) | — | Custom CA PEM string |
| Client Certificate (PEM) | — | mTLS client cert PEM string |
| Client Private Key (PEM) | — | mTLS client key PEM string (encrypted at rest) |

### 2. Create an input

Navigate to **Apps → MQTT Broker Add-on → Inputs → New Input → MQTT Subscriber**.

| Field | Default | Notes |
|---|---|---|
| Input Name | — | Unique stanza name |
| MQTT Broker | — | Select a configured broker |
| Topic Filter | `#` | MQTT topic or wildcard |
| QoS | `0` | 0 / 1 / 2 |
| MQTT Client ID | auto | Leave empty to auto-generate |
| Index | `default` | Target Splunk index |
| Sourcetype | `mqtt:message` | Applied to every event |
| Reconnect Interval | `30` | Seconds between reconnect attempts |

## Event Format

Every MQTT message produces one JSON event:

```json
{
  "broker":  "my_broker",
  "host":    "broker.example.com",
  "port":    8883,
  "topic":   "sensors/room1/temperature",
  "qos":     1,
  "retain":  false,
  "payload": "22.5"
}
```

Search example:

```spl
index=main sourcetype="mqtt:message" topic="sensors/*"
| spath payload
| timechart avg(payload) by topic
```

## Authentication Scenarios

### Anonymous

Leave username and password empty. Disable TLS (or enable if the broker
requires encrypted anonymous connections).

### Username / Password

Fill in username and password. TLS is optional but recommended to avoid
transmitting credentials in plaintext.

### Plain TLS (server-side only)

Enable TLS. Optionally paste the broker's CA certificate. Leave client cert
and key empty.

### Skip TLS Verification

Enable TLS, check **Skip TLS Certificate Verification**. The connection is
encrypted but the broker's certificate is not validated. Use this when the
broker has a self-signed certificate and you cannot install the CA.

### Mutual TLS (mTLS)

Enable TLS. Paste the CA cert, the client certificate, and the client private
key. The broker authenticates the Splunk add-on by its certificate.

## Project Structure

```
TA-MQTT/
├── globalConfig.json                   # UCC UI definition
├── additional_packaging.py             # pip install hook
├── requirements-build.txt              # ucc-gen dependency
├── package/
│   ├── app.manifest
│   ├── bin/
│   │   ├── import_declare_test.py      # sys.path bootstrap
│   │   ├── mqtt_subscriber.py          # UCC entry-point wrapper
│   │   └── input_module/
│   │       └── mqtt_subscriber.py      # ← core MQTT logic (edit here)
│   ├── default/
│   │   ├── app.conf
│   │   ├── inputs.conf
│   │   ├── props.conf
│   │   ├── transforms.conf
│   │   └── ta_mqtt_settings.conf
│   ├── lib/
│   │   └── requirements.txt            # paho-mqtt==1.6.1
│   └── metadata/
│       └── default.meta
└── tasks/
    ├── todo.md
    └── lessons.md
```

## License

Apache 2.0
