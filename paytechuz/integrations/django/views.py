"""
Django views for PayTechUZ.

Each view is a ready-to-use, CSRF-exempt webhook endpoint. Subclass the one you
need and override ``successfully_payment`` / ``cancelled_payment`` to hook your
own business logic into the payment flow.
"""
import logging

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .webhooks import (
    PaymeWebhook,
    ClickWebhook,
    UzumWebhook,
    PaynetWebhook,
    OctoWebhook,
)

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class BasePaymeWebhookView(PaymeWebhook):
    """
    Default Payme webhook view.

    This view handles webhook requests from the Payme payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from paytechuz.integrations.django.views import BasePaymeWebhookView

    class PaymeWebhookView(BasePaymeWebhookView):
        def successfully_payment(self, params, transaction):
            order = Order.objects.get(id=transaction.account_id)
            order.status = 'paid'
            order.save()
    ```
    """

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        logger.info("Payme payment successful: %s", transaction.transaction_id)

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        logger.info("Payme payment cancelled: %s", transaction.transaction_id)


@method_decorator(csrf_exempt, name='dispatch')
class BaseClickWebhookView(ClickWebhook):
    """
    Default Click webhook view.

    This view handles webhook requests from the Click payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from paytechuz.integrations.django.views import BaseClickWebhookView

    class ClickWebhookView(BaseClickWebhookView):
        def successfully_payment(self, params, transaction):
            order = Order.objects.get(id=transaction.account_id)
            order.status = 'paid'
            order.save()
    ```
    """

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        logger.info("Click payment successful: %s", transaction.transaction_id)

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.

        Args:
            params: Request parameters
            transaction: Transaction object
        """
        logger.info("Click payment cancelled: %s", transaction.transaction_id)


@method_decorator(csrf_exempt, name='dispatch')
class BaseUzumWebhookView(UzumWebhook):
    """
    Default Uzum webhook view.

    This view handles webhook requests from the Uzum payment system.
    The URL must accept an ``action`` kwarg, e.g.
    ``payments/webhook/uzum/<str:action>/``.

    Example:
    ```python
    from paytechuz.integrations.django.views import BaseUzumWebhookView

    class UzumWebhookView(BaseUzumWebhookView):
        def successfully_payment(self, params, transaction):
            order = Order.objects.get(id=transaction.account_id)
            order.status = 'paid'
            order.save()
    ```
    """

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.
        """
        logger.info("Uzum payment successful: %s", transaction.transaction_id)

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.
        """
        logger.info("Uzum payment cancelled: %s", transaction.transaction_id)


@method_decorator(csrf_exempt, name='dispatch')
class BasePaynetWebhookView(PaynetWebhook):
    """
    Default Paynet webhook view.

    This view handles webhook requests from the Paynet payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from paytechuz.integrations.django.views import BasePaynetWebhookView

    class PaynetWebhookView(BasePaynetWebhookView):
        def successfully_payment(self, params, transaction):
            order = Order.objects.get(id=transaction.account_id)
            order.status = 'paid'
            order.save()
    ```
    """

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.
        """
        logger.info("Paynet payment successful: %s", transaction.transaction_id)

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.
        """
        logger.info("Paynet payment cancelled: %s", transaction.transaction_id)


@method_decorator(csrf_exempt, name='dispatch')
class BaseOctoWebhookView(OctoWebhook):
    """
    Default Octo webhook view.

    This view handles callback notifications from the Octo payment system.
    You can extend this class and override the event methods to customize
    the behavior.

    Example:
    ```python
    from paytechuz.integrations.django.views import BaseOctoWebhookView

    class OctoWebhookView(BaseOctoWebhookView):
        def successfully_payment(self, params, transaction):
            order = Order.objects.get(id=transaction.account_id)
            order.status = 'paid'
            order.save()
    ```
    """

    def successfully_payment(self, params, transaction):
        """
        Called when a payment is successful.
        """
        logger.info("Octo payment successful: %s", transaction.transaction_id)

    def cancelled_payment(self, params, transaction):
        """
        Called when a payment is cancelled.
        """
        logger.info("Octo payment cancelled: %s", transaction.transaction_id)
