import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class PurchesConfig(AppConfig):
    name = "core.purches"

    def ready(self):
        # Import signals to register signal handlers. Keep the import even if unused.
        try:
            from . import signals  # noqa: F401
        except Exception as exc:
            logger.exception("failed to import signals: %s", exc)
