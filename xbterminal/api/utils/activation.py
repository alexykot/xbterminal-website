import django_rq

from website.models import Device
from api.utils.salt import Salt


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
    if salt.ping(device.key):
        # Activate
        device.activate()
        device.save()


def start(device, merchant):
    device.merchant = merchant
    device.start_activation()
    device.save()
    django_rq.enqueue(prepare_device, device.key)
