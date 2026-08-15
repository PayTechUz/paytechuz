"""
Factory helper for creating payment gateway instances by name.
"""
from paytechuz.core.base import BasePaymentGateway
from paytechuz.core.constants import PaymentGateway

from paytechuz.gateways.payme.client import PaymeGateway
from paytechuz.gateways.click.client import ClickGateway
from paytechuz.gateways.uzum.client import UzumGateway
from paytechuz.gateways.paynet.client import PaynetGateway
from paytechuz.gateways.octo.client import OctoGateway


GATEWAYS = {
    PaymentGateway.PAYME.value: PaymeGateway,
    PaymentGateway.CLICK.value: ClickGateway,
    PaymentGateway.UZUM.value: UzumGateway,
    PaymentGateway.PAYNET.value: PaynetGateway,
    PaymentGateway.OCTO.value: OctoGateway,
}


def create_gateway(gateway_type: str, **kwargs) -> BasePaymentGateway:
    """
    Create a payment gateway instance.

    Args:
        gateway_type: Type of gateway ('payme', 'click', 'uzum', 'paynet' or 'octo')
        **kwargs: Gateway-specific configuration

    Returns:
        Payment gateway instance

    Raises:
        ValueError: If the gateway type is not supported
    """
    gateway_class = GATEWAYS.get(gateway_type.lower())
    if gateway_class is None:
        supported = ', '.join(sorted(GATEWAYS))
        raise ValueError(
            f"Unsupported gateway type: {gateway_type}. Supported: {supported}"
        )

    return gateway_class(**kwargs)
