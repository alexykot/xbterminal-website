required-pkgs:
  pkg.installed:
    - names:
      - python-virtualenv
      - python-dev
      - libpq-dev
      - libffi-dev
      - libjpeg-dev

/home/vagrant/venv:
  virtualenv.managed:
    - requirements: /vagrant/requirements_dev.txt
    - no_chown: true
    - user: vagrant
    - python: /usr/bin/python2
    - system_site_packages: false
    - require:
      - pkg: required-pkgs
