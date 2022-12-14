from contextlib import contextmanager

from fabric.api import env, local, run, sudo, lcd, cd, settings


@contextmanager
def remotely(use_sudo=False):
    env.run = sudo if use_sudo else run
    env.cd = cd
    yield
    env.run = local
    env.cd = lcd


@contextmanager
def vagrant():
    local('vagrant up')

    # Parse SSH config
    ssh_config_str = local('vagrant ssh-config', capture=True)
    ssh_config = {}
    for line in ssh_config_str.splitlines():
        key, value = line.strip().split()
        ssh_config[key] = value
    host_string = '{0}@{1}:{2}'.format(
        ssh_config['User'],
        ssh_config['HostName'],
        ssh_config['Port'])

    with settings(host_string=host_string,
                  key_filename=ssh_config['IdentityFile'].strip('"'),
                  disable_known_hosts=True):
        yield
