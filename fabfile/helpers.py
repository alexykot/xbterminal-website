from contextlib import contextmanager

from fabric.api import env, local, run, sudo


@contextmanager
def remotely(use_sudo=False):
    env.run = sudo if use_sudo else run
    yield
    env.run = local
