#!/bin/bash

/var/lib/sentry/venv/bin/sentry upgrade --noinput
/var/lib/sentry/venv/bin/sentry createuser --superuser --email admin --password admin
