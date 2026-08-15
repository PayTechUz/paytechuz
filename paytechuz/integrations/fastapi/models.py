"""
FastAPI models for PayTechUZ.
"""
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PaymentTransaction(Base):
    """
    Payment transaction model for storing payment information.
    """
    __tablename__ = "payments"

    # Payment gateway choices
    PAYME = 'payme'
    CLICK = 'click'

    # Transaction states
    CREATED = 0
    INITIATING = 1
    SUCCESSFULLY = 2
    CANCELLED = -2
    CANCELLED_DURING_INIT = -1

    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(String(10), index=True)  # 'payme' or 'click'
    transaction_id = Column(String(255), index=True)
    account_id = Column(String(255), index=True)
    amount = Column(Float)
    state = Column(Integer, default=CREATED, index=True)
    reason = Column(Integer, nullable=True)  # Reason for cancellation
    extra_data = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow, index=True
    )
    performed_at = Column(DateTime, nullable=True, index=True)
    cancelled_at = Column(DateTime, nullable=True, index=True)

    @classmethod
    def create_transaction(
        cls,
        db,
        gateway: str,
        transaction_id: str,
        account_id: str,
        amount: float,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> "PaymentTransaction":
        """
        Create a new transaction or get an existing one.

        Args:
            db: Database session
            gateway: Payment gateway (payme or click)
            transaction_id: Transaction ID from the payment system
            account_id: Account or order ID
            amount: Payment amount
            extra_data: Additional data for the transaction

        Returns:
            PaymentTransaction instance
        """
        # Check if transaction already exists
        transaction = db.query(cls).filter(
            cls.gateway == gateway,
            cls.transaction_id == transaction_id
        ).first()

        if transaction:
            return transaction

        # Create new transaction
        transaction = cls(
            gateway=gateway,
            transaction_id=transaction_id,
            account_id=str(account_id),
            amount=amount,
            state=cls.CREATED,
            extra_data=extra_data or {}
        )

        db.add(transaction)
        db.commit()
        db.refresh(transaction)

        return transaction

    def mark_as_paid(self, db) -> "PaymentTransaction":
        """
        Mark the transaction as paid.

        Args:
            db: Database session

        Returns:
            PaymentTransaction instance
        """
        if self.state != self.SUCCESSFULLY:
            self.state = self.SUCCESSFULLY
            self.performed_at = datetime.utcnow()

            db.commit()
            db.refresh(self)

        return self

    def mark_as_cancelled(
        self, db, reason: Optional[str] = None
    ) -> "PaymentTransaction":
        """
        Mark the transaction as cancelled.

        Args:
            db: Database session
            reason: Reason for cancellation

        Returns:
            PaymentTransaction instance
        """
        if reason is None:
            reason_code = 5  # REASON_FUND_RETURNED
        else:
            if isinstance(reason, str) and reason.isdigit():
                reason_code = int(reason)
            else:
                reason_code = reason

        if self.state not in [self.CANCELLED, self.CANCELLED_DURING_INIT]:
            if self.state == self.INITIATING or reason_code == 3:
                self.state = self.CANCELLED_DURING_INIT
            else:
                # Otherwise, set state to CANCELLED (-2)
                self.state = self.CANCELLED

            self.cancelled_at = datetime.utcnow()

        # Store the reason directly in the reason column
        self.reason = reason_code

        # For backward compatibility, also store in extra_data
        extra_data = self.extra_data or {}
        extra_data['cancel_reason'] = reason_code
        self.extra_data = extra_data

        db.commit()
        db.refresh(self)

        return self


def run_migrations(engine: Any) -> None:
    """
    Run database migrations for PayTechUZ FastAPI integration.

    This function creates all necessary tables in the database for the
    PayTechUZ payment system. Call this function when setting up your FastAPI
    application to ensure all required database tables are created.

    Example:
        ```python
        from sqlalchemy import create_engine
        from paytechuz.integrations.fastapi.models import run_migrations

        engine = create_engine("sqlite:///./payments.db")
        run_migrations(engine)
        ```

    Args:
        engine: SQLAlchemy engine instance
    """
    Base.metadata.create_all(bind=engine)
