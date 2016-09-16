from fabric.api import env, task, settings, prefix, local, lcd


@task
def dirs():
    env.run("mkdir -p logs")


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
def bower():
    local('bower install')
    libs = [
        'bower_components/jquery/dist/jquery.min.js',
        'bower_components/jquery-qrcode/dist/jquery-qrcode.min.js',
        'bower_components/bootstrap/dist/css/bootstrap.min.css',
        'bower_components/bootstrap/dist/js/bootstrap.min.js',
        'bower_components/jquery.cookie/jquery.cookie.js',
        'bower_components/blueimp-file-upload/js/jquery.fileupload.js',
        'bower_components/blueimp-file-upload/js/jquery.iframe-transport.js',
        'bower_components/blueimp-file-upload/js/vendor/jquery.ui.widget.js',
        'bower_components/jquery-validation/dist/jquery.validate.min.js',
        'bower_components/skrollr/dist/skrollr.min.js',
        'bower_components/bootstrap-datepicker/dist/css/bootstrap-datepicker3.min.css',
        'bower_components/bootstrap-datepicker/dist/js/bootstrap-datepicker.min.js',
    ]
    for file_name in libs:
        local('cp {} xbterminal/website/static/lib/'.format(file_name))
    fonts = [
        'bower_components/bootstrap/dist/fonts/*',
    ]
    for file_name in fonts:
        local('cp {} xbterminal/website/static/fonts/'.format(file_name))


@task
def clean():
    env.run("find . -name '*.pyc' -delete")


@task(default=True)
def all(development='yes'):
    dirs()
    venv(development=development)
    compilemessages()
