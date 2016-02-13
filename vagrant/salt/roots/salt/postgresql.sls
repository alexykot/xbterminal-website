postgresql-repo:
  pkgrepo.managed:
    - name: deb http://apt.postgresql.org/pub/repos/apt/ trusty-pgdg main
    - file: /etc/apt/sources.list.d/pgdg.list
    - key_url: https://www.postgresql.org/media/keys/ACCC4CF8.asc

postgresql:
  pkg:
    - installed
    - pkgs:
      - postgresql-9.4
    - require:
      - pkgrepo: postgresql-repo
  service.running:
    - watch:
      - file: /etc/postgresql/9.4/main/postgresql.conf
      - file: /etc/postgresql/9.4/main/pg_hba.conf
    - require:
      - pkg: postgresql

xbt-user:
  postgres_user.present:
    - name: {{ pillar['postgresql']['user'] }}
    - createdb: {{ pillar['postgresql']['createdb'] }}
    - password: {{ pillar['postgresql']['password'] }}
    - require:
      - service: postgresql

xbt-database:
  postgres_database.present:
    - name: {{ pillar['postgresql']['database'] }}
    - encoding: UTF8
    - lc_ctype: en_US.UTF8
    - lc_collate: en_US.UTF8
    - template: template0
    - owner: {{ pillar['postgresql']['user'] }}
    - require:
      - postgres_user: xbt-user

postgresql.conf:
  file.managed:
    - name: /etc/postgresql/9.4/main/postgresql.conf
    - source: salt://postgresql/postgresql.conf
    - user: postgres
    - group: postgres
    - mode: 644
    - require:
      - pkg: postgresql

pg_hba.conf:
  file.managed:
    - name: /etc/postgresql/9.4/main/pg_hba.conf
    - source: salt://postgresql/pg_hba.conf
    - user: postgres
    - group: postgres
    - mode: 644
    - require:
      - pkg: postgresql
