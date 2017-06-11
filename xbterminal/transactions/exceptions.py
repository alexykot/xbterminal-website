class TransactionError(Exception):
    pass


class InsufficientFundsError(TransactionError):
    pass
