# -*- coding: utf-8 -*-
from fabric.api import *

def pack():
  local("tar -czf /tmp/xbterminal.tgz --exclude .hg .")
