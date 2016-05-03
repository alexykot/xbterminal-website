#!/bin/bash

set -e

# Restore database
if [ -f /vagrant/vagrant/backups/xbt.dump ]
then
    pg_restore -U postgres -d xbt /vagrant/vagrant/backups/xbt.dump
    echo "Database restored from backup."
fi

# Restore wallet
if [ -f /vagrant/vagrant/backups/wallet.dat ]
then
    service bitcoind stop
    cp /vagrant/vagrant/backups/wallet.dat /var/lib/bitcoind/testnet3/wallet.dat
    service bitcoind start
    echo "Wallet restored from backup."
fi
