import re

from fabric.api import env, task, settings, prefix, local, lcd


@task
def dirs():
    env.run("mkdir -p logs")
    env.run("mkdir -p firmware")
    env.run("mkdir -p reports")
    env.run("chmod -R a+w reports")
    env.run("mkdir -p media")
    env.run("chmod -R a+w media")


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


@task
def proto():
    with lcd("xbterminal/payment"):
        local("wget -O paymentrequest.proto "
              "https://raw.githubusercontent.com"
              "/bitcoin/bips/master/bip-0070/paymentrequest.proto")
        local("protoc --python_out . "
              "paymentrequest.proto")


@task
def makemessages():
    with lcd("xbterminal"):
        with prefix(". ../venv/bin/activate"):
            local("django-admin.py makemessages -a")
            local("django-admin.py makemessages -d djangojs -a")


@task
def compilemessages():
    with env.cd("xbterminal"):
        with prefix(". ../venv/bin/activate"):
            env.run("django-admin.py compilemessages")


@task(default=True)
def all():
    dirs()
    venv()
    compilemessages()
