class PaymentError(Exception):

    message = "Payment error"

    def __init__(self, message=None):
        super(PaymentError, self).__init__()
        if message:
            self.message = message

    def __str__(self):
        return self.message


class NetworkError(PaymentError):

    message = "Bitcoind error"


class InstantFiatError(PaymentError):

    message = "InstantFiat service error"


class InvalidTransaction(PaymentError):

    message = "Invalid transaction"

    def __init__(self, transaction_id):
        super(InvalidTransaction, self).__init__()
        self.message = "{0} {1}".format(self.message, transaction_id)


class InsufficientFunds(PaymentError):

    message = "Insufficient funds"


class InvalidPaymentMessage(PaymentError):

    message = "Invalid BIP0070 Payment message"
