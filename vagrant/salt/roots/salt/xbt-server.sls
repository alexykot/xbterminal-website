xbt_required_pkgs:
  pkg.installed:
    - names:
      - python-virtualenv
      - python-dev
      - libpq-dev
      - libffi-dev
      - libjpeg-dev

xbt_pg_user:
  postgres_user.present:
    - name: {{ pillar['postgresql']['user'] }}
    - createdb: {{ pillar['postgresql']['createdb'] }}
    - password: {{ pillar['postgresql']['password'] }}
    - require:
      - service: postgresql

xbt_pg_database:
  postgres_database.present:
    - name: {{ pillar['postgresql']['database'] }}
    - encoding: UTF8
    - lc_ctype: en_US.UTF8
    - lc_collate: en_US.UTF8
    - template: template0
    - owner: {{ pillar['postgresql']['user'] }}
    - require:
      - postgres_user: xbt_pg_user

/home/vagrant/venv:
  virtualenv.managed:
    - requirements: /vagrant/requirements_dev.txt
    - no_chown: true
    - user: vagrant
    - python: /usr/bin/python2
    - system_site_packages: false
    - require:
      - pkg: xbt_required_pkgs
      - postgres_database: xbt_pg_database
