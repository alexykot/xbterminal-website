bitcoin-ppa:
  pkgrepo.managed:
    - ppa: bitcoin/bitcoin
    - refresh_db: true

bitcoind:
  pkg:
    - installed
    - require:
      - pkgrepo: bitcoin-ppa
  service:
    - running
    - require:
      - pkg: bitcoind
      - file: /etc/init/bitcoind.conf
      - file: /etc/bitcoin/bitcoin.conf

bitcoin:
  group:
    - present
    - name: bitcoin
  user:
    - present
    - name: bitcoin
    - shell: /bin/bash
    - home: /var/lib/bitcoind
    - groups:
      - bitcoin
    - require:
      - group: bitcoin

/etc/bitcoin:
  file.directory:
    - name: /etc/bitcoin
    - user: bitcoin
    - group: bitcoin
    - require:
      - user: bitcoin

/etc/bitcoin/bitcoin.conf:
  file.managed:
    - name: /etc/bitcoin/bitcoin.conf
    - source: salt://bitcoind/bitcoin.conf
    - user: bitcoin
    - group: bitcoin
    - mode: 660
    - require:
      - file: /etc/bitcoin
      - user: bitcoin

/etc/init/bitcoind.conf:
  file.managed:
    - name: /etc/init/bitcoind.conf
    - source: salt://bitcoind/bitcoind.conf
    - mode: 755
    - require:
      - pkg: bitcoind
