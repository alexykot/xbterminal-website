import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Device
from website.utils import send_reconciliation


class Command(BaseCommand):

    def handle(self, *args, **options):
        now = timezone.localtime(timezone.now())
        for device in Device.objects.all():
            for item in device.rectime_set.all():  # Ordered by time
                rec_datetime = timezone.make_aware(
                    datetime.datetime.combine(now.date(), item.time),
                    timezone.utc)
                if device.last_reconciliation < rec_datetime <= now:
                    send_reconciliation(
                        item.email,
                        device,
                        (device.last_reconciliation, rec_datetime))
                    device.last_reconciliation = rec_datetime
                    device.save()
