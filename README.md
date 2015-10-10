# README

### Requirements

* Python 2
* Postgresql
* Redis
* nginx + uwsgi
* supervisord
* Debian packages: `apt-get install libffi-dev libpq-dev`
* Python packages listed in `requirements.txt`

### Local settings

These variables should be redefined in `xbterminal/xbterminal/local_settings.py`:

* DATABASES - database connection settings
* EMAIL_* - SMTP server settings
* PKI_KEY_FILE, PKI_CERTIFICATES - certificates for BIP70
* BITCOIND_AUTH - bitcoind settings
* RECAPTCHA_* - reCaptcha settings
* SALT_SERVERS - Salt server settings
