from django.utils import timezone
from raven.contrib.django.raven_compat.models import client
import rq
import django_rq

RESULT_TTL = 3600


def run_task(func, args, queue='high', timeout=None, time_delta=None):
    if time_delta:
        # Use scheduler
        scheduler = django_rq.get_scheduler(queue)
        scheduler.enqueue_in(
            time_delta,
            func,
            timeout=timeout,
            *args)
    else:
        queue_ = django_rq.get_queue(queue)
        return queue_.enqueue_call(
            func,
            args,
            timeout=timeout,
            result_ttl=RESULT_TTL)


def run_periodic_task(func, args, queue='high', interval=2, timeout=None):
    scheduler = django_rq.get_scheduler(queue)
    scheduler.schedule(
        scheduled_time=timezone.now(),
        func=func,
        args=args,
        interval=interval,
        repeat=None,
        result_ttl=RESULT_TTL,
        timeout=timeout)


def cancel_current_task(queue='high'):
    job = rq.get_current_job()
    django_rq.get_scheduler(queue).cancel(job)


def sentry_exc_handler(job, *exc_info):
    client.captureException(exc_info=exc_info)
    django_rq.get_scheduler(job.origin).cancel(job)
