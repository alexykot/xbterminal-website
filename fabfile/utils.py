from contextlib import contextmanager

from fabric.api import env, local, run, sudo, lcd, cd


@contextmanager
def remotely(use_sudo=False):
    env.run = sudo if use_sudo else run
    env.cd = cd
    yield
    env.run = local
    env.cd = lcd
