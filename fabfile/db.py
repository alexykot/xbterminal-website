from fabric.api import env, task, prefix


@task
def migrate():
    with prefix(". venv/bin/activate"):
        env.run('python xbterminal/manage.py migrate oauth2_provider --fake')
        env.run('python xbterminal/manage.py migrate')
