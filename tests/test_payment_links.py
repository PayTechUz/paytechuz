"""
Unit tests for payment link generation across the gateways.
"""
import base64

import pytest

from paytechuz import create_gateway
from paytechuz.gateways.payme import PaymeGateway
from paytechuz.gateways.paynet import PaynetGateway
from paytechuz.gateways.uzum import UzumGateway


class TestPaymeLinks:
    """Payme checkout URL generation."""

    @pytest.fixture
    def payme(self):
        return PaymeGateway(payme_id="merchant", payme_key="key", is_test_mode=True)

    @staticmethod
    def decode(link):
        return base64.b64decode(link.rsplit("/", 1)[1]).decode("utf-8")

    def test_default_account_field(self, payme):
        link = payme.create_payment(
            id=123, amount=1500, return_url="https://example.com/return"
        )

        assert link.startswith("https://test.paycom.uz/")
        assert self.decode(link) == (
            "m=merchant;ac.order_id=123;a=150000;c=https://example.com/return"
        )

    def test_custom_account_field(self, payme):
        link = payme.create_payment(
            id=7, amount=1500, return_url="", account_field_name="id"
        )

        assert self.decode(link) == "m=merchant;ac.id=7;a=150000;c="

    def test_amount_is_converted_to_tiyin(self, payme):
        link = payme.create_payment(id=1, amount=1234.56, return_url="")

        assert "a=123456;" in self.decode(link)

    def test_production_host(self):
        gateway = PaymeGateway(payme_id="m", payme_key="k", is_test_mode=False)
        link = gateway.create_payment(id=1, amount=1, return_url="")

        assert link.startswith("https://checkout.paycom.uz/")


class TestPaynetLinks:
    """Paynet app URL generation."""

    def test_with_amount(self):
        gateway = PaynetGateway(merchant_id=5678)
        assert gateway.create_payment(id="order_1", amount=15000000) == (
            "https://app.paynet.uz/?m=5678&c=order_1&a=15000000"
        )

    def test_without_amount(self):
        gateway = PaynetGateway(merchant_id="5678")
        assert gateway.create_payment(id="order_1") == (
            "https://app.paynet.uz/?m=5678&c=order_1"
        )

    def test_merchant_id_accepts_int_and_str(self):
        assert PaynetGateway(merchant_id=1).merchant_id == "1"
        assert PaynetGateway(merchant_id="1").merchant_id == "1"


class TestUzumLinks:
    """Uzum Biller URL generation."""

    def test_amount_is_converted_to_tiyin(self):
        gateway = UzumGateway(service_id="4986")
        link = gateway.create_payment(
            id=156, amount=100000, return_url="https://example.com/cb"
        )

        assert link == (
            "https://www.uzumbank.uz/open-service"
            "?serviceId=4986&order_id=156&amount=10000000"
            "&redirectUrl=https://example.com/cb"
        )

    def test_return_url_is_optional(self):
        gateway = UzumGateway(service_id="4986")
        link = gateway.create_payment(id=1, amount=1)

        assert "redirectUrl" not in link

    def test_refund_requires_credentials(self):
        gateway = UzumGateway(service_id="4986")

        with pytest.raises(ValueError, match="terminal_id and api_key"):
            gateway.cancel_payment(id="1", amount=100)


class TestFactory:
    """create_gateway() dispatch."""

    @pytest.mark.parametrize("name,kwargs,expected", [
        ("payme", {"payme_id": "m", "payme_key": "k"}, PaymeGateway),
        ("paynet", {"merchant_id": 1}, PaynetGateway),
        ("uzum", {"service_id": "s"}, UzumGateway),
    ])
    def test_known_gateways(self, name, kwargs, expected):
        assert isinstance(create_gateway(name, **kwargs), expected)

    def test_is_case_insensitive(self):
        assert isinstance(
            create_gateway("PAYME", payme_id="m", payme_key="k"), PaymeGateway
        )

    def test_unknown_gateway(self):
        with pytest.raises(ValueError, match="Unsupported gateway type"):
            create_gateway("visa")
