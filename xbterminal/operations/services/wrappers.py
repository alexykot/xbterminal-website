import logging

from operations.services import coindesk, btcaverage, blockcypher, sochain

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


def is_tx_reliable(tx_id, network):
    """
    Accepts:
        tx_id: transaction hash
        network: mainnet or testnet
    Returns:
        boolean
    """
    try:
        return blockcypher.is_tx_reliable(tx_id, network)
    except Exception as error:
        # Error when accessing blockcypher API
        logger.exception(error)
        return sochain.is_tx_reliable(tx_id, network)
