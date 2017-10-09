import logging

from transactions.services import coindesk, btcaverage, blockcypher, sochain

logger = logging.getLogger(__name__)


def get_exchange_rate(currency_name):
    """
    Accepts:
        currency_code: 3-letter code
    Returns:
        exchange_rate: Decimal
    """
    try:
        return coindesk.get_exchange_rate(currency_name)
    except Exception as error:
        logger.exception(error)
        return btcaverage.get_exchange_rate(currency_name)


def is_tx_reliable(tx_id, threshold, coin_name):
    """
    Accepts:
        tx_id: transaction hash
        threshold: minimal confidence factor, value between 0 and 1
        coin_name: coin name (currency name)
    Returns:
        boolean
    """
    try:
        confidence = blockcypher.get_tx_confidence(tx_id, coin_name)
    except Exception as error:
        # Error when accessing blockcypher API
        logger.exception(error)
        try:
            confidence = sochain.get_tx_confidence(tx_id, coin_name)
        except Exception as error:
            logger.exception(error)
            # Services are not available, consider transaction as unreliable
            return False
    if confidence >= threshold:
        return True
    else:
        return False
