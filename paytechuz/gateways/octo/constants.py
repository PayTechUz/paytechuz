"""
Constants for Octo payment gateway.
"""


class OctoEndpoints:
    """Octo API endpoints."""
    PREPARE_PAYMENT = "/prepare_payment"
    REFUND = "/refund"


class OctoNetworks:
    """Octo API networks.

    Note: Octo uses a single base URL for both test and production.
    Test mode is controlled via the ``test`` parameter in the request body.
    """
    PROD_NET = "https://secure.octo.uz"
    TEST_NET = "https://secure.octo.uz"


class OctoStatus:
    """Possible Octo transaction statuses."""
    CREATED = "created"
    WAITING_PAY = "waiting_pay"
    SUCCEEDED = "succeeded"
    CANCELED = "canceled"
    FAILED = "failed"
    REFUNDED = "refunded"


class OctoPaymentMethods:
    """Available Octo payment methods."""
    BANK_CARD = "bank_card"
    UZCARD = "uzcard"
    HUMO = "humo"

    ALL = [
        {"method": BANK_CARD},
        {"method": UZCARD},
        {"method": HUMO},
    ]
