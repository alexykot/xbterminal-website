from fabric.api import env, task, settings, prefix


@task
def venv():
    with settings(warn_only=True):
        result = env.run("test requirements.txt -ot venv/bin/activate")
    if result.failed:
        env.run("virtualenv venv")
        with prefix(". venv/bin/activate"):
            env.run("pip install -r requirements.txt --upgrade --allow-all-external --allow-unverified pyPdf")
        env.run("touch venv/bin/activate")


@task(default=True)
def all():
    venv()
