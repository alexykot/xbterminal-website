from fabric.api import task, prefix, local


@task
def python():
    with prefix('. venv/bin/activate'):
        local('flake8 --max-line-length=140 fabfile')
        local('flake8 '
              '--exclude=migrations,paymentrequest_pb2.py '
              '--max-line-length=140 '
              '--ignore=E111,E124,E126,E127,E128,E203,E221,E222,E302,E401,F401,F403,F841 '
              'xbterminal')


@task(default=True)
def all():
    python()
