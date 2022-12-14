import datetime
import logging
import time

from django.utils import timezone
from rq.job import Job, NoSuchJobError

from website.models import Device
from api.utils.salt import Salt
from api.utils.aptly import get_latest_version
from common import rq_helpers

CACHE_KEY_TEMPLATE = 'activation-{device_key}'
ACTIVATION_TIMEOUT = datetime.timedelta(minutes=30)

logger = logging.getLogger(__name__)


def start(device, merchant):
    device.merchant = merchant
    device.account = merchant.account_set.\
        filter(currency__is_fiat=False, currency__is_enabled=True).\
        first()
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
    logger.info('activation started (%s)', device.key)


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
    logger.info('device is online')
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


def wait_for_activation(device_key, activation_job_id):
    """
    Asynchronous task
    """
    device = Device.objects.get(key=device_key)
    if device.status == 'active':
        logger.info('activation finished (%s)', device.key)
        rq_helpers.cancel_current_task()
        return
    try:
        job = Job.fetch(activation_job_id)
    except NoSuchJobError as error:
        logger.exception(error)
        return
    if timezone.make_aware(job.started_at, timezone.utc) + \
            datetime.timedelta(seconds=job.timeout) < timezone.now():
        device.set_activation_error()
        device.save()
        logger.error('activation timeout (%s)', device.key)
        rq_helpers.cancel_current_task()
        return
    if job.is_failed:
        device.set_activation_error()
        device.save()
        logger.error('activation failed (%s)', device.key)
        rq_helpers.cancel_current_task()
        return
