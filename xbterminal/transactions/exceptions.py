class TransactionError(Exception):

    message = 'Transaction error'

    def __init__(self, message=None):
        super(TransactionError, self).__init__()
        if message:
            self.message = message

    def __str__(self):
        return self.message


class DustOutput(TransactionError):

    message = 'Output is below dust threshold'


class InvalidTransaction(TransactionError):

    message = 'Invalid transaction'

    def __init__(self, tx_id):
        super(InvalidTransaction, self).__init__()
        self.tx_id = tx_id


class InsufficientFunds(TransactionError):

    message = 'Insufficient funds'


class InvalidPaymentMessage(TransactionError):

    message = 'Invalid BIP0070 Payment message'


class RefundError(TransactionError):

    message = 'Refund error'


class DoubleSpend(TransactionError):

    message = 'Double spend detected'

    def __init__(self, another_tx_id):
        super(DoubleSpend, self).__init__()
        self.another_tx_id = another_tx_id


class TransactionModified(TransactionError):

    message = 'Transaction modified'

    def __init__(self, another_tx_id):
        super(TransactionModified, self).__init__()
        self.another_tx_id = another_tx_id
