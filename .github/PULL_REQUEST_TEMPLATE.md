## What this changes

<!-- What the change does, and why it is correct. -->

## Related issue

<!-- Fixes #123, or "none". -->

## Checklist

- [ ] `make test` passes
- [ ] `make lint` passes
- [ ] A test covers the change and fails without it
- [ ] No credentials, keys or card data in the diff
- [ ] Documentation updated if behaviour or configuration changed
- [ ] `CHANGELOG.md` updated

## Gateway protocol changes

<!-- Delete this section if it does not apply. -->

Webhook response shapes and error codes are a contract with the provider.
If this pull request changes one, state which provider, which method, the old
and new response, and the documentation that justifies it.
