"""
Exceptions for payment gateways.
"""
from typing import Optional, Dict, Any


class PaymentException(Exception):
    """Base exception for all payment exceptions."""
    code = "payment_error"
    message = "Payment error occurred"
    data: Dict[str, Any] = {}

    def __init__(
        self,
        message: Optional[str] = None,
        code: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the exception.

        Args:
            message: Custom error message
            code: Custom error code
            data: Additional error data
        """
        self.message = message or self.message
        self.code = code or self.code
        self.data = data or self.data
        super().__init__(self.message)

    def as_dict(self) -> Dict[str, Any]:
        """
        Convert the exception to a dictionary.

        Returns:
            Dict containing error details
        """
        return {
            "code": self.code,
            "message": self.message,
            "data": self.data
        }

# Authentication and Authorization Exceptions


class AuthenticationError(PaymentException):
    """Exception raised when authentication fails."""
    code = "authentication_error"
    message = "Authentication failed"


class InvalidCredentials(AuthenticationError):
    """Exception raised when credentials are invalid."""
    code = "invalid_credentials"
    message = "Invalid credentials provided"


class PermissionDenied(AuthenticationError):
    """Exception raised when permission is denied."""
    code = "permission_denied"
    message = "Permission denied"


class InvalidServiceId(AuthenticationError):
    """Exception raised when service ID is invalid."""
    code = "invalid_service_id"
    message = "Invalid service ID"


# Transaction Exceptions
class TransactionError(PaymentException):
    """Base exception for transaction errors."""
    code = "transaction_error"
    message = "Transaction error occurred"


class TransactionNotFound(TransactionError):
    """Exception raised when a transaction is not found."""
    code = "transaction_not_found"
    message = "Transaction not found"


class TransactionAlreadyExists(TransactionError):
    """Exception raised when a transaction already exists."""
    code = "transaction_already_exists"
    message = "Transaction already exists"


class AlreadyPaid(TransactionError):
    """Exception raised when payment has already been made."""
    code = "already_paid"
    message = "Payment has already been made"


class PaymentAlreadyMade(TransactionError):
    """Exception raised when payment has already been made."""
    code = "payment_already_made"
    message = "Payment has already been made"


class TransactionCancelled(TransactionError):
    """Exception raised when a transaction is cancelled."""
    code = "transaction_cancelled"
    message = "Transaction has been cancelled"


class TransactionInProgress(TransactionError):
    """Exception raised when a transaction is in progress."""
    code = "transaction_in_progress"
    message = "Transaction is in progress"


class TransactionCompleted(TransactionError):
    """Exception raised when a transaction is already completed."""
    code = "transaction_completed"
    message = "Transaction is already completed"


# Account Exceptions
class AccountError(PaymentException):
    """Base exception for account errors."""
    code = "account_error"
    message = "Account error occurred"


class AccountNotFound(AccountError):
    """Exception raised when an account is not found."""
    code = "account_not_found"
    message = "Account not found"


class InvalidAccount(AccountError):
    """Exception raised when an account is invalid."""
    code = "invalid_account"
    message = "Invalid account"


# Amount Exceptions
class AmountError(PaymentException):
    """Base exception for amount errors."""
    code = "amount_error"
    message = "Amount error occurred"


class InvalidAmount(AmountError):
    """Exception raised when an amount is invalid."""
    code = "invalid_amount"
    message = "Invalid amount"


class InsufficientFunds(AmountError):
    """Exception raised when there are insufficient funds."""
    code = "insufficient_funds"
    message = "Insufficient funds"


# Method Exceptions
class MethodError(PaymentException):
    """Base exception for method errors."""
    code = "method_error"
    message = "Method error occurred"


class MethodNotFound(MethodError):
    """Exception raised when a method is not found."""
    code = "method_not_found"
    message = "Method not found"


class UnsupportedMethod(MethodError):
    """Exception raised when a method is not supported."""
    code = "unsupported_method"
    message = "Method not supported"


class ServiceNotFound(MethodError):
    """Exception raised when a service is not found."""
    code = "service_not_found"
    message = "Service not found"


# System Exceptions
class SystemError(PaymentException):
    """Base exception for system errors."""
    code = "system_error"
    message = "System error occurred"


class InternalServiceError(SystemError):
    """Exception raised when an internal service error occurs."""
    code = "internal_service_error"
    message = "Internal service error"


class ExternalServiceError(SystemError):
    """Exception raised when an external service error occurs."""
    code = "external_service_error"
    message = "External service error"


class TimeoutError(SystemError):
    """Exception raised when a timeout occurs."""
    code = "timeout_error"
    message = "Operation timed out"


# Create a list of exceptions that should not be wrapped
exception_whitelist = (
    PaymentException,
    AuthenticationError,
    InvalidCredentials,
    PermissionDenied,
    TransactionError,
    TransactionNotFound,
    TransactionAlreadyExists,
    TransactionCancelled,
    TransactionInProgress,
    TransactionCompleted,
    AccountError,
    AccountNotFound,
    InvalidAccount,
    AmountError,
    InvalidAmount,
    InsufficientFunds,
    MethodError,
    MethodNotFound,
    UnsupportedMethod,
    ServiceNotFound,
    SystemError,
    InternalServiceError,
    ExternalServiceError,
    TimeoutError,
)
