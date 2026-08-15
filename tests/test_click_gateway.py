"""
Unit tests for ClickGateway class.
"""
import pytest
from unittest.mock import Mock, patch
from paytechuz.gateways.click.client import ClickGateway


class TestClickGateway:
    """Test cases for ClickGateway class."""

    @pytest.fixture
    def click_gateway(self):
        """Create a ClickGateway instance for testing."""
        return ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            merchant_user_id="test_merchant_user_id",
            secret_key="test_secret_key",
            is_test_mode=True
        )

    @pytest.fixture
    def click_gateway_no_merchant_user(self):
        """Create a ClickGateway instance without merchant_user_id."""
        return ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            is_test_mode=True
        )

    def test_create_payment_basic(self, click_gateway):
        """Test basic payment creation."""
        payment_url = click_gateway.create_payment(
            id="order_123",
            amount=150000
        )

        expected_params = [
            "service_id=test_service_id",
            "merchant_id=test_merchant_id",
            "amount=150000",
            "transaction_param=order_123",
            "merchant_user_id=test_merchant_user_id"
        ]

        assert isinstance(payment_url, str)
        assert payment_url.startswith("https://my.click.uz/services/pay?")
        for param in expected_params:
            assert param in payment_url

        # No description is injected unless the caller passes one
        assert "description=" not in payment_url

    def test_create_payment_with_optional_params(self, click_gateway):
        """Test payment creation with optional parameters."""
        payment_url = click_gateway.create_payment(
            id="order_456",
            amount=250000,
            description="Custom payment description",
            return_url="https://example.com/return",
            callback_url="https://example.com/callback"
        )

        expected_params = [
            "service_id=test_service_id",
            "merchant_id=test_merchant_id",
            "amount=250000",
            "transaction_param=order_456",
            "description=Custom payment description",
            "return_url=https://example.com/return",
            "callback_url=https://example.com/callback",
            "merchant_user_id=test_merchant_user_id"
        ]

        assert isinstance(payment_url, str)
        for param in expected_params:
            assert param in payment_url

    def test_create_payment_without_merchant_user_id(self, click_gateway_no_merchant_user):
        """Test payment creation without merchant_user_id."""
        payment_url = click_gateway_no_merchant_user.create_payment(
            id="order_789",
            amount=100000
        )

        assert isinstance(payment_url, str)
        assert "merchant_user_id" not in payment_url
        assert "service_id=test_service_id" in payment_url
        assert "merchant_id=test_merchant_id" in payment_url

    @patch('paytechuz.gateways.click.client.ClickMerchantApi')
    def test_check_payment_success(self, mock_merchant_api, click_gateway):
        """Test successful payment status check."""
        # Mock the merchant API response
        mock_api_instance = Mock()
        mock_merchant_api.return_value = mock_api_instance
        mock_api_instance.check_payment.return_value = {
            'status': 'success',
            'amount': 150000,
            'paid_at': '2024-01-01T12:00:00Z',
            'created_at': '2024-01-01T11:00:00Z'
        }

        # Reinitialize gateway to use mocked merchant API
        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            merchant_user_id="test_merchant_user_id",
            secret_key="test_secret_key",
            is_test_mode=True
        )

        result = gateway.check_payment("click_order_123_150000")

        assert result['transaction_id'] == "click_order_123_150000"
        assert result['status'] == 'paid'
        assert result['amount'] == 150000
        assert result['paid_at'] == '2024-01-01T12:00:00Z'
        mock_api_instance.check_payment.assert_called_once_with("order_123")

    def test_check_payment_invalid_transaction_id(self, click_gateway):
        """Test payment check with invalid transaction ID format."""
        with pytest.raises(ValueError, match="Invalid transaction ID format"):
            click_gateway.check_payment("invalid_format")

        with pytest.raises(ValueError, match="Invalid transaction ID format"):
            click_gateway.check_payment("payme_order_123_150000")

    @patch('paytechuz.gateways.click.client.ClickMerchantApi')
    def test_cancel_payment_success(self, mock_merchant_api, click_gateway):
        """Test successful payment cancellation."""
        # Mock the merchant API response
        mock_api_instance = Mock()
        mock_merchant_api.return_value = mock_api_instance
        mock_api_instance.cancel_payment.return_value = {
            'cancelled_at': '2024-01-01T13:00:00Z'
        }

        # Reinitialize gateway to use mocked merchant API
        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            merchant_user_id="test_merchant_user_id",
            secret_key="test_secret_key",
            is_test_mode=True
        )

        result = gateway.cancel_payment("click_order_123_150000", "Customer request")

        assert result['transaction_id'] == "click_order_123_150000"
        assert result['status'] == 'cancelled'
        assert result['cancelled_at'] == '2024-01-01T13:00:00Z'
        mock_api_instance.cancel_payment.assert_called_once_with("order_123", "Customer request")

    def test_cancel_payment_invalid_transaction_id(self, click_gateway):
        """Test payment cancellation with invalid transaction ID format."""
        with pytest.raises(ValueError, match="Invalid transaction ID format"):
            click_gateway.cancel_payment("invalid_format")

    @pytest.mark.parametrize("click_status,expected_status", [
        ('success', 'paid'),
        ('processing', 'waiting'),
        ('failed', 'failed'),
        ('cancelled', 'cancelled'),
        ('unknown_status', 'unknown')
    ])
    @patch('paytechuz.gateways.click.client.ClickMerchantApi')
    def test_status_mapping(self, mock_merchant_api, click_gateway, click_status, expected_status):
        """Test status mapping from Click to internal status."""
        mock_api_instance = Mock()
        mock_merchant_api.return_value = mock_api_instance
        mock_api_instance.check_payment.return_value = {
            'status': click_status,
            'amount': 150000
        }

        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            is_test_mode=True
        )

        result = gateway.check_payment("click_order_123_150000")
        assert result['status'] == expected_status

    def test_initialization_test_mode(self):
        """Test gateway initialization in test mode."""
        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            is_test_mode=True
        )

        assert gateway.service_id == "test_service_id"
        assert gateway.merchant_id == "test_merchant_id"
        assert gateway.merchant_user_id is None
        assert gateway.secret_key is None

    def test_initialization_production_mode(self):
        """Test gateway initialization in production mode."""
        gateway = ClickGateway(
            service_id="prod_service_id",
            merchant_id="prod_merchant_id",
            merchant_user_id="prod_user_id",
            secret_key="prod_secret",
            is_test_mode=False
        )

        assert gateway.service_id == "prod_service_id"
        assert gateway.merchant_id == "prod_merchant_id"
        assert gateway.merchant_user_id == "prod_user_id"
        assert gateway.secret_key == "prod_secret"

    @patch('paytechuz.gateways.click.client.ClickMerchantApi')
    def test_card_token_request_success(self, mock_merchant_api, click_gateway):
        """Test successful card token request."""
        mock_api_instance = Mock()
        mock_merchant_api.return_value = mock_api_instance
        mock_api_instance.card_token_request.return_value = {
            'error_code': 0,
            'error_note': '',
            'card_token': 'F64C0AD1-8744-4996-ACCC-E93129F3CB26',
            'phone_number': '********1717',
            'temporary': False,
            'eps_id': '0064'
        }

        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            secret_key="test_secret_key",
            is_test_mode=True
        )

        result = gateway.card_token_request(
            card_number="5614681005030279",
            expire_date="0330",
            temporary=0
        )

        assert result['error_code'] == 0
        assert result['card_token'] == 'F64C0AD1-8744-4996-ACCC-E93129F3CB26'
        assert result['phone_number'] == '********1717'
        mock_api_instance.card_token_request.assert_called_once_with(
            card_number="5614681005030279",
            expire_date="0330",
            temporary=0
        )

    @patch('paytechuz.gateways.click.client.ClickMerchantApi')
    def test_card_token_verify_success(self, mock_merchant_api, click_gateway):
        """Test successful card token verification."""
        mock_api_instance = Mock()
        mock_merchant_api.return_value = mock_api_instance
        mock_api_instance.card_token_verify.return_value = {
            'error_code': 0,
            'error_note': '',
            'card_number': '561468******0279',
            'eps_id': '0064'
        }

        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            secret_key="test_secret_key",
            is_test_mode=True
        )

        result = gateway.card_token_verify(
            card_token="4E0E7BA2-53BA-454B-B1FA-5725678C8CDE",
            sms_code=188375
        )

        assert result['error_code'] == 0
        assert result['card_number'] == '561468******0279'
        mock_api_instance.card_token_verify.assert_called_once_with(
            card_token="4E0E7BA2-53BA-454B-B1FA-5725678C8CDE",
            sms_code=188375
        )

    @patch('paytechuz.gateways.click.client.ClickMerchantApi')
    def test_card_token_verify_expired_sms(self, mock_merchant_api, click_gateway):
        """Test card token verification with expired SMS code."""
        mock_api_instance = Mock()
        mock_merchant_api.return_value = mock_api_instance
        mock_api_instance.card_token_verify.return_value = {
            'error_code': -301,
            'error_note': 'Время жизни смс-кода истекло'
        }

        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            secret_key="test_secret_key",
            is_test_mode=True
        )

        result = gateway.card_token_verify(
            card_token="4E0E7BA2-53BA-454B-B1FA-5725678C8CDE",
            sms_code=188375
        )

        assert result['error_code'] == -301
        assert 'истекло' in result['error_note']

    @patch('paytechuz.gateways.click.client.ClickMerchantApi')
    def test_card_token_payment_success(self, mock_merchant_api, click_gateway):
        """Test successful payment with card token."""
        mock_api_instance = Mock()
        mock_merchant_api.return_value = mock_api_instance
        mock_api_instance.card_token_payment.return_value = {
            'error_code': 0,
            'error_note': 'Успешно проведен',
            'payment_id': '4493670625',
            'payment_status': 2,
            'eps_id': '0064'
        }

        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            secret_key="test_secret_key",
            is_test_mode=True
        )

        result = gateway.card_token_payment(
            card_token="4E46C8F3-8E5A-4DC0-9F81-940C0FB23085",
            amount=1000,
            transaction_parameter="PAYMENT_1761563561"
        )

        assert result['error_code'] == 0
        assert result['payment_id'] == '4493670625'
        assert result['payment_status'] == 2
        mock_api_instance.card_token_payment.assert_called_once_with(
            card_token="4E46C8F3-8E5A-4DC0-9F81-940C0FB23085",
            amount=1000,
            transaction_parameter="PAYMENT_1761563561"
        )

    @patch('paytechuz.gateways.click.client.ClickMerchantApi')
    def test_card_token_payment_with_float_amount(self, mock_merchant_api, click_gateway):
        """Test payment with card token using float amount."""
        mock_api_instance = Mock()
        mock_merchant_api.return_value = mock_api_instance
        mock_api_instance.card_token_payment.return_value = {
            'error_code': 0,
            'error_note': 'Успешно проведен',
            'payment_id': '4493670626',
            'payment_status': 2,
            'eps_id': '0064'
        }

        gateway = ClickGateway(
            service_id="test_service_id",
            merchant_id="test_merchant_id",
            secret_key="test_secret_key",
            is_test_mode=True
        )

        result = gateway.card_token_payment(
            card_token="4E46C8F3-8E5A-4DC0-9F81-940C0FB23085",
            amount=1000.50,
            transaction_parameter="PAYMENT_1761563562"
        )

        assert result['error_code'] == 0
        assert result['payment_id'] == '4493670626'
        mock_api_instance.card_token_payment.assert_called_once_with(
            card_token="4E46C8F3-8E5A-4DC0-9F81-940C0FB23085",
            amount=1000.50,
            transaction_parameter="PAYMENT_1761563562"
        )
