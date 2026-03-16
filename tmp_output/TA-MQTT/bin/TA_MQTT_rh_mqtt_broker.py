
import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import logging


util.remove_http_proxy_env_vars()


special_fields = [
    field.RestField(
        'name',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.AllOf(
            validator.String(
                max_len=50, 
                min_len=1, 
            ), 
            validator.Pattern(
                regex=r"""^[a-zA-Z][a-zA-Z0-9_]*$""", 
            )
        )
    )
]

fields = [
    field.RestField(
        'host',
        required=True,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=1, 
        )
    ), 
    field.RestField(
        'port',
        required=True,
        encrypted=False,
        default='1883',
        validator=validator.Pattern(
            regex=r"""^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$""", 
        )
    ), 
    field.RestField(
        'username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=255, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'use_tls',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'skip_verify',
        required=False,
        encrypted=False,
        default=False,
        validator=None
    ), 
    field.RestField(
        'ca_cert',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=20000, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'client_cert',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            max_len=20000, 
            min_len=0, 
        )
    ), 
    field.RestField(
        'client_key',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            max_len=20000, 
            min_len=0, 
        )
    )
]
model = RestModel(fields, name=None, special_fields=special_fields)


endpoint = SingleModel(
    'ta_mqtt_mqtt_broker',
    model,
    config_name='mqtt_broker',
    need_reload=False,
)


if __name__ == '__main__':
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=AdminExternalHandler,
    )
