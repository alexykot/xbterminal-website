from django.utils import timezone
import rq
import django_rq


def run_periodic_task(func, args, interval=2):
    scheduler = django_rq.get_scheduler()
    scheduler.schedule(
        scheduled_time=timezone.now(),
        func=func,
        args=args,
        interval=interval,
        repeat=None,
        result_ttl=3600)


def cancel_current_task():
    django_rq.get_scheduler().cancel(rq.get_current_job())
