import logging

from transactions.services import (
    coinmarketcap,
    blockcypher,
    dashorg,
    sochain)

logger = logging.getLogger(__name__)


def get_exchange_rate(currency_name, coin_name):
    """
    Accepts:
        currency_code: currency name (fiat)
        coin_name: coin name (crypto)
    Returns:
        exchange_rate: Decimal
    """
    return coinmarketcap.get_exchange_rate(currency_name, coin_name)


def is_tx_reliable(tx_id, threshold, coin_name):
    """
    Accepts:
        tx_id: transaction hash
        threshold: minimal confidence factor, value between 0 and 1
        coin_name: coin name (currency name)
    Returns:
        boolean
    """
    if coin_name not in blockcypher.BLOCKCYPHER_CHAINS:
        # TODO: find confidence service for DASH
        return True
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


def get_tx_url(tx_id, coin_name):
    if coin_name in blockcypher.BLOCKCYPHER_CHAINS_LIVE:
        return blockcypher.get_tx_url(tx_id, coin_name)
    elif coin_name in dashorg.DASHORG_DOMAINS:
        return dashorg.get_tx_url(tx_id, coin_name)


def get_address_url(address, coin_name):
    if coin_name in blockcypher.BLOCKCYPHER_CHAINS_LIVE:
        return blockcypher.get_address_url(address, coin_name)
    elif coin_name in dashorg.DASHORG_DOMAINS:
        return dashorg.get_address_url(address, coin_name)
