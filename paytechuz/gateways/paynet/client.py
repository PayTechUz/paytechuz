"""
Paynet payment gateway client.
"""
import logging
from typing import Dict, Any, Optional, Union

from paytechuz.core.base import BasePaymentGateway
from paytechuz.core.utils import handle_exceptions


logger = logging.getLogger(__name__)


class PaynetGateway(BasePaymentGateway):
    """
    Paynet payment gateway implementation.

    This class provides methods for interacting with the Paynet payment gateway,
    including creating payment URLs for the Paynet mobile app.
    """

    BASE_URL = "https://app.paynet.uz"

    def __init__(
        self,
        merchant_id: Union[str, int],
        is_test_mode: bool = False,
        **kwargs
    ):
        """
        Initialize the Paynet gateway.

        Args:
            merchant_id: Paynet merchant ID (m parameter)
            is_test_mode: Whether to use the test environment
            **kwargs: Additional arguments (ignored, for backward compatibility)
        """
        super().__init__(is_test_mode)
        self.merchant_id = str(merchant_id)

    def generate_pay_link(
        self,
        id: Union[int, str],
        amount: Optional[Union[int, float, str]] = None
    ) -> str:
        """
        Generate a payment link for Paynet.

        Parameters
        ----------
        id : Union[int, str]
            Unique identifier for the account/payment (c parameter).
        amount : Optional[Union[int, float, str]]
            Payment amount in tiyin (optional, a parameter).

        Returns
        -------
        str
            Paynet payment URL: https://app.paynet.uz/?m={merchant_id}&c={id}&a={amount}
        """
        url = f"{self.BASE_URL}/?m={self.merchant_id}&c={id}"
        if amount is not None:
            url += f"&a={int(amount)}"
        return url

    async def generate_pay_link_async(
        self,
        id: Union[int, str],
        amount: Optional[Union[int, float, str]] = None
    ) -> str:
        """
        Async version of generate_pay_link.

        Parameters
        ----------
        id : Union[int, str]
            Unique identifier for the account/payment.
        amount : Optional[Union[int, float, str]]
            Payment amount in tiyin (optional).

        Returns
        -------
        str
            Paynet payment URL.
        """
        return self.generate_pay_link(id, amount)

    @handle_exceptions
    def create_payment(
        self,
        id: Union[int, str],
        amount: Optional[Union[int, float, str]] = None,
        **kwargs
    ) -> str:
        """
        Create a payment using Paynet.

        Args:
            id: Account or payment ID (c parameter)
            amount: Payment amount in tiyin (optional, a parameter)
            **kwargs: Additional parameters (ignored)

        Returns:
            str: Paynet payment URL
        """
        return self.generate_pay_link(id, amount)

    @handle_exceptions
    async def create_payment_async(
        self,
        id: Union[int, str],
        amount: Optional[Union[int, float, str]] = None,
        **kwargs
    ) -> str:
        """
        Async version of create_payment.

        Args:
            id: Account or payment ID
            amount: Payment amount in tiyin (optional)
            **kwargs: Additional parameters (ignored)

        Returns:
            str: Paynet payment URL
        """
        return await self.generate_pay_link_async(id, amount)

    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status.

        Note: Paynet uses webhooks for payment notifications.
        This method is not implemented for Paynet as payment verification
        is done through webhook callbacks.

        Args:
            transaction_id: The transaction ID to check

        Returns:
            Dict containing payment status and details

        Raises:
            NotImplementedError: Paynet uses webhooks for status updates
        """
        raise NotImplementedError(
            "Paynet uses webhooks for payment status updates. "
            "Implement webhook handlers to receive payment notifications."
        )

    def cancel_payment(
        self,
        transaction_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel payment.

        Note: Payment cancellation in Paynet is done through webhooks.

        Args:
            transaction_id: The transaction ID to cancel
            reason: Optional reason for cancellation

        Returns:
            Dict containing cancellation status and details

        Raises:
            NotImplementedError: Paynet uses webhooks for cancellations
        """
        raise NotImplementedError(
            "Paynet payment cancellation is handled through webhook callbacks. "
            "Implement the CancelTransaction webhook method."
        )
