from fabric.api import env, task, settings, prefix, local, lcd


@task
def dirs():
    env.run("mkdir -p logs")
    env.run("mkdir -p reports")
    env.run("chmod -R a+w reports")
    env.run("mkdir -p media")
    env.run("chmod -R a+w media")


@task
def venv(development='yes'):
    with settings(warn_only=True):
        test_command = 'test requirements.txt -ot venv/bin/activate'
        if development == 'yes':
            test_command += ' -a requirements_dev.txt -ot venv/bin/activate'
        result = env.run(test_command)
    if result.failed:
        env.run('virtualenv -p /usr/bin/python2 venv')
        with prefix('. venv/bin/activate'):
            if development == 'yes':
                env.run('pip install -r requirements_dev.txt --upgrade')
            else:
                env.run('pip install pip==7.1.2')
                env.run('pip install -r requirements.txt --upgrade')
        env.run('touch venv/bin/activate')


@task
def proto():
    with lcd("xbterminal/operations"):
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


@task
def clean():
    env.run("find . -name '*.pyc' -delete")


@task(default=True)
def all(development='yes'):
    dirs()
    venv(development=development)
    compilemessages()
