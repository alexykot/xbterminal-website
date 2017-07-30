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
