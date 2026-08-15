"""
Octo webhook handler for Django.

Handles callback notifications from Octo's payment system.
Octo sends POST requests to the ``notify_url`` specified during ``prepare_payment``.
"""
import hashlib
import json
import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict

from django.conf import settings
from django.http import JsonResponse
from django.views import View
from django.utils.module_loading import import_string

from paytechuz.core.exceptions import PermissionDenied, InvalidAmount, AccountNotFound
from paytechuz.integrations.django.models import PaymentTransaction
from paytechuz.gateways.octo.client import OctoGateway
from paytechuz.gateways.octo.constants import OctoStatus

logger = logging.getLogger(__name__)


class OctoWebhook(View):
    """
    Base Octo webhook handler for Django.

    Subclass it and override ``successfully_payment`` / ``cancelled_payment``
    to run your own logic.

    Reads configuration from ``settings.PAYTECHUZ['OCTO_BANK']``::

        PAYTECHUZ = {
            'OCTO_BANK': {
                'OCTO_SHOP_ID': 42125,
                'OCTO_SECRET': '...',
                'OCTO_UNIQUE_KEY': '...',
                'NOTIFY_URL': '...',
                'ACCOUNT_MODEL': 'orders.models.Order',
                'ACCOUNT_FIELD': 'id',
                'AMOUNT_FIELD': 'amount',
                'ONE_TIME_PAYMENT': True,
                'TEST_MODE': False,
            }
        }

    Signature verification:
        ``sha1(unique_key + octo_payment_UUID + status)``
    """
    REQUIRED_FIELDS = ("octo_payment_UUID", "shop_transaction_id", "status", "total_sum")
    VALID_STATUSES = {
        OctoStatus.CREATED,
        OctoStatus.WAITING_PAY,
        OctoStatus.SUCCEEDED,
        OctoStatus.CANCELED,
        OctoStatus.FAILED,
        OctoStatus.REFUNDED,
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        octo_settings = settings.PAYTECHUZ.get('OCTO_BANK', {})

        self.octo_shop_id = octo_settings.get('OCTO_SHOP_ID', '')
        self.octo_secret = octo_settings.get('OCTO_SECRET', '')
        self.unique_key = octo_settings.get('OCTO_UNIQUE_KEY', '')
        self.notify_url = octo_settings.get('NOTIFY_URL', '')
        self.is_test_mode = octo_settings.get('TEST_MODE', False)

        if not self.octo_shop_id:
            raise ValueError("PAYTECHUZ['OCTO_BANK']['OCTO_SHOP_ID'] is required")
        if not self.octo_secret:
            raise ValueError("PAYTECHUZ['OCTO_BANK']['OCTO_SECRET'] is required")

        # Account model settings (like Payme / Click)
        account_model_path = octo_settings.get('ACCOUNT_MODEL')
        if not account_model_path:
            raise ValueError("PAYTECHUZ['OCTO_BANK']['ACCOUNT_MODEL'] is required")
        try:
            self.account_model = import_string(account_model_path)
        except ImportError:
            logger.error(
                "Could not import %s. Check PAYTECHUZ.OCTO_BANK.ACCOUNT_MODEL setting.",
                account_model_path,
            )
            if account_model_path:
                raise ImportError(f"Import error: {account_model_path}") from None

        self.account_field = octo_settings.get('ACCOUNT_FIELD', 'id')
        self.amount_field = octo_settings.get('AMOUNT_FIELD', 'amount')
        self.one_time_payment = octo_settings.get('ONE_TIME_PAYMENT', True)

        if self.is_test_mode:
            logger.warning(
                "Octo webhook is running in TEST MODE. "
                "Signature verification is DISABLED. "
                "For production: set TEST_MODE to False and provide "
                "PAYTECHUZ['OCTO_BANK']['OCTO_UNIQUE_KEY'] from the Octo team."
            )
        elif not self.unique_key:
            raise ValueError(
                "PAYTECHUZ['OCTO_BANK']['OCTO_UNIQUE_KEY'] is required in production. "
                "Get this key from the Octo team, or set TEST_MODE: True for testing."
            )

        # Initialize gateway for API calls (check_payment, cancel_payment)
        self.gateway = OctoGateway(
            octo_shop_id=self.octo_shop_id,
            octo_secret=self.octo_secret,
            notify_url=self.notify_url,
            is_test_mode=self.is_test_mode,
        )

    # ------------------------------------------------------------------
    # Overridable hooks
    # ------------------------------------------------------------------

    def successfully_payment(self, params, transaction):
        """Called when a payment succeeds. Override in subclass."""
        pass

    def cancelled_payment(self, params, transaction):
        """Called when a payment is cancelled/failed. Override in subclass."""
        pass

    # ------------------------------------------------------------------
    # HTTP dispatch
    # ------------------------------------------------------------------

    def post(self, request, *args, **kwargs):
        """Handle incoming Octo callback POST request."""
        try:
            data = self._parse_request(request)
            self._validate_provider_context(data)
            self._check_signature(data)
            self._validate_payload(data)
            return self._handle_callback(data)
        except PermissionDenied as exc:
            return self._error_response(str(exc), status=403, code="permission_denied")
        except AccountNotFound as exc:
            return self._error_response(str(exc), status=404, code="account_not_found")
        except InvalidAmount as exc:
            return self._error_response(str(exc), status=400, code="invalid_amount")
        except ValueError as exc:
            return self._error_response(str(exc), status=400, code="invalid_payload")
        except Exception as exc:
            logger.exception("Unexpected error in Octo webhook: %s", exc)
            return self._error_response("Internal error", status=500, code="internal_error")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _error_response(message: str, status: int = 400, code: str = "") -> JsonResponse:
        payload = {"error": message}
        if code:
            payload["code"] = code
        return JsonResponse(payload, status=status)

    @staticmethod
    def _ok_response(transaction: PaymentTransaction) -> JsonResponse:
        return JsonResponse({
            "status": "ok",
            "transaction_status": transaction.state,
        })

    @staticmethod
    def _parse_request(request) -> Dict[str, Any]:
        try:
            data = json.loads(request.body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error("Octo webhook: invalid JSON body - %s", exc)
            raise ValueError("Invalid JSON") from exc

        if not isinstance(data, dict):
            raise ValueError("Invalid payload: JSON object expected")

        logger.info("Octo webhook received: %s", data)
        return data

    def _validate_provider_context(self, data: Dict[str, Any]) -> None:
        callback_shop_id = data.get("octo_shop_id")
        if callback_shop_id in (None, ""):
            return

        if str(callback_shop_id) != str(self.octo_shop_id):
            raise PermissionDenied("Invalid shop id")

    def _check_signature(self, data: Dict[str, Any]) -> None:
        if self.is_test_mode:
            logger.warning("Octo: Signature verification SKIPPED (test mode)")
            return

        signature = str(data.get("signature") or "").strip()
        uuid = str(data.get("octo_payment_UUID") or "").strip()
        status = str(data.get("status") or "").strip()

        if not signature:
            raise PermissionDenied("Missing signature")

        is_valid = self._verify_signature(
            unique_key=self.unique_key,
            uuid=uuid,
            status=status,
            signature=signature,
        )
        if not is_valid:
            logger.warning("Octo webhook: invalid signature")
            raise PermissionDenied("Invalid signature")

    def _validate_payload(self, data: Dict[str, Any]) -> None:
        missing_fields = [field for field in self.REQUIRED_FIELDS if data.get(field) in (None, "")]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        data["octo_payment_UUID"] = str(data["octo_payment_UUID"]).strip()
        data["shop_transaction_id"] = str(data["shop_transaction_id"]).strip()
        data["status"] = str(data["status"]).strip().lower()

        if data["status"] not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {data['status']}")

        amount = self._parse_decimal(data["total_sum"], field_name="total_sum")
        if amount < Decimal("0"):
            raise InvalidAmount("total_sum must be non-negative")

        needs_positive_amount = {
            OctoStatus.CREATED,
            OctoStatus.WAITING_PAY,
            OctoStatus.SUCCEEDED,
        }
        if data["status"] in needs_positive_amount and amount <= Decimal("0"):
            raise InvalidAmount("total_sum must be positive")

        data["total_sum"] = amount

    @staticmethod
    def _verify_signature(
        unique_key: str,
        uuid: str,
        status: str,
        signature: str,
    ) -> bool:
        """Verify callback signature using SHA-1."""
        raw = f"{unique_key}{uuid}{status}"
        computed = hashlib.sha1(raw.encode("utf-8")).hexdigest().upper()
        return computed == signature.upper()

    def _find_account(self, account_id):
        """Find the account (order) from ACCOUNT_MODEL by ACCOUNT_FIELD."""
        try:
            lookup_value = account_id
            if self.account_field == 'id':
                if isinstance(account_id, str) and account_id.isdigit():
                    lookup_value = int(account_id)

            lookup_kwargs = {self.account_field: lookup_value}
            return self.account_model._default_manager.get(**lookup_kwargs)
        except (self.account_model.DoesNotExist, ValueError):
            raise AccountNotFound(f"Account not found for {self.account_field}={account_id}") from None

    @staticmethod
    def _parse_decimal(value: Any, field_name: str) -> Decimal:
        try:
            return Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            raise ValueError(f"Invalid decimal value for {field_name}") from None

    def _validate_amount(self, received_amount, expected_amount):
        """Validate that the received amount matches the expected amount."""
        received = self._parse_decimal(received_amount, "total_sum")
        expected = self._parse_decimal(expected_amount, self.amount_field)

        if self.one_time_payment:
            if abs(received - expected) > Decimal("0.01"):
                logger.warning(
                    "Octo amount mismatch: received=%s, expected=%s",
                    received,
                    expected,
                )
                raise InvalidAmount(f"Amount mismatch: received={received}, expected={expected}")
            return

        if received <= Decimal("0"):
            logger.warning(
                "Octo invalid amount for non one-time flow: received=%s",
                received,
            )
            raise InvalidAmount("Amount must be positive")

    def _handle_callback(self, data: dict) -> JsonResponse:
        """Process the callback data and update the transaction."""
        shop_transaction_id = data["shop_transaction_id"]
        octo_payment_uuid = data["octo_payment_UUID"]
        status = data["status"]
        total_sum = data["total_sum"]

        extra_data = {
            "shop_transaction_id": shop_transaction_id,
            "transfer_sum": data.get("transfer_sum"),
            "refunded_sum": data.get("refunded_sum"),
            "card_country": data.get("card_country"),
            "maskedPan": data.get("maskedPan"),
            "rrn": data.get("rrn"),
            "riskLevel": data.get("riskLevel"),
            "payed_time": data.get("payed_time"),
            "card_type": data.get("card_type"),
            "currency": data.get("currency"),
            "card_vendor": data.get("card_vendor"),
            "status": status,
        }

        # 1. Check duplicate: if this octo_payment_UUID already processed
        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.OCTO,
                transaction_id=octo_payment_uuid,
            )

            # Already in a final state — return immediately
            if transaction.state in (
                PaymentTransaction.SUCCESSFULLY,
                PaymentTransaction.CANCELLED,
                PaymentTransaction.CANCELLED_DURING_INIT,
            ):
                # Allow explicit refund callback to move SUCCESSFULLY -> CANCELLED.
                if status == OctoStatus.REFUNDED and transaction.state == PaymentTransaction.SUCCESSFULLY:
                    pass
                else:
                    logger.info(
                        "Octo duplicate callback for %s, state=%s — skipping",
                        octo_payment_uuid,
                        transaction.state,
                    )
                    return self._ok_response(transaction)

            if transaction.amount is not None:
                self._validate_amount(total_sum, transaction.amount)

            # Update extra_data on existing non-final transaction
            current = transaction.extra_data or {}
            current.update(extra_data)
            transaction.extra_data = current
            transaction.save(update_fields=["extra_data", "updated_at"])

        except PaymentTransaction.DoesNotExist:
            # 2. Find account (order) from ACCOUNT_MODEL
            account = self._find_account(shop_transaction_id)

            # 3. Validate amount against account model
            expected_amount = getattr(account, self.amount_field, None)
            if expected_amount is None:
                raise InvalidAmount(f"Account is missing '{self.amount_field}' field")
            self._validate_amount(total_sum, expected_amount)

            # 4. Check one_time_payment: if this account already has a paid transaction
            if self.one_time_payment:
                already_paid = PaymentTransaction._default_manager.filter(
                    gateway=PaymentTransaction.OCTO,
                    account_id=str(account.pk),
                    state=PaymentTransaction.SUCCESSFULLY,
                ).exists()

                if already_paid:
                    logger.warning(
                        "Octo: account %s already has a successful payment — rejecting",
                        account.pk,
                    )
                    return self._error_response(
                        "Payment already completed for this account",
                        status=409,
                        code="already_paid",
                    )

            # 5. Create new transaction
            #    transaction_id  = octo_payment_UUID  (Octo's unique ID)
            #    account_id      = account.id          (merchant's order ID)
            transaction = PaymentTransaction.create_transaction(
                gateway=PaymentTransaction.OCTO,
                transaction_id=octo_payment_uuid,
                account_id=str(account.pk),
                amount=total_sum,
                extra_data=extra_data,
            )

        if status == OctoStatus.SUCCEEDED:
            transaction.mark_as_paid()
            self.successfully_payment(data, transaction)

        elif status in (OctoStatus.CANCELED, OctoStatus.FAILED, OctoStatus.REFUNDED):
            transaction.mark_as_cancelled()
            self.cancelled_payment(data, transaction)

        return self._ok_response(transaction)
