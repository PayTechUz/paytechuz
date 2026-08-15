"""
FastAPI schemas for PayTechUZ.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List

from pydantic import BaseModel, Field


class PaymentTransactionBase(BaseModel):
    """
    Base schema for payment transaction.
    """
    gateway: str = Field(..., description="Payment gateway (payme or click)")
    transaction_id: str = Field(
        ..., description="Transaction ID from the payment system"
    )
    account_id: str = Field(..., description="Account or order ID")
    amount: float = Field(..., description="Payment amount")
    state: int = Field(0, description="Transaction state")


class PaymentTransactionCreate(PaymentTransactionBase):
    """
    Schema for creating a payment transaction.
    """
    extra_data: Optional[Dict[str, Any]] = Field(
        None, description="Additional data for the transaction"
    )


class PaymentTransaction(PaymentTransactionBase):
    """
    Schema for payment transaction.
    """
    id: int = Field(..., description="Transaction ID")
    extra_data: Dict[str, Any] = Field(
        {}, description="Additional data for the transaction"
    )
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    performed_at: Optional[datetime] = Field(
        None, description="Payment timestamp"
    )
    cancelled_at: Optional[datetime] = Field(
        None, description="Cancellation timestamp"
    )

    class Config:
        """
        Pydantic configuration.
        """
        from_attributes = True


class PaymentTransactionList(BaseModel):
    """
    Schema for a list of payment transactions.
    """
    transactions: List[PaymentTransaction] = Field(
        ..., description="List of transactions"
    )
    total: int = Field(..., description="Total number of transactions")


class PaymeWebhookRequest(BaseModel):
    """
    Schema for Payme webhook request.
    """
    method: str = Field(..., description="Method name")
    params: Dict[str, Any] = Field(..., description="Method parameters")
    id: int = Field(..., description="Request ID")


class PaymeWebhookResponse(BaseModel):
    """
    Schema for Payme webhook response.
    """
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: int = Field(..., description="Request ID")
    result: Dict[str, Any] = Field(..., description="Response result")


class PaymeWebhookErrorResponse(BaseModel):
    """
    Schema for Payme webhook error response.
    """
    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: int = Field(..., description="Request ID")
    error: Dict[str, Any] = Field(..., description="Error details")


class ClickWebhookRequest(BaseModel):
    """
    Schema for Click webhook request.
    """
    click_trans_id: str = Field(..., description="Click transaction ID")
    service_id: str = Field(..., description="Service ID")
    merchant_trans_id: str = Field(..., description="Merchant transaction ID")
    amount: str = Field(..., description="Payment amount")
    action: str = Field(..., description="Action (0 - prepare, 1 - complete)")
    sign_time: str = Field(..., description="Signature timestamp")
    sign_string: str = Field(..., description="Signature string")
    error: Optional[str] = Field(None, description="Error code")
    error_note: Optional[str] = Field(None, description="Error note")


class ClickWebhookResponse(BaseModel):
    """
    Schema for Click webhook response.
    """
    click_trans_id: str = Field(..., description="Click transaction ID")
    merchant_trans_id: str = Field(..., description="Merchant transaction ID")
    merchant_prepare_id: Optional[int] = Field(
        None, description="Merchant prepare ID"
    )
    error: int = Field(0, description="Error code")
    error_note: str = Field("Success", description="Error note")
