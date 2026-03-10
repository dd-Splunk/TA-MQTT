"""
TA-MQTT  —  mqtt_subscriber input module
=========================================
UCC modular-input implementation.

Responsibilities
----------------
* validate_input()   : sanity-check the input stanza before Splunk saves it
* collect_events()   : connect to an MQTT broker and forward messages to Splunk

Authentication matrix
---------------------
| use_tls | skip_verify | ca_cert | client_cert + client_key | Result                     |
|---------|-------------|---------|--------------------------|----------------------------|
|    0    |      *      |    *    |             *            | Plain TCP (no TLS)         |
|    1    |      1      |    *    |             *            | TLS, no cert verification  |
|    1    |      0      |  empty  |           empty          | TLS, system CA store       |
|    1    |      0      |  set    |           empty          | TLS + custom CA            |
|    1    |      0      |  set?   |           set            | mTLS (client cert auth)    |

Anonymous access: leave username & password empty on the broker configuration.
"""

from __future__ import annotations

import json
import logging
import os
import queue
import ssl
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# paho-mqtt is installed into lib/ by ucc-gen (via lib/requirements.txt).
# The import_declare_test.py entry point adds lib/ to sys.path before this
# module is imported, so the bare import below is always safe.
# ---------------------------------------------------------------------------
import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)


# ───────────────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────────────

_TRUTHY = {"1", "true", "yes", "on"}


def _is_true(value: Any) -> bool:
    """Return True when a UCC checkbox / arbitrary value is logically true."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUTHY


def _get_broker_config(helper, broker_name: str) -> Dict[str, str]:
    """
    Retrieve a broker stanza from ``ta_mqtt_mqtt_broker.conf`` via the
    Splunk REST API (splunklib).  The session key is provided by the UCC
    helper context.
    """
    try:
        import splunklib.client as splunk_client  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "splunklib is not available.  "
            "Run 'ucc-gen build' to install dependencies."
        ) from exc

    mgmt_port = int(os.environ.get("SPLUNK_MGMT_PORT", "8089"))
    session_key = helper.context_meta.get("session_key", "")

    service = splunk_client.connect(
        host="localhost",
        port=mgmt_port,
        token=session_key,
        owner="nobody",
        app="TA-MQTT",
        scheme="https",
    )

    conf_name = "ta_mqtt_mqtt_broker"
    try:
        stanza = service.confs[conf_name][broker_name]
        content = dict(stanza.content)
        # Remove Splunk internal metadata keys
        for k in ("eai:acl", "eai:appName", "eai:userName"):
            content.pop(k, None)
        return content
    except KeyError:
        raise ValueError(
            f"Broker '{broker_name}' not found in {conf_name}.conf.  "
            "Please create it on the Configuration → MQTT Brokers page."
        )


class _TLSSetup:
    """
    Encapsulates TLS / mTLS configuration and certificate temp-file lifecycle.

    Usage::

        with _TLSSetup(broker_config) as tls:
            if tls.enabled:
                client.tls_set_context(tls.context)
    """

    def __init__(self, broker_config: Dict[str, str]) -> None:
        self.enabled: bool = _is_true(broker_config.get("use_tls", "0"))
        self.context: Optional[ssl.SSLContext] = None
        self._tmp_files: List[str] = []
        self._broker_config = broker_config

    def __enter__(self) -> "_TLSSetup":
        if self.enabled:
            self.context = self._build_context()
        return self

    def __exit__(self, *_) -> None:
        for path in self._tmp_files:
            try:
                os.unlink(path)
            except OSError:
                pass

    # ------------------------------------------------------------------
    def _write_tmp(self, content: str, suffix: str = ".pem") -> str:
        """Write *content* to a secure temp file and return its path."""
        fd, path = tempfile.mkstemp(suffix=suffix, prefix="ta_mqtt_")
        try:
            with os.fdopen(fd, "w") as fh:
                fh.write(content)
        except Exception:
            os.unlink(path)
            raise
        self._tmp_files.append(path)
        return path

    def _build_context(self) -> ssl.SSLContext:
        cfg = self._broker_config
        skip_verify = _is_true(cfg.get("skip_verify", "0"))
        ca_cert_pem = (cfg.get("ca_cert", "") or "").strip()
        client_cert = (cfg.get("client_cert", "") or "").strip()
        client_key = (cfg.get("client_key", "") or "").strip()

        # ── Build the SSLContext ───────────────────────────────────────────
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

        if skip_verify:
            # ⚠️  Disable cert verification — useful for mTLS brokers with
            #     self-signed certs when you still want transport encryption.
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            logger.warning(
                "TLS certificate verification is DISABLED for this broker.  "
                "This is insecure in production environments."
            )
        else:
            ctx.check_hostname = True
            ctx.verify_mode = ssl.CERT_REQUIRED
            if ca_cert_pem:
                # Custom CA certificate (PEM string loaded in-memory)
                ctx.load_verify_locations(cadata=ca_cert_pem)
                logger.debug("Loaded custom CA certificate from configuration.")
            else:
                # Fall back to the platform / system trust store
                ctx.load_default_certs(ssl.Purpose.SERVER_AUTH)
                logger.debug("Using system CA trust store.")

        # ── Optional client cert + key (mTLS) ─────────────────────────────
        if client_cert and client_key:
            cert_path = self._write_tmp(client_cert, suffix=".cert.pem")
            key_path = self._write_tmp(client_key, suffix=".key.pem")
            ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)
            logger.debug("Loaded client certificate and private key for mTLS.")
        elif client_cert or client_key:
            raise ValueError(
                "Both 'Client Certificate' and 'Client Private Key' must be "
                "provided together for mTLS.  Only one of them is set."
            )

        return ctx


# ───────────────────────────────────────────────────────────────────────────
# UCC entry points
# ───────────────────────────────────────────────────────────────────────────


def validate_input(helper, definition) -> None:
    """
    Called by Splunk when the user saves or edits an input stanza.

    Raises ValueError to surface a message in the UCC UI.
    """
    params = definition.parameters

    broker_name = params.get("broker", "").strip()
    if not broker_name:
        raise ValueError("An MQTT Broker must be selected.")

    topic = params.get("topic", "").strip()
    if not topic:
        raise ValueError("Topic Filter cannot be empty.")

    qos_raw = params.get("qos", "0")
    try:
        qos = int(qos_raw)
        if qos not in (0, 1, 2):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("QoS must be 0, 1, or 2.")

    interval_raw = params.get("interval", "30")
    try:
        interval = int(interval_raw)
        if interval < 1:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("Reconnect Interval must be a positive integer.")


def collect_events(helper, ew) -> None:
    """
    Main data collection loop.

    * Fetches broker config from Splunk REST.
    * Establishes an MQTT connection (plain, TLS, or mTLS).
    * Subscribes to the configured topic filter.
    * Writes received messages as JSON events to Splunk indefinitely.
    * Reconnects automatically on disconnection.
    """

    # ── Input parameters ──────────────────────────────────────────────────
    broker_name = helper.get_arg("broker") or ""
    topic = helper.get_arg("topic") or "#"
    qos = int(helper.get_arg("qos") or 0)
    sourcetype = helper.get_arg("sourcetype") or "mqtt:message"
    index = helper.get_arg("index") or "default"
    client_id = helper.get_arg("mqtt_client_id") or ""
    if str(client_id).strip().lower() == "auto":
        client_id = ""
    interval = int(helper.get_arg("interval") or 30)

    # Derive a unique, deterministic client ID from the input stanza name
    # when the user has not specified one explicitly.
    if not client_id:
        try:
            stanza_name = list(helper.get_input_stanza_names())[0]
        except Exception:
            stanza_name = "splunk"
        client_id = f"splunk-ta-mqtt-{stanza_name}"

    helper.log_info(
        f"Starting MQTT input  broker={broker_name!r}  topic={topic!r}  "
        f"qos={qos}  client_id={client_id!r}"
    )

    # ── Broker configuration ──────────────────────────────────────────────
    try:
        broker_cfg = _get_broker_config(helper, broker_name)
    except Exception as exc:
        helper.log_error(f"Cannot load broker configuration: {exc}")
        return

    host = broker_cfg.get("host", "localhost").strip()
    port = int(broker_cfg.get("port", "1883"))
    username = (broker_cfg.get("username", "") or "").strip()
    password = (broker_cfg.get("password", "") or "").strip()

    # ── Thread-safe event queue ───────────────────────────────────────────
    # MQTT callbacks run in paho's network thread; Splunk's ew.write_event()
    # should only be called from the main thread → use a queue.
    event_q: "queue.Queue[Any]" = queue.Queue(maxsize=10_000)

    shutdown_evt = threading.Event()

    # ── MQTT callbacks ────────────────────────────────────────────────────
    def on_connect(client, userdata, flags, rc):
        if rc == mqtt.MQTT_ERR_SUCCESS:
            helper.log_info(
                f"Connected to {host}:{port} as {client_id!r}.  "
                f"Subscribing to '{topic}' QoS {qos}."
            )
            result, mid = client.subscribe(topic, qos=qos)
            if result != mqtt.MQTT_ERR_SUCCESS:
                helper.log_error(f"Subscribe call failed: rc={result}")
        else:
            reason = {
                1: "Unacceptable protocol version",
                2: "Identifier rejected",
                3: "Server unavailable",
                4: "Bad username or password",
                5: "Not authorised",
            }.get(rc, f"Unknown rc={rc}")
            helper.log_error(f"MQTT connection refused: {reason}")

    def on_disconnect(client, userdata, rc):
        if rc == mqtt.MQTT_ERR_SUCCESS:
            helper.log_info("MQTT disconnected cleanly.")
        else:
            helper.log_warning(
                f"Unexpected disconnection from {host}:{port}  rc={rc}.  "
                f"Will retry in {interval}s."
            )

    def on_subscribe(client, userdata, mid, granted_qos):
        helper.log_info(
            f"Subscription confirmed  topic={topic!r}  " f"granted_qos={granted_qos}"
        )

    def on_message(client, userdata, msg):
        """Decode payload and push a structured dict onto the event queue."""
        # Decode binary payload → UTF-8 string or hex fallback
        try:
            payload_str = msg.payload.decode("utf-8")
        except (UnicodeDecodeError, AttributeError):
            payload_str = msg.payload.hex() if msg.payload else ""

        event_dict = {
            "broker": broker_name,
            "mqtt_host": host,
            "port": port,
            "topic": msg.topic,
            "qos": msg.qos,
            "retain": bool(msg.retain),
            "payload": payload_str,
        }
        try:
            event_q.put_nowait(event_dict)
        except queue.Full:
            helper.log_warning(
                "Event queue is full; dropping MQTT message on "
                f"topic={msg.topic!r}.  Consider increasing throughput or "
                "reducing topic breadth."
            )

    # ── Build MQTT client ─────────────────────────────────────────────────
    client = mqtt.Client(
        client_id=client_id,
        clean_session=True,
        protocol=mqtt.MQTTv311,
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_subscribe = on_subscribe
    client.on_message = on_message

    # Anonymous access: only set credentials when username is non-empty.
    if username:
        client.username_pw_set(username, password or None)
        helper.log_debug(f"Using credentials for user '{username}'.")
    else:
        helper.log_debug("Connecting anonymously (no credentials).")

    # ── TLS / mTLS setup ──────────────────────────────────────────────────
    with _TLSSetup(broker_cfg) as tls:
        if tls.enabled:
            client.tls_set_context(tls.context)
            skip = _is_true(broker_cfg.get("skip_verify", "0"))
            helper.log_info(
                f"TLS enabled  skip_verify={skip}  "
                f"mTLS={'yes' if broker_cfg.get('client_cert','').strip() else 'no'}"
            )
        else:
            helper.log_debug("TLS disabled — plain TCP connection.")

        # ── Main loop ─────────────────────────────────────────────────────
        while not shutdown_evt.is_set():
            try:
                helper.log_info(f"Connecting to {host}:{port} …")
                client.connect(host, port, keepalive=60)
                client.loop_start()

                # Drain the event queue, writing events to Splunk
                while not shutdown_evt.is_set():
                    # Flush all queued events
                    while True:
                        try:
                            event_dict = event_q.get_nowait()
                        except queue.Empty:
                            break

                        splunk_event = helper.new_event(
                            data=json.dumps(event_dict, ensure_ascii=False),
                            time=None,  # let Splunk assign _time = now
                            host=host,
                            source=f"mqtt://{host}:{port}/{event_dict['topic']}",
                            sourcetype=sourcetype,
                            index=index,
                            done=True,
                            unbroken=True,
                        )
                        ew.write_event(splunk_event)

                    time.sleep(0.05)  # 50 ms polling granularity

            except Exception as exc:
                helper.log_error(
                    f"Error in MQTT loop for broker '{broker_name}': {exc}"
                )
            finally:
                # Always stop paho's network thread before sleeping / exiting
                try:
                    client.loop_stop()
                    client.disconnect()
                except Exception:
                    pass
            if not shutdown_evt.is_set():
                helper.log_info(
                    f"Waiting {interval}s before reconnecting to {host}:{port}."
                )
                time.sleep(interval)

    helper.log_info(f"MQTT input for broker '{broker_name}' stopped.")
