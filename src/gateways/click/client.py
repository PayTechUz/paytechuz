"""
Click payment gateway client.
"""
import logging
from typing import Dict, Any, Optional, Union

from paytechuz.core.base import BasePaymentGateway
from paytechuz.core.http import HttpClient
from paytechuz.core.constants import ClickNetworks
from paytechuz.core.utils import handle_exceptions
from paytechuz.gateways.click.merchant import ClickMerchantApi

logger = logging.getLogger(__name__)


class ClickGateway(BasePaymentGateway):
    """
    Click payment gateway implementation.

    This class provides methods for interacting with the Click payment gateway,
    including creating payments, checking payment status, and canceling payments.
    """

    def __init__(
        self,
        service_id: str,
        merchant_id: str,
        merchant_user_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        is_test_mode: bool = False
    ):
        """
        Initialize the Click gateway.

        Args:
            service_id: Click service ID
            merchant_id: Click merchant ID
            merchant_user_id: Click merchant user ID
            secret_key: Secret key for authentication
            is_test_mode: Whether to use the test environment
        """
        super().__init__(is_test_mode)
        self.service_id = service_id
        self.merchant_id = merchant_id
        self.merchant_user_id = merchant_user_id
        self.secret_key = secret_key

        # Set the API URL based on the environment
        url = ClickNetworks.TEST_NET if is_test_mode else ClickNetworks.PROD_NET

        # Initialize HTTP client
        self.http_client = HttpClient(base_url=url)

        # Initialize merchant API
        self.merchant_api = ClickMerchantApi(
            http_client=self.http_client,
            service_id=service_id,
            merchant_user_id=merchant_user_id,
            secret_key=secret_key
        )

    @handle_exceptions
    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        **kwargs
    ) -> str:
        """
        Create a payment using Click.

        Args:
            id: The account ID or order ID
            amount: The payment amount in som
            **kwargs: Additional parameters for the payment
                - description: Payment description
                - return_url: URL to return after payment
                - callback_url: URL for payment notifications
                - language: Language code (uz, ru, en)
                - phone: Customer phone number
                - email: Customer email

        Returns:
            Payment URL string for redirecting the user to Click payment page
        """
        # Format amount for URL (no need to convert to tiyin for URL)

        # Extract additional parameters
        description = kwargs.get('description', f'Payment for account {id}')
        return_url = kwargs.get('return_url')
        callback_url = kwargs.get('callback_url')
        # These parameters are not used in the URL but are available in the API
        # language = kwargs.get('language', 'uz')
        # phone = kwargs.get('phone')
        # email = kwargs.get('email')

        # Create payment URL
        payment_url = "https://my.click.uz/services/pay"
        payment_url += f"?service_id={self.service_id}"
        payment_url += f"&merchant_id={self.merchant_id}"
        payment_url += f"&amount={amount}"
        payment_url += f"&transaction_param={id}"

        if return_url:
            payment_url += f"&return_url={return_url}"

        if callback_url:
            payment_url += f"&callback_url={callback_url}"

        if description:
            payment_url += f"&merchant_user_id={description}"

        # Return the payment URL directly
        return payment_url

    @handle_exceptions
    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status using Click merchant API.

        Args:
            transaction_id: The transaction ID to check

        Returns:
            Dict containing payment status and details
        """
        # Extract account_id from transaction_id
        # Format: click_account_id_amount
        parts = transaction_id.split('_')
        if len(parts) < 3 or parts[0] != 'click':
            raise ValueError(
                f"Invalid transaction ID format: {transaction_id}"
            )

        account_id = parts[1]

        # Check payment status using merchant API
        payment_data = self.merchant_api.check_payment(account_id)

        # Extract payment status
        status = payment_data.get('status')

        # Map Click status to our status
        status_mapping = {
            'success': 'paid',
            'processing': 'waiting',
            'failed': 'failed',
            'cancelled': 'cancelled'
        }

        mapped_status = status_mapping.get(status, 'unknown')

        return {
            'transaction_id': transaction_id,
            'status': mapped_status,
            'amount': payment_data.get('amount'),
            'paid_at': payment_data.get('paid_at'),
            'created_at': payment_data.get('created_at'),
            'raw_response': payment_data
        }

    @handle_exceptions
    def cancel_payment(
        self,
        transaction_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel payment using Click merchant API.

        Args:
            transaction_id: The transaction ID to cancel
            reason: Optional reason for cancellation

        Returns:
            Dict containing cancellation status and details
        """
        # Extract account_id from transaction_id
        # Format: click_account_id_amount
        parts = transaction_id.split('_')
        if len(parts) < 3 or parts[0] != 'click':
            raise ValueError(
                f"Invalid transaction ID format: {transaction_id}"
            )

        account_id = parts[1]

        # Cancel payment using merchant API
        cancel_data = self.merchant_api.cancel_payment(account_id, reason)

        return {
            'transaction_id': transaction_id,
            'status': 'cancelled',
            'cancelled_at': cancel_data.get('cancelled_at'),
            'raw_response': cancel_data
        }
