import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Device
from website.utils import send_reconciliation


class Command(BaseCommand):

    def handle(self, *args, **options):
        now = timezone.now()
        for device in Device.objects.all():
            for item in device.rectime_set.filter(
                time__range=(device.last_reconciliation.time(), now.time())):                
                rec_range = (
                    device.last_reconciliation,
                    timezone.make_aware(
                        datetime.datetime.combine(now.date(), item.time),
                        timezone.utc)
                )
                send_reconciliation(item.email, device, rec_range)
                device.last_reconciliation = rec_range[1]
                device.save()
