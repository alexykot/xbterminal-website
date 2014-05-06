import re

from fabric.api import env, task, settings, prefix, local


def pip_version():
    if env.run == local:
        output = env.run("pip --version", capture=True)
    else:
        output = env.run("pip --version")
    m = re.search(r"pip\s(?P<version>[\d\.]+)\sfrom", output)
    return m.group("version")


@task
def venv():
    with settings(warn_only=True):
        result = env.run("test requirements.txt -ot venv/bin/activate")
    if result.failed:
        env.run("virtualenv -p /usr/bin/python2 venv")
        with prefix(". venv/bin/activate"):
            pip_install = "pip install -r requirements.txt --upgrade"
            if pip_version() > "1.4":
                pip_install += " --allow-all-external --allow-unverified pyPdf"
            env.run(pip_install)
        env.run("touch venv/bin/activate")


@task(default=True)
def all():
    venv()
