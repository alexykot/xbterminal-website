#!/bin/sh
psql -h 127.0.0.1 -U postgres -c "create user xbterm_usr with password 'zx#213_Op';"
psql -h 127.0.0.1 -U postgres -c "create database xbterminal owner xbterm_usr encoding='utf8';"
