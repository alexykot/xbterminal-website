import logging

from website.models import Device
from api.utils.salt import Salt

logger = logging.getLogger(__name__)

MAIN_PACKAGES = [
    'python-core',
    'xserver-xorg',
    'python-pyqt',
    'python-qrcode',
    'python-requests',
    'bluez4',
    'python-pybluez',
    'python-dbus',
    'python-cryptography',
    'python-protobuf',
    'python-nfcpy',
    'python-tornado',
    'python-json-rpc',
    'zbar',
    'fswebcam',
    'gstreamer1.0',
    'salt-minion',
    'xbterminal-rpc',
    'xbterminal-gui',
]


def get_device_info(device_key):
    """
    Asynchronous task
    Retrieves system information from device using salt
    Accepts:
        device_key
    """
    device = Device.objects.get(key=device_key)
    salt = Salt()
    salt.login()
    try:
        versions = salt.get_pkg_versions(device.key, MAIN_PACKAGES)
    except AssertionError:
        logger.warning(
            'device is offline',
            extra={'data': {'device_key': device.key}})
    else:
        device.system_info = {'packages': versions}
        device.save()
        logger.info('device system info updated')
