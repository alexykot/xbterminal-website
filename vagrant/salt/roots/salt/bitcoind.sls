bitcoin_ppa:
  pkgrepo.managed:
    - ppa: bitcoin/bitcoin
    - refresh_db: true

bitcoind_package:
  pkg.latest:
    - name: bitcoind
    - require:
      - pkgrepo: bitcoin_ppa

bitcoin_group:
  group:
    - present
    - name: bitcoin

bitcoin_user:
  user:
    - present
    - name: bitcoin
    - shell: /bin/bash
    - home: /var/lib/bitcoind
    - groups:
      - bitcoin
    - require:
      - group: bitcoin_group

bitcoin_config_dir:
  file.directory:
    - name: /etc/bitcoin
    - user: bitcoin
    - group: bitcoin
    - require:
      - user: bitcoin_user

bitcoin_config:
  file.managed:
    - name: /etc/bitcoin/bitcoin.conf
    - source: salt://bitcoind/bitcoin.conf
    - template: jinja
    - context:
      rpc_user: {{ pillar['bitcoind']['user'] }}
      rpc_password: {{ pillar['bitcoind']['password'] }}
    - user: bitcoin
    - group: bitcoin
    - mode: 660
    - require:
      - file: bitcoin_config_dir
      - user: bitcoin_user

bitcoind_service_file:
  file.managed:
    - name: /lib/systemd/system/bitcoind.service
    - source: salt://bitcoind/bitcoind.service
    - require:
      - pkg: bitcoind_package

bitcoind_service:
  service:
    - running
    - name: bitcoind
    - enable: true
    - require:
      - pkg: bitcoind_package
      - file: bitcoind_service_file
      - file: bitcoin_config
    - watch:
      - pkg: bitcoind_package
      - file: bitcoin_config
