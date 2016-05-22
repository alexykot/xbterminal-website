bitcoin_ppa:
  pkgrepo.managed:
    - ppa: bitcoin/bitcoin
    - refresh_db: true

bitcoind:
  pkg:
    - installed
    - require:
      - pkgrepo: bitcoin_ppa
  service:
    - running
    - require:
      - pkg: bitcoind
      - file: /lib/systemd/system/bitcoind.service
      - file: /etc/bitcoin/bitcoin.conf

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

/etc/bitcoin:
  file.directory:
    - name: /etc/bitcoin
    - user: bitcoin
    - group: bitcoin
    - require:
      - user: bitcoin_user

/etc/bitcoin/bitcoin.conf:
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
      - file: /etc/bitcoin
      - user: bitcoin_user

/lib/systemd/system/bitcoind.service:
  file.managed:
    - source: salt://bitcoind/bitcoind.service
    - require:
      - pkg: bitcoind
