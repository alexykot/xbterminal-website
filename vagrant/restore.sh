#!/bin/bash

set -e

pg_restore -U postgres -d xbt /vagrant/vagrant/backups/xbt.dump
echo "Database restored."
systemctl stop bitcoind
cp /vagrant/vagrant/backups/wallet.dat /var/lib/bitcoind/testnet3/wallet.dat
systemctl start bitcoind
echo "Wallet restored."
