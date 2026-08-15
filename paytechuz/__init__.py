"""
PayTechUZ - Unified payment library for Uzbekistan payment systems.

This library provides a unified interface for working with Payme, Click, Uzum,
Paynet and Octo payment systems in Uzbekistan. It supports Django and FastAPI.
"""

__version__ = '0.4.0b2'

# Check framework availability
try:
    import django  # noqa: F401
    HAS_DJANGO = True
except ImportError:
    HAS_DJANGO = False

try:
    import fastapi  # noqa: F401
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False

# Import core components
from paytechuz.core.base import BasePaymentGateway  # noqa: E402
from paytechuz.core.constants import PaymentGateway  # noqa: E402
from paytechuz.gateways.payme.client import PaymeGateway  # noqa: E402
from paytechuz.gateways.click.client import ClickGateway  # noqa: E402
from paytechuz.gateways.uzum.client import UzumGateway  # noqa: E402
from paytechuz.gateways.paynet.client import PaynetGateway  # noqa: E402
from paytechuz.gateways.octo.client import OctoGateway  # noqa: E402
from paytechuz.factory import create_gateway  # noqa: E402

# Import dependency checker for users who need it
from paytechuz.core.dependencies import (  # noqa: E402
    check_dependencies,
    require_framework,
    get_missing_dependencies,
    DependencyError
)

__all__ = [
    # Version
    '__version__',

    # Framework availability flags
    'HAS_DJANGO',
    'HAS_FASTAPI',

    # Core classes
    'BasePaymentGateway',
    'PaymentGateway',

    # Gateways
    'PaymeGateway',
    'ClickGateway',
    'UzumGateway',
    'PaynetGateway',
    'OctoGateway',

    # Factory
    'create_gateway',

    # Dependency management
    'check_dependencies',
    'require_framework',
    'get_missing_dependencies',
    'DependencyError',
]
