"""
Django signals for PayTechUZ.
"""
from django.db.models.signals import post_save
from django.dispatch import Signal, receiver

from .models import PaymentTransaction

# Custom signals
payment_successful = Signal()
payment_cancelled = Signal()
payment_created = Signal()


# Signal handlers
@receiver(post_save, sender=PaymentTransaction)
def handle_transaction_state_change(sender, instance, created, **kwargs):
    """
    Handle transaction state changes.

    Args:
        sender: The model class
        instance: The actual instance being saved
        created: A boolean; True if a new record was created
        **kwargs: Additional keyword arguments
    """
    # Skip if the transaction was just created
    if created:
        payment_created.send(
            sender=sender,
            transaction=instance
        )
        return

    # Check if the transaction was marked as paid
    if instance.state == PaymentTransaction.SUCCESSFULLY:
        payment_successful.send(
            sender=sender,
            transaction=instance
        )

    # Check if the transaction was marked as cancelled
    elif instance.state in [PaymentTransaction.CANCELLED, PaymentTransaction.CANCELLED_DURING_INIT]:
        payment_cancelled.send(
            sender=sender,
            transaction=instance
        )
