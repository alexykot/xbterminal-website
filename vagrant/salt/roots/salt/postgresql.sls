postgresql_repo:
  pkgrepo.managed:
    - name: deb http://apt.postgresql.org/pub/repos/apt/ xenial-pgdg main
    - file: /etc/apt/sources.list.d/pgdg.list
    - key_url: https://www.postgresql.org/media/keys/ACCC4CF8.asc

postgresql_package:
  pkg:
    - installed
    - name: postgresql-9.4
    - require:
      - pkgrepo: postgresql_repo

postgresql_config:
  file.managed:
    - name: /etc/postgresql/9.4/main/postgresql.conf
    - source: salt://postgresql/postgresql.conf
    - user: postgres
    - group: postgres
    - mode: 644
    - require:
      - pkg: postgresql_package

postgresql_hba_config:
  file.managed:
    - name: /etc/postgresql/9.4/main/pg_hba.conf
    - source: salt://postgresql/pg_hba.conf
    - user: postgres
    - group: postgres
    - mode: 644
    - require:
      - pkg: postgresql_package

postgresql_service:
  service:
    - running
    - name: postgresql
    - enable: true
    - watch:
      - file: postgresql_config
      - file: postgresql_hba_config
    - require:
      - pkg: postgresql_package
