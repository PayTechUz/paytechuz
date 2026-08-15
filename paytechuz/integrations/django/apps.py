"""
Django app configuration for PayTechUZ.
"""
from django.apps import AppConfig


class PaytechuzConfig(AppConfig):
    """
    Django app configuration for PayTechUZ.
    """
    name = 'paytechuz.integrations.django'
    verbose_name = 'PayTechUZ'

    default_auto_field = 'django.db.models.AutoField'

    def ready(self):
        """
        Initialize the app.
        """
        try:
            import paytechuz.integrations.django.signals  # noqa
        except ImportError:
            pass
