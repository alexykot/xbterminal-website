#!/bin/sh

sudo -u postgres psql -h 127.0.0.1 -U postgres -c "create user xbterm_usr with password 'zx#213_Op';"
sudo -u postgres psql -h 127.0.0.1 -U postgres -c "drop database xbterminal;"
sudo -u postgres psql -h 127.0.0.1 -U postgres -c "create database xbterminal owner xbterm_usr encoding='utf8';"

rm -RIf website/migrations

python manage.py syncdb
python manage.py migrate
python manage.py schemamigration website --initial
python manage.py migrate website --fake
