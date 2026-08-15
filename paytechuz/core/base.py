"""
Base classes for payment gateways.
"""
import base64
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union

from paytechuz.core.exceptions import PermissionDenied


class BasePaymentGateway(ABC):
    """
    Base class for all payment gateways.

    This abstract class defines the common interface that all payment gateways
    must implement. It provides a consistent API for creating, checking, and
    canceling payments regardless of the underlying payment provider.
    """

    def __init__(self, is_test_mode: bool = False):
        """
        Initialize the payment gateway.

        Args:
            is_test_mode (bool): Whether to use the test environment
        """
        self.is_test_mode = is_test_mode

    @abstractmethod
    def create_payment(
        self,
        id: Union[int, str],
        amount: Union[int, float, str],
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a payment.

        Args:
            id: The account ID or order ID
            amount: The payment amount
            **kwargs: Additional parameters specific to the payment gateway

        Returns:
            Dict containing payment details including transaction ID
        """
        raise NotImplementedError

    @abstractmethod
    def check_payment(self, transaction_id: str) -> Dict[str, Any]:
        """
        Check payment status.

        Args:
            transaction_id: The transaction ID to check

        Returns:
            Dict containing payment status and details
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_payment(
        self,
        transaction_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cancel payment.

        Args:
            transaction_id: The transaction ID to cancel
            reason: Optional reason for cancellation

        Returns:
            Dict containing cancellation status and details
        """
        raise NotImplementedError


class BaseWebhookHandler(ABC):
    """
    Base class for payment gateway webhook handlers.

    This abstract class defines the common interface for handling webhook
    callbacks from payment gateways.
    """

    @abstractmethod
    def handle_webhook(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook data from payment gateway.

        Args:
            data: The webhook data received from the payment gateway

        Returns:
            Dict containing the response to be sent back to the payment gateway
        """
        raise NotImplementedError


class BasePaymentProcessor:
    """
    Base class for payment processors.

    This abstract class defines the common interface for processing payments.
    """

    def check_basic_auth(
        self,
        auth_header: Optional[str],
        expected_username: Optional[str] = None,
        expected_password: Optional[str] = None
    ) -> None:
        """
        Check Basic Authentication.

        Args:
            auth_header: The Authorization header value
            expected_username: The expected username (optional)
            expected_password: The expected password (optional)

        Raises:
            PermissionDenied: If authentication fails
        """
        if not auth_header:
            raise PermissionDenied("Missing authentication credentials")

        try:
            parts = auth_header.split()
            if len(parts) != 2 or parts[0].lower() != 'basic':
                raise PermissionDenied("Invalid authentication format")

            try:
                decoded = base64.b64decode(parts[1]).decode('utf-8')
            except Exception:
                raise PermissionDenied("Invalid base64 encoding")

            if ':' not in decoded:
                raise PermissionDenied("Invalid credentials format")

            username, password = decoded.split(':', 1)

            if expected_username is not None and username != expected_username:
                raise PermissionDenied("Invalid credentials")

            if expected_password is not None and password != expected_password:
                raise PermissionDenied("Invalid credentials")

        except PermissionDenied:
            raise
        except Exception as e:
            raise PermissionDenied(f"Authentication error: {str(e)}")
