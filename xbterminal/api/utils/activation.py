import time
import django_rq

from website.models import Device
from api.utils.salt import Salt
from api.utils.aptly import get_latest_xbtfw_version


def start(device, merchant):
    device.merchant = merchant
    device.start_activation()
    device.save()
    django_rq.enqueue(prepare_device, device.key)


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
