
# paytechuz

[![PyPI version](https://badge.fury.io/py/paytechuz.svg)](https://badge.fury.io/py/paytechuz)
[![Python Versions](https://img.shields.io/pypi/pyversions/paytechuz.svg)](https://pypi.org/project/paytechuz/)
[![Documentation](https://img.shields.io/badge/docs-pay--tech.uz-blue.svg)](https://pay-tech.uz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PayTechUZ is a unified payment library for integrating with popular payment systems in Uzbekistan. It provides a simple and consistent interface for working with Payme, Click, Uzum, and Paynet payment gateways.

📖 **[Complete Documentation](https://pay-tech.uz)** | 🚀 **[Quick Start Guide](https://pay-tech.uz/quickstart)**

## Features

- **API**: Consistent interface for multiple payment providers
- **Secure**: Built-in security features for payment processing
- **Framework Integration**: Native support for Django and FastAPI
- **Webhook Handling**: Easy-to-use webhook handlers for payment notifications
- **Transaction Management**: Automatic transaction tracking and management
- **Extensible**: Easy to add new payment providers
## Installation

### Basic Installation

```bash
pip install paytechuz
```

### Framework-Specific Installation

```bash
# For Django
pip install paytechuz[django]

# For FastAPI
pip install paytechuz[fastapi]

# For Flask
pip install paytechuz[flask]
```

## API Key Configuration

**Important:** PayTechUZ requires a valid license API key for license validation. Plz set it to .env

```bash
# Set your license API key as an environment variable
export PAYTECH_LICENSE_API_KEY="your-license-api-key-here"
```

To obtain a production license API key, please visit **[https://pay-tech.uz/console](https://pay-tech.uz/console)** or contact **@muhammadali_me** on Telegram.

## Quick Start

> 💡 **Need help?** Check out our [complete documentation](https://pay-tech.uz) for detailed guides and examples.

### Generate Payment Links

```python
from paytechuz.gateways.payme import PaymeGateway
from paytechuz.gateways.click import ClickGateway
from paytechuz.gateways.uzum.client import UzumGateway
from paytechuz.gateways.paynet import PaynetGateway

# Initialize Payme gateway
payme = PaymeGateway(
    payme_id="your_payme_id",
    payme_key="your_payme_key",
    is_test_mode=True  # Set to False in production environment
)

# Initialize Click gateway
click = ClickGateway(
    service_id="your_service_id",
    merchant_id="your_merchant_id",
    merchant_user_id="your_merchant_user_id",
    secret_key="your_secret_key",
    is_test_mode=True  # Set to False in production environment
)

# Initialize Uzum gateway (Biller/open-service)
uzum = UzumGateway(
    service_id="your_service_id",  # Uzum Service ID
    is_test_mode=True  # Set to False in production environment
)

# Initialize Paynet gateway
paynet = PaynetGateway(
    merchant_id="your_merchant_id",  # Paynet Merchant ID (accepts both str and int)
    is_test_mode=False  # Set to True for testing
)

# Generate payment links
payme_link = payme.create_payment(
    id="order_123",
    amount=150000,  # amount in UZS
    return_url="https://example.com/return",
    account_field_name="id"  # Payme-specific: field name for account ID (default: "order_id")
)
# Note: account_field_name is only used for Payme and specifies the field name
# that will be used in the payment URL (e.g., ac.id=123).
# Other payment gateways (Click, Uzum) don't use this parameter.

click_link = click.create_payment(
    id="order_123",
    amount=150000,  # amount in UZS
    description="Test payment",
    return_url="https://example.com/return"
)


# Generate Uzum Biller payment URL
# URL format: https://www.uzumbank.uz/open-service?serviceId=...&order_id=...&amount=...&redirectUrl=...
uzum_link = uzum.create_payment(
    id="order_123",  # Order ID (order_id parameter)
    amount=100000,  # amount in som (will be converted to tiyin)
    return_url="https://example.com/callback"  # redirectUrl parameter
)
# Result: https://www.uzumbank.uz/open-service?serviceId=your_service_id&order_id=order_123&amount=10000000&redirectUrl=https%3A%2F%2Fexample.com%2Fcallback

# Generate Paynet payment URL
# URL format: https://app.paynet.uz/?m={merchant_id}&c={payment_id}&a={amount}
paynet_link = paynet.create_payment(
    id="order_123",  # Payment ID (c parameter)
    amount=15000000  # amount in tiyin (optional, a parameter) - 150000 som = 15000000 tiyin
)
# Result: https://app.paynet.uz/?m=your_merchant_id&c=order_123&a=15000000

# Or without amount (amount will be configured on Paynet's side)
paynet_link_no_amount = paynet.create_payment(id="order_123")
# Result: https://app.paynet.uz/?m=your_merchant_id&c=order_123
```

### Important Notes

#### Payme `account_field_name` Parameter
**Example**:
```python
# Using default account_field_name = "order_id"
payme_link = payme.create_payment(
    id="123",
    amount=150000,
    return_url="https://example.com/return"
)
# Using custom account_field_name
payme_link = payme.create_payment(
    id="123",
    amount=150000,
    return_url="https://example.com/return",
    account_field_name="id"
)
```

**Note**: Other payment gateways (Click, Uzum, Paynet) do not use the `account_field_name` parameter.

#### Paynet Payment Gateway

Paynet uses a unique URL-based payment system:

- **URL Format**: `https://app.paynet.uz/?m={merchant_id}&c={payment_id}&a={amount}`
- **merchant_id**: Accepts both `str` and `int` types (automatically converted to string)
- **amount**: Optional parameter in tiyin. If provided, it will be included in the URL as `a` parameter
- **No return_url**: Paynet does NOT support return URL parameter
- **Mobile-first**: Payment is completed in the Paynet mobile app
  - Desktop users: QR code is displayed to scan
  - Mobile users: Direct link to open Paynet app
- **Webhooks**: Payment status updates are handled through JSON-RPC 2.0 webhooks


### Django Integration

1. Create Order model:

```python
# models.py
from django.db import models
from django.utils import timezone

class Order(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
        ('delivered', 'Delivered'),
    )

    product_name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.id} - {self.product_name} ({self.amount})"
```

2. Add to `INSTALLED_APPS` and configure settings:

```python
# settings.py
INSTALLED_APPS = [
    # ...
    'paytechuz.integrations.django',
]

PAYTECHUZ = {
    'PAYME': {
        'PAYME_ID': 'your_payme_id',
        'PAYME_KEY': 'your_payme_key',
        'ACCOUNT_MODEL': 'your_app.models.Order',  # For example: 'orders.models.Order'
        'ACCOUNT_FIELD': 'id',
        'AMOUNT_FIELD': 'amount',
        'ONE_TIME_PAYMENT': True,
    },
    'CLICK': {
        'SERVICE_ID': 'your_service_id',
        'MERCHANT_ID': 'your_merchant_id',
        'MERCHANT_USER_ID': 'your_merchant_user_id',
        'SECRET_KEY': 'your_secret_key',
        'ACCOUNT_MODEL': 'your_app.models.Order',
        'ACCOUNT_FIELD': 'id',
        'COMMISSION_PERCENT': 0.0,
        'ONE_TIME_PAYMENT': True,
    },

    'UZUM': {
        'SERVICE_ID': 'your_service_id',  # Uzum Service ID for Biller URL
        'USERNAME': 'your_uzum_username',  # For webhook Basic Auth
        'PASSWORD': 'your_uzum_password',  # For webhook Basic Auth
        'ACCOUNT_MODEL': 'your_app.models.Order',
        'ACCOUNT_FIELD': 'order_id',  # or 'id'
        'AMOUNT_FIELD': 'amount',
        'ONE_TIME_PAYMENT': True,
    },
    'PAYNET': {
        'SERVICE_ID': 'your_paynet_service_id',
        'USERNAME': 'your_paynet_username',
        'PASSWORD': 'your_paynet_password',
        'ACCOUNT_MODEL': 'your_app.models.Order',
        'ACCOUNT_FIELD': 'id',
        'AMOUNT_FIELD': 'amount',
        'ONE_TIME_PAYMENT': True,
    }
}
```

> **Note:** The `IS_TEST_MODE` parameter is configured when creating payment gateways (e.g., `PaymeGateway`, `ClickGateway`), not in webhook settings. Webhooks receive requests on the same URL regardless of test or production environment.

3. Create webhook handlers:

```python
# views.py
from paytechuz.integrations.django.views import (
    BasePaymeWebhookView,
    BaseClickWebhookView,
    BaseUzumWebhookView,
    BasePaynetWebhookView
)
from .models import Order

class PaymeWebhookView(BasePaymeWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'paid'
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'cancelled'
        order.save()

    def get_check_data(self, params, account): # optional
        # Return additional data for CheckPerformTransaction (fiscal receipt)
        return {
            "additional": {"first_name": account.first_name, "balance": account.balance},
            "detail": {
                "receipt_type": 0,
                "shipping": {"title": "Yetkazib berish", "price": 10000},
                "items": [
                    {
                        "discount": 0,
                        "title": account.product_name,
                        "price": int(account.amount * 100),
                        "count": 1,
                        "code": "00001",
                        "units": 1,
                        "vat_percent": 0,
                        "package_code": "123456"
                    }
                ]
            }
        }

class ClickWebhookView(BaseClickWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'paid'
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'cancelled'
        order.save()



class UzumWebhookView(BaseUzumWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'paid'
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'cancelled'
        order.save()

    def get_check_data(self, params, account):
        # Return additional data for check/create/status/confirm actions
        # Example: returning user's full name
        return {
            "fio": {
                "value": "Ivanov Ivan"
            }
        }

class PaynetWebhookView(BasePaynetWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'paid'
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'cancelled'
        order.save()

    def get_check_data(self, params, account) # optional:
        # Return additional data for GetInformation
        order = Order.objects.get(id=account.id)
        # You can use any key value pairs
        return {
            "fields": {
                "first_name": order.user.first_name,
                "balance": order.user.balance
            }
        }
```

4. Add webhook URLs to `urls.py`:

```python
# urls.py
from django.urls import path
from .views import PaymeWebhookView, ClickWebhookView, UzumWebhookView, PaynetWebhookView

urlpatterns = [
    # ...
    path('payments/webhook/payme/', PaymeWebhookView.as_view(), name='payme_webhook'),
    path('payments/webhook/click/', ClickWebhookView.as_view(), name='click_webhook'),

    path('payments/webhook/uzum/<str:action>/', UzumWebhookView.as_view(), name='uzum_webhook'),
    path('payments/webhook/paynet/', PaynetWebhookView.as_view(), name='paynet_webhook'),
]
```

### FastAPI Integration

1. Set up database models:

```python
from datetime import datetime, timezone

from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime

from paytechuz.integrations.fastapi import Base as PaymentsBase
from paytechuz.integrations.fastapi.models import run_migrations


# Create database engine
SQLALCHEMY_DATABASE_URL = "sqlite:///./payments.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# Create base declarative class
Base = declarative_base()

# Create Order model
class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, index=True)
    amount = Column(Float)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

# Create payment tables using run_migrations
run_migrations(engine)

# Create Order table
Base.metadata.create_all(bind=engine)

# Create session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

2. Create webhook handlers:

```python
from fastapi import FastAPI, Request, Depends

from sqlalchemy.orm import Session

from paytechuz.integrations.fastapi import PaymeWebhookHandler, ClickWebhookHandler


app = FastAPI()

# Dependency to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class CustomPaymeWebhookHandler(PaymeWebhookHandler):
    def successfully_payment(self, params, transaction):
        # Handle successful payment
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "paid"
        self.db.commit()

    def cancelled_payment(self, params, transaction):
        # Handle cancelled payment
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "cancelled"
        self.db.commit()

class CustomClickWebhookHandler(ClickWebhookHandler):
    def successfully_payment(self, params, transaction):
        # Handle successful payment
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "paid"
        self.db.commit()

    def cancelled_payment(self, params, transaction):
        # Handle cancelled payment
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "cancelled"
        self.db.commit()

@app.post("/payments/payme/webhook")
async def payme_webhook(request: Request, db: Session = Depends(get_db)):
    handler = CustomPaymeWebhookHandler(
        db=db,
        payme_id="your_merchant_id",
        payme_key="your_merchant_key",
        account_model=Order,
        account_field='id',
        amount_field='amount'
    )
    return await handler.handle_webhook(request)

@app.post("/payments/click/webhook")
async def click_webhook(request: Request, db: Session = Depends(get_db)):
    handler = CustomClickWebhookHandler(
        db=db,
        service_id="your_service_id",
        secret_key="your_secret_key",
        account_model=Order,
        account_field='id',
        one_time_payment=True
    )
    return await handler.handle_webhook(request)


```

📖 **Documentation:** [pay-tech.uz](https://pay-tech.uz)  
💬 **Support:** [Telegram](https://t.me/paytechuz)

## License
This project is licensed under the MIT License - see the LICENSE file for details.
