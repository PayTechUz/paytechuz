"""
Django webhook handlers for PayTechUZ.

Each handler is a plain Django ``View`` that implements the protocol of one
payment provider. Subclass a handler and override its event hooks
(``successfully_payment``, ``cancelled_payment``, ...) to run your own
business logic.
"""
from .payme import PaymeWebhook
from .click import ClickWebhook
from .uzum import UzumWebhook
from .paynet import PaynetWebhook
from .octo import OctoWebhook

__all__ = [
    'PaymeWebhook',
    'ClickWebhook',
    'UzumWebhook',
    'PaynetWebhook',
    'OctoWebhook',
]
