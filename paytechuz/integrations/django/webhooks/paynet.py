"""
Paynet webhook handler for Django.
"""
import json
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime

from django.views import View
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.module_loading import import_string

from paytechuz.core.exceptions import (
    PermissionDenied,
    InvalidAmount,
    TransactionNotFound,
    AccountNotFound,
    MethodNotFound,
    ServiceNotFound,
    TransactionAlreadyExists,
    AlreadyPaid
)
from paytechuz.core.base import BasePaymentProcessor

from paytechuz.integrations.django.models import PaymentTransaction
from paytechuz.gateways.paynet.constants import PaynetErrors


logger = logging.getLogger(__name__)


class PaynetWebhook(BasePaymentProcessor, View):
    """
    Base Paynet webhook handler for Django.

    Implements the Paynet JSON-RPC 2.0 methods: ``PerformTransaction``,
    ``CheckTransaction``, ``CancelTransaction``, ``GetStatement``,
    ``GetInformation`` and ``ChangePassword``. Requests are authenticated with
    HTTP Basic auth.

    Configuration is read from ``settings.PAYTECHUZ['PAYNET']``::

        PAYTECHUZ = {
            'PAYNET': {
                'SERVICE_ID': 'your_paynet_service_id',
                'USERNAME': 'your_paynet_username',
                'PASSWORD': 'your_paynet_password',
                'ACCOUNT_MODEL': 'orders.models.Order',
                'ACCOUNT_FIELD': 'id',
                'AMOUNT_FIELD': 'amount',
                'ONE_TIME_PAYMENT': True,
            }
        }

    Subclass it and override the event hooks to run your own logic.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        paynet_settings = settings.PAYTECHUZ.get('PAYNET', {})

        self.paynet_username = paynet_settings.get('USERNAME', '')
        self.paynet_password = paynet_settings.get('PASSWORD', '')
        self.paynet_service_id = paynet_settings.get('SERVICE_ID', '')

        account_model_path = paynet_settings.get('ACCOUNT_MODEL')

        try:
            self.account_model = import_string(account_model_path)
        except ImportError:
            logger.error(
                "Could not import %s. Check PAYTECHUZ.PAYNET.ACCOUNT_MODEL setting.",
                account_model_path
            )
            if account_model_path:
                raise ImportError(f"Import error: {account_model_path}") from None

        self.account_field = paynet_settings.get('ACCOUNT_FIELD', 'id')
        self.amount_field = paynet_settings.get('AMOUNT_FIELD', 'amount')
        self.account_info_fields = paynet_settings.get('ACCOUNT_INFO_FIELDS', ('id',))
        self.one_time_payment = paynet_settings.get('ONE_TIME_PAYMENT', True)

    def post(self, request, **_):
        """
        Handle POST requests from Paynet.
        """
        rpc_id = None
        try:
            # Check authorization
            self._check_auth(request)

            # Parse request data
            try:
                data = json.loads(request.body.decode('utf-8'))
            except json.JSONDecodeError:
                # Paynet error code for JSON parsing error is -32700
                return self._error_response(None, PaynetErrors.JSON_PARSING_ERROR, "Error parsing JSON.")

            if not isinstance(data, dict):
                return self._error_response(None, PaynetErrors.INVALID_RPC_REQUEST, "Invalid RPC Request")

            rpc_id = data.get('id')
            method = data.get('method')
            params = data.get('params', {})

            if not all(k in data for k in ("jsonrpc", "method", "id", "params")):
                return self._error_response(rpc_id, PaynetErrors.INVALID_RPC_REQUEST, "Missing required fields")

            # Process the request based on the method
            if method == 'PerformTransaction':
                result = self._perform_transaction(params, rpc_id)
            elif method == 'CheckTransaction':
                result = self._check_transaction(params)
            elif method == 'CancelTransaction':
                result = self._cancel_transaction(params, rpc_id)
            elif method == 'GetStatement':
                result = self._get_statement(params)
            elif method == 'ChangePassword':
                result = "success"
            elif method == 'GetInformation':
                result = self._get_information(params)
            else:
                raise MethodNotFound(f"method {method} is not supported")

            # Return the result
            return JsonResponse({
                'jsonrpc': '2.0',
                'id': rpc_id,
                'result': result
            })

        except PermissionDenied:
            response = self._error_response(rpc_id, PaynetErrors.INVALID_LOGIN_OR_PASSWORD, "Invalid login or password")
            response.status_code = 401
            return response

        except MethodNotFound as e:
            return self._error_response(rpc_id, PaynetErrors.METHOD_NOT_FOUND, str(e))

        except ServiceNotFound as e:
            return self._error_response(rpc_id, PaynetErrors.SERVICE_NOT_FOUND, str(e))

        except AccountNotFound:
            return self._error_response(rpc_id, PaynetErrors.CLIENT_NOT_FOUND, "Клиент не найден")

        except InvalidAmount as e:
            return self._error_response(rpc_id, PaynetErrors.INVALID_AMOUNT, str(e))

        except TransactionNotFound as e:
            return self._error_response(rpc_id, PaynetErrors.TRANSACTION_NOT_FOUND, str(e))

        except TransactionAlreadyExists as e:
            return self._error_response(rpc_id, PaynetErrors.TRANSACTION_ALREADY_EXISTS, str(e))

        except AlreadyPaid:
            return self._error_response(rpc_id, PaynetErrors.ALREADY_PAID, "Клиент не найден")

        except Exception as e:
            logger.exception("Unexpected error in Paynet webhook: %s", e)
            return self._error_response(rpc_id, PaynetErrors.SYSTEM_ERROR, "System error")

    def _check_auth(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        try:
            self.check_basic_auth(
                auth_header,
                expected_username=self.paynet_username,
                expected_password=self.paynet_password
            )
        except PermissionDenied:
            # Re-raise to be caught by handle_webhook which maps it to error response
            raise
        except Exception as e:
            raise PermissionDenied("Invalid authentication format") from e

    def _validate_service_id(self, params):
        service_id = params.get('serviceId')
        if service_id and self.paynet_service_id and str(service_id) != str(self.paynet_service_id):
            raise ServiceNotFound(f"Service {service_id} not found")

    def _error_response(self, rpc_id, code, message):
        return JsonResponse({
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {
                "code": code,
                "message": message
            }
        }, status=200)

    def _find_account(self, params):
        """
        Find account by parameters.
        """
        # Paynet passes fields in params['fields']
        fields = params.get('fields', {})
        account_value = fields.get(self.account_field)

        if not account_value:
            # Try looking in top level just in case, but standard is fields
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
        """Validate payment amount based on ONE_TIME_PAYMENT policy."""
        try:
            received_amount = Decimal(str(amount))
        except (InvalidOperation, TypeError, ValueError):
            raise InvalidAmount("Incorrect amount") from None

        if self.one_time_payment:
            expected_value = getattr(account, self.amount_field, None)
            if expected_value is None:
                raise InvalidAmount(f"Account is missing '{self.amount_field}' field")

            try:
                expected_amount = Decimal(str(expected_value)) * Decimal("100")
            except (InvalidOperation, TypeError, ValueError):
                raise InvalidAmount(f"Invalid '{self.amount_field}' value") from None

            if expected_amount != received_amount:
                raise InvalidAmount("Incorrect amount")
            return

        if received_amount <= 0:
            raise InvalidAmount("Amount must be positive")

    def _perform_transaction(self, params, rpc_id):
        self._validate_service_id(params)
        transaction_id = params.get('transactionId')
        amount = params.get('amount')
        service_id = params.get('serviceId')

        account = self._find_account(params)

        # Check for one-time payment - if account already has a successful transaction
        if self.one_time_payment:
            existing_transaction = PaymentTransaction._default_manager.filter(
                gateway=PaymentTransaction.PAYNET,
                account_id=account.id,
                state=PaymentTransaction.SUCCESSFULLY
            ).exclude(transaction_id=transaction_id).first()

            if existing_transaction:
                raise AlreadyPaid(f"Account {account.id} already has a successful payment")

        self._validate_amount(account, amount)

        # Check if transaction exists
        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYNET,
                transaction_id=transaction_id
            )
            raise TransactionAlreadyExists("Transaction already exists")
        except PaymentTransaction.DoesNotExist:
            pass

        # Create transaction
        transaction = PaymentTransaction.create_transaction(
            gateway=PaymentTransaction.PAYNET,
            transaction_id=transaction_id,
            account_id=account.id,
            amount=Decimal(amount) / 100,
            extra_data={
                'service_id': service_id,
                'rpc_id': rpc_id,
                'time': params.get('time')
            }
        )

        if transaction.state != PaymentTransaction.SUCCESSFULLY:
            # Using / 100 for now.
            transaction.amount = Decimal(amount) / 100
            transaction.state = PaymentTransaction.SUCCESSFULLY  # Paynet perform IS the payment execution usually
            transaction.save()

            transaction.mark_as_paid()

            self.successfully_payment(params, transaction)

        return {
            "providerTrnId": transaction.id,
            "timestamp": transaction.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "fields": {self.account_field: transaction.account_id},
        }

    def _check_transaction(self, params):
        self._validate_service_id(params)
        transaction_id = params.get('transactionId')

        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYNET,
                transaction_id=transaction_id
            )
        except PaymentTransaction.DoesNotExist:
            return {
                "transactionState": 3,  # Transaction not found
                "providerTrnId": 0,
                "timestamp": self._format_timestamp(datetime.now())
            }

        # Map transaction states
        # 1 - Successful
        # 2 - Cancelled
        status = 1 if transaction.state == PaymentTransaction.SUCCESSFULLY else 2

        return {
            "transactionState": status,
            "providerTrnId": transaction.id,
            "timestamp": self._format_timestamp(transaction.updated_at),
        }

    def _cancel_transaction(self, params, rpc_id):
        self._validate_service_id(params)
        transaction_id = params.get('transactionId')

        try:
            transaction = PaymentTransaction._default_manager.get(
                gateway=PaymentTransaction.PAYNET,
                transaction_id=transaction_id
            )
        except PaymentTransaction.DoesNotExist:
            raise TransactionNotFound("Transaction not found")

        if transaction.state == PaymentTransaction.CANCELLED:
            # throw -31061 or 202 TransactionAlreadyCancelled
            # PaynetErrors.TRANSACTION_ALREADY_CANCELLED = 202
            return {
               "providerTrnId": transaction.id,
               "timestamp": transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
               "transactionState": 2  # Cancelled
                }

        transaction.mark_as_cancelled()
        self.cancelled_payment(params, transaction)

        return {
            "providerTrnId": transaction.id,
            "timestamp": transaction.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            "transactionState": 2  # Cancelled
        }

    @staticmethod
    def _parse_boundary(value):
        """
        Parse a Paynet ``dateFrom``/``dateTo`` value into a datetime.

        Paynet sends ``YYYY-MM-DD HH:MM:SS`` without an offset. The value is
        attached to the project's current timezone when USE_TZ is on, so the
        comparison stays correct and Django does not warn about naive
        datetimes. Unparseable input is passed through untouched.
        """
        if not isinstance(value, str):
            return value

        moment = parse_datetime(value)
        if moment is None:
            return value

        if settings.USE_TZ and timezone.is_naive(moment):
            return timezone.make_aware(moment, timezone.get_current_timezone())
        if not settings.USE_TZ and timezone.is_aware(moment):
            return timezone.make_naive(moment, timezone.get_current_timezone())
        return moment

    def _get_statement(self, params):
        self._validate_service_id(params)
        date_from = self._parse_boundary(params.get('dateFrom'))
        date_to = self._parse_boundary(params.get('dateTo'))

        transactions = PaymentTransaction._default_manager.filter(
            gateway=PaymentTransaction.PAYNET,
            created_at__gte=date_from,
            created_at__lte=date_to
        ).exclude(state=PaymentTransaction.CANCELLED)

        statements = [
            {
                "amount": int(tx.amount * 100),  # Return to Tiyin
                "providerTrnId": tx.id,
                "transactionId": tx.transaction_id,
                "timestamp": tx.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for tx in transactions
        ]

        return {"statements": statements}

    def _get_information(self, params):
        self._validate_service_id(params)
        account = self._find_account(params)

        # Check for one-time payment - if account already has a successful transaction
        if self.one_time_payment:
            existing_transaction = PaymentTransaction._default_manager.filter(
                gateway=PaymentTransaction.PAYNET,
                account_id=account.id,
                state=PaymentTransaction.SUCCESSFULLY
            ).first()

            if existing_transaction:
                raise AlreadyPaid(f"Account {account.id} already has a successful payment")

        # Construct fields to return
        fields = {}
        for field in self.account_info_fields:
            if hasattr(account, field):
                fields[field] = getattr(account, field)
            else:
                # Try getting from dict if account is dict (unlikely for ORM)
                pass

        response = {
            "status": "0",  # Active
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "fields": fields
        }

        # Get additional check data from user implementation
        check_data = self.get_check_data(params, account)
        if check_data:
            # If user provides fields, merge them carefully
            if 'fields' in check_data:
                response['fields'].update(check_data.pop('fields'))

            # Merge other top-level keys (e.g. balance, custom status keys if any)
            response.update(check_data)

        if 'balance' in response:
            try:
                response['balance'] = int(float(response['balance']))
            except (ValueError, TypeError):
                pass

        return response

    # ------------------------------------------------------------------
    # Overridable event hooks
    # ------------------------------------------------------------------

    def successfully_payment(self, params, transaction):
        """Called once when a payment is performed successfully."""

    def cancelled_payment(self, params, transaction):
        """Called when a payment is cancelled."""

    def get_check_data(self, params, account):
        """
        Return additional data merged into the ``GetInformation`` response.

        Example::

            {
                "fields": {"first_name": "Vali"},
                "balance": 10000
            }
        """

    def _format_timestamp(self, dt):
        """
        Format timestamp to "Fri Jan 30 10:21:18 UZT 2026"
        """
        if isinstance(dt, (int, float)):
            if dt == 0:
                dt = datetime.now()
            else:
                dt = datetime.fromtimestamp(dt)
        return dt.strftime("%a %b %d %H:%M:%S UZT %Y")
