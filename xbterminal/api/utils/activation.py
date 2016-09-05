import datetime
import logging
import time

from django.core.cache import cache
from django.utils import timezone
from rq.job import Job

from website.models import Account, Device
from api.utils.salt import Salt
from api.utils.aptly import get_latest_version
from operations import rq_helpers

CACHE_KEY_TEMPLATE = 'activation-{device_key}'
ACTIVATION_TIMEOUT = datetime.timedelta(minutes=30)

logger = logging.getLogger(__name__)


def start(device, merchant):
    device.merchant = merchant
    try:
        device.account = merchant.account_set.get(currency=merchant.currency)
    except Account.DoesNotExist:
        device.account = merchant.account_set.get(currency__name='BTC')
    device.start_activation()
    device.save()
    activation_job_timeout = int(ACTIVATION_TIMEOUT.total_seconds()) + 600
    job = rq_helpers.run_task(
        prepare_device,
        [device.key],
        queue='low',
        timeout=activation_job_timeout)
    rq_helpers.run_periodic_task(
        wait_for_activation,
        [device.key, job.get_id()])
    logger.info('activation started ({})'.format(device.key))


def prepare_device(device_key):
    """
    Asynchronous task
    Accepts:
        device_key
    """
    device = Device.objects.get(key=device_key)
    # Accept minion's key
    salt = Salt()
    salt.login()
    salt.accept(device.key)
    # Wait for device
    ping_interval = 10
    while not salt.ping(device.key):
        logger.info('device is offline, waiting {} seconds'.format(
            ping_interval))
        time.sleep(ping_interval)
    # Collect information
    machine = salt.get_grain(device.key, 'machine')
    rpc_package_version = get_latest_version(machine, 'xbterminal-rpc')
    gui_package_version = get_latest_version(machine, 'xbterminal-gui')
    pillar_data = {
        'xbt': {
            'rpc_version': rpc_package_version,
            'gui_version': gui_package_version,
            'rpc_config': {},
            'gui_config': {},
        },
    }
    ui_theme = device.merchant.ui_theme.name
    ui_theme_package_version = get_latest_version(
        machine,
        'xbterminal-gui-theme-{}'.format(ui_theme))
    pillar_data['xbt']['themes'] = {
        ui_theme: ui_theme_package_version,
    }
    pillar_data['xbt']['gui_config']['theme'] = ui_theme
    # Apply state
    salt.highstate(device.key,
                   pillar_data,
                   int(ACTIVATION_TIMEOUT.total_seconds()))


def set_status(device, activation_status):
    """
    Save activation status to cache
    """
    assert device.status == 'activation'
    assert activation_status in ['in_progress', 'error']
    cache_key = CACHE_KEY_TEMPLATE.format(device_key=device.key)
    cache.set(cache_key, activation_status, timeout=None)


def get_status(device):
    """
    Get activation status from cache
    """
    assert device.status == 'activation'
    cache_key = CACHE_KEY_TEMPLATE.format(device_key=device.key)
    return cache.get(cache_key, 'in_progress')


def wait_for_activation(device_key, activation_job_id):
    """
    Asynchronous task
    """
    device = Device.objects.get(key=device_key)
    if device.status != 'activation':
        logger.info('activation finished ({})'.format(device.key))
        rq_helpers.cancel_current_task()
        return
    job = Job.fetch(activation_job_id)
    if timezone.make_aware(job.started_at, timezone.utc) + \
            datetime.timedelta(seconds=job.timeout) < timezone.now():
        set_status(device, 'error')
        logger.error('activation timeout ({})'.format(device.key))
        rq_helpers.cancel_current_task()
        return
    if job.is_failed:
        set_status(device, 'error')
        logger.error('activation failed ({})'.format(device.key))
        rq_helpers.cancel_current_task()
        return
