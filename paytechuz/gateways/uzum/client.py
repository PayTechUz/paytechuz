"""
Uzum payment gateway client.
This client uses Uzum Biller (open-service) for payment URL generation.
"""
import uuid
import logging
from typing import Dict, Any, Optional, Union

from paytechuz.core.http import HttpClient
from paytechuz.core.base import BasePaymentGateway
from paytechuz.gateways.uzum.constants import UzumNetworks, UzumEndpoints

logger = logging.getLogger(__name__)


class UzumGateway(BasePaymentGateway):
    """
    Uzum payment gateway implementation.

    This class provides methods for creating payment URLs via Uzum Biller (open-service).
    Payment URL format: https://www.uzumbank.uz/open-service?serviceId=...&order_id=...&amount=...&redirectUrl=...
    """

    def __init__(
        self,
        service_id: str,
        is_test_mode: bool = False,
        terminal_id: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize the Uzum gateway.

        Args:
            service_id: Uzum Service ID (serviceId parameter in Biller URL)
            is_test_mode: Whether to use the test environment
            terminal_id: Uzum Terminal ID for refund API (X-Terminal-Id header)
            api_key: Uzum API Key for refund API (X-API-Key header)
            **kwargs: Additional arguments
        """
        super().__init__(is_test_mode)
        self.service_id = service_id
        self.terminal_id = terminal_id
        self.api_key = api_key

        # Initialize HTTP client for refund API if credentials provided
        if terminal_id and api_key:
            api_url = UzumNetworks.TEST_NET if is_test_mode else UzumNetworks.PROD_NET
            headers = {
                "X-Terminal-Id": terminal_id,
                "X-API-Key": api_key,
                "Content-Type": "application/json"
            }
            self.http_client = HttpClient(base_url=api_url, headers=headers)
        else:
            self.http_client = None

    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = None,
        **kwargs
    ) -> str:
        """
        Create a payment URL using Uzum Biller (open-service).

        Example URL:
            https://www.uzumbank.uz/open-service?serviceId=498624684&order_id=156&amount=10000000&redirectUrl=https://example.com

        Args:
            id: Order ID (order_id parameter)
            amount: Payment amount in som (will be converted to tiyin)
            return_url: URL to redirect after payment (redirectUrl parameter)
            **kwargs: Optional parameters:
                - service_id: Uzum service ID (overrides self.service_id if provided)

        Returns:
            str: Payment URL for redirecting user to Uzum payment page
        """
        # Convert amount from som to tiyin (1 som = 100 tiyin)
        amount_tiyin = int(float(amount) * 100)

        service_id = kwargs.get("service_id", self.service_id)

        payment_url = (
            f"{UzumNetworks.BILLER_URL}"
            f"?serviceId={service_id}&order_id={id}&amount={amount_tiyin}"
        )
        if return_url:
            payment_url += f"&redirectUrl={return_url}"

        return payment_url

    async def create_payment_async(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = None,
        **kwargs
    ) -> str:
        """Async version of create_payment."""
        return self.create_payment(id, amount, return_url, **kwargs)

    def check_payment(self, id: str) -> Dict[str, Any]:
        """
        Check payment status by order ID.

        Note: This method is not supported for Biller URL payments.
        Use webhook callbacks to track payment status.

        Args:
            id: The order ID

        Returns:
            Dict containing payment status
        """
        raise NotImplementedError(
            "check_payment is not supported for Biller URL payments"
        )

    def cancel_payment(
        self,
        id: str,
        amount: int,
        operation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Refund/Cancel payment using Uzum Checkout API.

        Args:
            id: The order ID or Invoice ID to refund
            amount: Amount to refund in tiyin
            operation_id: Optional unique operation ID (X-Operation-Id header)

        Returns:
            Dict containing refund response
        """
        if not self.http_client:
            raise ValueError("terminal_id and api_key are required for refund API")

        headers = {"X-Operation-Id": operation_id or str(uuid.uuid4())}

        payload = {
            "orderId": str(id),
            "amount": int(amount)
        }
        return self.http_client.post(
            UzumEndpoints.REFUND,
            json_data=payload,
            headers=headers
        )
