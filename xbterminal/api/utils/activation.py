import time

from django.core.cache import cache
import django_rq
from rq.job import Job

from website.models import Device
from api.utils.salt import Salt
from api.utils.aptly import get_latest_xbtfw_version
from operations.rq_helpers import run_periodic_task, cancel_current_task


CACHE_KEY_TEMPLATE = 'activation-{device_key}'


def start(device, merchant):
    device.merchant = merchant
    device.start_activation()
    device.save()
    job = django_rq.enqueue(prepare_device, device.key)
    run_periodic_task(wait_for_activation, [device.key, job.get_id()])


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
    assert activation_status in ['in progress', 'error']
    cache_key = CACHE_KEY_TEMPLATE.format(device_key=device.key)
    cache.set(cache_key, activation_status, timeout=None)


def get_status(device):
    """
    Get activation status from cache
    """
    assert device.status == 'activation'
    cache_key = CACHE_KEY_TEMPLATE.format(device_key=device.key)
    return cache.get(cache_key, 'in progress')


def wait_for_activation(device_key, activation_job_id):
    """
    Asynchronous task
    """
    device = Device.objects.get(key=device_key)
    if device.status != 'activation':
        # Activation finished
        cancel_current_task()
        return
    job = Job.fetch(activation_job_id)
    if job.is_failed:
        # Activation failed
        set_status(device, 'error')
        cancel_current_task()
