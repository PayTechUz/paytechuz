class UzumEndpoints:
    """Uzum API endpoints."""
    REFUND = "/api/v1/acquiring/refund"


class UzumNetworks:
    """Uzum API networks."""
    PROD_NET = "https://checkout-key.inplat-tech.com"
    TEST_NET = "https://test-chk-api.uzumcheckout.uz"
    # Biller (open-service) URL for direct payment links
    BILLER_URL = "https://www.uzumbank.uz/open-service"


class UzumStatus:
    """Uzum API status codes."""
    OK = "OK"
    FAILED = "FAILED"
    CREATED = "CREATED"
    CONFIRMED = "CONFIRMED"
    REVERSED = "REVERSED"
