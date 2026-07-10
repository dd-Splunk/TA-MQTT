import json
import logging
import os
import ssl
import urllib.parse
import urllib.request

import import_declare_test

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.endpoint import (
    DataInputModel,
    RestModel,
    field,
    validator,
)

util.remove_http_proxy_env_vars()


_HEC_COLLECTION_PATH = "/servicesNS/nobody/splunk_httpinput/data/inputs/http"


def _splunk_rest_request(session_key, method, path, payload=None):
    mgmt_port = int(os.environ.get("SPLUNK_MGMT_PORT", "8089"))
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
        context=ssl._create_unverified_context(),
        timeout=10,
    ) as response:
        response_body = response.read().decode("utf-8")
    if not response_body:
        return {}
    return json.loads(response_body)


def _hec_token_name(stanza_id):
    return f"ta_mqtt_{stanza_id}"


def _find_hec_token(session_key, stanza_id):
    response = _splunk_rest_request(
        session_key,
        "GET",
        f"{_HEC_COLLECTION_PATH}?output_mode=json&count=0",
    )
    wanted_name = f"http://{_hec_token_name(stanza_id)}"
    for entry in response.get("entry", []):
        if entry.get("name") == wanted_name:
            return entry.get("content", {}).get("token")
    return ""


def _create_hec_token(session_key, stanza_id, payload):
    index_name = str(payload.get("index", "default") or "default").strip()
    request_payload = {
        "name": _hec_token_name(stanza_id),
        "index": index_name,
        "indexes": index_name,
    }
    sourcetype = str(payload.get("sourcetype", "") or "").strip()
    if sourcetype:
        request_payload["sourcetype"] = sourcetype

    response = _splunk_rest_request(
        session_key,
        "POST",
        f"{_HEC_COLLECTION_PATH}?output_mode=json",
        payload=request_payload,
    )
    return response.get("entry", [{}])[0].get("content", {}).get("token", "")


def _remove_hec_token(session_key, stanza_id):
    response = _splunk_rest_request(
        session_key,
        "GET",
        f"{_HEC_COLLECTION_PATH}?output_mode=json&count=0",
    )
    wanted_name = f"http://{_hec_token_name(stanza_id)}"
    for entry in response.get("entry", []):
        if entry.get("name") == wanted_name:
            remove_path = entry.get("links", {}).get("remove")
            if remove_path:
                _splunk_rest_request(session_key, "DELETE", remove_path)
            return


special_fields = [
    field.RestField(
        "name",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=100,
                min_len=1,
            ),
            validator.Pattern(
                regex=r"""^[a-zA-Z][a-zA-Z0-9_-]*$""",
            ),
        ),
    )
]

fields = [
    field.RestField(
        "broker",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^[a-zA-Z][a-zA-Z0-9_]*$""",
        ),
    ),
    field.RestField(
        "topic",
        required=True,
        encrypted=False,
        default="#",
        validator=validator.String(
            max_len=500,
            min_len=1,
        ),
    ),
    field.RestField(
        "qos",
        required=True,
        encrypted=False,
        default="0",
        validator=validator.Pattern(
            regex=r"""^[012]$""",
        ),
    ),
    field.RestField(
        "mqtt_client_id",
        required=False,
        encrypted=False,
        default="AUTO",
        validator=validator.Pattern(
            regex=r"""^$|^AUTO$|^[a-zA-Z0-9_-]{1,128}$""",
        ),
    ),
    field.RestField(
        "index",
        required=True,
        encrypted=False,
        default="default",
        validator=validator.AllOf(
            validator.Pattern(
                regex=r"""^[a-zA-Z0-9][a-zA-Z0-9\\_\\-]*$""",
            ),
            validator.String(
                max_len=80,
                min_len=1,
            ),
        ),
    ),
    field.RestField(
        "sourcetype",
        required=False,
        encrypted=False,
        default="mqtt:message",
        validator=validator.Pattern(
            regex=r"""^$|^[a-zA-Z0-9:._-]{1,200}$""",
        ),
    ),
    field.RestField(
        "interval",
        required=False,
        encrypted=False,
        default="30",
        validator=validator.Pattern(
            regex=r"""^((?:-1|\d+(?:\.\d+)?)|(([\*\d{1,2}\,\-\/]+\s){4}[\*\d{1,2}\,\-\/]+))$""",
        ),
    ),
    field.RestField(
        "queue_maxsize",
        required=False,
        encrypted=False,
        default="10000",
        validator=validator.Pattern(
            regex=r"""^[1-9][0-9]*$""",
        ),
    ),
    field.RestField(
        "batch_mode",
        required=False,
        encrypted=False,
        default="1",
        validator=validator.Pattern(
            regex=r"""^[01]$""",
        ),
    ),
    field.RestField(
        "hec_endpoint",
        required=False,
        encrypted=False,
        default="https://localhost:8088/services/collector/event",
        validator=validator.String(
            max_len=500,
            min_len=0,
        ),
    ),
    field.RestField(
        "hec_token",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^$|^[A-Za-z0-9][A-Za-z0-9-]{0,63}$""",
        ),
    ),
    field.RestField(
        "hec_verify_tls",
        required=False,
        encrypted=False,
        default=True,
        validator=None,
    ),
    field.RestField(
        "hec_batch_max_events",
        required=False,
        encrypted=False,
        default="500",
        validator=validator.Pattern(
            regex=r"""^[1-9][0-9]*$""",
        ),
    ),
    field.RestField(
        "hec_batch_max_bytes",
        required=False,
        encrypted=False,
        default="1048576",
        validator=validator.Pattern(
            regex=r"""^[1-9][0-9]*$""",
        ),
    ),
    field.RestField(
        "hec_flush_interval_ms",
        required=False,
        encrypted=False,
        default="250",
        validator=validator.Pattern(
            regex=r"""^[1-9][0-9]*$""",
        ),
    ),
    field.RestField(
        "hec_retry_max_attempts",
        required=False,
        encrypted=False,
        default="5",
        validator=validator.Pattern(
            regex=r"""^[0-9]+$""",
        ),
    ),
    field.RestField(
        "hec_retry_backoff_ms",
        required=False,
        encrypted=False,
        default="200",
        validator=validator.Pattern(
            regex=r"""^[1-9][0-9]*$""",
        ),
    ),
    field.RestField(
        "disabled",
        required=False,
        validator=None,
    ),
]

model = RestModel(fields, name=None, special_fields=special_fields)

endpoint = DataInputModel("mqtt_subscriber", model)


class MQTTSubscriberHandler(AdminExternalHandler):
    @staticmethod
    def _ensure_hec_token(session_key, stanza_id, payload):
        batch_mode = str(payload.get("batch_mode", "1")).strip()
        if batch_mode != "1":
            return

        hec_token = _find_hec_token(session_key, stanza_id)
        if not hec_token:
            hec_token = _create_hec_token(session_key, stanza_id, payload)
        if not hec_token:
            raise RuntimeError(
                f"Failed to provision a Splunk HEC token for input '{stanza_id}'."
            )
        payload["hec_token"] = hec_token

    def create_hook(self, session_key, config_name, stanza_id, payload):
        self._ensure_hec_token(session_key, stanza_id, payload)

    def edit_hook(self, session_key, config_name, stanza_id, payload):
        self._ensure_hec_token(session_key, stanza_id, payload)

    def delete_hook(self, session_key, config_name, stanza_id):
        _remove_hec_token(session_key, stanza_id)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(endpoint, handler=MQTTSubscriberHandler)
