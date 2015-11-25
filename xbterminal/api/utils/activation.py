from website.models import Device
import django_rq


def prepare_device(device_key):
    """
    Asynchronous task
    Accepts:
        device_key
    """
    device = Device.objects.get(key=device_key)
    device.activate()
    device.save()


def start(device, merchant):
    device.merchant = merchant
    device.start_activation()
    device.save()
    django_rq.enqueue(prepare_device, device.key)
