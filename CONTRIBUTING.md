# Contributing

Thanks for considering a contribution. This library moves real money, so the
bar for correctness is high — but the workflow is ordinary.

## Getting set up

```bash
git clone https://github.com/PayTechUz/paytechuz.git
cd paytechuz
make install-dev     # editable install with the django, fastapi and dev extras
make test            # 34 tests, no network, no credentials
```

`make install-dev` creates nothing outside the current environment; use a
virtualenv if you want isolation.

## Before opening a pull request

```bash
make test    # pytest
make lint    # flake8 --max-line-length=120
make build   # sdist + wheel, to catch packaging mistakes
```

CI runs the same three on Python 3.8 through 3.12. A pull request that fails
any of them will not be reviewed until it is green.

## What a good pull request looks like

- **One concern per pull request.** A bug fix and a refactor in the same diff
  take far longer to review.
- **A test that fails without the change.** For a bug fix this is the single
  most useful thing you can provide.
- **No network in tests.** Every test must pass offline with no credentials.
  Mock the gateway; see `tests/test_click_gateway.py` for the pattern.
- **Explain the why in the commit message.** What the diff does is visible;
  why it is correct is not.

## Things to be careful with

**Never commit credentials.** No merchant keys, no card tokens, no `.env`
files. If a test needs a value, invent an obviously fake one.

**Amount units.** Payme, Uzum and Paynet speak tiyin; the gateway constructors
take som and convert. When you touch amount handling, state the unit in the
code and check both directions.

**Webhook responses are a protocol, not an API you design.** Each provider
specifies exact error codes and response shapes. Changing one is a breaking
change for every merchant using it, even when the new shape looks better.

**Migrations.** The Django integration ships migrations under the app label
`django`. Adding a field means adding a migration; never edit an existing one.

## Adding a payment gateway

`docs/abstract_webhook.md` is the contract: what every provider must
implement, in what order, and the checklist of things that are easy to miss
(idempotency, one-time-payment conflicts, amount validation, signature
verification). Read it first.

In short, a new provider needs:

1. `paytechuz/gateways/<name>/` with `client.py` and `constants.py`
2. `paytechuz/integrations/django/webhooks/<name>.py`
3. A base view in `paytechuz/integrations/django/views.py`
4. The gateway added to `paytechuz/core/constants.py` and `factory.py`
5. A choice added to `PaymentTransaction.GATEWAY_CHOICES` plus a migration
6. Tests covering the auth failure, the amount mismatch, the happy path and a
   duplicate callback
7. README and documentation updates

## Reporting bugs

Open an issue with the version, the framework and version, what you sent and
what came back. Redact keys. If it involves a webhook, the raw request body
and the response are usually enough to reproduce.

For anything security-sensitive, do not open an issue — see
[SECURITY.md](SECURITY.md).

## Questions

[Telegram](https://t.me/paytechuz) for quick questions, GitHub issues for
anything that needs a paper trail.
