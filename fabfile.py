from fabric.api import env, cd, run
from fabric.operations import put


env.hosts = ['web@151.248.122.78']

PROJECT_NAME = 'xbterminal'
BITBUCKET_PROJECT_URL = 'bitbucket.org/alexykot/xbterminal-website'

PIP = '~/envs/%s/bin/pip' % PROJECT_NAME
PYTHON = '~/envs/%s/bin/python' % PROJECT_NAME
PROJECT_DIR = '~/projects/%s' % PROJECT_NAME
MANAGE = '%s %s/%s/manage.py' % (PYTHON, PROJECT_DIR, PROJECT_NAME)
PID = '~/%s.pid' % PROJECT_NAME
GUNICORN_CONF = '%s/gunicorn.conf.py' % PROJECT_DIR
AVAILABLE_NGINX_PATH = '/etc/nginx/sites-available/%s' % PROJECT_NAME
ENABLED_NGINX_PATH = '/etc/nginx/sites-enabled/%s' % PROJECT_NAME



def install():
    run('mkdir -p envs projects')
    run('virtualenv --clear --no-site-packages ~/envs/%s' % PROJECT_NAME)
    run('%s install -U distribute' % PIP)
    run('hg clone https://Zamzaraev@%s %s' % (BITBUCKET_PROJECT_URL, PROJECT_DIR))

    update_env()
    run('mkdir -p logs/%s' % PROJECT_NAME)
    run('(crontab -l ; echo "* * * * * %s run_gunicorn -c %s") | uniq - | crontab -' %
        (MANAGE, GUNICORN_CONF))

def install_con():
    syncdb(migrate=False)
    collectstatic()

    put('gunicorn.conf.py', GUNICORN_CONF)
    add_to_nginx()

    start()


def deploy():
    update_project()
    update_env()
    syncdb(migrate=True)
    collectstatic()
    stop()
    start()


def update():
    update_project()
    syncdb(migrate=True)
    collectstatic()
    stop()
    start()


def start():
    with cd(PROJECT_DIR):
        run('%s run_gunicorn -c gunicorn.conf.py' % MANAGE, pty=False)


def restart():
    run('kill -HUP `cat %s`' % PID)


def stop():
    run('kill `cat %s`' % PID)


def update_project():
    with cd(PROJECT_DIR):
        run('hg pull')
        run('hg update -C')


def update_env():
    with cd(PROJECT_DIR):
        run('%s install -U -r requirements.txt' % PIP)


def collectstatic():
    with cd(PROJECT_DIR):
        run('%s collectstatic --noinput' % MANAGE)


def syncdb(migrate=False):
    with cd(PROJECT_DIR):
        if migrate:
            run('%s syncdb --migrate' % MANAGE)
        else:
            run('%s syncdb' % MANAGE)

def add_to_nginx():
    put('nginx', AVAILABLE_NGINX_PATH, use_sudo=True)
    #run('sudo ln -s %s %s' % (AVAILABLE_NGINX_PATH, ENABLED_NGINX_PATH))
    run('sudo service nginx reload')

def add_local():
    put('xbterminal/xbterminal/local_settings.py',
        '%s/%s/%s/local_settings.py' % (PROJECT_DIR, PROJECT_NAME, PROJECT_NAME),
        use_sudo=True)
