web: python xbterminal/manage.py runserver 0.0.0.0:8083
scheduler: python xbterminal/manage.py rqscheduler --queue high --interval=1
worker_low: python xbterminal/manage.py rqworker low
worker_high: python xbterminal/manage.py rqworker high
