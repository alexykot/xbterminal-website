# README

## Production

Requirements:

* Python 2
* Postgresql
* Redis
* nginx + uwsgi
* supervisord
* Debian packages: `apt-get install libffi-dev libpq-dev libjpeg-dev`
* Python packages listed in `requirements.txt`

## Development

Requirements:

* Python 2
* VirtualBox
* vagrant
* vagrant-triggers plugin
* fabric

### Run vagrant

Edit `vagrant/settings.yml` (see [example](vagrant/default_settings.yml)).

Start VM:

```
vagrant up
```

### Prepare virtual env

```
fab build
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

### Start server

```
. venv/bin/activate
honcho start
```

### Testing

```
fab check
```
