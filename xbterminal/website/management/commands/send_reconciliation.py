from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import Device
from website.utils import send_reconciliation


class Command(BaseCommand):

    def handle(self, *args, **options):
        PERIOD_MINUTES = 5  # must comply with cron period
        minutes = PERIOD_MINUTES + 1  # stock
        now = timezone.now()
        date = (now - timedelta(1)).date()

        for device in Device.objects.filter(time__gt=(now - timedelta(minutes=minutes)).time(),
                                            time__lte=now.time()
                                            ).exclude(date=date):
            send_reconciliation(device.email, device, date)
            device.date = date
            device.save()
