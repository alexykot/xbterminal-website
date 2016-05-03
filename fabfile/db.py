from fabric.api import env, task, prefix, sudo, cd

from utils import vagrant


@task
def migrate():
    with prefix(". venv/bin/activate"):
        env.run('python xbterminal/manage.py migrate')


@task
def restore():
    with vagrant(), cd('/vagrant/vagrant/backups'):
        sudo('pg_restore -U postgres -d xbt xbt.dump')
        sudo('service bitcoind stop')
        sudo('cp wallet.dat /var/lib/bitcoind/testnet3/wallet.dat')
        sudo('service bitcoind start')
