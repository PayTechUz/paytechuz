# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1]

Documentation only. The README and this changelog were trimmed; the package
itself is unchanged from `0.4.0`.

## [0.4.0] - 2026-08-15

The library is now fully open source. Everything it does at runtime is in this
repository: pure Python, no compiled extensions. Nothing in the package
contacts an external service other than the payment gateway you configure.

### Removed

- **Compiled distribution.** Wheels are `py3-none-any` instead of
  per-platform binaries. The Cython build pipeline, the Docker build images
  and the `.so` artifacts are removed.
- The Flask extra, which never had an implementation behind it.

### Added

- **Octo gateway** (`paytechuz.gateways.octo.OctoGateway`) and its Django
  webhook view `BaseOctoWebhookView`, both of which existed in the source but
  were missing from the published wheel.
- `LICENSE` (MIT), which the README had always claimed.
- Migration `0003_paymenttransaction_gateway_choices`, aligning the gateway
  choices with the model. It emits no SQL — the previous migration still
  listed `atmos`, removed several versions earlier.
- `create_gateway()` now dispatches to Octo.

### Changed

- **Package layout.** The `internal.py` / `client.py` split and the
  `internal_webhooks/` / `webhooks.py` split existed only to hide compiled
  code. They are merged:

  | Before | After |
  | --- | --- |
  | `gateways/<name>/internal.py` | merged into `gateways/<name>/client.py` |
  | `integrations/django/internal_webhooks/` | `integrations/django/webhooks/` |
  | `integrations/fastapi/internal.py` | merged into `integrations/fastapi/routes.py` |

  Public imports are unchanged: `paytechuz.gateways.payme.PaymeGateway`,
  `paytechuz.integrations.django.views.BasePaymeWebhookView` and
  `paytechuz.integrations.fastapi.PaymeWebhookHandler` all still resolve.

- Packaging moved to a single `pyproject.toml`. The version is read from
  `paytechuz.__version__`, so it is declared in one place.
- Minimum Python is 3.8.

### Fixed

- **Wheel contents.** `gateways/octo` and the Django webhook package were
  missing from the `packages` list, so they never reached the published wheel.
- **`GetStatement` timezone handling.** Date bounds were built with naive
  datetimes, which logged a `RuntimeWarning` for every compared row under
  `USE_TZ` and shifted the comparison by the machine's UTC offset. Payme
  timestamps are now read as UTC and matched to the project's `USE_TZ`
  setting. Paynet's `dateFrom` / `dateTo` are parsed instead of being handed
  to the ORM as raw strings.
- **Click transaction IDs containing underscores.** `check_payment` and
  `cancel_payment` parsed `click_<account_id>_<amount>` by taking the second
  segment, so an account id such as `order_123` was truncated to `order`.
- **Click `merchant_user_id`.** The constructor accepted it and then ignored
  it when building the payment URL.
- FastAPI's `ClickWebhookHandler` read a hardcoded `amount` attribute instead
  of the configured `amount_field`.

## [0.3.51] and earlier

Released as compiled wheels. See the git history for details.

[0.4.0]: https://github.com/PayTechUz/paytechuz/releases/tag/v0.4.0
