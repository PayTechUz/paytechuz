"""
Django models for PayTechUZ.
"""
from django.db import models
from django.utils import timezone


class PaymentTransaction(models.Model):
    """
    Payment transaction model for storing payment information.
    """
    # Payment gateway choices
    PAYME = 'payme'
    CLICK = 'click'
    UZUM = 'uzum'
    PAYNET = 'paynet'
    OCTO = 'octo'

    GATEWAY_CHOICES = [
        (PAYME, 'Payme'),
        (CLICK, 'Click'),
        (UZUM, 'Uzum'),
        (PAYNET, 'Paynet'),
        (OCTO, 'Octo'),
    ]

    # Transaction states
    CREATED = 0
    INITIATING = 1
    SUCCESSFULLY = 2
    CANCELLED = -2
    CANCELLED_DURING_INIT = -1

    STATE_CHOICES = [
        (CREATED, "Created"),
        (INITIATING, "Initiating"),
        (SUCCESSFULLY, "Successfully"),
        (CANCELLED, "Cancelled after successful performed"),
        (CANCELLED_DURING_INIT, "Cancelled during initiation"),
    ]

    gateway = models.CharField(max_length=10, choices=GATEWAY_CHOICES)
    transaction_id = models.CharField(max_length=255)
    account_id = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    state = models.IntegerField(choices=STATE_CHOICES, default=CREATED)
    reason = models.IntegerField(null=True, blank=True)  # Reason for cancellation
    extra_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    performed_at = models.DateTimeField(null=True, blank=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        """
        Model Meta options.
        """
        verbose_name = "Payment Transaction"
        verbose_name_plural = "Payment Transactions"
        ordering = ["-created_at"]
        db_table = "payments"
        unique_together = [['gateway', 'transaction_id']]

    def __str__(self):
        """
        String representation of the PaymentTransaction model.
        """
        return f"{self.get_gateway_display()} Transaction #{self.transaction_id} - {self.amount}"

    def mark_as_paid(self):
        """
        Mark the transaction as paid.
        """
        if self.state != self.SUCCESSFULLY:
            self.state = self.SUCCESSFULLY
            self.performed_at = timezone.now()
            self.save()
        return self

    def mark_as_cancelled_during_init(self, reason):
        self.state = self.CANCELLED_DURING_INIT
        self.cancelled_at = timezone.now()
        self.reason = reason
        self.save()

    def mark_as_cancelled(self, reason=None):
        """
        Mark the transaction as cancelled.

        Args:
            reason: Reason for cancellation (integer code)

        Returns:
            PaymentTransaction instance
        """
        if self.state not in [self.CANCELLED, self.CANCELLED_DURING_INIT]:
            # Always set state to CANCELLED (-2) for Payme API compatibility
            # regardless of the current state
            self.state = self.CANCELLED
            self.cancelled_at = timezone.now()

            # Store reason directly in the reason column if provided
            if reason is not None:
                # Convert reason to int if it's a string
                if isinstance(reason, str) and reason.isdigit():
                    reason_code = int(reason)
                else:
                    reason_code = reason
                self.reason = reason_code

                # For backward compatibility, also store in extra_data
                extra_data = self.extra_data or {}
                extra_data['cancel_reason'] = reason_code
                self.extra_data = extra_data

            self.save()
        return self

    @classmethod
    def create_transaction(cls, gateway, transaction_id, account_id, amount, extra_data=None):
        """
        Create a new transaction or get an existing one.

        Args:
            gateway: Payment gateway (payme or click)
            transaction_id: Transaction ID from the payment system
            account_id: Account or order ID
            amount: Payment amount
            extra_data: Additional data for the transaction

        Returns:
            PaymentTransaction instance
        """
        transaction, created = cls.objects.get_or_create(
            gateway=gateway,
            transaction_id=transaction_id,
            defaults={
                'account_id': str(account_id),
                'amount': amount,
                'state': cls.CREATED,
                'extra_data': extra_data or {}
            }
        )

        return transaction

    @classmethod
    def update_transaction(cls, gateway, transaction_id, state=None, extra_data=None):
        """
        Update an existing transaction.

        Args:
            gateway: Payment gateway (payme or click)
            transaction_id: Transaction ID from the payment system
            state: New state for the transaction
            extra_data: Additional data to update

        Returns:
            PaymentTransaction instance or None if not found
        """
        try:
            transaction = cls.objects.get(gateway=gateway, transaction_id=transaction_id)

            if state is not None:
                transaction.state = state

                # Update timestamps based on state
                if state == cls.SUCCESSFULLY:
                    transaction.performed_at = timezone.now()
                elif state in [cls.CANCELLED, cls.CANCELLED_DURING_INIT]:
                    transaction.cancelled_at = timezone.now()

            # Update extra_data if provided
            if extra_data:
                current_extra_data = transaction.extra_data or {}
                current_extra_data.update(extra_data)
                transaction.extra_data = current_extra_data

            transaction.save()
            return transaction
        except cls.DoesNotExist:
            return None
