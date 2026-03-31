# Copyright (C) Lutra Consulting Limited
#
# SPDX-License-Identifier: AGPL-3.0-only OR LicenseRef-MerginMaps-Commercial

from decouple import config


class Configuration:
    OTEL_SERVICE_NAME = config("OTEL_SERVICE_NAME", default="mergin")
    OTEL_EXPORTER_OTLP_ENDPOINT = config(
        "OTEL_EXPORTER_OTLP_ENDPOINT", default="http://otel-collector:4317"
    )
    OTEL_PYTHON_FLASK_EXCLUDED_URLS = config(
        "OTEL_PYTHON_FLASK_EXCLUDED_URLS", default="ping,alive"
    )
    # this needs to be set to True for threads or gevent pool type in celery containers
    OTEL_MANUAL_CELERY_TRACING = config(
        "OTEL_MANUAL_CELERY_TRACING", default=False, cast=bool
    )
    OTEL_TRACES_SAMPLER_ARG = config("OTEL_TRACES_SAMPLER_ARG", default=1.0, cast=float)
