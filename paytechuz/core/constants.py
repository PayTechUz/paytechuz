"""
Constants for payment gateways.
"""
from enum import Enum


class TransactionState(Enum):
    """Transaction states."""
    CREATED = 0
    INITIATING = 1
    SUCCESSFULLY = 2
    CANCELED = -2
    CANCELED_DURING_INIT = -1


class PaymentGateway(Enum):
    """Payment gateway types."""
    PAYME = "payme"
    CLICK = "click"
    UZUM = "uzum"
    PAYNET = "paynet"
    OCTO = "octo"
