"""
Click payment gateway client.
"""
import logging
from typing import Dict, Any, Optional, Union

from paytechuz.core.http import HttpClient
from paytechuz.core.base import BasePaymentGateway
from paytechuz.core.utils import handle_exceptions
from paytechuz.gateways.click.constants import ClickNetworks
from paytechuz.gateways.click.merchant import ClickMerchantApi


logger = logging.getLogger(__name__)


class ClickGateway(BasePaymentGateway):
    """
    Click payment gateway implementation.

    This class provides methods for interacting with the Click payment gateway,
    including creating payments, checking payment status, and canceling payments.
    """

    PAYMENT_URL = "https://my.click.uz/services/pay"

    def __init__(
        self,
        service_id: str,
        merchant_id: str,
        merchant_user_id: Optional[str] = None,
        secret_key: Optional[str] = None,
        is_test_mode: bool = False,
        **kwargs
    ):
        """
        Initialize the Click gateway.

        Args:
            service_id: Click service ID
            merchant_id: Click merchant ID
            merchant_user_id: Click merchant user ID
            secret_key: Secret key for authentication
            is_test_mode: Whether to use the test environment
            **kwargs: Additional arguments (ignored, for backward compatibility)
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
            **kwargs: Additional query parameters for the payment URL
                - description: Payment description
                - return_url: URL to return after payment
                - merchant_user_id: Merchant user ID (defaults to the one
                  passed to the constructor)
                - any other key is appended as a query parameter

        Returns:
            Payment URL string
        """
        params = {
            'service_id': self.service_id,
            'merchant_id': self.merchant_id,
            'amount': amount,
            'transaction_param': id,
        }

        extra = dict(kwargs)
        merchant_user_id = extra.pop('merchant_user_id', self.merchant_user_id)

        for key, value in extra.items():
            if value is not None:
                params[key] = value

        if merchant_user_id:
            params['merchant_user_id'] = merchant_user_id

        query = "&".join(f"{key}={value}" for key, value in params.items())
        return f"{self.PAYMENT_URL}?{query}"

    @staticmethod
    def _parse_transaction_id(transaction_id: str) -> str:
        """
        Extract the account ID from a ``click_<account_id>_<amount>`` string.

        The account ID itself may contain underscores.

        Raises:
            ValueError: If the transaction ID does not match the format
        """
        parts = transaction_id.split('_')
        if len(parts) < 3 or parts[0] != 'click':
            raise ValueError(f"Invalid transaction ID format: {transaction_id}")

        return '_'.join(parts[1:-1])

    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status using Click merchant API.

        Args:
            transaction_id: The transaction ID to check

        Returns:
            Dict containing payment status and details

        Raises:
            ValueError: If the transaction ID format is invalid
        """
        account_id = self._parse_transaction_id(transaction_id)

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

        Raises:
            ValueError: If the transaction ID format is invalid
        """
        account_id = self._parse_transaction_id(transaction_id)

        # Cancel payment using merchant API
        cancel_data = self.merchant_api.cancel_payment(account_id, reason)

        return {
            'transaction_id': transaction_id,
            'status': 'cancelled',
            'cancelled_at': cancel_data.get('cancelled_at'),
            'raw_response': cancel_data
        }

    def card_token_request(
        self,
        card_number: str,
        expire_date: str,
        temporary: int = 0
    ) -> Dict[str, Any]:
        """
        Request a card token for card payment.

        Args:
            card_number: Card number (e.g., "5614681005030279")
            expire_date: Card expiration date (e.g., "0330" for March 2030)
            temporary: Whether the token is temporary (0 or 1)

        Returns:
            Dict containing card token and related information
        """
        return self.merchant_api.card_token_request(
            card_number=card_number,
            expire_date=expire_date,
            temporary=temporary
        )

    def card_token_verify(
        self,
        card_token: str,
        sms_code: Union[int, str]
    ) -> Dict[str, Any]:
        """
        Verify a card token with SMS code.

        Args:
            card_token: Card token from card_token_request
            sms_code: SMS code sent to the card holder

        Returns:
            Dict containing verification status and card information
        """
        return self.merchant_api.card_token_verify(
            card_token=card_token,
            sms_code=sms_code
        )

    def card_token_payment(
        self,
        card_token: str,
        amount: Union[int, float],
        transaction_parameter: str
    ) -> Dict[str, Any]:
        """
        Make a payment using a verified card token.

        Args:
            card_token: Verified card token
            amount: Payment amount in som
            transaction_parameter: Unique transaction parameter

        Returns:
            Dict containing payment status and payment ID
        """
        return self.merchant_api.card_token_payment(
            card_token=card_token,
            amount=amount,
            transaction_parameter=transaction_parameter
        )
