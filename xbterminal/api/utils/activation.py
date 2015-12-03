import logging
import time

from django.core.cache import cache
from rq.job import Job

from website.models import Device
from api.utils.salt import Salt
from api.utils.aptly import get_latest_xbtfw_version
from operations import rq_helpers

CACHE_KEY_TEMPLATE = 'activation-{device_key}'

logger = logging.getLogger(__name__)


def start(device, merchant):
    device.merchant = merchant
    device.start_activation()
    device.save()
    job = rq_helpers.run_task(prepare_device, [device.key], queue='low')
    rq_helpers.run_periodic_task(wait_for_activation,
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
    while not salt.ping(device.key):
        time.sleep(5)
    # Upgrade xbterminal-firmware package
    xbtfw_version = get_latest_xbtfw_version()
    salt.upgrade(device.key, xbtfw_version)
    # Reboot device
    salt.reboot(device.key)
    # Activate
    device.activate()
    device.save()


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
    if job.is_failed:
        set_status(device, 'error')
        logger.info('activation failed ({})'.format(device.key))
        rq_helpers.cancel_current_task()
