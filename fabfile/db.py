from fabric.api import env, task, prefix


@task
def migrate():
    with prefix(". venv/bin/activate"):
        env.run("python xbterminal/manage.py syncdb --noinput")
        env.run("python xbterminal/manage.py migrate")
