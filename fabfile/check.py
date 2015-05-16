from fabric.api import task, prefix, local


@task
def python():
    with prefix('. venv/bin/activate'):
        local('flake8 --max-line-length=140 fabfile')
        local('flake8 '
              '--exclude=migrations,paymentrequest_pb2.py '
              '--max-line-length=140 '
              '--ignore=E124,E221,F401,F841 '
              'xbterminal')


@task(default=True)
def all():
    python()
