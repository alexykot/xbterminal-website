from fabric.api import task, prefix, local


@task
def style():
    with prefix('. venv/bin/activate'):
        local('flake8 fabfile')
        local('flake8 '
              '--exclude=migrations,paymentrequest_pb2.py '
              '--max-line-length=140 '
              'xbterminal')


@task
def security():
    with prefix('. venv/bin/activate'):
        local('bandit -r -c .bandit -x tests xbterminal')


@task
def unit(target='website operations api transactions wallet'):
    with prefix('. venv/bin/activate'):
        local('coverage run '
              'xbterminal/manage.py test {}'.format(target))
        local('coverage report -i')


@task(default=True)
def all():
    style()
    security()
    unit()
