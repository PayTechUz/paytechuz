"""
Payme receipts operations.
"""
# base64 is used indirectly through generate_basic_auth
import logging
from typing import Dict, Any, Optional

from paytechuz.core.http import HttpClient
from paytechuz.gateways.payme.constants import PaymeEndpoints
from paytechuz.core.utils import handle_exceptions


logger = logging.getLogger(__name__)


class PaymeReceipts:
    """
    Payme receipts operations.

    This class provides methods for working with receipts in the Payme payment system,
    including creating receipts, paying receipts, and checking receipt status.
    """

    def __init__(
        self,
        http_client: HttpClient,
        payme_id: str,
        payme_key: Optional[str] = None
    ):
        """
        Initialize the Payme receipts component.

        Args:
            http_client: HTTP client for making requests
            payme_id: Payme merchant ID
            payme_key: Payme merchant key for authentication
        """
        self.http_client = http_client
        self.payme_id = payme_id
        self.payme_key = payme_key

    def _get_auth_headers(self, language: str = 'uz') -> Dict[str, str]:
        """
        Get authentication headers for Payme API.

        Args:
            language: Language code (uz, ru, en)

        Returns:
            Dict containing authentication headers
        """
        headers = {
            "Accept-Language": language,
            "X-Auth": f"{self.payme_id}:{self.payme_key}"
        }

        return headers

    @handle_exceptions
    def create(
        self,
        amount: int,
        account: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new receipt.

        Args:
            amount: Payment amount in tiyin (1 som = 100 tiyin)
            account: Account information (e.g., {"account_id": "12345"})
            **kwargs: Additional parameters
                - description: Payment description
                - detail: Payment details
                - callback_url: URL to redirect after payment
                - return_url: URL to return after payment
                - phone: Customer phone number
                - email: Customer email
                - language: Language code (uz, ru, en)
                - expire_minutes: Payment expiration time in minutes

        Returns:
            Dict containing receipt creation response
        """
        # Extract additional parameters
        description = kwargs.get('description', 'Payment')
        detail = kwargs.get('detail', {})
        callback_url = kwargs.get('callback_url')
        return_url = kwargs.get('return_url')
        phone = kwargs.get('phone')
        email = kwargs.get('email')
        language = kwargs.get('language', 'uz')
        expire_minutes = kwargs.get('expire_minutes', 60)  # Default 1 hour

        # Prepare request data
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.RECEIPTS_CREATE,
            "params": {
                "amount": amount,
                "account": account,
                "description": description,
                "detail": detail
            },
            "id": 1
        }

        # Add optional parameters
        if callback_url:
            data["params"]["callback_url"] = callback_url

        if return_url:
            data["params"]["return_url"] = return_url

        if phone:
            data["params"]["phone"] = phone

        if email:
            data["params"]["email"] = email

        if expire_minutes:
            data["params"]["expire_minutes"] = expire_minutes

        # Get authentication headers
        headers = self._get_auth_headers(language)

        # Make request
        response = self.http_client.post(
            endpoint="",
            json_data=data,
            headers=headers
        )

        return response

    @handle_exceptions
    def pay(
        self,
        receipt_id: str,
        token: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Pay a receipt with a card token.

        Args:
            receipt_id: Receipt ID
            token: Card token
            **kwargs: Additional parameters
                - language: Language code (uz, ru, en)

        Returns:
            Dict containing receipt payment response
        """
        # Extract additional parameters
        language = kwargs.get('language', 'uz')

        # Prepare request data
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.RECEIPTS_PAY,
            "params": {
                "id": receipt_id,
                "token": token
            },
            "id": 1
        }

        # Get authentication headers
        headers = self._get_auth_headers(language)

        # Make request
        response = self.http_client.post(
            endpoint="",
            json_data=data,
            headers=headers
        )

        return response

    @handle_exceptions
    def send(
        self,
        receipt_id: str,
        phone: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Send a receipt to a phone number.

        Args:
            receipt_id: Receipt ID
            phone: Phone number
            **kwargs: Additional parameters
                - language: Language code (uz, ru, en)

        Returns:
            Dict containing receipt sending response
        """
        # Extract additional parameters
        language = kwargs.get('language', 'uz')

        # Prepare request data
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.RECEIPTS_SEND,
            "params": {
                "id": receipt_id,
                "phone": phone
            },
            "id": 1
        }

        # Get authentication headers
        headers = self._get_auth_headers(language)

        # Make request
        response = self.http_client.post(
            endpoint="",
            json_data=data,
            headers=headers
        )

        return response

    @handle_exceptions
    def check(self, receipt_id: str, **kwargs) -> Dict[str, Any]:
        """
        Check receipt status.

        Args:
            receipt_id: Receipt ID
            **kwargs: Additional parameters
                - language: Language code (uz, ru, en)

        Returns:
            Dict containing receipt status response
        """
        # Extract additional parameters
        language = kwargs.get('language', 'uz')

        # Prepare request data
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.RECEIPTS_CHECK,
            "params": {
                "id": receipt_id
            },
            "id": 1
        }

        # Get authentication headers
        headers = self._get_auth_headers(language)

        # Make request
        response = self.http_client.post(
            endpoint="",
            json_data=data,
            headers=headers
        )

        return response

    @handle_exceptions
    def cancel(
        self,
        receipt_id: str,
        reason: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Cancel a receipt.

        Args:
            receipt_id: Receipt ID
            reason: Cancellation reason
            **kwargs: Additional parameters
                - language: Language code (uz, ru, en)

        Returns:
            Dict containing receipt cancellation response
        """
        # Extract additional parameters
        language = kwargs.get('language', 'uz')

        # Prepare request data
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.RECEIPTS_CANCEL,
            "params": {
                "id": receipt_id
            },
            "id": 1
        }

        # Add reason if provided
        if reason:
            data["params"]["reason"] = reason

        # Get authentication headers
        headers = self._get_auth_headers(language)

        # Make request
        response = self.http_client.post(
            endpoint="",
            json_data=data,
            headers=headers
        )

        return response

    @handle_exceptions
    def get(self, receipt_id: str, **kwargs) -> Dict[str, Any]:
        """
        Get receipt details.

        Args:
            receipt_id: Receipt ID
            **kwargs: Additional parameters
                - language: Language code (uz, ru, en)

        Returns:
            Dict containing receipt details response
        """
        # Extract additional parameters
        language = kwargs.get('language', 'uz')

        # Prepare request data
        data = {
            "jsonrpc": "2.0",
            "method": PaymeEndpoints.RECEIPTS_GET,
            "params": {
                "id": receipt_id
            },
            "id": 1
        }

        # Get authentication headers
        headers = self._get_auth_headers(language)

        # Make request
        response = self.http_client.post(
            endpoint="",
            json_data=data,
            headers=headers
        )

        return response
