"""
Payme payment gateway client.
"""
import base64
import logging
from typing import Dict, Any, Optional, Union

from paytechuz.core.http import HttpClient
from paytechuz.core.base import BasePaymentGateway
from paytechuz.core.utils import handle_exceptions

from paytechuz.gateways.payme.cards import PaymeCards
from paytechuz.gateways.payme.receipts import PaymeReceipts
from paytechuz.gateways.payme.constants import PaymeNetworks


logger = logging.getLogger(__name__)


class PaymeGateway(BasePaymentGateway):
    """
    Payme payment gateway implementation.

    This class provides methods for interacting with the Payme payment gateway,
    including creating payments, checking payment status, and canceling payments.
    """

    def __init__(
        self,
        payme_id: str,
        payme_key: Optional[str] = None,
        fallback_id: Optional[str] = None,
        is_test_mode: bool = False,
        **kwargs
    ):
        """
        Initialize the Payme gateway.

        Args:
            payme_id: Payme merchant ID
            payme_key: Payme merchant key for authentication
            fallback_id: Fallback merchant ID
            is_test_mode: Whether to use the test environment
            **kwargs: Additional arguments (ignored, for backward compatibility)
        """
        super().__init__(is_test_mode)
        self.payme_id = payme_id
        self.payme_key = payme_key
        self.fallback_id = fallback_id

        # Set the API URL based on the environment
        url = PaymeNetworks.TEST_NET if is_test_mode else PaymeNetworks.PROD_NET

        # Initialize HTTP client
        self.http_client = HttpClient(base_url=url)

        # Initialize components
        self.cards = PaymeCards(http_client=self.http_client, payme_id=payme_id)
        self.receipts = PaymeReceipts(
            http_client=self.http_client,
            payme_id=payme_id,
            payme_key=payme_key
        )

    def generate_pay_link(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str,
        account_field_name: str = "order_id"
    ) -> str:
        """
        Generate a payment link for a specific order.

        Parameters
        ----------
        id : Union[int, str]
            Unique identifier for the account/order.
        amount : Union[int, float, str]
            Payment amount in som.
        return_url : str
            URL to redirect after payment completion.
        account_field_name : str, optional
            Field name for account identifier (default: "order_id").

        Returns
        -------
        str
            Payme checkout URL with encoded parameters.

        References
        ----------
        https://developer.help.paycom.uz/initsializatsiya-platezhey/
        """
        # Convert amount to tiyin (1 som = 100 tiyin)
        amount_tiyin = int(float(amount) * 100)

        # Build parameters
        params = (
            f'm={self.payme_id};'
            f'ac.{account_field_name}={id};'
            f'a={amount_tiyin};'
            f'c={return_url}'
        )
        encoded_params = base64.b64encode(params.encode("utf-8")).decode("utf-8")

        # Return URL based on environment
        base_url = "https://test.paycom.uz" if self.is_test_mode else "https://checkout.paycom.uz"
        return f"{base_url}/{encoded_params}"

    async def generate_pay_link_async(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str,
        account_field_name: str = "order_id"
    ) -> str:
        """
        Async version of generate_pay_link.

        Parameters
        ----------
        id : Union[int, str]
            Unique identifier for the account/order.
        amount : Union[int, float, str]
            Payment amount in som.
        return_url : str
            URL to redirect after payment completion.
        account_field_name : str, optional
            Field name for account identifier (default: "order_id").

        Returns
        -------
        str
            Payme checkout URL with encoded parameters.
        """
        return self.generate_pay_link(id, amount, return_url, account_field_name)

    @handle_exceptions
    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = "",
        account_field_name: str = "order_id"
    ) -> str:
        """
        Create a payment using Payme.

        Args:
            id: Account or order ID
            amount: Payment amount in som
            return_url: Return URL after payment (default: "")
            account_field_name: Field name for account ID (default: "order_id")

        Returns:
            str: Payme payment URL
        """
        return self.generate_pay_link(id, amount, return_url, account_field_name)

    @handle_exceptions
    async def create_payment_async(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        return_url: str = "",
        account_field_name: str = "order_id"
    ) -> str:
        """
        Async version of create_payment.

        Args:
            id: Account or order ID
            amount: Payment amount in som
            return_url: Return URL after payment (default: "")
            account_field_name: Field name for account ID (default: "order_id")

        Returns:
            str: Payme payment URL
        """
        return await self.generate_pay_link_async(id, amount, return_url, account_field_name)

    @handle_exceptions
    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status using Payme receipts.

        Args:
            transaction_id: The receipt ID to check

        Returns:
            Dict containing payment status and details
        """
        receipt_data = self.receipts.check(receipt_id=transaction_id)

        # Extract receipt status
        receipt = receipt_data.get('receipt', {})
        status = receipt.get('state')

        # Map Payme status to our status
        status_mapping = {
            0: 'created',
            1: 'waiting',
            2: 'paid',
            3: 'cancelled',
            4: 'refunded'
        }

        mapped_status = status_mapping.get(status, 'unknown')

        return {
            'transaction_id': transaction_id,
            'status': mapped_status,
            'amount': receipt.get('amount') / 100,  # Convert from tiyin to som
            'paid_at': receipt.get('pay_time'),
            'created_at': receipt.get('create_time'),
            'cancelled_at': receipt.get('cancel_time'),
            'raw_response': receipt_data
        }

    @handle_exceptions
    def cancel_payment(
        self,
        transaction_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel payment using Payme receipts.

        Args:
            transaction_id: The receipt ID to cancel
            reason: Optional reason for cancellation

        Returns:
            Dict containing cancellation status and details
        """
        receipt_data = self.receipts.cancel(
            receipt_id=transaction_id,
            reason=reason or "Cancelled by merchant"
        )

        # Extract receipt status
        receipt = receipt_data.get('receipt', {})
        status = receipt.get('state')

        return {
            'transaction_id': transaction_id,
            'status': 'cancelled' if status == 3 else 'unknown',
            'cancelled_at': receipt.get('cancel_time'),
            'raw_response': receipt_data
        }
