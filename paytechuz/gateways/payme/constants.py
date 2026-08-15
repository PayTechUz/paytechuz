class PaymeEndpoints:
    """Payme API endpoints."""
    RECEIPTS_CREATE = "receipts.create"
    RECEIPTS_PAY = "receipts.pay"
    RECEIPTS_SEND = "receipts.send"
    RECEIPTS_CHECK = "receipts.check"
    RECEIPTS_CANCEL = "receipts.cancel"
    RECEIPTS_GET = "receipts.get"
    CARDS_CREATE = "cards.create"
    CARDS_VERIFY = "cards.verify"
    CARDS_CHECK = "cards.check"
    CARDS_REMOVE = "cards.remove"
    CARDS_GET_VERIFY_CODE = "cards.get_verify_code"


class PaymeNetworks:
    """Payme API networks."""
    TEST_NET = "https://checkout.test.paycom.uz/api"
    PROD_NET = "https://checkout.paycom.uz/api"


class PaymeCancelReason:
    """Payme cancel reason codes."""
    REASON_USER_NOT_FOUND = 1
    REASON_DEBIT_OPERATION_FAILED = 2
    REASON_EXECUTION_ERROR = 3
    REASON_TIMEOUT = 4
    REASON_FUND_RETURNED = 5
    REASON_UNKNOWN = 6
    REASON_CANCELLED_BY_USER = 7
    REASON_SUSPICIOUS_OPERATION = 8
    REASON_MERCHANT_DECISION = 9


class PaymeErrors:
    """Payme API error codes."""
    # System errors
    SYSTEM_ERROR = -32400
    INVALID_JSON_RPC = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Authorization errors
    AUTH_ERROR = -32504
    AUTH_TOKEN_INVALID = -32504
    AUTH_TOKEN_EXPIRED = -32504

    # Business logic errors
    INVALID_AMOUNT = -31001
    INVALID_ACCOUNT = -31050
    COULD_NOT_PERFORM = -31008
    COULD_NOT_CANCEL = -31007
    TRANSACTION_NOT_FOUND = -31003
    TRANSACTION_ALREADY_EXISTS = -31060
    TRANSACTION_ALREADY_CANCELLED = -31061
    TRANSACTION_ALREADY_COMPLETED = -31062
