# README

## Requirements

* Python 2
* Postgresql
* Redis
* nginx + uwsgi
* supervisord
* Debian packages: `apt-get install libffi-dev libpq-dev libjpeg-dev`
* Python packages listed in `requirements.txt`

## Run vagrant

Install requirements:

* VirtualBox
* vagrant
* vagrant-triggers plugin

Edit `vagrant/settings.yml` (see [example](vagrant/default_settings.yml)).

Start VM:

```
vagrant up
```

### Local settings

These variables should be redefined in `xbterminal/xbterminal/local_settings.py`:

* SITE_ID
* DATABASES - database connection settings
* EMAIL_* - SMTP server settings
* PKI_KEY_FILE, PKI_CERTIFICATES - certificates for BIP70
* BITCOIND_SERVERS - bitcoind settings
* RECAPTCHA_* - reCaptcha settings
* SALT_SERVERS - Salt server settings
* APTLY_SERVERS - Aptly server settings
