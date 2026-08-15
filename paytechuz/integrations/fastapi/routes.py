"""
FastAPI webhook handlers for PayTechUZ.

Subclass ``PaymeWebhookHandler`` / ``ClickWebhookHandler`` and override the
event hooks to run your own business logic, then call ``handle_webhook``
from your route.
"""

import hashlib
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, Optional

from fastapi import (
    APIRouter,
    HTTPException,
    Request,
    Response,
    status
)
from sqlalchemy.orm import Session

from paytechuz.core.exceptions import (
    PermissionDenied,
    InvalidAmount,
    TransactionNotFound,
    AccountNotFound,
    MethodNotFound,
    UnsupportedMethod,
    InvalidAccount,
)
from paytechuz.core.base import BasePaymentProcessor

from .models import PaymentTransaction

router = APIRouter()
logger = logging.getLogger(__name__)


class PaymeWebhookHandler(BasePaymentProcessor):
    """
    Base Payme webhook handler for FastAPI.

    Implements the Payme Merchant API (JSON-RPC 2.0). Extend this class and
    override the event methods to customize the behavior.

    Example:
    ```python
    from paytechuz.integrations.fastapi import PaymeWebhookHandler

    class CustomPaymeWebhookHandler(PaymeWebhookHandler):
        def successfully_payment(self, params, transaction):
            order = self.db.query(Order).filter(
                Order.id == transaction.account_id
            ).first()
            order.status = 'paid'
            self.db.commit()
    ```
    """

    def __init__(
        self,
        db: Session,
        payme_id: str,
        payme_key: str,
        account_model: Any,
        account_field: str = 'id',
        amount_field: str = 'amount',
        one_time_payment: bool = True
    ):
        """
        Initialize the Payme webhook handler.

        Args:
            db: Database session
            payme_id: Payme merchant ID
            payme_key: Payme merchant key
            account_model: Account model class
            account_field: Account field name
            amount_field: Amount field name
            one_time_payment: Whether to validate amount
        """
        self.db = db
        self.payme_id = payme_id
        self.payme_key = payme_key
        self.account_model = account_model
        self.account_field = account_field
        self.amount_field = amount_field
        self.one_time_payment = one_time_payment

    async def handle_webhook(self, request: Request) -> Response:
        """
        Handle webhook request from Payme.

        Args:
            request: FastAPI request object

        Returns:
            Response object with JSON data
        """
        request_id = 0
        try:
            # Check authorization
            auth_header = request.headers.get('Authorization')
            self._check_auth(auth_header)

            # Parse request data
            data = await request.json()
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
                return self._error_response(
                    request_id, -32601, f"Method not supported: {method}"
                )

            # Return the result
            return Response(
                content=json.dumps({
                    'jsonrpc': '2.0',
                    'id': request_id,
                    'result': result
                }),
                media_type="application/json",
                status_code=200
            )

        except PermissionDenied:
            return self._error_response(
                request_id, -32504, "permission denied"
            )

        except (MethodNotFound, UnsupportedMethod) as e:
            return self._error_response(
                request_id, -32601, str(e)
            )

        except (AccountNotFound, InvalidAccount) as e:
            return self._error_response(
                request_id, -31050, str(e)
            )

        except (InvalidAmount, TransactionNotFound) as e:
            return self._error_response(
                request_id, -31001, str(e)
            )

        except Exception as e:
            logger.exception("Unexpected error in Payme webhook: %s", e)
            return self._error_response(
                request_id, -32400, 'Internal error'
            )

    @staticmethod
    def _error_response(request_id: Any, code: int, message: str) -> Response:
        """Build a JSON-RPC error response."""
        return Response(
            content=json.dumps({
                'jsonrpc': '2.0',
                'id': request_id if request_id is not None else 0,
                'error': {
                    'code': code,
                    'message': message
                }
            }),
            media_type="application/json",
            status_code=200
        )

    def _check_auth(self, auth_header: Optional[str]) -> None:
        """Check authorization header."""
        try:
            self.check_basic_auth(auth_header, expected_password=self.payme_key)
        except PermissionDenied:
            raise
        except Exception as e:
            logger.error("Authentication error: %s", e)
            raise PermissionDenied("Authentication error")

    def _find_account(self, params: Dict[str, Any]) -> Any:
        """Find account by parameters."""
        account_value = params.get('account', {}).get(self.account_field)
        if not account_value:
            raise AccountNotFound("Account not found in parameters")

        lookup_field = 'id' if self.account_field == 'order_id' else (
            self.account_field
        )

        if (lookup_field == 'id' and
                isinstance(account_value, str) and
                account_value.isdigit()):
            account_value = int(account_value)

        account = self.db.query(self.account_model).filter_by(
            **{lookup_field: account_value}
        ).first()
        if not account:
            raise AccountNotFound(
                f"Account with {self.account_field}={account_value} not found"
            )

        return account

    def _validate_amount(self, account: Any, amount: int) -> bool:
        """Validate payment amount."""
        expected_amount = Decimal(getattr(account, self.amount_field)) * 100
        received_amount = Decimal(amount)

        if self.one_time_payment and expected_amount != received_amount:
            raise InvalidAmount(
                (f"Invalid amount. Expected: {expected_amount}, "
                 f"received: {received_amount}")
            )

        if not self.one_time_payment and received_amount <= 0:
            raise InvalidAmount(
                (f"Invalid amount. Amount must be positive, "
                 f"received: {received_amount}")
            )

        return True

    def _check_perform_transaction(
        self, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle CheckPerformTransaction method."""
        account = self._find_account(params)
        self._validate_amount(account, params.get('amount'))

        self.before_check_perform_transaction(params, account)

        result = {'allow': True}

        check_data = self.get_check_data(params, account)
        if check_data:
            result.update(check_data)

        return result

    def _create_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CreateTransaction method."""
        transaction_id = params.get('id')
        account = self._find_account(params)
        amount = params.get('amount')

        self._validate_amount(account, amount)

        if self.one_time_payment:
            existing_transactions = self.db.query(PaymentTransaction).filter(
                PaymentTransaction.gateway == PaymentTransaction.PAYME,
                PaymentTransaction.account_id == str(account.id)
            ).filter(
                PaymentTransaction.transaction_id != transaction_id
            ).all()

            non_final_transactions = [
                t for t in existing_transactions
                if t.state not in [
                    PaymentTransaction.SUCCESSFULLY,
                    PaymentTransaction.CANCELLED,
                    PaymentTransaction.CANCELLED_DURING_INIT
                ]
            ]

            if non_final_transactions:
                raise InvalidAccount(
                    (f"Account with {self.account_field}={account.id} "
                     f"already has a pending transaction")
                )

        transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.gateway == PaymentTransaction.PAYME,
            PaymentTransaction.transaction_id == transaction_id
        ).first()

        if transaction:
            self.transaction_already_exists(params, transaction)

            create_time = transaction.extra_data.get(
                'create_time', params.get('time')
            )

            return {
                'transaction': transaction.transaction_id,
                'state': transaction.state,
                'create_time': create_time,
            }

        transaction = PaymentTransaction(
            gateway=PaymentTransaction.PAYME,
            transaction_id=transaction_id,
            account_id=account.id,
            amount=Decimal(amount) / 100,
            state=PaymentTransaction.INITIATING,
            extra_data={
                'account_field': self.account_field,
                'account_value': (
                    params.get('account', {}).get(self.account_field)
                ),
                'create_time': params.get('time'),
                'raw_params': params
            }
        )

        self.db.add(transaction)
        self.db.commit()
        self.db.refresh(transaction)

        self.transaction_created(params, transaction, account)

        return {
            'transaction': transaction.transaction_id,
            'state': transaction.state,
            'create_time': params.get('time'),
        }

    def _perform_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle PerformTransaction method."""
        transaction_id = params.get('id')

        transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.gateway == PaymentTransaction.PAYME,
            PaymentTransaction.transaction_id == transaction_id
        ).first()

        if not transaction:
            raise TransactionNotFound(
                f"Transaction {transaction_id} not found"
            )

        transaction.mark_as_paid(self.db)

        self.successfully_payment(params, transaction)

        return {
            'transaction': transaction.transaction_id,
            'state': transaction.state,
            'perform_time': int(
                transaction.performed_at.timestamp() * 1000
            ) if transaction.performed_at else 0,
        }

    def _check_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CheckTransaction method."""
        transaction_id = params.get('id')

        transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.gateway == PaymentTransaction.PAYME,
            PaymentTransaction.transaction_id == transaction_id
        ).first()

        if not transaction:
            raise TransactionNotFound(
                f"Transaction {transaction_id} not found"
            )

        self.check_transaction(params, transaction)

        create_time = transaction.extra_data.get(
            'create_time', int(transaction.created_at.timestamp() * 1000)
        )

        return {
            'transaction': transaction.transaction_id,
            'state': transaction.state,
            'create_time': create_time,
            'perform_time': (
                int(transaction.performed_at.timestamp() * 1000)
                if transaction.performed_at else 0
            ),
            'cancel_time': (
                int(transaction.cancelled_at.timestamp() * 1000)
                if transaction.cancelled_at else 0
            ),
            'reason': transaction.reason,
        }

    def _cancel_response(
        self, transaction: PaymentTransaction
    ) -> Dict[str, Any]:
        """Helper method to generate cancel transaction response."""
        reason = transaction.reason

        if reason is None:
            from paytechuz.gateways.payme.constants import PaymeCancelReason
            reason = PaymeCancelReason.REASON_FUND_RETURNED
            transaction.reason = reason
            self.db.commit()
            self.db.refresh(transaction)

        return {
            'transaction': transaction.transaction_id,
            'state': transaction.state,
            'cancel_time': (int(transaction.cancelled_at.timestamp() * 1000)
                            if transaction.cancelled_at else 0),
            'reason': reason,
        }

    def _cancel_transaction(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle CancelTransaction method."""
        transaction_id = params.get('id')
        reason = params.get('reason')

        transaction = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.gateway == PaymentTransaction.PAYME,
            PaymentTransaction.transaction_id == transaction_id
        ).first()

        if not transaction:
            raise TransactionNotFound(
                f"Transaction {transaction_id} not found"
            )

        cancelled_states = [
            PaymentTransaction.CANCELLED,
            PaymentTransaction.CANCELLED_DURING_INIT
        ]
        if transaction.state in cancelled_states:
            if 'reason' in params:
                reason = params.get('reason')

                if reason is None:
                    from paytechuz.gateways.payme.constants import PaymeCancelReason
                    reason = PaymeCancelReason.REASON_FUND_RETURNED

                if isinstance(reason, str) and reason.isdigit():
                    reason = int(reason)

                transaction.reason = reason

                extra_data = transaction.extra_data or {}
                extra_data['cancel_reason'] = reason
                transaction.extra_data = extra_data

                self.db.commit()
                self.db.refresh(transaction)

            return self._cancel_response(transaction)

        reason = params.get('reason')
        transaction.mark_as_cancelled(self.db, reason=reason)

        extra_data = transaction.extra_data or {}
        if 'cancel_reason' not in extra_data:
            extra_data['cancel_reason'] = reason if reason is not None else 5
            transaction.extra_data = extra_data
            self.db.commit()
            self.db.refresh(transaction)

        self.cancelled_payment(params, transaction)

        return self._cancel_response(transaction)

    def _get_statement(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle GetStatement method."""
        from_date = params.get('from')
        to_date = params.get('to')

        if from_date:
            from_datetime = datetime.fromtimestamp(from_date / 1000)
        else:
            from_datetime = datetime.fromtimestamp(0)

        if to_date:
            to_datetime = datetime.fromtimestamp(to_date / 1000)
        else:
            to_datetime = datetime.now()

        transactions = self.db.query(PaymentTransaction).filter(
            PaymentTransaction.gateway == PaymentTransaction.PAYME,
            PaymentTransaction.created_at >= from_datetime,
            PaymentTransaction.created_at <= to_datetime
        ).all()

        result = []
        for transaction in transactions:
            result.append({
                'id': transaction.transaction_id,
                'time': int(transaction.created_at.timestamp() * 1000),
                'amount': int(transaction.amount * 100),
                'account': {
                    self.account_field: transaction.account_id
                },
                'state': transaction.state,
                'create_time': transaction.extra_data.get(
                    'create_time',
                    int(transaction.created_at.timestamp() * 1000)
                ),
                'perform_time': (
                    int(transaction.performed_at.timestamp() * 1000)
                    if transaction.performed_at else 0
                ),
                'cancel_time': (
                    int(transaction.cancelled_at.timestamp() * 1000)
                    if transaction.cancelled_at else 0
                ),
                'reason': transaction.reason,
            })

        self.get_statement(params, result)

        return {'transactions': result}

    # ------------------------------------------------------------------
    # Overridable event hooks
    # ------------------------------------------------------------------

    def before_check_perform_transaction(
        self, params: Dict[str, Any], account: Any
    ) -> None:
        """Called before checking if a transaction can be performed."""

    def transaction_already_exists(
        self, params: Dict[str, Any], transaction: PaymentTransaction
    ) -> None:
        """Called when a transaction already exists."""

    def transaction_created(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction,
        account: Any
    ) -> None:
        """Called when a transaction is created."""

    def successfully_payment(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """Called when a payment is successful."""

    def check_transaction(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """Called when checking a transaction."""

    def cancelled_payment(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """Called when a payment is cancelled."""

    def get_statement(
        self,
        params: Dict[str, Any],
        transactions: list
    ) -> None:
        """Called when getting a statement."""

    def get_check_data(
        self, params: Dict[str, Any], account: Any
    ) -> Optional[Dict[str, Any]]:
        """
        Return additional data merged into the ``CheckPerformTransaction`` result.

        Example::

            {"additional": {"first_name": "Anvarbek", "balance": 1000000}}
        """


class ClickWebhookHandler:
    """
    Base Click webhook handler for FastAPI.

    Handles the Click Merchant API prepare/complete flow. Extend this class and
    override the event methods to customize the behavior.

    Example:
    ```python
    from paytechuz.integrations.fastapi import ClickWebhookHandler

    class CustomClickWebhookHandler(ClickWebhookHandler):
        def successfully_payment(self, params, transaction):
            order = (db.query(Order)
                     .filter(Order.id == transaction.account_id)
                     .first())
            order.status = 'paid'
            db.commit()
    ```
    """

    def __init__(
        self,
        db: Session,
        service_id: str,
        secret_key: str,
        account_model: Any,
        commission_percent: float = 0.0,
        account_field: str = 'id',
        amount_field: str = 'amount',
        one_time_payment: bool = True
    ):
        """
        Initialize the Click webhook handler.

        Args:
            db: Database session
            service_id: Click service ID
            secret_key: Click secret key
            account_model: Account model class
            commission_percent: Commission percentage
            account_field: Field name to look up account by (default: 'id')
            amount_field: Field name holding the expected amount (default: 'amount')
            one_time_payment: Whether to validate amount (default: True)
        """
        self.db = db
        self.service_id = service_id
        self.secret_key = secret_key
        self.account_model = account_model
        self.commission_percent = commission_percent
        self.account_field = account_field
        self.amount_field = amount_field
        self.one_time_payment = one_time_payment

    async def handle_webhook(self, request: Request) -> Dict[str, Any]:
        """Handle webhook request from Click."""
        try:
            form_data = await request.form()
            params = {key: form_data.get(key) for key in form_data}

            self._check_auth(params)

            click_trans_id = params.get('click_trans_id')
            merchant_trans_id = params.get('merchant_trans_id')
            amount = float(params.get('amount', 0))
            action = int(params.get('action', -1))
            error = int(params.get('error', 0))

            try:
                account = self._find_account(merchant_trans_id)
            except Exception:
                logger.error("Account not found: %s", merchant_trans_id)
                return {
                    'click_trans_id': click_trans_id,
                    'merchant_trans_id': merchant_trans_id,
                    'error': -5,
                    'error_note': "User not found"
                }

            try:
                expected = float(getattr(account, self.amount_field, 0))
                self._validate_amount(amount, expected)
            except Exception as e:
                logger.error("Invalid amount: %s", e)
                return {
                    'click_trans_id': click_trans_id,
                    'merchant_trans_id': merchant_trans_id,
                    'error': -2,
                    'error_note': str(e)
                }

            transaction = self.db.query(PaymentTransaction).filter(
                PaymentTransaction.gateway == PaymentTransaction.CLICK,
                PaymentTransaction.transaction_id == click_trans_id
            ).first()

            if transaction:
                if transaction.state == PaymentTransaction.SUCCESSFULLY:
                    self.transaction_already_exists(params, transaction)

                    return {
                        'click_trans_id': click_trans_id,
                        'merchant_trans_id': merchant_trans_id,
                        'merchant_prepare_id': transaction.id,
                        'error': 0,
                        'error_note': "Success"
                    }

                if transaction.state == PaymentTransaction.CANCELLED:
                    return {
                        'click_trans_id': click_trans_id,
                        'merchant_trans_id': merchant_trans_id,
                        'merchant_prepare_id': transaction.id,
                        'error': -9,
                        'error_note': "Transaction cancelled"
                    }

            if action == 0:  # Prepare
                transaction = PaymentTransaction(
                    gateway=PaymentTransaction.CLICK,
                    transaction_id=click_trans_id,
                    account_id=str(account.id),
                    amount=amount,
                    state=PaymentTransaction.INITIATING,
                    extra_data={
                        'raw_params': params,
                        'merchant_trans_id': merchant_trans_id
                    }
                )

                self.db.add(transaction)
                self.db.commit()
                self.db.refresh(transaction)

                self.transaction_created(params, transaction, account)

                return {
                    'click_trans_id': click_trans_id,
                    'merchant_trans_id': merchant_trans_id,
                    'merchant_prepare_id': transaction.id,
                    'error': 0,
                    'error_note': "Success"
                }

            if action == 1:  # Complete
                is_successful = error >= 0

                if not transaction:
                    transaction = PaymentTransaction(
                        gateway=PaymentTransaction.CLICK,
                        transaction_id=click_trans_id,
                        account_id=str(account.id),
                        amount=amount,
                        state=PaymentTransaction.INITIATING,
                        extra_data={
                            'raw_params': params,
                            'merchant_trans_id': merchant_trans_id
                        }
                    )

                    self.db.add(transaction)
                    self.db.commit()
                    self.db.refresh(transaction)

                if is_successful:
                    transaction.mark_as_paid(self.db)
                    self.successfully_payment(params, transaction)
                else:
                    transaction.mark_as_cancelled(
                        self.db, reason=f"Error code: {error}"
                    )
                    self.cancelled_payment(params, transaction)

                return {
                    'click_trans_id': click_trans_id,
                    'merchant_trans_id': merchant_trans_id,
                    'merchant_prepare_id': transaction.id,
                    'error': 0,
                    'error_note': "Success"
                }

            logger.error("Unsupported action: %s", action)
            return {
                'click_trans_id': click_trans_id,
                'merchant_trans_id': merchant_trans_id,
                'error': -3,
                'error_note': "Action not found"
            }

        except Exception as e:
            logger.exception("Unexpected error in Click webhook: %s", e)
            return {
                'error': -7,
                'error_note': "Internal error"
            }

    def _check_auth(self, params: Dict[str, Any]) -> None:
        """Check authentication using signature."""
        if not all([self.service_id, self.secret_key]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing required settings: service_id or secret_key"
            )

        if str(params.get("service_id")) != self.service_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service ID"
            )

        sign_string = params.get("sign_string")
        sign_time = params.get("sign_time")

        if not sign_string or not sign_time:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing signature parameters"
            )

        text_parts = [
            str(params.get("click_trans_id") or ""),
            str(params.get("service_id") or ""),
            str(self.secret_key or ""),
            str(params.get("merchant_trans_id") or ""),
            str(params.get("merchant_prepare_id") or ""),
            str(params.get("amount") or ""),
            str(params.get("action") or ""),
            str(sign_time)
        ]

        calculated_hash = hashlib.md5(
            "".join(text_parts).encode("utf-8")
        ).hexdigest()

        if calculated_hash != sign_string:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid signature"
            )

    def _find_account(self, merchant_trans_id: str) -> Any:
        """Find account by merchant_trans_id."""
        account_value = merchant_trans_id

        if self.account_field == 'id':
            if isinstance(account_value, str) and account_value.isdigit():
                account_value = int(account_value)

        lookup_kwargs = {self.account_field: account_value}

        account = (
            self.db.query(self.account_model)
            .filter_by(**lookup_kwargs)
            .first()
        )
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Account with {self.account_field}={merchant_trans_id} "
                    f"not found"
                )
            )

        return account

    def _validate_amount(
        self, received_amount: float, expected_amount: float
    ) -> None:
        """Validate payment amount."""
        if self.one_time_payment:
            if self.commission_percent > 0:
                commission_factor = 1 + (self.commission_percent / 100)
                expected_amount = expected_amount * commission_factor
                expected_amount = round(expected_amount, 2)

            if abs(received_amount - expected_amount) > 0.01:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Incorrect amount. Expected: {expected_amount}, "
                        f"received: {received_amount}"
                    )
                )
        else:
            if received_amount <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Amount must be positive"
                )

    # ------------------------------------------------------------------
    # Overridable event hooks
    # ------------------------------------------------------------------

    def transaction_already_exists(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """Called when a transaction already exists."""

    def transaction_created(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction,
        account: Any
    ) -> None:
        """Called when a transaction is created."""

    def successfully_payment(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """Called when a payment is successful."""

    def cancelled_payment(
        self,
        params: Dict[str, Any],
        transaction: PaymentTransaction
    ) -> None:
        """Called when a payment is cancelled."""
