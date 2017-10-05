dash_source:
  archive.extracted:
    - name: /opt/
    - source: https://www.dash.org/binaries/dashcore-0.12.1.5-linux64.tar.gz
    - source_hash: https://github.com/dashpay/dash/releases/download/v0.12.1.5/SHA256SUMS.asc

{% set extracted_path = '/opt/dashcore-0.12.1' %}

dash_group:
  group.present:
    - name: dash

dash_user:
  user.present:
    - name: dash
    - shell: /bin/bash
    - home: /var/lib/dashd
    - groups:
      - dash
    - require:
      - group: dash_group

dash_daemon_bin:
  file.copy:
    - name: /usr/bin/dashd
    - source: {{ extracted_path }}/bin/dashd

dash_cli_bin:
  file.copy:
    - name: /usr/bin/dash-cli
    - source: {{ extracted_path }}/bin/dash-cli

dash_config_dir:
  file.directory:
    - name: /etc/dashd
    - user: dash
    - group: dash
    - require:
      - user: dash_user

dash_config:
  file.managed:
    - name: /etc/dashd/dash.conf
    - source: salt://dashd/dash.conf
    - template: jinja
    - context:
      rpc_user: {{ pillar['dashd']['user'] }}
      rpc_password: {{ pillar['dashd']['password'] }}
    - user: dash
    - group: dash
    - mode: 660
    - require:
      - file: dash_config_dir
      - user: dash_user

dashd_service_file:
  file.managed:
    - name: /lib/systemd/system/dashd.service
    - source: salt://dashd/dashd.service
    - require:
      - user: dash_user
      - file: dash_daemon_bin
      - file: dash_cli_bin
      - file: dash_config

dashd_service:
  service.running:
    - name: dashd
    - enable: true
    - require:
      - file: dashd_service_file
      - file: dash_config
    - watch:
      - file: dash_daemon_bin
      - file: dash_config
