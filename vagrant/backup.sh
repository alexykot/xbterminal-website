#!/bin/bash

set -e

mkdir -p /vagrant/vagrant/backup
pg_dump -Fc -U postgres xbt > /vagrant/vagrant/backup/xbt.dump
cp /var/lib/bitcoind/testnet3/wallet.dat /vagrant/vagrant/backup/
