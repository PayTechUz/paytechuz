# paytechuz

[![PyPI version](https://badge.fury.io/py/paytechuz.svg)](https://badge.fury.io/py/paytechuz)
[![Python Versions](https://img.shields.io/pypi/pyversions/paytechuz.svg)](https://pypi.org/project/paytechuz/)
[![Documentation](https://img.shields.io/badge/docs-pay--tech.uz-blue.svg)](https://pay-tech.uz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

PayTechUZ is a unified payment library for integrating with popular payment systems in Uzbekistan. It provides a simple and consistent interface for working with Payme, Click, Atmos, and Uzum payment gateways.

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

**Important:** PayTechUZ requires a valid license API key for license validation.

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
from paytechuz.gateways.atmos import AtmosGateway
from paytechuz.gateways.uzum.client import UzumGateway

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

# Initialize Atmos gateway
atmos = AtmosGateway(
    consumer_key="your_consumer_key",
    consumer_secret="your_consumer_secret",
    store_id="your_store_id",
    terminal_id="your_terminal_id",  # optional
    is_test_mode=True  # Set to False in production environment
)

# Initialize Uzum gateway (Biller/open-service)
uzum = UzumGateway(
    service_id="your_service_id",  # Uzum Service ID
    is_test_mode=True  # Set to False in production environment
)

# Generate payment links
payme_link = payme.create_payment(
    id="order_123",
    amount=150000,  # amount in UZS
    return_url="https://example.com/return"
)

click_link = click.create_payment(
    id="order_123",
    amount=150000,  # amount in UZS
    description="Test payment",
    return_url="https://example.com/return"
)

atmos_link = atmos.create_payment(
    account_id="order_123",
    amount=150000  # amount in UZS
)

# Generate Uzum Biller payment URL
# URL format: https://www.uzumbank.uz/open-service?serviceId=...&order_id=...&amount=...&redirectUrl=...
uzum_link = uzum.create_payment(
    id="order_123",  # Order ID (order_id parameter)
    amount=100000,  # amount in som (will be converted to tiyin)
    return_url="https://example.com/callback"  # redirectUrl parameter
)
# Result: https://www.uzumbank.uz/open-service?serviceId=your_service_id&order_id=order_123&amount=10000000&redirectUrl=https%3A%2F%2Fexample.com%2Fcallback
```

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
        'IS_TEST_MODE': True,  # Set to False in production
    },
    'CLICK': {
        'SERVICE_ID': 'your_service_id',
        'MERCHANT_ID': 'your_merchant_id',
        'MERCHANT_USER_ID': 'your_merchant_user_id',
        'SECRET_KEY': 'your_secret_key',
        'ACCOUNT_MODEL': 'your_app.models.Order',
        'COMMISSION_PERCENT': 0.0,
        'IS_TEST_MODE': True,  # Set to False in production
    },
    'ATMOS': {
        'CONSUMER_KEY': 'your_atmos_consumer_key',
        'CONSUMER_SECRET': 'your_atmos_consumer_secret',
        'STORE_ID': 'your_atmos_store_id',
        'TERMINAL_ID': 'your_atmos_terminal_id',  # Optional
        'API_KEY': 'your_atmos_api_key'
        'ACCOUNT_MODEL': 'your_app.models.Order',
        'ACCOUNT_FIELD': 'id',
        'IS_TEST_MODE': True,  # Set to False in production
    },
    'UZUM': {
        'SERVICE_ID': 'your_service_id',  # Uzum Service ID for Biller URL
        'USERNAME': 'your_uzum_username',  # For webhook Basic Auth
        'PASSWORD': 'your_uzum_password',  # For webhook Basic Auth
        'ACCOUNT_MODEL': 'your_app.models.Order',
        'ACCOUNT_FIELD': 'order_id',  # or 'id'
        'AMOUNT_FIELD': 'amount',
        'IS_TEST_MODE': True,  # Set to False in production
    }
}
```

3. Create webhook handlers:

```python
# views.py
from paytechuz.integrations.django.views import (
    BasePaymeWebhookView,
    BaseClickWebhookView,
    BaseAtmosWebhookView,
    BaseUzumWebhookView
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

class ClickWebhookView(BaseClickWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'paid'
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'cancelled'
        order.save()

class AtmosWebhookView(BaseAtmosWebhookView):
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
```

4. Add webhook URLs to `urls.py`:

```python
# urls.py
from django.urls import path
from .views import PaymeWebhookView, ClickWebhookView, AtmosWebhookView, UzumWebhookView

urlpatterns = [
    # ...
    path('payments/webhook/payme/', PaymeWebhookView.as_view(), name='payme_webhook'),
    path('payments/webhook/click/', ClickWebhookView.as_view(), name='click_webhook'),
    path('payments/webhook/atmos/', AtmosWebhookView.as_view(), name='atmos_webhook'),
    path('payments/webhook/uzum/<str:action>/', UzumWebhookView.as_view(), name='uzum_webhook'),
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
from paytechuz.gateways.atmos.webhook import AtmosWebhookHandler


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
        account_model=Order
    )
    return await handler.handle_webhook(request)

@app.post("/payments/atmos/webhook")
async def atmos_webhook(request: Request, db: Session = Depends(get_db)):
    import json

    # Atmos webhook handler
    atmos_handler = AtmosWebhookHandler(license_api_key="your_atmos_api_key")

    try:
        # Get request body
        body = await request.body()
        webhook_data = json.loads(body.decode('utf-8'))

        # Process webhook
        response = atmos_handler.handle_webhook(webhook_data)

        if response['status'] == 1:
            # Payment successful
            invoice = webhook_data.get('invoice')

            # Update order status
            order = db.query(Order).filter(Order.id == invoice).first()
            if order:
                order.status = "paid"
                db.commit()

        return response

    except Exception as e:
        return {
            'status': 0,
            'message': f'Error: {str(e)}'
        }
```

📖 **Documentation:** [pay-tech.uz](https://pay-tech.uz)  
💬 **Support:** [Telegram](https://t.me/paytechuz)

## License
This project is licensed under the MIT License - see the LICENSE file for details.
