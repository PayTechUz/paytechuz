# Security Policy

This library handles payments. A defect here can cost merchants money, so
security reports are treated as the highest priority.

## Supported versions

| Version | Supported |
| --- | --- |
| 0.4.x | Yes |
| 0.3.x and earlier | No — see the note below |

`0.3.x` was distributed as compiled wheels that required a license key. Its
source distributions on PyPI contain the retired license module, including an
offline key list and an HMAC secret. Those values are public and should be
treated as compromised. They grant no access to this project and are not used
by `0.4.x`. If you are on `0.3.x`, upgrade.

## Reporting a vulnerability

**Do not open a public issue.**

Report privately through either channel:

- [GitHub private vulnerability reporting](https://github.com/PayTechUz/paytechuz/security/advisories/new)
- Telegram: [@muhammadali_me](https://t.me/muhammadali_me)

Please include:

- the version of `paytechuz` and of Django or FastAPI
- what an attacker can do, concretely
- the smallest request or code sample that demonstrates it
- whether it is already being exploited, if you know

Redact merchant keys, card data and anything else you would not want in a
transcript.

### What to expect

- Acknowledgement within 72 hours.
- An assessment, with a fix timeline, within 7 days.
- Credit in the release notes if you want it.

Please give a reasonable window for a fix before disclosing publicly.

## Scope

In scope:

- signature and authentication bypass in any webhook handler
- amount, account or transaction-state handling that lets a payment be
  confirmed when it should not be
- replay or idempotency failures that double-credit an account
- injection reachable through gateway callbacks
- secrets leaking into logs, exceptions or responses

Out of scope:

- vulnerabilities in Payme, Click, Uzum, Paynet or Octo themselves — report
  those to the provider
- misconfiguration in an application using the library, such as `DEBUG=True`
  in production or credentials committed to a repository
- missing hardening that has no exploit path

## Notes for integrators

A few properties are the application's responsibility, not the library's:

- **Serve webhooks over HTTPS.** Payme and Click authenticate with a shared
  secret sent on every request; over plain HTTP it is readable in transit.
- **Keep keys out of source control.** Read them from the environment.
- **Do not disable signature verification in production.** For Octo,
  `TEST_MODE: True` skips it entirely; it exists for local testing.
- **Webhook handlers are not idempotent by accident.** Providers retry.
  Override the event hooks so that a repeated callback does not repeat a
  side effect such as shipping an order or crediting a wallet.
