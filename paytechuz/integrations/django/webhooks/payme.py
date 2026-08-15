"""
Payme webhook handler for Django.
"""
import json
import logging
from decimal import Decimal
from datetime import datetime, timezone as dt_timezone

from django.views import View
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.module_loading import import_string

from paytechuz.core.exceptions import (
    PermissionDenied,
    InvalidAmount,
    TransactionNotFound,
    AccountNotFound,
    MethodNotFound,
    UnsupportedMethod
)
from paytechuz.core.base import BasePaymentProcessor

from paytechuz.integrations.django.models import PaymentTransaction
from paytechuz.gateways.payme.constants import PaymeErrors


logger = logging.getLogger(__name__)


class PaymeWebhook(BasePaymentProcessor, View):
    """
    Base Payme webhook handler for Django.

    Implements the Payme Merchant API (JSON-RPC 2.0): ``CheckPerformTransaction``,
    ``CreateTransaction``, ``PerformTransaction``, ``CheckTransaction``,
    ``CancelTransaction`` and ``GetStatement``.

    Configuration is read from ``settings.PAYTECHUZ['PAYME']``::

        PAYTECHUZ = {
            'PAYME': {
                'PAYME_ID': 'your_payme_id',
                'PAYME_KEY': 'your_payme_key',
                'ACCOUNT_MODEL': 'orders.models.Order',
                'ACCOUNT_FIELD': 'id',
                'AMOUNT_FIELD': 'amount',
                'ONE_TIME_PAYMENT': True,
            }
        }

    Subclass it and override the event hooks to run your own logic::

        class MyPaymeWebhook(PaymeWebhook):
            def successfully_payment(self, params, transaction):
                order = Order.objects.get(id=transaction.account_id)
                order.status = 'paid'
                order.save()
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        payme_settings = settings.PAYTECHUZ.get('PAYME', {})

        self.payme_id = payme_settings.get('PAYME_ID', '')
        self.payme_key = payme_settings.get('PAYME_KEY', '')
        account_model_path = payme_settings.get('ACCOUNT_MODEL')

        try:
            self.account_model = import_string(account_model_path)
        except ImportError:
            logger.error(
                "Could not import %s. Check PAYTECHUZ.PAYME.ACCOUNT_MODEL setting.",
                account_model_path
            )
            # Raise if critical or allow to continue if not strictly needed immediately
            if account_model_path:
                raise ImportError(f"Import error: {account_model_path}") from None

        self.account_field = payme_settings.get('ACCOUNT_FIELD', 'id')
        self.amount_field = payme_settings.get('AMOUNT_FIELD', 'amount')
        self.one_time_payment = payme_settings.get('ONE_TIME_PAYMENT', True)

    def post(self, request, **_):
        """
        Handle POST requests from Payme.
        """
        try:
            # Check authorization
            self._check_auth(request)

            # Parse request data
            try:
                data = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError:
                raise MethodNotFound("Invalid JSON")

            method = data.get('method')
            params = data.get('params', {})
            request_id = data.get('id', 0)

            # Process the request based on the method
            if method == 'CheckPerformTransaction':
                result = self._check_perform_transaction(params)
            elif method == 'CreateTransaction':
                result = self._create_transaction(params)
            elif method == 'PerformTransaction':
                result = self._perform_transaction(params)
            elif method == 'CheckTransaction':
                result = self._check_transaction(params)
            elif method == 'CancelTransaction':
                result = self._cancel_transaction(params)
            elif method == 'GetStatement':
                result = self._get_statement(params)
            else:
                raise MethodNotFound(f"Method not supported: {method}")

            # Return the result
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': request_id,
                'result': result
            })

        except PermissionDenied as e:
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': request_id if 'request_id' in locals() else 0,
                'error': {
                    'code': PaymeErrors.AUTH_ERROR,
                    'message': str(e)
                }
            }, status=200)

        except (MethodNotFound, UnsupportedMethod) as e:
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': request_id if 'request_id' in locals() else 0,
                'error': {
                    'code': PaymeErrors.METHOD_NOT_FOUND,
                    'message': str(e)
                }
            }, status=200)

        except AccountNotFound as e:
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': request_id if 'request_id' in locals() else 0,
                'error': {
                    'code': PaymeErrors.INVALID_ACCOUNT,
                    'message': str(e)
                }
            }, status=200)

        except (InvalidAmount, TransactionNotFound) as e:
            # -31001 for Incorrect amount or transaction not found
            # However CheckTransaction returns -31003 if transaction not found.
            # But here global logic often maps to -31001 or specific codes
            # The original implementation used -31001 broadly.
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': request_id if 'request_id' in locals() else 0,
                'error': {
                    'code': PaymeErrors.INVALID_AMOUNT,
                    'message': str(e)
                }
            }, status=200)

        except Exception as e:
            logger.exception("Unexpected error in Payme webhook: %s", e)
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': request_id if 'request_id' in locals() else 0,
                'error': {
                    'code': PaymeErrors.SYSTEM_ERROR,
                    'message': 'Internal error'
                }
            }, status=200)

    def _check_auth(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        try:
            self.check_basic_auth(auth_header, expected_password=self.payme_key)
        except PermissionDenied as e:
            # Re-raise nicely formatted or just raise
            # Original raised PermissionDenied("Invalid merchant key") or "Authentication error"
            # Base raises PermissionDenied("Invalid credentials") etc.
            # We can just let it bubble up, but if we want to preserve exact logging:
            raise e
        except Exception as e:
            logger.error("Authentication error: %s", e)
            raise PermissionDenied("Authentication error") from e

    def _find_account(self, params):
        """
        Find account by parameters.
        """
        account_value = params.get('account', {}).get(self.account_field)
        if not account_value:
            raise AccountNotFound("Account not found in parameters")

        try:
            lookup_field = 'id' if self.account_field == 'order_id' else self.account_field

            if lookup_field == 'id' and isinstance(account_value, str) and account_value.isdigit():
                account_value = int(account_value)

            lookup_kwargs = {lookup_field: account_value}
            account = self.account_model._default_manager.get(**lookup_kwargs)
            return account
        except self.account_model.DoesNotExist:
            raise AccountNotFound(f"Account with {self.account_field}={account_value} not found") from None

    def _validate_amount(self, account, amount):
        """
        Validate payment amount.
        """
        expected_amount = Decimal(getattr(account, self.amount_field)) * 100
        received_amount = Decimal(amount)

        if self.one_time_payment and expected_amount != received_amount:
            raise InvalidAmount(f"Invalid amount. Expected: {expected_amount}, received: {received_amount}")

        if not self.one_time_payment and received_amount <= 0:
            raise InvalidAmount(f"Invalid amount. Amount must be positive, received: {received_amount}")

        return True

    def _check_perform_transaction(self, params):
        account = self._find_account(params)
        self._validate_amount(account, params.get('amount'))
        self.before_check_perform_transaction(params, account)

        result = {'allow': True}

        # Get additional check data from user implementation
        check_data = self.get_check_data(params, account)
        if check_data:
            result.update(check_data)

        return result

    def _create_transaction(self, params):
        transaction_id = params.get('id')
        account = self._find_account(params)
        amount = params.get('amount')

        self._validate_amount(account, amount)

        if self.one_time_payment:
            existing_transactions = PaymentTransaction._default_manager.filter(
                gateway=PaymentTransaction.PAYME,
                account_id=account.id
            ).exclude(transaction_id=transaction_id)

            non_final_transactions = existing_transactions.exclude(
                state__in=[PaymentTransaction.SUCCESSFULLY, PaymentTransaction.CANCELLED]
            )

            if non_final_transactions.exists():
                raise AccountNotFound(
                    f"Account with {self.account_field}={account.id} "
                    f"already has a pending transaction"
                )

        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYME,
                transaction_id=transaction_id
            )
            self.transaction_already_exists(params, transaction)
            return {
                'transaction': transaction.transaction_id,
                'state': transaction.state,
                'create_time': int(transaction.created_at.timestamp() * 1000),
            }
        except PaymentTransaction.DoesNotExist:
            pass

        transaction = PaymentTransaction.create_transaction(
            gateway=PaymentTransaction.PAYME,
            transaction_id=transaction_id,
            account_id=account.id,
            amount=Decimal(amount) / 100,
            extra_data={
                'account_field': self.account_field,
                'account_value': params.get('account', {}).get(self.account_field),
                'create_time': params.get('time'),
                'raw_params': params
            }
        )

        transaction.state = PaymentTransaction.INITIATING
        transaction.save()
        self.transaction_created(params, transaction, account)

        return {
            'transaction': transaction.transaction_id,
            'state': transaction.state,
            'create_time': int(transaction.created_at.timestamp() * 1000),
        }

    def _perform_transaction(self, params):
        transaction_id = params.get('id')
        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYME,
                transaction_id=transaction_id
            )
        except PaymentTransaction.DoesNotExist:
            raise TransactionNotFound(f"Transaction {transaction_id} not found") from None

        if transaction.state != PaymentTransaction.SUCCESSFULLY:
            transaction.mark_as_paid()
            self.successfully_payment(params, transaction)

        return {
            'transaction': transaction.transaction_id,
            'state': transaction.state,
            'perform_time': int(transaction.performed_at.timestamp() * 1000) if transaction.performed_at else 0,
        }

    def _check_transaction(self, params):
        transaction_id = params.get('id')
        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYME,
                transaction_id=transaction_id
            )
        except PaymentTransaction.DoesNotExist:
            raise TransactionNotFound(f"Transaction {transaction_id} not found") from None

        self.check_transaction(params, transaction)

        return {
            'transaction': transaction.transaction_id,
            'state': transaction.state,
            'create_time': int(transaction.created_at.timestamp() * 1000),
            'perform_time': int(transaction.performed_at.timestamp() * 1000) if transaction.performed_at else 0,
            'cancel_time': int(transaction.cancelled_at.timestamp() * 1000) if transaction.cancelled_at else 0,
            'reason': transaction.reason,
        }

    def _cancel_response(self, transaction):
        return {
            'transaction': transaction.transaction_id,
            'state': transaction.state,
            'cancel_time': int(transaction.cancelled_at.timestamp() * 1000) if transaction.cancelled_at else 0,
        }

    def _cancel_transaction(self, params):
        transaction_id = params.get('id')
        reason = params.get('reason')

        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYME,
                transaction_id=transaction_id
            )
        except PaymentTransaction.DoesNotExist:
            raise TransactionNotFound(f"Transaction {transaction_id} not found") from None

        if transaction.state == PaymentTransaction.CANCELLED:
            return self._cancel_response(transaction)

        if transaction.state == PaymentTransaction.INITIATING:
            transaction.mark_as_cancelled_during_init(reason=reason)
        else:
            transaction.mark_as_cancelled(reason=reason)

        self.cancelled_payment(params, transaction)
        return self._cancel_response(transaction)

    @staticmethod
    def _milliseconds_to_datetime(milliseconds):
        """
        Convert a Payme epoch-milliseconds value to a datetime.

        Payme timestamps are UTC-based, so they are read as UTC rather than as
        local time. The result matches the project's USE_TZ setting, which
        keeps Django from warning about naive datetimes in queries.
        """
        moment = datetime.fromtimestamp(milliseconds / 1000, tz=dt_timezone.utc)
        if settings.USE_TZ:
            return moment
        return timezone.make_naive(moment, dt_timezone.utc)

    def _get_statement(self, params):
        from_date = params.get('from')
        to_date = params.get('to')

        from_datetime = self._milliseconds_to_datetime(from_date or 0)
        if to_date:
            to_datetime = self._milliseconds_to_datetime(to_date)
        else:
            to_datetime = timezone.now() if settings.USE_TZ else datetime.now()

        transactions = PaymentTransaction._default_manager.filter(
            gateway=PaymentTransaction.PAYME,
            created_at__gte=from_datetime,
            created_at__lte=to_datetime
        )

        result = []
        for transaction in transactions:
            result.append({
                'id': transaction.transaction_id,
                'time': int(transaction.created_at.timestamp() * 1000),
                'amount': int(transaction.amount * 100),
                'account': {self.account_field: transaction.account_id},
                'state': transaction.state,
                'create_time': int(transaction.created_at.timestamp() * 1000),
                'perform_time': int(transaction.performed_at.timestamp() * 1000) if transaction.performed_at else 0,
                'cancel_time': int(transaction.cancelled_at.timestamp() * 1000) if transaction.cancelled_at else 0,
                'reason': transaction.reason,
            })

        self.get_statement(params, result)
        return {'transactions': result}

    # ------------------------------------------------------------------
    # Overridable event hooks
    # ------------------------------------------------------------------

    def before_check_perform_transaction(self, params, account):
        """Called before checking whether a transaction can be performed."""

    def transaction_already_exists(self, params, transaction):
        """Called when ``CreateTransaction`` hits an existing transaction."""

    def transaction_created(self, params, transaction, account):
        """Called right after a new transaction is created."""

    def successfully_payment(self, params, transaction):
        """Called once when a payment is performed successfully."""

    def check_transaction(self, params, transaction):
        """Called on every ``CheckTransaction`` request."""

    def cancelled_payment(self, params, transaction):
        """Called when a payment is cancelled."""

    def get_statement(self, params, transactions):
        """Called with the transaction list built for ``GetStatement``."""

    def get_check_data(self, params, account):
        """
        Return additional data merged into the ``CheckPerformTransaction`` result.

        Example::

            {
                "additional": {"first_name": "Anvarbek", "balance": 1000000},
                "detail": {
                    "receipt_type": 0,
                    "shipping": {"title": "Yetkazib berish", "price": 10000},
                    "items": [
                        {
                            "discount": 0,
                            "title": "Mahsulot nomi",
                            "price": 500000,
                            "count": 1,
                            "code": "00001",
                            "units": 1,
                            "vat_percent": 0,
                            "package_code": "123456"
                        }
                    ]
                }
            }
        """
