from fabric.api import task, prefix, local, settings, hide, abort


@task
def style():
    with prefix('. venv/bin/activate'):
        local('flake8 fabfile')
        local('flake8 '
              '--exclude=migrations,paymentrequest_pb2.py '
              '--max-line-length=125 '
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


@task
def migrations():
    with prefix('. venv/bin/activate'):
        with settings(hide('output'), warn_only=True):
            result = local(
                'python xbterminal/manage.py makemigrations --dry-run',
                capture=True)
    if result and "Migrations for '" in result:
        abort('New migrations detected')


@task(default=True)
def all():
    style()
    security()
    unit()
    migrations()
