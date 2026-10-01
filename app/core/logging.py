import logging
import sys

import structlog


def filter_secrets(logger, log_method, event_dict):
    """Redact secrets from logs."""
    sensitive_keys = {"password", "token", "email", "secret", "student_id"}
    for key in list(event_dict.keys()):
        if any(sens in key.lower() for sens in sensitive_keys):
            event_dict[key] = "***REDACTED***"
    return event_dict

def setup_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            filter_secrets,
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
