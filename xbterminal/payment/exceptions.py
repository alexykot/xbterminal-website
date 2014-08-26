class NetworkError(Exception):
    pass


class InvalidTransaction(Exception):
    pass


class PaymentError(Exception):

    def __init__(self, message):
        super(PaymentError, self).__init__()
        self.message = message

    def __str__(self):
        return "{0}: {1}".format(self.__class__.__name__, self.message)


class InstantFiatError(PaymentError):
    pass


class InvalidPayment(PaymentError):
    pass
