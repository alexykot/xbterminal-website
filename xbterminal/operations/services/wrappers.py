import logging

from operations.services import coindesk, btcaverage

logger = logging.getLogger(__name__)


def get_exchange_rate(currency_code):
    """
    Accepts:
        currency_code: 3-letter code
    Returns:
        exchange_rate: Decimal
    """
    try:
        return coindesk.get_exchange_rate(currency_code)
    except Exception as error:
        logger.exception(error)
        return btcaverage.get_exchange_rate(currency_code)
