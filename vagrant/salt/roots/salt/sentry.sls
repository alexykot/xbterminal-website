sentry_required_pkgs:
  pkg.installed:
    - names:
      - build-essential
      - python-virtualenv
      - python-dev
      - libpq-dev
      - libxml2-dev
      - libxslt1-dev
      - libffi-dev
      - libssl-dev
      - libjpeg-dev

sentry_group:
  group.present:
    - name: sentry

sentry_user:
  user.present:
    - name: sentry
    - shell: /bin/bash
    - home: /var/lib/sentry
    - groups:
      - sentry
    - require:
      - group: sentry_group

sentry_pg_user:
  postgres_user.present:
    - name: sentry
    - password: sentry
    - require:
      - service: postgresql_service

sentry_pg_database:
  postgres_database.present:
    - name: sentry
    - owner: sentry
    - require:
      - postgres_user: sentry_pg_user

/var/lib/sentry/venv:
  virtualenv.managed:
    - requirements: salt://sentry/requirements.txt
    - user: sentry
    - python: /usr/bin/python2
    - require:
      - pkg: sentry_required_pkgs
      - user: sentry_user

/etc/sentry:
  file.directory:
    - name: /etc/sentry
    - user: sentry
    - group: sentry
    - require:
      - user: sentry_user
      - group: sentry_group

/etc/sentry/sentry.conf.py:
  file.managed:
    - source: salt://sentry/sentry.conf.py
    - user: sentry
    - group: sentry
    - require:
      - file: /etc/sentry

/etc/sentry/config.yml:
  file.managed:
    - source: salt://sentry/config.yml
    - template: jinja
    - context:
      smtp_host: {{ pillar['sentry']['smtp_host'] }}
      smtp_port: {{ pillar['sentry']['smtp_port'] }}
      smtp_user: {{ pillar['sentry']['smtp_user'] }}
      smtp_password: {{ pillar['sentry']['smtp_password'] }}
    - user: sentry
    - group: sentry
    - require:
      - file: /etc/sentry

sentry_db_upgrade:
   cmd.script:
    - source: salt://sentry/sentry_upgrade.sh
    - runas: sentry
    - env:
      - SENTRY_CONF: /etc/sentry
    - require:
      - virtualenv: /var/lib/sentry/venv
      - file: /etc/sentry/sentry.conf.py
      - file: /etc/sentry/config.yml
      - postgres_database: sentry_pg_database

/lib/systemd/system/sentry-worker.service:
  file.managed:
    - source: salt://sentry/sentry-worker.service

/lib/systemd/system/sentry-scheduler.service:
  file.managed:
    - source: salt://sentry/sentry-scheduler.service

/lib/systemd/system/sentry-web.service:
  file.managed:
    - source: salt://sentry/sentry-web.service

sentry_web_service:
  service.running:
    - name: sentry-web
    - enable: true
    - require:
      - file: /lib/systemd/system/sentry-web.service
      - cmd: sentry_db_upgrade
    - watch:
      - virtualenv: /var/lib/sentry/venv
      - file: /etc/sentry/config.yml
      - cmd: sentry_db_upgrade

sentry_worker_service:
  service.running:
    - name: sentry-worker
    - enable: true
    - require:
      - file: /lib/systemd/system/sentry-worker.service
    - watch:
      - service: sentry_web_service

sentry_scheduler_service:
  service.running:
    - name: sentry-scheduler
    - enable: true
    - require:
      - file: /lib/systemd/system/sentry-scheduler.service
    - watch:
      - service: sentry_web_service
