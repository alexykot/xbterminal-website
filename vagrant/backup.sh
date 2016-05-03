#!/bin/bash

set -e

mkdir -p /vagrant/vagrant/backups
pg_dump -Fc -U postgres xbt > /vagrant/vagrant/backups/xbt.dump
echo "Database backup created."
cp /var/lib/bitcoind/testnet3/wallet.dat /vagrant/vagrant/backups/wallet.dat
echo "Wallet backup created."
