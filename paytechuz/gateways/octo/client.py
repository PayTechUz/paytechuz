"""
Octo payment gateway client.
"""
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Union, List

from paytechuz.core.http import HttpClient
from paytechuz.core.base import BasePaymentGateway
from paytechuz.gateways.octo.constants import (
    OctoNetworks,
    OctoEndpoints,
    OctoPaymentMethods,
)


logger = logging.getLogger(__name__)


class OctoGateway(BasePaymentGateway):
    """
    Octo payment gateway implementation.

    This class provides methods for interacting with the Octo payment gateway,
    including creating one-stage (auto_capture) payments, checking payment status,
    and processing refunds.

    Example::

        gateway = OctoGateway(
            octo_shop_id=123,
            octo_secret="your-secret-key",
            notify_url="https://example.com/octo/callback/",
        )

        pay_url = gateway.create_payment(
            id="order-001",
            amount=50000,
            return_url="https://example.com/payment/complete/",
        )
        # Redirect user to pay_url
    """

    def __init__(
        self,
        octo_shop_id: int,
        octo_secret: str,
        notify_url: str = "",
        is_test_mode: bool = False,
        **kwargs,
    ):
        """
        Initialize the Octo gateway.

        Args:
            octo_shop_id: Octo merchant shop ID.
            octo_secret: Octo secret key for authentication.
            notify_url: URL where Octo sends callback notifications.
            is_test_mode: When ``True``, transactions are created in test mode.
            **kwargs: Additional arguments (ignored, for backward compatibility).
        """
        super().__init__(is_test_mode)
        self.octo_shop_id = octo_shop_id
        self.octo_secret = octo_secret
        self.notify_url = notify_url

        # Octo uses the same URL; test mode is a request param
        url = OctoNetworks.TEST_NET if is_test_mode else OctoNetworks.PROD_NET

        # Initialize HTTP client
        self.http_client = HttpClient(base_url=url)

    def prepare_payment(
        self,
        shop_transaction_id: Union[int, str],
        amount: Union[int, float],
        return_url: str,
        currency: str = "UZS",
        description: str = "",
        basket: Optional[List[Dict[str, Any]]] = None,
        payment_methods: Optional[List[Dict[str, str]]] = None,
        language: str = "uz",
        ttl: int = 15,
        user_data: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a one-stage payment via Octo ``prepare_payment``.

        Args:
            shop_transaction_id: Unique transaction identifier on merchant side.
            amount: Total payment amount.
            return_url: URL the user is redirected to after payment.
            currency: Payment currency (default ``UZS``).
            description: Payment description.
            basket: List of basket items for fiscalisation.
            payment_methods: Accepted payment methods (default: all).
            language: UI language for the payment page (``uz``, ``ru``, ``en``).
            ttl: Payment page time-to-live in minutes (default 15).
            user_data: Optional user info (``user_id``, ``phone``, ``email``).
            **kwargs: Extra fields forwarded to the request body.

        Returns:
            Dict with ``octo_pay_url``, ``octo_payment_UUID``, ``status``, etc.
        """
        payload: Dict[str, Any] = {
            "octo_shop_id": self.octo_shop_id,
            "octo_secret": self.octo_secret,
            "shop_transaction_id": str(shop_transaction_id),
            "auto_capture": True,
            "init_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "test": self.is_test_mode,
            "total_sum": float(amount),
            "currency": currency,
            "description": description,
            "payment_methods": payment_methods or OctoPaymentMethods.ALL,
            "return_url": return_url,
            "language": language,
            "ttl": ttl,
        }

        if self.notify_url:
            payload["notify_url"] = self.notify_url

        if user_data:
            payload["user_data"] = user_data

        if basket:
            payload["basket"] = basket

        # Allow callers to pass additional/override fields
        payload.update(kwargs)

        response = self.http_client.post(
            endpoint=OctoEndpoints.PREPARE_PAYMENT,
            json_data=payload,
        )

        logger.info(
            "Octo prepare_payment response for %s: error=%s",
            shop_transaction_id,
            response.get("error"),
        )
        return response

    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = "",
        **kwargs,
    ) -> str:
        """
        Create a one-stage payment via Octo and return the payment URL.

        Args:
            id: Unique order/transaction identifier on the merchant side.
            amount: Payment amount in som.
            return_url: URL the user is redirected to after payment.
            **kwargs: Additional parameters forwarded to ``prepare_payment``
                (e.g. ``currency``, ``description``, ``basket``,
                ``payment_methods``, ``language``, ``ttl``, ``user_data``).

        Returns:
            str: Octo payment URL for redirecting the user.
        """
        response = self.prepare_payment(
            shop_transaction_id=id,
            amount=float(amount),
            return_url=return_url,
            **kwargs,
        )

        return response.get("data", {}).get("octo_pay_url", "")

    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status by calling ``prepare_payment`` with
        only ``octo_shop_id``, ``octo_secret``, and ``shop_transaction_id``.

        Args:
            transaction_id: The ``shop_transaction_id`` used when creating the payment.

        Returns:
            Dict containing payment status and details.
        """
        payload = {
            "octo_shop_id": self.octo_shop_id,
            "octo_secret": self.octo_secret,
            "shop_transaction_id": str(transaction_id),
        }

        response = self.http_client.post(
            endpoint=OctoEndpoints.PREPARE_PAYMENT,
            json_data=payload,
        )

        logger.info(
            "Octo check_payment response for %s: error=%s",
            transaction_id,
            response.get("error"),
        )
        return response

    def refund(
        self,
        octo_payment_uuid: str,
        amount: Union[int, float],
        shop_refund_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Refund a completed payment.

        Args:
            octo_payment_uuid: The ``octo_payment_UUID`` from the original payment.
            amount: Amount to refund.
            shop_refund_id: Unique refund identifier (auto-generated if omitted).

        Returns:
            Dict with refund status and details.
        """
        payload = {
            "octo_shop_id": self.octo_shop_id,
            "octo_secret": self.octo_secret,
            "octo_payment_UUID": octo_payment_uuid,
            "shop_refund_id": shop_refund_id or str(uuid.uuid4()),
            "amount": float(amount),
        }

        response = self.http_client.post(
            endpoint=OctoEndpoints.REFUND,
            json_data=payload,
        )

        logger.info(
            "Octo refund response for %s: error=%s",
            octo_payment_uuid,
            response.get("error"),
        )
        return response

    def cancel_payment(
        self,
        transaction_id: str,
        amount: Union[int, float] = 0,
        reason: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Refund/cancel a completed payment.

        Args:
            transaction_id: The ``octo_payment_UUID`` from the original payment.
            amount: Amount to refund.
            reason: Optional reason for refund (not sent to Octo, for local logging).
            **kwargs: Extra arguments forwarded to the refund call.

        Returns:
            Dict containing refund status and details.
        """
        if reason:
            logger.info("Octo refund reason: %s", reason)

        return self.refund(
            octo_payment_uuid=transaction_id,
            amount=float(amount),
            **kwargs,
        )
