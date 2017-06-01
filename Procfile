web: python xbterminal/manage.py runserver 0.0.0.0:8083
scheduler: python xbterminal/manage.py rqscheduler --queue high --interval=1
worker_low: python xbterminal/manage.py rqworker low --worker-class rq.SimpleWorker
worker_high: python xbterminal/manage.py rqworker high --worker-class rq.SimpleWorker
