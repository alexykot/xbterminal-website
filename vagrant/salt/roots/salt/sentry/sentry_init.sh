#!/bin/bash

# Apply migrations
/var/lib/sentry/venv/bin/sentry upgrade --noinput
# Create superuser
/var/lib/sentry/venv/bin/sentry createuser --superuser --email admin --password admin
