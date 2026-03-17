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

import base64
import json
import logging
import os
import queue
import re
import ssl
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
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
_OUTPUT_MODES = {"modinput_single_event", "hec_batch"}
_HEC_TOKEN_REGEX = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]{0,63}$")
_HEALTH_LOG_INTERVAL_SECS = 60.0
_QUEUE_GET_TIMEOUT_SECS = 1.0
_QUEUE_DRAIN_BATCH_SIZE = 200
_DROP_WARNING_INTERVAL_SECS = 30.0
_HEC_COLLECTION_PATH = "/servicesNS/nobody/splunk_httpinput/data/inputs/http"


def _is_true(value: Any) -> bool:
    """Return True when a UCC checkbox / arbitrary value is logically true."""
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUTHY


def _parse_positive_int(raw_value: Any, field_name: str) -> int:
    """Parse and validate positive integer settings values."""
    try:
        parsed_value = int(str(raw_value).strip())
    except (ValueError, TypeError):
        raise ValueError(f"{field_name} must be a positive integer.")
    if parsed_value < 1:
        raise ValueError(f"{field_name} must be a positive integer.")
    return parsed_value


def _decode_payload(payload_bytes: Any) -> Dict[str, Any]:
    """Decode MQTT payload with explicit fallback metadata for non-UTF bytes."""
    if payload_bytes in (None, b""):
        return {
            "payload": "",
            "payload_encoding": "utf-8",
            "payload_decode_fallback": False,
        }

    if isinstance(payload_bytes, str):
        return {
            "payload": payload_bytes,
            "payload_encoding": "utf-8",
            "payload_decode_fallback": False,
        }

    try:
        payload_text = payload_bytes.decode("utf-8")
        return {
            "payload": payload_text,
            "payload_encoding": "utf-8",
            "payload_decode_fallback": False,
        }
    except (UnicodeDecodeError, AttributeError):
        fallback_text = payload_bytes.decode("utf-8", errors="replace")
        payload_b64 = base64.b64encode(payload_bytes).decode("ascii")
        return {
            "payload": fallback_text,
            "payload_encoding": "utf-8-replace",
            "payload_decode_fallback": True,
            "payload_base64": payload_b64,
        }


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


def _splunk_rest_json(helper, method: str, path: str, payload=None) -> Dict[str, Any]:
    mgmt_port = int(os.environ.get("SPLUNK_MGMT_PORT", "8089"))
    session_key = helper.context_meta.get("session_key", "")
    if not session_key:
        raise RuntimeError("Splunk session key is not available.")

    url = f"https://localhost:{mgmt_port}{path}"
    body = None
    if payload is not None:
        body = urllib.parse.urlencode(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers={"Authorization": f"Splunk {session_key}"},
        method=method,
    )
    with urllib.request.urlopen(
        request,
        timeout=10,
        context=ssl._create_unverified_context(),
    ) as response:
        response_body = response.read().decode("utf-8", errors="replace")
    if not response_body:
        return {}
    return json.loads(response_body)


def _hec_token_name(stanza_name: str) -> str:
    return f"ta_mqtt_{stanza_name}"


def _get_input_stanza_name(helper) -> str:
    raw_stanza_names = helper.get_input_stanza_names()
    if isinstance(raw_stanza_names, str):
        return raw_stanza_names
    try:
        return next(iter(raw_stanza_names))
    except Exception:
        return "splunk"


def _lookup_hec_token(helper, stanza_name: str) -> str:
    response = _splunk_rest_json(
        helper,
        "GET",
        f"{_HEC_COLLECTION_PATH}?output_mode=json&count=0",
    )
    wanted_name = f"http://{_hec_token_name(stanza_name)}"
    for entry in response.get("entry", []):
        if entry.get("name") == wanted_name:
            return entry.get("content", {}).get("token", "")
    return ""


def _create_hec_token(helper, stanza_name: str, index: str, sourcetype: str) -> str:
    request_payload = {
        "name": _hec_token_name(stanza_name),
        "index": index,
        "indexes": index,
    }
    if sourcetype:
        request_payload["sourcetype"] = sourcetype

    response = _splunk_rest_json(
        helper,
        "POST",
        f"{_HEC_COLLECTION_PATH}?output_mode=json",
        payload=request_payload,
    )
    return response.get("entry", [{}])[0].get("content", {}).get("token", "")


def _persist_input_hec_token(helper, stanza_name: str, hec_token: str) -> None:
    try:
        import splunklib.client as splunk_client  # type: ignore
    except ImportError as exc:
        raise RuntimeError("splunklib is not available.") from exc

    mgmt_port = int(os.environ.get("SPLUNK_MGMT_PORT", "8089"))
    session_key = helper.context_meta.get("session_key", "")
    if not session_key:
        raise RuntimeError("Splunk session key is not available.")

    service = splunk_client.connect(
        host="localhost",
        port=mgmt_port,
        token=session_key,
        owner="nobody",
        app="TA-MQTT",
        scheme="https",
    )
    service.confs["inputs"][f"mqtt_subscriber://{stanza_name}"].update(
        hec_token=hec_token
    )


def _ensure_runtime_hec_token(
    helper,
    stanza_name: str,
    index: str,
    sourcetype: str,
    current_token: str,
) -> str:
    actual_token = _lookup_hec_token(helper, stanza_name)
    if not actual_token:
        actual_token = _create_hec_token(helper, stanza_name, index, sourcetype)
        if not actual_token:
            raise RuntimeError(
                f"Failed to provision a Splunk HEC token for input '{stanza_name}'."
            )
        helper.log_info(f"Provisioned Splunk HEC token for input '{stanza_name}'.")

    if current_token != actual_token:
        _persist_input_hec_token(helper, stanza_name, actual_token)
        helper.log_info(
            f"Updated persisted HEC token for input '{stanza_name}' to the active Splunk token."
        )

    return actual_token


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


class _EgressWriter:
    """Abstract egress writer interface for output strategy selection."""

    def write(self, event_dict: Dict[str, Any], host: str, port: int) -> None:
        raise NotImplementedError

    def flush(self, force: bool = False) -> None:
        del force

    def close(self) -> None:
        self.flush(force=True)


class _ModInputSingleEventWriter(_EgressWriter):
    """Current behavior: write each event individually via ew.write_event."""

    def __init__(self, helper, ew, sourcetype: str, index: str) -> None:
        self._helper = helper
        self._ew = ew
        self._sourcetype = sourcetype
        self._index = index

    def write(self, event_dict: Dict[str, Any], host: str, port: int) -> None:
        splunk_event = self._helper.new_event(
            data=json.dumps(event_dict, ensure_ascii=False),
            time=None,  # let Splunk assign _time = now
            host=host,
            source=f"mqtt://{host}:{port}/{event_dict['topic']}",
            sourcetype=self._sourcetype,
            index=self._index,
            done=True,
            unbroken=True,
        )
        self._ew.write_event(splunk_event)


class _HecBatchWriter(_EgressWriter):
    """Batch egress writer that sends newline-delimited events to Splunk HEC."""

    def __init__(
        self,
        helper,
        endpoint: str,
        token: str,
        verify_tls: bool,
        batch_max_events: int,
        batch_max_bytes: int,
        flush_interval_ms: int,
        retry_max_attempts: int,
        retry_backoff_ms: int,
        sourcetype: str,
        index: str,
    ) -> None:
        self._helper = helper
        self._endpoint = endpoint
        self._token = token
        self._verify_tls = verify_tls
        self._batch_max_events = batch_max_events
        self._batch_max_bytes = batch_max_bytes
        self._flush_interval_ms = flush_interval_ms
        self._retry_max_attempts = retry_max_attempts
        self._retry_backoff_ms = retry_backoff_ms
        self._sourcetype = sourcetype
        self._index = index

        self._buffer_lines: List[str] = []
        self._buffer_bytes = 0
        self._last_flush_monotonic = time.monotonic()

        self._hec_batches_sent = 0
        self._hec_batches_failed = 0
        self._hec_events_sent = 0
        self._hec_events_failed = 0
        self._hec_retries = 0
        self._closed = False
        self._close_calls = 0

    def _build_hec_payload_line(
        self,
        event_dict: Dict[str, Any],
        host: str,
        port: int,
    ) -> str:
        topic = event_dict.get("topic", "")
        hec_event = {
            "event": event_dict,
            "host": host,
            "source": f"mqtt://{host}:{port}/{topic}",
            "sourcetype": self._sourcetype,
            "index": self._index,
        }
        return json.dumps(hec_event, ensure_ascii=False, separators=(",", ":"))

    def write(self, event_dict: Dict[str, Any], host: str, port: int) -> None:
        line = self._build_hec_payload_line(event_dict=event_dict, host=host, port=port)
        line_bytes = len(line.encode("utf-8")) + 1

        if (
            self._buffer_lines
            and self._buffer_bytes + line_bytes > self._batch_max_bytes
        ):
            self.flush(force=True)

        self._buffer_lines.append(line)
        self._buffer_bytes += line_bytes

        if (
            len(self._buffer_lines) >= self._batch_max_events
            or self._buffer_bytes >= self._batch_max_bytes
        ):
            self.flush(force=True)

    def _build_ssl_context(self):
        if not self._endpoint.lower().startswith("https://"):
            return None
        if self._verify_tls:
            return ssl.create_default_context()
        return ssl._create_unverified_context()

    def _send_payload(self, payload: bytes, events_in_batch: int) -> None:
        headers = {
            "Authorization": f"Splunk {self._token}",
            "Content-Type": "application/json",
        }
        request = urllib.request.Request(
            self._endpoint,
            data=payload,
            headers=headers,
            method="POST",
        )
        ssl_context = self._build_ssl_context()

        last_error: Optional[Exception] = None
        for attempt_index in range(self._retry_max_attempts):
            try:
                with urllib.request.urlopen(
                    request,
                    timeout=10,
                    context=ssl_context,
                ) as response:
                    status_code = response.getcode()
                    response_body = response.read().decode("utf-8", errors="replace")

                if status_code != 200:
                    raise RuntimeError(
                        f"HEC HTTP status={status_code} body={response_body[:300]}"
                    )

                parsed_response = json.loads(response_body)
                if int(parsed_response.get("code", 1)) != 0:
                    raise RuntimeError(
                        "HEC application error "
                        f"code={parsed_response.get('code')} "
                        f"text={parsed_response.get('text')}"
                    )

                self._hec_batches_sent += 1
                self._hec_events_sent += events_in_batch
                return
            except Exception as exc:
                last_error = exc
                if attempt_index + 1 < self._retry_max_attempts:
                    self._hec_retries += 1
                    backoff_seconds = (
                        self._retry_backoff_ms * (2**attempt_index)
                    ) / 1000.0
                    time.sleep(backoff_seconds)

        self._hec_batches_failed += 1
        self._hec_events_failed += events_in_batch
        raise RuntimeError(f"HEC batch send failed after retries: {last_error}")

    def flush(self, force: bool = False) -> bool:
        """Flush the buffer if conditions are met.  Returns True if a flush was performed."""
        if not self._buffer_lines:
            return False

        if not force:
            elapsed_ms = (time.monotonic() - self._last_flush_monotonic) * 1000.0
            if (
                len(self._buffer_lines) < self._batch_max_events
                and self._buffer_bytes < self._batch_max_bytes
                and elapsed_ms < self._flush_interval_ms
            ):
                return False

        lines = self._buffer_lines
        buffered_bytes = self._buffer_bytes
        self._buffer_lines = []
        self._buffer_bytes = 0
        self._last_flush_monotonic = time.monotonic()

        payload = ("\n".join(lines) + "\n").encode("utf-8")
        events_in_batch = len(lines)

        try:
            self._send_payload(payload=payload, events_in_batch=events_in_batch)
            self._helper.log_debug(
                "HEC batch sent "
                f"events={events_in_batch} bytes={buffered_bytes} "
                f"retries_total={self._hec_retries}"
            )
        except Exception as exc:
            self._helper.log_error(
                "HEC batch flush failed; dropping buffered events "
                f"events={events_in_batch} error={exc}"
            )
        return True

    def close(self) -> None:
        self._close_calls += 1
        if self._closed:
            self._helper.log_debug(
                "HEC batch writer close called after writer already closed; "
                f"close_calls={self._close_calls}"
            )
            return

        buffered_events_before_close = len(self._buffer_lines)
        buffered_bytes_before_close = self._buffer_bytes
        flushed_on_close = False

        try:
            flushed_on_close = self.flush(force=True)
        finally:
            self._closed = True
            self._helper.log_info(
                "HEC batch writer summary "
                f"close_calls={self._close_calls} "
                f"flushed_on_close={1 if flushed_on_close else 0} "
                f"buffered_events_before_close={buffered_events_before_close} "
                f"buffered_bytes_before_close={buffered_bytes_before_close} "
                f"buffered_events_after_close={len(self._buffer_lines)} "
                f"buffered_bytes_after_close={self._buffer_bytes} "
                f"batches_sent={self._hec_batches_sent} "
                f"batches_failed={self._hec_batches_failed} "
                f"events_sent={self._hec_events_sent} "
                f"events_failed={self._hec_events_failed} "
                f"retries={self._hec_retries}"
            )


def _build_egress_writer(
    helper,
    ew,
    output_mode: str,
    sourcetype: str,
    index: str,
    hec_endpoint: str,
    hec_token: str,
    hec_verify_tls: bool,
    hec_batch_max_events: int,
    hec_batch_max_bytes: int,
    hec_flush_interval_ms: int,
    hec_retry_max_attempts: int,
    hec_retry_backoff_ms: int,
):
    """Return the active egress writer.

    `modinput_single_event` preserves current behavior.
    `hec_batch` enables batch POSTs to HEC.
    """
    normalized_mode = (output_mode or "modinput_single_event").strip().lower()
    if normalized_mode == "hec_batch":
        return _HecBatchWriter(
            helper=helper,
            endpoint=hec_endpoint,
            token=hec_token,
            verify_tls=hec_verify_tls,
            batch_max_events=hec_batch_max_events,
            batch_max_bytes=hec_batch_max_bytes,
            flush_interval_ms=hec_flush_interval_ms,
            retry_max_attempts=hec_retry_max_attempts,
            retry_backoff_ms=hec_retry_backoff_ms,
            sourcetype=sourcetype,
            index=index,
        )
    return _ModInputSingleEventWriter(helper, ew, sourcetype, index)


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

    batch_mode = _is_true(params.get("batch_mode", "0"))
    output_mode = "hec_batch" if batch_mode else "modinput_single_event"

    if output_mode == "hec_batch":
        hec_endpoint = str(params.get("hec_endpoint", "")).strip()
        if not hec_endpoint:
            raise ValueError(
                "HEC Endpoint is required when Batch Output Mode is enabled."
            )

        hec_token = str(params.get("hec_token", "")).strip()
        if hec_token and not _HEC_TOKEN_REGEX.fullmatch(hec_token):
            raise ValueError(
                "HEC Token must be 1-64 chars and contain only letters, "
                "digits, or '-'."
            )

    _parse_positive_int(
        params.get("hec_batch_max_events", "500"),
        "HEC Batch Max Events",
    )
    _parse_positive_int(
        params.get("hec_batch_max_bytes", "1048576"),
        "HEC Batch Max Bytes",
    )
    _parse_positive_int(
        params.get("hec_flush_interval_ms", "250"),
        "HEC Flush Interval",
    )
    _parse_positive_int(
        params.get("hec_retry_max_attempts", "5"),
        "HEC Retry Max Attempts",
    )
    _parse_positive_int(
        params.get("hec_retry_backoff_ms", "200"),
        "HEC Retry Backoff",
    )


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
    batch_mode_enabled = _is_true(helper.get_arg("batch_mode") or "0")
    output_mode = "hec_batch" if batch_mode_enabled else "modinput_single_event"

    hec_endpoint = (
        helper.get_arg("hec_endpoint")
        or "https://localhost:8088/services/collector/event"
    ).strip()
    hec_token = (helper.get_arg("hec_token") or "").strip()
    hec_verify_tls = _is_true(helper.get_arg("hec_verify_tls") or "1")
    hec_batch_max_events = _parse_positive_int(
        helper.get_arg("hec_batch_max_events") or "500",
        "HEC Batch Max Events",
    )
    hec_batch_max_bytes = _parse_positive_int(
        helper.get_arg("hec_batch_max_bytes") or "1048576",
        "HEC Batch Max Bytes",
    )
    hec_flush_interval_ms = _parse_positive_int(
        helper.get_arg("hec_flush_interval_ms") or "250",
        "HEC Flush Interval",
    )
    hec_retry_max_attempts = _parse_positive_int(
        helper.get_arg("hec_retry_max_attempts") or "5",
        "HEC Retry Max Attempts",
    )
    hec_retry_backoff_ms = _parse_positive_int(
        helper.get_arg("hec_retry_backoff_ms") or "200",
        "HEC Retry Backoff",
    )

    client_id = helper.get_arg("mqtt_client_id") or ""
    if str(client_id).strip().lower() == "auto":
        client_id = ""
    interval = int(helper.get_arg("interval") or 30)
    stanza_name = _get_input_stanza_name(helper)

    # Derive a unique, deterministic client ID from the input stanza name
    # when the user has not specified one explicitly.
    if not client_id:
        client_id = f"splunk-ta-mqtt-{stanza_name}"

    if output_mode == "hec_batch":
        if not hec_endpoint:
            helper.log_error("output_mode='hec_batch' requires hec_endpoint.")
            return
        try:
            hec_token = _ensure_runtime_hec_token(
                helper=helper,
                stanza_name=stanza_name,
                index=index,
                sourcetype=sourcetype,
                current_token=hec_token,
            )
        except Exception as exc:
            helper.log_error(f"Unable to provision a valid HEC token: {exc}")
            return

    helper.log_info(
        f"Starting MQTT input  broker={broker_name!r}  topic={topic!r}  "
        f"qos={qos}  client_id={client_id!r}  batch_mode={'1' if batch_mode_enabled else '0'}"
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
    event_q: "queue.Queue[Tuple[float, Dict[str, Any]]]" = queue.Queue(maxsize=10_000)

    shutdown_evt = threading.Event()
    stats_lock = threading.Lock()
    runtime_stats: Dict[str, Any] = {
        "messages_received": 0,
        "messages_written": 0,
        "messages_dropped": 0,
        "reconnect_attempts": 0,
        "queue_high_water": 0,
        "last_write_monotonic": None,
        "last_health_log": time.monotonic(),
        "last_logged_received": 0,
        "last_logged_written": 0,
        "last_logged_dropped": 0,
        "last_logged_reconnects": 0,
        "lag_window_count": 0,
        "lag_window_sum": 0.0,
        "lag_window_max": 0.0,
        "last_drop_warning": 0.0,
        "suppressed_drop_warnings": 0,
        "last_dropped_topic": None,
    }

    def _safe_qsize() -> int:
        try:
            return event_q.qsize()
        except NotImplementedError:
            return -1

    def _update_queue_high_water(queue_depth: int) -> None:
        if queue_depth < 0:
            return
        with stats_lock:
            runtime_stats["queue_high_water"] = max(
                runtime_stats["queue_high_water"], queue_depth
            )

    def _record_write(lag_seconds: float) -> None:
        now_monotonic = time.monotonic()
        with stats_lock:
            runtime_stats["messages_written"] += 1
            runtime_stats["lag_window_count"] += 1
            runtime_stats["lag_window_sum"] += lag_seconds
            runtime_stats["lag_window_max"] = max(
                runtime_stats["lag_window_max"], lag_seconds
            )
            runtime_stats["last_write_monotonic"] = now_monotonic

    def _record_reconnect_attempt() -> None:
        with stats_lock:
            runtime_stats["reconnect_attempts"] += 1

    def _log_drop_warning(topic_name: str) -> None:
        now_monotonic = time.monotonic()
        with stats_lock:
            runtime_stats["messages_dropped"] += 1
            runtime_stats["last_dropped_topic"] = topic_name
            should_log = (
                now_monotonic - runtime_stats["last_drop_warning"]
                >= _DROP_WARNING_INTERVAL_SECS
            )
            suppressed = runtime_stats["suppressed_drop_warnings"]
            if should_log:
                runtime_stats["last_drop_warning"] = now_monotonic
                runtime_stats["suppressed_drop_warnings"] = 0
                queue_high_water = runtime_stats["queue_high_water"]
            else:
                runtime_stats["suppressed_drop_warnings"] += 1
                queue_high_water = None
                suppressed = None
        if should_log:
            suppressed_suffix = f" suppressed={suppressed}" if suppressed else ""
            helper.log_warning(
                "Event queue is full; dropping MQTT message on "
                f"topic={topic_name!r}.{suppressed_suffix} "
                f"queue_high_water={queue_high_water}. Consider increasing "
                "throughput or reducing topic breadth."
            )

    def _maybe_log_health(force: bool = False) -> None:
        now_monotonic = time.monotonic()
        queue_depth = _safe_qsize()
        if queue_depth >= 0:
            _update_queue_high_water(queue_depth)

        with stats_lock:
            if (
                not force
                and now_monotonic - runtime_stats["last_health_log"]
                < _HEALTH_LOG_INTERVAL_SECS
            ):
                return

            received_delta = (
                runtime_stats["messages_received"]
                - runtime_stats["last_logged_received"]
            )
            written_delta = (
                runtime_stats["messages_written"] - runtime_stats["last_logged_written"]
            )
            dropped_delta = (
                runtime_stats["messages_dropped"] - runtime_stats["last_logged_dropped"]
            )
            reconnect_delta = (
                runtime_stats["reconnect_attempts"]
                - runtime_stats["last_logged_reconnects"]
            )

            lag_count = runtime_stats["lag_window_count"]
            lag_avg_ms = (
                (runtime_stats["lag_window_sum"] / lag_count) * 1000.0
                if lag_count
                else 0.0
            )
            lag_max_ms = runtime_stats["lag_window_max"] * 1000.0
            last_write_monotonic = runtime_stats["last_write_monotonic"]
            queue_high_water = runtime_stats["queue_high_water"]
            last_dropped_topic = runtime_stats["last_dropped_topic"]

            runtime_stats["last_health_log"] = now_monotonic
            runtime_stats["last_logged_received"] = runtime_stats["messages_received"]
            runtime_stats["last_logged_written"] = runtime_stats["messages_written"]
            runtime_stats["last_logged_dropped"] = runtime_stats["messages_dropped"]
            runtime_stats["last_logged_reconnects"] = runtime_stats[
                "reconnect_attempts"
            ]
            runtime_stats["lag_window_count"] = 0
            runtime_stats["lag_window_sum"] = 0.0
            runtime_stats["lag_window_max"] = 0.0

        idle_seconds = (
            now_monotonic - last_write_monotonic
            if last_write_monotonic is not None
            else None
        )
        idle_fragment = (
            f" idle_for_s={idle_seconds:.2f}" if idle_seconds is not None else ""
        )
        drop_fragment = (
            f" last_dropped_topic={last_dropped_topic!r}"
            if last_dropped_topic is not None
            else ""
        )
        helper.log_info(
            "MQTT runtime summary "
            f"broker={broker_name!r} recv_delta={received_delta} "
            f"written_delta={written_delta} dropped_delta={dropped_delta} "
            f"reconnect_delta={reconnect_delta} queue_depth={queue_depth} "
            f"queue_high_water={queue_high_water} lag_avg_ms={lag_avg_ms:.2f} "
            f"lag_max_ms={lag_max_ms:.2f}{idle_fragment}{drop_fragment}"
        )

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
        payload_fields = _decode_payload(getattr(msg, "payload", b""))

        event_dict = {
            "broker": broker_name,
            "mqtt_host": host,
            "port": port,
            "topic": msg.topic,
            "qos": msg.qos,
            "retain": bool(msg.retain),
            **payload_fields,
        }
        try:
            event_q.put_nowait((time.monotonic(), event_dict))
            queue_depth = _safe_qsize()
            with stats_lock:
                runtime_stats["messages_received"] += 1
            _update_queue_high_water(queue_depth)
        except queue.Full:
            _log_drop_warning(msg.topic)

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
        egress_writer = _build_egress_writer(
            helper=helper,
            ew=ew,
            output_mode=output_mode,
            sourcetype=sourcetype,
            index=index,
            hec_endpoint=hec_endpoint,
            hec_token=hec_token,
            hec_verify_tls=hec_verify_tls,
            hec_batch_max_events=hec_batch_max_events,
            hec_batch_max_bytes=hec_batch_max_bytes,
            hec_flush_interval_ms=hec_flush_interval_ms,
            hec_retry_max_attempts=hec_retry_max_attempts,
            hec_retry_backoff_ms=hec_retry_backoff_ms,
        )
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
        has_attempted_connection = False
        while not shutdown_evt.is_set():
            try:
                if has_attempted_connection:
                    _record_reconnect_attempt()
                else:
                    has_attempted_connection = True
                helper.log_info(f"Connecting to {host}:{port} …")
                client.connect(host, port, keepalive=60)
                client.loop_start()

                # Drain the event queue, writing events to Splunk
                while not shutdown_evt.is_set():
                    try:
                        first_enqueued_at, first_event_dict = event_q.get(
                            timeout=_QUEUE_GET_TIMEOUT_SECS
                        )
                    except queue.Empty:
                        _maybe_log_health()
                        continue

                    pending_items = [(first_enqueued_at, first_event_dict)]
                    for _ in range(_QUEUE_DRAIN_BATCH_SIZE - 1):
                        try:
                            pending_items.append(event_q.get_nowait())
                        except queue.Empty:
                            break

                    for enqueued_at, event_dict in pending_items:
                        egress_writer.write(event_dict=event_dict, host=host, port=port)
                        _record_write(max(0.0, time.monotonic() - enqueued_at))

                    egress_writer.flush(force=False)
                    _maybe_log_health()

            except Exception as exc:
                helper.log_error(
                    f"Error in MQTT loop for broker '{broker_name}': {exc}"
                )
            finally:
                # Always stop paho's network thread before sleeping / exiting
                try:
                    egress_writer.flush(force=True)
                    client.loop_stop()
                    client.disconnect()
                except Exception:
                    pass
            if not shutdown_evt.is_set():
                helper.log_info(
                    f"Waiting {interval}s before reconnecting to {host}:{port}."
                )
                time.sleep(interval)
        egress_writer.close()

    _maybe_log_health(force=True)
    helper.log_info(f"MQTT input for broker '{broker_name}' stopped.")
