# -*- coding: utf-8 -*-
from fabric.api import *

env.hosts = ['root@devlab.su']

def pack():
  local("tar -czf /tmp/xbterminal.tgz --exclude .hg .")

def copy():
  local('tar -C xbterminal -czf /tmp/xbterminal.tgz --exclude .hg .')
  put('/tmp/xbterminal.tgz','/home')
  with cd('/home'):
    run('tar -xzf /home/xbterminal.tgz -C /home/xbterminal')

def deploy():
  local('tar -C xbterminal -czf /tmp/xbterminal.tgz --exclude .hg .')
  put('/tmp/xbterminal.tgz','/home')
  with cd('/home'):
    run('service nginx stop')
    run('service uwsgi stop')
    run('rm -RIf /home/xbterminal')
    run('mkdir /home/xbterminal')
    run('tar -xzf /home/xbterminal.tgz -C /home/xbterminal')
    run('mkdir /home/xbterminal/venv')
    with cd('/home/xbterminal'):
      with cd('/home/xbterminal/venv'):
        run('virtualenv --no-site-packages xbterminal')
      with prefix('source ./venv/xbterminal/bin/activate'):
        run('pip install -r req.txt')
    run('cp /home/xbterminal/config/xbterminal /etc/nginx/sites-enabled')
    run('cp /home/xbterminal/config/xbterminal.ini /etc/uwsgi/apps-enabled')
    run('chgrp -R www-data /home/xbterminal')
    run('chown -R www-data /home/xbterminal')
    run('service uwsgi start')
    run('service nginx start')
