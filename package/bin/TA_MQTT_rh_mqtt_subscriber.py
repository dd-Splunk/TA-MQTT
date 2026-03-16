import logging
import uuid

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
                regex=r"""^[a-zA-Z][a-zA-Z0-9_]*$""",
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
        "batch_mode",
        required=False,
        encrypted=False,
        default="0",
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
    def _ensure_hec_token(payload):
        batch_mode = str(payload.get("batch_mode", "0")).strip()
        hec_token = str(payload.get("hec_token", "")).strip()
        if batch_mode == "1" and not hec_token:
            payload["hec_token"] = str(uuid.uuid4())

    def create_hook(self, session_key, config_name, stanza_id, payload):
        self._ensure_hec_token(payload)

    def edit_hook(self, session_key, config_name, stanza_id, payload):
        self._ensure_hec_token(payload)


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(endpoint, handler=MQTTSubscriberHandler)
