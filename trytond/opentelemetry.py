import logging
import sys

from trytond.config import config

logger = logging.getLogger('trytond:opentelemetry')
OPENTELEMETRY_ENABLED = config.getboolean(
    'opentelemetry', 'enabled', default=False)


def configure_trace():
    if not OPENTELEMETRY_ENABLED:
        return

    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource

    endpoint = config.get('opentelemetry', 'otlp_endpoint')
    if not endpoint:
        logger.warning('OTLP endpoint not set')
        raise ValueError('Missing OTLP endpoint')

    token = config.get('opentelemetry', 'otlp_token')
    if not token:
        logger.warning('OTLP token not set')
        token = None

    from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
        OTLPSpanExporter
    exporter = OTLPSpanExporter(
        endpoint=endpoint,
        headers={'Authorization': token} if token else None,
        )
    logger.info('Configured using OTLP')

    base_service_name = config.get(
        'opentelemetry', 'service_name', default='trytond')

    # Starting with celery always imports wsgi.py.
    # But celery instrumentation happens after startup, so there is no other
    # way AFAIK to detect which service is running except this.
    if sys.argv and sys.argv[0].endswith('celery'):
        service_name = base_service_name + '-celery'
    elif sys.argv and sys.argv[0].endswith('uwsgi'):
        service_name = base_service_name + '-uwsgi'
    elif sys.argv and sys.argv[0].endswith('trytond-admin'):
        service_name = base_service_name + '-admin'
    else:
        service_name = base_service_name
    resource = Resource(attributes={SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)


def pass_through(x):
    return x


Middleware = pass_through
if not OPENTELEMETRY_ENABLED:
    logger.warning(
        'Set enabled=True in the opentelemetry section of trytond.conf to '
        'enable opentelemetry')
else:
    from opentelemetry.instrumentation.wsgi import OpenTelemetryMiddleware
    from opentelemetry.instrumentation.requests import RequestsInstrumentor

    configure_trace()

    if config.getboolean(
            'opentelemetry', 'enable_request_instrumentation', default=True):
        RequestsInstrumentor().instrument()
        logger.info('Instrumented requests / urllib')

    if config.getboolean(
            'opentelemetry', 'enable_wsgi_instrumentation', default=True):
        Middleware = OpenTelemetryMiddleware
        logger.info('Instrumented uwsgi')

    if config.getboolean(
            'opentelemetry', 'enable_psycopg2_instrumentation', default=False):
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
        Psycopg2Instrumentor().instrument()
        logger.info('Instrumented psycopg2')

    if config.getboolean(
            'opentelemetry', 'enable_celery_instrumentation', default=True):
        from celery.signals import worker_process_init

        @worker_process_init.connect(weak=False)
        def init_celery_tracing(*args, **kwargs):
            from opentelemetry.instrumentation.celery import CeleryInstrumentor
            CeleryInstrumentor().instrument()

        logger.info('Instrumented celery')
