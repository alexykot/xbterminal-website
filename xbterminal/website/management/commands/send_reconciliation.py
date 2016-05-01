import datetime
import itertools

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Device
from website.utils.reconciliation import send_reconciliation


class Command(BaseCommand):

    help = 'Send reconciliation emails'

    def handle(self, *args, **options):
        now = timezone.localtime(timezone.now())
        for device in Device.objects.all():
            items = device.rectime_set.all()  # Ordered by time
            for rec_time, group in itertools.groupby(items,
                                                     lambda i: i.time):
                rec_datetime = timezone.make_aware(
                    datetime.datetime.combine(now.date(), rec_time),
                    timezone.get_current_timezone())
                if device.last_reconciliation < rec_datetime <= now:
                    # All emails in a group should be sent at the same time
                    for item in group:
                        send_reconciliation(
                            item.email,
                            device,
                            (device.last_reconciliation, rec_datetime))
                    device.last_reconciliation = rec_datetime
                    device.save()
