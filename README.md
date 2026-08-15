# paytechuz

[![PyPI version](https://badge.fury.io/py/paytechuz.svg)](https://pypi.org/project/paytechuz/)
[![Python Versions](https://img.shields.io/pypi/pyversions/paytechuz.svg)](https://pypi.org/project/paytechuz/)
[![CI](https://github.com/PayTechUz/paytechuz/actions/workflows/ci.yml/badge.svg)](https://github.com/PayTechUz/paytechuz/actions/workflows/ci.yml)
[![Documentation](https://img.shields.io/badge/docs-pay--tech.uz-blue.svg)](https://pay-tech.uz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

One library for the payment gateways used in Uzbekistan — **Payme, Click,
Uzum, Paynet and Octo** — with the same interface for each, and webhook
handlers for Django and FastAPI that you subclass instead of writing.

Fully open source: pure Python, no compiled extensions, no license key, no
telemetry. Everything the package does at runtime is in this repository.

📖 **[Documentation](https://pay-tech.uz)** &nbsp;|&nbsp; 💬 **[Telegram](https://t.me/paytechuz)** &nbsp;|&nbsp; 📋 **[Changelog](CHANGELOG.md)**

## Contents

- [Features](#features)
- [Compatibility](#compatibility)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Generate payment links](#generate-payment-links)
  - [Provider notes](#provider-notes)
- [Django Integration](#django-integration)
- [FastAPI Integration](#fastapi-integration)
- [The transaction table](#the-transaction-table)
- [Project layout](#project-layout)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Unified API**: consistent interface for multiple payment providers
- **Framework integration**: native support for Django and FastAPI
- **Webhook handling**: ready-to-use webhook handlers for payment notifications
- **Transaction management**: automatic transaction tracking in a single table
- **Extensible**: adding a new provider means adding one gateway and one webhook class

## Compatibility

| | Supported |
| --- | --- |
| Python | 3.8 – 3.12 |
| Django | 3.0 – 5.x |
| FastAPI | 0.68 – 0.x, with SQLAlchemy 1.4 – 2.x and pydantic 2.x |
| Gateways | Payme, Click, Uzum, Paynet, Octo |

Webhook handlers for Uzum, Paynet and Octo are currently Django only. Payme and
Click are available on both frameworks.

## Installation

```bash
pip install paytechuz

# For Django
pip install "paytechuz[django]"

# For FastAPI
pip install "paytechuz[fastapi]"
```

> **Upgrading from 0.3.x?** `0.4.0` removes the license key entirely — delete
> `PAYTECH_LICENSE_API_KEY` from your environment, it is no longer read. Public
> imports are unchanged. See the [changelog](CHANGELOG.md) for the full list.

## Quick Start

### Generate payment links

```python
from paytechuz.gateways.payme import PaymeGateway
from paytechuz.gateways.click import ClickGateway
from paytechuz.gateways.uzum import UzumGateway
from paytechuz.gateways.paynet import PaynetGateway
from paytechuz.gateways.octo import OctoGateway

# Payme
payme = PaymeGateway(
    payme_id="your_payme_id",
    payme_key="your_payme_key",
    is_test_mode=True,  # Set to False in production
)

# Click
click = ClickGateway(
    service_id="your_service_id",
    merchant_id="your_merchant_id",
    merchant_user_id="your_merchant_user_id",
    secret_key="your_secret_key",
    is_test_mode=True,
)

# Uzum (Biller / open-service)
uzum = UzumGateway(
    service_id="your_service_id",
    is_test_mode=True,
)

# Paynet
paynet = PaynetGateway(
    merchant_id="your_merchant_id",  # accepts both str and int
    is_test_mode=False,
)

# Octo
octo = OctoGateway(
    octo_shop_id=123,
    octo_secret="your_octo_secret",
    notify_url="https://example.com/payments/webhook/octo/",
    is_test_mode=True,
)
```

```python
# Payme — amount in som. account_field_name is the field name used in the
# payment URL (e.g. ac.id=123). Default: "order_id".
payme_link = payme.create_payment(
    id="order_123",
    amount=150000,
    return_url="https://example.com/return",
    account_field_name="id",
)

# Click — amount in som
click_link = click.create_payment(
    id="order_123",
    amount=150000,
    description="Test payment",
    return_url="https://example.com/return",
)

# Uzum — amount in som, converted to tiyin in the URL
uzum_link = uzum.create_payment(
    id="order_123",
    amount=100000,
    return_url="https://example.com/callback",
)
# https://www.uzumbank.uz/open-service?serviceId=...&order_id=order_123&amount=10000000&redirectUrl=...

# Paynet — amount in tiyin, optional
paynet_link = paynet.create_payment(id="order_123", amount=15000000)
# https://app.paynet.uz/?m=your_merchant_id&c=order_123&a=15000000

paynet_link_no_amount = paynet.create_payment(id="order_123")
# https://app.paynet.uz/?m=your_merchant_id&c=order_123

# Octo — amount in som, one-stage (auto_capture)
octo_link = octo.create_payment(
    id="order_123",
    amount=50000,
    return_url="https://example.com/payment/done/",
    description="Order #123",
)
```

You can also build a gateway by name:

```python
from paytechuz import create_gateway

payme = create_gateway("payme", payme_id="...", payme_key="...", is_test_mode=True)
```

### Provider notes

**Payme `account_field_name`** — only Payme uses this parameter. It sets the account
key inside the payment URL (`ac.<account_field_name>=<id>`). Other gateways ignore it.

**Paynet** — URL-based, mobile-first:

- URL format: `https://app.paynet.uz/?m={merchant_id}&c={payment_id}&a={amount}`
- `merchant_id` accepts both `str` and `int`
- `amount` is optional and expressed in tiyin
- no return URL support
- desktop users scan a QR code, mobile users open the Paynet app
- payment status arrives through JSON-RPC 2.0 webhooks

## Django Integration

1. Create your order model:

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

2. Add the app and configure the settings:

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
        'ACCOUNT_MODEL': 'orders.models.Order',
        'ACCOUNT_FIELD': 'id',
        'AMOUNT_FIELD': 'amount',
        'ONE_TIME_PAYMENT': True,
    },
    'CLICK': {
        'SERVICE_ID': 'your_service_id',
        'MERCHANT_ID': 'your_merchant_id',
        'MERCHANT_USER_ID': 'your_merchant_user_id',
        'SECRET_KEY': 'your_secret_key',
        'ACCOUNT_MODEL': 'orders.models.Order',
        'ACCOUNT_FIELD': 'id',
        'AMOUNT_FIELD': 'amount',
        'COMMISSION_PERCENT': 0.0,
        'ONE_TIME_PAYMENT': True,
    },
    'UZUM': {
        'SERVICE_ID': 'your_service_id',
        'USERNAME': 'your_uzum_username',   # webhook Basic auth
        'PASSWORD': 'your_uzum_password',   # webhook Basic auth
        'ACCOUNT_MODEL': 'orders.models.Order',
        'ACCOUNT_FIELD': 'order_id',        # or 'id'
        'AMOUNT_FIELD': 'amount',
        'ONE_TIME_PAYMENT': True,
    },
    'PAYNET': {
        'SERVICE_ID': 'your_paynet_service_id',
        'USERNAME': 'your_paynet_username',
        'PASSWORD': 'your_paynet_password',
        'ACCOUNT_MODEL': 'orders.models.Order',
        'ACCOUNT_FIELD': 'id',
        'AMOUNT_FIELD': 'amount',
        'ONE_TIME_PAYMENT': True,
    },
    'OCTO_BANK': {
        'OCTO_SHOP_ID': 42125,
        'OCTO_SECRET': 'your_octo_secret',
        'OCTO_UNIQUE_KEY': 'your_octo_unique_key',  # required in production
        'NOTIFY_URL': 'https://example.com/payments/webhook/octo/',
        'ACCOUNT_MODEL': 'orders.models.Order',
        'ACCOUNT_FIELD': 'id',
        'AMOUNT_FIELD': 'amount',
        'ONE_TIME_PAYMENT': True,
        'TEST_MODE': True,  # False in production — enables signature verification
    },
}
```

> **Note:** `is_test_mode` is a gateway constructor argument, not a webhook setting.
> Webhooks receive requests on the same URL in both test and production.

3. Run migrations:

```bash
python manage.py migrate
```

4. Create the webhook views:

```python
# views.py
from paytechuz.integrations.django.views import (
    BasePaymeWebhookView,
    BaseClickWebhookView,
    BaseUzumWebhookView,
    BasePaynetWebhookView,
    BaseOctoWebhookView,
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

    def get_check_data(self, params, account):  # optional
        # Extra data for CheckPerformTransaction (fiscal receipt)
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
                        "package_code": "123456",
                    }
                ],
            },
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

    def get_check_data(self, params, account):  # optional
        return {"fio": {"value": "Ivanov Ivan"}}


class PaynetWebhookView(BasePaynetWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'paid'
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'cancelled'
        order.save()

    def get_check_data(self, params, account):  # optional
        # Extra data for GetInformation
        return {
            "fields": {
                "first_name": account.user.first_name,
                "balance": account.user.balance,
            }
        }


class OctoWebhookView(BaseOctoWebhookView):
    def successfully_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'paid'
        order.save()

    def cancelled_payment(self, params, transaction):
        order = Order.objects.get(id=transaction.account_id)
        order.status = 'cancelled'
        order.save()
```

5. Register the webhook URLs:

```python
# urls.py
from django.urls import path

from .views import (
    PaymeWebhookView,
    ClickWebhookView,
    UzumWebhookView,
    PaynetWebhookView,
    OctoWebhookView,
)

urlpatterns = [
    path('payments/webhook/payme/', PaymeWebhookView.as_view(), name='payme_webhook'),
    path('payments/webhook/click/', ClickWebhookView.as_view(), name='click_webhook'),
    path('payments/webhook/uzum/<str:action>/', UzumWebhookView.as_view(), name='uzum_webhook'),
    path('payments/webhook/paynet/', PaynetWebhookView.as_view(), name='paynet_webhook'),
    path('payments/webhook/octo/', OctoWebhookView.as_view(), name='octo_webhook'),
]
```

## FastAPI Integration

1. Set up the database models:

```python
from datetime import datetime, timezone

from sqlalchemy import create_engine, Column, Integer, String, Numeric, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

from paytechuz.integrations.fastapi import run_migrations

SQLALCHEMY_DATABASE_URL = "sqlite:///./payments.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)

Base = declarative_base()


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    product_name = Column(String, index=True)
    amount = Column(Numeric(12, 2))
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


# Create the paytechuz payments table
run_migrations(engine)

# Create your own tables
Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
```

2. Create the webhook routes:

```python
from fastapi import FastAPI, Request, Depends
from sqlalchemy.orm import Session

from paytechuz.integrations.fastapi import PaymeWebhookHandler, ClickWebhookHandler

app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class CustomPaymeWebhookHandler(PaymeWebhookHandler):
    def successfully_payment(self, params, transaction):
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "paid"
        self.db.commit()

    def cancelled_payment(self, params, transaction):
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "cancelled"
        self.db.commit()


class CustomClickWebhookHandler(ClickWebhookHandler):
    def successfully_payment(self, params, transaction):
        order = self.db.query(Order).filter(Order.id == transaction.account_id).first()
        order.status = "paid"
        self.db.commit()

    def cancelled_payment(self, params, transaction):
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
        amount_field='amount',
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
        amount_field='amount',
        one_time_payment=True,
    )
    return await handler.handle_webhook(request)
```

> The FastAPI integration currently ships webhook handlers for Payme and Click.
> Uzum, Paynet and Octo webhooks are available for Django.

## The transaction table

Both integrations record every callback in one table, `payments`, so you rarely
need provider-specific queries.

```python
from paytechuz.integrations.django.models import PaymentTransaction

paid = PaymentTransaction.objects.filter(
    gateway=PaymentTransaction.PAYME,
    state=PaymentTransaction.SUCCESSFULLY,
)
```

| Column | Meaning |
| --- | --- |
| `gateway` | `payme`, `click`, `uzum`, `paynet` or `octo` |
| `transaction_id` | the provider's id; unique together with `gateway` |
| `account_id` | your order's primary key, as a string |
| `amount` | in som, not tiyin |
| `state` | see below |
| `reason` | provider cancellation code, when one was sent |
| `extra_data` | the raw callback payload |
| `created_at` / `performed_at` / `cancelled_at` | timestamps |

States:

| Value | Constant | Meaning |
| --- | --- | --- |
| `0` | `CREATED` | row exists, nothing confirmed |
| `1` | `INITIATING` | provider created the transaction |
| `2` | `SUCCESSFULLY` | paid |
| `-1` | `CANCELLED_DURING_INIT` | cancelled before it was performed |
| `-2` | `CANCELLED` | cancelled after a successful payment |

> **Note on the Django app label.** The integration is installed as
> `paytechuz.integrations.django`, so Django derives the app label `django` and
> its migrations are recorded under that name. This is why `makemigrations`
> output and `django_migrations` rows mention an app called `django`.

## Project layout

```
paytechuz/
├── core/                     # shared base classes, HTTP client, exceptions, utils
├── gateways/                 # one package per provider (client + constants)
│   ├── payme/  click/  uzum/  paynet/  octo/
└── integrations/
    ├── django/               # models, admin, signals, migrations
    │   ├── webhooks/         # one webhook handler per provider
    │   └── views.py          # CSRF-exempt base views
    └── fastapi/              # SQLAlchemy models, pydantic schemas, handlers
```

`docs/abstract_webhook.md` describes the shared webhook contract and the
checklist to follow when adding a new provider.

## Development

```bash
make install-dev   # editable install with django, fastapi and dev extras
make test          # run the test suite
make lint          # flake8
make build         # build sdist + wheel into dist/
```

## Contributing

Pull requests are welcome. [CONTRIBUTING.md](CONTRIBUTING.md) covers the setup,
what CI checks, and the extra care that amount handling and webhook protocols
need. `docs/abstract_webhook.md` is the contract to follow when adding a
gateway.

Found a security issue? Do not open an issue — see [SECURITY.md](SECURITY.md).

## License

MIT — see [LICENSE](LICENSE).
