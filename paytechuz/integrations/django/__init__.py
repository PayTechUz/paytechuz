"""
Django integration for PayTechUZ.

Add ``'paytechuz.integrations.django'`` to ``INSTALLED_APPS`` and configure the
``PAYTECHUZ`` settings dict, then subclass the views in
``paytechuz.integrations.django.views``.
"""

try:
    from paytechuz.core.dependencies import check_dependencies
    check_dependencies('django', raise_error=False)
except ImportError:  # pragma: no cover - during build/bootstrap
    pass


def get_payment_transaction_model():
    """
    Get the PaymentTransaction model lazily to avoid AppRegistryNotReady errors.

    Usage:
        PaymentTransaction = get_payment_transaction_model()
    """
    from paytechuz.integrations.django.models import PaymentTransaction
    return PaymentTransaction


__all__ = ['get_payment_transaction_model']
