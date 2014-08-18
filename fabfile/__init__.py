from fabric.api import env, local, lcd

import build
import db
try:
    import deploy
except ImportError:
    pass

env.use_ssh_config = True
env.run = local
env.cd = lcd
